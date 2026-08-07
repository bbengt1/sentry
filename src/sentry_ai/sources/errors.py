"""Source open/read failure hierarchy for capture adapters."""

from __future__ import annotations


class SourceError(RuntimeError):
    """Base error for camera/source adapter failures (open or configuration)."""


class SourceDisconnected(SourceError):
    """Raised when a read fails due to disconnect, EOF, or empty frame."""
