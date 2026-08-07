"""Server-side detection overlay drawing (DET-04).

Pure OpenCV helper — no ultralytics, no camera I/O. Used by MJPEG encode
and unit-tested with synthetic arrays.
"""

from __future__ import annotations

from collections.abc import Sequence

import cv2
import numpy as np

from sentry_ai.schemas.perception import Detection

__all__ = ["draw_detections"]

# High-contrast cyan-ish BGR for dark video backgrounds (UI-SPEC).
_BOX_COLOR = (0, 255, 180)
_BOX_THICKNESS = 2
_FONT = cv2.FONT_HERSHEY_SIMPLEX
_FONT_SCALE = 0.5
_FONT_THICKNESS = 1


def draw_detections(
    image_bgr: np.ndarray,
    detections: Sequence[Detection],
) -> np.ndarray:
    """Return a copy of ``image_bgr`` with boxes + labels drawn.

    Label format: ``{class_name} {confidence:.2f}`` above the box.
    Empty ``detections`` still returns a copy (content-equivalent).
    """
    out = image_bgr.copy()
    for det in detections:
        x1, y1, x2, y2 = (int(v) for v in det.bbox_xyxy)
        cv2.rectangle(out, (x1, y1), (x2, y2), _BOX_COLOR, _BOX_THICKNESS)
        label = f"{det.class_name} {det.confidence:.2f}"
        text_y = max(0, y1 - 5)
        cv2.putText(
            out,
            label,
            (x1, text_y),
            _FONT,
            _FONT_SCALE,
            _BOX_COLOR,
            _FONT_THICKNESS,
            cv2.LINE_AA,
        )
    return out
