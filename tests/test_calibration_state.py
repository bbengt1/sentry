"""CAL-04 / CAL-05: calibration fingerprint, validity, and CalibrationState."""

from __future__ import annotations

import math

import numpy as np
import pytest
from pydantic import ValidationError

from sentry_ai.control import CalibrationState
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
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
        CalibrationFingerprint(
            camera_id="cam0",
            motor_cmd=1.0,  # type: ignore[call-arg]
        )


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
    assert snap.online is False


def test_snapshot_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalibrationSnapshot(applied=False, command="drive")  # type: ignore[call-arg]


def test_no_motor_safety_command_fields_on_models() -> None:
    """Perception-only models: no motor/safety/command surface."""
    for model in (
        CalibrationFingerprint,
        CalibrationParams,
        CalibrationSample,
        CalibrationSnapshot,
    ):
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


# --- apply_map (CAL-03) -----------------------------------------------------


def test_apply_map_none_returns_none() -> None:
    state = CalibrationState()
    assert state.apply_map(None) is None
    state.set_draft_params(_params(scale=2.5, sample_count=2))
    state.apply()
    assert state.apply_map(None) is None


def test_apply_map_inactive_pass_through() -> None:
    state = CalibrationState()
    src = np.ones((8, 12), dtype=np.float32) * 4.0
    out = state.apply_map(src)
    assert out is src
    np.testing.assert_array_equal(out, src)


def test_apply_map_draft_only_pass_through() -> None:
    """Draft never transforms — only applied+valid scales."""
    state = CalibrationState()
    state.set_draft_params(_params(scale=9.0, sample_count=2))
    src = np.ones((4, 4), dtype=np.float32) * 4.0
    out = state.apply_map(src)
    assert out is src
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None


def test_apply_map_scale_only() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=2.5, offset=0.0, sample_count=2))
    state.apply()
    src = np.ones((6, 8), dtype=np.float32) * 4.0
    original = src.copy()
    out = state.apply_map(src)
    assert out is not src
    assert out.dtype == np.float32
    assert out.shape == (6, 8)
    np.testing.assert_allclose(out, 10.0, rtol=1e-6)
    np.testing.assert_array_equal(src, original)
    # Mutating the output must not touch the worker buffer.
    out[0, 0] = 99.0
    assert src[0, 0] == 4.0


def test_apply_map_scale_and_offset() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=2.0, offset=1.0, sample_count=2))
    state.apply()
    src = np.ones((5, 7), dtype=np.float32) * 3.0
    original = src.copy()
    out = state.apply_map(src)
    assert out is not src
    assert out.dtype == np.float32
    np.testing.assert_allclose(out, 7.0, rtol=1e-6)
    np.testing.assert_array_equal(src, original)


def test_apply_map_clear_applied_restores_pass_through() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=2.0, sample_count=2))
    state.apply()
    src = np.ones((3, 3), dtype=np.float32) * 5.0
    scaled = state.apply_map(src)
    np.testing.assert_allclose(scaled, 10.0, rtol=1e-6)
    state.clear_applied()
    out = state.apply_map(src)
    assert out is src
    np.testing.assert_array_equal(out, src)
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None


def test_apply_map_invalid_applied_does_not_transform() -> None:
    """Structurally invalid applied params (bypass apply) must not scale."""
    state = CalibrationState()
    state._applied_params = _params(scale=-1.0, sample_count=2)
    src = np.ones((4, 4), dtype=np.float32) * 4.0
    out = state.apply_map(src)
    assert out is src
    np.testing.assert_array_equal(out, src)
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None



# --- draft sample public API (WIZ-01) ---------------------------------------


def test_calibration_sample_requires_known_meters() -> None:
    sample = CalibrationSample(known_meters=1.25)
    assert sample.known_meters == 1.25
    assert sample.point_uv is None
    assert sample.bbox_xyxy is None
    assert sample.observed_raw is None
    with pytest.raises(ValidationError):
        CalibrationSample()  # type: ignore[call-arg]


def test_calibration_sample_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        CalibrationSample(known_meters=1.0, motor_cmd=1.0)  # type: ignore[call-arg]


