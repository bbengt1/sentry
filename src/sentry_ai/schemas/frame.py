"""Camera Frame identity contract.

Timestamps on the wire use ``time.time()`` epoch seconds (float) for
``t_capture`` / optional ``t_ingest``. Internal monotonic clocks may be
added later without changing this epoch convention.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Frame(BaseModel):
    """Minimal camera frame identity without image payload.

    Image arrays/bytes are intentionally omitted so Phase 1 contracts stay
    free of numpy/OpenCV dependencies.
    """

    model_config = ConfigDict(extra="forbid")

    frame_id: int = Field(ge=0)
    camera_id: str = Field(min_length=1)
    t_capture: float  # epoch seconds
    t_ingest: float | None = None
    width: int | None = None
    height: int | None = None
