"""Spatial Post - free-space / obstacle semantics from monocular depth (Phase 5).

CPU-only NumPy/OpenCV. No ML package imports at package touch.
"""

from __future__ import annotations

from typing import Any

__all__ = [
    "CalibrationFitResult",
    "FreeSpaceLoop",
    "FreeSpaceResult",
    "MAX_SCALE",
    "MIN_SCALE",
    "ObstacleCue",
    "OccupancySmoother",
    "compute_free_space",
    "draw_free_space",
    "fit_affine_lstsq",
    "fit_scale_median",
]


def __getattr__(name: str) -> Any:
    """Lazy-load to keep package import light (mirrors models.depth)."""
    if name in {
        "CalibrationFitResult",
        "MAX_SCALE",
        "MIN_SCALE",
        "fit_affine_lstsq",
        "fit_scale_median",
    }:
        from sentry_ai.spatial.calibration import (
            MAX_SCALE,
            MIN_SCALE,
            CalibrationFitResult,
            fit_affine_lstsq,
            fit_scale_median,
        )

        return {
            "CalibrationFitResult": CalibrationFitResult,
            "MAX_SCALE": MAX_SCALE,
            "MIN_SCALE": MIN_SCALE,
            "fit_affine_lstsq": fit_affine_lstsq,
            "fit_scale_median": fit_scale_median,
        }[name]
    if name in {"FreeSpaceResult", "ObstacleCue", "compute_free_space"}:
        from sentry_ai.spatial.free_space import (
            FreeSpaceResult,
            ObstacleCue,
            compute_free_space,
        )

        return {
            "FreeSpaceResult": FreeSpaceResult,
            "ObstacleCue": ObstacleCue,
            "compute_free_space": compute_free_space,
        }[name]
    if name == "OccupancySmoother":
        from sentry_ai.spatial.smoothing import OccupancySmoother

        return OccupancySmoother
    if name == "FreeSpaceLoop":
        from sentry_ai.spatial.loop import FreeSpaceLoop

        return FreeSpaceLoop
    if name == "draw_free_space":
        from sentry_ai.spatial.overlay import draw_free_space

        return draw_free_space
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
