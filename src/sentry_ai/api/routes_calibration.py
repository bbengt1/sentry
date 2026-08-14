"""Calibration wizard control plane (WIZ-01/02/04).

Handlers only snapshot PerceptionStore depth and mutate CalibrationState.
They never open cameras or run model inference.
"""

from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path
from typing import Any, Literal

import numpy as np
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, ValidationError

from sentry_ai.config.calibration_store import (
    calibration_path as resolve_calibration_file,
)
from sentry_ai.control.calibration_persist import clear_persisted, persist_applied
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
)
from sentry_ai.spatial.calibration import (
    fit_affine_lstsq,
    fit_scale_median,
    known_height_to_distance_m,
)

router = APIRouter()


class CalibrationSampleBody(BaseModel):
    """Wizard sample body. Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    point_uv: tuple[float, float] | None = None
    bbox_xyxy: tuple[float, float, float, float] | None = None
    known_meters: float | None = None
    known_height_m: float | None = None
    hfov_deg: float | None = None
    note: str | None = None


class CalibrationComputeBody(BaseModel):
    """Fit request. Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    fit: Literal["median", "affine"] = "median"
    method: str = "known_distance"


class CalibrationApplyBody(BaseModel):
    """Optional apply body. Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    persist: bool = False


class CalibrationSaveBody(BaseModel):
    """Save body (no fields). Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")


def _require_calibration_state(request: Request) -> Any:
    state = getattr(request.app.state, "calibration_state", None)
    if state is None:
        raise HTTPException(
            status_code=503,
            detail="calibration state not available",
        )
    return state


def _perception_store(request: Request) -> Any:
    return getattr(request.app.state, "perception_store", None)


def _reset_free_space_smoother(request: Request) -> None:
    """Belt-and-suspenders EMA drop on apply/clear. Cancel must not call."""
    loop = getattr(request.app.state, "free_space_loop", None)
    reset = getattr(loop, "reset_smoother", None)
    if callable(reset):
        reset()


def _depth_worker(request: Request) -> Any:
    return getattr(request.app.state, "depth_worker", None)


def _get_freeze_pin(request: Request) -> Any:
    return getattr(request.app.state, "calibration_freeze_pin", None)


def _drop_freeze_pin(request: Request) -> None:
    request.app.state.calibration_freeze_pin = None


def _parse_json_body(raw: bytes, model: type[Any]) -> Any:
    """Parse optional JSON body; empty → defaults; extra=forbid → 422."""
    if not raw or not raw.strip():
        return model()
    try:
        return model.model_validate_json(raw)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=exc.errors()) from exc


def _persist_path(request: Request, state: Any) -> Path | None:
    """Prefer app.state.calibration_path; else stem from applied camera_id."""
    raw = getattr(request.app.state, "calibration_path", None)
    if raw is not None:
        return Path(raw)
    getter = getattr(state, "get_applied_params", None)
    params = getter() if callable(getter) else None
    if params is None:
        return None
    camera_id = getattr(getattr(params, "fingerprint", None), "camera_id", None)
    if not camera_id:
        return None
    try:
        return resolve_calibration_file(str(camera_id))
    except ValueError:
        return None


def _copy_depth_product(product: Any) -> Any:
    """Shallow-copy product with an isolated depth_map array."""
    depth_map = getattr(product, "depth_map", None)
    copied_map = None if depth_map is None else np.array(depth_map, copy=True)
    if hasattr(product, "__dataclass_fields__"):
        return replace(product, depth_map=copied_map)
    return product


def _usable_depth_product(product: Any) -> bool:
    if product is None:
        return False
    if getattr(product, "error", None):
        return False
    return getattr(product, "depth_map", None) is not None


def _depth_product_for_sample(request: Request) -> Any:
    pin = _get_freeze_pin(request)
    if _usable_depth_product(pin):
        return pin
    store = _perception_store(request)
    if store is None or not hasattr(store, "snapshot_depth"):
        raise HTTPException(status_code=422, detail="no_depth_product")
    product = store.snapshot_depth()
    if not _usable_depth_product(product):
        raise HTTPException(status_code=422, detail="no_depth_product")
    return product


