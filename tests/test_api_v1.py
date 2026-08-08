"""API-01 / API-02: GET /v1/snapshot + WS /v1/stream PerceptionFrame."""

from __future__ import annotations

import inspect
from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api import routes_v1
from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection, ObstacleCue
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


def _app(
    *,
    store: PerceptionStore | None = None,
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
        kwargs["perception_store"] = (
            store if store is not None else PerceptionStore()
        )
    return create_app(**kwargs), loop


def _seed_det(store: PerceptionStore, *, frame_id: int = 7) -> None:
    store.set_detections(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=1000.0,
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
            )
        ],
        latency_ms=12.0,
        conf=0.25,
        model_name="yolo-fixed",
    )


def _seed_free_space(store: PerceptionStore, *, frame_id: int = 8) -> None:
    cue = ObstacleCue(
        bbox_xyxy=(10.0, 20.0, 30.0, 40.0),
        nearness_mean=0.8,
        nearness_max=0.95,
        area_px=100,
        band="near",
    )
    store.set_free_space(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=1000.1,
        latency_ms=4.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=[cue],
        bands={"near_frac": 0.15, "mid_frac": 0.25, "far_frac": 0.6},
        free_mask=np.ones((24, 32), dtype=np.uint8),
        occupied_mask=np.zeros((24, 32), dtype=np.uint8),
    )


def test_v1_snapshot_empty_store_returns_404() -> None:
    store = PerceptionStore()
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/snapshot")
            assert resp.status_code == 404
            detail = str(resp.json().get("detail", "")).lower()
            assert "product" in detail or "perception" in detail
    finally:
        loop.stop()


def test_v1_snapshot_without_store_returns_503() -> None:
    app, loop = _app(inject=False)
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/snapshot")
            assert resp.status_code == 503
    finally:
        loop.stop()


def test_v1_snapshot_returns_perception_frame() -> None:
    store = PerceptionStore()
    _seed_det(store)
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["schema_version"] == 1
            assert data["frame_id"] == 7
            assert data["completeness"]["detections"] is True
            assert data["detections"] is not None
            assert "stats" in data
            assert data["stats"] is not None
    finally:
        loop.stop()


def test_v1_snapshot_alias_parity_with_api_snapshot() -> None:
    """GET /api/snapshot body equals GET /v1/snapshot for same store state."""
    store = PerceptionStore()
    _seed_det(store)
    _seed_free_space(store)
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            v1 = client.get("/v1/snapshot")
            api = client.get("/api/snapshot")
            assert v1.status_code == 200
            assert api.status_code == 200
            d1 = v1.json()
            d2 = api.json()
            # Drop t_publish (wall clock between calls) for equality.
            d1.pop("t_publish", None)
            d2.pop("t_publish", None)
            # Ages may drift slightly between sequential calls — strip ages.
            for d in (d1, d2):
                stats = d.get("stats") or {}
                for key in list(stats):
                    if key.endswith("_age_ms") or key.endswith("_stale"):
                        stats.pop(key, None)
                    if key == "products_stale":
                        stats.pop(key, None)
            assert d1 == d2
    finally:
        loop.stop()


def test_v1_stream_yields_json_perception_frame() -> None:
    store = PerceptionStore()
    _seed_det(store)
    _seed_free_space(store)
    app, loop = _app(store=store)
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/v1/stream") as ws:
                msg = ws.receive_json()
                assert msg["schema_version"] == 1
                assert "completeness" in msg
                assert "stats" in msg
                assert msg["stats"] is not None
                assert msg["completeness"]["detections"] is True
                assert msg.get("free_space") is not None
                assert msg["free_space"]["method"] == "near_field_bands"
                # Bulk arrays never on wire
                assert "free_mask" not in (msg.get("free_space") or {})
                assert "depth_map" not in msg
    finally:
        loop.stop()


def test_routes_v1_uses_assembler_only() -> None:
    """Stream/snapshot use assemble_perception_frame; no free-space compute."""
    source = inspect.getsource(routes_v1)
    assert "assemble_perception_frame" in source
    assert "compute_free_space" not in source
    assert "import torch" not in source
    assert "ultralytics" not in source
    assert "send_json" in source or "model_dump" in source


def test_api_snapshot_docstring_mentions_v1_alias() -> None:
    from sentry_ai.api import routes_detection

    source = inspect.getsource(routes_detection.api_snapshot)
    lower = source.lower()
    assert "alias" in lower or "/v1" in source
