"""DEPTH-01/04: depth mode → model id + kind/unit honesty mapping."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentry_ai.models.depth.mapping import (
    ALLOWED_DEPTH_TIERS,
    DEFAULT_MODEL_ID,
    MODE_TO_MODEL,
    assert_depth_tier_allowed,
    kind_for_mode,
    tier_to_depth_model_id,
)
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import DepthPayload


def test_kind_for_mode_relative() -> None:
    kind, unit = kind_for_mode("relative")
    assert kind == DepthKind.RELATIVE
    assert unit is None


def test_kind_for_mode_metric_indoor() -> None:
    kind, unit = kind_for_mode("metric_indoor")
    assert kind == DepthKind.METRIC_ESTIMATED
    assert unit == "m"


def test_kind_for_mode_metric_outdoor() -> None:
    kind, unit = kind_for_mode("metric_outdoor")
    assert kind == DepthKind.METRIC_ESTIMATED
    assert unit == "m"


def test_kind_for_mode_unknown_raises() -> None:
    with pytest.raises(ValueError, match="unknown depth_mode"):
        kind_for_mode("absolute")
    with pytest.raises(ValueError, match="unknown depth_mode"):
        kind_for_mode("")


@pytest.mark.parametrize(
    "mode",
    ["relative", "metric_indoor", "metric_outdoor"],
)
def test_kind_for_mode_never_calibrated(mode: str) -> None:
    """Mode mapping never yields metric_calibrated (promotion is separate)."""
    kind, _unit = kind_for_mode(mode)
    assert kind != DepthKind.METRIC_CALIBRATED


def test_mode_to_model_only_small_hf_ids() -> None:
    assert set(MODE_TO_MODEL.keys()) == {
        "relative",
        "metric_indoor",
        "metric_outdoor",
    }
    assert MODE_TO_MODEL["relative"] == "depth-anything/Depth-Anything-V2-Small-hf"
    assert "Small" in MODE_TO_MODEL["metric_indoor"]
    assert "Indoor" in MODE_TO_MODEL["metric_indoor"]
    assert "Small" in MODE_TO_MODEL["metric_outdoor"]
    assert "Outdoor" in MODE_TO_MODEL["metric_outdoor"]
    for model_id in MODE_TO_MODEL.values():
        assert "Small" in model_id
        assert "Base" not in model_id
        assert "Large" not in model_id
        assert "Giant" not in model_id
        assert model_id.endswith("-hf")


def test_depth_tier_allowlist_small_only() -> None:
    assert ALLOWED_DEPTH_TIERS == frozenset({"small"})
    assert assert_depth_tier_allowed("small") == "small"
    assert assert_depth_tier_allowed("SMALL") == "small"
    assert tier_to_depth_model_id("small") == DEFAULT_MODEL_ID
    assert (
        tier_to_depth_model_id("small", depth_mode="metric_indoor")
        == MODE_TO_MODEL["metric_indoor"]
    )


def test_depth_tier_base_large_refused() -> None:
    for bad in ("base", "large", "Base", "Large", "giant", None, ""):
        with pytest.raises(ValueError, match="small|commercial|depth_tier"):
            assert_depth_tier_allowed(bad)  # type: ignore[arg-type]
        with pytest.raises(ValueError, match="small|commercial|depth_tier"):
            tier_to_depth_model_id(bad)  # type: ignore[arg-type]


def test_depth_payload_relative_unit_none_ok() -> None:
    payload = DepthPayload(
        kind=DepthKind.RELATIVE,
        unit=None,
        width=64,
        height=48,
    )
    assert payload.kind == DepthKind.RELATIVE
    assert payload.unit is None


def test_depth_payload_relative_with_meters_rejected() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.RELATIVE, unit="m", width=1, height=1)


def test_depth_payload_metric_estimated_with_m_ok() -> None:
    payload = DepthPayload(
        kind=DepthKind.METRIC_ESTIMATED,
        unit="m",
        width=32,
        height=24,
    )
    assert payload.unit == "m"
