"""Shared validation helpers for perception schemas."""

from __future__ import annotations

from sentry_ai.schemas.enums import DepthKind


def relative_depth_forbids_unit(kind: DepthKind, unit: str | None) -> None:
    """Raise ValueError when relative depth claims a physical unit (FOUND-03)."""
    if kind == DepthKind.RELATIVE and unit is not None:
        raise ValueError("relative depth must not set unit (meters forbidden)")
