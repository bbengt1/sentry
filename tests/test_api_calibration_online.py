"""ONL-01 / ONL-06: REST online toggle + status plane."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
)
from sentry_ai.state.perception_store import PerceptionStore
from tests.test_api_calibration import (
    _app,
    _apply_draft,
    _seed_depth,
)


def test_online_post_unapplied_is_409() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/depth/calibration/online",
                json={"enabled": True},
            )
            assert resp.status_code == 409
            detail = resp.json().get("detail", "")
            assert "online_requires_applied" in str(detail)
            data = client.get("/api/depth/calibration").json()
            assert data["online"] is False
            assert data["online_status"] == "online_off"
            assert data["applied"] is False
            assert state.is_applied() is False
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_online_post_enable_after_apply() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            applied = client.post("/api/depth/calibration/apply")
            assert applied.status_code == 200
            scale = applied.json()["scale"]
            resp = client.post(
                "/api/depth/calibration/online",
                json={"enabled": True},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["online"] is True
            assert data["online_status"] == "online_draft"
            assert data["applied"] is True
            assert data["scale"] == scale
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_online_post_disable_leaves_applied() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            assert client.post("/api/depth/calibration/apply").status_code == 200
            assert (
                client.post(
                    "/api/depth/calibration/online",
                    json={"enabled": True},
                ).status_code
                == 200
            )
            resp = client.post(
                "/api/depth/calibration/online",
                json={"enabled": False},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["online"] is False
            assert data["online_status"] == "online_off"
            got = client.get("/api/depth/calibration").json()
            assert got["applied"] is True
            assert got["online"] is False
            assert got["online_status"] == "online_off"
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_cancel_after_online_leaves_applied_and_online() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=2.0)
    app, loop, state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            _apply_draft(client)
            assert client.post("/api/depth/calibration/apply").status_code == 200
            assert (
                client.post(
                    "/api/depth/calibration/online",
                    json={"enabled": True},
                ).status_code
                == 200
            )
            state.set_draft_params(
                CalibrationParams(
                    scale=3.0,
                    sample_count=2,
                    fingerprint=CalibrationFingerprint(camera_id="cam0"),
                )
            )
            assert state.snapshot().has_draft_params is True
            resp = client.post("/api/depth/calibration/cancel")
            assert resp.status_code == 200
            data = resp.json()
            assert data["has_draft_params"] is False
            assert data["applied"] is True
            assert data["online"] is True
            assert data["online_status"] == "online_draft"
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_clear_after_online_drops_applied_and_yaml(tmp_path: Path) -> None:
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
            assert (
                client.post(
                    "/api/depth/calibration/online",
                    json={"enabled": True},
                ).status_code
                == 200
            )
            resp = client.post("/api/depth/calibration/clear")
            assert resp.status_code == 200
            data = resp.json()
            assert data["applied"] is False
            assert data["online"] is False
            assert data["online_status"] == "online_off"
            assert not dest.exists()
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_online_post_rejects_extra_and_missing_enabled() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            extra = client.post(
                "/api/depth/calibration/online",
                json={"enabled": True, "motor": 1},
            )
            assert extra.status_code == 422
            missing = client.post(
                "/api/depth/calibration/online",
                json={},
            )
            assert missing.status_code == 422
            empty = client.post("/api/depth/calibration/online")
            assert empty.status_code == 422
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_status_online_plane_distinct_from_kind_and_persist() -> None:
    store = PerceptionStore()
    _seed_depth(store)
    app, loop, _state, _store, worker = _app(store=store)
    try:
        with TestClient(app) as client:
            data = client.get("/api/status").json()
            assert "calibration_online" in data
            assert "calibration_online_status" in data
            assert data["calibration_online"] is False
            assert data["calibration_online_status"] == "online_off"
            assert data["depth_kind"] == "relative"
            assert data["calibration_persist"] == "none"
            assert data["calibration_online_status"] != data["depth_kind"]
            assert (
                data["calibration_online_status"]
                != data["calibration_persist"]
            )
            _apply_draft(client)
            assert client.post("/api/depth/calibration/apply").status_code == 200
            assert (
                client.post(
                    "/api/depth/calibration/online",
                    json={"enabled": True},
                ).status_code
                == 200
            )
            data = client.get("/api/status").json()
            assert data["calibration_online"] is True
            assert data["calibration_online_status"] == "online_draft"
            assert data["depth_kind"] == "relative"
            assert data["calibration_persist"] == "none"
            assert data["calibration_online_status"] != data["depth_kind"]
            assert (
                data["calibration_online_status"]
                != data["calibration_persist"]
            )
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_disable_online_rest_does_not_delete_yaml(tmp_path: Path) -> None:
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
            assert (
                client.post(
                    "/api/depth/calibration/online",
                    json={"enabled": True},
                ).status_code
                == 200
            )
            resp = client.post(
                "/api/depth/calibration/online",
                json={"enabled": False},
            )
            assert resp.status_code == 200
            assert dest.is_file()
            assert resp.json()["applied"] is True
            assert resp.json()["online"] is False
            assert resp.json()["online_status"] == "online_off"
            assert worker.process_calls == 0
    finally:
        loop.stop()
