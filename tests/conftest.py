"""Shared pytest fixtures for Sentry AI."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sentry_ai.schemas import Frame


def make_synthetic_frame(
    frame_id: int,
    camera_id: str = "synthetic0",
) -> Frame:
    """Build a schema-valid synthetic Frame without camera hardware.

    Imported lazily so Wave 0 / early collection still works before schemas exist.
    """
    from sentry_ai.schemas import Frame

    now = time.time()
    return Frame(
        frame_id=frame_id,
        camera_id=camera_id,
        t_capture=now,
        t_ingest=now,
    )
