"""PerceptionStore keep-latest detection + depth products (DET-04 / DEPTH-01)."""

from __future__ import annotations

import threading
import time

import numpy as np

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import DepthPayload, Detection
from sentry_ai.state.perception_store import (
    DepthProduct,
    DetectionProduct,
    PerceptionStore,
)


def _det(name: str = "person", conf: float = 0.9) -> Detection:
    return Detection(
        class_name=name,
        confidence=conf,
        bbox_xyxy=(0.0, 0.0, 10.0, 10.0),
    )


def test_snapshot_none_before_set() -> None:
    store = PerceptionStore()
    assert store.snapshot() is None
    assert store.snapshot_depth() is None


def test_set_detections_returns_product_fields() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=3,
        camera_id="cam0",
        t_capture=1.5,
        detections=[_det()],
        latency_ms=12.5,
        conf=0.25,
        model_name="yolo-fixed",
    )
    snap = store.snapshot()
    assert snap is not None
    assert isinstance(snap, DetectionProduct)
    assert snap.frame_id == 3
    assert snap.camera_id == "cam0"
    assert snap.t_capture == 1.5
    assert len(snap.detections) == 1
    assert snap.detections[0].class_name == "person"
    assert snap.latency_ms == 12.5
    assert snap.conf == 0.25
    assert snap.model_name == "yolo-fixed"
    assert snap.error is None


def test_set_overwrites_keep_latest() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        detections=[_det("a")],
        latency_ms=1.0,
    )
    store.set_detections(
        frame_id=2,
        camera_id="cam0",
        t_capture=2.0,
        detections=[_det("b"), _det("c")],
        latency_ms=2.0,
    )
    snap = store.snapshot()
    assert snap is not None
    assert snap.frame_id == 2
    assert len(snap.detections) == 2
    assert snap.detections[0].class_name == "b"


def test_snapshot_returns_isolated_copy() -> None:
    store = PerceptionStore()
    original = [_det("orig")]
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        detections=original,
        latency_ms=1.0,
    )
    snap = store.snapshot()
    assert snap is not None
    # Mutate returned list and product fields
    snap.detections.append(_det("mutated"))
    snap.detections[0] = _det("replaced")
    # Mutate caller's original list too
    original.append(_det("caller"))

    again = store.snapshot()
    assert again is not None
    assert len(again.detections) == 1
    assert again.detections[0].class_name == "orig"


def test_empty_detections_list_is_valid_product() -> None:
    """Empty list means stage ran with no hits (completeness semantics)."""
    store = PerceptionStore()
    store.set_detections(
        frame_id=9,
        camera_id="cam0",
        t_capture=9.0,
        detections=[],
        latency_ms=3.0,
    )
    snap = store.snapshot()
    assert snap is not None
    assert snap.detections == []
    assert snap.frame_id == 9


def test_set_error_detail() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        detections=[],
        latency_ms=0.0,
        error="predict failed: boom",
    )
    snap = store.snapshot()
    assert snap is not None
    assert snap.error == "predict failed: boom"


def test_concurrent_set_and_snapshot_no_raise() -> None:
    store = PerceptionStore()
    errors: list[BaseException] = []
    stop = threading.Event()

    def writer() -> None:
        i = 0
        try:
            while not stop.is_set():
                store.set_detections(
                    frame_id=i,
                    camera_id="cam0",
                    t_capture=float(i),
                    detections=[_det(f"c{i % 3}")],
                    latency_ms=float(i),
                )
                i += 1
        except BaseException as exc:  # noqa: BLE001 — surface to main
            errors.append(exc)

    def reader() -> None:
        try:
            for _ in range(200):
                _ = store.snapshot()
                time.sleep(0.0005)
        except BaseException as exc:  # noqa: BLE001
            errors.append(exc)

    threads = [
        threading.Thread(target=writer, daemon=True),
        threading.Thread(target=reader, daemon=True),
        threading.Thread(target=reader, daemon=True),
    ]
    for t in threads:
        t.start()
    time.sleep(0.05)
    stop.set()
    for t in threads:
        t.join(timeout=2.0)
    assert errors == []
    # Store should have some product after concurrent writes
    assert store.snapshot() is not None


