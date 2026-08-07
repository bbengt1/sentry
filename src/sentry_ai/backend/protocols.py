"""InferenceBackend Protocol and DeviceInfo stubs.

Phase 1: no real CUDA/torch probing — probe_device always reports unavailable.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict

from sentry_ai.schemas.enums import BackendName, RuntimeProfile


@runtime_checkable
class InferenceBackend(Protocol):
    """Minimal inference device abstraction used by later model workers."""

    name: BackendName

    def load(self) -> None: ...

    def infer(self, tensor: Any) -> Any: ...

    def close(self) -> None: ...


class DeviceInfo(BaseModel):
    """Advisory device probe result (not a hard requirement at runtime)."""

    model_config = ConfigDict(extra="forbid")

    profile: RuntimeProfile
    backend: BackendName
    device_id: str
    available: bool = False


def probe_device(
    profile: RuntimeProfile,
    *,
    backend: BackendName | None = None,
    device_id: str | None = None,
) -> DeviceInfo:
    """Stub device probe — never touches CUDA/torch; always available=False."""
    resolved_backend = backend
    resolved_id = device_id
    if resolved_backend is None or resolved_id is None:
        if profile == RuntimeProfile.DESKTOP_GPU:
            resolved_backend = resolved_backend or BackendName.TORCH
            resolved_id = resolved_id or "cuda:0"
        elif profile == RuntimeProfile.JETSON:
            resolved_backend = resolved_backend or BackendName.TENSORRT
            resolved_id = resolved_id or "0"
        else:
            resolved_backend = resolved_backend or BackendName.CPU
            resolved_id = resolved_id or "cpu"

    return DeviceInfo(
        profile=profile,
        backend=resolved_backend,
        device_id=resolved_id,
        available=False,
    )
