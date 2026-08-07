"""Capture-source lifecycle status values and wire status snapshot."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class SourceStatus(StrEnum):
    """Lifecycle state for a camera/source capture path.

    Used by the capture loop (02-02) and status APIs (02-03).
    """

    STARTING = "starting"
    STREAMING = "streaming"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"


class StatusSnapshot(BaseModel):
    """Wire-friendly capture status for ``/api/status`` (Phase 2 preview).

    ``bind`` is optional until CLI serve fills it in plan 02-03; defaults to
    ``None`` so the snapshot works without FastAPI.
    """

    model_config = ConfigDict(extra="forbid")

    source: str
    camera_id: str
    status: SourceStatus
    status_detail: str | None = None
    frame_id: int | None = None
    capture_fps: float = Field(ge=0.0)
    frames_dropped: int = Field(ge=0)
    bind: str | None = None
    t_capture: float | None = None
    # Optional detection telemetry (Phase 3); defaults keep Phase 2 callers valid.
    detections_count: int | None = None
    det_latency_ms: float | None = None
    det_conf: float | None = None
    det_fps: float | None = None
    det_frame_id: int | None = None

