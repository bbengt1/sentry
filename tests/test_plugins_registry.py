"""FOUND-04: Plugin registry stubs for sources, workers, sinks."""

from __future__ import annotations

import pytest

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.plugins.builtins import NoopWorker, NullSink, SyntheticSource
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


def test_get_source_synthetic_returns_class() -> None:
    registry = PluginRegistry()
    register_builtins(registry)

    source_cls = registry.get_source("synthetic")
    assert source_cls is SyntheticSource
    assert registry.get_worker("noop") is NoopWorker
    assert registry.get_sink("null") is NullSink


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
    assert "null" in registry.list_sinks()


def test_noop_worker_and_null_sink_lifecycle() -> None:
    worker = NoopWorker()
    sink = NullSink()
    result = worker.process(
        Frame(frame_id=0, camera_id="synthetic0", t_capture=0.0)
    )
    assert result is None
    sink.emit({"ignored": True})
    sink.close()
