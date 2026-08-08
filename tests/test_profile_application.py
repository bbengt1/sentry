"""EDGE-02: ProfileRuntime maps tiers + preferred_backend device policy."""

from __future__ import annotations

import pytest

from sentry_ai.config.load import load_config
from sentry_ai.config.profile_runtime import (
    ProfileRuntime,
    device_for_backend,
    profile_runtime,
)
from sentry_ai.models.cache import tier_to_open_vocab_weight, tier_to_weight
from sentry_ai.models.depth.mapping import (
    ALLOWED_DEPTH_TIERS,
    DEFAULT_MODEL_ID,
    assert_depth_tier_allowed,
    tier_to_depth_model_id,
)
from sentry_ai.schemas.enums import BackendName, RuntimeProfile


def test_tier_to_open_vocab_weight_mapping() -> None:
    assert tier_to_open_vocab_weight("n") == "yoloe-26n-seg.pt"
    assert tier_to_open_vocab_weight("s") == "yoloe-26s-seg.pt"
    assert tier_to_open_vocab_weight("m") == "yoloe-26s-seg.pt"  # no m OV weight
    assert tier_to_open_vocab_weight(None) == "yoloe-26s-seg.pt"
    assert tier_to_open_vocab_weight("unknown") == "yoloe-26s-seg.pt"
    assert tier_to_open_vocab_weight(" N ") == "yoloe-26n-seg.pt"


def test_device_for_backend_cpu_and_onnxruntime() -> None:
    assert device_for_backend("cpu", "cuda:0") == "cpu"
    assert device_for_backend("onnxruntime", "cpu") == "cpu"
    assert device_for_backend(BackendName.CPU, "anything") == "cpu"
    assert device_for_backend(BackendName.ONNXRUNTIME, "0") == "cpu"


def test_device_for_backend_torch() -> None:
    assert device_for_backend("torch", "cuda:0") == "cuda:0"
    assert device_for_backend(BackendName.TORCH, "cuda:1") == "cuda:1"
    # Empty / cpu device_id → auto (None → resolve_device at worker)
    assert device_for_backend("torch", "") is None
    assert device_for_backend("torch", "cpu") is None


def test_device_for_backend_tensorrt_honesty() -> None:
    """tensorrt is device policy only — never a fake torch device string."""
    dev = device_for_backend("tensorrt", "0")
    assert dev is not None
    assert "tensorrt" not in str(dev).lower()
    assert dev.startswith("cuda") or dev == "0" or "cuda" in str(dev)
    # Prefer cuda-like from bare index
    assert device_for_backend("tensorrt", "0") == "cuda:0"
    assert device_for_backend(BackendName.TENSORRT, "cuda:0") == "cuda:0"


def test_device_for_backend_openvino_advisory() -> None:
    assert device_for_backend("openvino", "cpu") is None
    assert device_for_backend(BackendName.OPENVINO, "0") is None


@pytest.mark.parametrize(
    ("profile", "detector_w", "ov_w", "backend"),
    [
        ("desktop-gpu", "yolo26s.pt", "yoloe-26s-seg.pt", "torch"),
        ("jetson", "yolo26n.pt", "yoloe-26n-seg.pt", "tensorrt"),
        ("cpu-fallback", "yolo26n.pt", "yoloe-26n-seg.pt", "onnxruntime"),
    ],
)
def test_profile_runtime_all_profiles(
    profile: str,
    detector_w: str,
    ov_w: str,
    backend: str,
) -> None:
    cfg = load_config(profile=profile)
    rt = profile_runtime(cfg)
    assert isinstance(rt, ProfileRuntime)
    assert rt.profile == RuntimeProfile(profile)
    assert rt.detector_weights == detector_w
    assert rt.open_vocab_weights == ov_w
    assert rt.depth_tier == "small"
    assert rt.depth_model_id == DEFAULT_MODEL_ID
    assert str(rt.preferred_backend) == backend or rt.preferred_backend == backend
    assert tier_to_weight(cfg.models.detector_tier) == detector_w
    assert tier_to_open_vocab_weight(cfg.models.detector_tier) == ov_w


def test_profile_runtime_cpu_fallback_forces_cpu() -> None:
    cfg = load_config(profile="cpu-fallback")
    rt = profile_runtime(cfg)
    assert rt.device == "cpu"
    assert rt.preferred_backend in ("onnxruntime", BackendName.ONNXRUNTIME)


def test_profile_runtime_desktop_gpu_device() -> None:
    cfg = load_config(profile="desktop-gpu")
    rt = profile_runtime(cfg)
    assert rt.device == "cuda:0"
    assert rt.preferred_backend in ("torch", BackendName.TORCH)


def test_profile_runtime_jetson_device_not_tensorrt_string() -> None:
    cfg = load_config(profile="jetson")
    rt = profile_runtime(cfg)
    assert rt.device is not None
    assert "tensorrt" not in str(rt.device).lower()
    assert rt.device == "cuda:0"
    assert rt.preferred_backend in ("tensorrt", BackendName.TENSORRT)


def test_depth_tier_small_allowed() -> None:
    assert "small" in ALLOWED_DEPTH_TIERS
    assert_depth_tier_allowed("small")
    assert_depth_tier_allowed("SMALL")
    assert tier_to_depth_model_id("small") == DEFAULT_MODEL_ID
    assert tier_to_depth_model_id("small", depth_mode="relative") == DEFAULT_MODEL_ID


def test_depth_tier_base_large_rejected() -> None:
    for bad in ("base", "large", "Base", "Large", "giant", "unknown", ""):
        with pytest.raises(ValueError, match="[Ss]mall|commercial|depth_tier"):
            assert_depth_tier_allowed(bad)
        with pytest.raises(ValueError, match="[Ss]mall|commercial|depth_tier"):
            tier_to_depth_model_id(bad)
