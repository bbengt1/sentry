"""UI-03: loop enable gates skip compute without thread teardown."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import numpy as np

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.control.pipeline_state import PipelineState
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.models.detection.loop import DetectionLoop
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection
from sentry_ai.spatial.free_space import DEFAULT_MID_CUT, DEFAULT_NEAR_CUT
from sentry_ai.spatial.loop import FreeSpaceLoop
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
    name: str = "fake-det"

    def __init__(self, conf: float = 0.25) -> None:
        self._conf = conf
        self.process_calls = 0

    def get_conf(self) -> float:
        return self._conf

    def process(self, frame: Any) -> list[Detection]:
        self.process_calls += 1
        return [
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
            )
        ]


@dataclass
class FakeDepthResult:
    depth_map: Any
    kind: DepthKind = DepthKind.RELATIVE
    unit: str | None = None
    width: int = 4
    height: int = 4
    error: str | None = None


class FakeDepthWorker:
    name: str = "fake-depth"

    def __init__(self) -> None:
        self.process_calls = 0

    def get_depth_mode(self) -> str:
        return "relative"

    def process(self, frame: Any) -> FakeDepthResult:
        self.process_calls += 1
        h, w = 4, 4
        return FakeDepthResult(
            depth_map=np.ones((h, w), dtype=np.float32),
            width=w,
            height=h,
        )


def _synthetic_depth(h: int = 120, w: int = 160) -> np.ndarray:
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5
    return depth


def _set_depth(store: PerceptionStore, frame_id: int) -> None:
    store.set_depth(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=float(frame_id),
        depth_map=_synthetic_depth(),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )


# ---------------------------------------------------------------------------
# PipelineState
# ---------------------------------------------------------------------------


def test_pipeline_state_defaults() -> None:
    state = PipelineState()
    snap = state.snapshot()
    assert snap["detection_enabled"] is True
    assert snap["depth_enabled"] is True
    assert snap["free_space_enabled"] is True
    assert snap["near_cut"] == DEFAULT_NEAR_CUT
    assert snap["mid_cut"] == DEFAULT_MID_CUT


def test_pipeline_state_partial_update() -> None:
    state = PipelineState()
    snap = state.update(detection_enabled=False, near_cut=0.8)
    assert snap["detection_enabled"] is False
    assert snap["depth_enabled"] is True
    assert snap["free_space_enabled"] is True
    assert snap["near_cut"] == 0.8
    assert snap["mid_cut"] == DEFAULT_MID_CUT


def test_pipeline_state_rejects_near_le_mid() -> None:
    state = PipelineState()
    try:
        state.update(near_cut=0.3, mid_cut=0.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Original values preserved
    snap = state.snapshot()
    assert snap["near_cut"] == DEFAULT_NEAR_CUT
    assert snap["mid_cut"] == DEFAULT_MID_CUT


def test_pipeline_state_rejects_cut_out_of_range() -> None:
    state = PipelineState()
    try:
        state.update(near_cut=1.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass


# ---------------------------------------------------------------------------
# Store clear_*
# ---------------------------------------------------------------------------


def test_clear_detections_sets_none() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="c",
        t_capture=0.0,
        detections=[],
        latency_ms=1.0,
    )
    assert store.snapshot() is not None
    store.clear_detections()
    assert store.snapshot() is None
    # FPS counters not reset
    assert store.metrics_snapshot().det_frames == 1


def test_clear_depth_and_free_space() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=1,
        camera_id="c",
        t_capture=0.0,
        depth_map=np.ones((4, 4), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )
    store.set_free_space(
        frame_id=1,
        camera_id="c",
        t_capture=0.0,
        latency_ms=1.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
    )
    assert store.snapshot_depth() is not None
    assert store.snapshot_free_space() is not None
    store.clear_depth()
    store.clear_free_space()
    assert store.snapshot_depth() is None
    assert store.snapshot_free_space() is None


# ---------------------------------------------------------------------------
# DetectionLoop enable gate
# ---------------------------------------------------------------------------


def test_detection_loop_skips_process_when_disabled(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDetectionWorker()
    loop = DetectionLoop(bus, worker, store)
    assert loop.is_enabled() is True
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(lambda: worker.process_calls >= 1, timeout=2.0)
        assert store.snapshot() is not None

        loop.set_enabled(False)
        assert loop.is_enabled() is False
        assert store.snapshot() is None  # cleared on disable
        calls_after_disable = worker.process_calls

        bus.publish(image_frame_factory(frame_id=2))
        time.sleep(0.08)
        assert worker.process_calls == calls_after_disable
        assert store.snapshot() is None

        # Thread still alive
        assert loop._thread is not None and loop._thread.is_alive()

        loop.set_enabled(True)
        bus.publish(image_frame_factory(frame_id=3))
        assert _wait_until(
            lambda: worker.process_calls > calls_after_disable,
            timeout=2.0,
        )
        assert store.snapshot() is not None
        assert store.snapshot().frame_id == 3  # type: ignore[union-attr]
    finally:
        loop.stop()


# ---------------------------------------------------------------------------
# DepthLoop enable gate
# ---------------------------------------------------------------------------


def test_depth_loop_skips_process_when_disabled(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker()
    loop = DepthLoop(bus, worker, store)
    assert loop.is_enabled() is True
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(lambda: worker.process_calls >= 1, timeout=2.0)
        assert store.snapshot_depth() is not None

        loop.set_enabled(False)
        assert store.snapshot_depth() is None
        calls_after = worker.process_calls
        bus.publish(image_frame_factory(frame_id=2))
        time.sleep(0.08)
        assert worker.process_calls == calls_after

        loop.set_enabled(True)
        bus.publish(image_frame_factory(frame_id=3))
        assert _wait_until(lambda: worker.process_calls > calls_after, timeout=2.0)
        assert store.snapshot_depth() is not None
    finally:
        loop.stop()


class DepFailDepthWorker:
    """Returns a missing-transformers error product (no raise)."""

    name: str = "dep-fail-depth"
    process_calls = 0

    def get_depth_mode(self) -> str:
        return "relative"

    def process(self, frame: Any) -> FakeDepthResult:
        DepFailDepthWorker.process_calls += 1
        self.process_calls = DepFailDepthWorker.process_calls
        return FakeDepthResult(
            depth_map=None,
            error=(
                "transformers is required for DepthAnythingWorker. "
                "Install the depth extra: uv sync --extra depth"
            ),
        )


def test_depth_loop_sticky_pause_on_missing_transformers(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """Missing depth extra pauses the loop after one soft failure (no spam)."""
    DepFailDepthWorker.process_calls = 0
    bus = FrameBus()
    store = PerceptionStore()
    worker = DepFailDepthWorker()
    loop = DepthLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1))
        assert _wait_until(lambda: worker.process_calls >= 1, timeout=2.0)
        assert _wait_until(lambda: not loop.is_enabled(), timeout=2.0)
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.error is not None
        assert "transformers" in snap.error.lower() or "depth extra" in snap.error

        calls_after = worker.process_calls
        bus.publish(image_frame_factory(frame_id=2))
        bus.publish(image_frame_factory(frame_id=3))
        time.sleep(0.1)
        # Sticky pause: no more process calls after dep failure.
        assert worker.process_calls == calls_after
    finally:
        loop.stop()


# ---------------------------------------------------------------------------
# FreeSpaceLoop enable gate
# ---------------------------------------------------------------------------


def test_free_space_loop_skips_compute_when_disabled() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    assert loop.is_enabled() is True
    try:
        loop.start()
        _set_depth(store, 1)
        assert _wait_until(
            lambda: store.snapshot_free_space() is not None, timeout=2.0
        )
        frames_before = store.metrics_snapshot().free_space_frames

        loop.set_enabled(False)
        assert store.snapshot_free_space() is None
        _set_depth(store, 2)
        time.sleep(0.08)
        assert store.snapshot_free_space() is None
        assert store.metrics_snapshot().free_space_frames == frames_before

        loop.set_enabled(True)
        # Need a new frame_id so keep-latest processes
        _set_depth(store, 3)
        assert _wait_until(
            lambda: store.snapshot_free_space() is not None
            and store.snapshot_free_space().frame_id == 3,  # type: ignore[union-attr]
            timeout=2.0,
        )
    finally:
        loop.stop()
