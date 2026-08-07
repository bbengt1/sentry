"""CAM-04: RTSP OpenCV source (mocked VideoCapture — no live RTSP in CI)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.plugins.registry import PluginRegistry, register_builtins
from sentry_ai.sources.errors import SourceDisconnected
from sentry_ai.sources.opencv_source import OpenCVSource, RtspSource

# No live RTSP servers in CI — all tests mock cv2.VideoCapture.


def _fake_bgr(h: int = 48, w: int = 64) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_rtsp_open_passes_url_to_videocapture() -> None:
    url = "rtsp://example.invalid/stream"
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, _fake_bgr())

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    with patch(vc_path, return_value=cap) as vc:
        source = RtspSource(url=url, camera_id="rtsp0")
        source.open()
        try:
            vc.assert_called_once_with(url)
            assert source.name == "rtsp"
            assert source.target == url
            image = source.read()
            assert isinstance(image, ImageFrame)
            assert image.camera_id == "rtsp0"
            assert image.frame_id == 0
        finally:
            source.close()
            cap.release.assert_called()


def test_rtsp_failed_read_raises_source_disconnected() -> None:
    url = "rtsp://example.invalid/stream"
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (False, None)

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    with patch(vc_path, return_value=cap):
        source = OpenCVSource(
            target=url,
            camera_id="rtsp0",
            name="rtsp",
            loop_file=False,
        )
        source.open()
        try:
            with pytest.raises(SourceDisconnected):
                source.read()
        finally:
            source.close()


def test_rtsp_empty_url_rejected() -> None:
    with pytest.raises(ValueError, match="empty"):
        RtspSource(url="", camera_id="rtsp0")


def test_rtsp_registered_as_builtin() -> None:
    registry = PluginRegistry()
    register_builtins(registry)
    assert "rtsp" in registry.list_sources()
    cls = registry.get_source("rtsp")
    assert cls is RtspSource
