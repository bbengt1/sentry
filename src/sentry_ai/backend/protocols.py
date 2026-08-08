"""InferenceBackend Protocol and light DeviceInfo probe (EDGE-02).

probe_device is advisory only: never raises, never hard-fails serve.
Optional torch.cuda check when torch is importable.
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
    """Light advisory device probe — never raises; never hard-fails serve.

    - Resolves default backend/device_id from profile when omitted.
    - If torch is importable: desktop-gpu/jetson use ``torch.cuda.is_available()``;
      cpu-fallback reports available=True (CPU always usable for live path).
    - If torch is missing: available=False without hard-importing torch.
    """
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

    available = False
    try:
        if profile == RuntimeProfile.CPU_FALLBACK:
            # CPU path is always usable for live PyTorch/ORT-export policy.
            available = True
        else:
            try:
                import torch  # local import — avoid module-level torch

                available = bool(torch.cuda.is_available())
            except ImportError:
                available = False
            except Exception:  # noqa: BLE001 — probe must never raise
                available = False
    except Exception:  # noqa: BLE001 — absolute never-raise guarantee
        available = False

    return DeviceInfo(
        profile=profile,
        backend=resolved_backend,
        device_id=resolved_id,
        available=available,
    )
