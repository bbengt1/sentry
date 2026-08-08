"""DEPTH-01: DepthLoop FrameBus subscriber (no camera ownership)."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.models.depth import loop as loop_mod
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.models.depth.worker import DepthResult
from sentry_ai.schemas.enums import DepthKind
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


class FakeDepthWorker:
    """Injectable worker for loop tests (no HF)."""

    name: str = "fake-depth"

    def __init__(self, *, raise_once: bool = False, value: float = 1.0) -> None:
        self._raise_once = raise_once
        self._value = value
        self.process_calls = 0
        self.seen_frame_ids: list[int] = []

    def process(self, frame: Any) -> DepthResult:
        self.process_calls += 1
        self.seen_frame_ids.append(frame.frame_id)
        if self._raise_once:
            self._raise_once = False
            raise RuntimeError("simulated depth failure")
        image = getattr(frame, "image_bgr", None)
        if image is None:
            h, w = 48, 64
        else:
            h, w = int(image.shape[0]), int(image.shape[1])
        return DepthResult(
            depth_map=np.full((h, w), self._value, dtype=np.float32),
            kind=DepthKind.RELATIVE,
            unit=None,
            width=w,
            height=h,
        )


def test_loop_processes_published_frame_into_store(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker()
    loop = DepthLoop(bus, worker, store)
    try:
        loop.start()
        frame = image_frame_factory(frame_id=7, camera_id="camA")
        bus.publish(frame)
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.frame_id == 7,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.frame_id == 7
        assert snap.camera_id == "camA"
        assert snap.kind == DepthKind.RELATIVE
        assert snap.unit is None
        assert snap.depth_map is not None
        assert snap.latency_ms >= 0.0
        assert snap.model_name == "fake-depth"
        assert snap.error is None
        assert worker.process_calls >= 1
    finally:
        loop.stop()


def test_loop_skips_same_frame_id(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker()
    loop = DepthLoop(bus, worker, store)
    try:
        loop.start()
        frame = image_frame_factory(frame_id=1)
        bus.publish(frame)
        assert _wait_until(lambda: store.snapshot_depth() is not None, timeout=2.0)
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
    worker = FakeDepthWorker()
    loop = DepthLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.frame_id == 1,
            timeout=2.0,
        )
        bus.publish(image_frame_factory(frame_id=2))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.frame_id == 2,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
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
    worker = FakeDepthWorker(raise_once=True)
    loop = DepthLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(lambda: worker.process_calls >= 1, timeout=2.0)
        # Error product for frame 1
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None
            and s.frame_id == 1
            and s.error is not None,
            timeout=2.0,
        )
        bus.publish(image_frame_factory(frame_id=2))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None
            and s.frame_id == 2
            and s.error is None,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.frame_id == 2
        assert snap.error is None
    finally:
        loop.stop()


def test_loop_start_stop_idempotent() -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker()
    loop = DepthLoop(bus, worker, store)
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
