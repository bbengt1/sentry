"""Camera source adapters (synthetic, OpenCV USB/file, …)."""

from __future__ import annotations

from sentry_ai.sources.errors import SourceDisconnected, SourceError
from sentry_ai.sources.synthetic import SyntheticSource

__all__ = [
    "SourceDisconnected",
    "SourceError",
    "SyntheticSource",
]
