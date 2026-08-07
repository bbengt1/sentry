"""Plugin Protocols for camera sources, model workers, and sinks.

Phase 1 contracts only — real cameras and inference land in later phases.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from sentry_ai.schemas.frame import Frame


@runtime_checkable
class CameraSource(Protocol):
    """Camera or synthetic frame source."""

    name: str

    def open(self) -> None: ...

    def read(self) -> Frame: ...

    def close(self) -> None: ...


@runtime_checkable
class ModelWorker(Protocol):
    """Perception worker that processes a Frame.

    Phase 1 noop workers return None; later phases return PerceptionFrame.
    """

    name: str

    def process(self, frame: Frame) -> object | None: ...


@runtime_checkable
class Sink(Protocol):
    """Downstream consumer of perception products."""

    name: str

    def emit(self, item: object) -> None: ...

    def close(self) -> None: ...
