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
from sentry_ai.spatial.free_space import (
    DEFAULT_MID_CUT,
    DEFAULT_NEAR_CUT,
    ObstacleCue,
    compute_free_space,
)
from sentry_ai.spatial.smoothing import OccupancySmoother
from sentry_ai.state.perception_store import PerceptionStore

logger = logging.getLogger(__name__)

__all__ = ["FreeSpaceLoop"]


def _obstacles_for_store(obstacles: list[Any]) -> list[Any]:
    """Convert ObstacleCue dataclasses to plain dicts for store isolation."""
    out: list[Any] = []
    for obs in obstacles:
        if isinstance(obs, ObstacleCue):
            item: dict[str, Any] = {
                "bbox_xyxy": list(obs.bbox_xyxy),
                "nearness_mean": obs.nearness_mean,
                "nearness_max": obs.nearness_max,
                "area_px": obs.area_px,
                "band": obs.band,
            }
            if obs.distance_m is not None:
                item["distance_m"] = obs.distance_m
            out.append(item)
        elif isinstance(obs, dict):
            out.append(dict(obs))
        else:
            out.append(obs)
    return out


def _validate_cut(name: str, value: float) -> float:
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    return v


class FreeSpaceLoop:
    """Daemon free-space thread: PerceptionStore depth → FreeSpaceProduct."""

    def __init__(self, store: PerceptionStore) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._enabled = threading.Event()
        self._enabled.set()  # stages on by default
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None
        self._smoother = OccupancySmoother(alpha=0.35)
        self._near_cut = DEFAULT_NEAR_CUT
        self._mid_cut = DEFAULT_MID_CUT
        self._last_kind: DepthKind | None = None

    @property
    def store(self) -> PerceptionStore:
        return self._store

    def is_enabled(self) -> bool:
        """Return True when the loop will compute free-space."""
        return self._enabled.is_set()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or pause free-space compute without stopping the thread.

        On disable, clears the free-space product once so completeness/overlays
        drop honestly. Does not call stop()/start().
        """
        if enabled:
            self._enabled.set()
        else:
            self._enabled.clear()
            self._store.clear_free_space()

    def get_near_cut(self) -> float:
        with self._lock:
            return self._near_cut

    def get_mid_cut(self) -> float:
        with self._lock:
            return self._mid_cut

    def set_near_cut(self, near_cut: float) -> None:
        """Update near_cut; requires near_cut > current mid_cut."""
        near = _validate_cut("near_cut", near_cut)
        with self._lock:
            if near <= self._mid_cut:
                raise ValueError(
                    f"near_cut must be > mid_cut "
                    f"(got near_cut={near}, mid_cut={self._mid_cut})"
                )
            self._near_cut = near

    def set_mid_cut(self, mid_cut: float) -> None:
        """Update mid_cut; requires current near_cut > mid_cut."""
        mid = _validate_cut("mid_cut", mid_cut)
        with self._lock:
            if self._near_cut <= mid:
                raise ValueError(
                    f"near_cut must be > mid_cut "
                    f"(got near_cut={self._near_cut}, mid_cut={mid})"
                )
            self._mid_cut = mid

    def set_cuts(
        self,
        *,
        near_cut: float | None = None,
        mid_cut: float | None = None,
    ) -> None:
        """Update near and/or mid cutoffs atomically. Does not reset smoother."""
        with self._lock:
            if near_cut is None:
                near = self._near_cut
            else:
                near = _validate_cut("near_cut", near_cut)
            if mid_cut is None:
                mid = self._mid_cut
            else:
                mid = _validate_cut("mid_cut", mid_cut)
            if near <= mid:
                raise ValueError(
                    f"near_cut must be > mid_cut (got near_cut={near}, mid_cut={mid})"
                )
            self._near_cut = near
            self._mid_cut = mid

    def reset_smoother(self) -> None:
        """Drop OccupancySmoother EMA (apply\u2194clear / kind change).

        Safe anytime; does not require the cuts lock.
        """
        self._smoother.reset()

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
            if not self._enabled.is_set():
                self._stop.wait(0.01)
                continue
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

            if self._last_kind is not None and depth.kind != self._last_kind:
                self.reset_smoother()
            self._last_kind = depth.kind

            with self._lock:
                near_cut = self._near_cut
                mid_cut = self._mid_cut

            t0 = time.perf_counter()
            try:
                result = compute_free_space(
                    depth.depth_map,
                    kind=depth.kind,
                    smoother=self._smoother,
                    near_cut=near_cut,
                    mid_cut=mid_cut,
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
                        units=result.units or "ordinal",
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
                        units=result.units,
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
                    units="ordinal",
                )
