"""PER-01 / PER-03: YAML calibration store + fingerprint refuse."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentry_ai.config.calibration_store import (
    calibration_path,
    default_calibration_dir,
    delete_params,
    fingerprints_match,
    load_params,
    safe_camera_stem,
    save_params,
)
from sentry_ai.models.cache import default_cache_root
from sentry_ai.schemas.calibration import CalibrationFingerprint, CalibrationParams


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
        "scale": 2.5,
        "offset": 0.1,
        "method": "known_distance",
        "sample_count": 3,
        "residual_rms": 0.02,
        "fingerprint": _fp(),
        "created_at": 1_700_000_000.0,
    }
    data.update(overrides)
    return CalibrationParams(**data)  # type: ignore[arg-type]


# --- path resolve -----------------------------------------------------------


def test_default_dir_calibration_env_wins(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cal = tmp_path / "cal-dir"
    monkeypatch.setenv("SENTRY_CALIBRATION_DIR", str(cal))
    monkeypatch.setenv("SENTRY_MODEL_CACHE", str(tmp_path / "cache"))
    assert default_calibration_dir() == cal
    assert not cal.exists()


def test_default_dir_model_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SENTRY_CALIBRATION_DIR", raising=False)
    monkeypatch.setenv("SENTRY_MODEL_CACHE", str(tmp_path / "cache"))
    assert default_calibration_dir() == tmp_path / "cache" / "calibration"


def test_default_dir_cache_root(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SENTRY_CALIBRATION_DIR", raising=False)
    monkeypatch.delenv("SENTRY_MODEL_CACHE", raising=False)
    assert default_calibration_dir() == default_cache_root() / "calibration"


def test_calibration_path_usb0_under_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("SENTRY_CALIBRATION_DIR", raising=False)
    monkeypatch.setenv("SENTRY_MODEL_CACHE", str(tmp_path / "cache"))
    path = calibration_path("usb0")
    assert path == tmp_path / "cache" / "calibration" / "usb0.yaml"
    assert str(path).endswith("calibration/usb0.yaml")


def test_calibration_path_directory_kwarg(tmp_path: Path) -> None:
    path = calibration_path("usb0", directory=tmp_path / "other")
    assert path == tmp_path / "other" / "usb0.yaml"
    assert path.parent == tmp_path / "other"


def test_calibration_path_explicit_file_wins(tmp_path: Path) -> None:
    explicit = tmp_path / "custom" / "override.yaml"
    path = calibration_path("usb0", explicit_file=explicit)
    assert path == explicit


# --- sanitize ---------------------------------------------------------------


def test_safe_camera_stem_allows_simple_and_dotted() -> None:
    assert safe_camera_stem("usb0") == "usb0"
    assert safe_camera_stem("cam.1-a") == "cam.1-a"


@pytest.mark.parametrize(
    "bad",
    ["", "   ", "..", "../x", "a/b", "a\\b", ".hidden", "cam..1"],
)
def test_safe_camera_stem_rejects_unsafe(bad: str) -> None:
    with pytest.raises(ValueError, match="unsafe|empty"):
        safe_camera_stem(bad)


def test_safe_camera_stem_never_escapes_directory(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsafe|empty"):
        calibration_path("../etc/passwd", directory=tmp_path)
    path = calibration_path("usb0", directory=tmp_path)
    assert path.resolve().parent == tmp_path.resolve()


# --- save / load / delete ---------------------------------------------------


def test_save_load_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    params = _params()
    saved = save_params(params, path)
    assert saved == path
    assert path.exists()
    assert not (tmp_path / "usb0.yaml.tmp").exists()
    loaded = load_params(path)
    assert loaded.status == "ok"
    assert loaded.params is not None
    assert loaded.params.scale == 2.5
    assert loaded.params.offset == 0.1
    assert loaded.params.method == "known_distance"
    assert loaded.params.sample_count == 3
    assert loaded.params.residual_rms == 0.02
    assert loaded.params.created_at == 1_700_000_000.0
    fp = loaded.params.fingerprint
    assert fp.camera_id == "usb0"
    assert fp.width == 1920
    assert fp.height == 1080
    assert fp.depth_mode == "relative"
    assert fp.model_id == "da2"


def test_saved_yaml_has_no_maps_or_samples(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(), path)
    text = path.read_text(encoding="utf-8")
    assert "depth_map" not in text
    assert "samples" not in text
    assert "freeze" not in text


def test_save_params_atomic_no_tmp_left(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "usb0.yaml"
    save_params(_params(), path)
    assert path.exists()
    leftovers = list(path.parent.glob("*.tmp"))
    assert leftovers == []


def test_load_params_missing(tmp_path: Path) -> None:
    result = load_params(tmp_path / "missing.yaml")
    assert result.status == "none"
    assert result.params is None


def test_load_params_not_a_mapping(tmp_path: Path) -> None:
    path = tmp_path / "list.yaml"
    path.write_text("- just a list\n", encoding="utf-8")
    result = load_params(path)
    assert result.status == "error"
    assert result.params is None


def test_load_params_corrupt_yaml(tmp_path: Path) -> None:
    path = tmp_path / "bad.yaml"
    path.write_text("{]", encoding="utf-8")
    result = load_params(path)
    assert result.status == "error"
    assert result.params is None


def test_load_params_invalid_params(tmp_path: Path) -> None:
    path = tmp_path / "invalid.yaml"
    path.write_text("scale: []\n", encoding="utf-8")
    result = load_params(path)
    assert result.status == "error"
    assert result.params is None


def test_delete_params_true_then_false(tmp_path: Path) -> None:
    path = tmp_path / "usb0.yaml"
    save_params(_params(), path)
    assert delete_params(path) is True
    assert not path.exists()
    assert delete_params(path) is False


# --- fingerprints_match -----------------------------------------------------


def test_fingerprints_match_same_camera_mode_model() -> None:
    saved = _fp()
    live = _fp()
    ok, reason = fingerprints_match(saved, live)
    assert ok is True
    assert reason is None


def test_fingerprints_match_camera_id_mismatch() -> None:
    ok, reason = fingerprints_match(_fp(camera_id="usb0"), _fp(camera_id="usb1"))
    assert ok is False
    assert reason == "camera_id"


def test_fingerprints_match_depth_mode_mismatch() -> None:
    ok, reason = fingerprints_match(
        _fp(depth_mode="relative"),
        _fp(depth_mode="metric_indoor"),
    )
    assert ok is False
    assert reason == "depth_mode"


def test_fingerprints_match_model_id_mismatch() -> None:
    ok, reason = fingerprints_match(_fp(model_id="da2"), _fp(model_id="other"))
    assert ok is False
    assert reason == "model_id"


def test_fingerprints_match_skips_size_when_live_none() -> None:
    saved = _fp(width=1920, height=1080)
    live = _fp(width=None, height=None)
    ok, reason = fingerprints_match(saved, live)
    assert ok is True
    assert reason is None


def test_fingerprints_match_same_resolution() -> None:
    ok, reason = fingerprints_match(
        _fp(width=1920, height=1080),
        _fp(width=1920, height=1080),
    )
    assert ok is True
    assert reason is None


def test_fingerprints_match_resolution_mismatch() -> None:
    ok, reason = fingerprints_match(
        _fp(width=1920, height=1080),
        _fp(width=1280, height=720),
    )
    assert ok is False
    assert reason == "resolution"


def test_fingerprints_match_saved_mode_none_skips() -> None:
    ok, reason = fingerprints_match(
        _fp(depth_mode=None),
        _fp(depth_mode="relative"),
    )
    assert ok is True
    assert reason is None


def test_fingerprints_match_saved_model_none_skips() -> None:
    ok, reason = fingerprints_match(_fp(model_id=None), _fp(model_id="da2"))
    assert ok is True
    assert reason is None


def test_fingerprints_match_saved_mode_vs_live_none() -> None:
    ok, reason = fingerprints_match(
        _fp(depth_mode="relative"),
        _fp(depth_mode=None),
    )
    assert ok is False
    assert reason == "depth_mode"


# --- module constraints -----------------------------------------------------


def test_store_module_safe_load_only_no_hot_imports() -> None:
    from sentry_ai.config import calibration_store

    src = Path(calibration_store.__file__).read_text(encoding="utf-8")
    assert "yaml.safe_load" in src
    assert "yaml.load(" not in src
    assert "import platformdirs" not in src
    lowered = src.lower()
    assert "fastapi" not in lowered
    assert "torch" not in lowered
    assert "DepthLoop" not in src
    assert "DetectionLoop" not in src
    assert "FrameBus" not in src
