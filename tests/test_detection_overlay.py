"""DET-04: Detection overlay drawing (pure OpenCV helper)."""

from __future__ import annotations

import numpy as np

from sentry_ai.models.detection.overlay import draw_detections
from sentry_ai.schemas.perception import Detection


def test_draw_detections_empty_list_returns_copy() -> None:
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[10, 10] = (1, 2, 3)
    out = draw_detections(image, [])
    assert out is not image
    assert out.shape == image.shape
    np.testing.assert_array_equal(out, image)
    # Mutating original must not affect the copy.
    image[10, 10] = (9, 9, 9)
    assert tuple(out[10, 10]) == (1, 2, 3)


def test_draw_detections_draws_box_and_leaves_far_pixels() -> None:
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    det = Detection(
        class_name="person",
        confidence=0.87,
        bbox_xyxy=(10.0, 20.0, 50.0, 60.0),
    )
    out = draw_detections(image, [det])
    # Corner of the rectangle should change (high-contrast cyan-ish BGR).
    # OpenCV draws on the edge; sample a point on the top edge of the box.
    edge = out[20, 30]
    assert not np.array_equal(edge, (0, 0, 0)), "box edge should be drawn"
    # Far corner remains black (no fill).
    assert tuple(out[90, 90]) == (0, 0, 0)
    # Original unmodified.
    assert tuple(image[20, 30]) == (0, 0, 0)


def test_draw_detections_accepts_list_bbox() -> None:
    image = np.zeros((40, 40, 3), dtype=np.uint8)
    det = Detection(
        class_name="cup",
        confidence=0.5,
        bbox_xyxy=[5, 5, 20, 20],
    )
    out = draw_detections(image, [det])
    assert out.shape == image.shape
    assert not np.array_equal(out[5, 10], (0, 0, 0))
