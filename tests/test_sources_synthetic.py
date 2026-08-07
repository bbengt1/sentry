"""CAM-03: SyntheticSource yields patterned ImageFrames without hardware."""

from __future__ import annotations

import numpy as np
import pytest

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.synthetic import SyntheticSource


def test_read_returns_image_frame_with_bgr_shape() -> None:
    source = SyntheticSource(camera_id="synthetic0", width=64, height=48, fps=0.0)
    source.open()
    try:
        image = source.read()
        assert isinstance(image, ImageFrame)
        assert isinstance(image.meta, Frame)
        assert image.image_bgr.shape == (48, 64, 3)
        assert image.image_bgr.dtype == np.uint8
        assert image.meta.width == 64
        assert image.meta.height == 48
        assert image.camera_id == "synthetic0"
        Frame.model_validate(image.meta.model_dump())
    finally:
        source.close()


def test_frame_id_starts_at_zero_and_increments() -> None:
    source = SyntheticSource(fps=0.0)
    source.open()
    try:
        first = source.read()
        second = source.read()
        third = source.read()
        assert first.frame_id == 0
        assert second.frame_id == 1
        assert third.frame_id == 2
        assert first.meta.frame_id == 0
        assert second.meta.frame_id == 1
    finally:
        source.close()


def test_read_before_open_raises() -> None:
    source = SyntheticSource(fps=0.0)
    with pytest.raises(RuntimeError, match="not open"):
        source.read()


def test_open_resets_frame_id() -> None:
    source = SyntheticSource(fps=0.0)
    source.open()
    try:
        _ = source.read()
        _ = source.read()
    finally:
        source.close()
    source.open()
    try:
        image = source.read()
        assert image.frame_id == 0
    finally:
        source.close()


def test_patterned_bgr_is_deterministic() -> None:
    source = SyntheticSource(width=32, height=16, fps=0.0)
    source.open()
    try:
        a = source.read()
        source.close()
        source.open()
        b = source.read()
        assert np.array_equal(a.image_bgr, b.image_bgr)
        # Green bar present somewhere
        assert (a.image_bgr[:, :, 1] == 255).any()
    finally:
        source.close()
