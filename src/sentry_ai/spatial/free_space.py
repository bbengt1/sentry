"""Pure free-space helpers for FreeSpaceLoop + golden tests (SPACE-01 / FS-01).

Two modes:
- RELATIVE / METRIC_ESTIMATED: image-space ordinal occupancy via percentile
  nearness (0.72 / 0.45). Emits ``units="ordinal"``.
- METRIC_CALIBRATED: absolute meter cuts on an already-scaled depth map
  (default near 1.5 m / mid 3.0 m) with pinned ``higher_is_farther``.
  Emits ``units="m"`` only because those meter cuts ran — never a label
  flip of ordinal percentile cuts, and never min–max normalize meters.

Consumes DepthLoop-scaled maps; does not re-scale. No torch/transformers —
OpenCV + numpy only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import cv2
import numpy as np

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.smoothing import OccupancySmoother, morphology_clean

__all__ = [
    "DEFAULT_METRIC_MID_CUT_M",
    "DEFAULT_METRIC_NEAR_CUT_M",
    "DEFAULT_MID_CUT",
    "DEFAULT_MIN_AREA_FRAC",
    "DEFAULT_NEAR_CUT",
    "DEFAULT_ROI_BOTTOM_FRAC",
    "FreeSpaceResult",
    "ObstacleCue",
    "compute_free_space",
    "depth_to_nearness",
]

DEFAULT_ROI_BOTTOM_FRAC = 0.55
DEFAULT_NEAR_CUT = 0.72
DEFAULT_MID_CUT = 0.45
DEFAULT_MIN_AREA_FRAC = 0.0015  # 0.15% of ROI pixels
DEFAULT_METRIC_NEAR_CUT_M = 1.5
DEFAULT_METRIC_MID_CUT_M = 3.0

NearnessPolarity = Literal["auto", "higher_is_farther", "higher_is_nearer"]


@dataclass
class ObstacleCue:
    """Image-space obstacle blob from connected components (ordinal nearness)."""

    bbox_xyxy: tuple[float, float, float, float]
    nearness_mean: float
    nearness_max: float
    area_px: int
    band: str = "near"


@dataclass
class FreeSpaceResult:
    """Pure Spatial Post output for one depth frame."""

    obstacles: list[ObstacleCue] = field(default_factory=list)
    bands: dict[str, float] = field(default_factory=dict)
    free_mask: np.ndarray | None = None
    occupied_mask: np.ndarray | None = None
    method: str = "near_field_bands"
    depth_kind: DepthKind = DepthKind.RELATIVE
    units: str = "ordinal"
    width: int = 0
    height: int = 0
    error: str | None = None


def depth_to_nearness(
    depth_map: np.ndarray,
    *,
    nearness_polarity: NearnessPolarity = "auto",
) -> np.ndarray:
    """Map depth → nearness ∈ [0, 1] where 1 = nearer.

    ``auto`` compares median of bottom 20% vs top 20% strips and chooses
    polarity so the bottom strip is nearer (typical robot-facing FOV).
    """
    arr = np.asarray(depth_map, dtype=np.float32)
    if arr.ndim != 2:
        raise ValueError(f"depth_map must be HxW, got shape {arr.shape}")

    finite = np.isfinite(arr)
    if not finite.any():
        return np.zeros(arr.shape, dtype=np.float32)

    vals = arr[finite]
    dmin = float(vals.min())
    dmax = float(vals.max())
    if dmax <= dmin:
        # Constant map: neutral mid nearness on finite pixels.
        out = np.zeros(arr.shape, dtype=np.float32)
        out[finite] = 0.5
        return out

    # Normalize raw depth to [0, 1] for polarity decisions.
    scaled = (arr - dmin) / (dmax - dmin)
    scaled = np.clip(scaled, 0.0, 1.0)
    scaled = np.where(finite, scaled, 0.0).astype(np.float32)

    polarity = nearness_polarity
    if polarity == "auto":
        polarity = _auto_polarity(scaled)

    if polarity == "higher_is_farther":
        # Low depth → near → high nearness.
        nearness = 1.0 - scaled
    elif polarity == "higher_is_nearer":
        nearness = scaled
    else:
        raise ValueError(
            f"nearness_polarity must be auto|higher_is_farther|higher_is_nearer, "
            f"got {nearness_polarity!r}"
        )

    nearness = np.where(finite, nearness, 0.0).astype(np.float32)
    return nearness


def _meters_to_nearness(depth_m: np.ndarray) -> np.ndarray:
    """Fixed-horizon nearness ∈ [0, 1]. 0 m → 1.0; d >= 3.0 m → 0.0.

    Constant horizon ``DEFAULT_METRIC_MID_CUT_M`` — not per-frame min–max.
    Non-finite pixels map to 0. Calibrated path only.
    """
    arr = np.asarray(depth_m, dtype=np.float32)
    finite = np.isfinite(arr)
    horizon = float(DEFAULT_METRIC_MID_CUT_M)
    nearness = (horizon - arr) / horizon
    nearness = np.clip(nearness, 0.0, 1.0)
    return np.where(finite, nearness, 0.0).astype(np.float32)


def _auto_polarity(
    scaled: np.ndarray,
) -> Literal["higher_is_farther", "higher_is_nearer"]:
    """Choose polarity so bottom strip median nearness > top strip median."""
    h = scaled.shape[0]
    strip = max(1, int(h * 0.20))
    top = scaled[:strip, :]
    bottom = scaled[h - strip :, :]
    top_med = float(np.median(top))
    bot_med = float(np.median(bottom))
    # If bottom has lower raw scaled depth than top, higher_is_farther makes
    # bottom nearer (1 - bot > 1 - top). If bottom is already higher, use
    # higher_is_nearer.
    if bot_med <= top_med:
        return "higher_is_farther"
    return "higher_is_nearer"


def _roi_mask(h: int, w: int, roi_bottom_frac: float) -> np.ndarray:
    frac = float(roi_bottom_frac)
    frac = max(0.0, min(1.0, frac))
    start = int(h * (1.0 - frac))
    mask = np.zeros((h, w), dtype=bool)
    mask[start:h, :] = True
    return mask


def compute_free_space(
    depth_map: np.ndarray,
    *,
    kind: DepthKind,
    nearness_polarity: NearnessPolarity = "auto",
    roi_bottom_frac: float = DEFAULT_ROI_BOTTOM_FRAC,
    near_cut: float = DEFAULT_NEAR_CUT,
    mid_cut: float = DEFAULT_MID_CUT,
    min_area_frac: float = DEFAULT_MIN_AREA_FRAC,
    smoother: OccupancySmoother | None = None,
    occupied_mask: np.ndarray | None = None,
    apply_morphology: bool = True,
    metric_near_cut_m: float = DEFAULT_METRIC_NEAR_CUT_M,
    metric_mid_cut_m: float = DEFAULT_METRIC_MID_CUT_M,
) -> FreeSpaceResult:
    """Derive free-space / obstacles from a monocular depth map.

    Parameters
    ----------
    depth_map:
        HxW float depth. Relative / estimated maps use percentile nearness
        (``units="ordinal"``). Calibrated maps must already be scaled meters;
        this function never re-scales.
    kind:
        Copied onto the result as ``depth_kind``. ``METRIC_CALIBRATED`` selects
        absolute meter cuts and ``units="m"``; other kinds stay ordinal.
    nearness_polarity:
        Ordinal path only. Ignored when ``kind`` is ``METRIC_CALIBRATED``
        (polarity is pinned ``higher_is_farther``).
    near_cut / mid_cut:
        Ordinal nearness thresholds in ``[0, 1]``. Ignored on the calibrated
        path (meter constants / ``metric_*_cut_m`` apply instead).
    metric_near_cut_m / metric_mid_cut_m:
        Absolute meter band cuts for the calibrated path only. Defaults
        1.5 m / 3.0 m. Invalid when ``near >= mid`` (error, ``units="ordinal"``).
    smoother:
        Optional loop-owned ``OccupancySmoother``. When provided, raw near-band
        occupancy is passed through morphology+EMA; spatial morphology alone
        is used when ``smoother is None`` and ``apply_morphology`` is True.
    occupied_mask:
        Optional precomputed HxW occupancy (0/nonzero). When set, band
        fractions still come from nearness or meters; CC uses this mask
        inside ROI.
    apply_morphology:
        When True and no smoother/precomputed mask path needs cleaning,
        apply open/close before connected components.
    """
    try:
        arr = np.asarray(depth_map, dtype=np.float32)
        if arr.ndim != 2:
            return FreeSpaceResult(
                error=f"depth_map must be HxW, got shape {arr.shape}",
                depth_kind=kind,
                units="ordinal",
                method="near_field_bands",
            )

        h, w = int(arr.shape[0]), int(arr.shape[1])
        calibrated = kind == DepthKind.METRIC_CALIBRATED
        near_m = float(metric_near_cut_m)
        mid_m = float(metric_mid_cut_m)
        if calibrated and near_m >= mid_m:
            return FreeSpaceResult(
                error=(
                    "metric_near_cut_m must be < metric_mid_cut_m, "
                    f"got {near_m} >= {mid_m}"
                ),
                depth_kind=kind,
                units="ordinal",
                method="near_field_bands",
            )

        roi = _roi_mask(h, w, roi_bottom_frac)
        roi_count = int(roi.sum())
        units = "m" if calibrated else "ordinal"
        if roi_count == 0:
            empty = np.zeros((h, w), dtype=np.uint8)
            return FreeSpaceResult(
                obstacles=[],
                bands={"near_frac": 0.0, "mid_frac": 0.0, "far_frac": 0.0},
                free_mask=empty,
                occupied_mask=empty,
                method="near_field_bands",
                depth_kind=kind,
                units=units,
                width=w,
                height=h,
            )

        if calibrated:
            # Pin farther-is-higher. Do not call depth_to_nearness (no min–max).
            nearness = _meters_to_nearness(arr)
            finite = np.isfinite(arr)
            finite_roi = finite & roi
            denom = int(finite_roi.sum())
            if denom == 0:
                bands = {"near_frac": 0.0, "mid_frac": 0.0, "far_frac": 0.0}
            else:
                d = arr[finite_roi]
                bands = {
                    "near_frac": float((d < near_m).sum()) / float(denom),
                    "mid_frac": float(((d >= near_m) & (d < mid_m)).sum())
                    / float(denom),
                    "far_frac": float((d >= mid_m).sum()) / float(denom),
                }
        else:
            nearness = depth_to_nearness(
                arr, nearness_polarity=nearness_polarity
            )
            roi_nearness = nearness[roi]
            near_band = roi_nearness >= float(near_cut)
            mid_band = (roi_nearness >= float(mid_cut)) & (
                roi_nearness < float(near_cut)
            )
            far_band = roi_nearness < float(mid_cut)
            bands = {
                "near_frac": float(near_band.sum()) / float(roi_count),
                "mid_frac": float(mid_band.sum()) / float(roi_count),
                "far_frac": float(far_band.sum()) / float(roi_count),
            }

        # Occupied seed: caller mask, else near meters (calibrated) or
        # nearness percentile (ordinal), always gated to ROI.
        if occupied_mask is not None:
            raw = ((np.asarray(occupied_mask) > 0) & roi).astype(np.uint8) * 255
        elif calibrated:
            raw = (finite & (arr < near_m) & roi).astype(np.uint8) * 255
        else:
            raw = ((nearness >= float(near_cut)) & roi).astype(np.uint8) * 255

        if smoother is not None:
            occ_u8 = smoother.smooth(raw)
        elif apply_morphology:
            occ_u8 = morphology_clean(raw)
        else:
            occ_u8 = raw

        # Keep occupied inside ROI after smoothing (EMA may slightly bleed).
        occ_u8 = np.where(roi, occ_u8, 0).astype(np.uint8)

        obstacles = _extract_obstacles(
            occ_u8,
            nearness,
            min_area_px=max(1, int(float(min_area_frac) * roi_count)),
        )

        free_u8 = np.zeros((h, w), dtype=np.uint8)
        free_u8[roi & (occ_u8 == 0)] = 255

        return FreeSpaceResult(
            obstacles=obstacles,
            bands=bands,
            free_mask=free_u8,
            occupied_mask=occ_u8,
            method="near_field_bands",
            depth_kind=kind,
            units=units,
            width=w,
            height=h,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — surface as product error
        return FreeSpaceResult(
            error=str(exc),
            depth_kind=kind,
            units="ordinal",
            method="near_field_bands",
        )


def _extract_obstacles(
    occupied_u8: np.ndarray,
    nearness: np.ndarray,
    *,
    min_area_px: int,
) -> list[ObstacleCue]:
    """Connected components → obstacle cues (bbox + nearness stats)."""
    binary = (occupied_u8 > 0).astype(np.uint8)
    num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(
        binary, connectivity=8
    )
    obstacles: list[ObstacleCue] = []
    for label in range(1, num_labels):  # 0 is background
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < min_area_px:
            continue
        x = int(stats[label, cv2.CC_STAT_LEFT])
        y = int(stats[label, cv2.CC_STAT_TOP])
        bw = int(stats[label, cv2.CC_STAT_WIDTH])
        bh = int(stats[label, cv2.CC_STAT_HEIGHT])
        component = labels == label
        vals = nearness[component]
        if vals.size == 0:
            continue
        obstacles.append(
            ObstacleCue(
                bbox_xyxy=(
                    float(x),
                    float(y),
                    float(x + bw),
                    float(y + bh),
                ),
                nearness_mean=float(vals.mean()),
                nearness_max=float(vals.max()),
                area_px=area,
                band="near",
            )
        )
    # Largest first for stable consumers.
    obstacles.sort(key=lambda o: o.area_px, reverse=True)
    return obstacles
