"""create_app factory: inject FrameBus + CaptureLoop; do not start capture."""

from __future__ import annotations

import threading
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from sentry_ai.api.deps import AppState
from sentry_ai.api.routes_calibration import router as calibration_router
from sentry_ai.api.routes_depth import router as depth_router
from sentry_ai.api.routes_detection import router as detection_router
from sentry_ai.api.routes_open_vocab import router as open_vocab_router
from sentry_ai.api.routes_pipeline import router as pipeline_router
from sentry_ai.api.routes_preview import router as preview_router
from sentry_ai.api.routes_v1 import router as v1_router
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
    pipeline_state: Any | None = None,
    detection_loop: Any | None = None,
    depth_loop: Any | None = None,
    free_space_loop: Any | None = None,
    open_vocab_worker: Any | None = None,
    open_vocab_loop: Any | None = None,
    backend_requested: str | None = None,
    backend_live: str | None = None,
    backend_reason: str | None = None,
    fallback_to_torch: bool | None = None,
    calibration_state: Any | None = None,
    serve_ui: bool = True,
) -> FastAPI:
    """Build FastAPI app with preview + detection + depth + pipeline + OV + /v1.

    Caller owns loop lifecycle. Handlers only read bus/status/store — they
    never open cameras or run inference. Optional store/workers/loops default
    to None for Phase 2/3 backward compatibility.

    ``serve_ui=False`` (EDGE-05 headless) keeps ``/api/*``, ``/v1/*``, and
    ``/preview/mjpeg`` but gates GET ``/`` Live Preview HTML.

    Sets ``app.state.shutdown_flag`` (threading.Event) on lifespan exit so
    long-lived MJPEG / WebSocket streams can stop during ``sentry serve`` Ctrl+C.
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
    app.state.pipeline_state = pipeline_state
    app.state.detection_loop = detection_loop
    app.state.depth_loop = depth_loop
    app.state.free_space_loop = free_space_loop
    app.state.open_vocab_worker = open_vocab_worker
    app.state.open_vocab_loop = open_vocab_loop
    # Phase 8 BACK-02: pass-through factory metadata (never recompute live).
    app.state.backend_requested = backend_requested
    app.state.backend_live = backend_live
    app.state.backend_reason = backend_reason
    # Phase 11 BACK-03: soft/strict policy flag (pass-through; preserve False).
    app.state.fallback_to_torch = fallback_to_torch
    app.state.calibration_state = calibration_state
    app.state.calibration_freeze_pin = None
    app.state.serve_ui = serve_ui
    app.state.shutdown_flag = shutdown_flag
    # Typed namespace for convenience (mirrors app.state fields).
    app.state.deps = AppState(
        bus=bus,
        capture_loop=capture_loop,
        bind=bind,
        perception_store=perception_store,
        detection_worker=detection_worker,
        depth_worker=depth_worker,
        pipeline_state=pipeline_state,
        detection_loop=detection_loop,
        depth_loop=depth_loop,
        free_space_loop=free_space_loop,
        open_vocab_worker=open_vocab_worker,
        open_vocab_loop=open_vocab_loop,
        backend_requested=backend_requested,
        backend_live=backend_live,
        backend_reason=backend_reason,
        fallback_to_torch=fallback_to_torch,
        calibration_state=calibration_state,
    )
    app.include_router(preview_router)
    app.include_router(detection_router)
    app.include_router(depth_router)
    app.include_router(calibration_router)
    app.include_router(pipeline_router)
    app.include_router(open_vocab_router)
    app.include_router(v1_router)
    return app
