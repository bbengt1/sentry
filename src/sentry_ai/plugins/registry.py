"""Hybrid plugin registry: in-tree register + entry-point discovery.

Discovery uses ``importlib.metadata.entry_points`` for groups
``sentry_ai.sources``, ``sentry_ai.workers``, and ``sentry_ai.sinks``.

When an entry point re-declares a name already registered (e.g. builtins),
it is **skipped** (skip-if-present) so ``discover()`` is idempotent with
``register_builtins``.
"""

from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any


class PluginRegistry:
    """Register and discover camera sources, model workers, and sinks."""

    def __init__(self) -> None:
        self._sources: dict[str, type] = {}
        self._workers: dict[str, type] = {}
        self._sinks: dict[str, type] = {}

    # --- sources -----------------------------------------------------------

    def register_source(self, name: str, cls: type) -> None:
        if name in self._sources:
            raise ValueError(f"duplicate source plugin: {name}")
        self._sources[name] = cls

    def get_source(self, name: str) -> type:
        return self._sources[name]

    def list_sources(self) -> list[str]:
        return sorted(self._sources)

    # --- workers -----------------------------------------------------------

    def register_worker(self, name: str, cls: type) -> None:
        if name in self._workers:
            raise ValueError(f"duplicate worker plugin: {name}")
        self._workers[name] = cls

    def get_worker(self, name: str) -> type:
        return self._workers[name]

    def list_workers(self) -> list[str]:
        return sorted(self._workers)

    # --- sinks -------------------------------------------------------------

    def register_sink(self, name: str, cls: type) -> None:
        if name in self._sinks:
            raise ValueError(f"duplicate sink plugin: {name}")
        self._sinks[name] = cls

    def get_sink(self, name: str) -> type:
        return self._sinks[name]

    def list_sinks(self) -> list[str]:
        return sorted(self._sinks)

    # --- discovery ---------------------------------------------------------

    def discover(self) -> None:
        """Load entry points; skip names already registered (idempotent)."""
        self._discover_group("sentry_ai.sources", self._sources)
        self._discover_group("sentry_ai.workers", self._workers)
        self._discover_group("sentry_ai.sinks", self._sinks)

    def _discover_group(self, group: str, target: dict[str, type]) -> None:
        # Python 3.11+: entry_points().select(group=...) or entry_points(group=...)
        try:
            eps = entry_points(group=group)
        except TypeError:  # pragma: no cover - older API fallback
            eps = entry_points().select(group=group)
        for ep in eps:
            if ep.name in target:
                # Skip-if-present: avoid re-loading builtins via entry points.
                continue
            loaded: Any = ep.load()
            target[ep.name] = loaded


def register_builtins(registry: PluginRegistry) -> None:
    """Register in-tree sources/workers/sinks without requiring entry points."""
    from sentry_ai.plugins.builtins import (
        NoopWorker,
        NullSink,
        SyntheticSource,
        VoiceNullSink,
    )
    from sentry_ai.sources.opencv_source import FileSource, RtspSource, UsbSource

    # Manual register raises on duplicate; only register if missing so this
    # helper is also safe to call after discover().
    if "synthetic" not in registry.list_sources():
        registry.register_source("synthetic", SyntheticSource)
    if "usb" not in registry.list_sources():
        registry.register_source("usb", UsbSource)
    if "file" not in registry.list_sources():
        registry.register_source("file", FileSource)
    if "rtsp" not in registry.list_sources():
        registry.register_source("rtsp", RtspSource)
    if "noop" not in registry.list_workers():
        registry.register_worker("noop", NoopWorker)
    # yolo-fixed: only when import succeeds (graceful without detect extra).
    if "yolo-fixed" not in registry.list_workers():
        try:
            from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
        except ImportError:
            pass
        else:
            registry.register_worker("yolo-fixed", YoloDetectionWorker)
    # depth-anything-v2-small: class import is light; torch only on real load.
    if "depth-anything-v2-small" not in registry.list_workers():
        try:
            from sentry_ai.models.depth.worker import DepthAnythingWorker
        except ImportError:
            pass
        else:
            registry.register_worker(
                "depth-anything-v2-small",
                DepthAnythingWorker,
            )
    if "null" not in registry.list_sinks():
        registry.register_sink("null", NullSink)
    # EDGE-04: voice extension point (no ASR/TTS). ROS2 bridge is intentionally
    # NOT auto-registered — import from sentry_ai.extensions.ros2.bridge instead.
    if "voice-null" not in registry.list_sinks():
        registry.register_sink("voice-null", VoiceNullSink)
