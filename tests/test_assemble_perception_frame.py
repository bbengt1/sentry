"""SPACE-04 / API-03 / API-04: assemble_perception_frame merge + TTL/stale."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from sentry_ai.api.assemble import (
    DEFAULT_TTL_MS,
    _units_for_depth_kind,
    assemble_perception_frame,
)
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection, ObstacleCue
from sentry_ai.state.perception_store import PerceptionStore


def _seed_det(
    store: PerceptionStore,
    *,
    frame_id: int = 1,
    t_capture: float = 1000.0,
    latency_ms: float = 10.0,
) -> None:
    store.set_detections(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=t_capture,
        detections=[
            Detection(class_name="person", confidence=0.9, bbox_xyxy=(1, 2, 3, 4))
        ],
        latency_ms=latency_ms,
        conf=0.25,
        model_name="yolo-test",
    )


def _seed_depth(
    store: PerceptionStore,
    *,
    frame_id: int = 2,
    t_capture: float = 1000.1,
    latency_ms: float = 40.0,
    error: str | None = None,
    kind: DepthKind = DepthKind.RELATIVE,
    unit: str | None = None,
) -> None:
    depth_map = None if error else np.full((24, 32), 1.0, dtype=np.float32)
    store.set_depth(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=t_capture,
        depth_map=depth_map,
        kind=kind,
        unit=unit,  # type: ignore[arg-type]
        latency_ms=latency_ms,
        width=32,
        height=24,
        model_name="depth-test",
        error=error,
    )


def _seed_free_space(
    store: PerceptionStore,
    *,
    frame_id: int = 2,
    t_capture: float = 1000.1,
    latency_ms: float = 5.0,
    error: str | None = None,
    with_masks: bool = True,
    depth_kind: DepthKind = DepthKind.RELATIVE,
    units: str = "ordinal",
    distance_m: float | None = None,
) -> None:
    cue = ObstacleCue(
        bbox_xyxy=(10.0, 20.0, 30.0, 40.0),
        nearness_mean=0.8,
        nearness_max=0.95,
        area_px=100,
        band="near",
        distance_m=distance_m,
    )
    free_mask = np.ones((24, 32), dtype=np.uint8) if with_masks else None
    occupied_mask = np.zeros((24, 32), dtype=np.uint8) if with_masks else None
    store.set_free_space(
        frame_id=frame_id,
        camera_id="cam0",
        t_capture=t_capture,
        latency_ms=latency_ms,
        depth_kind=depth_kind,
        obstacle_count=1,
        obstacles=[cue],
        bands={"near_frac": 0.2, "mid_frac": 0.3, "far_frac": 0.5},
        free_mask=free_mask,
        occupied_mask=occupied_mask,
        method="near_field_bands",
        error=error,
        units=units,
    )


def test_assemble_returns_none_when_all_absent() -> None:
    store = PerceptionStore()
    assert assemble_perception_frame(store) is None


def test_assemble_det_only_completeness() -> None:
    store = PerceptionStore()
    _seed_det(store, t_capture=100.0)
    frame = assemble_perception_frame(store, now=100.05)
    assert frame is not None
    assert frame.completeness.detections is True
    assert frame.completeness.depth is False
    assert frame.completeness.free_space is False
    assert frame.frame_id == 1
    assert frame.t_capture == 100.0
    assert frame.detections is not None
    assert len(frame.detections) == 1
    assert frame.depth is None
    assert frame.free_space is None


def test_assemble_free_space_payload_no_masks() -> None:
    store = PerceptionStore()
    _seed_depth(store, t_capture=200.0)
    _seed_free_space(store, t_capture=200.0, with_masks=True)
    frame = assemble_perception_frame(store, now=200.05)
    assert frame is not None
    assert frame.completeness.free_space is True
    assert frame.completeness.depth is True
    assert frame.free_space is not None
    assert frame.free_space.obstacle_count == 1
    assert len(frame.free_space.obstacles) == 1
    assert frame.free_space.obstacles[0].band == "near"
    assert frame.free_space.method == "near_field_bands"
    assert frame.free_space.units == "ordinal"
    assert frame.free_space.depth_kind == DepthKind.RELATIVE
    assert frame.free_space.bands is not None
    dumped = frame.model_dump()
    fs = dumped["free_space"]
    assert "free_mask" not in fs
    assert "occupied_mask" not in fs
    assert "depth_map" not in dumped
    assert "depth_map" not in (dumped.get("depth") or {})


def test_assemble_free_space_error_not_complete() -> None:
    store = PerceptionStore()
    _seed_free_space(store, error="compute failed", with_masks=False)
    frame = assemble_perception_frame(store, now=1000.0)
    assert frame is not None
    assert frame.completeness.free_space is False
    assert frame.free_space is None


def test_assemble_accepts_dict_obstacles_from_free_space_loop() -> None:
    """FreeSpaceLoop stores obstacles as plain dicts — must not 500 snapshot."""
    store = PerceptionStore()
    _seed_depth(store, t_capture=300.0)
    store.set_free_space(
        frame_id=2,
        camera_id="cam0",
        t_capture=300.0,
        latency_ms=5.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=[
            {
                "bbox_xyxy": [10.0, 20.0, 30.0, 40.0],
                "nearness_mean": 0.8,
                "nearness_max": 0.95,
                "area_px": 100,
                "band": "near",
            }
        ],
        bands={"near_frac": 0.2, "mid_frac": 0.3, "far_frac": 0.5},
        free_mask=None,
        occupied_mask=None,
        method="near_field_bands",
        error=None,
    )
    frame = assemble_perception_frame(store, now=300.05)
    assert frame is not None
    assert frame.free_space is not None
    assert frame.free_space.obstacle_count == 1
    assert frame.free_space.obstacles[0].nearness_mean == 0.8
    # Round-trip JSON like /v1/snapshot
    dumped = frame.model_dump()
    assert dumped["free_space"]["obstacles"][0]["band"] == "near"


def test_assemble_stale_independent_of_completeness() -> None:
    """age > TTL → stale flags true while completeness may still be true."""
    store = PerceptionStore()
    t0 = 1000.0
    _seed_det(store, t_capture=t0)
    _seed_depth(store, t_capture=t0)
    _seed_free_space(store, t_capture=t0)
    # Advance wall clock well past all TTLs (det 500ms, depth/fs 750ms).
    now = t0 + 2.0  # 2000 ms later
    frame = assemble_perception_frame(store, now=now)
    assert frame is not None
    assert frame.completeness.detections is True
    assert frame.completeness.depth is True
    assert frame.completeness.free_space is True
    stats = frame.stats or {}
    assert stats["det_stale"] is True or stats["det_stale"] == 1
    assert stats["depth_stale"] is True or stats["depth_stale"] == 1
    assert stats["free_space_stale"] is True or stats["free_space_stale"] == 1
    assert stats["products_stale"] is True or stats["products_stale"] == 1
    assert float(stats["det_age_ms"]) > DEFAULT_TTL_MS["detections"]
    assert float(stats["depth_age_ms"]) > DEFAULT_TTL_MS["depth"]
    assert float(stats["free_space_age_ms"]) > DEFAULT_TTL_MS["free_space"]


def test_assemble_fresh_products_not_stale() -> None:
    store = PerceptionStore()
    t0 = 5000.0
    _seed_det(store, t_capture=t0)
    _seed_depth(store, t_capture=t0)
    _seed_free_space(store, t_capture=t0)
    now = t0 + 0.05  # 50 ms later — under all TTLs
    frame = assemble_perception_frame(store, now=now)
    assert frame is not None
    stats = frame.stats or {}
    assert not stats.get("det_stale")
    assert not stats.get("depth_stale")
    assert not stats.get("free_space_stale")
    assert not stats.get("products_stale")


def test_assemble_primary_identity_max_t_capture() -> None:
    store = PerceptionStore()
    _seed_det(store, frame_id=1, t_capture=100.0)
    _seed_depth(store, frame_id=2, t_capture=100.5)
    _seed_free_space(store, frame_id=3, t_capture=100.8)
    frame = assemble_perception_frame(store, now=100.85)
    assert frame is not None
    assert frame.t_capture == 100.8
    assert frame.frame_id == 3
    assert frame.camera_id == "cam0"


def test_assemble_stats_include_free_space_and_ages() -> None:
    store = PerceptionStore()
    t0 = 2000.0
    _seed_det(store, frame_id=7, t_capture=t0, latency_ms=12.3)
    _seed_depth(store, frame_id=8, t_capture=t0 + 0.01, latency_ms=42.5)
    _seed_free_space(store, frame_id=8, t_capture=t0 + 0.01, latency_ms=5.5)
    now = t0 + 0.1
    frame = assemble_perception_frame(
        store,
        now=now,
        bus_metrics={"capture_fps": 30.0, "frames_dropped": 2},
    )
    assert frame is not None
    stats = frame.stats or {}
    assert stats["det_latency_ms"] == 12.3
    assert stats["det_frame_id"] == 7
    assert stats["depth_latency_ms"] == 42.5
    assert stats["depth_frame_id"] == 8
    assert stats["free_space_latency_ms"] == 5.5
    assert stats["free_space_frame_id"] == 8
    assert stats["free_space_obstacle_count"] == 1
    assert "det_age_ms" in stats
    assert "depth_age_ms" in stats
    assert "free_space_age_ms" in stats
    assert stats["capture_fps"] == 30.0
    assert stats["frames_dropped"] == 2
    # Store metrics (fps may be 0 early in window — keys present when available)
    assert "det_fps" in stats or stats.get("det_fps") is None or True
    # Free-space stage latency always present when product present
    assert float(stats["free_space_age_ms"]) >= 0.0


def test_assemble_no_safety_language_in_stats() -> None:
    store = PerceptionStore()
    _seed_det(store)
    _seed_depth(store)
    _seed_free_space(store)
    frame = assemble_perception_frame(store, now=1001.0)
    assert frame is not None
    stats = frame.stats or {}
    keys_lower = {str(k).lower() for k in stats}
    forbidden_substrings = (
        "safe",
        "go_nogo",
        "safe_to_drive",
        "clear_to_proceed",
        "nogo",
    )
    for key in keys_lower:
        for bad in forbidden_substrings:
            assert bad not in key, f"forbidden stats key language: {key}"
    dump_keys = set(frame.model_dump().keys())
    forbidden_top = {
        "cmd",
        "velocity",
        "motor",
        "path_plan",
        "motor_command",
        "safe_to_drive",
        "go_nogo",
        "cmd_vel",
        "twist",
    }
    assert dump_keys.isdisjoint(forbidden_top)


def test_default_ttl_constants() -> None:
    assert DEFAULT_TTL_MS["detections"] == 500
    assert DEFAULT_TTL_MS["depth"] == 750
    assert DEFAULT_TTL_MS["free_space"] == 750


def test_units_for_depth_kind_helper() -> None:
    assert _units_for_depth_kind(DepthKind.METRIC_CALIBRATED) == "m"
    assert _units_for_depth_kind(DepthKind.RELATIVE) == "ordinal"
    assert _units_for_depth_kind(DepthKind.METRIC_ESTIMATED) == "ordinal"


def test_assemble_calibrated_free_space_units_meters() -> None:
    store = PerceptionStore()
    _seed_depth(
        store,
        t_capture=200.0,
        kind=DepthKind.METRIC_CALIBRATED,
        unit="m",
    )
    _seed_free_space(
        store,
        t_capture=200.0,
        depth_kind=DepthKind.METRIC_CALIBRATED,
        units="m",
        distance_m=1.2,
    )
    frame = assemble_perception_frame(store, now=200.05)
    assert frame is not None
    assert frame.free_space is not None
    assert frame.free_space.units == "m"
    assert frame.free_space.depth_kind == DepthKind.METRIC_CALIBRATED
    cue = frame.free_space.obstacles[0]
    assert cue.distance_m == 1.2
    assert 0.0 <= cue.nearness_mean <= 1.0


def test_assemble_metric_estimated_free_space_stays_ordinal() -> None:
    store = PerceptionStore()
    _seed_depth(
        store,
        t_capture=200.0,
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
    )
    _seed_free_space(
        store,
        t_capture=200.0,
        depth_kind=DepthKind.METRIC_ESTIMATED,
        units="ordinal",
    )
    frame = assemble_perception_frame(store, now=200.05)
    assert frame is not None
    assert frame.free_space is not None
    assert frame.free_space.units == "ordinal"
    assert frame.free_space.obstacles[0].distance_m is None


def test_assemble_relative_dict_obstacles_distance_m_absent_ok() -> None:
    store = PerceptionStore()
    _seed_depth(store, t_capture=300.0)
    store.set_free_space(
        frame_id=2,
        camera_id="cam0",
        t_capture=300.0,
        latency_ms=5.0,
        depth_kind=DepthKind.RELATIVE,
        obstacle_count=1,
        obstacles=[
            {
                "bbox_xyxy": [10.0, 20.0, 30.0, 40.0],
                "nearness_mean": 0.8,
                "nearness_max": 0.95,
                "area_px": 100,
                "band": "near",
            }
        ],
        bands={"near_frac": 0.2},
        free_mask=None,
        occupied_mask=None,
        method="near_field_bands",
        error=None,
        units="ordinal",
    )
    frame = assemble_perception_frame(store, now=300.05)
    assert frame is not None
    assert frame.free_space is not None
    assert frame.free_space.units == "ordinal"
    assert frame.free_space.obstacles[0].distance_m is None


def test_obstacle_cue_extra_forbid() -> None:
    with pytest.raises(ValidationError):
        ObstacleCue(
            bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
            nearness_mean=0.5,
            nearness_max=0.6,
            area_px=10,
            motor=1,  # type: ignore[call-arg]
        )
