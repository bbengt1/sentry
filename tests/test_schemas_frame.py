"""FOUND-02: Frame schema identity fields (frame_id, camera_id, timestamps)."""

from __future__ import annotations

import time

import pytest
from pydantic import ValidationError

from sentry_ai.schemas import Frame


def test_frame_valid_minimal_identity() -> None:
    """Frame with frame_id, camera_id, and epoch t_capture validates."""
    t = time.time()
    frame = Frame(frame_id=0, camera_id="cam0", t_capture=t)
    assert frame.frame_id == 0
    assert frame.camera_id == "cam0"
    assert frame.t_capture == t
    assert frame.t_ingest is None


def test_frame_missing_camera_id_raises() -> None:
    with pytest.raises(ValidationError):
        Frame(frame_id=0, t_capture=time.time())  # type: ignore[call-arg]


def test_frame_missing_frame_id_raises() -> None:
    with pytest.raises(ValidationError):
        Frame(camera_id="cam0", t_capture=time.time())  # type: ignore[call-arg]


def test_frame_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        Frame(
            frame_id=0,
            camera_id="cam0",
            t_capture=time.time(),
            unexpected="nope",  # type: ignore[call-arg]
        )


def test_frame_rejects_negative_frame_id() -> None:
    with pytest.raises(ValidationError):
        Frame(frame_id=-1, camera_id="cam0", t_capture=time.time())


def test_frame_rejects_empty_camera_id() -> None:
    with pytest.raises(ValidationError):
        Frame(frame_id=0, camera_id="", t_capture=time.time())


def test_make_synthetic_frame_factory(synthetic_frame_factory) -> None:
    frame = synthetic_frame_factory(frame_id=7)
    assert frame.frame_id == 7
    assert frame.camera_id == "synthetic0"
    assert isinstance(frame.t_capture, float)
    assert frame.t_ingest is not None
