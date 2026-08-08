"""Temporal occupancy smoothing for Spatial Post (SPACE-01).

Morphology (open 3×3, close 5×5) + EMA on occupancy float, re-threshold 0.5.
Loop-owned state only — never stored on PerceptionStore.
No torch/transformers — OpenCV + numpy only.
"""

from __future__ import annotations

import cv2
import numpy as np

__all__ = [
    "DEFAULT_EMA_ALPHA",
    "OccupancySmoother",
    "morphology_clean",
    "smooth_occupancy",
]

DEFAULT_EMA_ALPHA = 0.35
_OPEN_KERNEL = 3
_CLOSE_KERNEL = 5
_RETHRESHOLD = 0.5


def morphology_clean(occupied_u8: np.ndarray) -> np.ndarray:
    """Open 3×3 then close 5×5 to kill salt/pepper speckles.

    Expects a binary-ish uint8 mask (0 / nonzero). Returns uint8 0/255.
    Does not mutate the input.
    """
    arr = np.asarray(occupied_u8)
    if arr.ndim != 2:
        raise ValueError(f"occupied_u8 must be HxW, got shape {arr.shape}")
    binary = (arr > 0).astype(np.uint8) * 255
    open_k = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (_OPEN_KERNEL, _OPEN_KERNEL)
    )
    close_k = cv2.getStructuringElement(
        cv2.MORPH_ELLIPSE, (_CLOSE_KERNEL, _CLOSE_KERNEL)
    )
    opened = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_k)
    closed = cv2.morphologyEx(opened, cv2.MORPH_CLOSE, close_k)
    return closed


def smooth_occupancy(
    occupied_u8: np.ndarray,
    *,
    alpha: float = DEFAULT_EMA_ALPHA,
    prev_ema: np.ndarray | None = None,
) -> np.ndarray:
    """Morphology then EMA then re-threshold at 0.5.

    Stateless convenience: when ``prev_ema`` is None the EMA cold-starts on
    the current cleaned frame (equivalent to morphology-only for that call).
    Prefer :class:`OccupancySmoother` for multi-frame temporal state.

    Returns binary uint8 0/255 mask. Does not mutate the input.
    """
    out, _ema = _smooth_with_state(occupied_u8, alpha=alpha, prev_ema=prev_ema)
    return out


def _smooth_with_state(
    occupied_u8: np.ndarray,
    *,
    alpha: float,
    prev_ema: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    cleaned = morphology_clean(occupied_u8)
    current = (cleaned > 0).astype(np.float32)
    a = float(alpha)
    a = max(0.0, min(1.0, a))
    if prev_ema is None or prev_ema.shape != current.shape:
        ema = current.copy()
    else:
        ema = (a * current) + ((1.0 - a) * prev_ema.astype(np.float32))
    out = (ema >= _RETHRESHOLD).astype(np.uint8) * 255
    return out, ema


class OccupancySmoother:
    """Stateful morphology + EMA smoother (owned by FreeSpaceLoop)."""

    def __init__(self, alpha: float = DEFAULT_EMA_ALPHA) -> None:
        self.alpha = float(alpha)
        self._ema: np.ndarray | None = None

    def reset(self) -> None:
        """Drop temporal state (e.g. on camera reconnect)."""
        self._ema = None

    def smooth(self, occupied_u8: np.ndarray) -> np.ndarray:
        """Update EMA state and return re-thresholded occupancy uint8."""
        out, self._ema = _smooth_with_state(
            occupied_u8,
            alpha=self.alpha,
            prev_ema=self._ema,
        )
        return out
