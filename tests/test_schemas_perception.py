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
    forbidden = {"cmd", "velocity", "motor", "path_plan", "motor_command"}
    fields = set(PerceptionFrame.model_fields)
    assert fields.isdisjoint(forbidden)


def test_detection_and_free_space_placeholders() -> None:
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
        free_space=FreeSpacePayload(obstacle_count=0),
    )
    assert pf.detections is not None
    assert pf.detections[0].class_name == "person"
    assert pf.free_space is not None
    assert pf.free_space.obstacle_count == 0
