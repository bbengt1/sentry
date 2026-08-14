"""Orchestrate YAML persist + fingerprint-gated re-apply (PER-01 / PER-03).

I/O stays in ``config.calibration_store``. ``CalibrationState`` stays
cold-path (no YAML). DepthLoop remains the sole ``apply_map`` site.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sentry_ai.config.calibration_store import (
    delete_params,
    fingerprints_match,
    load_params,
    save_params,
)
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.schemas.calibration import CalibrationFingerprint

__all__ = [
    "ReapplyResult",
    "clear_persisted",
    "persist_applied",
    "refuse_if_mismatch",
    "try_reapply",
]


@dataclass(frozen=True)
class ReapplyResult:
    status: Literal["none", "applied", "ignored_mismatch", "error"]
    reason: str | None = None
    path: Path | None = None


def try_reapply(
    state: CalibrationState,
    path: Path,
    live: CalibrationFingerprint,
) -> ReapplyResult:
    """Load + match + apply_params. Soft-fail corrupt/missing. Never fake samples."""
    dest = Path(path)
    loaded = load_params(dest)
    if loaded.status == "none":
        state.set_persist_status("none")
        return ReapplyResult(status="none", path=dest)
    if loaded.status == "error" or loaded.params is None:
        reason = loaded.reason or "invalid calibration file"
        state.set_persist_status("error", reason)
        return ReapplyResult(status="error", reason=reason, path=dest)
    ok, why = fingerprints_match(loaded.params.fingerprint, live)
    if not ok:
        state.set_persist_status("ignored_mismatch", why)
        return ReapplyResult(status="ignored_mismatch", reason=why, path=dest)
    try:
        state.apply_params(loaded.params)
    except ValueError as exc:
        reason = str(exc)
        state.set_persist_status("error", reason)
        return ReapplyResult(status="error", reason=reason, path=dest)
    state.set_persist_status("applied")
    return ReapplyResult(status="applied", path=dest)


def persist_applied(state: CalibrationState, path: Path) -> Path:
    """save_params(get_applied_params()). Raise ValueError if not applied."""
    params = state.get_applied_params()
    if params is None:
        raise ValueError("no applied calibration params to persist")
    return save_params(params, Path(path))


def clear_persisted(state: CalibrationState, path: Path) -> None:
    """clear_applied + clear_draft + delete_params. Used by REST Clear, not Cancel."""
    state.clear_applied()
    state.clear_draft()
    delete_params(Path(path))


def refuse_if_mismatch(
    state: CalibrationState,
    live: CalibrationFingerprint,
) -> str | None:
    """If applied and fingerprints_match fails → clear + ignored_mismatch.

    Return reason or None. DepthLoop calls this before apply_map (17-02).
    """
    params = state.get_applied_params()
    if params is None:
        return None
    ok, why = fingerprints_match(params.fingerprint, live)
    if ok:
        return None
    state.clear_applied()
    state.set_persist_status("ignored_mismatch", why)
    return why
