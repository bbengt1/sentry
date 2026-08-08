"""SPACE-01: morphology + EMA occupancy smoothing (pure NumPy/OpenCV)."""

from __future__ import annotations

import inspect

import numpy as np

import sentry_ai.spatial.smoothing as smoothing_mod
from sentry_ai.spatial.smoothing import OccupancySmoother, smooth_occupancy


def test_salt_noise_suppressed_by_morphology() -> None:
    """Single-pixel salt noise is suppressed; static blob persists."""
    h, w = 64, 80
    occupied = np.zeros((h, w), dtype=np.uint8)
    # Solid near blob (large enough to survive open 3×3)
    occupied[30:50, 25:55] = 255
    # Single-pixel salt
    occupied[5, 5] = 255
    occupied[10, 70] = 255
    occupied[60, 3] = 255

    # alpha=1 cold-start ≈ morphology-only on first frame
    out = smooth_occupancy(occupied, alpha=1.0)
    # Salt pixels gone
    assert out[5, 5] == 0
    assert out[10, 70] == 0
    assert out[60, 3] == 0
    # Blob core remains
    assert int(out[40, 40]) > 0


def test_static_blob_persists_across_ema_frames() -> None:
    smoother = OccupancySmoother(alpha=0.35)
    h, w = 48, 64
    blob = np.zeros((h, w), dtype=np.uint8)
    blob[20:40, 15:45] = 255

    last = None
    for _ in range(5):
        last = smoother.smooth(blob)
    assert last is not None
    assert int(last[30, 30]) > 0
    # After several frames of same input, occupancy should be stable
    again = smoother.smooth(blob)
    np.testing.assert_array_equal(last > 0, again > 0)


def test_ema_reduces_one_frame_speckle() -> None:
    """A one-frame flash of occupancy should not fully stick after EMA."""
    smoother = OccupancySmoother(alpha=0.35)
    h, w = 48, 64
    empty = np.zeros((h, w), dtype=np.uint8)
    flash = np.zeros((h, w), dtype=np.uint8)
    # Smallish region that survives morphology
    flash[18:30, 20:40] = 255

    # Warm up on empty
    for _ in range(3):
        out = smoother.smooth(empty)
        assert int(out.sum()) == 0

    # One flash frame
    flashed = smoother.smooth(flash)
    # EMA α=0.35 → first flash may or may not pass 0.5 depending on morphology;
    # subsequent empty should decay.
    for _ in range(4):
        out = smoother.smooth(empty)
    # After several empty frames, occupancy should be gone or greatly reduced.
    assert int(out.sum()) < int(flashed.sum()) or int(out.sum()) == 0


def test_smooth_occupancy_does_not_mutate_input() -> None:
    occupied = np.zeros((32, 32), dtype=np.uint8)
    occupied[10:20, 10:20] = 255
    original = occupied.copy()
    _ = smooth_occupancy(occupied, alpha=0.35)
    np.testing.assert_array_equal(occupied, original)


def test_smoothing_module_has_no_ml_imports() -> None:
    source = inspect.getsource(smoothing_mod)
    assert "import torch" not in source
    assert "from transformers" not in source
    assert "import transformers" not in source
    assert "ultralytics" not in source
