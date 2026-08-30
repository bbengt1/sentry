"""Calibration params, fingerprint, and structural validity (CAL-04/05).

Field design only for Phase 13 — no YAML I/O, no residual RMS product thresholds
(Phase 14), no wizard wiring (Phase 15). Perception-only: no motor/safety fields.
"""

from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "CalibrationFingerprint",
    "CalibrationParams",
    "CalibrationSample",
    "CalibrationSnapshot",
    "is_valid_calibration_params",
]


class CalibrationFingerprint(BaseModel):
    """Identity of the capture/model context for a calibration fit.

    Designed so Phase 17 persist can refuse re-apply on fingerprint mismatch.
    """

    model_config = ConfigDict(extra="forbid")

    camera_id: str = Field(min_length=1)
    width: int | None = None
    height: int | None = None
    depth_mode: str | None = None  # relative | metric_indoor | metric_outdoor
    model_id: str | None = None
    schema_version: int = 1


class CalibrationParams(BaseModel):
    """Scale/offset fit result with capture fingerprint."""

    model_config = ConfigDict(extra="forbid")

    version: int = 1
    scale: float
    offset: float = 0.0
    method: str = "known_distance"  # known_distance | known_height | manual_scale
    sample_count: int = 0
    residual_rms: float | None = None
    fingerprint: CalibrationFingerprint
    created_at: float | None = None


class CalibrationSample(BaseModel):
    """One wizard GT sample. Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    point_uv: tuple[float, float] | None = None
    bbox_xyxy: tuple[float, float, float, float] | None = None
    known_meters: float
    observed_raw: float | None = None  # filled at sample time
    frame_id: int | None = None
    note: str | None = None


class CalibrationSnapshot(BaseModel):
    """API/status-safe view of CalibrationState (Phase 15 will wire this)."""

    model_config = ConfigDict(extra="forbid")

    applied: bool = False
    valid: bool = False
    draft_sample_count: int = 0
    has_draft_params: bool = False
    # Optional status-safe fields when applied (no bulk arrays)
    scale: float | None = None
    method: str | None = None
    fingerprint: CalibrationFingerprint | None = None
    persist_status: Literal["none", "applied", "ignored_mismatch", "error"] = "none"
    persist_reason: str | None = None
    online: bool = False


def is_valid_calibration_params(params: CalibrationParams) -> tuple[bool, str | None]:
    """Structural validity only — no residual RMS threshold policy (Phase 14).

    Returns
    -------
    (True, None) when params are structurally valid.
    (False, reason_code) otherwise.
    """
    if not math.isfinite(params.scale) or params.scale <= 0:
        return False, "scale_not_positive_finite"
    if not math.isfinite(params.offset):
        return False, "offset_not_finite"
    if not params.fingerprint.camera_id:
        return False, "missing_camera_id"
    if params.method == "manual_scale":
        return True, None
    if params.sample_count < 1:
        return False, "insufficient_samples"
    return True, None
