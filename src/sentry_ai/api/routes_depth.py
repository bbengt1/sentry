"""Depth API: runtime depth_mode config (DEPTH-04).

Handlers only read/update depth_worker mode. They never open cameras
or run model inference.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class DepthConfigUpdate(BaseModel):
    """Runtime depth_mode update body (DEPTH-04). Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    depth_mode: Literal["relative", "metric_indoor", "metric_outdoor"]


def _depth_worker(request: Request) -> Any:
    return getattr(request.app.state, "depth_worker", None)


def _require_worker(request: Request) -> Any:
    worker = _depth_worker(request)
    if worker is None:
        raise HTTPException(
            status_code=503,
            detail="depth worker not available",
        )
    return worker


@router.get("/api/depth/config")
async def get_depth_config(request: Request) -> dict[str, Any]:
    """Return current depth_mode (+ optional model id / device)."""
    worker = _require_worker(request)
    payload: dict[str, Any] = {
        "depth_mode": str(worker.get_depth_mode()),
    }
    model_id = getattr(worker, "model_id", None) or getattr(
        worker, "_model_id", None
    )
    if model_id is not None:
        payload["model_id"] = str(model_id)
    name = getattr(worker, "name", None)
    if name is not None:
        payload["model"] = str(name)
    device = getattr(worker, "device", None) or getattr(worker, "_device", None)
    if device is not None:
        payload["device"] = str(device)
    return payload


@router.patch("/api/depth/config")
async def patch_depth_config(
    body: DepthConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Update worker depth_mode without process restart (DEPTH-04)."""
    worker = _require_worker(request)
    worker.set_depth_mode(body.depth_mode)
    return {"depth_mode": str(worker.get_depth_mode())}