def test_set_depth_returns_product_fields() -> None:
    store = PerceptionStore()
    depth = np.arange(12, dtype=np.float32).reshape(3, 4)
    store.set_depth(
        frame_id=5,
        camera_id="camD",
        t_capture=2.5,
        depth_map=depth,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=8.0,
        model_name="depth-anything-v2-small",
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert isinstance(snap, DepthProduct)
    assert snap.frame_id == 5
    assert snap.camera_id == "camD"
    assert snap.t_capture == 2.5
    assert snap.kind == DepthKind.RELATIVE
    assert snap.unit is None
    assert snap.width == 4
    assert snap.height == 3
    assert snap.latency_ms == 8.0
    assert snap.model_name == "depth-anything-v2-small"
    assert snap.error is None
    assert snap.min_value == 0.0
    assert snap.max_value == 11.0
    assert snap.mean_value is not None


def test_set_depth_keep_latest_overwrite() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        depth_map=np.ones((2, 2), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )
    store.set_depth(
        frame_id=2,
        camera_id="cam0",
        t_capture=2.0,
        depth_map=np.full((2, 2), 3.0, dtype=np.float32),
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
        latency_ms=2.0,
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.frame_id == 2
    assert snap.kind == DepthKind.METRIC_ESTIMATED
    assert snap.unit == "m"
    assert snap.min_value == 3.0


def test_snapshot_depth_isolates_product() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        depth_map=np.ones((2, 2), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
        model_name="depth",
    )
    snap = store.snapshot_depth()
    assert snap is not None
    snap.frame_id = 999
    snap.model_name = "mutated"
    again = store.snapshot_depth()
    assert again is not None
    assert again.frame_id == 1
    assert again.model_name == "depth"
    assert snap is not again


def test_depth_error_product_without_map() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=3,
        camera_id="cam0",
        t_capture=3.0,
        depth_map=None,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=0.5,
        error="predict failed: boom",
        width=64,
        height=48,
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.error == "predict failed: boom"
    assert snap.depth_map is None
    assert snap.min_value is None
    assert snap.width == 64
    assert snap.height == 48


def test_record_depth_drop_and_metrics_snapshot() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        depth_map=np.zeros((2, 2), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=4.0,
    )
    store.record_depth_drop(2)
    metrics = store.metrics_snapshot()
    assert metrics.depth_frames == 1
    assert metrics.depth_frames_dropped == 2
    assert metrics.last_depth_latency_ms == 4.0
    assert metrics.depth_fps >= 0.0
    # Detection half still present in metrics
    assert metrics.det_frames == 0
    assert metrics.det_frames_dropped == 0


def test_dual_det_and_depth_coexistence() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=10,
        camera_id="cam0",
        t_capture=10.0,
        detections=[_det("person")],
        latency_ms=5.0,
        conf=0.3,
        model_name="yolo-fixed",
    )
    store.set_depth(
        frame_id=11,
        camera_id="cam0",
        t_capture=11.0,
        depth_map=np.ones((4, 4), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=7.0,
        model_name="depth-anything-v2-small",
    )
    det = store.snapshot()
    depth = store.snapshot_depth()
    assert det is not None
    assert depth is not None
    assert det.frame_id == 10
    assert depth.frame_id == 11
    assert len(det.detections) == 1
    assert depth.kind == DepthKind.RELATIVE
    metrics = store.metrics_snapshot()
    assert metrics.det_frames == 1
    assert metrics.depth_frames == 1


def test_depth_product_builds_valid_depth_payload() -> None:
    store = PerceptionStore()
    store.set_depth(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        depth_map=np.ones((3, 5), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=1.0,
    )
    product = store.snapshot_depth()
    assert product is not None
    payload = DepthPayload(
        kind=product.kind,
        unit=product.unit,
        width=product.width,
        height=product.height,
    )
    assert payload.kind == DepthKind.RELATIVE
    assert payload.unit is None


# --- Free-space product (Phase 5 / SPACE-01) ---


def test_snapshot_free_space_none_before_set() -> None:
    store = PerceptionStore()
    assert store.snapshot_free_space() is None


def test_set_free_space_returns_product_fields() -> None:
    store = PerceptionStore()
    free = np.zeros((4, 6), dtype=np.uint8)
    free[2:, :] = 255
    occ = np.zeros((4, 6), dtype=np.uint8)
    occ[2:4, 1:3] = 255
    obstacles = [
        {
            "bbox_xyxy": (1.0, 2.0, 3.0, 4.0),
            "nearness_mean": 0.9,
            "nearness_max": 0.95,
            "area_px": 4,
            "band": "near",
        }
    ]
    bands = {"near_frac": 0.2, "mid_frac": 0.3, "far_frac": 0.5}
    store.set_free_space(
        frame_id=5,
        camera_id="camF",
        t_capture=2.5,
        latency_ms=3.5,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=obstacles,
        bands=bands,
        free_mask=free,
        occupied_mask=occ,
        method="near_field_bands",
    )
    snap = store.snapshot_free_space()
    assert snap is not None
    assert snap.frame_id == 5
    assert snap.camera_id == "camF"
    assert snap.t_capture == 2.5
    assert snap.latency_ms == 3.5
    assert snap.depth_kind == DepthKind.RELATIVE
    assert snap.obstacle_count == 1
    assert len(snap.obstacles) == 1
    assert snap.bands == bands
    assert snap.method == "near_field_bands"
    assert snap.error is None
    assert snap.free_mask is not None
    assert snap.occupied_mask is not None
    assert snap.t_compute > 0.0


def test_set_free_space_keep_latest_overwrite() -> None:
    store = PerceptionStore()
    store.set_free_space(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        latency_ms=1.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        obstacles=[],
        bands={"near_frac": 0.0, "mid_frac": 0.0, "far_frac": 1.0},
    )
    store.set_free_space(
        frame_id=2,
        camera_id="cam0",
        t_capture=2.0,
        latency_ms=2.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=2,
        obstacles=[{"bbox_xyxy": (0, 0, 1, 1), "area_px": 1}],
        bands={"near_frac": 0.5, "mid_frac": 0.25, "far_frac": 0.25},
    )
    snap = store.snapshot_free_space()
    assert snap is not None
    assert snap.frame_id == 2
    assert snap.obstacle_count == 2


def test_snapshot_free_space_isolates_obstacles_and_bands() -> None:
    store = PerceptionStore()
    obstacles = [{"bbox_xyxy": (0.0, 0.0, 1.0, 1.0), "area_px": 1, "band": "near"}]
    bands = {"near_frac": 0.1, "mid_frac": 0.2, "far_frac": 0.7}
    free = np.ones((2, 2), dtype=np.uint8)
    store.set_free_space(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        latency_ms=1.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=obstacles,
        bands=bands,
        free_mask=free,
        occupied_mask=np.zeros((2, 2), dtype=np.uint8),
    )
    snap = store.snapshot_free_space()
    assert snap is not None
    snap.obstacles.append({"mutated": True})
    snap.bands["near_frac"] = 99.0
    snap.frame_id = 999
    again = store.snapshot_free_space()
    assert again is not None
    assert again.frame_id == 1
    assert len(again.obstacles) == 1
    assert again.bands["near_frac"] == 0.1
    assert snap is not again
    # Masks may share array ref (immutable after set)
    assert again.free_mask is free or np.array_equal(again.free_mask, free)


def test_record_free_space_drop_and_metrics() -> None:
    store = PerceptionStore()
    store.set_free_space(
        frame_id=1,
        camera_id="cam0",
        t_capture=1.0,
        latency_ms=4.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        obstacles=[],
        bands={},
    )
    store.record_free_space_drop(3)
    metrics = store.metrics_snapshot()
    assert metrics.free_space_frames == 1
    assert metrics.free_space_frames_dropped == 3
    assert metrics.last_free_space_latency_ms == 4.0
    assert metrics.free_space_fps >= 0.0
    # Det/depth half still present
    assert metrics.det_frames == 0
    assert metrics.depth_frames == 0


def test_triple_product_coexistence() -> None:
    store = PerceptionStore()
    store.set_detections(
        frame_id=10,
        camera_id="cam0",
        t_capture=10.0,
        detections=[_det("person")],
        latency_ms=5.0,
    )
    store.set_depth(
        frame_id=11,
        camera_id="cam0",
        t_capture=11.0,
        depth_map=np.ones((4, 4), dtype=np.float32),
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=7.0,
    )
    store.set_free_space(
        frame_id=11,
        camera_id="cam0",
        t_capture=11.0,
        latency_ms=2.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        obstacles=[],
        bands={"near_frac": 0.0, "mid_frac": 0.0, "far_frac": 1.0},
    )
    assert store.snapshot() is not None
    assert store.snapshot_depth() is not None
    free = store.snapshot_free_space()
    assert free is not None
    assert free.frame_id == 11
    metrics = store.metrics_snapshot()
    assert metrics.det_frames == 1
    assert metrics.depth_frames == 1
    assert metrics.free_space_frames == 1


def test_free_space_error_product() -> None:
    store = PerceptionStore()
    store.set_free_space(
        frame_id=3,
        camera_id="cam0",
        t_capture=3.0,
        latency_ms=0.5,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=0,
        obstacles=[],
        bands={},
        free_mask=None,
        occupied_mask=None,
        error="compute failed: boom",
    )
    snap = store.snapshot_free_space()
    assert snap is not None
    assert snap.error == "compute failed: boom"
    assert snap.obstacle_count == 0
    assert snap.obstacles == []
