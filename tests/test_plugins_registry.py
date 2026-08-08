"""FOUND-04: Plugin registry stubs for sources, workers, sinks."""

from __future__ import annotations

import pytest

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.plugins.builtins import (
    NoopWorker,
    NullSink,
    SyntheticSource,
    VoiceNullSink,
)
from sentry_ai.plugins.registry import PluginRegistry, register_builtins
from sentry_ai.schemas import Frame


def test_register_builtins_lists_synthetic_noop_null() -> None:
    registry = PluginRegistry()
    register_builtins(registry)

    assert "synthetic" in registry.list_sources()
    assert "usb" in registry.list_sources()
    assert "file" in registry.list_sources()
    assert "noop" in registry.list_workers()
    assert "null" in registry.list_sinks()
    # EDGE-04: voice-null no-op sink (no ASR/TTS)
    assert "voice-null" in registry.list_sinks()
    # yolo-fixed registers when importable (no ultralytics required for class import)
    assert "yolo-fixed" in registry.list_workers()
    # depth-anything-v2-small registers when importable (torch only on real load)
    assert "depth-anything-v2-small" in registry.list_workers()


def test_get_source_synthetic_returns_class() -> None:
    registry = PluginRegistry()
    register_builtins(registry)

    source_cls = registry.get_source("synthetic")
    assert source_cls is SyntheticSource
    assert registry.get_worker("noop") is NoopWorker
    assert registry.get_sink("null") is NullSink
    assert registry.get_sink("voice-null") is VoiceNullSink


def test_synthetic_source_read_returns_valid_image_frame() -> None:
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    source.open()
    try:
        image = source.read()
        assert isinstance(image, ImageFrame)
        assert image.camera_id == "synthetic0"
        assert image.frame_id == 0

        image2 = source.read()
        assert image2.frame_id == 1
        # Round-trip meta through model_validate to prove schema validity
        Frame.model_validate(image.meta.model_dump())
    finally:
        source.close()


def test_duplicate_register_raises_value_error() -> None:
    registry = PluginRegistry()
    registry.register_source("synthetic", SyntheticSource)

    with pytest.raises(ValueError, match="duplicate source"):
        registry.register_source("synthetic", SyntheticSource)

    registry.register_worker("noop", NoopWorker)
    with pytest.raises(ValueError, match="duplicate worker"):
        registry.register_worker("noop", NoopWorker)

    registry.register_sink("null", NullSink)
    with pytest.raises(ValueError, match="duplicate sink"):
        registry.register_sink("null", NullSink)


def test_discover_is_idempotent_with_builtins() -> None:
    """discover() must not crash when builtins already registered.

    Entry-point re-declarations of builtins are skipped (skip-if-present).
    """
    registry = PluginRegistry()
    register_builtins(registry)
    registry.discover()  # should not raise
    registry.discover()  # second call still ok

    assert "synthetic" in registry.list_sources()
    assert "noop" in registry.list_workers()
    assert "yolo-fixed" in registry.list_workers()
    assert "depth-anything-v2-small" in registry.list_workers()
    assert "null" in registry.list_sinks()
    assert "voice-null" in registry.list_sinks()
    assert registry.get_sink("voice-null") is VoiceNullSink


def test_voice_null_discover_without_prior_register() -> None:
    """Entry point voice-null is discoverable when builtins not pre-registered."""
    registry = PluginRegistry()
    registry.discover()
    assert "voice-null" in registry.list_sinks()
    assert registry.get_sink("voice-null") is VoiceNullSink


def test_yolo_fixed_worker_class_from_registry() -> None:
    from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker

    registry = PluginRegistry()
    register_builtins(registry)
    assert registry.get_worker("yolo-fixed") is YoloDetectionWorker


def test_depth_worker_class_from_registry() -> None:
    from sentry_ai.models.depth.worker import DepthAnythingWorker

    registry = PluginRegistry()
    register_builtins(registry)
    assert registry.get_worker("depth-anything-v2-small") is DepthAnythingWorker


def test_noop_worker_and_null_sink_lifecycle() -> None:
    worker = NoopWorker()
    sink = NullSink()
    result = worker.process(
        Frame(frame_id=0, camera_id="synthetic0", t_capture=0.0)
    )
    assert result is None
    sink.emit({"ignored": True})
    sink.close()
