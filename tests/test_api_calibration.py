"""WIZ-01/02/04 + OPS-01 + PER-04: calibration wizard REST (ASGI)."""

from __future__ import annotations

import inspect
import time
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sentry_ai.api import routes_calibration
from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.config.calibration_store import load_params
from sentry_ai.control.calibration_persist import try_reapply
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.models.depth.worker import DepthResult
from sentry_ai.schemas.calibration import CalibrationFingerprint
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.frame import Frame
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


def test_compute_stages_draft_without_promoting_live_kind() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            resp = _compute(client)
            assert resp.status_code == 200
            data = resp.json()
            assert data["has_draft_params"] is True
            assert data["applied"] is False
            assert data["fit"]["ok"] is True
            assert data["fit"]["scale"] == pytest.approx(2.0)
            snap = client.get("/api/snapshot")
            assert snap.json()["depth"]["kind"] == "relative"
            status = client.get("/api/status")
            assert status.status_code == 200
            st = status.json()
            assert st["depth_kind"] == "relative"
            assert st["calibration_active"] is False
            assert st["calibration_sample_count"] == 1
            assert "calibration_scale" not in st
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_rejected_fit_422_no_draft() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            empty = _compute(client)
            assert empty.status_code == 422
            assert state.snapshot().has_draft_params is False
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=1e5),
            )
            absurd = _compute(client)
            assert absurd.status_code == 422
            detail = absurd.json().get("detail", {})
            reason = (
                detail.get("reason")
                if isinstance(detail, dict)
                else str(detail)
            )
            assert "absurd_scale" in str(reason)
            assert state.snapshot().has_draft_params is False
            extra = client.post(
                "/api/depth/calibration/compute",
                json={"fit": "median", "nope": 1},
            )
            assert extra.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_delete_samples_drops_count_and_draft_params() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert _compute(client).status_code == 200
            resp = client.delete("/api/depth/calibration/samples")
            assert resp.status_code == 200
            data = resp.json()
            assert data["draft_sample_count"] == 0
            assert data["has_draft_params"] is False
            assert data["applied"] is False
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_apply_commits_status_but_store_kind_stays_relative() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, state, store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert _compute(client).status_code == 200
            resp = client.post("/api/depth/calibration/apply")
            assert resp.status_code == 200
            data = resp.json()
            assert data["applied"] is True
            assert data["valid"] is True
            assert data["has_draft_params"] is False
            status = client.get("/api/status").json()
            assert status["calibration_active"] is True
            assert status["calibration_scale"] == pytest.approx(2.0)
            assert status["calibration_method"] == "known_distance"
            assert status["calibration_camera_id"] == "cam0"
            assert status["depth_kind"] == "relative"
            snap = client.get("/api/snapshot").json()
            assert snap["depth"]["kind"] == "relative"
            kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
            assert kind == DepthKind.METRIC_CALIBRATED
            assert unit == "m"
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_apply_then_depth_loop_product_is_metric_calibrated() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    state = CalibrationState()
    app, loop, state, store, worker = _app(
        store=store, calibration_state=state
    )
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert _compute(client).status_code == 200
            assert client.post("/api/depth/calibration/apply").status_code == 200
            seeded = store.snapshot_depth()
            assert seeded is not None
            assert seeded.kind == DepthKind.RELATIVE

        loop_worker = _LoopDepthWorker(value=2.0)
        bus = FrameBus()
        depth_loop = DepthLoop(bus, loop_worker, store, calibration=state)
        depth_loop.start()
        try:
            meta = Frame(
                frame_id=99,
                camera_id="cam0",
                t_capture=time.time(),
                t_ingest=time.time(),
                width=32,
                height=24,
            )
            image = np.zeros((24, 32, 3), dtype=np.uint8)
            bus.publish(ImageFrame(meta=meta, image_bgr=image))
            deadline = time.monotonic() + 2.0
            product = None
            while time.monotonic() < deadline:
                product = store.snapshot_depth()
                if product is not None and product.frame_id == 99:
                    break
                time.sleep(0.01)
            assert product is not None
            assert product.frame_id == 99
            assert product.kind == DepthKind.METRIC_CALIBRATED
            assert product.unit == "m"
        finally:
            depth_loop.stop()
        assert worker.process_calls == 0
    finally:
        loop.stop()


