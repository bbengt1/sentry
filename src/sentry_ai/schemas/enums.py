"""Shared enumerations for schema and config contracts."""

from __future__ import annotations

from enum import StrEnum


class DepthKind(StrEnum):
    """How depth values should be interpreted.

    - relative: ordinal / inverse-depth style; never labeled as meters
    - metric_estimated: approximate meters without full calibration
    - metric_calibrated: meters after metric calibration
    """

    RELATIVE = "relative"
    METRIC_ESTIMATED = "metric_estimated"
    METRIC_CALIBRATED = "metric_calibrated"


class RuntimeProfile(StrEnum):
    """Built-in multi-target runtime profiles (FOUND-06)."""

    DESKTOP_GPU = "desktop-gpu"
    JETSON = "jetson"
    CPU_FALLBACK = "cpu-fallback"


class BackendName(StrEnum):
    """Preferred inference backend names (advisory in Phase 1)."""

    TORCH = "torch"
    ONNXRUNTIME = "onnxruntime"
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"
    CPU = "cpu"
