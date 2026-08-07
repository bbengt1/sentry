"""Detection API routes: GET /api/snapshot + GET/PATCH /api/detection/config."""

from __future__ import annotations

import inspect
import time
from typing import Any

from fastapi.testclient import TestClient

from sentry_ai.api import routes_detection
from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.schemas.perception import Detection
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


class FakeDetectionWorker:
    """Minimal conf-only worker for API tests (no YOLO)."""

    name = "fake-det"

    def __init__(self, conf: float = 0.25) -> None:
        self._conf = conf
        self.weights = "yolo26n.pt"
        self.device = "cpu"

    def set_conf(self, conf: float) -> None:
        value = float(conf)
        if value < 0.0 or value > 1.0:
            raise ValueError(f"conf must be in [0, 1], got {conf!r}")
        self._conf = value

    def get_conf(self) -> float:
        return self._conf

    def process(self, frame: Any) -> list[Detection]:
        _ = frame
        return []


def _app(
    *,
    store: PerceptionStore | None = None,
    worker: FakeDetectionWorker | None = None,
    inject: bool = True,
):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    kwargs: dict[str, Any] = {
        "bus": bus,
        "capture_loop": loop,
        "bind": "127.0.0.1:8000",
    }
    if inject:
        kwargs["perception_store"] = store if store is not None else PerceptionStore()
        kwargs["detection_worker"] = worker if worker is not None else FakeDetectionWorker()
    return create_app(**kwargs), loop


def test_create_app_without_store_worker_still_serves_preview() -> None:
    app, loop = _app(inject=False)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/status")
            assert resp.status_code == 200
            assert "status" in resp.json()
    finally:
        loop.stop()


def test_snapshot_empty_store_returns_404() -> None:
    store = PerceptionStore()
    app, loop = _app(store=store, worker=FakeDetectionWorker())
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 404
            body = resp.json()
            detail = body.get("detail", body)
            assert "detection" in str(detail).lower() or "product" in str(detail).lower()
    finally:
        loop.stop()


def test_snapshot_returns_perception_frame_matching_store() -> None:
    store = PerceptionStore()
    dets = [
        Detection(class_name="person", confidence=0.91, bbox_xyxy=(1, 2, 3, 4)),
        Detection(class_name="cup", confidence=0.55, bbox_xyxy=[10, 20, 30, 40]),
    ]
    store.set_detections(
        frame_id=7,
        camera_id="cam0",
        t_capture=1234.5,
        detections=dets,
        latency_ms=12.3,
        conf=0.25,
        model_name="yolo-fixed",
    )
    app, loop = _app(store=store, worker=FakeDetectionWorker())
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["frame_id"] == 7
            assert data["camera_id"] == "cam0"
            assert data["t_capture"] == 1234.5
            assert data["completeness"]["detections"] is True
            assert data["completeness"]["depth"] is False
            assert data["completeness"]["free_space"] is False
            assert data["detections"] is not None
            assert len(data["detections"]) == 2
            assert data["detections"][0]["class_name"] == "person"
            assert data["detections"][0]["confidence"] == 0.91
            assert list(data["detections"][0]["bbox_xyxy"]) == [1.0, 2.0, 3.0, 4.0]
            # Parity: same content as store product
            product = store.snapshot()
            assert product is not None
            assert len(product.detections) == len(data["detections"])
            assert product.detections[0].class_name == data["detections"][0]["class_name"]
            assert product.detections[1].class_name == data["detections"][1]["class_name"]
            # Stats when available
            stats = data.get("stats") or {}
            assert stats.get("det_latency_ms") == 12.3
            assert stats.get("det_conf") == 0.25
            assert stats.get("det_model") == "yolo-fixed"
            assert data.get("t_publish") is not None
    finally:
        loop.stop()


def test_snapshot_empty_detections_list_still_complete() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=time.time(),
        detections=[],
        latency_ms=5.0,
    )
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["completeness"]["detections"] is True
            assert data["detections"] == []
    finally:
        loop.stop()


def test_patch_detection_config_updates_worker() -> None:
    worker = FakeDetectionWorker(conf=0.25)
    app, loop = _app(worker=worker)
    try:
        with TestClient(app) as client:
            resp = client.patch("/api/detection/config", json={"conf": 0.4})
            assert resp.status_code == 200
            assert resp.json()["conf"] == 0.4
            assert worker.get_conf() == 0.4
            get_resp = client.get("/api/detection/config")
            assert get_resp.status_code == 200
            assert get_resp.json()["conf"] == 0.4
    finally:
        loop.stop()


def test_patch_detection_config_out_of_range_422() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch("/api/detection/config", json={"conf": 1.5})
            assert resp.status_code == 422
            resp2 = client.patch("/api/detection/config", json={"conf": -0.1})
            assert resp2.status_code == 422
    finally:
        loop.stop()


def test_patch_detection_config_extra_fields_422() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/detection/config",
                json={"conf": 0.3, "weights": "evil.pt"},
            )
            assert resp.status_code == 422
    finally:
        loop.stop()


def test_detection_config_missing_worker_503() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        perception_store=store,
        detection_worker=None,
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/detection/config").status_code == 503
            assert (
                client.patch("/api/detection/config", json={"conf": 0.3}).status_code
                == 503
            )
    finally:
        loop.stop()


def test_snapshot_missing_store_503() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        perception_store=None,
        detection_worker=FakeDetectionWorker(),
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/snapshot").status_code == 503
    finally:
        loop.stop()


def test_routes_detection_has_no_videocapture() -> None:
    source = inspect.getsource(routes_detection)
    assert "cv2.VideoCapture" not in source
    assert "VideoCapture(" not in source
    assert "YOLO" not in source
    assert "predict" not in source
