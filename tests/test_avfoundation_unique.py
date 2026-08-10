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


def test_unique_source_require_non_black_fails_on_black() -> None:
    """Continuity path must not stay open on pure-black streams."""
    import cv2

    # Near-black JPEG (mean ~0) — Continuity "listed but not streaming".
    ok, buf = cv2.imencode(".jpg", np.zeros((16, 16, 3), dtype=np.uint8))
    assert ok
    jpeg = buf.tobytes()
    header = len(jpeg).to_bytes(4, "big")

    def _read(n: int) -> bytes:
        if n == 4:
            return header
        return jpeg

    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read = MagicMock(side_effect=_read)
    proc.poll = MagicMock(return_value=None)
    proc.stderr = MagicMock()
    proc.stderr.read = MagicMock(return_value=b"capture_av_device: black test\n")

    with patch(
        "sentry_ai.sources.avfoundation_unique.ensure_capture_av_binary",
        return_value=MagicMock(),
    ), patch(
        "sentry_ai.sources.avfoundation_unique.subprocess.Popen",
        return_value=proc,
    ):
        src = AvFoundationUniqueSource(
            unique_id="UID-1",
            require_non_black=True,
            warm_up_seconds=0.15,
        )
        with pytest.raises(SourceError, match="black|Continuity|FaceTime"):
            src.open()


def test_unique_source_require_non_black_rejects_near_black_noise() -> None:
    """mean≈7 Continuity noise must not count as a valid stream."""
    import cv2

    nearly = np.full((32, 32, 3), 8, dtype=np.uint8)
    ok, buf = cv2.imencode(".jpg", nearly)
    assert ok
    jpeg = buf.tobytes()
    header = len(jpeg).to_bytes(4, "big")

    def _read(n: int) -> bytes:
        if n == 4:
            return header
        return jpeg

    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read = MagicMock(side_effect=_read)
    proc.poll = MagicMock(return_value=None)
    proc.stderr = MagicMock()
    proc.stderr.read = MagicMock(return_value=b"")

    with patch(
        "sentry_ai.sources.avfoundation_unique.ensure_capture_av_binary",
        return_value=MagicMock(),
    ), patch(
        "sentry_ai.sources.avfoundation_unique.subprocess.Popen",
        return_value=proc,
    ):
        src = AvFoundationUniqueSource(
            unique_id="UID-1",
            require_non_black=True,
            warm_up_seconds=0.15,
        )
        with pytest.raises(SourceError, match="black|Continuity|FaceTime"):
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
