"""CAL-05: PerceptionStore.set_depth rejects dishonest kind/unit pairs."""

from __future__ import annotations

import numpy as np
import pytest

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.state.perception_store import PerceptionStore


def _small_map() -> np.ndarray:
    return np.ones((2, 2), dtype=np.float32)


def test_set_depth_rejects_relative_with_meters() -> None:
    store = PerceptionStore()
    with pytest.raises(ValueError, match=r"relative|meters|unit"):
        store.set_depth(
            frame_id=1,
            camera_id="cam0",
            t_capture=1.0,
            depth_map=_small_map(),
            kind=DepthKind.RELATIVE,
            unit="m",
            latency_ms=1.0,
        )
    assert store.snapshot_depth() is None


def test_set_depth_rejects_calibrated_without_meters() -> None:
    store = PerceptionStore()
    with pytest.raises(ValueError, match=r"CAL-04|meters|metric_calibrated"):
        store.set_depth(
            frame_id=1,
            camera_id="cam0",
            t_capture=1.0,
            depth_map=_small_map(),
            kind=DepthKind.METRIC_CALIBRATED,
            unit=None,
            latency_ms=1.0,
        )
    assert store.snapshot_depth() is None


def test_set_depth_accepts_metric_estimated_with_m() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=2,
        camera_id="cam0",
        t_capture=2.0,
        depth_map=_small_map(),
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
        latency_ms=2.0,
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.kind == DepthKind.METRIC_ESTIMATED
    assert snap.unit == "m"


def test_set_depth_accepts_relative_unit_none() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=3,
        camera_id="cam0",
        t_capture=3.0,
        depth_map=_small_map(),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.kind == DepthKind.RELATIVE
    assert snap.unit is None


def test_set_depth_accepts_calibrated_with_m() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=4,
        camera_id="cam0",
        t_capture=4.0,
        depth_map=_small_map(),
        kind=DepthKind.METRIC_CALIBRATED,
        unit="m",
        latency_ms=1.0,
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.kind == DepthKind.METRIC_CALIBRATED
    assert snap.unit == "m"


def test_set_depth_reject_leaves_prior_product_unchanged() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=10,
        camera_id="cam0",
        t_capture=10.0,
        depth_map=_small_map(),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )
    with pytest.raises(ValueError):
        store.set_depth(
            frame_id=11,
            camera_id="cam0",
            t_capture=11.0,
            depth_map=_small_map(),
            kind=DepthKind.RELATIVE,
            unit="m",
            latency_ms=1.0,
        )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.frame_id == 10
    assert snap.kind == DepthKind.RELATIVE
    assert snap.unit is None
