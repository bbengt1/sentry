"""FOUND-02/03: PerceptionFrame identity and completeness contracts."""

from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from sentry_ai.schemas import (
    Completeness,
    DepthKind,
    DepthPayload,
    PerceptionFrame,
)


def test_perception_frame_requires_identity() -> None:
    t = time.time()
    pf = PerceptionFrame(frame_id=1, camera_id="cam0", t_capture=t)
    assert pf.frame_id == 1
    assert pf.camera_id == "cam0"
    assert pf.t_capture == t


def test_perception_frame_missing_camera_id_raises() -> None:
    with pytest.raises(ValidationError):
        PerceptionFrame(frame_id=1, t_capture=time.time())  # type: ignore[call-arg]


def test_perception_frame_missing_frame_id_raises() -> None:
    with pytest.raises(ValidationError):
        PerceptionFrame(camera_id="cam0", t_capture=time.time())  # type: ignore[call-arg]


def test_completeness_defaults_all_false() -> None:
    pf = PerceptionFrame(frame_id=0, camera_id="cam0", t_capture=time.time())
    assert pf.completeness.depth is False
    assert pf.completeness.detections is False
    assert pf.completeness.free_space is False
    c = Completeness()
    assert c.depth is False
    assert c.detections is False
    assert c.free_space is False


def test_schema_version_defaults_to_one() -> None:
    pf = PerceptionFrame(frame_id=0, camera_id="cam0", t_capture=time.time())
    assert pf.schema_version == 1


def test_perception_frame_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        PerceptionFrame(
            frame_id=0,
            camera_id="cam0",
            t_capture=time.time(),
            velocity=0.5,  # type: ignore[call-arg]
        )


def test_nested_relative_depth_rejects_meters() -> None:
    with pytest.raises(ValidationError):
        PerceptionFrame(
            frame_id=0,
            camera_id="cam0",
            t_capture=time.time(),
            depth=DepthPayload(kind=DepthKind.RELATIVE, unit="m"),
        )


def test_nested_relative_depth_ok_with_unit_none() -> None:
    pf = PerceptionFrame(
        frame_id=0,
        camera_id="cam0",
        t_capture=time.time(),
        depth=DepthPayload(kind=DepthKind.RELATIVE, unit=None),
        completeness=Completeness(depth=True),
    )
    assert pf.depth is not None
    assert pf.depth.kind == DepthKind.RELATIVE
    assert pf.completeness.depth is True


def test_perception_from_synthetic_frame(synthetic_frame_factory) -> None:
    frame = synthetic_frame_factory(frame_id=3, camera_id="synthetic0")
    pf = PerceptionFrame(
        frame_id=frame.frame_id,
        camera_id=frame.camera_id,
        t_capture=frame.t_capture,
    )
    assert pf.frame_id == frame.frame_id
    assert pf.camera_id == frame.camera_id


def test_no_motor_velocity_cmd_fields() -> None:
    """API-05: PerceptionFrame model_fields must stay perception-only."""
    forbidden = {
        "cmd",
        "velocity",
        "motor",
        "path_plan",
        "motor_command",
        "safe_to_drive",
        "go_nogo",
        "cmd_vel",
        "twist",
        "steering",
        "throttle",
    }
    fields = set(PerceptionFrame.model_fields)
    assert fields.isdisjoint(forbidden)


