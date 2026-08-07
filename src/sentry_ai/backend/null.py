"""NullBackend — no-op InferenceBackend for tests and Phase 1 smoke.

Intentionally imports neither torch nor onnxruntime.
"""

from __future__ import annotations

from typing import Any

from sentry_ai.schemas.enums import BackendName


class NullBackend:
    """Records infer() calls and returns None without running models."""

    name: BackendName = BackendName.CPU

    def __init__(self) -> None:
        self.infer_calls: int = 0
        self._loaded: bool = False

    def load(self) -> None:
        self._loaded = True

    def infer(self, tensor: Any) -> Any:
        _ = tensor
        self.infer_calls += 1
        return None

    def close(self) -> None:
        self._loaded = False
