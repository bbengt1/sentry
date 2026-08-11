"""Shared validation helpers for perception schemas."""

from __future__ import annotations

from sentry_ai.schemas.enums import DepthKind


def assert_depth_kind_unit(kind: DepthKind, unit: str | None) -> None:
    """FOUND-03 / CAL-04 / CAL-05 honesty matrix for depth kind↔unit pairs.

    - relative: unit must be None (never meters)
    - metric_estimated: unit must be ``"m"``
    - metric_calibrated: unit must be ``"m"`` (CAL-04 pair)
    """
    if kind == DepthKind.RELATIVE:
        if unit is not None:
            raise ValueError("relative depth must not set unit (meters forbidden)")
        return
    if kind == DepthKind.METRIC_ESTIMATED:
        if unit != "m":
            raise ValueError("metric_estimated depth requires unit='m'")
        return
    if kind == DepthKind.METRIC_CALIBRATED:
        if unit != "m":
            raise ValueError("metric_calibrated depth requires unit='m' (CAL-04 pair)")
        return
    raise ValueError(f"unknown depth kind: {kind!r}")


def assert_free_space_units(depth_kind: DepthKind, units: str) -> None:
    """Enforce free-space units honesty (CAL-05).

    ``units="m"`` is allowed only when ``depth_kind`` is metric_calibrated.
    ``metric_calibrated`` + ``units="ordinal"`` remains allowed until Phase 16.
    """
    if units == "m" and depth_kind != DepthKind.METRIC_CALIBRATED:
        raise ValueError(
            "free-space units='m' only allowed when depth_kind=metric_calibrated"
        )
    if units not in ("ordinal", "m"):
        raise ValueError(f"unknown free-space units: {units!r}")


def promote_kind_unit(
    base_kind: DepthKind,
    base_unit: str | None,
    *,
    applied: bool,
    valid: bool,
) -> tuple[DepthKind, str | None]:
    """Return wire kind/unit. Draft/invalid never promote (CAL-04)."""
    if applied and valid:
        return DepthKind.METRIC_CALIBRATED, "m"
    return base_kind, base_unit


def relative_depth_forbids_unit(kind: DepthKind, unit: str | None) -> None:
    """Raise ValueError when relative depth claims a physical unit (FOUND-03).

    Implemented via :func:`assert_depth_kind_unit` so callers keep working.
    """
    assert_depth_kind_unit(kind, unit)
