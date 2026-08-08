"""OVD-01/02 open-vocab API: config + run (no inference on request path)."""

from __future__ import annotations

import inspect
from typing import Any

from fastapi.testclient import TestClient

from sentry_ai.api import routes_open_vocab
from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.models.detection.open_vocab_loop import OpenVocabLoop
from sentry_ai.schemas.perception import Detection
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


class FakeOvWorker:
    name = "fake-ov"

    def __init__(self, conf: float = 0.25) -> None:
        self._conf = conf
        self._classes: list[str] = []
        self.process_calls = 0

    def set_conf(self, conf: float) -> None:
        value = float(conf)
        if value < 0.0 or value > 1.0:
            raise ValueError(f"conf must be in [0, 1], got {conf!r}")
        self._conf = value

    def get_conf(self) -> float:
        return self._conf

    def set_prompt_classes(self, classes: list[str]) -> None:
        self._classes = [str(c).strip() for c in classes if str(c).strip()]

    def get_prompt_classes(self) -> list[str]:
        return list(self._classes)

    def process(self, frame: Any) -> list[Detection]:
        self.process_calls += 1
        raise AssertionError("handlers must never call process")


def _app(
    *,
    store: PerceptionStore | None = None,
    worker: FakeOvWorker | None = None,
    inject: bool = True,
    with_loop: bool = True,
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
        store = store if store is not None else PerceptionStore()
        worker = worker if worker is not None else FakeOvWorker()
        kwargs["perception_store"] = store
        kwargs["open_vocab_worker"] = worker
        if with_loop:
            ov_loop = OpenVocabLoop(bus, worker, store)
            kwargs["open_vocab_loop"] = ov_loop
    return create_app(**kwargs), loop, kwargs.get("open_vocab_loop"), kwargs.get(
        "open_vocab_worker"
    )


def test_get_config_503_without_worker() -> None:
    app, cap_loop, _, _ = _app(inject=False)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/open-vocab/config")
            assert resp.status_code == 503
    finally:
        cap_loop.stop()


def test_get_patch_config_roundtrip() -> None:
    app, cap_loop, ov_loop, worker = _app()
    try:
        with TestClient(app) as client:
            resp = client.get("/api/open-vocab/config")
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "off"
            assert data["classes"] == []
            assert data["conf"] == 0.25
            assert data["every_n"] == 3

            resp = client.patch(
                "/api/open-vocab/config",
                json={
                    "prompt": "person, red cup",
                    "mode": "continuous",
                    "conf": 0.4,
                    "every_n": 5,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["mode"] == "continuous"
            assert data["classes"] == ["person", "red cup"]
            assert data["conf"] == 0.4
            assert data["every_n"] == 5
            assert worker.get_prompt_classes() == ["person", "red cup"]
            assert ov_loop.get_mode() == "continuous"
            assert worker.process_calls == 0  # no inference on handler
    finally:
        if ov_loop is not None:
            ov_loop.stop()
        cap_loop.stop()


def test_post_run_arms_without_process() -> None:
    app, cap_loop, ov_loop, worker = _app()
    try:
        with TestClient(app) as client:
            resp = client.post(
                "/api/open-vocab/run",
                json={"prompt": "toolbox, person"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["armed"] is True
            assert data["mode"] == "on_demand"
            assert data["classes"] == ["toolbox", "person"]
            assert worker.process_calls == 0
            assert ov_loop.is_armed() is True
    finally:
        if ov_loop is not None:
            ov_loop.stop()
        cap_loop.stop()


def test_prompt_class_count_cap_422() -> None:
    app, cap_loop, ov_loop, _ = _app()
    try:
        with TestClient(app) as client:
            too_many = ", ".join(f"c{i}" for i in range(33))
            resp = client.patch(
                "/api/open-vocab/config",
                json={"prompt": too_many},
            )
            assert resp.status_code == 422
    finally:
        if ov_loop is not None:
            ov_loop.stop()
        cap_loop.stop()


def test_prompt_class_length_cap_422() -> None:
    app, cap_loop, ov_loop, _ = _app()
    try:
        with TestClient(app) as client:
            long_name = "x" * 65
            resp = client.post(
                "/api/open-vocab/run",
                json={"classes": [long_name]},
            )
            assert resp.status_code == 422
    finally:
        if ov_loop is not None:
            ov_loop.stop()
        cap_loop.stop()


def test_extra_fields_rejected() -> None:
    app, cap_loop, ov_loop, _ = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/open-vocab/config",
                json={"prompt": "a", "motor": 1},
            )
            assert resp.status_code == 422
    finally:
        if ov_loop is not None:
            ov_loop.stop()
        cap_loop.stop()


def test_handlers_never_call_process_in_source() -> None:
    source = inspect.getsource(routes_open_vocab)
    # No actual process invocation on request path (docstring may mention it).
    assert ".process(" not in source
    assert "process(frame" not in source
