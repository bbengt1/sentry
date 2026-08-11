"""CAL-04 / CAL-05: calibration fingerprint, validity, and CalibrationState."""

from __future__ import annotations

import math

import pytest
from pydantic import ValidationError

from sentry_ai.control import CalibrationState
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSnapshot,
    is_valid_calibration_params,
)
from sentry_ai.schemas.enums import DepthKind


def _fp(**overrides: object) -> CalibrationFingerprint:
    data: dict[str, object] = {"camera_id": "cam0"}
    data.update(overrides)
    return CalibrationFingerprint(**data)  # type: ignore[arg-type]


def _params(**overrides: object) -> CalibrationParams:
    data: dict[str, object] = {
        "scale": 1.5,
        "sample_count": 3,
        "fingerprint": _fp(),
    }
    data.update(overrides)
    return CalibrationParams(**data)  # type: ignore[arg-type]


# --- CalibrationFingerprint -------------------------------------------------


def test_fingerprint_requires_camera_id() -> None:
    with pytest.raises(ValidationError):
        CalibrationFingerprint(camera_id="")


def test_fingerprint_camera_id_min_length() -> None:
    fp = CalibrationFingerprint(camera_id="c")
    assert fp.camera_id == "c"
    assert fp.schema_version == 1
    assert fp.width is None
    assert fp.height is None
    assert fp.depth_mode is None
    assert fp.model_id is None


def test_fingerprint_all_fields_settable() -> None:
    fp = CalibrationFingerprint(
        camera_id="cam1",
        width=640,
        height=480,
        depth_mode="metric_indoor",
        model_id="depth-anything-v2-small",
        schema_version=2,
    )
    assert fp.camera_id == "cam1"
    assert fp.width == 640
    assert fp.height == 480
    assert fp.depth_mode == "metric_indoor"
    assert fp.model_id == "depth-anything-v2-small"
    assert fp.schema_version == 2


def test_fingerprint_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalibrationFingerprint(camera_id="cam0", motor_cmd=1.0)  # type: ignore[call-arg]


# --- CalibrationParams ------------------------------------------------------


def test_params_requires_fingerprint_and_scale() -> None:
    p = _params()
    assert p.scale == 1.5
    assert p.offset == 0.0
    assert p.method == "known_distance"
    assert p.sample_count == 3
    assert p.fingerprint.camera_id == "cam0"
    assert p.version == 1
    assert p.residual_rms is None
    assert p.created_at is None


def test_params_defaults() -> None:
    p = CalibrationParams(scale=2.0, fingerprint=_fp())
    assert p.offset == 0.0
    assert p.method == "known_distance"
    assert p.sample_count == 0
    assert p.version == 1


def test_params_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalibrationParams(
            scale=1.0,
            fingerprint=_fp(),
            safety_flag=True,  # type: ignore[call-arg]
        )


# --- is_valid_calibration_params --------------------------------------------


def test_valid_params_pass() -> None:
    ok, reason = is_valid_calibration_params(_params())
    assert ok is True
    assert reason is None


def test_invalid_scale_non_positive() -> None:
    for scale in (0.0, -1.0, -0.001):
        ok, reason = is_valid_calibration_params(_params(scale=scale))
        assert ok is False
        assert reason is not None
        assert "scale" in reason


def test_invalid_scale_non_finite() -> None:
    for scale in (math.nan, math.inf, -math.inf):
        ok, reason = is_valid_calibration_params(_params(scale=scale))
        assert ok is False
        assert reason is not None
        assert "scale" in reason


def test_invalid_offset_nan() -> None:
    ok, reason = is_valid_calibration_params(_params(offset=math.nan))
    assert ok is False
    assert reason is not None
    assert "offset" in reason


def test_invalid_offset_inf() -> None:
    ok, reason = is_valid_calibration_params(_params(offset=math.inf))
    assert ok is False
    assert reason is not None
    assert "offset" in reason


def test_sample_count_floor_non_manual() -> None:
    ok, reason = is_valid_calibration_params(
        _params(method="known_distance", sample_count=0)
    )
    assert ok is False
    assert reason is not None
    assert "sample" in reason


def test_manual_scale_allows_zero_samples() -> None:
    ok, reason = is_valid_calibration_params(
        _params(method="manual_scale", sample_count=0)
    )
    assert ok is True
    assert reason is None


def test_known_height_requires_samples() -> None:
    ok, reason = is_valid_calibration_params(
        _params(method="known_height", sample_count=0)
    )
    assert ok is False
    assert reason is not None


def test_valid_params_with_full_fingerprint() -> None:
    p = _params(
        fingerprint=CalibrationFingerprint(
            camera_id="front",
            width=1280,
            height=720,
            depth_mode="relative",
            model_id="da2",
            schema_version=1,
        ),
        sample_count=2,
    )
    ok, reason = is_valid_calibration_params(p)
    assert ok is True
    assert reason is None
    assert p.fingerprint.camera_id == "front"
    assert p.fingerprint.width == 1280


