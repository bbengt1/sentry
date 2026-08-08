"""DepthLoop: daemon thread reads FrameBus, writes PerceptionStore (DEPTH-01).

Structural twin of DetectionLoop — never opens cameras or owns capture I/O.
Keep-latest: skip when frame_id matches last processed; short Event.wait sleep.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.models.depth.mapping import kind_for_mode
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.state.perception_store import PerceptionStore

logger = logging.getLogger(__name__)

__all__ = ["DepthLoop"]


class DepthLoop:
    """Daemon depth thread: FrameBus → ModelWorker → PerceptionStore."""

    def __init__(
        self,
        bus: FrameBus,
        worker: Any,
        store: PerceptionStore,
    ) -> None:
        self._bus = bus
        self._worker = worker
        self._store = store
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None

    @property
    def bus(self) -> FrameBus:
        return self._bus

    @property
    def store(self) -> PerceptionStore:
        return self._store

    def start(self) -> None:
        """Spawn daemon depth thread. Idempotent if already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="depth",
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

    def _default_kind_unit(self) -> tuple[DepthKind, str | None]:
        mode = getattr(self._worker, "get_depth_mode", None)
        if callable(mode):
            try:
                return kind_for_mode(mode())
            except Exception:  # noqa: BLE001
                pass
        depth_mode = getattr(self._worker, "_depth_mode", None)
        if isinstance(depth_mode, str):
            try:
                return kind_for_mode(depth_mode)
            except Exception:  # noqa: BLE001
                pass
        return DepthKind.RELATIVE, None

    def _run(self) -> None:
        while not self._stop.is_set():
            frame = self._bus.get_latest()
            if frame is None or frame.frame_id == self._last_frame_id:
                self._stop.wait(0.005)
                continue

            if self._last_frame_id is not None:
                gap = frame.frame_id - self._last_frame_id - 1
                if gap > 0:
                    self._store.record_depth_drop(gap)

            t0 = time.perf_counter()
            model_name = str(getattr(self._worker, "name", "unknown"))
            try:
                result = self._worker.process(frame)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = frame.frame_id
                self._store.set_depth(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    depth_map=getattr(result, "depth_map", None),
                    kind=getattr(result, "kind", DepthKind.RELATIVE),
                    unit=getattr(result, "unit", None),
                    latency_ms=latency_ms,
                    width=getattr(result, "width", None),
                    height=getattr(result, "height", None),
                    model_name=model_name,
                    error=getattr(result, "error", None),
                )
            except Exception as exc:  # noqa: BLE001 — keep thread alive (T-04-04)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = frame.frame_id
                kind, unit = self._default_kind_unit()
                logger.exception(
                    "Depth worker failed frame_id=%s: %s",
                    frame.frame_id,
                    exc,
                )
                self._store.set_depth(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    depth_map=None,
                    kind=kind,
                    unit=unit,
                    latency_ms=latency_ms,
                    model_name=model_name,
                    error=str(exc),
                )
