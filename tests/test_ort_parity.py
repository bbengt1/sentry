"""ORT-02 / ORT-04: live ORT factory path Detection parity via mocks only.

Proves schema-identical detections + runtime conf on the factory live ORT
branch without Jetson, GPU ORT, or real YOLO("*.onnx") loads in default CI.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any

import pytest

from sentry_ai.config.load import load_config
from sentry_ai.config.profile_runtime import profile_runtime
from sentry_ai.models.detection import factory as factory_mod
from sentry_ai.models.detection.factory import WorkerBuild, build_detection_worker
from sentry_ai.schemas.perception import Detection

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame


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


class FakeModel:
    """Records predict kwargs; returns configurable Results-like payloads."""

    def __init__(self, results: list[Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self._results = results

    def predict(self, **kwargs: Any) -> list[Any]:
        self.calls.append(kwargs)
        if self._results is not None:
            return self._results
        boxes = _FakeBoxes(
            xyxy=[[10.0, 20.0, 30.0, 40.0]],
            conf=[0.88],
            cls=[0],
        )
        return [SimpleNamespace(boxes=boxes, names={0: "person"})]


def _live_ort_build(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    model: FakeModel,
    *,
    conf: float = 0.25,
) -> WorkerBuild:
    """Factory live ORT path: resolve mock + dep True + injectable FakeModel.

    Asserts backend_live=onnxruntime before return so soft-stub regressions
    fail loud (T-09-07).
    """
    onnx_path = tmp_path / "yolo26n.onnx"
    onnx_path.write_bytes(b"fake-onnx")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (onnx_path, None),
    )
    monkeypatch.setattr(factory_mod, "_onnxruntime_available", lambda: True)

    rt = profile_runtime(load_config(profile="cpu-fallback"))
    build = build_detection_worker(rt, conf=conf, model=model)

    assert build.backend_live == "onnxruntime", (
        f"expected live ORT path, got live={build.backend_live!r} "
        f"reason={build.backend_reason!r}"
    )
    assert build.backend_requested == "onnxruntime"
    assert build.backend_reason is None
    assert str(build.worker._weights).endswith(".onnx")
    assert not str(build.worker._weights).endswith(".pt")
    return build


def test_ort_process_detection_contract(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """Known box via FakeModel → Detection fields + source=fixed (ORT-02)."""
    model = FakeModel()
    build = _live_ort_build(monkeypatch, tmp_path, model, conf=0.25)
    frame = image_frame_factory(frame_id=1)

    dets = build.worker.process(frame)

    assert isinstance(dets, list)
    assert len(dets) == 1
    assert isinstance(dets[0], Detection)
    assert dets[0].class_name == "person"
    assert dets[0].confidence == pytest.approx(0.88)
    assert dets[0].bbox_xyxy == (10.0, 20.0, 30.0, 40.0)
    assert dets[0].source == "fixed"
    assert len(model.calls) == 1
    call = model.calls[0]
    assert call["source"] is frame.image_bgr
    assert call["conf"] == pytest.approx(0.25)
    assert call["verbose"] is False


def test_ort_set_conf_applies_on_next_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """set_conf on ORT-path worker is reflected in next predict conf kwarg."""
    model = FakeModel()
    build = _live_ort_build(monkeypatch, tmp_path, model, conf=0.25)
    frame = image_frame_factory(frame_id=2)

    build.worker.set_conf(0.5)
    build.worker.process(frame)

    assert model.calls[-1]["conf"] == pytest.approx(0.5)
    assert build.worker.get_conf() == pytest.approx(0.5)


def test_ort_empty_predict_returns_empty_list(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """Empty predict results yield [] (not None) on ORT factory path."""
    empty = SimpleNamespace(boxes=_FakeBoxes([], [], []), names={})
    model = FakeModel(results=[empty])
    build = _live_ort_build(monkeypatch, tmp_path, model)

    dets = build.worker.process(image_frame_factory(frame_id=0))

    assert dets == []
    assert isinstance(dets, list)


def test_ort_live_weights_are_onnx_not_pt(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Honesty guard: live=onnxruntime always pairs with .onnx weights."""
    model = FakeModel()
    build = _live_ort_build(monkeypatch, tmp_path, model)
    assert build.backend_live == "onnxruntime"
    assert str(build.worker._weights).endswith(".onnx")
    assert not str(build.worker._weights).endswith(".pt")
