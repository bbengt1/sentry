"""ONL-07 / ONL-05 runtime: DepthLoop online hook, serve wiring, status (21-02)."""

from __future__ import annotations

import ast
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
from fastapi.testclient import TestClient

from sentry_ai import cli as cli_mod
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.control.online_sampler import OnlineSampler
from sentry_ai.models.depth import loop as loop_mod
from sentry_ai.models.depth.loop import DepthLoop
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
)
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.state.perception_store import PerceptionStore
from tests.test_api_calibration import _app, _seed_depth
from tests.test_depth_loop import FakeDepthWorker, _wait_until

if TYPE_CHECKING:
    from sentry_ai.capture.image_frame import ImageFrame

SRC = Path(__file__).resolve().parents[1] / "src" / "sentry_ai"


def _online_state(*, scale: float, known: float) -> CalibrationState:
    """Wizard apply() with one consent anchor, then online on."""
    state = CalibrationState()
    state.add_draft_sample(
        CalibrationSample(point_uv=(2.0, 2.0), known_meters=known, observed_raw=1.0)
    )
    state.set_draft_params(
        CalibrationParams(
            scale=scale,
            offset=0.0,
            sample_count=1,
            fingerprint=CalibrationFingerprint(
                camera_id="cam0", depth_mode="relative", model_id="fake-depth"
            ),
        )
    )
    state.apply()
    state.set_online(True)
    return state


class _Clocked:
    """Wrap a real sampler; replace the loop's monotonic clock with frame_id."""

    def __init__(self, inner: OnlineSampler) -> None:
        self.inner = inner
        self.results: list[Any] = []

    def consider(self, depth_map: Any, **kwargs: Any) -> Any:
        kwargs["now_s"] = float(kwargs["frame_id"])
        result = self.inner.consider(depth_map, **kwargs)
        self.results.append(result)
        return result


class _Recorder:
    def __init__(self, log: list[str] | None = None) -> None:
        self.log = log if log is not None else []
        self.maps: list[np.ndarray] = []
        self.kwargs: list[dict[str, Any]] = []

    def consider(self, depth_map: Any, **kwargs: Any) -> None:
        self.log.append("consider")
        self.maps.append(np.array(depth_map, copy=True))
        self.kwargs.append(kwargs)


class _FreeSpaceSpy:
    def __init__(self) -> None:
        self.resets = 0

    def reset_smoother(self) -> None:
        self.resets += 1


def _publish_and_wait(
    bus: FrameBus,
    store: PerceptionStore,
    factory: Callable[..., ImageFrame],
    frame_id: int,
    camera_id: str = "cam0",
) -> Any:
    bus.publish(factory(frame_id=frame_id, camera_id=camera_id))
    assert _wait_until(
        lambda: (s := store.snapshot_depth()) is not None and s.frame_id == frame_id,
        timeout=2.0,
    )
    return store.snapshot_depth()


def _run_frames(
    loop: DepthLoop,
    bus: FrameBus,
    store: PerceptionStore,
    factory: Callable[..., ImageFrame],
    frame_ids: list[int],
    camera_id: str = "cam0",
) -> list[Any]:
    snaps = []
    try:
        loop.start()
        for fid in frame_ids:
            snaps.append(_publish_and_wait(bus, store, factory, fid, camera_id))
    finally:
        loop.stop()
    return snaps


# --- hook inputs and order ---------------------------------------------------


def test_sampler_gets_raw_map_and_live_fingerprint(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=3.0, known=3.0)
    rec = _Recorder()
    loop = DepthLoop(bus, FakeDepthWorker(value=2.0), store, calibration=state)
    loop.set_online_sampler(rec)
    (snap,) = _run_frames(loop, bus, store, image_frame_factory, [5])
    assert len(rec.maps) == 1
    # Pre-apply raw worker output (2.0), not the stored scaled map (6.0).
    assert float(np.mean(rec.maps[0])) == pytest.approx(2.0)
    assert float(np.mean(snap.depth_map)) == pytest.approx(6.0)
    kw = rec.kwargs[0]
    assert kw["frame_id"] == 5
    assert isinstance(kw["now_s"], float)
    live = kw["live_fingerprint"]
    assert live.camera_id == "cam0"
    assert (live.width, live.height) == (64, 48)
    assert live.depth_mode == "relative" and live.model_id == "fake-depth"


