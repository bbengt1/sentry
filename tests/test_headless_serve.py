"""EDGE-05: Headless serve — create_app(serve_ui=False) without Live Preview HTML."""

from __future__ import annotations

import time

from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


def _wait_for_frame(bus: FrameBus, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bus.get_latest() is not None:
            return
        time.sleep(0.01)
    raise AssertionError("no frame published within timeout")


def test_headless_create_app_root_not_html() -> None:
    """serve_ui=False → GET / is 404 JSON, not Live Preview HTML."""
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    loop.start()
    try:
        _wait_for_frame(bus)
        store = PerceptionStore()
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            perception_store=store,
            serve_ui=False,
        )
        assert app.state.serve_ui is False
        with TestClient(app) as client:
            resp = client.get("/")
            assert resp.status_code == 404
            # Not HTML
            ctype = resp.headers.get("content-type", "")
            assert "html" not in ctype.lower()
            body = resp.text.lower()
            assert "<!doctype html" not in body
            assert "<html" not in body
            data = resp.json()
            detail = data.get("detail", "").lower()
            assert "headless" in detail or "ui disabled" in detail
            assert data.get("v1") == "/v1/snapshot"
    finally:
        loop.stop()


def test_headless_api_status_and_v1_snapshot() -> None:
    """Headless still serves /api/status and /v1/snapshot routes."""
    from sentry_ai.schemas.perception import Detection

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    loop.start()
    try:
        _wait_for_frame(bus)
        store = PerceptionStore()
        store.set_detections(
            frame_id=1,
            camera_id="synthetic0",
            t_capture=time.time(),
            detections=[
                Detection(
                    class_name="person",
                    confidence=0.9,
                    bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
                )
            ],
            latency_ms=5.0,
            conf=0.25,
            model_name="yolo-fixed",
        )
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            perception_store=store,
            serve_ui=False,
        )
        with TestClient(app) as client:
            status = client.get("/api/status")
            assert status.status_code == 200
            assert "status" in status.json()

            snap = client.get("/v1/snapshot")
            # Seeded store → 200 PerceptionFrame; empty would be 404 (existing).
            assert snap.status_code == 200
            body = snap.json()
            assert (
                "schema_version" in body
                or "completeness" in body
                or "frame_id" in body
            )
    finally:
        loop.stop()


def test_serve_ui_true_returns_html_at_root() -> None:
    """Default serve_ui=True still returns Live Preview HTML at GET /."""
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        serve_ui=True,
    )
    assert app.state.serve_ui is True
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        ctype = resp.headers.get("content-type", "")
        assert "html" in ctype.lower()
        text = resp.text.lower()
        assert "html" in text or "sentry" in text


def test_headless_keeps_preview_mjpeg_route() -> None:
    """EDGE-05: MJPEG remains available for debug under headless."""
    bus = FrameBus()
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    loop = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        serve_ui=False,
    )
    # Named routes still resolve (do not consume infinite MJPEG stream).
    assert app.url_path_for("preview_mjpeg") == "/preview/mjpeg"
    assert app.url_path_for("api_status") == "/api/status"
    # /v1/snapshot endpoint name from routes_v1
    snap_path = None
    for name in ("v1_snapshot", "snapshot"):
        try:
            snap_path = app.url_path_for(name)
            break
        except Exception:  # noqa: BLE001
            continue
    if snap_path is None:
        # Fallback: openapi paths list
        schema = app.openapi()
        assert "/v1/snapshot" in schema.get("paths", {})
    else:
        assert snap_path == "/v1/snapshot"
