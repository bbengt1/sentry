"""Pure free-space helpers for FreeSpaceLoop + golden tests (SPACE-01 / FS-01).

Two modes:
- RELATIVE / METRIC_ESTIMATED: image-space ordinal occupancy via percentile
  nearness (0.72 / 0.45). Emits ``units=\"ordinal\"``.
- METRIC_CALIBRATED: absolute meter cuts on an already-scaled depth map
  (default near 1.5 m / mid 3.0 m) with pinned ``higher_is_farther``.
  Emits ``units=\"m\"`` only because those meter cuts ran — never a label
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
