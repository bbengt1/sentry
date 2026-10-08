"""Camera reconnect: online sampler restarts cleanly on a new capture session.

Brent-approved follow-up to 21-02 (amends the Phase 20 frame_id lock for
reconnects only). CaptureLoop counts successful opens and stamps that session
number on each ImageFrame; DepthLoop calls ``OnlineSampler.reset_session()``
when the session changes. Within a session frame_id must still strictly
increase.
"""

from __future__ import annotations

import dataclasses
import itertools
import threading
import time
from collections.abc import Callable
from typing import Any

import numpy as np
import pytest

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.loop import CaptureLoop
from sentry_ai.control.online_sampler import OnlineSampler
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.schemas.calibration import CalibrationFingerprint, CalibrationSample
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.errors import SourceDisconnected
from sentry_ai.state.perception_store import PerceptionStore
from tests.test_depth_loop import FakeDepthWorker, _wait_until
from tests.test_depth_loop_online import _online_state

CAM0 = CalibrationFingerprint(
    camera_id="cam0", width=64, height=48, depth_mode="relative",
    model_id="fake-depth",
)


def _map(value: float) -> np.ndarray:
    return np.full((48, 64), value, dtype=np.float32)


def _feed(
    sampler: OnlineSampler,
    value: float,
    frame_ids: range | list[int],
    *,
    t0: float,
    live: CalibrationFingerprint | None = CAM0,
) -> list[Any]:
    return [
        sampler.consider(
            _map(value), frame_id=fid, now_s=t0 + float(i), live_fingerprint=live
        )
        for i, fid in enumerate(frame_ids)
    ]


# --- sampler: reset_session ---------------------------------------------------


def test_reconnect_mid_window_drops_window_and_resumes_with_new_ids() -> None:
    state = _online_state(scale=1.5, known=2.0)
    sampler = OnlineSampler(state)
    old = _feed(sampler, 1.0, range(500, 504), t0=0.0)
    assert [r.reason for r in old] == ["window_short"] * 4
    assert len(state.get_draft_samples()) == 4

    sampler.reset_session()
    assert state.get_draft_samples() == []

    # New session restarts at frame_id 0: accepted, not frame_not_advanced.
    new = _feed(sampler, 1.0, range(0, 8), t0=100.0)
    assert [r.reason for r in new] == ["window_short"] * 7 + ["draft_staged"]


