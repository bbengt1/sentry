"""SPACE-01: near-field percentile band free-space (pure NumPy/OpenCV)."""

from __future__ import annotations

import inspect

import numpy as np

import sentry_ai.spatial.free_space as free_space_mod
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.free_space import FreeSpaceResult, compute_free_space


def _synthetic_near_obstacle_depth(h: int = 120, w: int = 160) -> np.ndarray:
    """Higher values = farther. Near blob (low values) in lower-center."""
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5
    return depth


def test_near_blob_yields_obstacle_and_occupied_in_roi() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert isinstance(result, FreeSpaceResult)
    assert result.error is None
    assert len(result.obstacles) >= 1
    assert result.occupied_mask is not None
    assert int(result.occupied_mask.sum()) > 0
    # Occupied pixels must lie inside bottom ROI (default 0.55).
    h = depth.shape[0]
    roi_start = int(h * (1.0 - 0.55))
    occ_ys, _ = np.where(result.occupied_mask > 0)
    assert occ_ys.size > 0
    assert int(occ_ys.min()) >= roi_start


def test_upper_fov_outside_roi_not_counted_as_free() -> None:
    """Sky/upper FOV outside ROI is not free-space for ground robots."""
    h, w = 100, 80
    # Near blob only in upper half (outside default ROI).
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[0 : int(h * 0.3), int(w * 0.3) : int(w * 0.7)] = 0.2
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
        roi_bottom_frac=0.55,
    )
    free = result.free_mask
    assert free is not None
    # Upper strip must have zero free pixels (free only defined in ROI).
    upper = free[: int(h * 0.4), :]
    assert int(upper.sum()) == 0


def test_relative_kind_units_ordinal_method_and_no_distance_m() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert result.units == "ordinal"
    assert result.method == "near_field_bands"
    assert result.depth_kind == DepthKind.RELATIVE
    assert not hasattr(result, "distance_m")
    for obs in result.obstacles:
        assert not hasattr(obs, "distance_m")
        assert "distance_m" not in getattr(obs, "__dict__", {})
        if isinstance(obs, dict):
            assert "distance_m" not in obs


def test_metric_estimated_still_ordinal_units() -> None:
    """Research Q4: no meters without calibration even if kind is metric_estimated."""
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.METRIC_ESTIMATED,
        nearness_polarity="higher_is_farther",
    )
    assert result.units == "ordinal"
    assert result.depth_kind == DepthKind.METRIC_ESTIMATED


def test_higher_is_nearer_and_farther_polarities() -> None:
    h, w = 120, 160
    # higher_is_farther: low values = near obstacle in lower center
    depth_far = np.full((h, w), 5.0, dtype=np.float32)
    depth_far[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5
    r_far = compute_free_space(
        depth_far,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert len(r_far.obstacles) >= 1

    # higher_is_nearer: invert map so high values = near
    depth_near = np.full((h, w), 0.5, dtype=np.float32)
    depth_near[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 5.0
    r_near = compute_free_space(
        depth_near,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_nearer",
    )
    assert len(r_near.obstacles) >= 1
    # Occupied should concentrate in lower half for both.
    for r in (r_far, r_near):
        ys, _ = np.where(r.occupied_mask > 0)
        assert ys.size > 0
        assert float(ys.mean()) > h * 0.5


def test_auto_polarity_chooses_bottom_nearer_on_typical_fov() -> None:
    """auto: bottom strip nearer than top on typical robot FOV synthetic."""
    h, w = 120, 160
    # Gradient: low at bottom, high at top (higher_is_farther style) + near blob
    yy = np.linspace(0.0, 1.0, h, dtype=np.float32).reshape(h, 1)
    depth = np.broadcast_to(5.0 - 4.0 * yy, (h, w)).copy()  # bottom=1, top=5
    depth[int(h * 0.6) : h, int(w * 0.4) : int(w * 0.6)] = 0.3
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="auto",
    )
    assert result.error is None
    # Nearness should make bottom occupied more than top.
    assert int(result.occupied_mask[int(h * 0.7) :, :].sum()) > int(
        result.occupied_mask[: int(h * 0.3), :].sum()
    )


def test_bands_frac_sum_and_keys() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert set(result.bands.keys()) >= {"near_frac", "mid_frac", "far_frac"}
    total = (
        result.bands["near_frac"]
        + result.bands["mid_frac"]
        + result.bands["far_frac"]
    )
    assert 0.99 <= total <= 1.01


def test_free_space_module_has_no_ml_imports() -> None:
    source = inspect.getsource(free_space_mod)
    assert "import torch" not in source
    assert "from transformers" not in source
    assert "import transformers" not in source
    assert "ultralytics" not in source
