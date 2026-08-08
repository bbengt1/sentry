"""Detection API: snapshot PerceptionFrame + runtime conf (DET-03/DET-04).

Handlers only read PerceptionStore / call worker.set_conf.
They never open cameras or run model inference.

Phase 4: snapshot merges depth + detections completeness (DEPTH-02).
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from sentry_ai.schemas.perception import Completeness, DepthPayload, PerceptionFrame

router = APIRouter()


class DetectionConfigUpdate(BaseModel):
    """Runtime conf update body (DET-03). Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    conf: float = Field(ge=0.0, le=1.0)


def _store(request: Request) -> Any:
    return getattr(request.app.state, "perception_store", None)


def _detection_worker(request: Request) -> Any:
    return getattr(request.app.state, "detection_worker", None)


def _require_store(request: Request) -> Any:
    store = _store(request)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="perception store not available",
        )
    return store


def _require_worker(request: Request) -> Any:
    worker = _detection_worker(request)
    if worker is None:
        raise HTTPException(
            status_code=503,
            detail="detection worker not available",
        )
    return worker


@router.get("/api/snapshot")
async def api_snapshot(request: Request) -> dict[str, Any]:
    """Return PerceptionFrame JSON from latest store products (DET-04/DEPTH-02).

    404 only when neither detection nor depth product exists. Depth-only or
    det-only returns 200 with completeness flags. Full depth_map arrays are
    never serialized — metadata + stats only.
    """
    store = _require_store(request)
    det = store.snapshot()
    depth = store.snapshot_depth()

    if det is None and depth is None:
        raise HTTPException(
            status_code=404,
            detail="no perception product yet",
        )

    depth_good = depth is not None and depth.error is None
    det_present = det is not None

    # Prefer identity from the product with the latest t_capture.
    if det is not None and depth is not None:
        primary = det if det.t_capture >= depth.t_capture else depth
    elif det is not None:
        primary = det
    else:
        primary = depth
    assert primary is not None

    stats: dict[str, float | int | str] = {}
    if det is not None:
        stats["det_latency_ms"] = det.latency_ms
        stats["det_frame_id"] = det.frame_id
        if det.conf is not None:
            stats["det_conf"] = det.conf
        if det.model_name is not None:
            stats["det_model"] = det.model_name

    if depth is not None:
        stats["depth_frame_id"] = depth.frame_id
        stats["depth_latency_ms"] = depth.latency_ms
        if depth.min_value is not None:
            stats["depth_min"] = depth.min_value
        if depth.max_value is not None:
            stats["depth_max"] = depth.max_value
        if depth.mean_value is not None:
            stats["depth_mean"] = depth.mean_value
        if depth.model_name is not None:
            stats["depth_model"] = depth.model_name

    depth_payload: DepthPayload | None = None
    if depth_good and depth is not None:
        # Metadata only — never attach depth_map (T-04-03).
        depth_payload = DepthPayload(
            kind=depth.kind,
            unit=depth.unit,
            width=depth.width if depth.width else None,
            height=depth.height if depth.height else None,
        )

    frame = PerceptionFrame(
        schema_version=1,
        frame_id=primary.frame_id,
        camera_id=primary.camera_id,
        t_capture=primary.t_capture,
        t_publish=time.time(),
        completeness=Completeness(
            detections=det_present,
            depth=depth_good,
            free_space=False,
        ),
        depth=depth_payload,
        detections=list(det.detections) if det is not None else None,
        stats=stats if stats else None,
    )
    return frame.model_dump()


@router.get("/api/detection/config")
async def get_detection_config(request: Request) -> dict[str, Any]:
    """Return current detection conf (+ optional weights/device)."""
    worker = _require_worker(request)
    payload: dict[str, Any] = {"conf": float(worker.get_conf())}
    weights = getattr(worker, "weights", None) or getattr(worker, "_weights", None)
    if weights is not None:
        payload["weights"] = str(weights)
    device = getattr(worker, "device", None) or getattr(worker, "_device", None)
    if device is not None:
        payload["device"] = str(device)
    name = getattr(worker, "name", None)
    if name is not None:
        payload["model"] = str(name)
    return payload


@router.patch("/api/detection/config")
async def patch_detection_config(
    body: DetectionConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Update worker conf without process restart (DET-03)."""
    worker = _require_worker(request)
    worker.set_conf(body.conf)
    return {"conf": float(worker.get_conf())}
