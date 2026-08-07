"""Built-in plugins: real synthetic source, noop worker, null sink.

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
