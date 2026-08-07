"""Capture-source lifecycle status values."""

from __future__ import annotations

from enum import StrEnum


class SourceStatus(StrEnum):
    """Lifecycle state for a camera/source capture path.

    Used by the capture loop (02-02) and status APIs (02-03).
    """

    STARTING = "starting"
    STREAMING = "streaming"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"
