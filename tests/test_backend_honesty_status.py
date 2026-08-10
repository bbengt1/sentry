"""Phase 8 BACK-02: backend_requested / backend_live honesty on status."""

from __future__ import annotations

import time

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.capture.status import SourceStatus, StatusSnapshot
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
    return ImageFrame(meta=meta, image_bgr=image)


def _wait_for_frame(bus: FrameBus, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if bus.get_latest() is not None:
            return
        time.sleep(0.01)
    raise AssertionError("no frame published within timeout")


def _running_app(**backend_kwargs: object) -> tuple[CaptureLoop, object]:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    loop.start()
    _wait_for_frame(bus)
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        **backend_kwargs,  # type: ignore[arg-type]
    )
    return loop, app


def test_status_snapshot_backend_fields_optional() -> None:
    """StatusSnapshot accepts optional backend_* with None defaults."""
    snap = StatusSnapshot(
        source="synthetic",
        camera_id="cam0",
        status=SourceStatus.STREAMING,
        capture_fps=0.0,
        frames_dropped=0,
    )
    data = snap.model_dump()
    assert data.get("backend_requested") is None
    assert data.get("backend_live") is None
    assert data.get("backend_reason") is None
    assert data.get("fallback_to_torch") is None

    filled = StatusSnapshot(
        source="synthetic",
        camera_id="cam0",
        status=SourceStatus.STREAMING,
        capture_fps=0.0,
        frames_dropped=0,
        backend_requested="tensorrt",
        backend_live="torch",
        backend_reason="trt_artifact_missing",
        fallback_to_torch=True,
    )
    dumped = filled.model_dump()
    assert dumped["backend_requested"] == "tensorrt"
    assert dumped["backend_live"] == "torch"
    assert dumped["backend_reason"] == "trt_artifact_missing"
    assert dumped["fallback_to_torch"] is True

    strict = StatusSnapshot(
        source="synthetic",
        camera_id="cam0",
        status=SourceStatus.STREAMING,
        capture_fps=0.0,
        frames_dropped=0,
        backend_requested="tensorrt",
        backend_live=None,
        backend_reason="trt_artifact_missing",
        fallback_to_torch=False,
    )
    strict_dump = strict.model_dump()
    assert strict_dump["fallback_to_torch"] is False
    assert strict_dump["backend_live"] is None


def test_api_status_honesty_tensorrt_soft_stub() -> None:
    """TRT preferred soft-stub: requested=tensorrt live=torch + reason."""
    loop, app = _running_app(
        backend_requested="tensorrt",
        backend_live="torch",
        backend_reason="trt_artifact_missing",
        fallback_to_torch=True,
    )
    try:
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["backend_requested"] == "tensorrt"
            assert data["backend_live"] == "torch"
            assert data["backend_reason"] == "trt_artifact_missing"
            assert data["fallback_to_torch"] is True
            # Route must never invent live ORT/TRT
            assert data["backend_live"] not in ("tensorrt", "onnxruntime")
    finally:
        loop.stop()


def test_api_status_honesty_onnxruntime_soft_stub() -> None:
    """ORT preferred soft-stub: requested=onnxruntime live=torch + reason."""
    loop, app = _running_app(
        backend_requested="onnxruntime",
        backend_live="torch",
        backend_reason="ort_artifact_missing",
        fallback_to_torch=True,
    )
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data["backend_requested"] == "onnxruntime"
            assert data["backend_live"] == "torch"
            assert data["backend_reason"] == "ort_artifact_missing"
            assert data["backend_live"] not in ("tensorrt", "onnxruntime")
            assert data["fallback_to_torch"] is True
    finally:
        loop.stop()


def test_api_status_without_backend_injection() -> None:
    """create_app without backend kwargs: fields None/absent, no crash."""
    loop, app = _running_app()
    try:
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data.get("backend_live") is None
            assert data.get("backend_requested") is None
            assert data.get("backend_reason") is None
            # Capture keys still present
            assert "capture_fps" in data
            assert data["bind"] == "127.0.0.1:8000"
    finally:
        loop.stop()


def test_api_status_desktop_gpu_torch_match() -> None:
    """desktop-gpu: requested=torch live=torch, reason optional None."""
    loop, app = _running_app(
        backend_requested="torch",
        backend_live="torch",
        backend_reason=None,
    )
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data["backend_requested"] == "torch"
            assert data["backend_live"] == "torch"
            # reason None may be null or omitted
            assert data.get("backend_reason") is None
    finally:
        loop.stop()


def test_api_status_honesty_onnxruntime_live() -> None:
    """Live ORT: requested=onnxruntime live=onnxruntime reason=None pass-through.

    Status must not recompute live from preferred — factory-authored fields only.
    """
    loop, app = _running_app(
        backend_requested="onnxruntime",
        backend_live="onnxruntime",
        backend_reason=None,
    )
    try:
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["backend_requested"] == "onnxruntime"
            assert data["backend_live"] == "onnxruntime"
            assert data.get("backend_reason") is None
            # Pass-through: live ORT is allowed when factory authored it
            assert data["backend_live"] == data["backend_requested"]
    finally:
        loop.stop()


