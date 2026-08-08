"""Built-in plugins: real synthetic source, noop worker, null sinks.

SyntheticSource is implemented in ``sentry_ai.sources.synthetic`` and
re-exported here so the entry point path stays stable.
No model inference.
"""

from __future__ import annotations

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.sources.synthetic import SyntheticSource

__all__ = [
    "NoopWorker",
    "NullSink",
    "SyntheticSource",
    "VoiceNullSink",
]


class NoopWorker:
    """Model worker stub that performs no inference."""

    name: str = "noop"

    def process(self, frame: ImageFrame | object) -> object | None:
        # Phase 1/2: no models — return None so callers can branch.
        _ = frame
        return None


class NullSink:
    """Sink stub that discards emitted items."""

    name: str = "null"

    def emit(self, item: object) -> None:
        _ = item

    def close(self) -> None:
        return None


class VoiceNullSink:
    """EDGE-04 voice extension point — no ASR/TTS; discards all emits.

    Twin of :class:`NullSink` for future voice I/O plugins. Registered as
    entry point ``voice-null``. Does not open audio devices or network I/O
    (T-07-21).
    """

    name: str = "voice-null"

    def emit(self, item: object) -> None:
        _ = item

    def close(self) -> None:
        return None
