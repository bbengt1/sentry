"""Device/backend abstraction stubs (FOUND-06)."""

from __future__ import annotations

from sentry_ai.backend.null import NullBackend
from sentry_ai.backend.protocols import DeviceInfo, InferenceBackend, probe_device

__all__ = [
    "DeviceInfo",
    "InferenceBackend",
    "NullBackend",
    "probe_device",
]
