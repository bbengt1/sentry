"""create_app factory: inject FrameBus + CaptureLoop; do not start capture."""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from sentry_ai.api.deps import AppState
from sentry_ai.api.routes_depth import router as depth_router
from sentry_ai.api.routes_detection import router as detection_router
from sentry_ai.api.routes_preview import router as preview_router
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop


def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
    perception_store: Any | None = None,
    detection_worker: Any | None = None,
    depth_worker: Any | None = None,
) -> FastAPI:
    """Build FastAPI app with preview + detection + depth routes.

    Caller owns loop lifecycle. Handlers only read bus/status/store — they
    never open cameras or run inference. Optional store/workers default to
    None for Phase 2/3 backward compatibility.

    Sets ``app.state.shutdown_flag`` (threading.Event) on lifespan exit so
    long-lived MJPEG streams can stop during ``sentry serve`` Ctrl+C.
    """
    shutdown_flag = threading.Event()

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            shutdown_flag.set()

    app = FastAPI(
        title="Sentry AI — Live Preview",
        docs_url=None,
        redoc_url=None,
        lifespan=lifespan,
    )
    app.state.bus = bus
    app.state.capture_loop = capture_loop
    app.state.bind = bind
    app.state.perception_store = perception_store
    app.state.detection_worker = detection_worker
    app.state.depth_worker = depth_worker
    app.state.shutdown_flag = shutdown_flag
    # Typed namespace for convenience (mirrors app.state fields).
    app.state.deps = AppState(
        bus=bus,
        capture_loop=capture_loop,
        bind=bind,
        perception_store=perception_store,
        detection_worker=detection_worker,
        depth_worker=depth_worker,
    )
    app.include_router(preview_router)
    app.include_router(detection_router)
    app.include_router(depth_router)
    return app
