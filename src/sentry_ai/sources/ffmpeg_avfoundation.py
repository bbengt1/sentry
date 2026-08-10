"""macOS Continuity-friendly capture via FFmpeg AVFoundation.

OpenCV ``CAP_AVFOUNDATION`` indices are unreliable for Continuity Camera: the
system may open the laptop FaceTime camera while labels still say Continuity.
FFmpeg's avfoundation input selects the device more consistently by index from
its own device list (same names as Continuity / FaceTime).

Optional dependency: system ``ffmpeg`` on PATH (Homebrew: ``brew install ffmpeg``).
"""

from __future__ import annotations

import logging
import re
import shutil
import subprocess
import time
from typing import Any

import numpy as np

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.errors import SourceDisconnected, SourceError

logger = logging.getLogger(__name__)

__all__ = [
    "FfmpegAvFoundationSource",
    "ffmpeg_available",
    "list_ffmpeg_av_video_devices",
    "match_ffmpeg_device_index",
]

_VIDEO_DEVICE_RE = re.compile(
    r"\[(\d+)\]\s+(.+?)\s*$",
)
_DEFAULT_WIDTH = 1280
_DEFAULT_HEIGHT = 720
_DEFAULT_FPS = 30


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def list_ffmpeg_av_video_devices(
    *,
    run_subprocess: Any | None = None,
) -> list[tuple[int, str]]:
    """Return ``[(index, name), ...]`` from ``ffmpeg -f avfoundation -list_devices``.

    FFmpeg writes the list to stderr and exits non-zero; that is expected.
    """
    run = run_subprocess or subprocess.run
    try:
        proc = run(
            [
                "ffmpeg",
                "-f",
                "avfoundation",
                "-list_devices",
                "true",
                "-i",
                "",
            ],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        logger.debug("ffmpeg list_devices failed: %s", exc)
        return []

    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    devices: list[tuple[int, str]] = []
    in_video = False
    for line in text.splitlines():
        lower = line.lower()
        if "avfoundation video devices" in lower:
            in_video = True
            continue
        if "avfoundation audio devices" in lower:
            break
        if not in_video:
            continue
        # Example: [AVFoundation indev @ 0x…] [1] Brent's 16max pro Camera
        m = _VIDEO_DEVICE_RE.search(line)
        if not m:
            continue
        idx = int(m.group(1))
        name = m.group(2).strip()
        if "capture screen" in name.lower():
            continue
        devices.append((idx, name))
    return devices


def match_ffmpeg_device_index(
    preferred_name: str | None,
    *,
    prefer_continuity: bool = True,
    devices: list[tuple[int, str]] | None = None,
) -> tuple[int, str] | None:
    """Pick FFmpeg AVFoundation index for Continuity / name match."""
    devs = devices if devices is not None else list_ffmpeg_av_video_devices()
    if not devs:
        return None

    def _is_cont(n: str) -> bool:
        low = n.lower()
        if "desk view" in low or "deskview" in low:
            return False
        return (
            "continuity" in low
            or "iphone" in low
            or "ipad" in low
            or (
                "camera" in low
                and "facetime" not in low
                and "built-in" not in low
                and "macbook" not in low
            )
        )

    if preferred_name:
        key = preferred_name.lower().strip()
        for idx, name in devs:
            if key and key in name.lower():
                return idx, name

    if prefer_continuity:
        for idx, name in devs:
            if _is_cont(name):
                return idx, name

    return None


class FfmpegAvFoundationSource:
    """Read BGR frames from macOS AVFoundation via FFmpeg (Continuity-safe)."""

    name: str = "usb"

    def __init__(
        self,
        device_index: int,
        *,
        camera_id: str = "usb0",
        width: int = _DEFAULT_WIDTH,
        height: int = _DEFAULT_HEIGHT,
        fps: int = _DEFAULT_FPS,
        device_label: str | None = None,
    ) -> None:
        self.device_index = int(device_index)
        self.camera_id = camera_id
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.device_label = device_label
        self._proc: subprocess.Popen[bytes] | None = None
        self._next_frame_id = 0
        self._frame_bytes = self.width * self.height * 3

    def open(self) -> None:
        if not ffmpeg_available():
            raise SourceError(
                "ffmpeg not found on PATH (install: brew install ffmpeg)"
            )
        # Force scale+format so frame size is deterministic for pipe reads.
        vf = f"scale={self.width}:{self.height},format=bgr24"
        cmd = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-f",
            "avfoundation",
            "-framerate",
            str(self.fps),
            "-i",
            f"{self.device_index}:none",
            "-an",
            "-vf",
            vf,
            "-f",
            "rawvideo",
            "-pix_fmt",
            "bgr24",
            "pipe:1",
        ]
        logger.info(
            "Opening FFmpeg AVFoundation device %s (%s) %sx%s@%sfps",
            self.device_index,
            self.device_label or "unnamed",
            self.width,
            self.height,
            self.fps,
        )
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=self._frame_bytes * 2,
            )
        except OSError as exc:
            raise SourceError(f"failed to start ffmpeg: {exc}") from exc

        if self._proc.stdout is None:
            self.close()
            raise SourceError("ffmpeg stdout pipe missing")

        # Warm-up: Continuity often sends black frames first.
        deadline = time.time() + 8.0
        last_err = "no frames yet"
        while time.time() < deadline:
            try:
                frame = self.read()
                mean = float(np.mean(frame.image_bgr))
                if mean >= 1.0:
                    # Rewind frame id so first delivered frame is 0 after open.
                    self._next_frame_id = 0
                    logger.info(
                        "FFmpeg Continuity warm-up ok (mean=%.1f)",
                        mean,
                    )
                    return
                last_err = f"black frames (mean={mean:.1f})"
            except SourceDisconnected as exc:
                last_err = str(exc)
                time.sleep(0.05)
        # Keep process open — CaptureLoop may still get frames; log once.
        logger.warning(
            "FFmpeg device %s still %s after warm-up; leaving open. "
            "Unlock iPhone / free Continuity Camera if stream stays black.",
            self.device_index,
            last_err,
        )
        self._next_frame_id = 0

    def read(self) -> ImageFrame:
        if self._proc is None or self._proc.stdout is None:
            raise RuntimeError(
                f"{type(self).__name__} is not open; call open() first"
            )
        buf = self._proc.stdout.read(self._frame_bytes)
        if buf is None or len(buf) < self._frame_bytes:
            detail = f"short read ({0 if buf is None else len(buf)} bytes)"
            code = self._proc.poll()
            if code is not None:
                detail = f"{detail}; ffmpeg exit={code}"
            raise SourceDisconnected(
                f"no frame from ffmpeg avfoundation:{self.device_index} ({detail})"
            )
        bgr = np.frombuffer(buf, dtype=np.uint8).reshape(
            (self.height, self.width, 3)
        ).copy()
        now = time.time()
        meta = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=self.width,
            height=self.height,
        )
        self._next_frame_id += 1
        return ImageFrame(meta=meta, image_bgr=bgr)

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
