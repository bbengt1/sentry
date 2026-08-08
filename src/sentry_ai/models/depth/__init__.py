"""Monocular depth workers and helpers (Phase 4)."""

from __future__ import annotations

from typing import Any

__all__ = [
    "DepthAnythingWorker",
    "DepthLoop",
]


def __getattr__(name: str) -> Any:
    """Lazy-load worker/loop to avoid heavy imports on package touch."""
    if name == "DepthAnythingWorker":
        from sentry_ai.models.depth.worker import DepthAnythingWorker

        return DepthAnythingWorker
    if name == "DepthLoop":
        from sentry_ai.models.depth.loop import DepthLoop

        return DepthLoop
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
