"""PER-01 / PER-03: try_reapply honesty (match / mismatch / corrupt / missing)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentry_ai.config.calibration_store import load_params, save_params
from sentry_ai.control.calibration_persist import (
    clear_persisted,
    persist_applied,
    refuse_if_mismatch,
    try_reapply,
)
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
)
from sentry_ai.schemas.enums import DepthKind


def _fp(**overrides: object) -> CalibrationFingerprint:
    data: dict[str, object] = {
        "camera_id": "usb0",
        "width": 1920,
        "height": 1080,
        "depth_mode": "relative",
        "model_id": "da2",
    }
    data.update(overrides)
    return CalibrationFingerprint(**data)  # type: ignore[arg-type]


def _params(**overrides: object) -> CalibrationParams:
    data: dict[str, object] = {
        "scale": 2.25,
        "offset": 0.0,
        "method": "manual_scale",
        "sample_count": 0,
        "fingerprint": _fp(),
    }
    data.update(overrides)
    return CalibrationParams(**data)  # type: ignore[arg-type]


def _live(**overrides: object) -> CalibrationFingerprint:
    return _fp(**overrides)


def test_try_reapply_match_applies_without_draft_samples(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(scale=2.25), path)
    state = CalibrationState()
    result = try_reapply(state, path, _live())
    assert result.status == "applied"
    assert result.path == path
    assert state.is_applied() is True
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 2.25
    assert state.get_draft_samples() == []
    assert state.snapshot().has_draft_params is False
    assert state.get_persist_status() == ("applied", None)
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"


def test_try_reapply_wrong_camera_id_ignored(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(), path)
    state = CalibrationState()
    result = try_reapply(state, path, _live(camera_id="other"))
    assert result.status == "ignored_mismatch"
    assert result.reason == "camera_id"
    assert state.is_applied() is False
    status, reason = state.get_persist_status()
    assert status == "ignored_mismatch"
    assert reason is not None
    assert "camera_id" in reason
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None


def test_try_reapply_missing_is_none(tmp_path: Path) -> None:
    path = tmp_path / "missing.yaml"
    state = CalibrationState()
    result = try_reapply(state, path, _live())
    assert result.status == "none"
    assert state.is_applied() is False
    assert state.get_persist_status() == ("none", None)


def test_try_reapply_corrupt_yaml_is_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("{]", encoding="utf-8")
    state = CalibrationState()
    result = try_reapply(state, path, _live())
    assert result.status == "error"
    assert state.is_applied() is False
    assert state.get_persist_status()[0] == "error"
    kind, _unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE


def test_try_reapply_invalid_params_is_error(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("scale: []\n", encoding="utf-8")
    state = CalibrationState()
    result = try_reapply(state, path, _live())
    assert result.status == "error"
    assert state.is_applied() is False


def test_try_reapply_structurally_invalid_scale_is_error(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(scale=0.0), path)
    state = CalibrationState()
    result = try_reapply(state, path, _live())
    assert result.status == "error"
    assert state.is_applied() is False
    assert state.get_persist_status()[0] == "error"


def test_try_reapply_does_not_invent_draft_samples(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(), path)
    state = CalibrationState()
    state.add_draft_sample(CalibrationSample(known_meters=1.0, observed_raw=0.4))
    result = try_reapply(state, path, _live())
    assert result.status == "applied"
    assert state.get_draft_samples() == []


def test_persist_applied_writes_loadable_file(tmp_path: Path) -> None:
    state = CalibrationState()
    state.apply_params(_params(scale=3.5))
    path = tmp_path / "out.yaml"
    written = persist_applied(state, path)
    assert written == path
    loaded = load_params(path)
    assert loaded.status == "ok"
    assert loaded.params is not None
    assert loaded.params.scale == 3.5


def test_persist_applied_inactive_raises(tmp_path: Path) -> None:
    state = CalibrationState()
    with pytest.raises(ValueError):
        persist_applied(state, tmp_path / "out.yaml")
    assert not (tmp_path / "out.yaml").exists()


def test_clear_persisted_unlinks_and_clears(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    state = CalibrationState()
    state.apply_params(_params())
    persist_applied(state, path)
    assert path.exists()
    clear_persisted(state, path)
    assert not path.exists()
    assert state.is_applied() is False
    assert state.get_draft_samples() == []
    assert state.snapshot().has_draft_params is False


def test_refuse_if_mismatch_clears_on_resolution() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    state.set_persist_status("applied")
    why = refuse_if_mismatch(state, _live(width=1280, height=720))
    assert why == "resolution"
    assert state.is_applied() is False
    assert state.get_persist_status() == ("ignored_mismatch", "resolution")


def test_refuse_if_mismatch_skips_when_live_size_none() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    why = refuse_if_mismatch(state, _live(width=None, height=None))
    assert why is None
    assert state.is_applied() is True


def test_refuse_if_mismatch_noop_when_inactive() -> None:
    state = CalibrationState()
    why = refuse_if_mismatch(state, _live())
    assert why is None
    assert state.is_applied() is False


def test_try_reapply_match_does_not_enable_online(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(scale=2.25), path)
    state = CalibrationState()
    result = try_reapply(state, path, _live())
    assert result.status == "applied"
    assert state.is_applied() is True
    assert state.is_online() is False
    assert state.snapshot().online is False


def test_disable_online_leaves_yaml(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    state = CalibrationState()
    state.apply_params(_params())
    persist_applied(state, path)
    state.set_online(True)
    state.set_online(False)
    assert path.exists()
    loaded = load_params(path)
    assert loaded.status == "ok"
    assert loaded.params is not None
    assert state.is_applied() is True
    assert state.is_online() is False


def test_clear_persisted_forces_online_off(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    state = CalibrationState()
    state.apply_params(_params())
    persist_applied(state, path)
    state.set_online(True)
    clear_persisted(state, path)
    assert not path.exists()
    assert state.is_online() is False
    assert state.snapshot().online_status == "online_off"
