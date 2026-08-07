"""Keep-latest FrameBus mailbox with drop/FPS metrics (CAM-05).

Depth-1 single-slot design: publish overwrites the previous frame.
``frames_dropped`` is an overwrite-count — every publish that replaces a
non-None slot increments the counter. No ``queue.Queue`` or growing lists.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from sentry_ai.capture.image_frame import ImageFrame


@dataclass
class BusMetrics:
    """Plain metrics for capture status / API (no numpy).

    ``frames_dropped`` counts overwrites: each publish while the slot is
    already occupied increments the counter (keep-latest drop semantics).
    """

    frames_published: int = 0
    frames_dropped: int = 0  # overwrite-count (publish while slot occupied)
    last_publish_t: float | None = None
    capture_fps: float = 0.0


class FrameBus:
    """Thread-safe depth-1 keep-latest mailbox for ImageFrame.

    Subscribers call ``get_latest`` (non-blocking, non-consuming). Capture
    publishes; consumers never backpressure the capture thread.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: ImageFrame | None = None
        self._metrics = BusMetrics()
        self._fps_window_t0 = time.monotonic()
        self._fps_count = 0

    def publish(self, frame: ImageFrame) -> None:
        """Store ``frame`` as the latest; count overwrite as a drop."""
        with self._lock:
            if self._latest is not None:
                self._metrics.frames_dropped += 1
            self._latest = frame
            self._metrics.frames_published += 1
            self._metrics.last_publish_t = time.time()
            self._fps_count += 1
            now = time.monotonic()
            dt = now - self._fps_window_t0
            if dt >= 1.0:
                self._metrics.capture_fps = self._fps_count / dt
                self._fps_count = 0
                self._fps_window_t0 = now

    def get_latest(self) -> ImageFrame | None:
        """Return current slot without consuming (keep-latest, not pop)."""
        with self._lock:
            return self._latest

    def metrics_snapshot(self) -> BusMetrics:
        """Return an isolated copy of metrics (mutating it is safe)."""
        with self._lock:
            return BusMetrics(
                frames_published=self._metrics.frames_published,
                frames_dropped=self._metrics.frames_dropped,
                last_publish_t=self._metrics.last_publish_t,
                capture_fps=self._metrics.capture_fps,
            )
