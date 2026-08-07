"""UI-01: FastAPI MJPEG preview + status API (ASGI TestClient)."""

from __future__ import annotations

import asyncio
import inspect
import time

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api import routes_preview
from sentry_ai.api.app import create_app
from sentry_ai.api.routes_preview import BOUNDARY, _mjpeg_generator
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.synthetic import SyntheticSource


def _make_frame(frame_id: int = 0) -> ImageFrame:
    meta = Frame(
        frame_id=frame_id,
        camera_id="synthetic0",
        t_capture=time.time(),
        t_ingest=time.time(),
        width=64,
        height=48,
    )
    image = np.zeros((48, 64, 3), dtype=np.uint8)
    image[:, :8] = (0, 255, 0)
    return ImageFrame(meta=meta, image_bgr=image)


def _wait_for_frame(bus: FrameBus, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bus.get_latest() is not None:
            return
        time.sleep(0.01)
    raise AssertionError("no frame published within timeout")


def test_api_status_returns_expected_keys() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    loop.start()
    try:
        _wait_for_frame(bus)
        app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert "status" in data
            assert "capture_fps" in data
            assert "frames_dropped" in data
            assert data["bind"] == "127.0.0.1:8000"
            assert data["camera_id"] == "synthetic0"
    finally:
        loop.stop()


def test_preview_mjpeg_route_headers() -> None:
    """Route returns multipart media type without consuming infinite stream."""
    bus = FrameBus()
    bus.publish(_make_frame())
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    loop = CaptureLoop(source, bus)
    app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")

    from starlette.requests import Request

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": "/preview/mjpeg",
        "raw_path": b"/preview/mjpeg",
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "app": app,
    }
    request = Request(scope)

    async def _call() -> None:
        response = await routes_preview.preview_mjpeg(request)
        assert "multipart" in response.media_type
        assert BOUNDARY in response.media_type
        # Pull one multipart part then cancel (never spin forever).
        gen = response.body_iterator
        chunk = await gen.__anext__()
        assert isinstance(chunk, (bytes, memoryview))
        data = bytes(chunk)
        assert b"--frame" in data or b"\xff\xd8" in data
        await gen.aclose()

    asyncio.run(_call())


def test_mjpeg_generator_emits_jpeg_boundary() -> None:
    bus = FrameBus()
    bus.publish(_make_frame())

    async def _one_part() -> bytes:
        gen = _mjpeg_generator(bus)
        try:
            return await gen.__anext__()
        finally:
            await gen.aclose()

    chunk = asyncio.run(_one_part())
    assert b"--frame" in chunk
    assert b"Content-Type: image/jpeg" in chunk
    assert b"\xff\xd8" in chunk  # JPEG SOI


def test_routes_preview_has_no_videocapture() -> None:
    """Architecture: handlers never open cameras (only bus/status)."""
    source = inspect.getsource(routes_preview)
    # Reject OpenCV capture API usage (docstring mentions alone are not enough).
    assert "cv2.VideoCapture" not in source
    assert "VideoCapture(" not in source


def test_mjpeg_generator_awaits_sleep() -> None:
    """Generator must await asyncio.sleep so CPU does not spin (T-2-02)."""
    source = inspect.getsource(routes_preview)
    assert "asyncio.sleep" in source


def test_root_serves_live_preview_html() -> None:
    """GET / returns UI-SPEC Live Preview page with MJPEG auto-connect."""
    bus = FrameBus()
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    loop = CaptureLoop(source, bus)
    app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        body = resp.text
        assert "Sentry AI — Live Preview" in body
        assert "preview/mjpeg" in body
        assert "api/status" in body
        # Copy constraints from UI-SPEC
        lower = body.lower()
        assert "autonomous" not in lower
        assert "safe to drive" not in lower
