"""WIZ-01/02/04 + OPS-01 + PER-04: calibration wizard REST (ASGI)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.models.depth.worker import DepthResult
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


class FakeDepthWorker:
    """Minimal depth worker for API tests (no HF). process must never run."""

    name = "fake-depth"

    def __init__(self, depth_mode: str = "relative") -> None:
        self._depth_mode = depth_mode
        self.model_id = "depth-anything/Depth-Anything-V2-Small-hf"
        self.device = "cpu"
        self.process_calls = 0

    def get_depth_mode(self) -> str:
        return self._depth_mode

    def set_depth_mode(self, mode: str) -> None:
        self._depth_mode = mode

    def process(self, frame: Any) -> Any:
        self.process_calls += 1
        _ = frame
        raise AssertionError("handlers must never call process")


class _LoopDepthWorker:
    """Processing worker for DepthLoop tick after apply (not used by REST)."""

    name = "loop-depth"
    model_id = "depth-anything/Depth-Anything-V2-Small-hf"

    def __init__(self, value: float = 2.0) -> None:
        self._value = value
        self.process_calls = 0

    def get_depth_mode(self) -> str:
        return "relative"

    def process(self, frame: Any) -> DepthResult:
        self.process_calls += 1
        image = getattr(frame, "image_bgr", None)
        if image is None:
            h, w = 24, 32
        else:
            h, w = int(image.shape[0]), int(image.shape[1])
        return DepthResult(
            depth_map=np.full((h, w), self._value, dtype=np.float32),
            kind=DepthKind.RELATIVE,
            unit=None,
            width=w,
            height=h,
        )


def _app(
    *,
    store: PerceptionStore | None = None,
    calibration_state: CalibrationState | None = None,
    depth_worker: FakeDepthWorker | None = None,
    inject_calibration: bool = True,
    inject_store: bool = True,
    inject_depth: bool = True,
    calibration_path: Path | str | None = None,
):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    if store is None:
        store = PerceptionStore()
    if calibration_state is None:
        calibration_state = CalibrationState()
    if depth_worker is None:
        depth_worker = FakeDepthWorker()
    kwargs: dict[str, Any] = {
        "bus": bus,
        "capture_loop": loop,
        "bind": "127.0.0.1:8000",
    }
    if inject_store:
        kwargs["perception_store"] = store
    if inject_calibration:
        kwargs["calibration_state"] = calibration_state
    if inject_depth:
        kwargs["depth_worker"] = depth_worker
    if calibration_path is not None:
        kwargs["calibration_path"] = calibration_path
    return create_app(**kwargs), loop, calibration_state, store, depth_worker


def _seed_depth(
    store: PerceptionStore,
    *,
    value: float = 2.0,
    kind: DepthKind = DepthKind.RELATIVE,
    unit: str | None = None,
    frame_id: int = 11,
    error: str | None = None,
    depth_map: np.ndarray | None = None,
) -> None:
    if depth_map is None and error is None:
        depth_map = np.ones((24, 32), dtype=np.float32) * float(value)
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


def _sample_body(
    *,
    known_meters: float = 4.0,
    point_uv: tuple[float, float] | None = (8.0, 6.0),
    bbox_xyxy: tuple[float, float, float, float] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {}
    if known_meters is not None:
        body["known_meters"] = known_meters
    if point_uv is not None:
        body["point_uv"] = list(point_uv)
    if bbox_xyxy is not None:
        body["bbox_xyxy"] = list(bbox_xyxy)
    return body


def _compute(client: TestClient):
    return client.post("/api/depth/calibration/compute", json={})


def _apply_draft(client: TestClient) -> None:
    assert (
        client.post(
            "/api/depth/calibration/sample",
            json=_sample_body(known_meters=4.0),
        ).status_code
        == 200
    )
    assert _compute(client).status_code == 200


def test_missing_calibration_state_503() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(
        store=store, inject_calibration=False
    )
    try:
        with TestClient(app) as client:
            assert client.get("/api/depth/calibration").status_code == 503
            assert client.post("/api/depth/calibration/freeze").status_code == 503
            assert (
                client.post(
                    "/api/depth/calibration/sample",
                    json=_sample_body(),
                ).status_code
                == 503
            )
            assert (
                client.delete("/api/depth/calibration/samples").status_code == 503
            )
            assert _compute(client).status_code == 503
            assert client.post("/api/depth/calibration/apply").status_code == 503
            assert client.post("/api/depth/calibration/save").status_code == 503
            assert client.post("/api/depth/calibration/cancel").status_code == 503
            assert client.post("/api/depth/calibration/clear").status_code == 503
            assert (
                client.post(
                    "/api/depth/calibration/online",
                    json={"enabled": True},
                ).status_code
                == 503
            )
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_get_snapshot_includes_fields_and_frozen() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/depth/calibration")
            assert resp.status_code == 200
            data = resp.json()
            assert data["applied"] is False
            assert data["valid"] is False
            assert data["draft_sample_count"] == 0
            assert data["has_draft_params"] is False
            assert data["samples"] == []
            assert data["frozen"] is False
            assert data["online"] is False
            assert data["online_status"] == "online_off"
            assert "depth_map" not in resp.text
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_freeze_pins_frame_for_later_sample() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0, frame_id=11)
    app, loop, _state, store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            freeze = client.post("/api/depth/calibration/freeze")
            assert freeze.status_code == 200
            assert freeze.json()["frozen"] is True
            _seed_depth(store, value=9.0, frame_id=12)
            resp = client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["draft_sample_count"] == 1
            observed = data["sample"]["observed_raw"]
            assert observed == pytest.approx(2.0)
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_freeze_missing_depth_422() -> None:
    store = PerceptionStore()
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.post("/api/depth/calibration/freeze")
            assert resp.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_sample_point_fills_observed_raw() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0, point_uv=(8.0, 6.0)),
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["draft_sample_count"] == 1
            assert data["applied"] is False
            assert data["sample"]["observed_raw"] == pytest.approx(2.0)
            assert data["samples"][0]["known_meters"] == 4.0
            assert "depth_map" not in resp.text
            snap = client.get("/api/snapshot")
            assert snap.status_code == 200
            assert snap.json()["depth"]["kind"] == "relative"
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_sample_bbox_fills_observed_raw() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/depth/calibration/sample",
                json={
                    "bbox_xyxy": [2.0, 2.0, 10.0, 10.0],
                    "known_meters": 4.0,
                },
            )
            assert resp.status_code == 200
            assert resp.json()["sample"]["observed_raw"] == pytest.approx(2.0)
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_sample_neither_point_nor_bbox_422() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/depth/calibration/sample",
                json={"known_meters": 4.0},
            )
            assert resp.status_code == 422
            extra = client.post(
                "/api/depth/calibration/sample",
                json={
                    "point_uv": [8.0, 6.0],
                    "known_meters": 4.0,
                    "motor": 1,
                },
            )
            assert extra.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_sample_while_applied_409() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            assert (
                client.post(
                    "/api/depth/calibration/sample",
                    json=_sample_body(known_meters=4.0),
                ).status_code
                == 200
            )
            compute = _compute(client)
            assert compute.status_code == 200
            apply = client.post("/api/depth/calibration/apply")
            assert apply.status_code == 200
            assert apply.json()["applied"] is True
            before = client.get("/api/depth/calibration").json()
            count = before["draft_sample_count"]
            resp = client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert resp.status_code == 409
            detail = resp.json().get("detail", "")
            assert "calibration_already_applied" in str(detail)
            after = client.get("/api/depth/calibration").json()
            assert after["draft_sample_count"] == count
            assert after["applied"] is True
            assert state.is_applied() is True
            assert worker.process_calls == 0
    finally:
        loop.stop()
