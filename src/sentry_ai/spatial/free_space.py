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
