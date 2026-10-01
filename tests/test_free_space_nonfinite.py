"""CR-001: non-finite depth must not publish a complete, obstacle-free clearance."""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import pytest

from sentry_ai.api.assemble import assemble_perception_frame
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.free_space import compute_free_space
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


def _assert_not_a_clear_product(result: Any) -> None:
    assert result.error == "no finite depth in roi"
    assert result.units == "ordinal"
    assert result.free_mask is None
    assert result.occupied_mask is None
    assert result.obstacles == []
    assert result.bands.get("far_frac", 0.0) != 1.0


@pytest.mark.parametrize(
    "kind",
    [DepthKind.RELATIVE, DepthKind.METRIC_CALIBRATED],
)
@pytest.mark.parametrize("fill", [np.nan, np.inf, -np.inf])
def test_nonfinite_depth_is_not_a_complete_clear_path(
    kind: DepthKind,
    fill: float,
) -> None:
    """All-NaN and all-inf maps must not look obstacle-free and complete."""
    depth = np.full((20, 20), fill, dtype=np.float32)
    result = compute_free_space(depth, kind=kind)
    _assert_not_a_clear_product(result)

    unit = "m" if kind == DepthKind.METRIC_CALIBRATED else None
    store = PerceptionStore()
    t0 = time.time()
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=t0,
        depth_map=depth,
        kind=kind,
        unit=unit,  # type: ignore[arg-type]
        latency_ms=1.0,
    )
    store.set_free_space(
        frame_id=1,
        camera_id="cam0",
        t_capture=t0,
        latency_ms=1.0,
        depth_kind=result.depth_kind,
        obstacle_count=len(result.obstacles),
        obstacles=[],
        bands=dict(result.bands),
        free_mask=result.free_mask,
        occupied_mask=result.occupied_mask,
        error=result.error,
        units=result.units,
    )
    frame = assemble_perception_frame(store, now=t0 + 0.05)
    assert frame is not None
    assert frame.completeness.depth is True
    assert frame.completeness.free_space is False
    assert frame.free_space is None


@pytest.mark.parametrize(
    "kind",
    [DepthKind.RELATIVE, DepthKind.METRIC_CALIBRATED],
)
def test_roi_with_no_finite_depth_is_not_clear(kind: DepthKind) -> None:
    """Finite pixels outside the bottom ROI do not make that ROI a clear path."""
    h, w = 20, 20
    depth = np.full((h, w), np.nan, dtype=np.float32)
    roi_start = int(h * (1.0 - 0.55))
    depth[:roi_start, :] = 1.0
    result = compute_free_space(depth, kind=kind)
    _assert_not_a_clear_product(result)


def test_one_finite_roi_pixel_is_not_refused() -> None:
    """A single finite ROI sample is data, not the empty-finite failure."""
    depth = np.full((20, 20), np.nan, dtype=np.float32)
    depth[-1, -1] = 1.0
    result = compute_free_space(
        depth,
        kind=DepthKind.RELATIVE,
        nearness_polarity="higher_is_farther",
    )
    assert result.error is None
    assert result.units == "ordinal"


def test_free_space_loop_publishes_nonfinite_depth_as_error() -> None:
    """The live loop must store the refusal, not a successful all-far product."""
    store = PerceptionStore()
    loop = FreeSpaceLoop(store)
    depth = np.full((20, 20), np.nan, dtype=np.float32)
    try:
        loop.start()
        store.set_depth(
            frame_id=4,
            camera_id="cam0",
            t_capture=time.time(),
            depth_map=depth,
            kind=DepthKind.RELATIVE,
            unit=None,
            latency_ms=1.0,
        )
        assert _wait_until(
            lambda: (snap := store.snapshot_free_space()) is not None
            and snap.frame_id == 4,
            timeout=2.0,
        )
        snap = store.snapshot_free_space()
        assert snap is not None
        assert snap.error == "no finite depth in roi"
        assert snap.units == "ordinal"
        assert snap.free_mask is None
        assert snap.occupied_mask is None
        assert snap.obstacle_count == 0
        frame = assemble_perception_frame(store, now=time.time())
        assert frame is not None
        assert frame.completeness.free_space is False
        assert frame.free_space is None
    finally:
        loop.stop()
