"""Throttled online sampler with gated auto-commit (ONL-03..05, ONL-09).

Control plane over CalibrationState. By default a full window only stages
draft fit params (Phase 20). With ``auto_commit=True`` a passed fit goes live
through ``apply_params(expect_applied=...)`` only when every gate holds,
including the strict free-space horizon refuse and the commit deadband. It
never calls ``apply()`` or ``apply_map``, never writes YAML, and never reads
PerceptionStore. The depth loop stays the only map-transform site.
"""

from __future__ import annotations

import logging
import math
import threading
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal

import numpy as np

from sentry_ai.config.calibration_store import fingerprints_match
from sentry_ai.control.calibration_state import CalibrationState, ConsentAnchor
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
)
from sentry_ai.spatial.calibration import CalibrationFitResult, fit_scale_median
from sentry_ai.spatial.free_space import DEFAULT_METRIC_MID_CUT_M

__all__ = [
    "ONLINE_COMMIT_DEADBAND",
    "ONLINE_MIN_INTERVAL_S",
    "ONLINE_WINDOW_N",
    "OnlineSampleResult",
    "OnlineSampler",
    "horizon_median_m",
    "within_deadband",
]

logger = logging.getLogger(__name__)

ONLINE_WINDOW_N = 8
ONLINE_MIN_INTERVAL_S = 1.0
# Relative commit deadband (Brent 2026-10-08). The only place the 1% lives.
ONLINE_COMMIT_DEADBAND = 0.01


def horizon_median_m(
    raw_map: np.ndarray, scale: float, offset: float
) -> float | None:
    """``scale * median(finite > 0 raw) + offset``, or None with no valid pixel."""
    arr = np.asarray(raw_map, dtype=np.float64)
    valid = arr[np.isfinite(arr) & (arr > 0.0)]
    if valid.size == 0:
        return None
    return float(scale) * float(np.median(valid)) + float(offset)


def within_deadband(candidate_scale: float, applied_scale: float) -> bool:
    """True when ``abs(candidate - applied) < ONLINE_COMMIT_DEADBAND * applied``.

    Same as ``abs(candidate / applied - 1) < ONLINE_COMMIT_DEADBAND`` for a
    positive applied scale. Exactly 1% is outside the band (commits).
    """
    return abs(float(candidate_scale) - float(applied_scale)) < (
        ONLINE_COMMIT_DEADBAND * float(applied_scale)
    )


@dataclass(frozen=True)
class OnlineSampleResult:
    """In-process result. Not a REST model and not a snapshot field."""

    accepted: bool
    reason: str
    fit_ok: bool | None = None


