"""CAL-03 / WIZ-01: same CalibrationState into DepthLoop and create_app."""

from __future__ import annotations

import inspect

from sentry_ai import cli as cli_mod
from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.sources.synthetic import SyntheticSource


def test_serve_injects_calibration_state_into_depth_loop() -> None:
    source = inspect.getsource(cli_mod.serve)
    assert "CalibrationState" in source
    assert "calibration_state = CalibrationState()" in source
    assert "calibration=calibration_state" in source
    ctor = "DepthLoop(bus, depth_worker, store, calibration=calibration_state)"
    assert ctor in source


def test_serve_injects_same_calibration_state_into_create_app() -> None:
    source = inspect.getsource(cli_mod.serve)
    assert "calibration_state=calibration_state" in source
    # Hoisted before depth extra import so missing extra still injects.
    idx_ctor = source.index("calibration_state = CalibrationState()")
    idx_depth_worker = source.index("DepthAnythingWorker")
    idx_create = source.index("calibration_state=calibration_state")
    assert idx_ctor < idx_depth_worker
    assert idx_ctor < idx_create


def test_create_app_calibration_state_identity() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    state = CalibrationState()
    try:
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            calibration_state=state,
        )
        assert app.state.calibration_state is state
        assert app.state.deps.calibration_state is state
    finally:
        loop.stop()


def test_create_app_without_calibration_state_is_none() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    try:
        app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
        assert getattr(app.state, "calibration_state", None) is None
        assert app.state.deps.calibration_state is None
    finally:
        loop.stop()
