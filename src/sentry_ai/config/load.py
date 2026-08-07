"""Load and merge runtime profiles from YAML + env overrides.

Security (T-1-01): only ``yaml.safe_load`` is used — never ``yaml.load``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from sentry_ai.config.models import SentryConfig
from sentry_ai.schemas.enums import RuntimeProfile

_PROFILES_DIR = Path(__file__).resolve().parent / "profiles"
_DEFAULT_PROFILE = RuntimeProfile.CPU_FALLBACK


def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"invalid boolean env value: {value!r}")


def _coerce_profile(profile: RuntimeProfile | str) -> RuntimeProfile:
    if isinstance(profile, RuntimeProfile):
        return profile
    try:
        return RuntimeProfile(profile)
    except ValueError as exc:
        known = ", ".join(p.value for p in RuntimeProfile)
        raise ValueError(
            f"unknown runtime profile {profile!r}; expected one of: {known}"
        ) from exc


def _profile_path(profile: RuntimeProfile) -> Path:
    path = _PROFILES_DIR / f"{profile.value}.yaml"
    if not path.is_file():
        raise FileNotFoundError(f"missing built-in profile YAML: {path}")
    return path


def _read_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"config root must be a mapping: {path}")
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = dict(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_profile(profile: RuntimeProfile | str) -> SentryConfig:
    """Load a built-in profile YAML into a validated :class:`SentryConfig`."""
    resolved = _coerce_profile(profile)
    data = _read_yaml(_profile_path(resolved))
    # Ensure profile field matches the requested profile even if YAML omits it.
    data.setdefault("profile", resolved.value)
    return SentryConfig.model_validate(data)


def load_config(
    profile: RuntimeProfile | str | None = None,
    user_config_path: str | Path | None = None,
) -> SentryConfig:
    """Load config with merge order: built-in profile → optional user file → env.

    Env overrides:
    - ``SENTRY_PROFILE`` selects the built-in profile when ``profile`` is None
    - ``SENTRY_ALLOW_CLOUD`` overrides ``models.allow_cloud`` (default false)
    """
    env_profile = os.environ.get("SENTRY_PROFILE")
    selected = profile if profile is not None else env_profile or _DEFAULT_PROFILE
    resolved = _coerce_profile(selected)

    data = _read_yaml(_profile_path(resolved))
    data.setdefault("profile", resolved.value)

    if user_config_path is not None:
        user_path = Path(user_config_path)
        if user_path.is_file():
            data = _deep_merge(data, _read_yaml(user_path))

    allow_cloud = _parse_bool(os.environ.get("SENTRY_ALLOW_CLOUD"), default=False)
    models = data.setdefault("models", {})
    if not isinstance(models, dict):
        raise ValueError("models config must be a mapping")
    # Env always wins for allow_cloud so accidental YAML true can be forced off,
    # and explicit SENTRY_ALLOW_CLOUD=true is the only opt-in path in tests.
    if "SENTRY_ALLOW_CLOUD" in os.environ:
        models["allow_cloud"] = allow_cloud
    else:
        models.setdefault("allow_cloud", False)

    return SentryConfig.model_validate(data)
