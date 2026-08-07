"""create_app factory: inject FrameBus + CaptureLoop; do not start capture."""

from __future__ import annotations

from fastapi import FastAPI

from sentry_ai.api.deps import AppState
from sentry_ai.api.routes_preview import router as preview_router
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop


def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
) -> FastAPI:
    """Build FastAPI app with preview routes; caller owns CaptureLoop lifecycle.

    Handlers only read bus/status — they never open cameras.
    """
    app = FastAPI(
        title="Sentry AI — Live Preview",
        docs_url=None,
        redoc_url=None,
    )
    app.state.bus = bus
    app.state.capture_loop = capture_loop
    app.state.bind = bind
    # Typed namespace for convenience (mirrors app.state fields).
    app.state.deps = AppState(bus=bus, capture_loop=capture_loop, bind=bind)
    app.include_router(preview_router)
    return app
