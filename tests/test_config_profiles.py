"""FOUND-06 / MODEL-01: Runtime profiles and allow_cloud defaults."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentry_ai.config.load import load_config, load_profile
from sentry_ai.config.models import SentryConfig
from sentry_ai.policy.models import (
    CORE_PATH_LOCAL_OSS_ONLY,
    DEFAULT_ALLOW_CLOUD,
    DEFAULT_DEPTH_WEIGHT_KEY,
)
from sentry_ai.schemas import RuntimeProfile


def test_runtime_profile_enum_exact_set() -> None:
    assert {m.value for m in RuntimeProfile} == {
        "desktop-gpu",
        "jetson",
        "cpu-fallback",
    }


@pytest.mark.parametrize(
    "profile",
    [
        RuntimeProfile.DESKTOP_GPU,
        RuntimeProfile.JETSON,
        RuntimeProfile.CPU_FALLBACK,
        "desktop-gpu",
        "jetson",
        "cpu-fallback",
    ],
)
def test_load_profile_succeeds(profile: RuntimeProfile | str) -> None:
    cfg = load_profile(profile)
    assert isinstance(cfg, SentryConfig)
    assert isinstance(cfg.profile, RuntimeProfile)


@pytest.mark.parametrize(
    "profile",
    ["desktop-gpu", "jetson", "cpu-fallback"],
)
def test_allow_cloud_false_on_all_profiles(profile: str) -> None:
    cfg = load_profile(profile)
    assert cfg.models.allow_cloud is False


def test_models_config_default_allow_cloud_false() -> None:
    from sentry_ai.config.models import ModelsConfig

    assert ModelsConfig().allow_cloud is False


def test_unknown_profile_raises() -> None:
    with pytest.raises((ValueError, KeyError)) as exc_info:
        load_profile("not-a-real-profile")
    assert "not-a-real-profile" in str(exc_info.value).lower() or "profile" in str(
        exc_info.value
    ).lower()


def test_load_config_uses_sentry_profile_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_PROFILE", "jetson")
    monkeypatch.delenv("SENTRY_ALLOW_CLOUD", raising=False)
    cfg = load_config()
    assert cfg.profile == RuntimeProfile.JETSON
    assert cfg.models.allow_cloud is False


def test_load_config_allow_cloud_env_explicit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTRY_PROFILE", "cpu-fallback")
    monkeypatch.setenv("SENTRY_ALLOW_CLOUD", "true")
    cfg = load_config()
    assert cfg.models.allow_cloud is True


def test_load_config_allow_cloud_env_default_false(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SENTRY_PROFILE", "desktop-gpu")
    monkeypatch.delenv("SENTRY_ALLOW_CLOUD", raising=False)
    cfg = load_config()
    assert cfg.models.allow_cloud is False


def test_yaml_profiles_use_safe_load() -> None:
    """Config loader must use yaml.safe_load only (T-1-01)."""
    root = Path(__file__).resolve().parents[1]
    load_src = root / "src" / "sentry_ai" / "config" / "load.py"
    text = load_src.read_text(encoding="utf-8")
    assert "safe_load" in text
    # Disallow unsafe yaml.load( usage (but allow safe_load)
    for line in text.splitlines():
        stripped = line.strip()
        if "yaml.load" in stripped and "safe_load" not in stripped:
            pytest.fail(f"unsafe yaml.load found: {stripped}")


def test_policy_local_oss_core_path() -> None:
    assert CORE_PATH_LOCAL_OSS_ONLY is True
    assert DEFAULT_ALLOW_CLOUD is False
    assert DEFAULT_DEPTH_WEIGHT_KEY == "depth-anything-v2-small"


def test_desktop_gpu_backend_hint() -> None:
    cfg = load_profile(RuntimeProfile.DESKTOP_GPU)
    assert str(cfg.device.preferred_backend) in {"torch", "BackendName.TORCH"} or (
        cfg.device.preferred_backend == "torch"
    )


def test_cpu_fallback_device_id() -> None:
    cfg = load_profile(RuntimeProfile.CPU_FALLBACK)
    assert cfg.device.device_id == "cpu"
