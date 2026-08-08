"""Depth mode → HF model id and honest DepthKind/unit mapping.

Kind/unit come only from the configured mode string — never from array
range heuristics. Only Small HF ids are allowlisted (never Base/Large NC).
"""

from __future__ import annotations

from sentry_ai.schemas.enums import DepthKind

__all__ = [
    "ALLOWED_DEPTH_TIERS",
    "DEFAULT_MODEL_ID",
    "MODE_TO_MODEL",
    "assert_depth_tier_allowed",
    "kind_for_mode",
    "tier_to_depth_model_id",
]

# Allowlist: Apache-friendly Small HF models only (T-04-02 / T-04-03 / T-07-03).
MODE_TO_MODEL: dict[str, str] = {
    "relative": "depth-anything/Depth-Anything-V2-Small-hf",
    "metric_indoor": "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf",
    "metric_outdoor": "depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf",
}

DEFAULT_MODEL_ID: str = MODE_TO_MODEL["relative"]

# v1 profiles only support commercially-friendly Small depth models.
ALLOWED_DEPTH_TIERS: frozenset[str] = frozenset({"small"})


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


def assert_depth_tier_allowed(tier: str | None) -> str:
    """Validate depth_tier; only ``small`` is allowed (never Base/Large NC).

    Returns the normalized tier string. Raises ``ValueError`` for base/large
    or any unknown tier so commercial-unfriendly NC models cannot load.
    """
    if tier is None:
        raise ValueError(
            "depth_tier is required; only commercially-friendly "
            "'small' is allowed (never Base/Large NC)"
        )
    key = str(tier).strip().lower()
    if key not in ALLOWED_DEPTH_TIERS:
        raise ValueError(
            f"depth_tier {tier!r} refused: only commercially-friendly "
            "'small' is allowed (never Base/Large NC)"
        )
    return key


def tier_to_depth_model_id(
    tier: str | None,
    *,
    depth_mode: str = "relative",
) -> str:
    """Map depth_tier + depth_mode to an allowlisted Small HF model id.

    Only ``small`` tier is accepted. Base/Large NC tiers raise ValueError.
    ``depth_mode`` selects among relative / metric Small HF ids in MODE_TO_MODEL.
    """
    assert_depth_tier_allowed(tier)
    if depth_mode not in MODE_TO_MODEL:
        raise ValueError(f"unknown depth_mode: {depth_mode!r}")
    return MODE_TO_MODEL[depth_mode]
