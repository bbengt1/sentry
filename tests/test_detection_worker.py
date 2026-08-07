"""DET-01: YoloDetectionWorker with injectable fake model (no weights)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest

from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
from sentry_ai.plugins.protocols import ModelWorker
from sentry_ai.schemas.perception import Detection

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame


class FakeModel:
    """Records predict kwargs; returns configurable fake results."""

    def __init__(self, results: list[Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._results = results

    def predict(self, **kwargs: Any) -> list[Any]:
        self.calls.append(kwargs)
        if self._results is not None:
            return self._results
        from types import SimpleNamespace

        boxes = _FakeBoxes(
            xyxy=[[10.0, 20.0, 30.0, 40.0]],
            conf=[0.88],
            cls=[0],
        )
        return [SimpleNamespace(boxes=boxes, names={0: "person"})]


class _FakeBoxes:
    def __init__(
        self,
        xyxy: list[list[float]],
        conf: list[float],
        cls: list[int],
    ) -> None:
        self.xyxy = xyxy
        self.conf = conf
        self.cls = cls

    def __len__(self) -> int:
        return len(self.xyxy)


def test_worker_name_and_protocol() -> None:
    worker = YoloDetectionWorker(model=FakeModel())
    assert worker.name == "yolo-fixed"
    assert isinstance(worker, ModelWorker)


def test_process_returns_detections_from_fake_model(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = YoloDetectionWorker(model=model, conf=0.25)
    frame = image_frame_factory(frame_id=1)
    dets = worker.process(frame)
    assert isinstance(dets, list)
    assert len(dets) == 1
    assert isinstance(dets[0], Detection)
    assert dets[0].class_name == "person"
    assert dets[0].confidence == pytest.approx(0.88)
    assert dets[0].bbox_xyxy == (10.0, 20.0, 30.0, 40.0)
    assert len(model.calls) == 1
    call = model.calls[0]
    assert call["source"] is frame.image_bgr
    assert call["conf"] == pytest.approx(0.25)
    assert call["imgsz"] == 640
    assert call["verbose"] is False
    assert call["save"] is False


def test_set_conf_applies_on_next_process(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = YoloDetectionWorker(model=model, conf=0.25)
    frame = image_frame_factory(frame_id=2)
    worker.set_conf(0.5)
    worker.process(frame)
    assert model.calls[-1]["conf"] == pytest.approx(0.5)
    assert worker.get_conf() == pytest.approx(0.5)


def test_set_conf_out_of_range_raises() -> None:
    worker = YoloDetectionWorker(model=FakeModel())
    with pytest.raises(ValueError, match="conf"):
        worker.set_conf(-0.1)
    with pytest.raises(ValueError, match="conf"):
        worker.set_conf(1.01)
    worker.set_conf(0.0)
    worker.set_conf(1.0)


def test_empty_predict_returns_empty_list(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    from types import SimpleNamespace

    empty = SimpleNamespace(boxes=_FakeBoxes([], [], []), names={})
    model = FakeModel(results=[empty])
    worker = YoloDetectionWorker(model=model)
    dets = worker.process(image_frame_factory(frame_id=0))
    assert dets == []


def test_process_does_not_open_camera() -> None:
    """Worker must only use frame.image_bgr — no VideoCapture."""
    import sentry_ai.models.detection.yolo_worker as mod

    source = inspect.getsource(mod)
    assert "VideoCapture" not in source
    assert "source.read" not in source
