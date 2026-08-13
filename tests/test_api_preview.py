"""UI-01: FastAPI MJPEG preview + status API (ASGI TestClient)."""

from __future__ import annotations

import asyncio
import inspect
import time
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api import routes_preview
from sentry_ai.api.app import create_app
from sentry_ai.api.routes_preview import (
    BOUNDARY,
    QuietStreamingResponse,
    _mjpeg_generator,
)
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


def test_quiet_streaming_response_swallows_cancelled() -> None:
    async def _body() -> Any:
        yield b"x"
        raise asyncio.CancelledError

    resp = QuietStreamingResponse(_body(), media_type="text/plain")

    async def _run() -> None:
        messages: list[Any] = []

        async def receive() -> dict[str, str]:
            return {"type": "http.disconnect"}

        async def send(message: dict[str, Any]) -> None:
            messages.append(message)

        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "path": "/",
            "raw_path": b"/",
            "query_string": b"",
            "headers": [],
        }
        # Should not raise CancelledError to caller
        await resp(scope, receive, send)

    asyncio.run(_run())


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
        # Phase 5: free-space footer + STALE/incomplete honesty
        assert "metric-free-space" in body
        assert "metric-obstacles" in body
        assert "metric-free-age" in body
        assert "stale-pill" in body
        assert "incomplete-pill" in body
        assert "obstacle_count" in body or "Obstacles" in body
        # Phase 6: stage toggles + free-space cuts + stage FPS (UI-03/04/05)
        assert "pipeline/config" in body
        assert "toggle-detection" in body
        assert "toggle-depth" in body
        assert "toggle-free-space" in body
        assert "near-cut-slider" in body
        assert "mid-cut-slider" in body
        assert "metric-det-fps" in body
        assert "metric-depth-fps" in body
        assert "metric-free-fps" in body
        assert "detection_enabled" in body
        assert "near_cut" in body
        # Phase 6 open-vocab prompt UX (OVD-01/02/03)
        assert "open-vocab" in body.lower()
        assert "open-vocab/run" in body or "/api/open-vocab/" in body
        assert "ov-prompt" in body
        assert "ov-run" in body
        assert "ov-continuous" in body
        assert "metric-ov-ms" in body
        assert "metric-ov-fps" in body
        assert "person, red cup, toolbox" in body  # placeholder
        assert "AGPL" in body or "yoloe" in body.lower()
        # Phase 15: calibration wizard (WIZ-03 / OPS-01 UI)
        assert "calibration-wizard" in body
        assert "api/depth/calibration" in body
        assert "calib-known-m" in body
        assert "calib-sample" in body
        assert "calib-compute" in body
        assert "calib-apply" in body
        assert "calib-cancel" in body
        assert "calib-clear" in body
        assert "calib-count" in body
        assert "calib-draft" in body
        assert "metric-calibration" in body
        assert "calibration_active" in body
        # Copy constraints from UI-SPEC (T-05-06)
        lower = body.lower()
        assert "autonomous" not in lower
        assert "safe to drive" not in lower
        assert "safe_to_drive" not in lower
        assert "clear to proceed" not in lower
        assert "navigation cleared" not in lower
        assert "go_nogo" not in lower
        assert "motor" not in lower
        assert "velocity" not in lower


def test_live_preview_and_readme_language_denylist() -> None:
    """T-05-06: HTML + README never claim safe-to-drive / go-nogo."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "src" / "sentry_ai" / "ui" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    readme = (root / "README.md").read_text(encoding="utf-8")
    banned = (
        "safe to drive",
        "safe_to_drive",
        "clear to proceed",
        "clear_to_proceed",
        "navigation cleared",
        "go_nogo",
        "go/nogo",
    )
    for text, label in ((html, "index.html"), (readme, "README.md")):
        lower = text.lower()
        for phrase in banned:
            assert phrase not in lower, f"{label} contains banned phrase: {phrase}"
        # Status field names for free-space must be present in HTML
    assert "free_space_stale" in html or "stale-pill" in html
    assert "obstacle_count" in html or "metric-obstacles" in html
    # README documents /v1 contract
    assert "/v1/snapshot" in readme
    assert "/v1/stream" in readme
    assert "near_field_bands" in readme
    assert "perception" in readme.lower()


def test_calibration_wizard_html_contracts() -> None:
    """WIZ-03 / OPS-01: static wizard panel + honesty; no local metric_calibrated."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    html = (root / "src" / "sentry_ai" / "ui" / "static" / "index.html").read_text(
        encoding="utf-8"
    )
    lower = html.lower()
    assert 'id="calibration-wizard"' in html
    assert "api/depth/calibration" in html
    assert "/api/depth/calibration/sample" in html
    assert "/api/depth/calibration/compute" in html
    assert "/api/depth/calibration/apply" in html
    assert "/api/depth/calibration/cancel" in html
    assert "/api/depth/calibration/clear" in html
    assert 'id="calib-known-m"' in html
    assert 'id="calib-method"' in html
    assert 'id="calib-height-m"' in html
    assert 'id="calib-sample"' in html
    assert 'id="calib-compute"' in html
    assert 'id="calib-apply"' in html
    assert 'id="calib-cancel"' in html
    assert 'id="calib-clear"' in html
    assert 'id="calib-count"' in html
    assert 'id="calib-draft"' in html
    assert 'id="calib-msg"' in html
    assert 'id="metric-calibration"' in html
    assert "calibration_active" in html
    assert "calibration_sample_count" in html
    assert "naturalWidth" in html
    assert "naturalHeight" in html
    assert "hobby monocular" in lower
    assert "not vehicle-grade" in lower
    assert "drops draft only" in lower
    assert "drops applied" in lower
    assert "approximate fov helper" in lower
    assert "draft (not live)" in lower
    assert "clear applied first" in lower
    assert "STATUS_POLL_MS = 500" in html
    # Depth badge driven only by status depth_kind — never assign locally.
    assert 'elDepthKind.textContent = "metric_calibrated"' not in html
    assert "elDepthKind.textContent = 'metric_calibrated'" not in html
    assert "elCalibDraft" in html
    banned = (
        "autonomous",
        "safe_to_drive",
        "go_nogo",
        "motor",
        "velocity",
    )
    for phrase in banned:
        assert phrase not in lower, f"index.html contains banned phrase: {phrase}"


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


