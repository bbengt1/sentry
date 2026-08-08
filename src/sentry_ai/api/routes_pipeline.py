"""Pipeline control plane: stage flags + free-space cutoffs (UI-03/UI-04).

Handlers only read/update PipelineState and push flags into loops.
They never open cameras or run model inference.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()


class PipelineConfigUpdate(BaseModel):
    """Partial pipeline config update. Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    detection_enabled: bool | None = None
    depth_enabled: bool | None = None
    free_space_enabled: bool | None = None
    near_cut: float | None = Field(default=None, ge=0.0, le=1.0)
    mid_cut: float | None = Field(default=None, ge=0.0, le=1.0)


def _pipeline_state(request: Request) -> Any:
    return getattr(request.app.state, "pipeline_state", None)


def _require_pipeline_state(request: Request) -> Any:
    state = _pipeline_state(request)
    if state is None:
        raise HTTPException(
            status_code=503,
            detail="pipeline state not available",
        )
    return state


def _detection_loop(request: Request) -> Any:
    return getattr(request.app.state, "detection_loop", None)


def _depth_loop(request: Request) -> Any:
    return getattr(request.app.state, "depth_loop", None)


def _free_space_loop(request: Request) -> Any:
    return getattr(request.app.state, "free_space_loop", None)


@router.get("/api/pipeline/config")
async def get_pipeline_config(request: Request) -> dict[str, Any]:
    """Return full pipeline stage flags + free-space cutoffs."""
    state = _require_pipeline_state(request)
    return state.snapshot()


@router.patch("/api/pipeline/config")
async def patch_pipeline_config(
    body: PipelineConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    """Update stage flags / free-space cuts without process restart (UI-03/04).

    Side-effects push enable flags and cuts into injected loops when present.
    Never runs inference.
    """
    state = _require_pipeline_state(request)
    partial = body.model_dump(exclude_unset=True)
    if not partial:
        return state.snapshot()

    try:
        snap = state.update(**partial)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Push enable flags into loops (pause without teardown).
    if "detection_enabled" in partial:
        det_loop = _detection_loop(request)
        if det_loop is not None:
            det_loop.set_enabled(bool(partial["detection_enabled"]))
    if "depth_enabled" in partial:
        depth_loop = _depth_loop(request)
        if depth_loop is not None:
            depth_loop.set_enabled(bool(partial["depth_enabled"]))
    if "free_space_enabled" in partial:
        free_loop = _free_space_loop(request)
        if free_loop is not None:
            free_loop.set_enabled(bool(partial["free_space_enabled"]))

    # Push free-space cuts when present.
    if "near_cut" in partial or "mid_cut" in partial:
        free_loop = _free_space_loop(request)
        if free_loop is not None:
            cut_kwargs: dict[str, float] = {}
            if "near_cut" in partial:
                cut_kwargs["near_cut"] = float(partial["near_cut"])
            if "mid_cut" in partial:
                cut_kwargs["mid_cut"] = float(partial["mid_cut"])
            try:
                free_loop.set_cuts(**cut_kwargs)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc)) from exc

    return snap
