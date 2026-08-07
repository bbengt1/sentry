"""Plugin Protocols for camera sources, model workers, and sinks.

Phase 2 sources return ``ImageFrame`` (identity ``Frame`` + BGR image).
``Frame`` remains the identity/wire schema without numpy payloads.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sentry_ai.capture.image_frame import ImageFrame


@runtime_checkable
class CameraSource(Protocol):
    """Camera or synthetic frame source."""

    name: str

    def open(self) -> None: ...

    def read(self) -> ImageFrame: ...

    def close(self) -> None: ...


@runtime_checkable
class ModelWorker(Protocol):
    """Perception worker that processes an ImageFrame (or Frame identity).

    Phase 1 noop workers return None; later phases return PerceptionFrame.
    """

    name: str

    def process(self, frame: ImageFrame | object) -> object | None: ...


@runtime_checkable
class Sink(Protocol):
    """Downstream consumer of perception products."""

    name: str

    def emit(self, item: object) -> None: ...

    def close(self) -> None: ...
