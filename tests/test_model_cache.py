"""MODEL-02: Sentry-owned model cache path policy (no network)."""

from __future__ import annotations

from pathlib import Path

import pytest

from sentry_ai.models.cache import (
    KNOWN_WEIGHTS,
    configure_model_cache,
    default_cache_root,
    tier_to_weight,
)


def test_default_cache_root_is_home_cache_sentry_ai() -> None:
    root = default_cache_root()
    assert root == Path.home() / ".cache" / "sentry-ai"


def test_tier_to_weight_known_tiers() -> None:
    assert tier_to_weight("n") == "yolo26n.pt"
    assert tier_to_weight("s") == "yolo26s.pt"
    assert tier_to_weight("m") == "yolo26m.pt"
    assert tier_to_weight("N") == "yolo26n.pt"
    assert tier_to_weight(" S ") == "yolo26s.pt"


def test_tier_to_weight_default_and_unknown() -> None:
    assert tier_to_weight(None) == "yolo26n.pt"
    assert tier_to_weight("xl") == "yolo26n.pt"
    assert tier_to_weight("") == "yolo26n.pt"


def test_known_weights_allowlist() -> None:
    assert KNOWN_WEIGHTS == frozenset({"yolo26n.pt", "yolo26s.pt", "yolo26m.pt"})
    for name in (tier_to_weight(t) for t in ("n", "s", "m", None)):
        assert name in KNOWN_WEIGHTS
        assert ".." not in name
        assert "/" not in name
        assert "\\" not in name


def test_configure_model_cache_uses_arg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SENTRY_MODEL_CACHE", raising=False)
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    monkeypatch.delenv("YOLO_CONFIG_DIR", raising=False)
    weights = configure_model_cache(tmp_path)
    assert weights == tmp_path / "weights"
    assert weights.is_dir()
    assert os_environ_yolo_config_under(tmp_path)
    assert os_environ_hf_home_under(tmp_path)


def test_configure_model_cache_uses_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    env_root = tmp_path / "env-cache"
    monkeypatch.setenv("SENTRY_MODEL_CACHE", str(env_root))
    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    monkeypatch.delenv("YOLO_CONFIG_DIR", raising=False)
    weights = configure_model_cache()
    assert weights == env_root / "weights"
    assert weights.is_dir()
    assert os_environ_hf_home_under(env_root)


def test_configure_model_cache_idempotent(tmp_path: Path) -> None:
    w1 = configure_model_cache(tmp_path)
    w2 = configure_model_cache(tmp_path)
    assert w1 == w2
    assert w1.is_dir()
    assert (tmp_path / "hf").is_dir()


def test_configure_model_cache_sets_hf_home(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MODEL-02: HF_HOME is sibling of weights/ under cache root."""
    import os

    monkeypatch.delenv("HF_HOME", raising=False)
    monkeypatch.delenv("HUGGINGFACE_HUB_CACHE", raising=False)
    weights = configure_model_cache(tmp_path)
    assert weights == tmp_path / "weights"
    assert weights.is_dir()
    hf = tmp_path / "hf"
    assert hf.is_dir()
    assert os.environ["HF_HOME"] == str(hf)
    assert os.environ["HUGGINGFACE_HUB_CACHE"] == str(hf / "hub")


def os_environ_yolo_config_under(root: Path) -> bool:
    import os

    yolo = os.environ.get("YOLO_CONFIG_DIR")
    return yolo is not None and str(root / "ultralytics") in yolo


def os_environ_hf_home_under(root: Path) -> bool:
    import os

    hf = os.environ.get("HF_HOME")
    return hf is not None and str(root / "hf") in hf
