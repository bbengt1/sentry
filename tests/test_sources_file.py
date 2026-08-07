"""CAM-02: OpenCV file source reads fixture frames with increasing frame_id."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.sources.opencv_source import FileSource, OpenCVSource


def _write_sample_clip(path: Path, frames: int = 5, width: int = 32, height: int = 24) -> Path:
    """Write a short BGR clip for file-source tests (no shell; pure OpenCV)."""
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, 10.0, (width, height))
    assert writer.isOpened(), f"VideoWriter failed for {path}"
    try:
        for i in range(frames):
            img = np.zeros((height, width, 3), dtype=np.uint8)
            img[:, :, 0] = (i * 40) % 256  # blue channel ramp
            writer.write(img)
    finally:
        writer.release()
    return path


@pytest.fixture
def sample_clip(tmp_path: Path) -> Path:
    return _write_sample_clip(tmp_path / "sample_clip.mp4", frames=5)


def test_file_source_reads_multiple_frames(sample_clip: Path) -> None:
    source = FileSource(path=str(sample_clip), camera_id="file0", loop_file=False)
    source.open()
    try:
        frames: list[ImageFrame] = []
        for _ in range(3):
            frames.append(source.read())
        assert frames[0].frame_id == 0
        assert frames[1].frame_id == 1
        assert frames[2].frame_id == 2
        for image in frames:
            assert isinstance(image, ImageFrame)
            assert image.image_bgr.ndim == 3
            assert image.image_bgr.shape[2] == 3
            assert image.image_bgr.dtype == np.uint8
            assert image.meta.width == image.image_bgr.shape[1]
            assert image.meta.height == image.image_bgr.shape[0]
    finally:
        source.close()


def test_file_loop_rewinds_on_eof(sample_clip: Path) -> None:
    source = OpenCVSource(
        target=str(sample_clip),
        camera_id="file0",
        name="file",
        loop_file=True,
    )
    source.open()
    try:
        # Clip has 5 frames; reading more than that should loop without error.
        ids = [source.read().frame_id for _ in range(8)]
        assert ids == list(range(8))
    finally:
        source.close()


def test_file_empty_path_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        FileSource(path="", camera_id="file0")
