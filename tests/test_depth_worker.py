"""DEPTH-01: DepthAnythingWorker with injectable fake model (no HF download)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

from sentry_ai.models.depth.worker import DepthAnythingWorker, DepthResult
from sentry_ai.plugins.protocols import ModelWorker
from sentry_ai.schemas.enums import DepthKind

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame


class FakeProcessor:
    """Minimal HF AutoImageProcessor stand-in."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, *, images: Any, return_tensors: str = "pt") -> dict[str, Any]:
        self.calls.append({"images": images, "return_tensors": return_tensors})
        # Shape is ignored by FakeModel; return a simple marker.
        return {"pixel_values": "fake-pixels"}


class FakeModel:
    """Returns fixed HxW predicted_depth from input frame size via side channel."""

    def __init__(self, value: float = 1.5) -> None:
        self.value = value
        self.calls: list[Any] = []
        self._last_hw: tuple[int, int] | None = None

    def set_hw(self, h: int, w: int) -> None:
        self._last_hw = (h, w)

    def __call__(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        h, w = self._last_hw or (48, 64)
        from types import SimpleNamespace

        depth = np.full((h, w), self.value, dtype=np.float32)
        return SimpleNamespace(predicted_depth=depth)


def test_worker_name_and_protocol() -> None:
    worker = DepthAnythingWorker(model=FakeModel(), processor=FakeProcessor())
    assert worker.name == "depth-anything-v2-small"
    assert isinstance(worker, ModelWorker)


def test_process_relative_returns_depth_map(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel(value=2.0)
    processor = FakeProcessor()
    worker = DepthAnythingWorker(
        model=model,
        processor=processor,
        depth_mode="relative",
    )
    frame = image_frame_factory(frame_id=1, width=32, height=24)
    model.set_hw(24, 32)
    result = worker.process(frame)
    assert isinstance(result, DepthResult)
    assert result.kind == DepthKind.RELATIVE
    assert result.unit is None
    assert result.depth_map is not None
    assert result.depth_map.shape == (24, 32)
    assert result.width == 32
    assert result.height == 24
    assert float(result.depth_map.mean()) == pytest.approx(2.0)
    assert len(processor.calls) == 1
    assert len(model.calls) == 1


def test_process_metric_indoor_kind_and_unit(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel(value=1.0)
    worker = DepthAnythingWorker(
        model=model,
        processor=FakeProcessor(),
        depth_mode="metric_indoor",
    )
    frame = image_frame_factory(frame_id=2, width=16, height=12)
    model.set_hw(12, 16)
    result = worker.process(frame)
    assert result.kind == DepthKind.METRIC_ESTIMATED
    assert result.unit == "m"


def test_process_missing_image_bgr_safe() -> None:
    from types import SimpleNamespace

    worker = DepthAnythingWorker(model=FakeModel(), processor=FakeProcessor())
    frame = SimpleNamespace(image_bgr=None, frame_id=0)
    result = worker.process(frame)
    assert isinstance(result, DepthResult)
    assert result.depth_map is None
    assert result.error is not None
    assert result.kind == DepthKind.RELATIVE
    assert result.unit is None


def test_invalid_depth_mode_raises() -> None:
    with pytest.raises(ValueError, match="unknown depth_mode|depth_mode"):
        DepthAnythingWorker(
            model=FakeModel(),
            processor=FakeProcessor(),
            depth_mode="base-large",
        )


def test_set_get_depth_mode(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = DepthAnythingWorker(
        model=model,
        processor=FakeProcessor(),
        depth_mode="relative",
    )
    assert worker.get_depth_mode() == "relative"
    worker.set_depth_mode("metric_outdoor")
    assert worker.get_depth_mode() == "metric_outdoor"
    frame = image_frame_factory(frame_id=3, width=8, height=8)
    model.set_hw(8, 8)
    result = worker.process(frame)
    assert result.kind == DepthKind.METRIC_ESTIMATED
    assert result.unit == "m"


def test_default_model_id_is_small_relative() -> None:
    worker = DepthAnythingWorker(model=FakeModel(), processor=FakeProcessor())
    assert "Small" in worker.model_id
    assert "Base" not in worker.model_id
    assert "Large" not in worker.model_id


def test_process_does_not_open_camera() -> None:
    import sentry_ai.models.depth.worker as mod

    source = inspect.getsource(mod)
    assert "VideoCapture" not in source
    assert "source.read" not in source


def test_import_error_message_mentions_extra_depth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker = DepthAnythingWorker(depth_mode="relative")
    # Force real load path with no injected model.
    assert worker._model is None

    import builtins

    real_import = builtins.__import__

    def fake_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "transformers" or name.startswith("transformers."):
            raise ImportError("no transformers")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(ImportError, match="extra depth|--extra depth"):
        worker._ensure_model()
