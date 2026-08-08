"""API-05: /v1 snapshot + stream envelopes never carry motor/safety fields."""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection, ObstacleCue
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore

FORBIDDEN_TOP_LEVEL = {
    "cmd",
    "velocity",
    "motor",
    "path_plan",
    "motor_command",
    "twist",
    "cmd_vel",
    "steering",
    "throttle",
    "safe_to_drive",
    "go_nogo",
}

FORBIDDEN_NESTED_FREE_SPACE = {
    "safe",
    "go",
    "safe_to_drive",
    "go_nogo",
    "clear_to_proceed",
    "nogo",
    "cmd",
    "velocity",
    "motor",
    "path_plan",
}


def _app(store: PerceptionStore):
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


def _seed_full(store: PerceptionStore) -> None:
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=100.0,
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
            )
        ],
        latency_ms=10.0,
    )
    depth = np.linspace(0.0, 1.0, 16 * 16, dtype=np.float32).reshape(16, 16)
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=100.0,
        depth_map=depth,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=20.0,
    )
    cue = ObstacleCue(
        bbox_xyxy=(2.0, 2.0, 8.0, 8.0),
        nearness_mean=0.7,
        nearness_max=0.9,
        area_px=36,
        band="near",
    )
    store.set_free_space(
        frame_id=1,
        camera_id="cam0",
        t_capture=100.0,
        latency_ms=3.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=[cue],
        bands={"near_frac": 0.2},
    )


def _assert_perception_only(payload: dict[str, Any]) -> None:
    assert FORBIDDEN_TOP_LEVEL.isdisjoint(payload.keys())
    fs = payload.get("free_space")
    if isinstance(fs, dict):
        assert FORBIDDEN_NESTED_FREE_SPACE.isdisjoint(fs.keys())
        lower_keys = {str(k).lower() for k in fs.keys()}
        for bad in ("safe", "go_nogo", "safe_to_drive", "clear_to_proceed"):
            assert bad not in lower_keys
    stats = payload.get("stats")
    if isinstance(stats, dict):
        assert FORBIDDEN_TOP_LEVEL.isdisjoint(stats.keys())


def test_v1_snapshot_dump_is_perception_only() -> None:
    store = PerceptionStore()
    _seed_full(store)
    app, loop = _app(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/v1/snapshot")
            assert resp.status_code == 200
            _assert_perception_only(resp.json())
    finally:
        loop.stop()


def test_v1_stream_message_is_perception_only() -> None:
    store = PerceptionStore()
    _seed_full(store)
    app, loop = _app(store)
    try:
        with TestClient(app) as client:
            with client.websocket_connect("/v1/stream") as ws:
                msg = ws.receive_json()
                _assert_perception_only(msg)
    finally:
        loop.stop()


def test_api_snapshot_dump_is_perception_only() -> None:
    """Alias path also stays perception-only (same assembler)."""
    store = PerceptionStore()
    _seed_full(store)
    app, loop = _app(store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/snapshot")
            assert resp.status_code == 200
            _assert_perception_only(resp.json())
    finally:
        loop.stop()
