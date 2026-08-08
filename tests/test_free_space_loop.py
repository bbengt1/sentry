"""SPACE-01: FreeSpaceLoop Spatial Post daemon (synthetic depth, no ML)."""

from __future__ import annotations

import inspect
import time
from typing import Any

import numpy as np

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial import loop as loop_mod
from sentry_ai.spatial.loop import FreeSpaceLoop
from sentry_ai.state.perception_store import PerceptionStore


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


def _synthetic_depth(h: int = 120, w: int = 160) -> np.ndarray:
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5
    return depth


def _set_depth(
    store: PerceptionStore,
    frame_id: int,
    *,
    depth_map: np.ndarray | None = None,
    error: str | None = None,
    camera_id: str = "cam0",
    t_capture: float | None = None,
) -> None:
    store.set_depth(
        frame_id=frame_id,
        camera_id=camera_id,
        t_capture=float(frame_id) if t_capture is None else t_capture,
        depth_map=depth_map if depth_map is not None else _synthetic_depth(),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        error=error,
    )


def test_loop_processes_depth_into_free_space_product() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        _set_depth(store, 7, camera_id="camA", t_capture=1.25)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 7
            and s.error is None,
            timeout=2.0,
        )
        snap = store.snapshot_free_space()
        assert snap is not None
        assert snap.frame_id == 7
        assert snap.camera_id == "camA"
        assert snap.t_capture == 1.25
        assert snap.method == "near_field_bands"
        assert snap.obstacle_count >= 1
        assert len(snap.obstacles) == snap.obstacle_count
        assert snap.occupied_mask is not None
        assert snap.free_mask is not None
        assert snap.latency_ms >= 0.0
        assert snap.error is None
    finally:
        loop.stop()


def test_loop_start_stop_idempotent() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        loop.start()  # no-op
        _set_depth(store, 1)
        assert _wait_until(
            lambda: store.snapshot_free_space() is not None, timeout=2.0
        )
    finally:
        loop.stop()
        loop.stop()  # no-op


def test_loop_skips_same_frame_id() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        _set_depth(store, 1)
        assert _wait_until(
            lambda: store.snapshot_free_space() is not None, timeout=2.0
        )
        frames_after = store.metrics_snapshot().free_space_frames
        time.sleep(0.05)
        assert store.metrics_snapshot().free_space_frames == frames_after
    finally:
        loop.stop()


def test_loop_skips_missing_error_and_null_map() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        # No depth yet
        time.sleep(0.03)
        assert store.snapshot_free_space() is None

        # Error product with no map
        _set_depth(store, 1, depth_map=None, error="depth failed")
        time.sleep(0.05)
        assert store.snapshot_free_space() is None

        # Null map without error still skipped
        store.set_depth(
            frame_id=2,
            camera_id="cam0",
            t_capture=2.0,
            depth_map=None,
            kind=DepthKind.RELATIVE,
            unit=None,
            latency_ms=0.0,
        )
        time.sleep(0.05)
        assert store.snapshot_free_space() is None

        # Good map processes
        _set_depth(store, 3)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 3,
            timeout=2.0,
        )
    finally:
        loop.stop()


def test_loop_records_drop_on_frame_id_gaps() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        _set_depth(store, 1)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 1,
            timeout=2.0,
        )
        _set_depth(store, 5)  # gap of 3 frames (2,3,4)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 5,
            timeout=2.0,
        )
        metrics = store.metrics_snapshot()
        assert metrics.free_space_frames_dropped >= 3
    finally:
        loop.stop()


def test_loop_survives_compute_exception() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)

    # Force compute path to raise once via monkeypatch.
    import sentry_ai.spatial.loop as fs_loop_mod

    original = fs_loop_mod.compute_free_space
    calls = {"n": 0}

    def flaky(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated free-space failure")
        return original(*args, **kwargs)

    fs_loop_mod.compute_free_space = flaky  # type: ignore[assignment]
    try:
        loop.start()
        _set_depth(store, 1)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 1
            and s.error is not None,
            timeout=2.0,
        )
        err_snap = store.snapshot_free_space()
        assert err_snap is not None
        assert "simulated free-space failure" in (err_snap.error or "")
        assert err_snap.obstacle_count == 0
        assert err_snap.obstacles == []

        # Thread still alive — next frame succeeds
        _set_depth(store, 2)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 2
            and s.error is None,
            timeout=2.0,
        )
    finally:
        fs_loop_mod.compute_free_space = original  # type: ignore[assignment]
        loop.stop()


def test_loop_module_has_no_ml_or_framebus_imports() -> None:
    source = inspect.getsource(loop_mod)
    assert "import torch" not in source
    assert "transformers" not in source
    assert "ultralytics" not in source
    assert "FrameBus" not in source
    assert "frame_bus" not in source