def test_hook_order_refuse_consider_promote_apply(
    image_frame_factory: Callable[..., ImageFrame],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=2.0, known=2.0)
    log: list[str] = []
    real_refuse = loop_mod.refuse_if_mismatch
    real_promote = state.promote_kind_unit
    real_apply = state.apply_map

    def _refuse(*a: Any, **k: Any) -> Any:
        log.append("refuse")
        return real_refuse(*a, **k)

    def _promote(*a: Any, **k: Any) -> Any:
        log.append("promote")
        return real_promote(*a, **k)

    def _apply(*a: Any, **k: Any) -> Any:
        log.append("apply_map")
        return real_apply(*a, **k)

    monkeypatch.setattr(loop_mod, "refuse_if_mismatch", _refuse)
    monkeypatch.setattr(state, "promote_kind_unit", _promote)
    monkeypatch.setattr(state, "apply_map", _apply)
    loop = DepthLoop(bus, FakeDepthWorker(value=1.0), store, calibration=state)
    loop.set_online_sampler(_Recorder(log))
    _run_frames(loop, bus, store, image_frame_factory, [1])
    assert log == ["refuse", "consider", "promote", "apply_map"]


def test_no_sampler_keeps_existing_behavior(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=3.0, known=3.0)
    loop = DepthLoop(bus, FakeDepthWorker(value=2.0), store, calibration=state)
    (snap,) = _run_frames(loop, bus, store, image_frame_factory, [1])
    assert float(np.mean(snap.depth_map)) == pytest.approx(6.0)
    assert snap.kind == DepthKind.METRIC_CALIBRATED


# --- commit through live frames ---------------------------------------------


def test_commit_on_frame_n_is_used_by_frame_n(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=1.5, known=2.0)
    spy = _FreeSpaceSpy()
    sampler = _Clocked(
        OnlineSampler(state, auto_commit=True, on_auto_commit=spy.reset_smoother)
    )
    loop = DepthLoop(
        bus, FakeDepthWorker(value=1.0), store, calibration=state,
        online_sampler=sampler,
    )
    snaps = _run_frames(loop, bus, store, image_frame_factory, list(range(1, 9)))
    assert [r.reason for r in sampler.results][-1] == "committed"
    for snap in snaps[:7]:
        assert float(np.mean(snap.depth_map)) == pytest.approx(1.5)
    last = snaps[7]
    assert last.kind == DepthKind.METRIC_CALIBRATED and last.unit == "m"
    assert float(np.mean(last.depth_map)) == pytest.approx(2.0)
    assert state.snapshot().online_status == "auto_committed"
    assert spy.resets == 1


def test_sampler_exception_is_contained_and_frame_publishes(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    class _Boom:
        calls = 0

        def consider(self, *_a: Any, **_k: Any) -> None:
            _Boom.calls += 1
            raise RuntimeError("sampler blew up")

    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=3.0, known=3.0)
    loop = DepthLoop(bus, FakeDepthWorker(value=2.0), store, calibration=state)
    loop.set_online_sampler(_Boom())
    snaps = _run_frames(loop, bus, store, image_frame_factory, [1, 2])
    assert _Boom.calls == 2
    for snap in snaps:
        assert snap.error is None
        assert snap.kind == DepthKind.METRIC_CALIBRATED
        assert float(np.mean(snap.depth_map)) == pytest.approx(6.0)
    assert state.get_applied_params().scale == 3.0  # type: ignore[union-attr]


def test_mismatch_frame_refused_before_sampler(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=1.5, known=2.0)
    sampler = _Clocked(OnlineSampler(state, auto_commit=True))
    loop = DepthLoop(
        bus, FakeDepthWorker(value=1.0), store, calibration=state,
        online_sampler=sampler,
    )
    (snap,) = _run_frames(
        loop, bus, store, image_frame_factory, [1], camera_id="cam9"
    )
    assert state.is_applied() is False
    assert state.get_persist_status()[0] == "ignored_mismatch"
    assert sampler.results[0].reason in {"online_off", "not_applied"}
    assert snap.kind == DepthKind.RELATIVE


