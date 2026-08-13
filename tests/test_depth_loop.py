"""DEPTH-01: DepthLoop FrameBus subscriber (no camera ownership)."""

from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.models.depth import loop as loop_mod
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.models.depth.worker import DepthResult
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
)
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
            lambda: (
                (s := store.snapshot_depth()) is not None
                and s.frame_id == 1
                and s.error is not None
            ),
            timeout=2.0,
        )
        bus.publish(image_frame_factory(frame_id=2))
        assert _wait_until(
            lambda: (
                (s := store.snapshot_depth()) is not None
                and s.frame_id == 2
                and s.error is None
            ),
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


def _applied_calibration(
    *,
    scale: float,
    offset: float = 0.0,
    camera_id: str = "cam0",
    depth_mode: str = "relative",
    model_id: str = "fake-depth",
) -> CalibrationState:
    """Stage+apply valid params with fingerprint including depth_mode+model_id."""
    state = CalibrationState()
    params = CalibrationParams(
        scale=scale,
        offset=offset,
        sample_count=1,
        fingerprint=CalibrationFingerprint(
            camera_id=camera_id,
            depth_mode=depth_mode,
            model_id=model_id,
        ),
    )
    state.set_draft_params(params)
    state.apply()
    return state


def test_loop_without_calibration_keeps_relative_raw(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """calibration=None (default) preserves pre-Phase-14 relative behavior."""
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker(value=2.0)
    loop = DepthLoop(bus, worker, store)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=11, camera_id="cam0"))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.frame_id == 11,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.kind == DepthKind.RELATIVE
        assert snap.unit is None
        assert snap.depth_map is not None
        assert float(np.mean(snap.depth_map)) == pytest.approx(2.0)
        assert snap.error is None
    finally:
        loop.stop()


def test_loop_inactive_calibration_keeps_relative_raw(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker(value=2.0)
    calib = CalibrationState()
    loop = DepthLoop(bus, worker, store, calibration=calib)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=12, camera_id="cam0"))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.frame_id == 12,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.kind == DepthKind.RELATIVE
        assert snap.unit is None
        assert snap.depth_map is not None
        assert float(np.mean(snap.depth_map)) == pytest.approx(2.0)
        assert snap.error is None
    finally:
        loop.stop()


def test_loop_applies_calibration_scale_and_promotes(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker(value=2.0)
    calib = _applied_calibration(scale=3.0, offset=0.0)
    loop = DepthLoop(bus, worker, store, calibration=calib)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=13, camera_id="cam0"))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.frame_id == 13,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.kind == DepthKind.METRIC_CALIBRATED
        assert snap.unit == "m"
        assert snap.depth_map is not None
        assert snap.depth_map.dtype == np.float32
        assert float(np.mean(snap.depth_map)) == pytest.approx(6.0)
        assert snap.error is None
    finally:
        loop.stop()


def test_loop_error_path_does_not_invent_calibrated_meters(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    """Exception products keep base kind/unit even when calibration is applied."""
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker(raise_once=True)
    calib = _applied_calibration(scale=3.0, offset=0.0)
    loop = DepthLoop(bus, worker, store, calibration=calib)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1, camera_id="cam0"))
        assert _wait_until(
            lambda: (
                (s := store.snapshot_depth()) is not None
                and s.frame_id == 1
                and s.error is not None
            ),
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.kind == DepthKind.RELATIVE
        assert snap.unit is None
        assert snap.depth_map is None
        assert snap.error is not None
    finally:
        loop.stop()


class _DepFailDepthWorker:
    """Soft missing-transformers error product (dependency path)."""

    name: str = "dep-fail-depth"
    process_calls = 0

    def get_depth_mode(self) -> str:
        return "relative"

    def process(self, frame: Any) -> DepthResult:
        _DepFailDepthWorker.process_calls += 1
        self.process_calls = _DepFailDepthWorker.process_calls
        return DepthResult(
            depth_map=None,
            kind=DepthKind.RELATIVE,
            unit=None,
            error=(
                "transformers is required for DepthAnythingWorker. "
                "Install the depth extra: uv sync --extra depth"
            ),
        )


def test_loop_dependency_failure_does_not_invent_calibrated_meters(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    _DepFailDepthWorker.process_calls = 0
    bus = FrameBus()
    store = PerceptionStore()
    worker = _DepFailDepthWorker()
    calib = _applied_calibration(scale=3.0, offset=0.0)
    loop = DepthLoop(bus, worker, store, calibration=calib)
    try:
        loop.start()
        bus.publish(image_frame_factory(frame_id=1, camera_id="cam0"))
        assert _wait_until(
            lambda: (s := store.snapshot_depth()) is not None and s.error is not None,
            timeout=2.0,
        )
        snap = store.snapshot_depth()
        assert snap is not None
        assert snap.kind == DepthKind.RELATIVE
        assert snap.unit is None
        assert snap.depth_map is None
        assert snap.error is not None
    finally:
        loop.stop()


def test_loop_single_apply_site() -> None:
    """T-14-02: promote + apply_map together; one apply_map call site."""
    source = inspect.getsource(loop_mod)
    assert "promote_kind_unit" in source
    assert "apply_map" in source
    assert source.count("apply_map(") == 1
    assert source.count("promote_kind_unit(") == 1
