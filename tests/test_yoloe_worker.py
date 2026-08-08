"""OVD-01: YoloeOpenVocabWorker with injectable fake model (no weights)."""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import pytest

from sentry_ai.models.detection.yoloe_worker import (
    DEFAULT_WEIGHTS,
    YoloeOpenVocabWorker,
)
from sentry_ai.plugins.protocols import ModelWorker
from sentry_ai.schemas.perception import Detection

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame


class FakeModel:
    """Records set_classes + predict kwargs; returns configurable results."""

    def __init__(self, results: list[Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.set_classes_calls: list[list[str]] = []
        self._results = results

    def set_classes(self, classes: list[str], embeddings: Any = None) -> None:
        self.set_classes_calls.append(list(classes))

    def predict(self, **kwargs: Any) -> list[Any]:
        self.calls.append(kwargs)
        if self._results is not None:
            return self._results
        from types import SimpleNamespace

        boxes = _FakeBoxes(
            xyxy=[[10.0, 20.0, 30.0, 40.0]],
            conf=[0.91],
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


def test_worker_name_protocol_and_default_weights() -> None:
    worker = YoloeOpenVocabWorker(model=FakeModel())
    assert worker.name == "yoloe-open-vocab"
    assert isinstance(worker, ModelWorker)
    assert DEFAULT_WEIGHTS == "yoloe-26s-seg.pt"


def test_empty_prompt_returns_empty_without_predict(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = YoloeOpenVocabWorker(model=model)
    # default empty classes
    dets = worker.process(image_frame_factory(frame_id=1))
    assert dets == []
    assert model.calls == []
    assert model.set_classes_calls == []

    worker.set_prompt_classes(["", "  ", None])  # type: ignore[list-item]
    dets = worker.process(image_frame_factory(frame_id=2))
    assert dets == []
    assert model.calls == []


def test_set_classes_called_once_when_dirty(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = YoloeOpenVocabWorker(model=model)
    worker.set_prompt_classes(["person", "red cup"])
    frame = image_frame_factory(frame_id=1)

    worker.process(frame)
    worker.process(frame)
    assert model.set_classes_calls == [["person", "red cup"]]
    assert len(model.calls) == 2

    # Change prompt → set_classes again
    worker.set_prompt_classes(["toolbox"])
    worker.process(frame)
    assert model.set_classes_calls == [["person", "red cup"], ["toolbox"]]
    assert len(model.calls) == 3


def test_process_tags_source_open_vocab(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = YoloeOpenVocabWorker(model=model)
    worker.set_prompt_classes(["person"])
    dets = worker.process(image_frame_factory(frame_id=1))
    assert len(dets) == 1
    assert isinstance(dets[0], Detection)
    assert dets[0].class_name == "person"
    assert dets[0].confidence == pytest.approx(0.91)
    assert dets[0].source == "open_vocab"
    assert dets[0].bbox_xyxy == (10.0, 20.0, 30.0, 40.0)


def test_set_conf_applies_on_next_process(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    model = FakeModel()
    worker = YoloeOpenVocabWorker(model=model, conf=0.25)
    worker.set_prompt_classes(["person"])
    frame = image_frame_factory(frame_id=2)
    worker.set_conf(0.5)
    worker.process(frame)
    assert model.calls[-1]["conf"] == pytest.approx(0.5)
    assert worker.get_conf() == pytest.approx(0.5)


def test_set_conf_out_of_range_raises() -> None:
    worker = YoloeOpenVocabWorker(model=FakeModel())
    with pytest.raises(ValueError, match="conf"):
        worker.set_conf(-0.1)
    with pytest.raises(ValueError, match="conf"):
        worker.set_conf(1.01)


def test_set_prompt_classes_strips_empties() -> None:
    worker = YoloeOpenVocabWorker(model=FakeModel())
    worker.set_prompt_classes([" person ", "", "  red cup  ", "   "])
    assert worker.get_prompt_classes() == ["person", "red cup"]


def test_detection_source_defaults_fixed() -> None:
    det = Detection(
        class_name="person",
        confidence=0.9,
        bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
    )
    assert det.source == "fixed"
    ov = Detection(
        class_name="cup",
        confidence=0.8,
        bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
        source="open_vocab",
    )
    assert ov.source == "open_vocab"


def test_process_does_not_open_camera() -> None:
    import sentry_ai.models.detection.yoloe_worker as mod

    source = inspect.getsource(mod)
    assert "VideoCapture" not in source
    assert "source.read" not in source


def test_missing_ultralytics_raises_clear_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without injected model, missing ultralytics must mention detect extra."""
    import builtins

    real_import = builtins.__import__

    def _block_ultralytics(name: str, *args: Any, **kwargs: Any) -> Any:
        if name == "ultralytics" or name.startswith("ultralytics."):
            raise ImportError("No module named ultralytics")
        return real_import(name, *args, **kwargs)

    worker = YoloeOpenVocabWorker(model=None)
    # Force unload path
    worker._model = None  # type: ignore[attr-defined]
    monkeypatch.setattr(builtins, "__import__", _block_ultralytics)
    with pytest.raises(ImportError, match="detect extra"):
        worker._ensure_model()  # type: ignore[attr-defined]
