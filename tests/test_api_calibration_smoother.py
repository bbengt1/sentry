"""16-02: apply/clear reset OccupancySmoother; cancel does not."""

from __future__ import annotations

from typing import Any

import numpy as np
from fastapi.testclient import TestClient

from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.sources.synthetic import SyntheticSource
from sentry_ai.state.perception_store import PerceptionStore


class FakeDepthWorker:
    name = "fake-depth"

    def __init__(self) -> None:
        self._depth_mode = "relative"
        self.process_calls = 0

    def get_depth_mode(self) -> str:
        return self._depth_mode

    def set_depth_mode(self, mode: str) -> None:
        self._depth_mode = mode

    def process(self, frame: Any) -> Any:
        self.process_calls += 1
        _ = frame
        raise AssertionError("handlers must never call process")


def test_apply_and_clear_reset_smoother_cancel_does_not() -> None:
    """Belt-and-suspenders: apply/clear call reset_smoother; cancel does not."""
    store = PerceptionStore()
    store.set_depth(
        frame_id=11,
        camera_id="cam0",
        t_capture=1011.0,
        depth_map=np.ones((24, 32), dtype=np.float32) * 2.0,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        model_name="depth-anything-v2-small",
    )
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    worker = FakeDepthWorker()
    app = create_app(
        bus=bus,
        capture_loop=loop,
        bind="127.0.0.1:8000",
        perception_store=store,
        calibration_state=CalibrationState(),
        depth_worker=worker,
    )

    class _FakeFsLoop:
        def __init__(self) -> None:
            self.calls = 0

        def reset_smoother(self) -> None:
            self.calls += 1

    fake = _FakeFsLoop()
    app.state.free_space_loop = fake
    try:
        with TestClient(app) as client:
            sample = client.post(
                "/api/depth/calibration/sample",
                json={"known_meters": 4.0, "point_uv": [8.0, 6.0]},
            )
            assert sample.status_code == 200
            compute = client.post("/api/depth/calibration/compute", json={})
            assert compute.status_code == 200
            assert fake.calls == 0
            assert client.post("/api/depth/calibration/apply").status_code == 200
            assert fake.calls == 1
            assert client.post("/api/depth/calibration/cancel").status_code == 200
            assert fake.calls == 1
            assert client.post("/api/depth/calibration/clear").status_code == 200
            assert fake.calls == 2
            assert worker.process_calls == 0
    finally:
        loop.stop()
