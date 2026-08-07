"""Camera source adapters (synthetic, OpenCV USB/file, …)."""

from __future__ import annotations

from sentry_ai.sources.errors import SourceDisconnected, SourceError

__all__ = [
    "SourceDisconnected",
    "SourceError",
]
