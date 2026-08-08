"""FreeSpaceLoop: daemon Spatial Post owner (SPACE-01).

Structural twin of DepthLoop — polls PerceptionStore.snapshot_depth(), never
opens cameras, never reads the frame bus, never imports torch/HF.
Keep-latest: skip when frame_id matches last processed; short Event.wait sleep.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.free_space import ObstacleCue, compute_free_space
from sentry_ai.spatial.smoothing import OccupancySmoother
from sentry_ai.state.perception_store import PerceptionStore

logger = logging.getLogger(__name__)

__all__ = ["FreeSpaceLoop"]


def _obstacles_for_store(obstacles: list[Any]) -> list[Any]:
    """Convert ObstacleCue dataclasses to plain dicts for store isolation."""
    out: list[Any] = []
    for obs in obstacles:
        if isinstance(obs, ObstacleCue):
            out.append(
                {
                    "bbox_xyxy": list(obs.bbox_xyxy),
                    "nearness_mean": obs.nearness_mean,
                    "nearness_max": obs.nearness_max,
                    "area_px": obs.area_px,
                    "band": obs.band,
                }
            )
        elif isinstance(obs, dict):
            out.append(dict(obs))
        else:
            out.append(obs)
    return out


class FreeSpaceLoop:
    """Daemon free-space thread: PerceptionStore depth → FreeSpaceProduct."""

    def __init__(self, store: PerceptionStore) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None
        self._smoother = OccupancySmoother(alpha=0.35)

    @property
    def store(self) -> PerceptionStore:
        return self._store

    def start(self) -> None:
        """Spawn daemon free-space thread. Idempotent if already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="free-space",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Signal stop and join thread. Idempotent."""
        self._stop.set()
        thread = None
        with self._lock:
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
        with self._lock:
            self._thread = None

    def _run(self) -> None:
        while not self._stop.is_set():
            depth = self._store.snapshot_depth()
            if (
                depth is None
                or depth.error is not None
                or depth.depth_map is None
                or depth.frame_id == self._last_frame_id
            ):
                self._stop.wait(0.005)
                continue

            if self._last_frame_id is not None:
                gap = depth.frame_id - self._last_frame_id - 1
                if gap > 0:
                    self._store.record_free_space_drop(gap)

            t0 = time.perf_counter()
            try:
                result = compute_free_space(
                    depth.depth_map,
                    kind=depth.kind,
                    smoother=self._smoother,
                )
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = depth.frame_id
                if result.error is not None:
                    self._store.set_free_space(
                        frame_id=depth.frame_id,
                        camera_id=depth.camera_id,
                        t_capture=depth.t_capture,
                        latency_ms=latency_ms,
                        depth_kind=depth.kind,
                        obstacle_count=0,
                        obstacles=[],
                        bands={},
                        free_mask=None,
                        occupied_mask=None,
                        method="near_field_bands",
                        error=result.error,
                    )
                else:
                    self._store.set_free_space(
                        frame_id=depth.frame_id,
                        camera_id=depth.camera_id,
                        t_capture=depth.t_capture,
                        latency_ms=latency_ms,
                        depth_kind=result.depth_kind,
                        obstacle_count=len(result.obstacles),
                        obstacles=_obstacles_for_store(result.obstacles),
                        bands=dict(result.bands),
                        free_mask=result.free_mask,
                        occupied_mask=result.occupied_mask,
                        method=result.method,
                        error=None,
                    )
            except Exception as exc:  # noqa: BLE001 — keep thread alive (T-05-03)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = depth.frame_id
                kind = getattr(depth, "kind", DepthKind.RELATIVE)
                logger.exception(
                    "Free-space failed frame_id=%s: %s",
                    depth.frame_id,
                    exc,
                )
                self._store.set_free_space(
                    frame_id=depth.frame_id,
                    camera_id=depth.camera_id,
                    t_capture=depth.t_capture,
                    latency_ms=latency_ms,
                    depth_kind=kind,
                    obstacle_count=0,
                    obstacles=[],
                    bands={},
                    free_mask=None,
                    occupied_mask=None,
                    method="near_field_bands",
                    error=str(exc),
                )
