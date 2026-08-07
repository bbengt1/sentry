"""FOUND-06: Device/backend abstraction protocol stubs."""

from __future__ import annotations

import sys

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


def test_probe_device_stub_returns_unavailable() -> None:
    info = probe_device(RuntimeProfile.DESKTOP_GPU)
    assert isinstance(info, DeviceInfo)
    assert info.available is False
    assert info.profile == RuntimeProfile.DESKTOP_GPU
