"""Keep-latest perception product store (detection + depth dual products).

Depth-1 mailbox mirroring FrameBus: set overwrites; snapshot returns an
isolated copy. Full float depth_map stays in-process only (not wire JSON).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Any, Literal

from sentry_ai.models.depth.preprocess import depth_stats
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection

__all__ = [
    "DepthProduct",
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
class DepthProduct:
    """Latest depth product for one processed frame (in-process map).

    ``depth_map`` is HxW float32 for colormap / Phase 5 consumers.
    Wire/API paths should use metadata + stats only (no bulk arrays).
    """

    frame_id: int
    camera_id: str
    t_capture: float
    kind: DepthKind
    unit: Literal["m"] | None
    width: int
    height: int
    latency_ms: float
    depth_map: Any  # np.ndarray HxW float32 — in-process only
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    model_name: str | None = None
    error: str | None = None


@dataclass
class StoreMetrics:
    """Plain metrics for detection + depth paths (no numpy)."""

    det_frames: int = 0
    det_frames_dropped: int = 0
    det_fps: float = 0.0
    last_latency_ms: float | None = None
    depth_frames: int = 0
    depth_frames_dropped: int = 0
    depth_fps: float = 0.0
    last_depth_latency_ms: float | None = None


class PerceptionStore:
    """Thread-safe depth-1 keep-latest store for detection and depth products.

    DetectionLoop / DepthLoop are the intended sole producers; API/UI only
    snapshot. Dual products share one lock; keep-latest independently.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: DetectionProduct | None = None
        self._latest_depth: DepthProduct | None = None
        self._metrics = StoreMetrics()
        self._fps_window_t0 = time.monotonic()
        self._fps_count = 0
        self._depth_fps_window_t0 = time.monotonic()
        self._depth_fps_count = 0

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
        """Return an isolated copy of the latest detection product, or None."""
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

    def set_depth(
        self,
        frame_id: int,
        camera_id: str,
        t_capture: float,
        depth_map: Any,
        kind: DepthKind,
        unit: Literal["m"] | None,
        latency_ms: float,
        width: int | None = None,
        height: int | None = None,
        model_name: str | None = None,
        error: str | None = None,
    ) -> None:
        """Store latest depth product (keep-latest). Computes stats when map present."""
        min_value: float | None = None
        max_value: float | None = None
        mean_value: float | None = None
        resolved_w = 0 if width is None else int(width)
        resolved_h = 0 if height is None else int(height)

        if depth_map is not None and error is None:
            try:
                arr = depth_map
                if hasattr(arr, "shape") and len(arr.shape) >= 2:
                    resolved_h = int(arr.shape[0]) if resolved_h == 0 else resolved_h
                    resolved_w = int(arr.shape[1]) if resolved_w == 0 else resolved_w
                stats = depth_stats(arr)
                min_value = stats["min"]
                max_value = stats["max"]
                mean_value = stats["mean"]
            except Exception:  # noqa: BLE001 — stats best-effort
                pass

        product = DepthProduct(
            frame_id=frame_id,
            camera_id=camera_id,
            t_capture=t_capture,
            kind=kind,
            unit=unit,
            width=resolved_w,
            height=resolved_h,
            latency_ms=latency_ms,
            depth_map=depth_map,
            min_value=min_value,
            max_value=max_value,
            mean_value=mean_value,
            model_name=model_name,
            error=error,
        )
        with self._lock:
            self._latest_depth = product
            self._metrics.depth_frames += 1
            self._metrics.last_depth_latency_ms = latency_ms
            self._depth_fps_count += 1
            now = time.monotonic()
            dt = now - self._depth_fps_window_t0
            if dt >= 1.0:
                self._metrics.depth_fps = self._depth_fps_count / dt
                self._depth_fps_count = 0
                self._depth_fps_window_t0 = now

    def record_depth_drop(self, n: int = 1) -> None:
        """Increment skipped intermediate depth-frame counter."""
        with self._lock:
            self._metrics.depth_frames_dropped += max(0, n)

    def snapshot_depth(self) -> DepthProduct | None:
        """Return an isolated copy of the latest depth product, or None.

        Metadata is always copied into a new DepthProduct. ``depth_map`` may
        share the array reference (immutable after set); do not mutate.
        """
        with self._lock:
            if self._latest_depth is None:
                return None
            p = self._latest_depth
            return DepthProduct(
                frame_id=p.frame_id,
                camera_id=p.camera_id,
                t_capture=p.t_capture,
                kind=p.kind,
                unit=p.unit,
                width=p.width,
                height=p.height,
                latency_ms=p.latency_ms,
                depth_map=p.depth_map,
                min_value=p.min_value,
                max_value=p.max_value,
                mean_value=p.mean_value,
                model_name=p.model_name,
                error=p.error,
            )

    def metrics_snapshot(self) -> StoreMetrics:
        """Return an isolated copy of store metrics (det + depth)."""
        with self._lock:
            return StoreMetrics(
                det_frames=self._metrics.det_frames,
                det_frames_dropped=self._metrics.det_frames_dropped,
                det_fps=self._metrics.det_fps,
                last_latency_ms=self._metrics.last_latency_ms,
                depth_frames=self._metrics.depth_frames,
                depth_frames_dropped=self._metrics.depth_frames_dropped,
                depth_fps=self._metrics.depth_fps,
                last_depth_latency_ms=self._metrics.last_depth_latency_ms,
            )
