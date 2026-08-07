"""DET-02: Ultralytics Results → Detection mapping (pure, no torch)."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from sentry_ai.models.detection.mapping import results_to_detections
from sentry_ai.schemas.perception import Detection


class _FakeBoxes:
    """Minimal Boxes-like object supporting list-style access."""

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


def make_fake_yolo_result(
    *,
    boxes: _FakeBoxes | None,
    names: dict[int, str] | None = None,
) -> SimpleNamespace:
    """Build a duck-typed Ultralytics Results stand-in (no network/weights)."""
    return SimpleNamespace(
        boxes=boxes,
        names=names if names is not None else {0: "person", 1: "bicycle", 2: "car"},
    )


def test_empty_boxes_returns_empty_list() -> None:
    result = make_fake_yolo_result(boxes=_FakeBoxes([], [], []))
    assert results_to_detections(result) == []


def test_none_boxes_returns_empty_list() -> None:
    result = make_fake_yolo_result(boxes=None)
    assert results_to_detections(result) == []


def test_known_boxes_map_to_detections() -> None:
    boxes = _FakeBoxes(
        xyxy=[[10.0, 20.0, 100.5, 200.25], [1.0, 2.0, 3.0, 4.0]],
        conf=[0.91, 0.55],
        cls=[0, 2],
    )
    result = make_fake_yolo_result(
        boxes=boxes,
        names={0: "person", 2: "car"},
    )
    dets = results_to_detections(result)
    assert len(dets) == 2
    assert all(isinstance(d, Detection) for d in dets)

    assert dets[0].class_name == "person"
    assert dets[0].confidence == pytest.approx(0.91)
    assert dets[0].bbox_xyxy == (10.0, 20.0, 100.5, 200.25)

    assert dets[1].class_name == "car"
    assert dets[1].confidence == pytest.approx(0.55)
    assert dets[1].bbox_xyxy == (1.0, 2.0, 3.0, 4.0)


def test_unknown_class_id_falls_back_to_str_id() -> None:
    boxes = _FakeBoxes(
        xyxy=[[0.0, 0.0, 1.0, 1.0]],
        conf=[0.4],
        cls=[99],
    )
    result = make_fake_yolo_result(boxes=boxes, names={0: "person"})
    dets = results_to_detections(result)
    assert len(dets) == 1
    assert dets[0].class_name == "99"


def test_tensor_like_cpu_numpy_path() -> None:
    """Support objects with .cpu().numpy() (Ultralytics tensor path)."""

    class _TensorLike:
        def __init__(self, data: list) -> None:
            self._data = data

        def cpu(self) -> _TensorLike:
            return self

        def numpy(self) -> list:
            return self._data

    class Boxes:
        def __init__(self) -> None:
            self.xyxy = _TensorLike([[5.0, 6.0, 7.0, 8.0]])
            self.conf = _TensorLike([0.77])
            self.cls = _TensorLike([1])

        def __len__(self) -> int:
            return 1

    result = SimpleNamespace(boxes=Boxes(), names={1: "bicycle"})
    dets = results_to_detections(result)
    assert len(dets) == 1
    assert dets[0].class_name == "bicycle"
    assert dets[0].confidence == pytest.approx(0.77)
    assert dets[0].bbox_xyxy == (5.0, 6.0, 7.0, 8.0)
