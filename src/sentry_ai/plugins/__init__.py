"""Plugin registry, protocols, and built-in stubs (FOUND-04)."""

from __future__ import annotations

from sentry_ai.plugins.builtins import NoopWorker, NullSink, SyntheticSource
from sentry_ai.plugins.protocols import CameraSource, ModelWorker, Sink
from sentry_ai.plugins.registry import PluginRegistry, register_builtins

__all__ = [
    "CameraSource",
    "ModelWorker",
    "NoopWorker",
    "NullSink",
    "PluginRegistry",
    "Sink",
    "SyntheticSource",
    "register_builtins",
]
