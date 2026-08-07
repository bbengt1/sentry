"""Keep-latest detection product store (single truth for UI/API).

Depth-1 mailbox mirroring FrameBus: set overwrites; snapshot returns an
isolated copy. No numpy on the store wire path.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass

from sentry_ai.schemas.perception import Detection

__all__ = [
    "DetectionProduct",
    "PerceptionStore",
    "StoreMetrics",
]


@dataclass
class DetectionProduct:
    """Latest detection product for one processed frame."""

    frame_id: int
    camera_id: str
    t_capture: float
    detections: list[Detection]
    latency_ms: float
    conf: float | None = None
    model_name: str | None = None
    error: str | None = None


@dataclass
class StoreMetrics:
    """Plain metrics for detection path status / API (no numpy)."""

    det_frames: int = 0
    det_frames_dropped: int = 0
    det_fps: float = 0.0
    last_latency_ms: float | None = None


class PerceptionStore:
    """Thread-safe depth-1 keep-latest store for detection products.

    DetectionLoop is the intended sole producer; API/UI only snapshot.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: DetectionProduct | None = None
        self._metrics = StoreMetrics()
        self._fps_window_t0 = time.monotonic()
        self._fps_count = 0

    def set_detections(
        self,
        frame_id: int,
        camera_id: str,
        t_capture: float,
        detections: list[Detection],
        latency_ms: float,
        conf: float | None = None,
        model_name: str | None = None,
        error: str | None = None,
    ) -> None:
        """Store a copy of detections as the latest product (keep-latest)."""
        product = DetectionProduct(
            frame_id=frame_id,
            camera_id=camera_id,
            t_capture=t_capture,
            detections=list(detections),
            latency_ms=latency_ms,
            conf=conf,
            model_name=model_name,
            error=error,
        )
        with self._lock:
            self._latest = product
            self._metrics.det_frames += 1
            self._metrics.last_latency_ms = latency_ms
            self._fps_count += 1
            now = time.monotonic()
            dt = now - self._fps_window_t0
            if dt >= 1.0:
                self._metrics.det_fps = self._fps_count / dt
                self._fps_count = 0
                self._fps_window_t0 = now

    def record_drop(self, n: int = 1) -> None:
        """Increment skipped intermediate-frame counter (optional loop use)."""
        with self._lock:
            self._metrics.det_frames_dropped += max(0, n)

    def snapshot(self) -> DetectionProduct | None:
        """Return an isolated copy of the latest product, or None."""
        with self._lock:
            if self._latest is None:
                return None
            p = self._latest
            return DetectionProduct(
                frame_id=p.frame_id,
                camera_id=p.camera_id,
                t_capture=p.t_capture,
                detections=list(p.detections),
                latency_ms=p.latency_ms,
                conf=p.conf,
                model_name=p.model_name,
                error=p.error,
            )

    def metrics_snapshot(self) -> StoreMetrics:
        """Return an isolated copy of store metrics."""
        with self._lock:
            return StoreMetrics(
                det_frames=self._metrics.det_frames,
                det_frames_dropped=self._metrics.det_frames_dropped,
                det_fps=self._metrics.det_fps,
                last_latency_ms=self._metrics.last_latency_ms,
            )
