"""SPACE-01 / FS-01 / FS-02: near-field bands (ordinal + metric compute)."""

from __future__ import annotations

import inspect

import numpy as np

import sentry_ai.spatial.free_space as free_space_mod
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.free_space import (
    DEFAULT_METRIC_MID_CUT_M,
    DEFAULT_METRIC_NEAR_CUT_M,
    FreeSpaceResult,
    _meters_to_nearness,
    compute_free_space,
)


def _synthetic_near_obstacle_depth(h: int = 120, w: int = 160) -> np.ndarray:
    """Higher values = farther. Near blob (low values) in lower-center."""
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5
    return depth


def _synthetic_far_hallway_depth(h: int = 120, w: int = 160) -> np.ndarray:
    """All pixels 4.0–5.0 m; slightly nearer blob at 4.1 m in lower-center."""
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 4.1
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
    for obs in result.obstacles:
        assert getattr(obs, "distance_m", None) is None


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


def test_metric_constants_are_absolute_meters_not_percentiles() -> None:
    assert DEFAULT_METRIC_NEAR_CUT_M == 1.5
    assert DEFAULT_METRIC_MID_CUT_M == 3.0
    assert DEFAULT_METRIC_NEAR_CUT_M != free_space_mod.DEFAULT_NEAR_CUT
    assert DEFAULT_METRIC_MID_CUT_M != free_space_mod.DEFAULT_MID_CUT


def test_meters_to_nearness_fixed_horizon_not_minmax() -> None:
    arr = np.array([[0.0, 1.5, 3.0, 5.0, np.nan]], dtype=np.float32)
    nearness = _meters_to_nearness(arr)
    assert nearness.shape == arr.shape
    assert abs(float(nearness[0, 0]) - 1.0) < 1e-6
    assert abs(float(nearness[0, 1]) - 0.5) < 1e-6
    assert abs(float(nearness[0, 2]) - 0.0) < 1e-6
    assert abs(float(nearness[0, 3]) - 0.0) < 1e-6
    assert abs(float(nearness[0, 4]) - 0.0) < 1e-6


def test_calibrated_half_meter_blob_emits_meters_and_occupies() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(depth, kind=DepthKind.METRIC_CALIBRATED)
    assert result.error is None
    assert result.units == "m"
    assert result.depth_kind == DepthKind.METRIC_CALIBRATED
    assert result.method == "near_field_bands"
    assert len(result.obstacles) >= 1
    assert result.occupied_mask is not None
    h, w = depth.shape
    blob = result.occupied_mask[
        int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)
    ]
    assert int(blob.sum()) > 0
    for obs in result.obstacles:
        assert 0.0 <= obs.nearness_mean <= 1.0
        assert 0.0 <= obs.nearness_max <= 1.0
        assert obs.distance_m is not None
        assert abs(obs.distance_m - 0.5) < 0.05


def test_relative_and_estimated_stay_ordinal_on_meter_shaped_array() -> None:
    depth = _synthetic_near_obstacle_depth()
    for kind in (DepthKind.RELATIVE, DepthKind.METRIC_ESTIMATED):
        result = compute_free_space(depth, kind=kind)
        assert result.units == "ordinal"
        assert result.depth_kind == kind


def test_fs02_far_hallway_metric_is_far_relative_may_occupy() -> None:
    """FS-02 smoking gun: 4–5 m scene is far in meters, not a 0.72 label flip."""
    depth = _synthetic_far_hallway_depth()
    metric = compute_free_space(depth, kind=DepthKind.METRIC_CALIBRATED)
    assert metric.error is None
    assert metric.units == "m"
    assert metric.bands["near_frac"] < 0.02
    occ = metric.occupied_mask
    assert occ is not None
    assert int((occ > 0).sum()) == 0
    assert metric.obstacles == []

    relative = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert relative.units == "ordinal"
    assert relative.occupied_mask is not None
    assert int(relative.occupied_mask.sum()) > 0
    assert len(relative.obstacles) >= 1


def test_calibrated_uniform_2m_is_mid_not_minmax_split() -> None:
    h, w = 120, 160
    uniform = np.full((h, w), 2.0, dtype=np.float32)
    result = compute_free_space(uniform, kind=DepthKind.METRIC_CALIBRATED)
    assert result.units == "m"
    assert result.bands["mid_frac"] > 0.95
    assert result.bands["near_frac"] < 0.02
    assert result.bands["far_frac"] < 0.02

    rng = np.random.default_rng(0)
    noisy = uniform + rng.uniform(-0.05, 0.05, size=(h, w)).astype(np.float32)
    noisy_result = compute_free_space(noisy, kind=DepthKind.METRIC_CALIBRATED)
    assert noisy_result.bands["mid_frac"] > 0.95
    assert noisy_result.bands["near_frac"] < 0.02
    assert noisy_result.bands["far_frac"] < 0.02


def test_calibrated_ignores_ordinal_near_mid_cuts() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.METRIC_CALIBRATED,
        near_cut=0.99,
        mid_cut=0.01,
    )
    assert result.units == "m"
    assert len(result.obstacles) >= 1
    assert result.occupied_mask is not None
    assert int(result.occupied_mask.sum()) > 0

    uniform = np.full((120, 160), 2.0, dtype=np.float32)
    mid = compute_free_space(
        uniform,
        kind=DepthKind.METRIC_CALIBRATED,
        near_cut=0.99,
        mid_cut=0.01,
    )
    assert mid.bands["mid_frac"] > 0.95
    assert mid.bands["near_frac"] < 0.02
    assert mid.bands["far_frac"] < 0.02


