"""CAM-01: OpenCV USB source constructs VideoCapture(index) with buffer=1."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.sources.errors import SourceDisconnected, SourceError
from sentry_ai.sources.opencv_source import OpenCVSource, UsbSource


def _fake_bgr(h: int = 48, w: int = 64) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_usb_open_uses_index_and_buffersize() -> None:
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, _fake_bgr())

    with patch("sentry_ai.sources.opencv_source.cv2.VideoCapture", return_value=cap) as vc:
        source = UsbSource(device=0, camera_id="usb0")
        source.open()
        try:
            vc.assert_called_once_with(0)
            # CAP_PROP_BUFFERSIZE = 38 in OpenCV; mock set should be called with 1
            set_calls = [c.args for c in cap.set.call_args_list]
            assert any(args[1] == 1 for args in set_calls), set_calls
            image = source.read()
            assert isinstance(image, ImageFrame)
            assert image.frame_id == 0
            assert image.camera_id == "usb0"
            assert image.image_bgr.shape == (48, 64, 3)
        finally:
            source.close()
            cap.release.assert_called()


def test_usb_open_failure_raises_source_error() -> None:
    cap = MagicMock()
    cap.isOpened.return_value = False

    with patch("sentry_ai.sources.opencv_source.cv2.VideoCapture", return_value=cap):
        source = OpenCVSource(target=0, camera_id="usb0", name="usb")
        with pytest.raises((SourceError, RuntimeError), match="0"):
            source.open()


def test_failed_read_raises_source_disconnected() -> None:
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (False, None)

    with patch("sentry_ai.sources.opencv_source.cv2.VideoCapture", return_value=cap):
        source = OpenCVSource(target=0, camera_id="usb0", name="usb", loop_file=False)
        source.open()
        try:
            with pytest.raises(SourceDisconnected):
                source.read()
        finally:
            source.close()


def test_empty_path_raises_value_error() -> None:
    with pytest.raises(ValueError, match="empty"):
        OpenCVSource(target="", camera_id="file0", name="file")
