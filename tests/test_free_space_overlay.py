"""SPACE-03 foundation: draw_free_space pure OpenCV helper."""

from __future__ import annotations

import inspect

import numpy as np

import sentry_ai.spatial.overlay as overlay_mod
from sentry_ai.spatial.overlay import draw_free_space


def test_draw_free_space_returns_copy_same_shape_dtype() -> None:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[10, 10] = (1, 2, 3)
    free = np.zeros((48, 64), dtype=np.uint8)
    free[20:40, 10:50] = 255
    occ = np.zeros((48, 64), dtype=np.uint8)
    occ[30:40, 20:30] = 255
    out = draw_free_space(image, free_mask=free, occupied_mask=occ)
    assert out is not image
    assert out.shape == image.shape
    assert out.dtype == image.dtype
    # Original not mutated
    assert tuple(image[10, 10]) == (1, 2, 3)
    image[10, 10] = (9, 9, 9)
    assert tuple(out[10, 10]) == (1, 2, 3)


def test_draw_free_space_does_not_mutate_masks() -> None:
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    free = np.zeros((40, 40), dtype=np.uint8)
    free[5:15, 5:15] = 255
    free_copy = free.copy()
    occ = np.zeros((40, 40), dtype=np.uint8)
    occ[20:30, 20:30] = 255
    occ_copy = occ.copy()
    _ = draw_free_space(image, free_mask=free, occupied_mask=occ)
    np.testing.assert_array_equal(free, free_copy)
    np.testing.assert_array_equal(occ, occ_copy)


def test_draw_free_space_tints_free_and_occupied() -> None:
    image = np.zeros((50, 50, 3), dtype=np.uint8)
    free = np.zeros((50, 50), dtype=np.uint8)
    free[5:20, 5:20] = 255
    occ = np.zeros((50, 50), dtype=np.uint8)
    occ[30:45, 30:45] = 255
    out = draw_free_space(image, free_mask=free, occupied_mask=occ, alpha=0.5)
    # Free region should pick up green channel (cool/green tint in BGR)
    free_px = out[10, 10]
    assert free_px[1] > free_px[0]  # G > B for green-ish
    assert free_px[1] > 0
    # Occupied should pick up amber-red (higher R/B warm tones in BGR: R is index 2)
    occ_px = out[35, 35]
    assert occ_px[2] > 0  # red channel
    assert not np.array_equal(free_px, occ_px)
    # Untinted corner stays black
    assert tuple(out[0, 0]) == (0, 0, 0)


def test_draw_free_space_none_masks_returns_content_equivalent_copy() -> None:
    image = np.zeros((30, 40, 3), dtype=np.uint8)
    image[5, 5] = (10, 20, 30)
    out = draw_free_space(image, free_mask=None, occupied_mask=None)
    assert out is not image
    np.testing.assert_array_equal(out, image)


def test_draw_free_space_empty_masks_returns_copy() -> None:
    image = np.full((20, 20, 3), 50, dtype=np.uint8)
    free = np.zeros((20, 20), dtype=np.uint8)
    occ = np.zeros((20, 20), dtype=np.uint8)
    out = draw_free_space(image, free_mask=free, occupied_mask=occ)
    assert out is not image
    np.testing.assert_array_equal(out, image)


def test_draw_free_space_resizes_masks_on_shape_mismatch() -> None:
    image = np.zeros((60, 80, 3), dtype=np.uint8)
    free = np.zeros((30, 40), dtype=np.uint8)
    free[:, :] = 255
    out = draw_free_space(image, free_mask=free, occupied_mask=None, alpha=0.4)
    assert out.shape == (60, 80, 3)
    # Resized free should tint most of the frame
    assert out.mean() > 0


def test_draw_free_space_optional_obstacle_bboxes() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    obstacles = [
        {
            "bbox_xyxy": (10.0, 20.0, 50.0, 60.0),
            "nearness_mean": 0.9,
            "nearness_max": 0.95,
            "area_px": 100,
            "band": "near",
        }
    ]
    out = draw_free_space(image, obstacles=obstacles)
    # Box edge should change
    edge = out[20, 30]
    assert not np.array_equal(edge, (0, 0, 0))
    # Far corner remains black
    assert tuple(out[90, 90]) == (0, 0, 0)
    # Original unmodified
    assert tuple(image[20, 30]) == (0, 0, 0)


def test_draw_free_space_no_safe_go_nogo_text() -> None:
    source = inspect.getsource(overlay_mod)
    lower = source.lower()
    # Explicit safety / autonomy phrases must not appear on pixels or source
    assert "safe to" not in lower
    assert "safe_to" not in lower
    assert "go/nogo" not in lower
    assert "nogo" not in lower
    assert "clear to proceed" not in lower
    assert "putText" not in source  # no labels implying navigability


def test_overlay_module_has_no_model_or_compute_imports() -> None:
    source = inspect.getsource(overlay_mod)
    assert "compute_free_space" not in source
    assert "import torch" not in source
    assert "transformers" not in source
    assert "ultralytics" not in source
    assert "perception_store" not in source