def test_free_space_payload_rejects_motor_fields() -> None:
    """API-05: FreeSpacePayload rejects control/safety language extras."""
    from sentry_ai.schemas import FreeSpacePayload

    forbidden = {
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
    assert set(FreeSpacePayload.model_fields).isdisjoint(forbidden)
    with pytest.raises(ValidationError):
        FreeSpacePayload(
            depth_kind=DepthKind.RELATIVE,
            safe_to_drive=True,  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError):
        FreeSpacePayload(
            depth_kind=DepthKind.RELATIVE,
            go_nogo="go",  # type: ignore[call-arg]
        )


def test_obstacle_cue_requires_fields_no_distance_m() -> None:
    """SPACE-02: ObstacleCue is ordinal nearness only — never distance_m."""
    from sentry_ai.schemas.perception import ObstacleCue

    cue = ObstacleCue(
        bbox_xyxy=(1.0, 2.0, 3.0, 4.0),
        nearness_mean=0.8,
        nearness_max=0.95,
        area_px=120,
        band="near",
    )
    assert cue.band == "near"
    assert "distance_m" not in ObstacleCue.model_fields
    with pytest.raises(ValidationError):
        ObstacleCue(
            bbox_xyxy=(0, 0, 1, 1),
            nearness_mean=0.5,
            nearness_max=0.6,
            area_px=10,
            distance_m=1.2,  # type: ignore[call-arg]
        )
    with pytest.raises(ValidationError):
        ObstacleCue(
            bbox_xyxy=(0, 0, 1, 1),
            nearness_mean=0.5,
            nearness_max=0.6,
            area_px=10,
            band="ultra",  # type: ignore[arg-type]
        )


def test_free_space_payload_expanded_round_trip() -> None:
    """SPACE-02: FreeSpacePayload carries obstacles, bands, method, units."""
    from sentry_ai.schemas import Detection, FreeSpacePayload
    from sentry_ai.schemas.perception import ObstacleCue

    cue = ObstacleCue(
        bbox_xyxy=[10.0, 20.0, 30.0, 40.0],
        nearness_mean=0.7,
        nearness_max=0.9,
        area_px=200,
        band="mid",
    )
    payload = FreeSpacePayload(
        depth_kind=DepthKind.RELATIVE,
        units="ordinal",
        obstacle_count=1,
        obstacles=[cue],
        bands={"near_frac": 0.1, "mid_frac": 0.2, "far_frac": 0.7},
        width=160,
        height=120,
        roi_bottom_frac=0.55,
    )
    assert payload.method == "near_field_bands"
    assert payload.units == "ordinal"
    assert payload.depth_kind == DepthKind.RELATIVE
    assert payload.obstacle_count == 1
    assert len(payload.obstacles) == 1
    assert payload.obstacles[0].band == "mid"
    dumped = payload.model_dump()
    assert "free_mask" not in dumped
    assert "occupied_mask" not in dumped
    assert "distance_m" not in dumped
    restored = FreeSpacePayload.model_validate(dumped)
    assert restored.obstacle_count == 1
    assert restored.bands is not None
    assert restored.bands["near_frac"] == 0.1

    pf = PerceptionFrame(
        frame_id=0,
        camera_id="cam0",
        t_capture=time.time(),
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
            )
        ],
        free_space=payload,
        completeness=Completeness(detections=True, free_space=True),
    )
    assert pf.detections is not None
    assert pf.detections[0].class_name == "person"
    assert pf.free_space is not None
    assert pf.free_space.obstacle_count == 1
    assert pf.completeness.free_space is True
    # completeness.free_space still defaults false on bare frames
    bare = PerceptionFrame(frame_id=1, camera_id="cam0", t_capture=time.time())
    assert bare.completeness.free_space is False


def test_free_space_payload_rejects_extra_fields() -> None:
    from sentry_ai.schemas import FreeSpacePayload

    with pytest.raises(ValidationError):
        FreeSpacePayload(
            depth_kind=DepthKind.RELATIVE,
            free_mask=[[1]],  # type: ignore[call-arg]
        )


def test_detection_and_free_space_placeholders() -> None:
    """Backward-compatible construction with expanded FreeSpacePayload."""
    from sentry_ai.schemas import Detection, FreeSpacePayload

    pf = PerceptionFrame(
        frame_id=0,
        camera_id="cam0",
        t_capture=time.time(),
        detections=[
            Detection(
                class_name="person",
                confidence=0.9,
                bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
            )
        ],
        free_space=FreeSpacePayload(
            depth_kind=DepthKind.RELATIVE,
            obstacle_count=0,
        ),
    )
    assert pf.detections is not None
    assert pf.detections[0].class_name == "person"
    assert pf.free_space is not None
    assert pf.free_space.obstacle_count == 0
    assert pf.free_space.units == "ordinal"
    assert pf.free_space.method == "near_field_bands"
