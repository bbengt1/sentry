"""Unit tests for FFmpeg AVFoundation Continuity capture helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sentry_ai.sources.errors import SourceDisconnected, SourceError
from sentry_ai.sources.ffmpeg_avfoundation import (
    FfmpegAvFoundationSource,
    list_ffmpeg_av_video_devices,
    match_ffmpeg_device_index,
)

_FFMPEG_LIST_STDERR = """
[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] FaceTime HD Camera
[AVFoundation indev @ 0x1] [1] Brent's 16max pro Camera
[AVFoundation indev @ 0x1] [2] Brent's 16max pro Desk View Camera
[AVFoundation indev @ 0x1] [3] Capture screen 0
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] MacBook Pro Microphone
"""


def test_list_ffmpeg_av_video_devices_parses_names() -> None:
    def fake_run(*_a, **_k):
        return SimpleNamespace(returncode=1, stdout="", stderr=_FFMPEG_LIST_STDERR)

    devs = list_ffmpeg_av_video_devices(run_subprocess=fake_run)
    assert devs == [
        (0, "FaceTime HD Camera"),
        (1, "Brent's 16max pro Camera"),
        (2, "Brent's 16max pro Desk View Camera"),
    ]


def test_match_ffmpeg_prefers_continuity_not_desk_view() -> None:
    devs = [
        (0, "FaceTime HD Camera"),
        (1, "Brent's 16max pro Camera"),
        (2, "Brent's 16max pro Desk View Camera"),
    ]
    m = match_ffmpeg_device_index(None, prefer_continuity=True, devices=devs)
    assert m is not None
    assert m[0] == 1
    assert "Desk View" not in m[1]

    m2 = match_ffmpeg_device_index(
        "Brent's 16max pro Camera",
        prefer_continuity=False,
        devices=devs,
    )
    assert m2 == (1, "Brent's 16max pro Camera")


def test_ffmpeg_source_read_reshapes_bgr() -> None:
    w, h = 64, 48
    frame = np.full((h, w, 3), 40, dtype=np.uint8)
    raw = frame.tobytes()

    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read = MagicMock(return_value=raw)
    proc.poll = MagicMock(return_value=None)
    proc.stderr = None

    src = FfmpegAvFoundationSource(
        device_index=1,
        camera_id="usb1",
        width=w,
        height=h,
        device_label="Test Continuity",
    )
    src._proc = proc
    out = src.read()
    assert out.image_bgr.shape == (h, w, 3)
    assert int(out.image_bgr.mean()) == 40
    assert out.camera_id == "usb1"


def test_ffmpeg_source_short_read_disconnects() -> None:
    proc = MagicMock()
    proc.stdout = MagicMock()
    proc.stdout.read = MagicMock(return_value=b"xx")
    proc.poll = MagicMock(return_value=1)
    proc.stderr = None
    src = FfmpegAvFoundationSource(device_index=1, width=2, height=2)
    src._proc = proc
    with pytest.raises(SourceDisconnected):
        src.read()


def test_ffmpeg_source_open_requires_ffmpeg() -> None:
    with patch(
        "sentry_ai.sources.ffmpeg_avfoundation.ffmpeg_available",
        return_value=False,
    ):
        src = FfmpegAvFoundationSource(device_index=1)
        with pytest.raises(SourceError, match="ffmpeg"):
            src.open()
