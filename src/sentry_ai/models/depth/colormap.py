"""Server-side depth colormap (DEPTH-03).

Pure OpenCV helper — no HF packages, no camera I/O. Used by MJPEG encode
and unit-tested with synthetic arrays.

Near/far colors come from OpenCV COLORMAP_TURBO after min-max normalize of
finite values (near ≈ warm after normalize of inverse-style maps).
"""

from __future__ import annotations

import cv2
import numpy as np

__all__ = ["blend_depth", "colorize_depth"]


def colorize_depth(depth_map: np.ndarray) -> np.ndarray:
    """Convert HxW float depth to HxWx3 uint8 BGR via COLORMAP_TURBO.

    Finite values are min-max normalized to 0..255. Constant maps (zero range)
    map to mid-gray before the colormap. Does not mutate ``depth_map``.
    Never draws unit text (no kind-based meter labels on pixels).
    """
    arr = np.asarray(depth_map)
    if arr.ndim != 2:
        raise ValueError(f"depth_map must be HxW, got shape {arr.shape}")

    finite = arr[np.isfinite(arr)]
    if finite.size == 0:
        norm_u8 = np.zeros(arr.shape, dtype=np.uint8)
    else:
        dmin = float(finite.min())
        dmax = float(finite.max())
        if dmax <= dmin:
            # Constant map: fill mid-gray so TURBO still produces a solid tint.
            norm_u8 = np.full(arr.shape, 128, dtype=np.uint8)
            norm_u8[~np.isfinite(arr)] = 0
        else:
            # Work on a float buffer so callers keep their original map.
            scaled = (arr.astype(np.float64, copy=True) - dmin) / (dmax - dmin)
            scaled = np.clip(scaled, 0.0, 1.0)
            scaled[~np.isfinite(arr)] = 0.0
            norm_u8 = (scaled * 255.0).astype(np.uint8)

    return cv2.applyColorMap(norm_u8, cv2.COLORMAP_TURBO)


def blend_depth(
    rgb_bgr: np.ndarray,
    depth_map: np.ndarray,
    alpha: float = 0.45,
) -> np.ndarray:
    """Alpha-blend TURBO depth colormap onto a BGR image.

    Returns a new array the same HxW as ``rgb_bgr``. If the colorized map
    shape differs, it is resized to the RGB spatial size. Does not mutate
    ``rgb_bgr`` or ``depth_map``. Caller should skip when map is empty/None.
    """
    base = np.asarray(rgb_bgr)
    if base.ndim != 3 or base.shape[2] != 3:
        raise ValueError(f"rgb_bgr must be HxWx3, got shape {base.shape}")

    color = colorize_depth(depth_map)
    h, w = base.shape[:2]
    if color.shape[0] != h or color.shape[1] != w:
        color = cv2.resize(color, (w, h), interpolation=cv2.INTER_LINEAR)

    # addWeighted expects matching dtypes; keep uint8 pipeline.
    a = float(alpha)
    a = max(0.0, min(1.0, a))
    out = cv2.addWeighted(base, 1.0 - a, color, a, 0.0)
    return out
