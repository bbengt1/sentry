"""Keep-latest perception product store (detection + depth + free-space).

Depth-1 mailbox mirroring FrameBus: set overwrites; snapshot returns an
isolated copy. Full float depth_map and free/occupied masks stay in-process
only (not wire JSON).
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from sentry_ai.models.depth.preprocess import depth_stats
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection

__all__ = [
    "DepthProduct",
    "DetectionProduct",
    "FreeSpaceProduct",
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
class FreeSpaceProduct:
    """Latest free-space product for one processed depth frame.

    ``free_mask`` / ``occupied_mask`` are HxW uint8 in-process only for
    MJPEG overlay. Wire/API paths use obstacles + bands + counts only.
    """

    frame_id: int
    camera_id: str
    t_capture: float
    t_compute: float
    latency_ms: float
    depth_kind: DepthKind
    obstacle_count: int
    obstacles: list[Any] = field(default_factory=list)
    bands: dict[str, float] = field(default_factory=dict)
    free_mask: Any | None = None  # np.ndarray — in-process only
    occupied_mask: Any | None = None
    method: str = "near_field_bands"
    error: str | None = None


@dataclass
class StoreMetrics:
    """Plain metrics for detection + depth + free-space paths (no numpy)."""

    det_frames: int = 0
    det_frames_dropped: int = 0
    det_fps: float = 0.0
    last_latency_ms: float | None = None
    depth_frames: int = 0
    depth_frames_dropped: int = 0
    depth_fps: float = 0.0
    last_depth_latency_ms: float | None = None
    free_space_frames: int = 0
    free_space_frames_dropped: int = 0
    free_space_fps: float = 0.0
    last_free_space_latency_ms: float | None = None


class PerceptionStore:
    """Thread-safe depth-1 keep-latest store for det / depth / free-space.

    DetectionLoop / DepthLoop / FreeSpaceLoop are the intended sole producers;
    API/UI only snapshot. Triple products share one lock; keep-latest
    independently.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: DetectionProduct | None = None
        self._latest_depth: DepthProduct | None = None
        self._latest_free_space: FreeSpaceProduct | None = None
        self._metrics = StoreMetrics()
        self._fps_window_t0 = time.monotonic()
        self._fps_count = 0
        self._depth_fps_window_t0 = time.monotonic()
        self._depth_fps_count = 0
        self._free_space_fps_window_t0 = time.monotonic()
        self._free_space_fps_count = 0

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

    def set_free_space(
        self,
        frame_id: int,
        camera_id: str,
        t_capture: float,
        latency_ms: float,
        depth_kind: DepthKind,
        obstacle_count: int = 0,
        obstacles: list[Any] | None = None,
        bands: dict[str, float] | None = None,
        free_mask: Any | None = None,
        occupied_mask: Any | None = None,
        method: str = "near_field_bands",
        error: str | None = None,
        t_compute: float | None = None,
    ) -> None:
        """Store latest free-space product (keep-latest)."""
        product = FreeSpaceProduct(
            frame_id=frame_id,
            camera_id=camera_id,
            t_capture=t_capture,
            t_compute=time.time() if t_compute is None else float(t_compute),
            latency_ms=latency_ms,
            depth_kind=depth_kind,
            obstacle_count=int(obstacle_count),
            obstacles=list(obstacles) if obstacles is not None else [],
            bands=dict(bands) if bands is not None else {},
            free_mask=free_mask,
            occupied_mask=occupied_mask,
            method=method,
            error=error,
        )
        with self._lock:
            self._latest_free_space = product
            self._metrics.free_space_frames += 1
            self._metrics.last_free_space_latency_ms = latency_ms
            self._free_space_fps_count += 1
            now = time.monotonic()
            dt = now - self._free_space_fps_window_t0
            if dt >= 1.0:
                self._metrics.free_space_fps = self._free_space_fps_count / dt
                self._free_space_fps_count = 0
                self._free_space_fps_window_t0 = now

    def record_free_space_drop(self, n: int = 1) -> None:
        """Increment skipped intermediate free-space frame counter."""
        with self._lock:
            self._metrics.free_space_frames_dropped += max(0, n)

    def snapshot_free_space(self) -> FreeSpaceProduct | None:
        """Return an isolated copy of the latest free-space product, or None.

        Metadata, obstacles list, and bands dict are always copied.
        ``free_mask`` / ``occupied_mask`` may share array refs (immutable
        after set); do not mutate.
        """
        with self._lock:
            if self._latest_free_space is None:
                return None
            p = self._latest_free_space
            return FreeSpaceProduct(
                frame_id=p.frame_id,
                camera_id=p.camera_id,
                t_capture=p.t_capture,
                t_compute=p.t_compute,
                latency_ms=p.latency_ms,
                depth_kind=p.depth_kind,
                obstacle_count=p.obstacle_count,
                obstacles=list(p.obstacles),
                bands=dict(p.bands),
                free_mask=p.free_mask,
                occupied_mask=p.occupied_mask,
                method=p.method,
                error=p.error,
            )

    def metrics_snapshot(self) -> StoreMetrics:
        """Return an isolated copy of store metrics (det + depth + free-space)."""
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
                free_space_frames=self._metrics.free_space_frames,
                free_space_frames_dropped=self._metrics.free_space_frames_dropped,
                free_space_fps=self._metrics.free_space_fps,
                last_free_space_latency_ms=self._metrics.last_free_space_latency_ms,
            )
