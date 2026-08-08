"""Versioned perception API: GET /v1/snapshot + WS /v1/stream (API-01/API-02).

Handlers only read PerceptionStore via assemble_perception_frame.
They never open cameras, run inference, or compute free-space (Spatial Post).

WS /v1/stream is keep-latest at ~10 Hz JSON — no per-client queue, no
inference in the stream task. Honors app.state.shutdown_flag like MJPEG.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

from sentry_ai.api.assemble import assemble_perception_frame

router = APIRouter()

# ~10 Hz keep-latest publish rate (API-01). Fixed sleep; no backlog queue.
STREAM_PERIOD_S = 0.1
STREAM_POLL_S = 0.02  # interruptible sleep slice for fast shutdown


def _store(request: Request) -> Any:
    return getattr(request.app.state, "perception_store", None)


def _require_store(request: Request) -> Any:
    store = _store(request)
    if store is None:
        raise HTTPException(
            status_code=503,
            detail="perception store not available",
        )
    return store


@router.get("/v1/snapshot")
async def v1_snapshot(request: Request) -> dict[str, Any]:
    """Return merged PerceptionFrame JSON (API-02).

    404 only when det, depth, and free_space products are all absent.
    Bulk depth_map / free_mask / occupied_mask arrays are never serialized.
    Canonical path; ``GET /api/snapshot`` is a thin alias of this contract.
    """
    store = _require_store(request)
    frame = assemble_perception_frame(store)
    if frame is None:
        raise HTTPException(
            status_code=404,
            detail="no perception product yet",
        )
    return frame.model_dump()


@router.websocket("/v1/stream")
async def v1_stream(websocket: WebSocket) -> None:
    """Stream PerceptionFrame JSON at ~10 Hz keep-latest (API-01).

    - Accepts connection even when store empty (sends when products appear)
    - No per-client queue: always latest assemble result
    - Breaks on shutdown_flag or WebSocketDisconnect
    - Never runs Spatial Post / inference in this task
    """
    await websocket.accept()
    store = getattr(websocket.app.state, "perception_store", None)
    shutdown_flag = getattr(websocket.app.state, "shutdown_flag", None)

    async def _interruptible_sleep(seconds: float) -> bool:
        """Sleep in slices; return True if shutdown requested mid-sleep."""
        remaining = seconds
        while remaining > 0:
            if shutdown_flag is not None and shutdown_flag.is_set():
                return True
            step = min(STREAM_POLL_S, remaining)
            await asyncio.sleep(step)
            remaining -= step
        return shutdown_flag is not None and shutdown_flag.is_set()

    try:
        while True:
            if shutdown_flag is not None and shutdown_flag.is_set():
                break
            if store is not None:
                frame = assemble_perception_frame(store)
                if frame is not None:
                    await websocket.send_json(frame.model_dump())
            if await _interruptible_sleep(STREAM_PERIOD_S):
                break
    except WebSocketDisconnect:
        return
