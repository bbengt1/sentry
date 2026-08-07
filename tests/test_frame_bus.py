"""CAM-05: FrameBus keep-latest mailbox with drop/FPS metrics."""

from __future__ import annotations

import threading
import time

from sentry_ai.bus.frame_bus import BusMetrics, FrameBus
from tests.conftest import make_image_frame


def test_get_latest_none_before_publish() -> None:
    bus = FrameBus()
    assert bus.get_latest() is None
    snap = bus.metrics_snapshot()
    assert snap.frames_published == 0
    assert snap.frames_dropped == 0
    assert snap.last_publish_t is None
    assert snap.capture_fps == 0.0


def test_publish_returns_same_frame_identity() -> None:
    bus = FrameBus()
    frame = make_image_frame(frame_id=7)
    bus.publish(frame)
    latest = bus.get_latest()
    assert latest is not None
    assert latest.frame_id == 7
    assert latest is frame  # keep-latest holds reference


def test_second_publish_increments_frames_dropped() -> None:
    bus = FrameBus()
    bus.publish(make_image_frame(frame_id=0))
    bus.publish(make_image_frame(frame_id=1))
    snap = bus.metrics_snapshot()
    assert snap.frames_published == 2
    assert snap.frames_dropped == 1
    latest = bus.get_latest()
    assert latest is not None
    assert latest.frame_id == 1


def test_depth_one_only_latest_retained_after_many_publishes() -> None:
    bus = FrameBus()
    for i in range(50):
        bus.publish(make_image_frame(frame_id=i))
    latest = bus.get_latest()
    assert latest is not None
    assert latest.frame_id == 49
    snap = bus.metrics_snapshot()
    assert snap.frames_published == 50
    # First publish fills empty slot (no drop); remaining 49 overwrite.
    assert snap.frames_dropped == 49


def test_frames_published_counts_every_publish() -> None:
    bus = FrameBus()
    for i in range(5):
        bus.publish(make_image_frame(frame_id=i))
    assert bus.metrics_snapshot().frames_published == 5


def test_metrics_snapshot_is_isolated_copy() -> None:
    bus = FrameBus()
    bus.publish(make_image_frame(frame_id=0))
    snap = bus.metrics_snapshot()
    assert isinstance(snap, BusMetrics)
    snap.frames_published = 999
    snap.frames_dropped = 999
    snap.capture_fps = 999.0
    snap.last_publish_t = 0.0
    internal = bus.metrics_snapshot()
    assert internal.frames_published == 1
    assert internal.frames_dropped == 0
    assert internal.capture_fps != 999.0
    assert internal.last_publish_t is not None


def test_get_latest_does_not_consume() -> None:
    """Keep-latest is not consume-once: repeated get returns same slot."""
    bus = FrameBus()
    frame = make_image_frame(frame_id=3)
    bus.publish(frame)
    a = bus.get_latest()
    b = bus.get_latest()
    assert a is frame
    assert b is frame
    # No claim/consume: overwrite still counts as drop
    bus.publish(make_image_frame(frame_id=4))
    assert bus.metrics_snapshot().frames_dropped == 1


def test_capture_fps_non_negative_after_publishes() -> None:
    bus = FrameBus()
    for i in range(10):
        bus.publish(make_image_frame(frame_id=i))
    assert bus.metrics_snapshot().capture_fps >= 0.0


def test_capture_fps_updates_after_one_second_window() -> None:
    """Drive FPS window with real monotonic time (~1s of publishes)."""
    bus = FrameBus()
    deadline = time.monotonic() + 1.15
    n = 0
    while time.monotonic() < deadline:
        bus.publish(make_image_frame(frame_id=n))
        n += 1
        time.sleep(0.02)
    # One more publish after window may have rolled, or window already rolled.
    bus.publish(make_image_frame(frame_id=n))
    fps = bus.metrics_snapshot().capture_fps
    assert fps >= 0.0
    # With ~50 publishes/sec over 1s window, expect positive FPS once window closes.
    assert fps > 0.0 or n < 5  # soft: allow edge if scheduler starves


def test_concurrent_publish_get_latest_smoke() -> None:
    bus = FrameBus()
    errors: list[BaseException] = []
    stop = threading.Event()

    def publisher() -> None:
        try:
            i = 0
            while not stop.is_set() and i < 200:
                bus.publish(make_image_frame(frame_id=i))
                i += 1
        except BaseException as exc:  # noqa: BLE001 — collect for assertion
            errors.append(exc)

    def consumer() -> None:
        try:
            for _ in range(200):
                _ = bus.get_latest()
                _ = bus.metrics_snapshot()
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    t_pub = threading.Thread(target=publisher, daemon=True)
    t_con = threading.Thread(target=consumer, daemon=True)
    t_pub.start()
    t_con.start()
    t_pub.join(timeout=5.0)
    stop.set()
    t_con.join(timeout=5.0)
    assert errors == []
    assert bus.metrics_snapshot().frames_published > 0
    assert bus.get_latest() is not None