class OnlineSampler:
    """Collect consented observations into draft samples and fit a full window.

    A full window runs ``fit_scale_median``.

    ``auto_commit=False`` (default, Phase 20): ``ok=True`` stages draft params
    only; ``ok=False`` clears draft params. Never commits or sets status.

    ``auto_commit=True`` (Phase 21): a passed fit is checked against the
    safety gates (online, applied, residual, live fingerprint, scale-only,
    strict horizon). Any refuse keeps the applied params, clears draft params,
    and marks ``rejected``. A safe candidate within the deadband is skipped
    (status unchanged). Otherwise it commits via the guarded ``apply_params``,
    clears the window, and calls ``on_auto_commit``.
    """

    def __init__(
        self,
        state: CalibrationState,
        *,
        window_n: int = ONLINE_WINDOW_N,
        min_interval_s: float = ONLINE_MIN_INTERVAL_S,
        auto_commit: bool = False,
        on_auto_commit: Callable[[], None] | None = None,
    ) -> None:
        self._state = state
        self.window_n = window_n
        self.min_interval_s = min_interval_s
        self.auto_commit = bool(auto_commit)
        self._on_auto_commit = on_auto_commit
        self._lock = threading.Lock()
        self._window: deque[list[CalibrationSample]] = deque(maxlen=window_n)
        self._last_accept_s: float | None = None
        self._last_frame_id: int | None = None

    def consider(
        self,
        depth_map: np.ndarray | None,
        *,
        frame_id: int | None,
        now_s: float,
        map_space: Literal["raw", "applied"] = "raw",
        live_fingerprint: CalibrationFingerprint | None = None,
    ) -> OnlineSampleResult:
        """Accept one frame into the draft window, or explain why not.

        A short window returns ``window_short``. A full window runs
        ``fit_scale_median``. Without auto-commit: ``ok=True`` stages draft
        params only (``draft_staged``); ``ok=False`` clears draft params and
        leaves the applied params untouched (``fit_rejected``). With
        auto-commit the outcome is ``committed``, ``within_deadband``,
        ``fit_rejected``, or a gate refuse token; ``live_fingerprint`` is the
        frame's fingerprint and is required for a commit.
        """
        with self._lock:
            if frame_id is None:
                return OnlineSampleResult(accepted=False, reason="missing_frame_id")
            if not self._state.is_online():
                return OnlineSampleResult(accepted=False, reason="online_off")
            if not self._state.is_applied():
                return OnlineSampleResult(accepted=False, reason="not_applied")
            anchors = self._state.get_consent_anchors()
            if not anchors:
                return OnlineSampleResult(accepted=False, reason="no_anchors")
            if (
                self._last_frame_id is not None
                and frame_id <= self._last_frame_id
            ):
                return OnlineSampleResult(
                    accepted=False, reason="frame_not_advanced"
                )
            if (
                self._last_accept_s is not None
                and (float(now_s) - self._last_accept_s) < self.min_interval_s
            ):
                return OnlineSampleResult(accepted=False, reason="throttled")

            raw_map, reject = self._raw_map(depth_map, map_space)
            if reject is not None:
                return reject
            assert raw_map is not None
            observed: list[float] = []
            for anchor in anchors:
                value = _read_positive(raw_map, anchor)
                if value is None:
                    return OnlineSampleResult(accepted=False, reason="empty_roi")
                observed.append(value)

            frame_samples = [
                CalibrationSample(
                    point_uv=anchor.point_uv,
                    bbox_xyxy=anchor.bbox_xyxy,
                    known_meters=anchor.known_meters,
                    observed_raw=value,
                    frame_id=frame_id,
                    note="online",
                )
                for anchor, value in zip(anchors, observed, strict=True)
            ]
            # Cancel clears draft samples. Drop the matching window so the
            # next accept cannot put those frames back.
            if self._window and not self._state.get_draft_samples():
                self._window.clear()
            self._window.append(frame_samples)
            flat = [sample for frame in self._window for sample in frame]
            self._state.replace_draft_samples(flat)
            self._last_accept_s = float(now_s)
            self._last_frame_id = frame_id
            if len(self._window) < self.window_n:
                return OnlineSampleResult(
                    accepted=True, reason="window_short", fit_ok=None
                )
            return self._fit_window(raw_map, live_fingerprint)

    def _fit_window(
        self,
        raw_map: np.ndarray,
        live_fingerprint: CalibrationFingerprint | None,
    ) -> OnlineSampleResult:
        """Fit the full window, then stage (default) or gate and commit."""
        applied = self._state.get_applied_params()
        if applied is None:
            return OnlineSampleResult(accepted=False, reason="not_applied")
        samples = [sample for frame in self._window for sample in frame]
        observed = [float(sample.observed_raw) for sample in samples]
        known = [float(sample.known_meters) for sample in samples]
        result = fit_scale_median(observed, known, method="known_distance")
        if not result.ok:
            self._state.clear_draft_params()
            if self.auto_commit:
                self._state.mark_online_rejected()
            return OnlineSampleResult(
                accepted=True, reason="fit_rejected", fit_ok=False
            )
        applied = self._state.get_applied_params()
        if applied is None:
            return OnlineSampleResult(accepted=False, reason="not_applied")
        candidate = CalibrationParams(
            scale=result.scale,
            offset=result.offset,
            method=result.method,
            sample_count=result.sample_count,
            residual_rms=result.residual_rms,
            fingerprint=applied.fingerprint.model_copy(),
            created_at=time.time(),
        )
        if not self.auto_commit:
            self._state.set_draft_params(candidate)
            return OnlineSampleResult(
                accepted=True, reason="draft_staged", fit_ok=True
            )
        return self._auto_commit(candidate, result, live_fingerprint, raw_map)

    def _auto_commit(
        self,
        candidate: CalibrationParams,
        result: CalibrationFitResult,
        live_fingerprint: CalibrationFingerprint | None,
        raw_map: np.ndarray,
    ) -> OnlineSampleResult:
        """Safety gates, then deadband, then the guarded apply_params."""
        refuse = self._commit_gate(candidate, result, live_fingerprint, raw_map)
        if refuse is not None:
            self._state.clear_draft_params()
            self._state.mark_online_rejected()
            return OnlineSampleResult(accepted=True, reason=refuse, fit_ok=True)
        applied = self._state.get_applied_params()
        if applied is None:
            # Cleared between the gate and here; Clear wins, no status write.
            return OnlineSampleResult(
                accepted=True, reason="commit_stale", fit_ok=True
            )
        if within_deadband(candidate.scale, applied.scale):
            # Safe but not worth a commit: not a refusal, status unchanged.
            self._state.clear_draft_params()
            return OnlineSampleResult(
                accepted=True, reason="within_deadband", fit_ok=True
            )
        try:
            self._state.apply_params(candidate, expect_applied=applied)
        except ValueError:
            self._state.mark_online_rejected()
            return OnlineSampleResult(
                accepted=True, reason="commit_stale", fit_ok=True
            )
        self._window.clear()
        callback = self._on_auto_commit
        if callback is not None:
            try:
                callback()
            except Exception:  # noqa: BLE001 — commit stands; log only
                logger.exception("online auto-commit callback failed")
        return OnlineSampleResult(accepted=True, reason="committed", fit_ok=True)

    def _commit_gate(
        self,
        candidate: CalibrationParams,
        result: CalibrationFitResult,
        live_fingerprint: CalibrationFingerprint | None,
        raw_map: np.ndarray,
    ) -> str | None:
        """Return the first failing safety gate token, or None when all pass.

        Order: online, applied, residual, fingerprint, scale-only, horizon.
        Fit ok and the v0.3 absurd-scale / residual gates already passed in
        ``fit_scale_median``; this re-checks them without editing them.
        """
        if not self._state.is_online():
            return "gate_online_off"
        applied = self._state.get_applied_params()
        if applied is None:
            return "gate_not_applied"
        rms = result.residual_rms
        if not result.ok or rms is None or not math.isfinite(float(rms)):
            return "gate_residual"
        if live_fingerprint is None:
            return "fingerprint_unavailable"
        match, _why = fingerprints_match(applied.fingerprint, live_fingerprint)
        if not match:
            return "fingerprint_mismatch"
        if candidate.offset != 0.0 or candidate.method != "known_distance":
            return "offset_not_zero"
        # Strict (Brent 2026-10-08): never consult the applied scale.
        d_med = horizon_median_m(raw_map, candidate.scale, candidate.offset)
        if d_med is None:
            return "horizon_unknown"
        if d_med >= DEFAULT_METRIC_MID_CUT_M:
            return "horizon_refused"
        return None

    def _raw_map(
        self,
        depth_map: np.ndarray | None,
        map_space: str,
    ) -> tuple[np.ndarray | None, OnlineSampleResult | None]:
        """Return a pre-apply map. Invert only for map_space='applied'."""
        if map_space == "applied":
            params = self._state.get_applied_params()
            if params is None:
                return None, OnlineSampleResult(accepted=False, reason="not_applied")
            scale = float(params.scale)
            offset = float(params.offset)
            # Copied out of the state lock (get_applied_params releases it).
            if (
                not math.isfinite(scale)
                or scale <= 0.0
                or not math.isfinite(offset)
            ):
                return None, OnlineSampleResult(
                    accepted=False, reason="bad_applied_scale"
                )
            if depth_map is None:
                return None, OnlineSampleResult(accepted=False, reason="empty_roi")
            arr = np.asarray(depth_map, dtype=np.float64)
            return (arr - offset) / scale, None
        if depth_map is None:
            return None, OnlineSampleResult(accepted=False, reason="empty_roi")
        return np.asarray(depth_map), None


