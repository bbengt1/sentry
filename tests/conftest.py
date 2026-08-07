"""Shared pytest fixtures for Sentry AI."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
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


@pytest.fixture
def synthetic_frame_factory() -> Callable[..., Frame]:
    """Pytest-accessible factory for schema-valid synthetic Frames."""
    return make_synthetic_frame
