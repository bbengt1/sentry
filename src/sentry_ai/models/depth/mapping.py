"""Depth mode → HF model id and honest DepthKind/unit mapping.

Kind/unit come only from the configured mode string — never from array
range heuristics. Only Small HF ids are allowlisted (never Base/Large NC).
"""

from __future__ import annotations

from sentry_ai.schemas.enums import DepthKind

__all__ = [
    "DEFAULT_MODEL_ID",
    "MODE_TO_MODEL",
    "kind_for_mode",
]

# Allowlist: Apache-friendly Small HF models only (T-04-02 / T-04-03).
MODE_TO_MODEL: dict[str, str] = {
    "relative": "depth-anything/Depth-Anything-V2-Small-hf",
    "metric_indoor": "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf",
    "metric_outdoor": "depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf",
}

DEFAULT_MODEL_ID: str = MODE_TO_MODEL["relative"]


def kind_for_mode(mode: str) -> tuple[DepthKind, str | None]:
    """Map depth_mode config to (DepthKind, unit).

    - relative → RELATIVE, unit=None (never meters)
    - metric_indoor / metric_outdoor → METRIC_ESTIMATED, unit=\"m\"
    """
    if mode == "relative":
        return DepthKind.RELATIVE, None
    if mode in ("metric_indoor", "metric_outdoor"):
        return DepthKind.METRIC_ESTIMATED, "m"
    raise ValueError(f"unknown depth_mode: {mode!r}")
