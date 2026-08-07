"""Public schema contracts for Sentry AI wire types."""

from __future__ import annotations

from sentry_ai.schemas.enums import BackendName, DepthKind, RuntimeProfile
from sentry_ai.schemas.frame import Frame
from sentry_ai.schemas.perception import (
    Completeness,
    DepthPayload,
    Detection,
    FreeSpacePayload,
    PerceptionFrame,
)

__all__ = [
    "BackendName",
    "Completeness",
    "DepthKind",
    "DepthPayload",
    "Detection",
    "Frame",
    "FreeSpacePayload",
    "PerceptionFrame",
    "RuntimeProfile",
]
