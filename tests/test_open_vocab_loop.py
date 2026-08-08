"""OVD-02: OpenVocabLoop modes (off / on_demand / continuous)."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.models.detection import open_vocab_loop as ov_mod
from sentry_ai.models.detection.loop import DetectionLoop
from sentry_ai.models.detection.open_vocab_loop import OpenVocabLoop
from sentry_ai.schemas.perception import Detection
from sentry_ai.state.perception_store import PerceptionStore

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame


def _wait_until(
    predicate: Any,
    *,
    timeout: float = 2.0,
    interval: float = 0.01,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False


class FakeOvWorker:
    """Injectable OV worker (no YOLOE)."""

    name: str = "fake-ov"

    def __init__(
        self,
        detections: list[Detection] | None = None,
        *,
        conf: float = 0.25,
    ) -> None:
        self._detections = (
            detections
            if detections is not None
            else [
                Detection(
                    class_name="cup",
                    confidence=0.8,
                    bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
                    source="open_vocab",
                )
            ]
        )
        self._conf = conf
        self._classes: list[str] = []
        self.process_calls = 0
        self.seen_frame_ids: list[int] = []

    def get_conf(self) -> float:
        return self._conf

    def set_conf(self, conf: float) -> None:
        self._conf = conf

    def set_prompt_classes(self, classes: list[str]) -> None:
        self._classes = list(classes)

    def get_prompt_classes(self) -> list[str]:
        return list(self._classes)

    def process(self, frame: Any) -> list[Detection]:
        self.process_calls += 1
        self.seen_frame_ids.append(frame.frame_id)
        return list(self._detections)


class FakeDetWorker:
    name = "fake-det"

    def __init__(self) -> None:
        self.process_calls = 0
        self._conf = 0.25

    def get_conf(self) -> float:
        return self._conf

    def process(self, frame: Any) -> list[Detection]:
        self.process_calls += 1
        return [
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
            )
        ]


def test_default_mode_off_no_process(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeOvWorker()
    loop = OpenVocabLoop(bus, worker, store)
    assert loop.get_mode() == "off"
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        time.sleep(0.08)
        assert worker.process_calls == 0
        assert store.snapshot_open_vocab() is None
    finally:
        loop.stop()


def test_on_demand_processes_exactly_one(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeOvWorker()
    worker.set_prompt_classes(["cup"])
    loop = OpenVocabLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=5, camera_id="camA"))
        time.sleep(0.03)
        assert worker.process_calls == 0
        loop.arm()
        assert _wait_until(lambda: worker.process_calls >= 1, timeout=2.0)
        assert _wait_until(
            lambda: (s := store.snapshot_open_vocab()) is not None
            and s.frame_id == 5,
            timeout=2.0,
        )
        calls = worker.process_calls
        time.sleep(0.05)
        # No re-process without re-arm.
        assert worker.process_calls == calls
        snap = store.snapshot_open_vocab()
        assert snap is not None
        assert snap.detections[0].source == "open_vocab"
        assert snap.model_name == "fake-ov"
        # Never wrote fixed detections slot.
        assert store.snapshot() is None
    finally:
        loop.stop()


def test_continuous_every_n(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeOvWorker()
    loop = OpenVocabLoop(bus, worker, store, every_n=3)
    loop.set_mode("continuous")
    try:
        loop.start()
        for fid in (1, 2, 3, 4, 5, 6):
            bus.publish(image_frame_factory(frame_id=fid))
            time.sleep(0.02)
        assert _wait_until(lambda: worker.process_calls >= 2, timeout=2.0)
        # every_n=3 → roughly frames 3 and 6 (2 calls for 6 frames)
        assert worker.process_calls <= 3
        assert store.snapshot() is None  # never dual-write
        assert store.snapshot_open_vocab() is not None
    finally:
        loop.stop()


def test_fixed_detection_loop_independent(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """OV running must not block or write into fixed DetectionLoop path."""
    bus = FrameBus()
    store = PerceptionStore()
    det_worker = FakeDetWorker()
    ov_worker = FakeOvWorker()
    det_loop = DetectionLoop(bus, det_worker, store)
    ov_loop = OpenVocabLoop(bus, ov_worker, store)
    ov_loop.set_mode("continuous")
    ov_loop.set_every_n(1)
    try:
        det_loop.start()
        ov_loop.start()
        for fid in (1, 2, 3):
            bus.publish(image_frame_factory(frame_id=fid))
            time.sleep(0.03)
        assert _wait_until(lambda: det_worker.process_calls >= 3, timeout=2.0)
        assert _wait_until(lambda: ov_worker.process_calls >= 1, timeout=2.0)
        assert store.snapshot() is not None
        assert store.snapshot_open_vocab() is not None
        # Fixed product has fixed source; OV has open_vocab.
        assert store.snapshot().detections[0].source == "fixed"  # type: ignore[union-attr]
        assert (
            store.snapshot_open_vocab().detections[0].source == "open_vocab"  # type: ignore[union-attr]
        )
    finally:
        ov_loop.stop()
        det_loop.stop()


def test_mode_off_clears_product(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeOvWorker()
    loop = OpenVocabLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        loop.arm()
        assert _wait_until(
            lambda: store.snapshot_open_vocab() is not None, timeout=2.0
        )
        loop.set_mode("off")
        assert _wait_until(
            lambda: store.snapshot_open_vocab() is None, timeout=2.0
        )
    finally:
        loop.stop()


def test_loop_source_has_no_videocapture() -> None:
    source = inspect.getsource(ov_mod)
    assert "VideoCapture" not in source
    # Dual-writer anti-pattern: must not *call* set_detections (doc mentions ok).
    assert "set_open_vocab(" in source
    assert ".set_detections(" not in source
