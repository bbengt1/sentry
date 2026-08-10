"""Tests for AVFoundation uniqueID capture helper wiring."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sentry_ai.sources.avfoundation_unique import AvFoundationUniqueSource
from sentry_ai.sources.errors import SourceDisconnected, SourceError


def test_unique_source_read_decodes_length_prefixed_jpeg() -> None:
    # Minimal 1x1 JPEG
    import cv2

    ok, buf = cv2.imencode(".jpg", np.zeros((8, 8, 3), dtype=np.uint8))
    assert ok
    jpeg = buf.tobytes()
    header = len(jpeg).to_bytes(4, "big")

    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read = MagicMock(side_effect=[header, jpeg])
    proc.poll = MagicMock(return_value=None)

    src = AvFoundationUniqueSource(
        unique_id="UID-1",
        camera_id="usb1",
        device_label="Continuity",
    )
    src._proc = proc
    frame = src.read()
    assert frame.image_bgr.ndim == 3
    assert frame.camera_id == "usb1"


def test_unique_source_open_requires_binary() -> None:
    with patch(
        "sentry_ai.sources.avfoundation_unique.ensure_capture_av_binary",
        return_value=None,
    ):
        src = AvFoundationUniqueSource(unique_id="UID-1")
        with pytest.raises(SourceError, match="capture_av_device|swift"):
            src.open()


def test_unique_source_short_header_disconnects() -> None:
    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read = MagicMock(return_value=b"\x00\x00")
    proc.poll = MagicMock(return_value=1)
    src = AvFoundationUniqueSource(unique_id="UID-1")
    src._proc = proc
    with pytest.raises(SourceDisconnected):
        src.read()
