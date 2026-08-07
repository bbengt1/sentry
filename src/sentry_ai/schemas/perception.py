"""PerceptionFrame contracts and nested depth/detection payloads.

Timestamps use epoch seconds (float), same convention as :mod:`sentry_ai.schemas.frame`.

Depth honesty (FOUND-03): relative depth must never claim meters.
There is intentionally no ``depth_m`` field on :class:`DepthPayload`.

Perception-only: no motor, velocity, or command fields (T-1-05).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.validators import relative_depth_forbids_unit


class Completeness(BaseModel):
    """Which optional perception products are present on a frame."""

    model_config = ConfigDict(extra="forbid")

    depth: bool = False
    detections: bool = False
    free_space: bool = False


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


class Detection(BaseModel):
    """Minimal detection placeholder; tightened in later detection phases."""

    model_config = ConfigDict(extra="forbid")

    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float] | list[float]


class FreeSpacePayload(BaseModel):
    """Minimal free-space placeholder reserved for Phase 5."""

    model_config = ConfigDict(extra="forbid")

    obstacle_count: int | None = None


class PerceptionFrame(BaseModel):
    """Perception product for a single camera frame (no robot control fields)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    frame_id: int = Field(ge=0)
    camera_id: str = Field(min_length=1)
    t_capture: float  # epoch seconds
    t_publish: float | None = None
    completeness: Completeness = Field(default_factory=Completeness)
    depth: DepthPayload | None = None
    detections: list[Detection] | None = None
    free_space: FreeSpacePayload | None = None
    # Loose until Phase 5 telemetry contracts harden.
    stats: dict[str, float | int | str] | None = None