def _read_observed_raw(
    product: Any,
    point_uv: tuple[float, float] | None = None,
    bbox_xyxy: tuple[float, float, float, float] | None = None,
) -> float:
    depth_map = getattr(product, "depth_map", None)
    if depth_map is None:
        raise HTTPException(status_code=422, detail="no_depth_product")
    arr = np.asarray(depth_map)
    if arr.ndim < 2 or arr.shape[0] < 1 or arr.shape[1] < 1:
        raise HTTPException(status_code=422, detail="no_depth_product")
    h, w = int(arr.shape[0]), int(arr.shape[1])
    if point_uv is not None:
        u, v = float(point_uv[0]), float(point_uv[1])
        x = int(np.clip(round(u), 0, w - 1))
        y = int(np.clip(round(v), 0, h - 1))
        val = float(arr[y, x])
        if not np.isfinite(val) or val <= 0.0:
            raise HTTPException(status_code=422, detail="empty_roi")
        return val
    if bbox_xyxy is not None:
        x1, y1, x2, y2 = (float(v) for v in bbox_xyxy)
        xa = int(np.clip(min(x1, x2), 0, w - 1))
        xb = int(np.clip(max(x1, x2), 0, w - 1))
        ya = int(np.clip(min(y1, y2), 0, h - 1))
        yb = int(np.clip(max(y1, y2), 0, h - 1))
        roi = arr[ya : yb + 1, xa : xb + 1]
        finite = roi[np.isfinite(roi) & (roi > 0.0)]
        if finite.size == 0:
            raise HTTPException(status_code=422, detail="empty_roi")
        return float(np.median(finite))
    raise HTTPException(
        status_code=422,
        detail="point_uv or bbox_xyxy required",
    )


def _sample_summary(sample: Any) -> dict[str, Any]:
    if hasattr(sample, "model_dump"):
        data = sample.model_dump()
    elif isinstance(sample, dict):
        data = dict(sample)
    else:
        data = {
            "point_uv": getattr(sample, "point_uv", None),
            "bbox_xyxy": getattr(sample, "bbox_xyxy", None),
            "known_meters": getattr(sample, "known_meters", None),
            "observed_raw": getattr(sample, "observed_raw", None),
            "frame_id": getattr(sample, "frame_id", None),
            "note": getattr(sample, "note", None),
        }
    data.pop("depth_map", None)
    return data


def _snapshot_payload(request: Request, state: Any) -> dict[str, Any]:
    snap = state.snapshot()
    data = snap.model_dump()
    data["samples"] = [_sample_summary(s) for s in state.get_draft_samples()]
    data["frozen"] = _get_freeze_pin(request) is not None
    return data


