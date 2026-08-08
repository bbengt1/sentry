"""DEPTH-04 honesty: relative never meters on wire; metric labeled clearly."""

from __future__ import annotations

import json

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


def _client_with_store(store: PerceptionStore):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        perception_store=store,
    )
    return app, loop


def test_relative_snapshot_unit_null_no_depth_m_key() -> None:
    store = PerceptionStore()
    depth = np.linspace(0.0, 1.0, 16 * 16, dtype=np.float32).reshape(16, 16)
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        depth_map=depth,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=5.0,
    )
    app, loop = _client_with_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["depth"]["kind"] == "relative"
            assert data["depth"]["unit"] is None
            # No depth_m key anywhere in the JSON tree.
            dumped = json.dumps(data)
            assert "depth_m" not in dumped
            # Nested keys must not include depth_m
            assert "depth_m" not in data
            assert "depth_m" not in (data.get("depth") or {})
            assert "depth_m" not in (data.get("stats") or {})
    finally:
        loop.stop()


def test_metric_snapshot_kind_and_unit_m() -> None:
    store = PerceptionStore()
    depth = np.linspace(0.5, 3.0, 16 * 16, dtype=np.float32).reshape(16, 16)
    store.set_depth(
        frame_id=2,
        camera_id="cam0",
        t_capture=2.0,
        depth_map=depth,
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
        latency_ms=8.0,
    )
    app, loop = _client_with_store(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            data = resp.json()
            assert data["depth"]["kind"] == "metric_estimated"
            assert data["depth"]["unit"] == "m"
            assert "depth_m" not in json.dumps(data)
    finally:
        loop.stop()
