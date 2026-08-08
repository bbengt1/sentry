"""DEPTH-02/04 API: snapshot DepthPayload + depth config routes."""

from __future__ import annotations

import json
import time
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


class FakeDepthWorker:
    """Minimal depth_mode worker for API tests (no HF)."""

    name = "fake-depth"

    def __init__(self, depth_mode: str = "relative") -> None:
        self._depth_mode = depth_mode
        self.model_id = "depth-anything/Depth-Anything-V2-Small-hf"
        self.device = "cpu"

    def get_depth_mode(self) -> str:
        return self._depth_mode

    def set_depth_mode(self, mode: str) -> None:
        if mode not in ("relative", "metric_indoor", "metric_outdoor"):
            raise ValueError(f"unknown depth_mode: {mode!r}")
        self._depth_mode = mode

    def process(self, frame: Any) -> Any:
        _ = frame
        raise AssertionError("handlers must never call process")


def _app(
    *,
    store: PerceptionStore | None = None,
    depth_worker: FakeDepthWorker | None = None,
    inject_depth: bool = True,
    inject_store: bool = True,
):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    kwargs: dict[str, Any] = {
        "bus": bus,
        "capture_loop": loop,
        "bind": "127.0.0.1:8000",
    }
    if inject_store:
        kwargs["perception_store"] = (
            store if store is not None else PerceptionStore()
        )
    if inject_depth:
        kwargs["depth_worker"] = (
            depth_worker if depth_worker is not None else FakeDepthWorker()
        )
    return create_app(**kwargs), loop


def _seed_depth(
    store: PerceptionStore,
    *,
    kind: DepthKind = DepthKind.RELATIVE,
    unit: str | None = None,
    frame_id: int = 11,
    error: str | None = None,
    depth_map: np.ndarray | None = None,
) -> None:
    if depth_map is None and error is None:
        depth_map = np.linspace(0.1, 2.0, 24 * 32, dtype=np.float32).reshape(24, 32)
    store.set_depth(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=1000.0 + frame_id,
        depth_map=depth_map,
        kind=kind,
        unit=unit,  # type: ignore[arg-type]
        latency_ms=42.5,
        model_name="depth-anything-v2-small",
        error=error,
    )


def test_snapshot_neither_product_returns_404() -> None:
    store = PerceptionStore()
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 404
            detail = str(resp.json().get("detail", "")).lower()
            assert "product" in detail
    finally:
        loop.stop()


def test_snapshot_depth_only_200_completeness() -> None:
    store = PerceptionStore()
    _seed_depth(store, kind=DepthKind.RELATIVE, unit=None)
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["completeness"]["depth"] is True
            assert data["completeness"]["detections"] is False
            assert data["completeness"]["free_space"] is False
            assert data["depth"] is not None
            assert data["depth"]["kind"] == "relative"
            assert data["depth"]["unit"] is None
            assert data["depth"]["width"] == 32
            assert data["depth"]["height"] == 24
            assert data["detections"] is None or data["detections"] == []
            stats = data.get("stats") or {}
            assert stats.get("depth_latency_ms") == 42.5
            assert "depth_min" in stats
            assert "depth_max" in stats
            assert "depth_mean" in stats
            assert stats.get("depth_frame_id") == 11
            assert stats.get("depth_model") == "depth-anything-v2-small"
            # Body size sanity: no full depth_map array
            raw = resp.content
            assert len(raw) < 50_000
            assert "depth_map" not in data
            assert "depth_m" not in json.dumps(data)
    finally:
        loop.stop()


def test_snapshot_det_and_depth_both_complete() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=7,
        camera_id="cam0",
        t_capture=1234.5,
        detections=[
            Detection(class_name="person", confidence=0.9, bbox_xyxy=(1, 2, 3, 4))
        ],
        latency_ms=12.3,
        conf=0.25,
        model_name="yolo-fixed",
    )
    _seed_depth(store, kind=DepthKind.RELATIVE, unit=None, frame_id=8)
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["completeness"]["detections"] is True
            assert data["completeness"]["depth"] is True
            assert len(data["detections"]) == 1
            assert data["depth"]["kind"] == "relative"
            stats = data["stats"]
            assert stats["det_latency_ms"] == 12.3
            assert stats["depth_latency_ms"] == 42.5
            assert stats["det_frame_id"] == 7
            assert stats["depth_frame_id"] == 8
    finally:
        loop.stop()


def test_snapshot_metric_depth_payload() -> None:
    store = PerceptionStore()
    _seed_depth(
        store,
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
    )
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["depth"]["kind"] == "metric_estimated"
            assert data["depth"]["unit"] == "m"
    finally:
        loop.stop()


def test_snapshot_depth_with_error_not_complete() -> None:
    store = PerceptionStore()
    _seed_depth(
        store,
        kind=DepthKind.RELATIVE,
        unit=None,
        error="boom",
        depth_map=None,
    )
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            # Product exists but error → completeness.depth false; still 200
            # (product present so not 404 for depth-only error case).
            assert resp.status_code == 200
            data = resp.json()
            assert data["completeness"]["depth"] is False
            assert data["depth"] is None
    finally:
        loop.stop()


def test_get_depth_config() -> None:
    worker = FakeDepthWorker(depth_mode="relative")
    app, loop = _app(depth_worker=worker)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/depth/config")
            assert resp.status_code == 200
            data = resp.json()
            assert data["depth_mode"] == "relative"
            assert "model" in data or "model_id" in data
    finally:
        loop.stop()


def test_patch_depth_config_updates_mode() -> None:
    worker = FakeDepthWorker(depth_mode="relative")
    app, loop = _app(depth_worker=worker)
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/depth/config",
                json={"depth_mode": "metric_indoor"},
            )
            assert resp.status_code == 200
            assert resp.json()["depth_mode"] == "metric_indoor"
            assert worker.get_depth_mode() == "metric_indoor"
    finally:
        loop.stop()


def test_patch_depth_config_invalid_mode_422() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/depth/config",
                json={"depth_mode": "not_a_mode"},
            )
            assert resp.status_code == 422
            resp2 = client.patch(
                "/api/depth/config",
                json={"depth_mode": "relative", "extra": 1},
            )
            assert resp2.status_code == 422
    finally:
        loop.stop()


def test_depth_config_missing_worker_503() -> None:
    store = PerceptionStore()
    app, loop = _app(store=store, inject_depth=False)
    # create_app without depth_worker
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop2 = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=loop2,
        bind="127.0.0.1:8000",
        perception_store=store,
        depth_worker=None,
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/depth/config").status_code == 503
            assert (
                client.patch(
                    "/api/depth/config",
                    json={"depth_mode": "relative"},
                ).status_code
                == 503
            )
    finally:
        loop.stop()
        loop2.stop()


def test_create_app_without_depth_worker_still_serves() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
    try:
        with TestClient(app) as client:
            assert client.get("/api/status").status_code == 200
    finally:
        loop.stop()


def test_snapshot_no_giant_arrays() -> None:
    store = PerceptionStore()
    big = np.random.rand(480, 640).astype(np.float32)
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=time.time(),
        depth_map=big,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=10.0,
    )
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            # Full 480x640 float would be hundreds of KB as JSON.
            assert len(resp.content) < 20_000
            text = resp.text
            assert "depth_map" not in text
    finally:
        loop.stop()