def _resolve_known_meters(
    body: CalibrationSampleBody,
    product: Any,
) -> float:
    if body.known_meters is not None:
        if body.known_meters <= 0.0:
            raise HTTPException(
                status_code=422,
                detail="known_meters must be positive",
            )
        return float(body.known_meters)
    if body.known_height_m is not None and body.bbox_xyxy is not None:
        width = int(getattr(product, "width", 0) or 0)
        depth_map = getattr(product, "depth_map", None)
        if width <= 0 and depth_map is not None:
            arr = np.asarray(depth_map)
            if arr.ndim >= 2:
                width = int(arr.shape[1])
        hfov = 70.0 if body.hfov_deg is None else float(body.hfov_deg)
        try:
            return known_height_to_distance_m(
                known_height_m=float(body.known_height_m),
                bbox_xyxy=body.bbox_xyxy,
                image_width_px=width,
                hfov_deg=hfov,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    raise HTTPException(
        status_code=422,
        detail="known_meters or known_height_m+bbox_xyxy required",
    )


def _fingerprint_from_context(
    request: Request,
    product: Any | None,
) -> CalibrationFingerprint:
    camera_id = "unknown"
    width: int | None = None
    height: int | None = None
    if product is not None:
        cam = getattr(product, "camera_id", None)
        if cam:
            camera_id = str(cam)
        w = getattr(product, "width", None)
        h = getattr(product, "height", None)
        if w:
            width = int(w)
        if h:
            height = int(h)
        depth_map = getattr(product, "depth_map", None)
        if depth_map is not None:
            arr = np.asarray(depth_map)
            if arr.ndim >= 2:
                if not height:
                    height = int(arr.shape[0])
                if not width:
                    width = int(arr.shape[1])
    worker = _depth_worker(request)
    depth_mode = None
    model_id = None
    if worker is not None:
        getter = getattr(worker, "get_depth_mode", None)
        if callable(getter):
            try:
                depth_mode = str(getter())
            except Exception:  # noqa: BLE001 — fingerprint best-effort
                depth_mode = None
        model_id = getattr(worker, "model_id", None) or getattr(
            worker, "_model_id", None
        )
        if model_id is not None:
            model_id = str(model_id)
    return CalibrationFingerprint(
        camera_id=camera_id,
        width=width,
        height=height,
        depth_mode=depth_mode,
        model_id=model_id,
    )


def _pairs_from_samples(state: Any) -> tuple[list[float], list[float]]:
    observed: list[float] = []
    known: list[float] = []
    for sample in state.get_draft_samples():
        if isinstance(sample, dict):
            o = sample.get("observed_raw")
            k = sample.get("known_meters")
        else:
            o = getattr(sample, "observed_raw", None)
            k = getattr(sample, "known_meters", None)
        if o is None or k is None:
            continue
        observed.append(float(o))
        known.append(float(k))
    return observed, known


def _fit_detail(result: Any) -> dict[str, Any]:
    return {
        "ok": bool(result.ok),
        "reason": result.reason,
        "scale": result.scale,
        "offset": result.offset,
        "residual_rms": result.residual_rms,
        "sample_count": result.sample_count,
        "method": result.method,
    }


@router.get("/api/depth/calibration")
async def get_calibration(request: Request) -> dict[str, Any]:
    """Return wizard snapshot + sample summaries (no depth maps)."""
    state = _require_calibration_state(request)
    return _snapshot_payload(request, state)


@router.post("/api/depth/calibration/freeze")
async def freeze_calibration(request: Request) -> dict[str, Any]:
    """Pin current snapshot_depth in-memory for stable ROI sampling."""
    state = _require_calibration_state(request)
    store = _perception_store(request)
    if store is None or not hasattr(store, "snapshot_depth"):
        raise HTTPException(status_code=422, detail="no_depth_product")
    product = store.snapshot_depth()
    if not _usable_depth_product(product):
        raise HTTPException(status_code=422, detail="no_depth_product")
    request.app.state.calibration_freeze_pin = _copy_depth_product(product)
    return _snapshot_payload(request, state)


@router.post("/api/depth/calibration/sample")
async def sample_calibration(
    body: CalibrationSampleBody,
    request: Request,
) -> dict[str, Any]:
    """Fill observed_raw from freeze pin or snapshot_depth; append draft."""
    state = _require_calibration_state(request)
    if state.is_applied():
        raise HTTPException(
            status_code=409,
            detail="calibration_already_applied",
        )
    has_point = body.point_uv is not None
    has_bbox = body.bbox_xyxy is not None
    if has_point == has_bbox:
        raise HTTPException(
            status_code=422,
            detail="exactly one of point_uv or bbox_xyxy required",
        )
    product = _depth_product_for_sample(request)
    try:
        observed_raw = _read_observed_raw(
            product,
            point_uv=body.point_uv,
            bbox_xyxy=body.bbox_xyxy,
        )
        known_meters = _resolve_known_meters(body, product)
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    sample = CalibrationSample(
        point_uv=body.point_uv,
        bbox_xyxy=body.bbox_xyxy,
        known_meters=known_meters,
        observed_raw=observed_raw,
        frame_id=getattr(product, "frame_id", None),
        note=body.note,
    )
    state.add_draft_sample(sample)
    payload = _snapshot_payload(request, state)
    payload["sample"] = _sample_summary(sample)
    return payload


@router.delete("/api/depth/calibration/samples")
async def delete_calibration_samples(request: Request) -> dict[str, Any]:
    """Drop draft samples and stale draft params; freeze pin may remain."""
    state = _require_calibration_state(request)
    state.clear_draft()
    return _snapshot_payload(request, state)


@router.post("/api/depth/calibration/compute")
async def compute_calibration(
    request: Request,
    body: CalibrationComputeBody | None = None,
) -> dict[str, Any]:
    """Fit draft samples; only ok=True may set_draft_params."""
    state = _require_calibration_state(request)
    if body is None:
        body = CalibrationComputeBody()
    observed, known = _pairs_from_samples(state)
    try:
        if body.fit == "affine":
            result = fit_affine_lstsq(observed, known, method=body.method)
        else:
            result = fit_scale_median(observed, known, method=body.method)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not result.ok:
        raise HTTPException(status_code=422, detail=_fit_detail(result))
    pin = _get_freeze_pin(request)
    product = pin if _usable_depth_product(pin) else None
    if product is None:
        store = _perception_store(request)
        if store is not None and hasattr(store, "snapshot_depth"):
            product = store.snapshot_depth()
    params = CalibrationParams(
        scale=float(result.scale),
        offset=float(result.offset),
        method=str(result.method),
        sample_count=int(result.sample_count),
        residual_rms=result.residual_rms,
        fingerprint=_fingerprint_from_context(request, product),
        created_at=time.time(),
    )
    snap = state.set_draft_params(params)
    payload = _snapshot_payload(request, state)
    payload["fit"] = _fit_detail(result)
    payload["has_draft_params"] = snap.has_draft_params
    return payload


@router.post("/api/depth/calibration/apply")
async def apply_calibration(request: Request) -> dict[str, Any]:
    """Commit draft params to applied. Optional persist:true writes YAML."""
    state = _require_calibration_state(request)
    body = _parse_json_body(await request.body(), CalibrationApplyBody)
    try:
        state.apply()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if body.persist:
        path = _persist_path(request, state)
        if path is None:
            raise HTTPException(status_code=422, detail="no calibration_path")
        try:
            persist_applied(state, path)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        setter = getattr(state, "set_persist_status", None)
        if callable(setter):
            setter("applied")
    _drop_freeze_pin(request)
    _reset_free_space_smoother(request)
    return _snapshot_payload(request, state)


@router.post("/api/depth/calibration/save")
async def save_calibration(request: Request) -> dict[str, Any]:
    """Write applied params to YAML. 422 if not applied or no path."""
    state = _require_calibration_state(request)
    _parse_json_body(await request.body(), CalibrationSaveBody)
    if not state.is_applied():
        raise HTTPException(status_code=422, detail="no applied calibration")
    path = _persist_path(request, state)
    if path is None:
        raise HTTPException(status_code=422, detail="no calibration_path")
    try:
        persist_applied(state, path)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    setter = getattr(state, "set_persist_status", None)
    if callable(setter):
        setter("applied")
    return _snapshot_payload(request, state)


@router.post("/api/depth/calibration/cancel")
async def cancel_calibration(request: Request) -> dict[str, Any]:
    """Discard draft only — never clears already-applied calibration."""
    state = _require_calibration_state(request)
    state.clear_draft()
    _drop_freeze_pin(request)
    return _snapshot_payload(request, state)


@router.post("/api/depth/calibration/clear")
async def clear_calibration(request: Request) -> dict[str, Any]:
    """Wipe applied + draft and delete persisted YAML when path known."""
    state = _require_calibration_state(request)
    path = _persist_path(request, state)
    if path is not None:
        clear_persisted(state, path)
    else:
        state.clear_applied()
        state.clear_draft()
    _drop_freeze_pin(request)
    _reset_free_space_smoother(request)
    return _snapshot_payload(request, state)