def test_add_draft_sample_increments_count_not_applied() -> None:
    state = CalibrationState()
    sample = CalibrationSample(
        known_meters=2.0, observed_raw=1.0, point_uv=(4.0, 5.0)
    )
    snap = state.add_draft_sample(sample)
    assert snap.draft_sample_count == 1
    assert snap.applied is False
    assert snap.has_draft_params is False
    assert state.is_applied() is False


def test_get_draft_samples_returns_copy() -> None:
    state = CalibrationState()
    sample = CalibrationSample(known_meters=1.0, observed_raw=0.5)
    state.add_draft_sample(sample)
    got = state.get_draft_samples()
    assert len(got) == 1
    got.clear()
    assert len(state.get_draft_samples()) == 1
    got2 = state.get_draft_samples()
    got2.append("nope")
    assert len(state.get_draft_samples()) == 1


def test_clear_draft_samples_zeros_count_keeps_draft_params() -> None:
    state = CalibrationState()
    state.add_draft_sample(CalibrationSample(known_meters=1.0, observed_raw=0.5))
    state.set_draft_params(_params())
    snap = state.clear_draft_samples()
    assert snap.draft_sample_count == 0
    assert snap.has_draft_params is True
    assert state.is_applied() is False


def test_clear_draft_clears_samples_and_params() -> None:
    state = CalibrationState()
    state.add_draft_sample(CalibrationSample(known_meters=1.0, observed_raw=0.5))
    state.set_draft_params(_params())
    snap = state.clear_draft()
    assert snap.draft_sample_count == 0
    assert snap.has_draft_params is False
    assert state.is_applied() is False


# --- apply_params + persist status (PER-01 / 17-01) -------------------------


def test_apply_params_valid_without_draft() -> None:
    state = CalibrationState()
    snap = state.apply_params(_params(scale=2.25, sample_count=2))
    assert snap.applied is True
    assert snap.valid is True
    assert snap.has_draft_params is False
    assert state.is_applied() is True
    assert state.get_draft_samples() == []
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 2.25
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"


def test_apply_params_clears_existing_draft() -> None:
    state = CalibrationState()
    state.add_draft_sample(CalibrationSample(known_meters=1.0, observed_raw=0.5))
    state.set_draft_params(_params(scale=9.0, sample_count=2))
    snap = state.apply_params(_params(scale=1.5, sample_count=1))
    assert snap.applied is True
    assert snap.has_draft_params is False
    assert snap.draft_sample_count == 0
    assert state.get_draft_samples() == []
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 1.5


def test_apply_params_invalid_scale_leaves_applied_unchanged() -> None:
    state = CalibrationState()
    state.apply_params(_params(scale=1.25, sample_count=2))
    with pytest.raises(ValueError):
        state.apply_params(_params(scale=0.0, sample_count=5))
    assert state.is_applied() is True
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 1.25


def test_apply_still_requires_draft_after_apply_params() -> None:
    state = CalibrationState()
    with pytest.raises(ValueError, match="no draft"):
        state.apply()
    assert state.is_applied() is False


def test_persist_status_defaults_and_snapshot() -> None:
    state = CalibrationState()
    snap = state.snapshot()
    assert snap.persist_status == "none"
    assert snap.persist_reason is None
    assert state.get_persist_status() == ("none", None)
    state.set_persist_status("error", "bad yaml")
    snap = state.snapshot()
    assert snap.persist_status == "error"
    assert snap.persist_reason == "bad yaml"
    assert state.get_persist_status() == ("error", "bad yaml")


def test_clear_applied_resets_persist_status() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    state.set_persist_status("applied")
    snap = state.clear_applied()
    assert snap.applied is False
    assert snap.persist_status == "none"
    assert snap.persist_reason is None
    assert state.get_persist_status() == ("none", None)


def test_snapshot_persist_defaults() -> None:
    snap = CalibrationSnapshot()
    assert snap.persist_status == "none"
    assert snap.persist_reason is None


# --- online consent flag (ONL-01 / ONL-02) ----------------------------------


def test_online_defaults_off() -> None:
    state = CalibrationState()
    assert state.is_online() is False
    assert state.snapshot().online is False
    assert state.is_applied() is False
    snap = CalibrationSnapshot()
    assert snap.online is False


def test_set_online_true_unapplied_raises() -> None:
    state = CalibrationState()
    with pytest.raises(ValueError, match="online_requires_applied"):
        state.set_online(True)
    assert state.is_online() is False
    assert state.is_applied() is False
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None