def test_metric_obstacle_nearness_in_unit_interval_closer_is_higher() -> None:
    h, w = 120, 160
    near_map = np.full((h, w), 5.0, dtype=np.float32)
    near_map[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5
    midish_map = np.full((h, w), 5.0, dtype=np.float32)
    midish_map[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 1.2
    near_r = compute_free_space(near_map, kind=DepthKind.METRIC_CALIBRATED)
    mid_r = compute_free_space(midish_map, kind=DepthKind.METRIC_CALIBRATED)
    assert len(near_r.obstacles) >= 1
    assert len(mid_r.obstacles) >= 1
    for obs in (*near_r.obstacles, *mid_r.obstacles):
        assert 0.0 <= obs.nearness_mean <= 1.0
        assert 0.0 <= obs.nearness_max <= 1.0
    assert near_r.obstacles[0].nearness_mean > mid_r.obstacles[0].nearness_mean
    expected = (DEFAULT_METRIC_MID_CUT_M - 0.5) / DEFAULT_METRIC_MID_CUT_M
    assert abs(near_r.obstacles[0].nearness_mean - expected) < 0.05


def test_calibrated_does_not_auto_flip_polarity_on_inverted_meters() -> None:
    """5 m blob on 0.5 m background must not become near via auto polarity."""
    h, w = 120, 160
    depth = np.full((h, w), 0.5, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 5.0
    result = compute_free_space(
        depth,
        kind=DepthKind.METRIC_CALIBRATED,
        nearness_polarity="auto",
    )
    assert result.units == "m"
    occ = result.occupied_mask
    assert occ is not None
    cy, cx = int(h * 0.75), int(w * 0.50)
    assert int(occ[cy, cx]) == 0
    y, x = int(h * 0.80), int(w * 0.10)
    assert int(occ[y, x]) > 0


def test_calibrated_ignores_higher_is_nearer_polarity() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.METRIC_CALIBRATED,
        nearness_polarity="higher_is_nearer",
    )
    assert result.units == "m"
    assert len(result.obstacles) >= 1
    h, w = depth.shape
    blob = result.occupied_mask[
        int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)
    ]
    assert int(blob.sum()) > 0


def test_calibrated_invalid_metric_cuts_error_stays_ordinal() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.METRIC_CALIBRATED,
        metric_near_cut_m=3.0,
        metric_mid_cut_m=1.5,
    )
    assert result.error is not None
    assert result.units == "ordinal"
    assert result.depth_kind == DepthKind.METRIC_CALIBRATED

    equal = compute_free_space(
        depth,
        kind=DepthKind.METRIC_CALIBRATED,
        metric_near_cut_m=2.0,
        metric_mid_cut_m=2.0,
    )
    assert equal.error is not None
    assert equal.units == "ordinal"


def test_calibrated_honors_occupied_mask_override() -> None:
    depth = np.full((120, 160), 5.0, dtype=np.float32)
    mask = np.zeros((120, 160), dtype=np.uint8)
    mask[80:110, 40:80] = 255
    result = compute_free_space(
        depth,
        kind=DepthKind.METRIC_CALIBRATED,
        occupied_mask=mask,
        apply_morphology=False,
    )
    assert result.units == "m"
    assert result.occupied_mask is not None
    assert int(result.occupied_mask[90, 60]) > 0


def test_calibrated_excludes_nonfinite_from_band_denominator() -> None:
    h, w = 120, 160
    depth = np.full((h, w), 2.0, dtype=np.float32)
    depth[int(h * 0.70) : h, : int(w * 0.20)] = np.nan
    result = compute_free_space(depth, kind=DepthKind.METRIC_CALIBRATED)
    assert result.units == "m"
    total = (
        result.bands["near_frac"]
        + result.bands["mid_frac"]
        + result.bands["far_frac"]
    )
    assert 0.99 <= total <= 1.01
    assert result.bands["mid_frac"] > 0.95


def test_calibrated_path_source_does_not_call_depth_to_nearness() -> None:
    source = inspect.getsource(compute_free_space)
    # Calibrated branch must not invoke min–max nearness.
    calibrated_idx = source.index("calibrated = kind == DepthKind.METRIC_CALIBRATED")
    ordinal_call = source.index("depth_to_nearness(")
    meters_call = source.index("_meters_to_nearness(")
    assert meters_call > calibrated_idx
    # The only depth_to_nearness call is on the ordinal else path.
    assert source.count("depth_to_nearness(") == 1
    assert ordinal_call > meters_call


def test_metric_kwargs_ignored_on_ordinal_path() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
        metric_near_cut_m=0.1,
        metric_mid_cut_m=0.2,
    )
    assert result.units == "ordinal"
    assert len(result.obstacles) >= 1


def test_relative_obstacles_omit_distance_m() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert len(result.obstacles) >= 1
    for obs in result.obstacles:
        assert obs.distance_m is None


def test_estimated_obstacles_omit_distance_m() -> None:
    depth = _synthetic_near_obstacle_depth()
    result = compute_free_space(depth, kind=DepthKind.METRIC_ESTIMATED)
    assert result.units == "ordinal"
    for obs in result.obstacles:
        assert obs.distance_m is None
