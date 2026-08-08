"""DEPTH-01: pure depth preprocess helpers (BGR→RGB + depth_stats)."""

from __future__ import annotations

import numpy as np

from sentry_ai.models.depth.preprocess import bgr_to_rgb_uint8, depth_stats


def test_bgr_to_rgb_swaps_channels_and_preserves_shape() -> None:
    # BGR pixel: blue=10, green=20, red=30
    bgr = np.zeros((2, 3, 3), dtype=np.uint8)
    bgr[0, 0] = (10, 20, 30)
    bgr[1, 2] = (1, 2, 3)
    original = bgr.copy()

    rgb = bgr_to_rgb_uint8(bgr)

    assert rgb.shape == (2, 3, 3)
    assert rgb.dtype == np.uint8
    assert tuple(rgb[0, 0]) == (30, 20, 10)
    assert tuple(rgb[1, 2]) == (3, 2, 1)
    # Input not mutated
    np.testing.assert_array_equal(bgr, original)


def test_bgr_to_rgb_rejects_non_3channel() -> None:
    gray = np.zeros((4, 4), dtype=np.uint8)
    with __import__("pytest").raises(AssertionError):
        bgr_to_rgb_uint8(gray)
    four = np.zeros((2, 2, 4), dtype=np.uint8)
    with __import__("pytest").raises(AssertionError):
        bgr_to_rgb_uint8(four)


def test_depth_stats_on_ramp() -> None:
    ramp = np.arange(0, 12, dtype=np.float32).reshape(3, 4)
    stats = depth_stats(ramp)
    assert set(stats.keys()) == {"min", "max", "mean"}
    assert stats["min"] == 0.0
    assert stats["max"] == 11.0
    assert stats["mean"] == float(ramp.mean())
    assert all(np.isfinite(v) for v in stats.values())


def test_depth_stats_empty_or_all_nan_returns_zeros() -> None:
    empty = np.array([], dtype=np.float32)
    stats = depth_stats(empty)
    assert stats == {"min": 0.0, "max": 0.0, "mean": 0.0}

    all_nan = np.full((2, 2), np.nan, dtype=np.float32)
    stats_nan = depth_stats(all_nan)
    assert stats_nan == {"min": 0.0, "max": 0.0, "mean": 0.0}


def test_depth_stats_ignores_nan_inf() -> None:
    arr = np.array([[1.0, np.nan], [np.inf, 3.0]], dtype=np.float32)
    stats = depth_stats(arr)
    assert stats["min"] == 1.0
    assert stats["max"] == 3.0
    assert stats["mean"] == 2.0
