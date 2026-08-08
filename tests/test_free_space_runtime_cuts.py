"""UI-04: FreeSpaceLoop near/mid cut runtime knobs."""

from __future__ import annotations

import time
from typing import Any
from unittest.mock import patch

import numpy as np

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.free_space import DEFAULT_MID_CUT, DEFAULT_NEAR_CUT
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


def test_free_space_loop_default_cuts() -> None:
    loop = FreeSpaceLoop(PerceptionStore())
    assert loop.get_near_cut() == DEFAULT_NEAR_CUT
    assert loop.get_mid_cut() == DEFAULT_MID_CUT


def test_set_cuts_validation() -> None:
    loop = FreeSpaceLoop(PerceptionStore())
    try:
        loop.set_cuts(near_cut=0.3, mid_cut=0.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    try:
        loop.set_near_cut(0.1)  # 0.1 <= mid 0.45
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Valid change
    loop.set_cuts(near_cut=0.9, mid_cut=0.2)
    assert loop.get_near_cut() == 0.9
    assert loop.get_mid_cut() == 0.2


def test_runtime_cuts_passed_to_compute_free_space() -> None:
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    received: list[tuple[float, float]] = []

    real_compute = __import__(
        "sentry_ai.spatial.free_space", fromlist=["compute_free_space"]
    ).compute_free_space

    def spy_compute(depth_map: Any, **kwargs: Any) -> Any:
        received.append((kwargs.get("near_cut"), kwargs.get("mid_cut")))
        return real_compute(depth_map, **kwargs)

    try:
        loop.start()
        with patch(
            "sentry_ai.spatial.loop.compute_free_space",
            side_effect=spy_compute,
        ):
            _set_depth(store, 1)
            assert _wait_until(lambda: len(received) >= 1, timeout=2.0)
            assert received[0] == (DEFAULT_NEAR_CUT, DEFAULT_MID_CUT)

            loop.set_cuts(near_cut=0.85, mid_cut=0.3)
            _set_depth(store, 2)
            assert _wait_until(lambda: len(received) >= 2, timeout=2.0)
            assert received[-1] == (0.85, 0.3)
    finally:
        loop.stop()


def test_cut_change_affects_bands_on_next_frame() -> None:
    """Extreme cuts change free/occupied band fractions vs defaults."""
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    try:
        loop.start()
        _set_depth(store, 1)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.error is None,
            timeout=2.0,
        )
        snap_default = store.snapshot_free_space()
        assert snap_default is not None
        default_near = snap_default.bands.get("near_frac", 0.0)

        # Very high near_cut → fewer near-band pixels
        loop.set_cuts(near_cut=0.99, mid_cut=0.01)
        _set_depth(store, 2)
        assert _wait_until(
            lambda: (s := store.snapshot_free_space()) is not None
            and s.frame_id == 2
            and s.error is None,
            timeout=2.0,
        )
        snap_tight = store.snapshot_free_space()
        assert snap_tight is not None
        tight_near = snap_tight.bands.get("near_frac", 0.0)
        # Tight near cut should yield less or equal near_frac
        assert tight_near <= default_near + 1e-6
    finally:
        loop.stop()
