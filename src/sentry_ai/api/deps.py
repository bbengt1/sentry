"""App-state holders for injected bus + capture loop (no process globals)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sentry_ai.bus.frame_bus import FrameBus
    from sentry_ai.capture.loop import CaptureLoop


@dataclass
class AppState:
    """Runtime dependencies attached to ``app.state`` by ``create_app``."""

    bus: FrameBus
    capture_loop: CaptureLoop
    bind: str
    perception_store: Any | None = None
    detection_worker: Any | None = None
    depth_worker: Any | None = None
    pipeline_state: Any | None = None
    detection_loop: Any | None = None
    depth_loop: Any | None = None
    free_space_loop: Any | None = None
    open_vocab_worker: Any | None = None
    open_vocab_loop: Any | None = None
    # Phase 8 BACK-02: factory-authored backend honesty (optional).
    backend_requested: str | None = None
    backend_live: str | None = None
    backend_reason: str | None = None
    # Phase 11 BACK-03: soft vs strict policy (pass-through; False must survive).
    fallback_to_torch: bool | None = None
    calibration_state: Any | None = None