def _read_positive(arr: np.ndarray, anchor: ConsentAnchor) -> float | None:
    """Point pixel or bbox median. Finite and > 0, same clipping as the wizard."""
    if getattr(arr, "ndim", 0) < 2 or arr.shape[0] < 1 or arr.shape[1] < 1:
        return None
    height, width = int(arr.shape[0]), int(arr.shape[1])
    if anchor.point_uv is not None:
        u, v = anchor.point_uv
        x = int(np.clip(round(float(u)), 0, width - 1))
        y = int(np.clip(round(float(v)), 0, height - 1))
        val = float(arr[y, x])
        if not np.isfinite(val) or val <= 0.0:
            return None
        return val
    if anchor.bbox_xyxy is None:
        return None
    x1, y1, x2, y2 = (float(v) for v in anchor.bbox_xyxy)
    xa = int(np.clip(min(x1, x2), 0, width - 1))
    xb = int(np.clip(max(x1, x2), 0, width - 1))
    ya = int(np.clip(min(y1, y2), 0, height - 1))
    yb = int(np.clip(max(y1, y2), 0, height - 1))
    roi = arr[ya : yb + 1, xa : xb + 1]
    finite = roi[np.isfinite(roi) & (roi > 0.0)]
    if finite.size == 0:
        return None
    return float(np.median(finite))
