"""EDGE-04: Multi camera_id identity contracts (schema + store).

v1 is a **single active source** pipeline — multi-cam fusion / calibration
is deferred. ``camera_id`` is the extension key so integrators can distinguish
identities when they later run multiple sources outside this process.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentry_ai.schemas import Frame, PerceptionFrame
from sentry_ai.schemas.perception import Detection
from sentry_ai.state.perception_store import DetectionProduct, PerceptionStore


def test_distinct_frame_camera_ids_are_independent_identities() -> None:
    """cam0 vs cam1 (or cam_left/cam_right) must not collapse in schema sense."""
    a = Frame(frame_id=0, camera_id="cam0", t_capture=1.0)
    b = Frame(frame_id=0, camera_id="cam1", t_capture=1.0)
    assert a.camera_id != b.camera_id
    assert a.camera_id == "cam0"
    assert b.camera_id == "cam1"

    left = Frame(frame_id=1, camera_id="cam_left", t_capture=2.0)
    right = Frame(frame_id=1, camera_id="cam_right", t_capture=2.0)
    assert left.camera_id != right.camera_id
    assert {left.camera_id, right.camera_id} == {"cam_left", "cam_right"}


def test_distinct_perception_frame_camera_ids() -> None:
    a = PerceptionFrame(frame_id=0, camera_id="cam0", t_capture=1.0)
    b = PerceptionFrame(frame_id=0, camera_id="cam1", t_capture=1.0)
    assert a.camera_id != b.camera_id
    dumped = {a.camera_id, b.camera_id}
    assert dumped == {"cam0", "cam1"}


def test_empty_camera_id_rejected_on_frame_and_perception() -> None:
    with pytest.raises(ValidationError):
        Frame(frame_id=0, camera_id="", t_capture=1.0)
    with pytest.raises(ValidationError):
        PerceptionFrame(frame_id=0, camera_id="", t_capture=1.0)


def test_detection_products_preserve_distinct_camera_ids() -> None:
    """Store products carry camera_id; two identities do not fuse in schema.

    v1 PerceptionStore is keep-latest single-slot — writing cam1 overwrites
    cam0. That is intentional (single active source). The products themselves
    remain distinct identity carriers for multi-cam extension later.
    """
    det = Detection(
        class_name="person",
        confidence=0.9,
        bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
    )
    p0 = DetectionProduct(
        frame_id=0,
        camera_id="cam0",
        t_capture=1.0,
        detections=[det],
        latency_ms=1.0,
    )
    p1 = DetectionProduct(
        frame_id=0,
        camera_id="cam1",
        t_capture=1.0,
        detections=[det],
        latency_ms=1.0,
    )
    assert p0.camera_id != p1.camera_id
    assert p0.camera_id == "cam0"
    assert p1.camera_id == "cam1"

    store = PerceptionStore()
    store.set_detections(
        frame_id=0,
        camera_id="cam0",
        t_capture=1.0,
        detections=[det],
        latency_ms=2.0,
    )
    snap0 = store.snapshot()
    assert snap0 is not None
    assert snap0.camera_id == "cam0"

    store.set_detections(
        frame_id=1,
        camera_id="cam1",
        t_capture=2.0,
        detections=[det],
        latency_ms=3.0,
    )
    snap1 = store.snapshot()
    assert snap1 is not None
    # Keep-latest overwrites; camera_id on the product is still the writer's id
    assert snap1.camera_id == "cam1"
    assert snap1.camera_id != "cam0"
