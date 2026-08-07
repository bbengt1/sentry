"""Detection API: snapshot PerceptionFrame + runtime conf (DET-03/DET-04).

Handlers only read PerceptionStore / call worker.set_conf.
They never open cameras or run model inference.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from sentry_ai.schemas.perception import Completeness, PerceptionFrame

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
    """Return PerceptionFrame JSON from the latest store product (DET-04)."""
    store = _require_store(request)
    product = store.snapshot()
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="no detection product yet",
        )

    stats: dict[str, float | int | str] = {
        "det_latency_ms": product.latency_ms,
    }
    if product.conf is not None:
        stats["det_conf"] = product.conf
    if product.model_name is not None:
        stats["det_model"] = product.model_name

    frame = PerceptionFrame(
        schema_version=1,
        frame_id=product.frame_id,
        camera_id=product.camera_id,
        t_capture=product.t_capture,
        t_publish=time.time(),
        completeness=Completeness(
            detections=True,
            depth=False,
            free_space=False,
        ),
        detections=list(product.detections),
        stats=stats,
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
