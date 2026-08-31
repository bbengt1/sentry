"""Thread-safe draft vs applied monocular calibration state (CAL-04/05).

Cold-path control plane only — no FastAPI imports, no DepthLoop, no YAML I/O.
Wizard (Phase 15) mutates draft/apply via REST.

Apply formula (CAL-03): map' = scale * map + offset as a new float32 array
(copy-on-write; never mutate the worker buffer). Same apply path for
relative and metric_estimated bases; fingerprint retains depth_mode +
model_id (no undo of metric prior).

DepthLoop (Phase 14):
  result = worker.process(frame)
  kind, unit = state.promote_kind_unit(result.kind, result.unit)
  depth_map = state.apply_map(result.depth_map)
  store.set_depth(..., kind=kind, unit=unit, depth_map=depth_map)
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np

from sentry_ai.schemas.calibration import (
    CalibrationParams,
    CalibrationSnapshot,
    is_valid_calibration_params,
)
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.validators import promote_kind_unit as _promote_kind_unit

__all__ = ["CalibrationState"]

_PERSIST_STATUSES = frozenset({"none", "applied", "ignored_mismatch", "error"})
_ONLINE_STATUSES = frozenset(
    {"online_off", "online_draft", "auto_committed", "rejected"}
)


@dataclass
class CalibrationState:
    """Thread-safe draft vs applied calibration; draft never promotes."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _draft_params: CalibrationParams | None = field(default=None, repr=False)
    _applied_params: CalibrationParams | None = field(default=None, repr=False)
    _draft_samples: list[Any] = field(default_factory=list, repr=False)
    _persist_status: str = field(default="none", repr=False)
    _persist_reason: str | None = field(default=None, repr=False)
    _online_enabled: bool = field(default=False, repr=False)
    _online_status: str = field(default="online_off", repr=False)

    def snapshot(self) -> CalibrationSnapshot:
        """Return an isolated status-safe view of current calibration state."""
        with self._lock:
            return self._snapshot_unlocked()

    def _snapshot_unlocked(self) -> CalibrationSnapshot:
        applied = self._applied_params is not None
        valid = False
        scale: float | None = None
        method: str | None = None
        fingerprint = None
        if self._applied_params is not None:
            ok, _reason = is_valid_calibration_params(self._applied_params)
            valid = ok
            scale = self._applied_params.scale
            method = self._applied_params.method
            fingerprint = self._applied_params.fingerprint
        return CalibrationSnapshot(
            applied=applied,
            valid=valid,
            draft_sample_count=len(self._draft_samples),
            has_draft_params=self._draft_params is not None,
            scale=scale,
            method=method,
            fingerprint=fingerprint,
            persist_status=self._persist_status,  # type: ignore[arg-type]
            persist_reason=self._persist_reason,
            online=self._online_enabled,
            online_status=self._online_status,  # type: ignore[arg-type]
        )

    def add_draft_sample(self, sample: Any) -> CalibrationSnapshot:
        """Append a draft sample under lock; does not apply."""
        with self._lock:
            self._draft_samples.append(sample)
            return self._snapshot_unlocked()

    def get_draft_samples(self) -> list[Any]:
        """Return a shallow copy of draft samples."""
        with self._lock:
            return list(self._draft_samples)

    def clear_draft_samples(self) -> CalibrationSnapshot:
        """Clear samples only (keep draft params unless caller also clear_draft)."""
        with self._lock:
            self._draft_samples.clear()
            return self._snapshot_unlocked()

    def set_draft_params(self, params: CalibrationParams) -> CalibrationSnapshot:
        """Stage draft params without applying (draft never is_applied)."""
        with self._lock:
            self._draft_params = params
            return self._snapshot_unlocked()

    def clear_draft(self) -> CalibrationSnapshot:
        """Discard draft params/samples; does not clear applied."""
        with self._lock:
            self._draft_params = None
            self._draft_samples.clear()
            return self._snapshot_unlocked()

    def apply(self) -> CalibrationSnapshot:
        """Copy valid draft → applied under lock; clear draft on success.

        Raises
        ------
        ValueError
            No draft staged, or draft fails structural validity. Already-applied
            params are left unchanged on failure.
        """
        with self._lock:
            if self._draft_params is None:
                raise ValueError("no draft calibration params to apply")
            ok, reason = is_valid_calibration_params(self._draft_params)
            if not ok:
                raise ValueError(
                    f"invalid draft calibration params: {reason or 'unknown'}"
                )
            self._applied_params = self._draft_params
            self._draft_params = None
            self._draft_samples.clear()
            return self._snapshot_unlocked()

    def apply_params(self, params: CalibrationParams) -> CalibrationSnapshot:
        """Commit valid params as applied without a wizard draft.

        Raises ValueError if structurally invalid. Clears draft on success
        (same as apply()). Does not invent samples.
        """
        with self._lock:
            ok, reason = is_valid_calibration_params(params)
            if not ok:
                raise ValueError(
                    f"invalid calibration params: {reason or 'unknown'}"
                )
            self._applied_params = params
            self._draft_params = None
            self._draft_samples.clear()
            return self._snapshot_unlocked()

    def set_persist_status(
        self,
        status: Literal["none", "applied", "ignored_mismatch", "error"],
        reason: str | None = None,
    ) -> None:
        if status not in _PERSIST_STATUSES:
            raise ValueError(f"invalid persist status: {status}")
        with self._lock:
            self._persist_status = status
            self._persist_reason = reason

    def get_persist_status(self) -> tuple[str, str | None]:
        with self._lock:
            return self._persist_status, self._persist_reason

    def is_online(self) -> bool:
        """Session online-recal flag. Default off; never invents first scale."""
        with self._lock:
            return self._online_enabled

    def set_online_status(
        self,
        status: Literal[
            "online_off", "online_draft", "auto_committed", "rejected"
        ],
    ) -> None:
        """Set four-way online_status. Rejects unknown tokens.

        Phase 19 production routes must not assign auto_committed or rejected.
        """
        if status not in _ONLINE_STATUSES:
            raise ValueError(f"invalid online status: {status}")
        with self._lock:
            self._online_status = status

    def set_online(self, enabled: bool) -> CalibrationSnapshot:
        """Enable or disable session online-recal.

        Enabling while unapplied raises ``ValueError("online_requires_applied")``
        and leaves applied/draft/kind unchanged. Disabling does not clear
        applied params (disable ≠ Clear) and does not touch YAML.
        """
        with self._lock:
            if enabled and self._applied_params is None:
                raise ValueError("online_requires_applied")
            self._online_enabled = bool(enabled)
            if enabled:
                self._online_status = "online_draft"
            else:
                self._online_status = "online_off"
            return self._snapshot_unlocked()

    def clear_applied(self) -> CalibrationSnapshot:
        """Clear applied calibration; restores base kind/unit promotion."""
        with self._lock:
            self._applied_params = None
            self._persist_status = "none"
            self._persist_reason = None
            self._online_enabled = False
            self._online_status = "online_off"
            return self._snapshot_unlocked()

    def is_applied(self) -> bool:
        with self._lock:
            return self._applied_params is not None

    def is_valid_applied(self) -> bool:
        with self._lock:
            if self._applied_params is None:
                return False
            ok, _reason = is_valid_calibration_params(self._applied_params)
            return ok

    def get_applied_params(self) -> CalibrationParams | None:
        """Return applied params (or None). For Phase 14 consumers."""
        with self._lock:
            return self._applied_params

    def promote_kind_unit(
        self, base_kind: DepthKind, base_unit: str | None
    ) -> tuple[DepthKind, str | None]:
        """Return wire kind/unit; only applied+valid yields metric_calibrated+m."""
        with self._lock:
            applied = self._applied_params is not None
            valid = False
            if self._applied_params is not None:
                ok, _reason = is_valid_calibration_params(self._applied_params)
                valid = ok
        return _promote_kind_unit(base_kind, base_unit, applied=applied, valid=valid)

    def apply_map(self, depth_map: np.ndarray | None) -> np.ndarray | None:
        """Copy-on-write float32 ``scale * map + offset`` when applied+valid.

        ``None`` always returns ``None``. Inactive, not-applied, or structurally
        invalid applied params pass through the original array reference (no
        allocation, no calibrated claim). Transforming always returns a new
        HxW float32 array and never mutates the worker buffer.
        """
        if depth_map is None:
            return None
        with self._lock:
            params = self._applied_params
            if params is None:
                return depth_map
            ok, _reason = is_valid_calibration_params(params)
            if not ok:
                return depth_map
            scale = float(params.scale)
            offset = float(params.offset)
        # Compute outside the lock so the hot path does not hold state.
        arr = np.asarray(depth_map)
        return np.asarray(scale * arr + offset, dtype=np.float32)
