"""FOUND-06 / EDGE-02: Device/backend abstraction + light probe_device."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

from sentry_ai.backend import NullBackend
from sentry_ai.backend.null import NullBackend as NullBackendDirect
from sentry_ai.backend.protocols import DeviceInfo, InferenceBackend, probe_device
from sentry_ai.schemas.enums import BackendName, RuntimeProfile


def test_null_backend_importable_from_package() -> None:
    assert NullBackend is NullBackendDirect


def test_null_backend_lifecycle_without_torch() -> None:
    assert "torch" not in sys.modules

    backend = NullBackend()
    assert backend.name == BackendName.CPU
    backend.load()
    assert backend.infer(None) is None
    assert backend.infer({"x": 1}) is None
    assert backend.infer_calls == 2
    backend.close()

    # Still no torch after use
    assert "torch" not in sys.modules


def test_null_backend_is_inference_backend() -> None:
    backend = NullBackend()
    assert isinstance(backend, InferenceBackend)


def test_device_info_for_all_profiles() -> None:
    for profile in RuntimeProfile:
        info = DeviceInfo(
            profile=profile,
            backend=BackendName.CPU,
            device_id="cpu",
            available=False,
        )
        assert info.profile == profile
        assert info.available is False
        assert info.device_id == "cpu"


def test_device_info_cpu_fallback_defaults() -> None:
    info = DeviceInfo(
        profile=RuntimeProfile.CPU_FALLBACK,
        backend=BackendName.CPU,
        device_id="cpu",
    )
    assert info.available is False


def test_probe_device_never_raises() -> None:
    """EDGE-02: probe_device is advisory — never raises for any profile."""
    for profile in RuntimeProfile:
        info = probe_device(profile)
        assert isinstance(info, DeviceInfo)
        assert info.profile == profile
        assert isinstance(info.available, bool)
        assert info.device_id
        assert info.backend is not None


def test_probe_device_shape_desktop_gpu() -> None:
    info = probe_device(RuntimeProfile.DESKTOP_GPU)
    assert isinstance(info, DeviceInfo)
    assert info.profile == RuntimeProfile.DESKTOP_GPU
    assert info.backend == BackendName.TORCH
    assert info.device_id == "cuda:0"
    assert isinstance(info.available, bool)


def test_probe_device_shape_jetson() -> None:
    info = probe_device(RuntimeProfile.JETSON)
    assert info.backend == BackendName.TENSORRT
    assert info.device_id == "0"
    assert isinstance(info.available, bool)


def test_probe_device_cpu_fallback_available() -> None:
    """cpu-fallback reports available=True (CPU always usable)."""
    info = probe_device(RuntimeProfile.CPU_FALLBACK)
    assert info.profile == RuntimeProfile.CPU_FALLBACK
    assert info.available is True
    assert info.device_id == "cpu"


def test_probe_device_without_torch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When torch is missing, desktop/jetson report available=False."""
    import builtins

    real_import = builtins.__import__

    def _no_torch(name: str, *args: object, **kwargs: object) -> object:
        if name == "torch" or name.startswith("torch."):
            raise ImportError("mocked: no torch")
        return real_import(name, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(builtins, "__import__", _no_torch)
    info = probe_device(RuntimeProfile.DESKTOP_GPU)
    assert info.available is False
    assert isinstance(info, DeviceInfo)


def test_probe_device_with_mock_cuda(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When torch.cuda.is_available is True, desktop probe is available."""
    mock_torch = MagicMock()
    mock_torch.cuda.is_available.return_value = True
    monkeypatch.setitem(sys.modules, "torch", mock_torch)
    info = probe_device(RuntimeProfile.DESKTOP_GPU)
    assert info.available is True
    mock_torch.cuda.is_available.return_value = False
    info2 = probe_device(RuntimeProfile.DESKTOP_GPU)
    assert info2.available is False