def test_routes_preview_draw_order_includes_free_space() -> None:
    """SPACE-03 / UI-06: blend_depth → draw_free_space → draw_detections.

    Free-space comes from store product only — never compute_free_space in
    the preview route module.
    """
    source = inspect.getsource(routes_preview)
    assert "draw_free_space" in source
    assert "snapshot_free_space" in source
    assert "compute_free_space" not in source
    blend_i = source.index("blend_depth")
    free_i = source.index("draw_free_space(")
    det_i = source.index("draw_detections(")
    assert blend_i < free_i < det_i


def test_api_status_includes_free_space_fields_when_store_present() -> None:
    """SPACE-03 / UI-02: free_space_* + obstacle_count on /api/status."""
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.schemas.perception import ObstacleCue
    from sentry_ai.state.perception_store import PerceptionStore

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    store.set_free_space(
        frame_id=11,
        camera_id="synthetic0",
        t_capture=time.time(),
        latency_ms=5.5,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=2,
        obstacles=[
            ObstacleCue(
                bbox_xyxy=(1.0, 1.0, 5.0, 5.0),
                nearness_mean=0.8,
                nearness_max=0.9,
                area_px=16,
                band="near",
            )
        ],
        bands={"near_frac": 0.1},
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
            assert data["free_space_latency_ms"] == 5.5
            assert data["free_space_frame_id"] == 11
            assert data["obstacle_count"] == 2
            assert "free_space_fps" in data
            assert "free_space_age_ms" in data
            assert isinstance(data["free_space_stale"], bool)
            assert data.get("free_space_error") in (None, "")
    finally:
        loop.stop()


def test_api_status_includes_pipeline_stage_flags() -> None:
    """UI-03/UI-05: stage flags + free-space cuts on /api/status when state set."""
    from sentry_ai.control.pipeline_state import PipelineState
    from sentry_ai.spatial.free_space import DEFAULT_MID_CUT, DEFAULT_NEAR_CUT
    from sentry_ai.state.perception_store import PerceptionStore

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    state = PipelineState()
    state.update(detection_enabled=False, near_cut=0.8)
    loop.start()
    try:
        _wait_for_frame(bus)
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            perception_store=store,
            pipeline_state=state,
        )
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["detection_enabled"] is False
            assert data["depth_enabled"] is True
            assert data["free_space_enabled"] is True
            assert data["near_cut"] == 0.8
            assert data["mid_cut"] == DEFAULT_MID_CUT
            # Existing telemetry keys still present when store set
            assert "det_fps" in data
            assert "depth_fps" in data
            assert "free_space_fps" in data
    finally:
        loop.stop()

    # Without pipeline_state, stage keys omitted (not forced false).
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
        )
        with TestClient(app2) as client:
            data = client.get("/api/status").json()
            assert data.get("detection_enabled") is None
            assert data.get("near_cut") is None
            # Capture keys still present
            assert "capture_fps" in data
            assert data.get("near_cut", DEFAULT_NEAR_CUT) or True
    finally:
        loop2.stop()


def test_api_status_free_space_error_field() -> None:
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.state.perception_store import PerceptionStore

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    store.set_free_space(
        frame_id=2,
        camera_id="synthetic0",
        t_capture=time.time(),
        latency_ms=1.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        error="free-space failed",
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
            assert data.get("free_space_error") == "free-space failed"
    finally:
        loop.stop()


def test_mjpeg_generator_with_free_space_product_still_jpeg() -> None:
    """Free-space overlay path still yields decodable multipart JPEG."""
    from sentry_ai.schemas.enums import DepthKind
    from sentry_ai.schemas.perception import ObstacleCue
    from sentry_ai.state.perception_store import PerceptionStore

    bus = FrameBus()
    bus.publish(_make_frame())
    store = PerceptionStore()
    free_mask = np.ones((48, 64), dtype=np.uint8)
    free_mask[:10, :] = 0
    occ = np.zeros((48, 64), dtype=np.uint8)
    occ[:10, :10] = 1
    store.set_free_space(
        frame_id=0,
        camera_id="synthetic0",
        t_capture=time.time(),
        latency_ms=3.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=[
            ObstacleCue(
                bbox_xyxy=(2.0, 2.0, 12.0, 12.0),
                nearness_mean=0.7,
                nearness_max=0.9,
                area_px=100,
                band="near",
            )
        ],
        free_mask=free_mask,
        occupied_mask=occ,
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
