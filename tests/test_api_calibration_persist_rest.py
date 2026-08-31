"""Persist/save/clear YAML REST tests (helpers in test_api_calibration)."""

from __future__ import annotations

import inspect
from pathlib import Path

from fastapi.testclient import TestClient

from sentry_ai.api import routes_calibration
from sentry_ai.config.calibration_store import load_params
from sentry_ai.control.calibration_persist import try_reapply
from sentry_ai.schemas.calibration import CalibrationFingerprint
from sentry_ai.state.perception_store import PerceptionStore

from tests.test_api_calibration import (
    _app,
    _apply_draft,
    _seed_depth,
)


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
            assert loaded.params.scale == 2.0
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
