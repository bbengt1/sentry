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

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    with (
        patch(vc_path, return_value=cap) as vc,
        patch("sentry_ai.sources.opencv_source.sys.platform", "linux"),
    ):
        source = UsbSource(device=0, camera_id="usb0")
        source.open()
        try:
            vc.assert_called_once_with(0)
            # CAP_PROP_BUFFERSIZE; mock set should be called with value 1
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


def test_usb_open_uses_avfoundation_on_macos() -> None:
    """macOS device indices must match sentry cameras (CAP_AVFOUNDATION)."""
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (True, _fake_bgr())

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    avf = "sentry_ai.sources.opencv_source.cv2.CAP_AVFOUNDATION"
    with (
        patch(vc_path, return_value=cap) as vc,
        patch("sentry_ai.sources.opencv_source.sys.platform", "darwin"),
        patch(avf, 1200, create=True),
    ):
        source = UsbSource(device=1, camera_id="usb1")
        source.open()
        try:
            # Second arg is AVFoundation preference
            assert vc.call_args[0][0] == 1
            assert vc.call_args[0][1] == 1200
            # Warm-up read attempted after open
            assert cap.read.called
        finally:
            source.close()


def test_usb_open_no_frames_raises_clear_continuity_hint() -> None:
    cap = MagicMock()
    cap.isOpened.return_value = True
    cap.read.return_value = (False, None)

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    with (
        patch(vc_path, return_value=cap),
        patch("sentry_ai.sources.opencv_source.sys.platform", "linux"),
        patch("sentry_ai.sources.opencv_source.time.sleep", return_value=None),
    ):
        source = UsbSource(device=1, camera_id="usb1")
        with pytest.raises(SourceError, match="no frames|Continuity|cameras"):
            source.open()


def test_usb_open_failure_raises_source_error() -> None:
    cap = MagicMock()
    cap.isOpened.return_value = False

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    with patch(vc_path, return_value=cap):
        source = OpenCVSource(target=0, camera_id="usb0", name="usb")
        with pytest.raises((SourceError, RuntimeError), match="0"):
            source.open()


def test_failed_read_raises_source_disconnected() -> None:
    cap = MagicMock()
    cap.isOpened.return_value = True
    # Warm-up succeeds once; later read fails (post-open disconnect).
    cap.read.side_effect = [
        (True, _fake_bgr()),
        (False, None),
    ]

    vc_path = "sentry_ai.sources.opencv_source.cv2.VideoCapture"
    with (
        patch(vc_path, return_value=cap),
        patch("sentry_ai.sources.opencv_source.sys.platform", "linux"),
    ):
        source = OpenCVSource(
            target=0,
            camera_id="usb0",
            name="usb",
            loop_file=False,
        )
        source.open()
        try:
            with pytest.raises(SourceDisconnected):
                source.read()
        finally:
            source.close()


def test_empty_path_raises_value_error() -> None:
    with pytest.raises(ValueError, match="empty"):
        OpenCVSource(target="", camera_id="file0", name="file")
