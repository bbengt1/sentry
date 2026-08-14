"""DepthLoop: daemon thread reads FrameBus, writes PerceptionStore (DEPTH-01).

Structural twin of DetectionLoop — never opens cameras or owns capture I/O.
Keep-latest: skip when frame_id matches last processed; short Event.wait sleep.

Calibration (CAL-03): optional CalibrationState. On the success path after
worker.process, refuse_if_mismatch then promote_kind_unit then apply_map
before set_depth. Single apply site — error/dependency products do not
invent metric_calibrated meters.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.control.calibration_persist import refuse_if_mismatch
from sentry_ai.models.depth.mapping import kind_for_mode
from sentry_ai.schemas.calibration import CalibrationFingerprint
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
        calibration: Any | None = None,
    ) -> None:
        self._bus = bus
        self._worker = worker
        self._store = store
        self._calibration = calibration
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._enabled = threading.Event()
        self._enabled.set()  # stages on by default
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None
        self._dep_failed = False  # sticky: missing transformers/torch etc.

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

        On disable, clears the depth product once so completeness/overlays
        drop honestly. Does not call stop()/start().
        """
        if enabled:
            self._enabled.set()
        else:
            self._enabled.clear()
            self._store.clear_depth()

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

    @staticmethod
    def _is_dependency_error(message: str) -> bool:
        """True when error indicates missing depth extra (transformers/torch)."""
        lower = message.lower()
        return (
            "transformers" in lower
            or "install the depth extra" in lower
            or ("torch" in lower and "required" in lower)
            or "no module named" in lower
        )

    def _handle_dependency_failure(self, message: str, frame: Any) -> None:
        """Log once, record error product, pause stage to stop per-frame spam."""
        if not self._dep_failed:
            self._dep_failed = True
            logger.error(
                "Depth disabled: missing dependency (%s). "
                "Install with: uv sync --extra depth",
                message,
            )
        kind, unit = self._default_kind_unit()
        model_name = str(getattr(self._worker, "name", "unknown"))
        self._store.set_depth(
            frame_id=frame.frame_id,
            camera_id=frame.camera_id,
            t_capture=frame.meta.t_capture,
            depth_map=None,
            kind=kind,
            unit=unit,
            latency_ms=0.0,
            model_name=model_name,
            error=message,
        )
        # Pause without tearing down thread; UI can still show stage off-ish.
        self._enabled.clear()

    def _live_fingerprint(
        self,
        frame: Any,
        depth_map: Any,
    ) -> CalibrationFingerprint:
        """Build live fingerprint from frame meta + map HxW + worker."""
        camera_id = getattr(frame, "camera_id", None)
        if not camera_id:
            meta = getattr(frame, "meta", None)
            if meta is not None:
                camera_id = getattr(meta, "camera_id", None)
        if not camera_id and self._calibration is not None:
            params = self._calibration.get_applied_params()
            if params is not None:
                camera_id = params.fingerprint.camera_id
        width: int | None = None
        height: int | None = None
        shape = getattr(depth_map, "shape", None)
        if shape is not None and len(shape) >= 2:
            height = int(shape[0])
            width = int(shape[1])
        depth_mode = None
        getter = getattr(self._worker, "get_depth_mode", None)
        if callable(getter):
            try:
                depth_mode = str(getter())
            except Exception:  # noqa: BLE001 — fingerprint best-effort
                depth_mode = None
        model_id = getattr(self._worker, "model_id", None)
        if model_id is None:
            model_id = getattr(self._worker, "_model_id", None)
        if model_id is not None:
            model_id = str(model_id)
        return CalibrationFingerprint(
            camera_id=str(camera_id or "unknown"),
            width=width,
            height=height,
            depth_mode=depth_mode,
            model_id=model_id,
        )

    def _run(self) -> None:
        while not self._stop.is_set():
            if not self._enabled.is_set() or self._dep_failed:
                self._stop.wait(0.01)
                continue
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
                err = getattr(result, "error", None)
                # Missing depth extra → sticky pause (one log, no per-frame spam).
                if err and self._is_dependency_error(str(err)):
                    self._handle_dependency_failure(str(err), frame)
                    continue
                depth_map = getattr(result, "depth_map", None)
                kind = getattr(result, "kind", DepthKind.RELATIVE)
                unit = getattr(result, "unit", None)
                if self._calibration is not None:
                    if depth_map is not None:
                        live = self._live_fingerprint(frame, depth_map)
                        refuse_if_mismatch(self._calibration, live)
                    # Promote + apply together before set_depth (T-14-02).
                    kind, unit = self._calibration.promote_kind_unit(kind, unit)
                    depth_map = self._calibration.apply_map(depth_map)
                self._store.set_depth(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    depth_map=depth_map,
                    kind=kind,
                    unit=unit,
                    latency_ms=latency_ms,
                    width=getattr(result, "width", None),
                    height=getattr(result, "height", None),
                    model_name=model_name,
                    error=err,
                )
            except ImportError as exc:
                self._last_frame_id = frame.frame_id
                self._handle_dependency_failure(str(exc), frame)
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
