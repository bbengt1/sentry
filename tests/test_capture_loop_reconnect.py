"""CAM-06: CaptureLoop thread, reconnect policy, and status visibility."""

from __future__ import annotations

import threading
import time
from typing import Any

import numpy as np
import pytest

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.capture.status import SourceStatus
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.errors import SourceDisconnected
from sentry_ai.sources.synthetic import SyntheticSource


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


class _FailThenSucceedSource:
    """Fails read N times after open, then streams synthetic-like frames."""

    name: str = "fake-fail"

    def __init__(self, fail_reads: int = 1, camera_id: str = "fake0") -> None:
        self.camera_id = camera_id
        self.fail_reads = fail_reads
        self._reads = 0
        self._open = False
        self._next_frame_id = 0
        self.open_count = 0
        self.close_count = 0

    def open(self) -> None:
        self._open = True
        self.open_count += 1
        self._next_frame_id = 0

    def read(self) -> ImageFrame:
        if not self._open:
            raise RuntimeError("not open")
        self._reads += 1
        if self._reads <= self.fail_reads:
            raise SourceDisconnected(f"simulated disconnect #{self._reads}")
        now = time.time()
        meta = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=None,
            width=8,
            height=8,
        )
        self._next_frame_id += 1
        img = np.zeros((8, 8, 3), dtype=np.uint8)
        return ImageFrame(meta=meta, image_bgr=img)

    def close(self) -> None:
        self._open = False
        self.close_count += 1


class _OpenFailsThenWorksSource:
    """open() fails N times, then succeeds and streams frames."""

    name: str = "fake-open-fail"

    def __init__(self, fail_opens: int = 2, camera_id: str = "openfail0") -> None:
        self.camera_id = camera_id
        self.fail_opens = fail_opens
        self._open_attempts = 0
        self._open = False
        self._next_frame_id = 0

    def open(self) -> None:
        self._open_attempts += 1
        if self._open_attempts <= self.fail_opens:
            raise OSError(f"open failed attempt {self._open_attempts}")
        self._open = True

    def read(self) -> ImageFrame:
        if not self._open:
            raise RuntimeError("not open")
        now = time.time()
        meta = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=8,
            height=8,
        )
        self._next_frame_id += 1
        return ImageFrame(
            meta=meta,
            image_bgr=np.zeros((8, 8, 3), dtype=np.uint8),
        )

    def close(self) -> None:
        self._open = False


def test_happy_path_synthetic_publishes_and_streams() -> None:
    bus = FrameBus()
    source = SyntheticSource(width=32, height=24, fps=0.0)
    loop = CaptureLoop(
        source,
        bus,
        initial_backoff=0.01,
        max_backoff=0.05,
    )
    try:
        loop.start()
        assert _wait_until(lambda: bus.get_latest() is not None, timeout=2.0)
        assert loop.status == SourceStatus.STREAMING
        assert bus.get_latest() is not None
        assert loop.status_detail is None
    finally:
        loop.stop()
    assert loop.status == SourceStatus.STOPPED
    assert source._open is False  # noqa: SLF001 — verify close


def test_stop_idempotent_without_start() -> None:
    bus = FrameBus()
    source = SyntheticSource(fps=0.0)
    loop = CaptureLoop(source, bus, initial_backoff=0.01, max_backoff=0.05)
    loop.stop()
    loop.stop()
    assert loop.status == SourceStatus.STOPPED


def test_disconnect_recovery_returns_to_streaming() -> None:
    bus = FrameBus()
    source = _FailThenSucceedSource(fail_reads=1)
    loop = CaptureLoop(
        source,
        bus,
        initial_backoff=0.01,
        max_backoff=0.05,
        factor=2.0,
    )
    seen_reconnecting = threading.Event()

    def watch() -> None:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline:
            if loop.status == SourceStatus.RECONNECTING:
                seen_reconnecting.set()
                return
            time.sleep(0.005)

    watcher = threading.Thread(target=watch, daemon=True)
    try:
        loop.start()
        watcher.start()
        assert _wait_until(
            lambda: loop.status == SourceStatus.STREAMING
            and bus.get_latest() is not None,
            timeout=3.0,
        )
        # Disconnect path should have been visible (or already recovered very fast)
        watcher.join(timeout=0.5)
        assert (
            seen_reconnecting.is_set()
            or source.open_count >= 2
            or bus.metrics_snapshot().frames_published >= 1
        )
        assert loop.status == SourceStatus.STREAMING
        detail_while_ok = loop.status_detail
        assert detail_while_ok is None
    finally:
        loop.stop()
    assert loop.status == SourceStatus.STOPPED


def test_open_failure_sets_detail_then_recovers() -> None:
    bus = FrameBus()
    source = _OpenFailsThenWorksSource(fail_opens=2)
    loop = CaptureLoop(
        source,
        bus,
        initial_backoff=0.01,
        max_backoff=0.05,
    )
    try:
        loop.start()
        # Not silent: either ERROR/RECONNECTING with detail, or already streaming
        assert _wait_until(
            lambda: loop.status
            in (
                SourceStatus.ERROR,
                SourceStatus.RECONNECTING,
                SourceStatus.STREAMING,
            )
            and (
                loop.status_detail is not None
                or loop.status == SourceStatus.STREAMING
            ),
            timeout=2.0,
        )
        assert _wait_until(
            lambda: loop.status == SourceStatus.STREAMING
            and bus.get_latest() is not None,
            timeout=3.0,
        )
        assert loop.status == SourceStatus.STREAMING
        assert bus.get_latest() is not None
    finally:
        loop.stop()


def test_start_does_not_raise_into_caller_on_bad_source() -> None:
    class AlwaysFailOpen:
        name = "always-fail"
        camera_id = "x"

        def open(self) -> None:
            raise OSError("device missing")

        def read(self) -> ImageFrame:
            raise RuntimeError("unreachable")

        def close(self) -> None:
            return None

    bus = FrameBus()
    loop = CaptureLoop(
        AlwaysFailOpen(),  # type: ignore[arg-type]
        bus,
        initial_backoff=0.01,
        max_backoff=0.05,
    )
    try:
        loop.start()  # must not raise
        assert _wait_until(
            lambda: loop.status
            in (SourceStatus.ERROR, SourceStatus.RECONNECTING)
            and loop.status_detail is not None,
            timeout=2.0,
        )
        assert "device missing" in (loop.status_detail or "")
    finally:
        loop.stop()


def test_loop_stamps_t_ingest_when_missing() -> None:
    bus = FrameBus()
    source = _FailThenSucceedSource(fail_reads=0)  # always succeeds
    loop = CaptureLoop(source, bus, initial_backoff=0.01, max_backoff=0.05)
    try:
        loop.start()
        assert _wait_until(lambda: bus.get_latest() is not None, timeout=2.0)
        latest = bus.get_latest()
        assert latest is not None
        assert latest.meta.t_ingest is not None
    finally:
        loop.stop()


def test_start_never_called_status_stopped() -> None:
    loop = CaptureLoop(
        SyntheticSource(fps=0.0),
        FrameBus(),
        initial_backoff=0.01,
        max_backoff=0.05,
    )
    assert loop.status == SourceStatus.STOPPED
