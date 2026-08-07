"""Built-in plugin stubs: synthetic source, noop worker, null sink.

No OpenCV, numpy image payloads, or model inference.
"""

from __future__ import annotations

import time

from sentry_ai.schemas.frame import Frame


class SyntheticSource:
    """Yields schema-valid synthetic Frames without camera hardware."""

    name: str = "synthetic"

    def __init__(self, camera_id: str = "synthetic0") -> None:
        self.camera_id = camera_id
        self._next_frame_id = 0
        self._open = False

    def open(self) -> None:
        self._open = True
        self._next_frame_id = 0

    def read(self) -> Frame:
        if not self._open:
            raise RuntimeError("SyntheticSource is not open; call open() first")
        now = time.time()
        frame = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
        )
        self._next_frame_id += 1
        return frame

    def close(self) -> None:
        self._open = False


class NoopWorker:
    """Model worker stub that performs no inference."""

    name: str = "noop"

    def process(self, frame: Frame) -> object | None:
        # Phase 1: no models — return None so callers can branch.
        _ = frame
        return None


class NullSink:
    """Sink stub that discards emitted items."""

    name: str = "null"

    def emit(self, item: object) -> None:
        _ = item

    def close(self) -> None:
        return None