def test_cancel_after_compute_drops_draft_not_applied() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert _compute(client).status_code == 200
            resp = client.post("/api/depth/calibration/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["has_draft_params"] is False
            assert data["applied"] is False
            assert data["draft_sample_count"] == 0
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_cancel_after_apply_leaves_applied() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert _compute(client).status_code == 200
            assert client.post("/api/depth/calibration/apply").status_code == 200
            resp = client.post("/api/depth/calibration/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["applied"] is True
            status = client.get("/api/status").json()
            assert status["calibration_active"] is True
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_clear_after_apply_drops_applied() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            client.post(
                "/api/depth/calibration/sample",
                json=_sample_body(known_meters=4.0),
            )
            assert _compute(client).status_code == 200
            assert client.post("/api/depth/calibration/apply").status_code == 200
            resp = client.post("/api/depth/calibration/clear")
            assert resp.status_code == 200
            data = resp.json()
            assert data["applied"] is False
            status = client.get("/api/status").json()
            assert status["calibration_active"] is False
            assert "calibration_scale" not in status
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_status_inactive_when_injected() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data["calibration_active"] is False
            assert data["calibration_sample_count"] == 0
            assert "calibration_scale" not in data
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_apply_without_draft_422() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.post("/api/depth/calibration/apply")
            assert resp.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_handlers_never_call_process_or_open_cameras() -> None:
    source = inspect.getsource(routes_calibration)
    assert "worker.process" not in source
    assert "VideoCapture" not in source
    assert ".process(" not in source
    assert "apply_map" not in source


def test_apply_without_persist_writes_nothing(tmp_path: Path) -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    dest = tmp_path / "cam0.yaml"
    app, loop, _state, _store, worker = _app(
        store=store, calibration_path=dest
    )
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            resp = client.post("/api/depth/calibration/apply")
            assert resp.status_code == 200
            assert resp.json()["applied"] is True
            assert not dest.exists()
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_apply_persist_true_writes_yaml(tmp_path: Path) -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    dest = tmp_path / "cam0.yaml"
    app, loop, _state, _store, worker = _app(
        store=store, calibration_path=dest
    )
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            resp = client.post(
                "/api/depth/calibration/apply",
                json={"persist": True},
            )
            assert resp.status_code == 200
            assert resp.json()["applied"] is True
            assert dest.is_file()
            loaded = load_params(dest)
            assert loaded.status == "ok"
            assert loaded.params is not None
            assert loaded.params.scale == pytest.approx(2.0)
            extra = client.post(
                "/api/depth/calibration/apply",
                json={"persist": True, "motor": 1},
            )
            assert extra.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_save_after_apply_writes_yaml(tmp_path: Path) -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    dest = tmp_path / "cam0.yaml"
    app, loop, _state, _store, worker = _app(
        store=store, calibration_path=dest
    )
    try:
        with TestClient(app) as client:
            missing = client.post("/api/depth/calibration/save")
            assert missing.status_code == 422
            _apply_draft(client)
            assert client.post("/api/depth/calibration/apply").status_code == 200
            assert not dest.exists()
            resp = client.post("/api/depth/calibration/save")
            assert resp.status_code == 200
            assert dest.is_file()
            loaded = load_params(dest)
            assert loaded.status == "ok"
            extra = client.post(
                "/api/depth/calibration/save",
                json={"nope": 1},
            )
            assert extra.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_clear_deletes_file_so_reapply_is_none(tmp_path: Path) -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    dest = tmp_path / "cam0.yaml"
    app, loop, state, _store, worker = _app(
        store=store, calibration_path=dest
    )
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            assert (
                client.post(
                    "/api/depth/calibration/apply",
                    json={"persist": True},
                ).status_code
                == 200
            )
            assert dest.is_file()
            resp = client.post("/api/depth/calibration/clear")
            assert resp.status_code == 200
            assert resp.json()["applied"] is False
            assert not dest.exists()
            live = CalibrationFingerprint(camera_id="cam0")
            result = try_reapply(state, dest, live)
            assert result.status == "none"
            assert state.is_applied() is False
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_cancel_does_not_delete_saved_file(tmp_path: Path) -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    dest = tmp_path / "cam0.yaml"
    app, loop, _state, _store, worker = _app(
        store=store, calibration_path=dest
    )
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            assert (
                client.post(
                    "/api/depth/calibration/apply",
                    json={"persist": True},
                ).status_code
                == 200
            )
            assert dest.is_file()
            resp = client.post("/api/depth/calibration/cancel")
            assert resp.status_code == 200
            assert resp.json()["applied"] is True
            assert dest.is_file()
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_status_persist_fields_separate_from_depth_kind() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert data["calibration_persist"] == "none"
            assert "calibration_persist_reason" not in data
            assert data["depth_kind"] == "relative"
            state.set_persist_status("ignored_mismatch", "resolution")
            data = client.get("/api/status").json()
            assert data["calibration_persist"] == "ignored_mismatch"
            assert data["calibration_persist_reason"] == "resolution"
            assert data["depth_kind"] == "relative"
            assert data["depth_kind"] != "metric_calibrated"
            assert data["calibration_active"] is False
            assert worker.process_calls == 0
    finally:
        loop.stop()
