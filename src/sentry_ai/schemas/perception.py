"""Depth payload and (later) PerceptionFrame contracts.

Depth honesty (FOUND-03): relative depth must never claim meters.
There is intentionally no ``depth_m`` field on :class:`DepthPayload`.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.validators import relative_depth_forbids_unit


class DepthPayload(BaseModel):
    """Wire-facing depth metadata. Bulk depth arrays stay out of Phase 1."""

    model_config = ConfigDict(extra="forbid")

    kind: DepthKind
    unit: Literal["m"] | None = None
    width: int | None = None
    height: int | None = None
    # Intentionally NO field named depth_m

    @model_validator(mode="after")
    def relative_must_not_claim_meters(self) -> DepthPayload:
        relative_depth_forbids_unit(self.kind, self.unit)
        return self