# --- CalibrationSnapshot ----------------------------------------------------


def test_snapshot_defaults() -> None:
    snap = CalibrationSnapshot()
    assert snap.applied is False
    assert snap.valid is False
    assert snap.draft_sample_count == 0
    assert snap.has_draft_params is False


def test_snapshot_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalibrationSnapshot(applied=False, command="drive")  # type: ignore[call-arg]


def test_no_motor_safety_command_fields_on_models() -> None:
    """Perception-only models: no motor/safety/command surface."""
    for model in (CalibrationFingerprint, CalibrationParams, CalibrationSnapshot):
        names = set(model.model_fields)
        for banned in ("motor", "safety", "command", "velocity", "throttle"):
            assert not any(banned in n for n in names), f"{model.__name__} has {banned}"


# --- CalibrationState draft vs applied --------------------------------------


def test_state_defaults_not_applied() -> None:
    state = CalibrationState()
    assert state.is_applied() is False
    assert state.is_valid_applied() is False
    snap = state.snapshot()
    assert snap.applied is False
    assert snap.valid is False
    assert snap.has_draft_params is False
    assert snap.draft_sample_count == 0
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None
    kind, unit = state.promote_kind_unit(DepthKind.METRIC_ESTIMATED, "m")
    assert kind == DepthKind.METRIC_ESTIMATED
    assert unit == "m"


def test_draft_params_do_not_apply_or_promote() -> None:
    state = CalibrationState()
    snap = state.set_draft_params(_params())
    assert snap.has_draft_params is True
    assert snap.applied is False
    assert state.is_applied() is False
    assert state.is_valid_applied() is False
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None


def test_apply_no_draft_raises() -> None:
    state = CalibrationState()
    with pytest.raises(ValueError):
        state.apply()
    assert state.is_applied() is False


def test_apply_invalid_draft_raises_and_stays_unapplied() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=-1.0, sample_count=2))
    with pytest.raises(ValueError):
        state.apply()
    assert state.is_applied() is False
    assert state.is_valid_applied() is False
    kind, unit = state.promote_kind_unit(DepthKind.METRIC_ESTIMATED, "m")
    assert kind == DepthKind.METRIC_ESTIMATED
    assert unit == "m"


def test_apply_valid_draft_promotes_to_calibrated() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=2.0, sample_count=4))
    snap = state.apply()
    assert snap.applied is True
    assert snap.valid is True
    assert state.is_applied() is True
    assert state.is_valid_applied() is True
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"
    kind, unit = state.promote_kind_unit(DepthKind.METRIC_ESTIMATED, "m")
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"


def test_clear_draft_after_apply_leaves_applied() -> None:
    state = CalibrationState()
    state.set_draft_params(_params())
    state.apply()
    snap = state.clear_draft()
    assert state.is_applied() is True
    assert state.is_valid_applied() is True
    assert snap.has_draft_params is False
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"


def test_clear_applied_restores_base_promotion() -> None:
    state = CalibrationState()
    state.set_draft_params(_params())
    state.apply()
    snap = state.clear_applied()
    assert snap.applied is False
    assert state.is_applied() is False
    assert state.is_valid_applied() is False
    kind, unit = state.promote_kind_unit(DepthKind.METRIC_ESTIMATED, "m")
    assert kind == DepthKind.METRIC_ESTIMATED
    assert unit == "m"


def test_failed_apply_does_not_wipe_prior_applied() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=1.25, sample_count=2))
    state.apply()
    assert state.is_applied() is True
    # Stage an invalid draft and attempt apply
    state.set_draft_params(_params(scale=0.0, sample_count=5))
    with pytest.raises(ValueError):
        state.apply()
    assert state.is_applied() is True
    assert state.is_valid_applied() is True
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"
    # Applied params still have original scale
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 1.25


def test_snapshot_includes_applied_fields() -> None:
    state = CalibrationState()
    fp = CalibrationFingerprint(
        camera_id="cam-front",
        width=640,
        height=480,
        depth_mode="metric_indoor",
        model_id="da2",
    )
    state.set_draft_params(
        _params(scale=3.0, method="known_distance", sample_count=2, fingerprint=fp)
    )
    snap = state.apply()
    assert snap.applied is True
    assert snap.valid is True
    assert snap.scale == 3.0
    assert snap.method == "known_distance"
    assert snap.fingerprint is not None
    assert snap.fingerprint.camera_id == "cam-front"
    assert snap.fingerprint.width == 640


def test_snapshot_isolated_from_mutations() -> None:
    state = CalibrationState()
    before = state.snapshot()
    state.set_draft_params(_params())
    assert before.has_draft_params is False
    after = state.snapshot()
    assert after.has_draft_params is True


def test_control_package_exports_calibration_state() -> None:
    from sentry_ai import control

    assert hasattr(control, "CalibrationState")
    assert "CalibrationState" in control.__all__
