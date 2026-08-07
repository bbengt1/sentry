"""Camera source adapters (synthetic, OpenCV USB/file, …)."""

from __future__ import annotations

from sentry_ai.sources.errors import SourceDisconnected, SourceError
from sentry_ai.sources.opencv_source import (
    FileSource,
    OpenCVSource,
    RtspSource,
    UsbSource,
)
from sentry_ai.sources.synthetic import SyntheticSource

__all__ = [
    "FileSource",
    "OpenCVSource",
    "RtspSource",
    "SourceDisconnected",
    "SourceError",
    "SyntheticSource",
    "UsbSource",
]
