"""Fixed-class detection workers and helpers (Phase 3)."""

from __future__ import annotations

from typing import Any

from sentry_ai.models.detection.mapping import results_to_detections

__all__ = [
    "DetectionLoop",
    "YoloDetectionWorker",
    "results_to_detections",
]


def __getattr__(name: str) -> Any:
    """Lazy-load worker/loop to avoid heavy imports on package touch."""
    if name == "YoloDetectionWorker":
        from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker

        return YoloDetectionWorker
    if name == "DetectionLoop":
        from sentry_ai.models.detection.loop import DetectionLoop

        return DetectionLoop
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
