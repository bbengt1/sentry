"""UI-03/UI-04: GET/PATCH /api/pipeline/config control plane."""

from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.control.pipeline_state import PipelineState
from sentry_ai.schemas.perception import Detection
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.spatial.free_space import DEFAULT_MID_CUT, DEFAULT_NEAR_CUT
from sentry_ai.state.perception_store import PerceptionStore


class FakeDetectionWorker:
    name = "fake-det"

    def __init__(self, conf: float = 0.25) -> None:
        self._conf = conf
        self.process_calls = 0

    def set_conf(self, conf: float) -> None:
        self._conf = float(conf)

    def get_conf(self) -> float:
        return self._conf

    def process(self, frame: Any) -> list[Detection]:
        self.process_calls += 1
        raise AssertionError("handlers must never call process")


class FakeLoop:
    """Records set_enabled / set_cuts for pipeline PATCH side-effects."""

    def __init__(self) -> None:
        self.enabled = True
        self.enabled_calls: list[bool] = []
        self.near_cut = DEFAULT_NEAR_CUT
        self.mid_cut = DEFAULT_MID_CUT
        self.cut_calls: list[dict[str, float]] = []

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        self.enabled_calls.append(enabled)

    def is_enabled(self) -> bool:
        return self.enabled

    def set_cuts(
        self,
        *,
        near_cut: float | None = None,
        mid_cut: float | None = None,
    ) -> None:
        kwargs: dict[str, float] = {}
        if near_cut is not None:
            kwargs["near_cut"] = float(near_cut)
            self.near_cut = float(near_cut)
        if mid_cut is not None:
            kwargs["mid_cut"] = float(mid_cut)
            self.mid_cut = float(mid_cut)
        if self.near_cut <= self.mid_cut:
            raise ValueError(
                f"near_cut must be > mid_cut "
                f"(got near_cut={self.near_cut}, mid_cut={self.mid_cut})"
            )
        self.cut_calls.append(kwargs)


def _app(
    *,
    pipeline_state: PipelineState | None = None,
    detection_loop: FakeLoop | None = None,
    depth_loop: FakeLoop | None = None,
    free_space_loop: FakeLoop | None = None,
    worker: FakeDetectionWorker | None = None,
    inject_pipeline: bool = True,
):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    store = PerceptionStore()
    kwargs: dict[str, Any] = {
        "bus": bus,
        "capture_loop": loop,
        "bind": "127.0.0.1:8000",
        "perception_store": store,
        "detection_worker": worker if worker is not None else FakeDetectionWorker(),
    }
    if inject_pipeline:
        kwargs["pipeline_state"] = (
            pipeline_state if pipeline_state is not None else PipelineState()
        )
        kwargs["detection_loop"] = detection_loop
        kwargs["depth_loop"] = depth_loop
        kwargs["free_space_loop"] = free_space_loop
    return create_app(**kwargs), loop


def test_get_pipeline_config_defaults() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.get("/api/pipeline/config")
            assert resp.status_code == 200
            data = resp.json()
            assert data["detection_enabled"] is True
            assert data["depth_enabled"] is True
            assert data["free_space_enabled"] is True
            assert data["near_cut"] == DEFAULT_NEAR_CUT
            assert data["mid_cut"] == DEFAULT_MID_CUT
    finally:
        loop.stop()


def test_get_pipeline_config_503_without_state() -> None:
    app, loop = _app(inject_pipeline=False)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/pipeline/config")
            assert resp.status_code == 503
    finally:
        loop.stop()


def test_patch_partial_stage_flags() -> None:
    det = FakeLoop()
    depth = FakeLoop()
    free = FakeLoop()
    state = PipelineState()
    app, loop = _app(
        pipeline_state=state,
        detection_loop=det,
        depth_loop=depth,
        free_space_loop=free,
    )
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/pipeline/config",
                json={"detection_enabled": False},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["detection_enabled"] is False
            assert data["depth_enabled"] is True
            assert data["free_space_enabled"] is True
            assert det.enabled_calls == [False]
            assert depth.enabled_calls == []
            assert free.enabled_calls == []
    finally:
        loop.stop()


def test_patch_all_stages_and_cuts() -> None:
    det = FakeLoop()
    depth = FakeLoop()
    free = FakeLoop()
    app, loop = _app(
        detection_loop=det,
        depth_loop=depth,
        free_space_loop=free,
    )
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/pipeline/config",
                json={
                    "detection_enabled": False,
                    "depth_enabled": False,
                    "free_space_enabled": False,
                    "near_cut": 0.9,
                    "mid_cut": 0.2,
                },
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["detection_enabled"] is False
            assert data["depth_enabled"] is False
            assert data["free_space_enabled"] is False
            assert data["near_cut"] == 0.9
            assert data["mid_cut"] == 0.2
            assert det.enabled_calls == [False]
            assert depth.enabled_calls == [False]
            assert free.enabled_calls == [False]
            assert free.cut_calls
            assert free.near_cut == 0.9
            assert free.mid_cut == 0.2
    finally:
        loop.stop()


def test_patch_invalid_near_le_mid_422() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/pipeline/config",
                json={"near_cut": 0.3, "mid_cut": 0.5},
            )
            assert resp.status_code == 422
            # State unchanged
            get = client.get("/api/pipeline/config").json()
            assert get["near_cut"] == DEFAULT_NEAR_CUT
            assert get["mid_cut"] == DEFAULT_MID_CUT
    finally:
        loop.stop()


def test_patch_out_of_range_cut_422() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/pipeline/config",
                json={"near_cut": 1.5},
            )
            assert resp.status_code == 422
    finally:
        loop.stop()


def test_patch_extra_fields_422() -> None:
    app, loop = _app()
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/pipeline/config",
                json={"detection_enabled": True, "motor_cmd": 1.0},
            )
            assert resp.status_code == 422
    finally:
        loop.stop()


def test_patch_never_calls_worker_process() -> None:
    worker = FakeDetectionWorker()
    app, loop = _app(worker=worker, detection_loop=FakeLoop())
    try:
        with TestClient(app) as client:
            resp = client.patch(
                "/api/pipeline/config",
                json={"detection_enabled": False, "near_cut": 0.8},
            )
            assert resp.status_code == 200
            assert worker.process_calls == 0
    finally:
        loop.stop()


def test_existing_detection_config_still_works() -> None:
    worker = FakeDetectionWorker(conf=0.25)
    app, loop = _app(worker=worker)
    try:
        with TestClient(app) as client:
            resp = client.get("/api/detection/config")
            assert resp.status_code == 200
            assert resp.json()["conf"] == 0.25
            resp = client.patch(
                "/api/detection/config",
                json={"conf": 0.4},
            )
            assert resp.status_code == 200
            assert resp.json()["conf"] == 0.4
            assert worker.process_calls == 0
    finally:
        loop.stop()
