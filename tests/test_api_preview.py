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
        gen = _mjpeg_generator(bus, store=None)
        try:
            return await gen.__anext__()
        finally:
            await gen.aclose()

    chunk = asyncio.run(_one_part())
    assert b"--frame" in chunk
    assert b"Content-Type: image/jpeg" in chunk
    assert b"\xff\xd8" in chunk  # JPEG SOI


def test_mjpeg_generator_stops_on_shutdown_flag() -> None:
    """Serve Ctrl+C sets shutdown_flag; generator must exit without hang."""
    import threading

    bus = FrameBus()
    bus.publish(_make_frame())
    flag = threading.Event()
    flag.set()

    async def _drain() -> int:
        gen = _mjpeg_generator(bus, store=None, shutdown_flag=flag)
        count = 0
        async for _ in gen:
            count += 1
            if count > 5:
                break
        return count

    # Already set → zero or immediate exit (no infinite stream)
    n = asyncio.run(_drain())
    assert n == 0


def test_create_app_has_shutdown_flag() -> None:
    bus = FrameBus()
    source = SyntheticSource(camera_id="t", fps=0.0)
    loop = CaptureLoop(source, bus)
    app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
    assert hasattr(app.state, "shutdown_flag")
    assert app.state.shutdown_flag.is_set() is False


def test_mjpeg_generator_with_store_overlay_still_jpeg() -> None:
    """Store detections are drawn before encode; stream remains multipart JPEG."""
    from sentry_ai.schemas.perception import Detection
    from sentry_ai.state.perception_store import PerceptionStore

    bus = FrameBus()
    bus.publish(_make_frame())
    store = PerceptionStore()
    store.set_detections(
        frame_id=0,
        camera_id="synthetic0",
        t_capture=time.time(),
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(2.0, 2.0, 20.0, 20.0),
            )
        ],
        latency_ms=8.0,
        conf=0.25,
    )

    async def _one_part() -> bytes:
        gen = _mjpeg_generator(bus, store=store)
        try:
            return await gen.__anext__()
        finally:
            await gen.aclose()

    chunk = asyncio.run(_one_part())
    assert b"--frame" in chunk
    assert b"\xff\xd8" in chunk


def test_api_status_includes_det_fields_when_store_present() -> None:
    from sentry_ai.schemas.perception import Detection
    from sentry_ai.state.perception_store import PerceptionStore

    class _Worker:
        def get_conf(self) -> float:
            return 0.33

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    store.set_detections(
        frame_id=3,
        camera_id="synthetic0",
        t_capture=time.time(),
        detections=[
            Detection(class_name="cup", confidence=0.7, bbox_xyxy=(1, 1, 5, 5))
        ],
        latency_ms=15.5,
        conf=0.33,
    )
    loop.start()
    try:
        _wait_for_frame(bus)
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            perception_store=store,
            detection_worker=_Worker(),
        )
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["detections_count"] == 1
            assert data["det_latency_ms"] == 15.5
            assert data["det_conf"] == 0.33
            assert data["det_frame_id"] == 3
            assert "det_fps" in data
    finally:
        loop.stop()


def test_routes_preview_has_no_videocapture() -> None:
    """Architecture: handlers never open cameras (only bus/status)."""
    source = inspect.getsource(routes_preview)
    # Reject OpenCV capture API usage (docstring mentions alone are not enough).
    assert "cv2.VideoCapture" not in source
    assert "VideoCapture(" not in source
    # Never run inference on the MJPEG path.
    assert "worker.process" not in source
    assert ".predict(" not in source


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
        # Phase 3: conf control + det telemetry
        assert "Conf" in body or "conf" in body
        assert "Detections" in body
        assert "Det ms" in body
        assert "detection/config" in body
        assert "conf-slider" in body or 'type="range"' in body
        # Phase 4: depth kind + latency (UI-SPEC)
        assert "metric-depth-kind" in body
        assert "metric-depth-ms" in body
        assert "Depth" in body
        assert "not meters" in body  # honesty copy in JS or note
        # Copy constraints from UI-SPEC
        lower = body.lower()
        assert "autonomous" not in lower
        assert "safe to drive" not in lower
        assert "motor" not in lower
        assert "velocity" not in lower


