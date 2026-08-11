"""Public schema contracts for Sentry AI wire types."""

from __future__ import annotations

from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSnapshot,
)
from sentry_ai.schemas.enums import BackendName, DepthKind, RuntimeProfile
from sentry_ai.schemas.frame import Frame
from sentry_ai.schemas.perception import (
    Completeness,
    DepthPayload,
    Detection,
    FreeSpacePayload,
    ObstacleCue,
    PerceptionFrame,
)

__all__ = [
    "BackendName",
    "CalibrationFingerprint",
    "CalibrationParams",
    "CalibrationSnapshot",
    "Completeness",
    "DepthKind",
    "DepthPayload",
    "Detection",
    "Frame",
    "FreeSpacePayload",
    "ObstacleCue",
    "PerceptionFrame",
    "RuntimeProfile",
]
