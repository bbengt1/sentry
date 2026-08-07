"""Capture runtime types: ImageFrame, source status, and CaptureLoop."""

from __future__ import annotations

from typing import Any

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.status import SourceStatus, StatusSnapshot

__all__ = [
    "CaptureLoop",
    "ImageFrame",
    "SourceStatus",
    "StatusSnapshot",
]


def __getattr__(name: str) -> Any:
    """Lazy-load CaptureLoop to avoid bus ↔ capture circular import."""
    if name == "CaptureLoop":
        from sentry_ai.capture.loop import CaptureLoop

        return CaptureLoop
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
