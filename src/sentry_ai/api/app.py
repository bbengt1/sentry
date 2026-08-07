"""create_app factory: inject FrameBus + CaptureLoop; do not start capture."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI

from sentry_ai.api.deps import AppState
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
) -> FastAPI:
    """Build FastAPI app with preview + detection routes; caller owns loops.

    Handlers only read bus/status/store — they never open cameras or run
    inference. Optional ``perception_store`` / ``detection_worker`` default
    to None for Phase 2 backward compatibility.
    """
    app = FastAPI(
        title="Sentry AI — Live Preview",
        docs_url=None,
        redoc_url=None,
    )
    app.state.bus = bus
    app.state.capture_loop = capture_loop
    app.state.bind = bind
    app.state.perception_store = perception_store
    app.state.detection_worker = detection_worker
    # Typed namespace for convenience (mirrors app.state fields).
    app.state.deps = AppState(
        bus=bus,
        capture_loop=capture_loop,
        bind=bind,
        perception_store=perception_store,
        detection_worker=detection_worker,
    )
    app.include_router(preview_router)
    app.include_router(detection_router)
    return app
