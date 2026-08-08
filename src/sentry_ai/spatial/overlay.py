"""Server-side free-space overlay drawing (SPACE-03 foundation).

Pure OpenCV helper — no models, no free-space math, no camera I/O.
Used by MJPEG encode (05-03) and unit-tested with synthetic arrays.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

import cv2
import numpy as np

__all__ = ["draw_free_space"]

# Cool green free tint / amber-red occupied (BGR). Perception cues only.
_FREE_COLOR_BGR = (80, 200, 80)
_OCCUPIED_COLOR_BGR = (40, 80, 220)
_BOX_COLOR_BGR = (40, 80, 220)
_BOX_THICKNESS = 2
_DEFAULT_ALPHA = 0.35


def draw_free_space(
    image_bgr: np.ndarray,
    free_mask: np.ndarray | None = None,
    occupied_mask: np.ndarray | None = None,
    obstacles: Sequence[Any] | None = None,
    *,
    alpha: float = _DEFAULT_ALPHA,
) -> np.ndarray:
    """Return a copy of ``image_bgr`` with free-space / obstacles drawn.

    - Free mask pixels: semi-transparent cool green
    - Occupied / near mask pixels: semi-transparent amber-red
    - Optional obstacle bbox outlines (no confidence / safety labels)

    Does not mutate ``image_bgr`` or masks. Resizes masks to image spatial
    size when shapes differ. Empty/None masks still return a copy
    (content-equivalent when both masks are None/empty and no obstacles).
    """
    base = np.asarray(image_bgr)
    if base.ndim != 3 or base.shape[2] != 3:
        raise ValueError(f"image_bgr must be HxWx3, got shape {base.shape}")

    out = base.copy()
    h, w = out.shape[:2]
    a = float(alpha)
    a = max(0.0, min(1.0, a))

    if free_mask is not None:
        out = _blend_mask(out, free_mask, _FREE_COLOR_BGR, a, h, w)
    if occupied_mask is not None:
        out = _blend_mask(out, occupied_mask, _OCCUPIED_COLOR_BGR, a, h, w)

    if obstacles:
        for obs in obstacles:
            bbox = _bbox_from_obstacle(obs)
            if bbox is None:
                continue
            x1, y1, x2, y2 = (int(v) for v in bbox)
            cv2.rectangle(out, (x1, y1), (x2, y2), _BOX_COLOR_BGR, _BOX_THICKNESS)

    return out


def _blend_mask(
    image: np.ndarray,
    mask: np.ndarray,
    color_bgr: tuple[int, int, int],
    alpha: float,
    h: int,
    w: int,
) -> np.ndarray:
    """Alpha-blend a solid color where mask is nonzero. Returns new array."""
    m = np.asarray(mask)
    if m.ndim != 2:
        raise ValueError(f"mask must be HxW, got shape {m.shape}")
    if m.shape[0] != h or m.shape[1] != w:
        m = cv2.resize(m.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST)
    active = m > 0
    if not active.any():
        return image

    tint = np.zeros_like(image)
    tint[:, :] = color_bgr
    blended = cv2.addWeighted(image, 1.0 - alpha, tint, alpha, 0.0)
    out = image.copy()
    out[active] = blended[active]
    return out


def _bbox_from_obstacle(
    obs: Any,
) -> tuple[float, float, float, float] | None:
    if isinstance(obs, Mapping):
        bbox = obs.get("bbox_xyxy")
    else:
        bbox = getattr(obs, "bbox_xyxy", None)
    if bbox is None:
        return None
    try:
        x1, y1, x2, y2 = (float(v) for v in bbox)
    except (TypeError, ValueError):
        return None
    return (x1, y1, x2, y2)
