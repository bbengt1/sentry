"""Shared pytest fixtures for Sentry AI."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np
import pytest

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame
    from sentry_ai.schemas import Frame


def make_synthetic_frame(
    frame_id: int,
    camera_id: str = "synthetic0",
) -> Frame:
    """Build a schema-valid synthetic Frame without camera hardware."""
    from sentry_ai.schemas import Frame

    now = time.time()
    return Frame(
        frame_id=frame_id,
        camera_id=camera_id,
        t_capture=now,
        t_ingest=now,
    )


def make_image_frame(
    frame_id: int,
    camera_id: str = "synthetic0",
    width: int = 64,
    height: int = 48,
) -> ImageFrame:
    """Build a runtime ImageFrame with a small patterned BGR buffer."""
    from sentry_ai.capture.image_frame import ImageFrame
    from sentry_ai.schemas.frame import Frame

    now = time.time()
    meta = Frame(
        frame_id=frame_id,
        camera_id=camera_id,
        t_capture=now,
        t_ingest=now,
        width=width,
        height=height,
    )
    # Patterned BGR: green bar keyed by frame_id for deterministic tests.
    image = np.zeros((height, width, 3), dtype=np.uint8)
    x = (frame_id * 8) % max(width, 1)
    bar_end = min(x + 8, width)
    image[:, x:bar_end] = (0, 255, 0)
    return ImageFrame(meta=meta, image_bgr=image)


@pytest.fixture
def synthetic_frame_factory() -> Callable[..., Frame]:
    """Pytest-accessible factory for schema-valid synthetic Frames."""
    return make_synthetic_frame


@pytest.fixture
def image_frame_factory() -> Callable[..., ImageFrame]:
    """Pytest-accessible factory for runtime ImageFrames."""
    return make_image_frame
