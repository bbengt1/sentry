"""Pure depth preprocess helpers for worker + golden tests.

No torch/transformers — OpenCV + numpy only.
"""

from __future__ import annotations

import cv2
import numpy as np

__all__ = [
    "bgr_to_rgb_uint8",
    "depth_stats",
]


def bgr_to_rgb_uint8(image_bgr: np.ndarray) -> np.ndarray:
    """Convert BGR HxWx3 uint8 to RGB (copy via cvtColor; does not mutate input)."""
    assert image_bgr.ndim == 3 and image_bgr.shape[2] == 3
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def depth_stats(depth: np.ndarray) -> dict[str, float]:
    """Return min/max/mean over finite values; zeros when no finite samples."""
    finite = depth[np.isfinite(depth)]
    if finite.size == 0:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": float(finite.min()),
        "max": float(finite.max()),
        "mean": float(finite.mean()),
    }
