"""DET-01: DetectionLoop FrameBus subscriber (no camera ownership)."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.models.detection import loop as loop_mod
from sentry_ai.models.detection.loop import DetectionLoop
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


class FakeDetectionWorker:
    """Injectable worker for loop tests (no YOLO)."""

    name: str = "fake-det"

    def __init__(
        self,
        detections: list[Detection] | None = None,
        *,
        conf: float = 0.25,
        raise_once: bool = False,
    ) -> None:
        self._detections = (
            detections
            if detections is not None
            else [
                Detection(
                    class_name="person",
                    confidence=0.9,
                    bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
                )
            ]
        )
        self._conf = conf
        self._raise_once = raise_once
        self.process_calls = 0
        self.seen_frame_ids: list[int] = []

    def get_conf(self) -> float:
        return self._conf

    def process(self, frame: Any) -> list[Detection]:
        self.process_calls += 1
        self.seen_frame_ids.append(frame.frame_id)
        if self._raise_once:
            self._raise_once = False
            raise RuntimeError("simulated predict failure")
        return list(self._detections)


def test_loop_processes_published_frame_into_store(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDetectionWorker()
    loop = DetectionLoop(bus, worker, store)
    try:
        loop.start()
        frame = image_frame_factory(frame_id=7, camera_id="camA")
        bus.publish(frame)
        assert _wait_until(
            lambda: (s := store.snapshot()) is not None and s.frame_id == 7,
            timeout=2.0,
        )
        snap = store.snapshot()
        assert snap is not None
        assert snap.frame_id == 7
        assert snap.camera_id == "camA"
        assert len(snap.detections) == 1
        assert snap.detections[0].class_name == "person"
        assert snap.latency_ms >= 0.0
        assert snap.conf == 0.25
        assert snap.model_name == "fake-det"
        assert worker.process_calls >= 1
    finally:
        loop.stop()


def test_loop_skips_same_frame_id(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDetectionWorker()
    loop = DetectionLoop(bus, worker, store)
    try:
        loop.start()
        frame = image_frame_factory(frame_id=1)
        bus.publish(frame)
        assert _wait_until(lambda: store.snapshot() is not None, timeout=2.0)
        calls_after_first = worker.process_calls
        time.sleep(0.05)
        assert worker.process_calls == calls_after_first
    finally:
        loop.stop()


def test_loop_newer_frame_overwrites_product(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDetectionWorker()
    loop = DetectionLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(
            lambda: (s := store.snapshot()) is not None and s.frame_id == 1,
            timeout=2.0,
        )
        bus.publish(image_frame_factory(frame_id=2))
        assert _wait_until(
            lambda: (s := store.snapshot()) is not None and s.frame_id == 2,
            timeout=2.0,
        )
        snap = store.snapshot()
        assert snap is not None
        assert snap.frame_id == 2
        assert 2 in worker.seen_frame_ids
    finally:
        loop.stop()


def test_loop_survives_worker_exception(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDetectionWorker(raise_once=True)
    loop = DetectionLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(lambda: worker.process_calls >= 1, timeout=2.0)
        bus.publish(image_frame_factory(frame_id=2))
        assert _wait_until(
            lambda: (s := store.snapshot()) is not None and s.frame_id == 2,
            timeout=2.0,
        )
        snap = store.snapshot()
        assert snap is not None
        assert snap.frame_id == 2
        assert snap.error is None
    finally:
        loop.stop()


def test_loop_start_stop_idempotent() -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDetectionWorker()
    loop = DetectionLoop(bus, worker, store)
    loop.stop()
    loop.stop()
    loop.start()
    loop.start()
    loop.stop()
    loop.stop()


def test_loop_source_has_no_videocapture() -> None:
    source = inspect.getsource(loop_mod)
    assert "VideoCapture" not in source
    assert "source.read" not in source
    assert "cv2.VideoCapture" not in source