def test_api_status_includes_depth_fields_when_store_present() -> None:
    """DEPTH-04 telemetry: depth_kind + latency; relative omits unit m."""
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.state.perception_store import PerceptionStore

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    depth = np.linspace(0.0, 1.0, 48 * 64, dtype=np.float32).reshape(48, 64)
    store.set_depth(
        frame_id=9,
        camera_id="synthetic0",
        t_capture=time.time(),
        depth_map=depth,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=33.25,
        model_name="depth-anything-v2-small",
    )
    loop.start()
    try:
        _wait_for_frame(bus)
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            perception_store=store,
        )
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["depth_latency_ms"] == 33.25
            assert data["depth_frame_id"] == 9
            assert data["depth_kind"] == "relative"
            assert "depth_fps" in data
            # Relative honesty: unit omitted or null — never forced to "m"
            assert data.get("depth_unit") in (None, "")
            assert data.get("depth_error") in (None, "")
    finally:
        loop.stop()


def test_api_status_depth_error_and_metric_unit() -> None:
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.state.perception_store import PerceptionStore

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    store.set_depth(
        frame_id=2,
        camera_id="synthetic0",
        t_capture=time.time(),
        depth_map=None,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        error="depth failed",
    )
    loop.start()
    try:
        _wait_for_frame(bus)
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            perception_store=store,
        )
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data.get("depth_error") == "depth failed"
    finally:
        loop.stop()

    store2 = PerceptionStore()
    depth = np.ones((16, 16), dtype=np.float32)
    store2.set_depth(
        frame_id=3,
        camera_id="synthetic0",
        t_capture=time.time(),
        depth_map=depth,
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
        latency_ms=10.0,
    )
    source2 = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus2 = FrameBus()
    loop2 = CaptureLoop(source2, bus2)
    loop2.start()
    try:
        _wait_for_frame(bus2)
        app2 = create_app(
            bus=bus2,
            capture_loop=loop2,
            bind="127.0.0.1:8000",
            perception_store=store2,
        )
        with TestClient(app2) as client:
            data = client.get("/api/status").json()
            assert data["depth_kind"] == "metric_estimated"
            assert data["depth_unit"] == "m"
    finally:
        loop2.stop()


def test_mjpeg_generator_with_depth_product_still_jpeg() -> None:
    """DEPTH-03: depth blend path still yields decodable multipart JPEG."""
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.schemas.perception import Detection
    from sentry_ai.state.perception_store import PerceptionStore

    bus = FrameBus()
    bus.publish(_make_frame())
    store = PerceptionStore()
    depth = np.linspace(0.0, 2.0, 48 * 64, dtype=np.float32).reshape(48, 64)
    store.set_depth(
        frame_id=0,
        camera_id="synthetic0",
        t_capture=time.time(),
        depth_map=depth,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=20.0,
    )
    store.set_detections(
        frame_id=0,
        camera_id="synthetic0",
        t_capture=time.time(),
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(2.0, 2.0, 20.0, 20.0),
            )
        ],
        latency_ms=8.0,
    )

    async def _one_part() -> bytes:
        gen = _mjpeg_generator(bus, store=store)
        try:
            return await gen.__anext__()
        finally:
            await gen.aclose()

    chunk = asyncio.run(_one_part())
    assert b"--frame" in chunk
    assert b"\xff\xd8" in chunk  # JPEG SOI


def test_mjpeg_generator_skips_blend_on_depth_error() -> None:
    """Empty/error depth → RGB (+ dets) only; stream stays valid JPEG."""
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.state.perception_store import PerceptionStore

    bus = FrameBus()
    bus.publish(_make_frame())
    store = PerceptionStore()
    store.set_depth(
        frame_id=0,
        camera_id="synthetic0",
        t_capture=time.time(),
        depth_map=None,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        error="no map",
    )

    async def _one_part() -> bytes:
        gen = _mjpeg_generator(bus, store=store)
        try:
            return await gen.__anext__()
        finally:
            await gen.aclose()

    chunk = asyncio.run(_one_part())
    assert b"\xff\xd8" in chunk


def test_routes_preview_uses_blend_depth() -> None:
    """MJPEG path imports/calls blend_depth before draw_detections."""
    source = inspect.getsource(routes_preview)
    assert "blend_depth" in source
    assert "snapshot_depth" in source
    # Order: depth blend before detections (string positions).
    assert source.index("blend_depth") < source.index("draw_detections(")
    assert "worker.process" not in source
    assert "cv2.VideoCapture" not in source
