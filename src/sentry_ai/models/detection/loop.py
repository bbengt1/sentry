"""DetectionLoop: daemon thread reads FrameBus, writes PerceptionStore (DET-01).

Structural twin of CaptureLoop — never opens cameras or owns capture I/O.
Keep-latest: skip when frame_id matches last processed; short Event.wait sleep.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.state.perception_store import PerceptionStore

logger = logging.getLogger(__name__)

__all__ = ["DetectionLoop"]


class DetectionLoop:
    """Daemon detection thread: FrameBus → ModelWorker → PerceptionStore."""

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
        self._enabled = threading.Event()
        self._enabled.set()  # stages on by default
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None
        self._dep_failed = False  # sticky: missing ultralytics etc.

    @property
    def bus(self) -> FrameBus:
        return self._bus

    @property
    def store(self) -> PerceptionStore:
        return self._store

    def is_enabled(self) -> bool:
        """Return True when the loop will process frames."""
        return self._enabled.is_set()

    def set_enabled(self, enabled: bool) -> None:
        """Enable or pause processing without stopping the thread.

        On disable, clears the detection product once so completeness/overlays
        drop honestly. Does not call stop()/start().
        """
        if enabled:
            self._enabled.set()
        else:
            self._enabled.clear()
            self._store.clear_detections()

    def start(self) -> None:
        """Spawn daemon detection thread. Idempotent if already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="detection",
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

    @staticmethod
    def _is_dependency_error(message: str) -> bool:
        lower = message.lower()
        return (
            "ultralytics" in lower
            or "install the detect extra" in lower
            or ("no module named" in lower and "ultra" in lower)
        )

    def _handle_dependency_failure(self, message: str, frame: Any) -> None:
        """Log once, record error product, pause stage to stop per-frame spam."""
        if not self._dep_failed:
            self._dep_failed = True
            logger.error(
                "Detection disabled: missing dependency (%s). "
                "Install with: uv sync --extra detect",
                message,
            )
        conf = getattr(self._worker, "get_conf", lambda: None)()
        model_name = str(getattr(self._worker, "name", "unknown"))
        self._store.set_detections(
            frame_id=frame.frame_id,
            camera_id=frame.camera_id,
            t_capture=frame.meta.t_capture,
            detections=[],
            latency_ms=0.0,
            conf=float(conf) if conf is not None else None,
            model_name=model_name,
            error=message,
        )
        self._enabled.clear()

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._enabled.is_set() or self._dep_failed:
                self._stop.wait(0.01)
                continue
            frame = self._bus.get_latest()
            if frame is None or frame.frame_id == self._last_frame_id:
                self._stop.wait(0.005)
                continue

            # Count intermediate drops if frame_id jumped (optional metric).
            if self._last_frame_id is not None:
                gap = frame.frame_id - self._last_frame_id - 1
                if gap > 0:
                    self._store.record_drop(gap)

            t0 = time.perf_counter()
            conf = getattr(self._worker, "get_conf", lambda: None)()
            model_name = str(getattr(self._worker, "name", "unknown"))
            try:
                dets = self._worker.process(frame)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = frame.frame_id
                self._store.set_detections(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    detections=list(dets or []),
                    latency_ms=latency_ms,
                    conf=float(conf) if conf is not None else None,
                    model_name=model_name,
                    error=None,
                )
            except ImportError as exc:
                self._last_frame_id = frame.frame_id
                self._handle_dependency_failure(str(exc), frame)
            except Exception as exc:  # noqa: BLE001 — keep thread alive (T-03-04)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = frame.frame_id
                msg = str(exc)
                if self._is_dependency_error(msg):
                    self._handle_dependency_failure(msg, frame)
                    continue
                logger.exception(
                    "Detection worker failed frame_id=%s: %s",
                    frame.frame_id,
                    exc,
                )
                self._store.set_detections(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    detections=[],
                    latency_ms=latency_ms,
                    conf=float(conf) if conf is not None else None,
                    model_name=model_name,
                    error=msg,
                )
