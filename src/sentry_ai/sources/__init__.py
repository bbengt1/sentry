"""Camera source adapters (synthetic, OpenCV USB/file, …)."""

from __future__ import annotations

from sentry_ai.sources.errors import SourceDisconnected, SourceError
from sentry_ai.sources.list_cameras import (
    LocalCameraInfo,
    format_camera_list,
    list_local_cameras,
    probe_camera_index,
)
from sentry_ai.sources.opencv_source import (
    FileSource,
    OpenCVSource,
    RtspSource,
    UsbSource,
)
from sentry_ai.sources.synthetic import SyntheticSource

__all__ = [
    "FileSource",
    "LocalCameraInfo",
    "OpenCVSource",
    "RtspSource",
    "SourceDisconnected",
    "SourceError",
    "SyntheticSource",
    "UsbSource",
    "format_camera_list",
    "list_local_cameras",
    "probe_camera_index",
]
