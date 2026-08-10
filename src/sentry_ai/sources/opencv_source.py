"""OpenCV-based camera source for USB indices, files, and URL targets.

Uses opencv-python-headless only. Targets are passed directly to
``cv2.VideoCapture`` (no shell). Empty string paths are rejected (T-2-01).

On macOS, integer device indices open with ``CAP_AVFOUNDATION`` so indices
match ``sentry cameras`` / Continuity Camera probes.
"""

from __future__ import annotations

import sys
import time
from typing import Any

import cv2
import numpy as np

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.errors import SourceDisconnected, SourceError

_URL_PREFIXES = ("rtsp://", "rtsps://", "http://", "https://")
# Continuity / AVFoundation often need a few discarded reads after open.
_DEVICE_WARMUP_READS = 8
_DEVICE_WARMUP_SLEEP_S = 0.05


def _is_file_target(target: int | str) -> bool:
    """True for filesystem paths; False for device indices and stream URLs."""
    if not isinstance(target, str):
        return False
    return not target.lower().startswith(_URL_PREFIXES)


def _open_video_capture(target: int | str) -> Any:
    """Open VideoCapture; use AVFoundation for macOS device indices."""
    # Path/index/url only — never via shell (T-2-01).
    if isinstance(target, int) and sys.platform == "darwin":
        api = getattr(cv2, "CAP_AVFOUNDATION", None)
        if api is not None:
            return cv2.VideoCapture(target, api)
    return cv2.VideoCapture(target)


class OpenCVSource:
    """One adapter for USB index, file path, or future RTSP/HTTP URL targets."""

    name: str = "opencv"

    def __init__(
        self,
        target: int | str,
        *,
        camera_id: str,
        name: str = "opencv",
        loop_file: bool = True,
    ) -> None:
        if isinstance(target, str) and target.strip() == "":
            raise ValueError("empty path target is not allowed")
        self.target = target
        self.camera_id = camera_id
        self.name = name
        self.loop_file = loop_file
        self._cap: Any | None = None
        self._next_frame_id = 0
        self._is_file = _is_file_target(target)

    def open(self) -> None:
        self._cap = _open_video_capture(self.target)
        if not self._cap.isOpened():
            self._cap.release()
            self._cap = None
            raise SourceError(f"failed to open source: {self.target!r}")
        # Best-effort low latency (may be ignored by some backends).
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        # Live devices (USB / Continuity): discard a few reads so the first
        # real frame is more likely valid after AVFoundation / Continuity wake.
        if isinstance(self.target, int):
            got_frame = False
            for _ in range(_DEVICE_WARMUP_READS):
                ok, frame = self._cap.read()
                if ok and frame is not None:
                    got_frame = True
                    break
                time.sleep(_DEVICE_WARMUP_SLEEP_S)
            if not got_frame:
                # Leave open — CaptureLoop will reconnect; surface a clear error.
                self._cap.release()
                self._cap = None
                raise SourceError(
                    f"opened device {self.target!r} but no frames yet "
                    f"(macOS Continuity: unlock iPhone, leave Continuity free, "
                    f"use the IDX with OPEN=yes from `sentry cameras`)"
                )
        self._next_frame_id = 0

    def read(self) -> ImageFrame:
        if self._cap is None:
            raise RuntimeError(f"{type(self).__name__} is not open; call open() first")

        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            if self._is_file and self.loop_file:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, bgr = self._cap.read()
            if not ok or bgr is None:
                raise SourceDisconnected(f"no frame from {self.target!r}")

        if not isinstance(bgr, np.ndarray):
            raise SourceDisconnected(f"invalid frame from {self.target!r}")

        h, w = bgr.shape[:2]
        now = time.time()
        meta = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=int(w),
            height=int(h),
        )
        self._next_frame_id += 1
        return ImageFrame(meta=meta, image_bgr=bgr)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None


class UsbSource(OpenCVSource):
    """USB UVC source plugin (device index)."""

    name: str = "usb"

    def __init__(
        self,
        device: int = 0,
        camera_id: str = "usb0",
        *,
        loop_file: bool = False,
    ) -> None:
        super().__init__(
            target=device,
            camera_id=camera_id,
            name="usb",
            loop_file=loop_file,
        )


class FileSource(OpenCVSource):
    """Local video file source plugin."""

    name: str = "file"

    def __init__(
        self,
        path: str,
        camera_id: str = "file0",
        *,
        loop_file: bool = True,
    ) -> None:
        super().__init__(
            target=path,
            camera_id=camera_id,
            name="file",
            loop_file=loop_file,
        )


class RtspSource(OpenCVSource):
    """Network/IP camera source via OpenCV URL (CAM-04 best-effort).

    OpenCV FFmpeg backend only — no PyAV/GStreamer in Phase 2.
    See docs/camera-sources.md for known latency and reliability limits.
    """

    name: str = "rtsp"

    def __init__(
        self,
        url: str,
        camera_id: str = "rtsp0",
        *,
        loop_file: bool = False,
    ) -> None:
        if not isinstance(url, str) or url.strip() == "":
            raise ValueError("empty RTSP/url target is not allowed")
        super().__init__(
            target=url,
            camera_id=camera_id,
            name="rtsp",
            loop_file=loop_file,
        )
