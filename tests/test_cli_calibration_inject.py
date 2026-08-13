"""CAL-03: cli.serve constructs CalibrationState and injects it into DepthLoop."""

from __future__ import annotations

import inspect

from sentry_ai import cli as cli_mod


def test_serve_injects_calibration_state_into_depth_loop() -> None:
    source = inspect.getsource(cli_mod.serve)
    assert "CalibrationState" in source
    assert "calibration_state = CalibrationState()" in source
    assert "calibration=calibration_state" in source
    assert "DepthLoop(bus, depth_worker, store, calibration=calibration_state)" in source
