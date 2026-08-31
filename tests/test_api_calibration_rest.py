"""Compute/apply/cancel/clear REST tests (helpers in test_api_calibration)."""

from __future__ import annotations

import time

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.frame import Frame
from sentry_ai.state.perception_store import PerceptionStore

from tests.test_api_calibration import (
    _LoopDepthWorker,
    _app,
    _compute,
    _sample_body,
    _seed_depth,
)


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
