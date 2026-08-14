"""CAL-03 / WIZ-01 / PER-02: same CalibrationState + serve re-apply wiring."""

from __future__ import annotations

import inspect
from pathlib import Path

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


def test_serve_calls_try_reapply_banner_and_calibration_file() -> None:
    """PER-02: serve loads matching YAML; --no-ui still calls try_reapply."""
    source = inspect.getsource(cli_mod.serve)
    assert "try_reapply(" in source
    assert "--calibration-file" in source
    assert "calibration:" in source
    assert "calibration_path=" in source
    assert "calibration_path(" in source
    idx_src = source.index("_build_serve_source")
    idx_ctor = source.index("calibration_state = CalibrationState()")
    idx_depth = source.index("DepthAnythingWorker")
    idx_reapply = source.index("try_reapply(")
    idx_create = source.index("create_app(")
    assert idx_src < idx_reapply
    assert idx_ctor < idx_reapply
    assert idx_depth < idx_reapply
    assert idx_reapply < idx_create
    # Headless still loads — reapply is not gated on no_ui.
    assert "serve_ui=not no_ui" in source
    before_create = source.split("create_app(")[0]
    assert "try_reapply(" in before_create


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
        assert getattr(app.state, "calibration_path", None) is None
        assert app.state.deps.calibration_path is None
    finally:
        loop.stop()


def test_create_app_calibration_path_stashed() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    dest = Path("/tmp/sentry-calib-cam0.yaml")
    try:
        app = create_app(
            bus=bus,
            capture_loop=loop,
            bind="127.0.0.1:8000",
            calibration_path=dest,
        )
        assert app.state.calibration_path == dest
        assert app.state.deps.calibration_path == dest
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


def test_serve_help_shows_calibration_file() -> None:
    from sentry_ai.cli import app
    from tests.cli_helpers import cli_help_output

    out = cli_help_output(app, "serve", "--help")
    assert "--calibration-file" in out