def test_api_status_honesty_tensorrt_live() -> None:
    """Live TRT: requested=tensorrt live=tensorrt reason=None pass-through.

    Status must not recompute live from preferred — factory-authored fields only.
    """
    loop, app = _running_app(
        backend_requested="tensorrt",
        backend_live="tensorrt",
        backend_reason=None,
    )
    try:
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            data = resp.json()
            assert data["backend_requested"] == "tensorrt"
            assert data["backend_live"] == "tensorrt"
            assert data.get("backend_reason") is None
            # Pass-through: live TRT is allowed when factory authored it
            assert data["backend_live"] == data["backend_requested"]
    finally:
        loop.stop()


def test_status_snapshot_live_ort_fields() -> None:
    """StatusSnapshot accepts live=onnxruntime with reason=None."""
    snap = StatusSnapshot(
        source="synthetic",
        camera_id="cam0",
        status=SourceStatus.STREAMING,
        capture_fps=0.0,
        frames_dropped=0,
        backend_requested="onnxruntime",
        backend_live="onnxruntime",
        backend_reason=None,
    )
    dumped = snap.model_dump()
    assert dumped["backend_requested"] == "onnxruntime"
    assert dumped["backend_live"] == "onnxruntime"
    assert dumped.get("backend_reason") is None


def test_status_snapshot_live_trt_fields() -> None:
    """StatusSnapshot accepts live=tensorrt with reason=None."""
    snap = StatusSnapshot(
        source="synthetic",
        camera_id="cam0",
        status=SourceStatus.STREAMING,
        capture_fps=0.0,
        frames_dropped=0,
        backend_requested="tensorrt",
        backend_live="tensorrt",
        backend_reason=None,
    )
    dumped = snap.model_dump()
    assert dumped["backend_requested"] == "tensorrt"
    assert dumped["backend_live"] == "tensorrt"
    assert dumped.get("backend_reason") is None


def test_create_app_attaches_backend_to_app_state() -> None:
    """create_app kwargs land on app.state (and AppState when mirrored)."""
    bus = FrameBus()
    bus.publish(_make_frame())
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    loop = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        backend_requested="tensorrt",
        backend_live="torch",
        backend_reason="trt_artifact_missing",
        fallback_to_torch=False,
    )
    assert app.state.backend_requested == "tensorrt"
    assert app.state.backend_live == "torch"
    assert app.state.backend_reason == "trt_artifact_missing"
    assert app.state.fallback_to_torch is False
    deps = app.state.deps
    assert getattr(deps, "backend_requested", None) == "tensorrt"
    assert getattr(deps, "backend_live", None) == "torch"
    assert getattr(deps, "backend_reason", None) == "trt_artifact_missing"
    assert getattr(deps, "fallback_to_torch", None) is False


def test_api_status_fallback_to_torch_true_pass_through() -> None:
    """Soft policy flag False must not be dropped by truthiness checks."""
    loop, app = _running_app(
        backend_requested="onnxruntime",
        backend_live="torch",
        backend_reason="ort_artifact_missing",
        fallback_to_torch=True,
    )
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data["fallback_to_torch"] is True
    finally:
        loop.stop()


def test_api_status_fallback_to_torch_false_pass_through() -> None:
    """Strict policy: fallback_to_torch=False survives /api/status pass-through."""
    loop, app = _running_app(
        backend_requested="tensorrt",
        backend_live=None,
        backend_reason="trt_artifact_missing",
        fallback_to_torch=False,
    )
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data["fallback_to_torch"] is False
            assert data["backend_requested"] == "tensorrt"
            assert data.get("backend_live") is None
            assert data["backend_reason"] == "trt_artifact_missing"
    finally:
        loop.stop()


def test_api_status_does_not_recompute_live_from_preferred() -> None:
    """Route source must not import factory or preferred_backend for live."""
    from pathlib import Path

    route_src = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "sentry_ai"
        / "api"
        / "routes_preview.py"
    ).read_text(encoding="utf-8")
    assert "build_detection_worker" not in route_src
    assert "preferred_backend" not in route_src or "Never recompute" in route_src
    # Pass-through only — no inventing live from preferred
    assert "fallback_to_torch" in route_src


def test_live_preview_html_has_backend_metric() -> None:
    """Live Preview footer shows backend requested → live from /api/status."""
    from pathlib import Path

    html_path = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "sentry_ai"
        / "ui"
        / "static"
        / "index.html"
    )
    text = html_path.read_text(encoding="utf-8")
    assert "metric-backend" in text
    assert "backend_requested" in text
    assert "backend_live" in text
    assert "backend_reason" in text
    assert "fallback_to_torch" in text
    # Strict null-live still shows reason
    assert "!live" in text or "showReason" in text
