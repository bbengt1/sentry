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
    # Optional depth telemetry (Phase 4); defaults keep Phase 2/3 callers valid.
    depth_latency_ms: float | None = None
    depth_fps: float | None = None
    depth_frame_id: int | None = None
    depth_kind: str | None = None
    depth_unit: str | None = None
    depth_error: str | None = None
    # Optional free-space telemetry (Phase 5); defaults keep Phase 2–4 callers valid.
    free_space_latency_ms: float | None = None
    free_space_fps: float | None = None
    free_space_frame_id: int | None = None
    obstacle_count: int | None = None
    free_space_error: str | None = None
    free_space_age_ms: float | None = None
    free_space_stale: bool | None = None
    # Optional pipeline control plane (Phase 6); stage flags + free-space cuts.
    detection_enabled: bool | None = None
    depth_enabled: bool | None = None
    free_space_enabled: bool | None = None
    near_cut: float | None = None
    mid_cut: float | None = None
    # Optional open-vocab telemetry (Phase 6 OVD).
    ov_fps: float | None = None
    ov_latency_ms: float | None = None
    ov_count: int | None = None
    ov_mode: str | None = None
    ov_frame_id: int | None = None
    # Optional backend honesty (Phase 8 BACK-02); factory-authored only.
    backend_requested: str | None = None
    backend_live: str | None = None
    backend_reason: str | None = None
    # Phase 11 BACK-03: soft vs strict policy surface (pass-through only).
    fallback_to_torch: bool | None = None