def test_window_never_mixes_sessions(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _online_state(scale=1.5, known=2.0)
    staged: list[Any] = []
    real_set = state.set_draft_params

    def _spy(params: Any) -> Any:
        staged.append(params)
        return real_set(params)

    monkeypatch.setattr(state, "set_draft_params", _spy)
    sampler = OnlineSampler(state)
    _feed(sampler, 1.0, range(500, 507), t0=0.0)  # 7 old-session frames
    sampler.reset_session()
    results = _feed(sampler, 0.5, range(0, 8), t0=100.0)
    assert results[-1].reason == "draft_staged"
    samples = state.get_draft_samples()
    assert len(samples) == 8
    assert {s.frame_id for s in samples} == set(range(8))
    assert {s.observed_raw for s in samples} == {0.5}
    # 2.0 m / 0.5 raw: only new-session frames in the fit (mixed would be < 4).
    assert len(staged) == 1 and staged[0].scale == pytest.approx(4.0)


def test_reconnect_drops_staged_draft_from_old_window() -> None:
    state = _online_state(scale=1.5, known=2.0)
    sampler = OnlineSampler(state)
    assert _feed(sampler, 1.0, range(500, 508), t0=0.0)[-1].reason == "draft_staged"
    assert state.snapshot().has_draft_params is True
    sampler.reset_session()
    snap = state.snapshot()
    assert snap.has_draft_params is False
    assert state.get_draft_samples() == []


def test_reconnect_keeps_applied_anchors_and_online_state() -> None:
    state = _online_state(scale=1.5, known=2.0)
    sampler = OnlineSampler(state)
    _feed(sampler, 1.0, range(500, 504), t0=0.0)
    applied = state.get_applied_params()
    anchors = state.get_consent_anchors()
    status = state.snapshot().online_status
    sampler.reset_session()
    assert state.get_applied_params() == applied
    assert state.get_consent_anchors() == anchors
    assert state.is_online() is True
    assert state.snapshot().online_status == status


def test_reset_with_empty_window_leaves_other_draft_alone() -> None:
    state = _online_state(scale=1.5, known=2.0)
    wizard = CalibrationSample(point_uv=(1.0, 1.0), known_meters=3.0, observed_raw=2.0)
    state.add_draft_sample(wizard)
    sampler = OnlineSampler(state)
    sampler.reset_session()
    assert state.get_draft_samples() == [wizard]


def test_within_session_non_increasing_ids_still_refused_after_reset() -> None:
    state = _online_state(scale=1.5, known=2.0)
    sampler = OnlineSampler(state)
    _feed(sampler, 1.0, [500], t0=0.0)
    sampler.reset_session()
    assert sampler.consider(_map(1.0), frame_id=10, now_s=50.0).accepted is True
    same = sampler.consider(_map(1.0), frame_id=10, now_s=60.0)
    older = sampler.consider(_map(1.0), frame_id=9, now_s=70.0)
    assert same.reason == "frame_not_advanced"
    assert older.reason == "frame_not_advanced"


def test_reconnect_to_different_camera_cannot_commit() -> None:
    state = _online_state(scale=1.5, known=2.0)
    sampler = OnlineSampler(state, auto_commit=True)
    _feed(sampler, 1.0, range(500, 504), t0=0.0)
    applied = state.get_applied_params()
    sampler.reset_session()
    other = CAM0.model_copy(update={"camera_id": "cam9"})
    results = _feed(sampler, 1.0, range(0, 8), t0=100.0, live=other)
    assert results[-1].reason == "fingerprint_mismatch"
    assert "committed" not in {r.reason for r in results}
    assert state.get_applied_params() == applied
    assert state.snapshot().online_status == "rejected"


# --- CaptureLoop: session stamp ---------------------------------------------


class _DropOnceSource:
    """Streams frames, disconnects once at read #4, then streams again."""

    name = "drop-once"
    camera_id = "cam0"

    def __init__(self) -> None:
        self._reads = 0
        self._next = 0

    def open(self) -> None:
        self._next = 0

    def read(self) -> ImageFrame:
        self._reads += 1
        if self._reads == 4:
            raise SourceDisconnected("simulated unplug")
        meta = Frame(frame_id=self._next, camera_id="cam0", t_capture=time.time())
        self._next += 1
        return ImageFrame(meta=meta, image_bgr=np.zeros((4, 4, 3), np.uint8))

    def close(self) -> None:
        pass


class _RecordingBus(FrameBus):
    def __init__(self) -> None:
        super().__init__()
        self.seen: list[tuple[int, int]] = []
        self._seen_lock = threading.Lock()

    def publish(self, frame: ImageFrame) -> None:
        with self._seen_lock:
            self.seen.append((frame.session, frame.frame_id))
        super().publish(frame)


def test_capture_loop_stamps_new_session_on_reopen() -> None:
    bus = _RecordingBus()
    loop = CaptureLoop(_DropOnceSource(), bus, initial_backoff=0.01, max_backoff=0.01)
    try:
        loop.start()
        assert _wait_until(lambda: len(bus.seen) >= 6, timeout=2.0)
    finally:
        loop.stop()
    first, second = bus.seen[:3], bus.seen[3:6]
    assert [fid for _s, fid in first] == [0, 1, 2]
    assert [fid for _s, fid in second] == [0, 1, 2]
    (s1,) = {s for s, _ in first}
    (s2,) = {s for s, _ in second}
    assert s2 > s1 >= 1


def test_image_frame_session_defaults_to_zero(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    assert image_frame_factory(frame_id=1).session == 0


# --- DepthLoop: reset on session change --------------------------------------

_T = itertools.count(1)


def _frame(
    factory: Callable[..., ImageFrame], fid: int, session: int, camera: str = "cam0"
) -> ImageFrame:
    base = factory(frame_id=fid, camera_id=camera)
    # Unique t_capture so waits can tell same-id frames from two sessions apart.
    meta = base.meta.model_copy(update={"t_capture": float(next(_T))})
    return dataclasses.replace(base, meta=meta, session=session)


def _push(bus: FrameBus, store: PerceptionStore, frame: ImageFrame) -> Any:
    bus.publish(frame)
    assert _wait_until(
        lambda: (s := store.snapshot_depth()) is not None
        and s.t_capture == frame.meta.t_capture,
        timeout=2.0,
    )
    return store.snapshot_depth()


class _SessionClock:
    """Real sampler; test clock = session * 1000 + frame_id (always rising)."""

    def __init__(self, inner: OnlineSampler) -> None:
        self.inner = inner
        self.session = 0
        self.resets = 0
        self.results: list[Any] = []

    def reset_session(self) -> None:
        self.resets += 1
        self.inner.reset_session()

    def consider(self, depth_map: Any, **kwargs: Any) -> Any:
        kwargs["now_s"] = self.session * 1000.0 + float(kwargs["frame_id"])
        result = self.inner.consider(depth_map, **kwargs)
        self.results.append(result)
        return result


def _run(
    loop: DepthLoop,
    bus: FrameBus,
    store: PerceptionStore,
    clock: _SessionClock | None,
    frames: list[ImageFrame],
) -> list[Any]:
    snaps = []
    try:
        loop.start()
        for frame in frames:
            if clock is not None:
                clock.session = frame.session
            snaps.append(_push(bus, store, frame))
    finally:
        loop.stop()
    return snaps


def test_depth_loop_reconnect_resumes_and_commits_on_new_session_only(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=1.5, known=2.0)
    clock = _SessionClock(OnlineSampler(state, auto_commit=True))
    loop = DepthLoop(
        bus, FakeDepthWorker(value=1.0), store, calibration=state,
        online_sampler=clock,
    )
    frames = [_frame(image_frame_factory, fid, 1) for fid in range(500, 504)]
    frames += [_frame(image_frame_factory, fid, 2) for fid in range(0, 8)]
    snaps = _run(loop, bus, store, clock, frames)
    reasons = [r.reason for r in clock.results]
    assert clock.resets == 1
    assert "frame_not_advanced" not in reasons
    # 4 old + 7 new short; the 8th new-session frame commits (no mixing).
    assert reasons == ["window_short"] * 11 + ["committed"]
    assert snaps[-1].kind == DepthKind.METRIC_CALIBRATED
    assert float(np.mean(snaps[-1].depth_map)) == pytest.approx(2.0)


def test_depth_loop_processes_new_session_frame_with_old_last_id(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=1.5, known=2.0)
    worker = FakeDepthWorker(value=1.0)
    clock = _SessionClock(OnlineSampler(state))
    loop = DepthLoop(bus, worker, store, calibration=state, online_sampler=clock)
    frames = [_frame(image_frame_factory, 3, 1), _frame(image_frame_factory, 3, 2)]
    _run(loop, bus, store, clock, frames)
    assert worker.process_calls == 2
    assert clock.resets == 1
    assert [r.reason for r in clock.results] == ["window_short", "window_short"]


def test_depth_loop_no_reset_within_one_session(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=1.5, known=2.0)
    clock = _SessionClock(OnlineSampler(state))
    loop = DepthLoop(
        bus, FakeDepthWorker(value=1.0), store, calibration=state,
        online_sampler=clock,
    )
    frames = [_frame(image_frame_factory, fid, 1) for fid in (1, 2, 3)]
    _run(loop, bus, store, clock, frames)
    assert clock.resets == 0


def test_depth_loop_reconnect_to_other_camera_never_commits(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=1.5, known=2.0)
    clock = _SessionClock(OnlineSampler(state, auto_commit=True))
    loop = DepthLoop(
        bus, FakeDepthWorker(value=1.0), store, calibration=state,
        online_sampler=clock,
    )
    frames = [_frame(image_frame_factory, fid, 1) for fid in range(500, 504)]
    frames += [_frame(image_frame_factory, fid, 2, "cam9") for fid in range(0, 8)]
    snaps = _run(loop, bus, store, clock, frames)
    assert "committed" not in {r.reason for r in clock.results}
    # Existing mismatch refuse (Phase 19) clears applied before the sampler.
    assert state.is_applied() is False
    assert snaps[-1].kind == DepthKind.RELATIVE
