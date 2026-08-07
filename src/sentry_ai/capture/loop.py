"""CaptureLoop: daemon thread owns source lifecycle and FrameBus publish (CAM-06).

Reconnect policy (defaults):
  initial_backoff=0.25s, max_backoff=5.0s, factor=2.0
  On read failure: status RECONNECTING, close, sleep, re-open.
  On open failure before first success: status ERROR; after first success: RECONNECTING.
  Stale last frame remains on the bus while reconnecting.

FastAPI / UI never call source.read — only bus.get_latest and loop status.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.capture.status import SourceStatus, StatusSnapshot
from sentry_ai.sources.errors import SourceDisconnected

logger = logging.getLogger(__name__)

# Default reconnect policy (documented for operators / tests override).
DEFAULT_INITIAL_BACKOFF = 0.25
DEFAULT_MAX_BACKOFF = 5.0
DEFAULT_BACKOFF_FACTOR = 2.0


class CaptureLoop:
    """Daemon capture thread that publishes ImageFrames to a FrameBus."""

    def __init__(
        self,
        source: Any,
        bus: FrameBus,
        *,
        initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
        max_backoff: float = DEFAULT_MAX_BACKOFF,
        factor: float = DEFAULT_BACKOFF_FACTOR,
    ) -> None:
        self._source = source
        self._bus = bus
        self._initial_backoff = initial_backoff
        self._max_backoff = max_backoff
        self._factor = factor

        self._lock = threading.Lock()
        self._status = SourceStatus.STOPPED
        self._status_detail: str | None = None
        self._ever_opened = False
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    # --- thread-safe properties ------------------------------------------------

    @property
    def status(self) -> SourceStatus:
        with self._lock:
            return self._status

    @property
    def status_detail(self) -> str | None:
        with self._lock:
            return self._status_detail

    @property
    def source_name(self) -> str:
        return str(getattr(self._source, "name", "unknown"))

    @property
    def camera_id(self) -> str:
        return str(getattr(self._source, "camera_id", self.source_name))

    @property
    def bus(self) -> FrameBus:
        return self._bus

    def build_status(self, *, bind: str | None = None) -> StatusSnapshot:
        """Combine loop status + bus metrics + latest frame meta for API.

        ``bind`` is filled by ``sentry serve`` in 02-03; leave ``None`` for
        unit tests and non-HTTP use.
        """
        latest = self._bus.get_latest()
        metrics = self._bus.metrics_snapshot()
        frame_id = latest.frame_id if latest is not None else None
        t_capture = latest.meta.t_capture if latest is not None else None
        return StatusSnapshot(
            source=self.source_name,
            camera_id=self.camera_id,
            status=self.status,
            status_detail=self.status_detail,
            frame_id=frame_id,
            capture_fps=metrics.capture_fps,
            frames_dropped=metrics.frames_dropped,
            bind=bind,
            t_capture=t_capture,
        )

    # --- lifecycle -------------------------------------------------------------

    def start(self) -> None:
        """Spawn daemon capture thread. Does not block on first frame."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._status = SourceStatus.STARTING
            self._status_detail = None
            self._thread = threading.Thread(
                target=self._run,
                name=f"capture-{self.source_name}",
                daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        """Signal stop, join thread, close source. Idempotent."""
        self._stop.set()
        thread = None
        with self._lock:
            thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=5.0)
        self._safe_close()
        with self._lock:
            self._status = SourceStatus.STOPPED
            self._status_detail = None
            self._thread = None

    # --- internal --------------------------------------------------------------

    def _set_status(
        self,
        status: SourceStatus,
        detail: str | None = None,
    ) -> None:
        with self._lock:
            self._status = status
            self._status_detail = detail

    def _safe_close(self) -> None:
        try:
            self._source.close()
        except Exception:  # noqa: BLE001 — never raise out of close path
            logger.debug("source.close() raised during cleanup", exc_info=True)

    def _safe_open(self) -> None:
        self._source.open()
        with self._lock:
            self._ever_opened = True

    def _stamp_ingest(self, frame: ImageFrame) -> ImageFrame:
        if frame.meta.t_ingest is not None:
            return frame
        meta = frame.meta.model_copy(update={"t_ingest": time.time()})
        return ImageFrame(meta=meta, image_bgr=frame.image_bgr)

    def _interruptible_sleep(self, seconds: float) -> None:
        """Sleep up to ``seconds`` but wake early on stop."""
        end = time.monotonic() + max(seconds, 0.0)
        while not self._stop.is_set():
            remaining = end - time.monotonic()
            if remaining <= 0:
                return
            self._stop.wait(timeout=min(remaining, 0.05))

    def _run(self) -> None:
        backoff = self._initial_backoff
        source_open = False
        try:
            while not self._stop.is_set():
                # Ensure source is open
                if not source_open:
                    try:
                        self._safe_open()
                        source_open = True
                        backoff = self._initial_backoff
                    except Exception as exc:  # noqa: BLE001 — surface via status
                        detail = str(exc) or exc.__class__.__name__
                        with self._lock:
                            ever = self._ever_opened
                        if ever:
                            self._set_status(SourceStatus.RECONNECTING, detail)
                        else:
                            self._set_status(SourceStatus.ERROR, detail)
                        logger.warning("capture open failed: %s", detail)
                        self._interruptible_sleep(backoff)
                        backoff = min(backoff * self._factor, self._max_backoff)
                        continue

                # Read + publish
                try:
                    frame = self._source.read()
                    frame = self._stamp_ingest(frame)
                    self._bus.publish(frame)
                    self._set_status(SourceStatus.STREAMING, None)
                    backoff = self._initial_backoff
                except (SourceDisconnected, OSError, RuntimeError) as exc:
                    detail = str(exc) or exc.__class__.__name__
                    self._set_status(SourceStatus.RECONNECTING, detail)
                    logger.warning("capture read failed: %s", detail)
                    self._safe_close()
                    source_open = False
                    self._interruptible_sleep(backoff)
                    backoff = min(backoff * self._factor, self._max_backoff)
                except Exception as exc:  # noqa: BLE001 — keep thread alive
                    detail = str(exc) or exc.__class__.__name__
                    self._set_status(SourceStatus.ERROR, detail)
                    logger.exception("unexpected capture error: %s", detail)
                    self._safe_close()
                    source_open = False
                    self._interruptible_sleep(backoff)
                    backoff = min(backoff * self._factor, self._max_backoff)
        finally:
            self._safe_close()
            source_open = False
            if self._stop.is_set():
                self._set_status(SourceStatus.STOPPED, None)
