"""Pydantic configuration tree for Sentry AI runtime profiles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from sentry_ai.schemas.enums import BackendName, RuntimeProfile


class DeviceConfig(BaseModel):
    """Device / backend preference (advisory in Phase 1; not executed)."""

    model_config = ConfigDict(extra="forbid")

    preferred_backend: BackendName | str = BackendName.CPU
    device_id: str = "cpu"


class ModelsConfig(BaseModel):
    """Model policy and tier selection (MODEL-01: local-only default)."""

    model_config = ConfigDict(extra="forbid")

    allow_cloud: bool = False
    defaults_commercially_friendly: bool = True
    detector_tier: str | None = None
    depth_tier: str | None = None


class SourceConfig(BaseModel):
    """Camera / frame source selection."""

    model_config = ConfigDict(extra="forbid")

    type: str = "synthetic"
    device: int | None = None
    path: str | None = None
    url: str | None = None
    camera_id: str | None = None


class SentryConfig(BaseModel):
    """Merged runtime configuration for a selected profile."""

    model_config = ConfigDict(extra="forbid")

    profile: RuntimeProfile
    device: DeviceConfig = Field(default_factory=DeviceConfig)
    models: ModelsConfig = Field(default_factory=ModelsConfig)
    source: SourceConfig | None = Field(default_factory=SourceConfig)
