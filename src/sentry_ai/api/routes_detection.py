"""Detection API: snapshot PerceptionFrame + runtime conf (DET-03/DET-04).

Handlers only read PerceptionStore / call worker.set_conf.
They never open cameras or run model inference.

Phase 5: GET /api/snapshot is a thin alias of GET /v1/snapshot — both call
assemble_perception_frame only. No dual merge logic here.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from sentry_ai.api.assemble import assemble_perception_frame

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
    """Back-compat alias of GET /v1/snapshot (same assembler).

    404 only when det, depth, and free_space products are all absent.
    Bulk depth_map / free_mask / occupied_mask arrays are never serialized.
    """
    store = _require_store(request)
    frame = assemble_perception_frame(store)
    if frame is None:
        raise HTTPException(
            status_code=404,
            detail="no perception product yet",
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