# --- serve wiring + smoother ------------------------------------------------


def test_attach_online_sampler_wires_auto_commit_and_reset() -> None:
    state = CalibrationState()
    store = PerceptionStore()
    loop = DepthLoop(FrameBus(), FakeDepthWorker(), store, calibration=state)
    spy = _FreeSpaceSpy()
    cli_mod._attach_online_sampler(loop, state, spy)  # noqa: SLF001
    sampler = loop._online_sampler  # noqa: SLF001
    assert isinstance(sampler, OnlineSampler)
    assert sampler.auto_commit is True
    sampler._on_auto_commit()  # noqa: SLF001
    assert spy.resets == 1


def test_attach_online_sampler_noops_without_loop_or_state() -> None:
    cli_mod._attach_online_sampler(None, CalibrationState(), _FreeSpaceSpy())  # noqa: SLF001
    loop = DepthLoop(FrameBus(), FakeDepthWorker(), PerceptionStore())
    cli_mod._attach_online_sampler(loop, None, _FreeSpaceSpy())  # noqa: SLF001
    assert loop._online_sampler is None  # noqa: SLF001


@pytest.mark.parametrize(
    ("scale", "known", "reason"),
    [
        (1.5, 2.0, "committed"),
        (2.0, 1000.0, "horizon_refused"),
        (2.0, 2.01, "within_deadband"),
    ],
)
def test_wired_reset_only_on_commit(
    image_frame_factory: Callable[..., ImageFrame],
    scale: float,
    known: float,
    reason: str,
) -> None:
    bus, store = FrameBus(), PerceptionStore()
    state = _online_state(scale=scale, known=known)
    spy = _FreeSpaceSpy()
    loop = DepthLoop(bus, FakeDepthWorker(value=1.0), store, calibration=state)
    cli_mod._attach_online_sampler(loop, state, spy)  # noqa: SLF001
    sampler = _Clocked(loop._online_sampler)  # noqa: SLF001
    loop.set_online_sampler(sampler)
    _run_frames(loop, bus, store, image_frame_factory, list(range(1, 9)))
    assert sampler.results[-1].reason == reason
    assert spy.resets == (1 if reason == "committed" else 0)


# --- status plane -------------------------------------------------------------


def test_api_status_shows_online_decisions_on_their_own_plane() -> None:
    store = PerceptionStore()
    _seed_depth(store, value=1.0, kind=DepthKind.METRIC_CALIBRATED, unit="m")
    state = _online_state(scale=1.5, known=2.0)
    state.set_persist_status("applied")
    app, capture, _state, _store, _worker = _app(store=store, calibration_state=state)
    live = CalibrationFingerprint(
        camera_id="cam0",
        width=4,
        height=4,
        depth_mode="relative",
        model_id="fake-depth",
    )
    depth = np.full((4, 4), 1.0, dtype=np.float32)
    try:
        with TestClient(app) as client:
            sampler = OnlineSampler(state, auto_commit=True)
            for fid in range(1, 9):
                sampler.consider(
                    depth, frame_id=fid, now_s=float(fid), live_fingerprint=live
                )
            data = client.get("/api/status").json()
            assert data["calibration_online_status"] == "auto_committed"
            assert data["calibration_persist"] == "applied"
            assert data["depth_kind"] == DepthKind.METRIC_CALIBRATED.value
            # Inconsistent window after the commit -> fit_rejected -> rejected.
            for fid in range(9, 17):
                value = 1.0 if fid % 2 else 50.0
                sampler.consider(
                    np.full((4, 4), value, dtype=np.float32),
                    frame_id=fid,
                    now_s=float(fid),
                    live_fingerprint=live,
                )
            data = client.get("/api/status").json()
            assert data["calibration_online_status"] == "rejected"
            assert data["calibration_persist"] == "applied"
            assert data["depth_kind"] == DepthKind.METRIC_CALIBRATED.value
    finally:
        capture.stop()


# --- sole apply_map site -----------------------------------------------------


def test_apply_map_called_only_in_depth_loop() -> None:
    callers: set[str] = set()
    for path in SRC.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "apply_map"
            ):
                callers.add(path.relative_to(SRC).as_posix())
    assert callers == {"models/depth/loop.py"}

