"""OpenVocabLoop: daemon thread for open-vocab detection (OVD-02).

Structural twin of DetectionLoop — never opens cameras or owns capture I/O.
Writes **only** ``store.set_open_vocab`` (never ``set_detections``).

Modes (default ``off``):
  - off: thread alive, no process; clear OV product once on enter
  - on_demand: process one latest frame when armed, then idle
  - continuous: process every ``every_n`` new frame_ids (default 3)
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Literal

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.state.perception_store import PerceptionStore

logger = logging.getLogger(__name__)

Mode = Literal["off", "on_demand", "continuous"]

DEFAULT_EVERY_N = 3

__all__ = ["DEFAULT_EVERY_N", "OpenVocabLoop"]


class OpenVocabLoop:
    """Daemon open-vocab thread: FrameBus → YOLOE worker → OpenVocabProduct."""

    def __init__(
        self,
        bus: FrameBus,
        worker: Any,
        store: PerceptionStore,
        *,
        every_n: int = DEFAULT_EVERY_N,
        mode: Mode = "off",
    ) -> None:
        self._bus = bus
        self._worker = worker
        self._store = store
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None
        self._mode: Mode = mode
        self._every_n = max(1, int(every_n))
        self._armed = False
        self._continuous_counter = 0
        self._cleared_on_off = mode == "off"

    @property
    def bus(self) -> FrameBus:
        return self._bus

    @property
    def store(self) -> PerceptionStore:
        return self._store

    def get_mode(self) -> Mode:
        with self._lock:
            return self._mode

    def set_mode(self, mode: Mode) -> None:
        """Set scheduler mode. ``off`` clears OV product once."""
        if mode not in ("off", "on_demand", "continuous"):
            raise ValueError(
                f"mode must be off|on_demand|continuous, got {mode!r}"
            )
        with self._lock:
            prev = self._mode
            self._mode = mode
            if mode == "off":
                self._armed = False
                self._continuous_counter = 0
                # Clear outside? clear under lock is fine (store has own lock).
                if prev != "off" or not self._cleared_on_off:
                    self._cleared_on_off = True
                    clear = True
                else:
                    clear = False
            else:
                self._cleared_on_off = False
                clear = False
        if clear:
            self._store.clear_open_vocab()

    def get_every_n(self) -> int:
        with self._lock:
            return self._every_n

    def set_every_n(self, every_n: int) -> None:
        value = int(every_n)
        if value < 1:
            raise ValueError(f"every_n must be >= 1, got {every_n!r}")
        with self._lock:
            self._every_n = value

    def arm(self) -> None:
        """Arm one-shot processing for on_demand mode."""
        with self._lock:
            self._armed = True
            if self._mode == "off":
                self._mode = "on_demand"
                self._cleared_on_off = False

    def is_armed(self) -> bool:
        with self._lock:
            return self._armed

    def start(self) -> None:
        """Spawn daemon open-vocab thread. Idempotent if already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="open-vocab",
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

    def _should_process(self, frame_id: int) -> bool:
        """Decide whether to run worker for this new frame_id (caller holds no lock)."""
        with self._lock:
            mode = self._mode
            if mode == "off":
                return False
            if mode == "on_demand":
                if not self._armed:
                    return False
                self._armed = False
                return True
            # continuous
            every_n = self._every_n
            self._continuous_counter += 1
            if self._continuous_counter >= every_n:
                self._continuous_counter = 0
                return True
            return False

    def _run(self) -> None:
        while not self._stop.is_set():
            with self._lock:
                mode = self._mode
            if mode == "off":
                # Clear product once when sitting in off.
                with self._lock:
                    if not self._cleared_on_off:
                        self._cleared_on_off = True
                        do_clear = True
                    else:
                        do_clear = False
                if do_clear:
                    self._store.clear_open_vocab()
                self._stop.wait(0.01)
                continue

            frame = self._bus.get_latest()
            if frame is None or frame.frame_id == self._last_frame_id:
                self._stop.wait(0.005)
                continue

            # New frame id observed — decide whether to process.
            if not self._should_process(frame.frame_id):
                # Still advance last_frame_id for continuous counting so we
                # only count each frame once; for on_demand idle, skip without
                # consuming so arm still sees latest when armed later.
                with self._lock:
                    mode_now = self._mode
                if mode_now == "continuous":
                    self._last_frame_id = frame.frame_id
                self._stop.wait(0.005)
                continue

            if self._last_frame_id is not None:
                gap = frame.frame_id - self._last_frame_id - 1
                if gap > 0:
                    self._store.record_open_vocab_drop(gap)

            t0 = time.perf_counter()
            conf = getattr(self._worker, "get_conf", lambda: None)()
            model_name = str(getattr(self._worker, "name", "unknown"))
            prompt = None
            get_classes = getattr(self._worker, "get_prompt_classes", None)
            if callable(get_classes):
                try:
                    classes = get_classes()
                    if classes:
                        prompt = ", ".join(str(c) for c in classes)
                except Exception:  # noqa: BLE001 — audit best-effort
                    prompt = None
            try:
                dets = self._worker.process(frame)
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = frame.frame_id
                self._store.set_open_vocab(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    detections=list(dets or []),
                    latency_ms=latency_ms,
                    conf=float(conf) if conf is not None else None,
                    model_name=model_name,
                    prompt=prompt,
                    error=None,
                )
            except Exception as exc:  # noqa: BLE001 — keep thread alive
                latency_ms = (time.perf_counter() - t0) * 1000.0
                self._last_frame_id = frame.frame_id
                logger.exception(
                    "Open-vocab worker failed frame_id=%s: %s",
                    frame.frame_id,
                    exc,
                )
                self._store.set_open_vocab(
                    frame_id=frame.frame_id,
                    camera_id=frame.camera_id,
                    t_capture=frame.meta.t_capture,
                    detections=[],
                    latency_ms=latency_ms,
                    conf=float(conf) if conf is not None else None,
                    model_name=model_name,
                    prompt=prompt,
                    error=str(exc),
                )