def test_set_online_false_unapplied_is_idempotent() -> None:
    state = CalibrationState()
    snap = state.set_online(False)
    assert snap.online is False
    assert state.is_online() is False
    assert state.is_applied() is False


def test_apply_does_not_enable_online() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=2.0, sample_count=4))
    snap = state.apply()
    assert snap.applied is True
    assert snap.valid is True
    assert state.is_online() is False
    assert snap.online is False
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"


def test_set_online_true_after_apply() -> None:
    state = CalibrationState()
    state.set_draft_params(_params(scale=2.0, sample_count=4))
    state.apply()
    snap = state.set_online(True)
    assert snap.online is True
    assert snap.applied is True
    assert state.is_online() is True
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 2.0
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"
    snap2 = state.set_online(True)
    assert snap2.online is True
    assert snap2.applied is True


def test_apply_params_does_not_enable_online() -> None:
    state = CalibrationState()
    snap = state.apply_params(_params(scale=2.25, sample_count=2))
    assert snap.applied is True
    assert state.is_online() is False
    assert snap.online is False
    snap2 = state.set_online(True)
    assert snap2.online is True
    assert snap2.applied is True


def test_set_online_true_never_creates_applied() -> None:
    state = CalibrationState()
    with pytest.raises(ValueError, match="online_requires_applied"):
        state.set_online(True)
    assert state.get_applied_params() is None
    assert state.is_applied() is False


def test_clear_applied_forces_online_off() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    state.set_online(True)
    assert state.is_online() is True
    snap = state.clear_applied()
    assert snap.online is False
    assert state.is_online() is False
    assert state.is_applied() is False


def test_disable_online_does_not_clear_applied() -> None:
    state = CalibrationState()
    state.apply_params(_params(scale=1.75, sample_count=2))
    state.set_online(True)
    snap = state.set_online(False)
    assert snap.online is False
    assert state.is_online() is False
    assert state.is_applied() is True
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 1.75


# --- online_status plane (ONL-01 / ONL-06) ----------------------------------


def test_snapshot_online_status_defaults() -> None:
    snap = CalibrationSnapshot()
    assert snap.online_status == "online_off"


def test_snapshot_online_status_enum_constructs() -> None:
    committed = CalibrationSnapshot(online_status="auto_committed")
    assert committed.online_status == "auto_committed"
    rejected = CalibrationSnapshot(online_status="rejected")
    assert rejected.online_status == "rejected"
    with pytest.raises(ValidationError):
        CalibrationSnapshot(online_status="not_a_status")  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        CalibrationSnapshot(
            online_status="online_off",
            extra_field=1,  # type: ignore[call-arg]
        )


def test_set_online_true_sets_online_draft() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    snap = state.set_online(True)
    assert snap.online is True
    assert snap.online_status == "online_draft"
    assert state.is_online() is True


def test_clear_draft_leaves_online_on() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    state.set_online(True)
    state.set_draft_params(_params(scale=3.0, sample_count=2))
    snap = state.clear_draft()
    assert snap.has_draft_params is False
    assert state.is_applied() is True
    assert state.is_online() is True
    assert snap.online is True
    assert snap.online_status == "online_draft"


def test_clear_applied_forces_online_off_status() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    state.set_online(True)
    snap = state.clear_applied()
    assert state.is_applied() is False
    assert state.is_online() is False
    assert snap.online_status == "online_off"
    assert snap.persist_status == "none"


def test_set_online_false_leaves_applied() -> None:
    state = CalibrationState()
    state.apply_params(_params(scale=1.75, sample_count=2))
    state.set_online(True)
    snap = state.set_online(False)
    assert state.is_applied() is True
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 1.75
    assert snap.online is False
    assert snap.online_status == "online_off"


def test_production_paths_never_leave_phase21_online_status() -> None:
    """set_online / clear_applied / clear_draft never yield auto_committed."""
    forbidden = {"auto_committed", "rejected"}
    state = CalibrationState()
    assert state.snapshot().online_status not in forbidden
    state.apply_params(_params())
    snap = state.set_online(True)
    assert snap.online_status not in forbidden
    snap = state.clear_draft()
    assert snap.online_status not in forbidden
    snap = state.set_online(False)
    assert snap.online_status not in forbidden
    state.set_online(True)
    snap = state.clear_applied()
    assert snap.online_status not in forbidden
