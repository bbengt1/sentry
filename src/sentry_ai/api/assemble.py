"""Single PerceptionFrame merge path for REST + future WS (SPACE-04 / API-03/04).

Pure snapshot merge — no free-space compute, no depth inference, no motor fields.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import (
    Completeness,
    DepthPayload,
    FreeSpacePayload,
    ObstacleCue,
    PerceptionFrame,
)

__all__ = [
    "DEFAULT_TTL_MS",
    "TtlConfig",
    "assemble_perception_frame",
]

# Product age thresholds (ms). Stale ≠ incomplete (SPACE-04).
DEFAULT_TTL_MS: dict[str, float] = {
    "detections": 500.0,
    "depth": 750.0,
    "free_space": 750.0,
    "open_vocab": 500.0,
}


@dataclass(frozen=True)
class TtlConfig:
    """Per-product TTL overrides in milliseconds."""

    detections: float = 500.0
    depth: float = 750.0
    free_space: float = 750.0
    open_vocab: float = 500.0

    @classmethod
    def from_mapping(cls, mapping: dict[str, float] | None) -> TtlConfig:
        if mapping is None:
            return cls()
        return cls(
            detections=float(mapping.get("detections", DEFAULT_TTL_MS["detections"])),
            depth=float(mapping.get("depth", DEFAULT_TTL_MS["depth"])),
            free_space=float(mapping.get("free_space", DEFAULT_TTL_MS["free_space"])),
            open_vocab=float(
                mapping.get("open_vocab", DEFAULT_TTL_MS["open_vocab"])
            ),
        )


def _age_ms(now: float, t_capture: float) -> float:
    return max(0.0, (now - t_capture) * 1000.0)


def _obstacle_to_wire(cue: Any) -> ObstacleCue:
    """Copy product obstacle (dict, dataclass, or model) into wire ObstacleCue.

    FreeSpaceLoop stores obstacles as plain dicts for store isolation
    (``_obstacles_for_store``); spatial ObstacleCue dataclasses may also
    appear. Both shapes must convert cleanly for ``/v1/snapshot``.
    """
    from collections.abc import Mapping

    if isinstance(cue, ObstacleCue):
        return cue
    # FreeSpaceLoop path: plain dicts (must run before attribute access).
    if isinstance(cue, Mapping):
        data = dict(cue)
        return ObstacleCue(
            bbox_xyxy=list(data.get("bbox_xyxy") or data.get("bbox") or ()),
            nearness_mean=float(data.get("nearness_mean", 0.0)),
            nearness_max=float(data.get("nearness_max", 0.0)),
            area_px=int(data.get("area_px", 0)),
            band=data.get("band") or "near",
            distance_m=data.get("distance_m"),
        )
    if hasattr(cue, "model_dump"):
        return ObstacleCue.model_validate(cue.model_dump())
    return ObstacleCue(
        bbox_xyxy=tuple(cue.bbox_xyxy),  # type: ignore[arg-type]
        nearness_mean=float(cue.nearness_mean),
        nearness_max=float(cue.nearness_max),
        area_px=int(cue.area_px),
        band=getattr(cue, "band", "near") or "near",
        distance_m=getattr(cue, "distance_m", None),
    )


def _units_for_depth_kind(kind: DepthKind) -> str:
    """Wire units: meters only for metric_calibrated; else ordinal."""
    if kind == DepthKind.METRIC_CALIBRATED:
        return "m"
    return "ordinal"  # relative AND metric_estimated


def assemble_perception_frame(
    store: Any,
    *,
    now: float | None = None,
    ttl: TtlConfig | dict[str, float] | None = None,
    bus_metrics: dict[str, Any] | None = None,
) -> PerceptionFrame | None:
    """Merge det + depth + free_space + open_vocab store products.

    Returns ``None`` when all products are absent (callers map to 404
    or skip WS send). Completeness = presence and ``error is None``.
    Detections completeness is true if fixed **or** open-vocab product present.
    Wire detections: fixed first, then OV (with source tags).
    Stale flags live in ``stats`` and are independent of completeness.
    """
    det = store.snapshot()
    depth = store.snapshot_depth()
    free = store.snapshot_free_space()
    ov = None
    if hasattr(store, "snapshot_open_vocab"):
        try:
            ov = store.snapshot_open_vocab()
        except Exception:  # noqa: BLE001 — best-effort
            ov = None

    if det is None and depth is None and free is None and ov is None:
        return None

    wall = time.time() if now is None else float(now)
    ttl_cfg = (
        ttl
        if isinstance(ttl, TtlConfig)
        else TtlConfig.from_mapping(ttl if isinstance(ttl, dict) else None)
    )

    depth_good = depth is not None and depth.error is None
    free_good = free is not None and free.error is None
    # Detections: present counts as complete even with empty list (DET-04).
    # OV product also counts (OVD-03).
    det_present = det is not None
    ov_present = ov is not None
    detections_complete = det_present or ov_present

    # Primary identity = product with max t_capture among present products.
    candidates: list[Any] = [
        p for p in (det, depth, free, ov) if p is not None
    ]
    primary = max(candidates, key=lambda p: p.t_capture)

    stats: dict[str, float | int | str] = {}

    if det is not None:
        stats["det_latency_ms"] = det.latency_ms
        stats["det_frame_id"] = det.frame_id
        if det.conf is not None:
            stats["det_conf"] = det.conf
        if det.model_name is not None:
            stats["det_model"] = det.model_name
        det_age = _age_ms(wall, det.t_capture)
        stats["det_age_ms"] = det_age
        # stats values must be float|int|str (schema); use 0/1 not bool.
        stats["det_stale"] = 1 if det_age > ttl_cfg.detections else 0

    if ov is not None:
        stats["ov_latency_ms"] = ov.latency_ms
        stats["ov_frame_id"] = ov.frame_id
        if ov.conf is not None:
            stats["ov_conf"] = ov.conf
        if ov.model_name is not None:
            stats["ov_model"] = ov.model_name
        if ov.prompt is not None:
            stats["ov_prompt"] = ov.prompt
        ov_age = _age_ms(wall, ov.t_capture)
        stats["ov_age_ms"] = ov_age
        stats["ov_stale"] = 1 if ov_age > ttl_cfg.open_vocab else 0
        stats["ov_count"] = len(ov.detections)

    if depth is not None:
        stats["depth_frame_id"] = depth.frame_id
        stats["depth_latency_ms"] = depth.latency_ms
        if depth.min_value is not None:
            stats["depth_min"] = depth.min_value
        if depth.max_value is not None:
            stats["depth_max"] = depth.max_value
        if depth.mean_value is not None:
            stats["depth_mean"] = depth.mean_value
        if depth.model_name is not None:
            stats["depth_model"] = depth.model_name
        depth_age = _age_ms(wall, depth.t_capture)
        stats["depth_age_ms"] = depth_age
        stats["depth_stale"] = 1 if depth_age > ttl_cfg.depth else 0

    if free is not None:
        stats["free_space_frame_id"] = free.frame_id
        stats["free_space_latency_ms"] = free.latency_ms
        stats["free_space_obstacle_count"] = free.obstacle_count
        free_age = _age_ms(wall, free.t_capture)
        stats["free_space_age_ms"] = free_age
        stats["free_space_stale"] = 1 if free_age > ttl_cfg.free_space else 0

    products_stale = bool(
        stats.get("det_stale")
        or stats.get("depth_stale")
        or stats.get("free_space_stale")
        or stats.get("ov_stale")
    )
    stats["products_stale"] = 1 if products_stale else 0

    # Stage FPS / drops from store metrics when available.
    metrics = None
    if hasattr(store, "metrics_snapshot"):
        try:
            metrics = store.metrics_snapshot()
        except Exception:  # noqa: BLE001 — best-effort
            metrics = None
    if metrics is not None:
        if getattr(metrics, "det_fps", None) is not None:
            stats["det_fps"] = float(metrics.det_fps)
        if getattr(metrics, "depth_fps", None) is not None:
            stats["depth_fps"] = float(metrics.depth_fps)
        if getattr(metrics, "free_space_fps", None) is not None:
            stats["free_space_fps"] = float(metrics.free_space_fps)
        if getattr(metrics, "ov_fps", None) is not None:
            stats["ov_fps"] = float(metrics.ov_fps)
        if getattr(metrics, "det_frames_dropped", None) is not None:
            stats["det_frames_dropped"] = int(metrics.det_frames_dropped)
        if getattr(metrics, "depth_frames_dropped", None) is not None:
            stats["depth_frames_dropped"] = int(metrics.depth_frames_dropped)
        if getattr(metrics, "free_space_frames_dropped", None) is not None:
            stats["free_space_frames_dropped"] = int(metrics.free_space_frames_dropped)
        if getattr(metrics, "ov_frames_dropped", None) is not None:
            stats["ov_frames_dropped"] = int(metrics.ov_frames_dropped)

    if bus_metrics is not None:
        if "capture_fps" in bus_metrics and bus_metrics["capture_fps"] is not None:
            stats["capture_fps"] = float(bus_metrics["capture_fps"])
        if (
            "frames_dropped" in bus_metrics
            and bus_metrics["frames_dropped"] is not None
        ):
            stats["frames_dropped"] = int(bus_metrics["frames_dropped"])

    depth_payload: DepthPayload | None = None
    if depth_good and depth is not None:
        # Metadata only — never attach depth_map (T-04-03 / T-05-04).
        depth_payload = DepthPayload(
            kind=depth.kind,
            unit=depth.unit,
            width=depth.width if depth.width else None,
            height=depth.height if depth.height else None,
        )

    free_space_payload: FreeSpacePayload | None = None
    if free_good and free is not None:
        wire_obstacles = [_obstacle_to_wire(c) for c in free.obstacles]
        stored_units = getattr(free, "units", None)
        units = stored_units or _units_for_depth_kind(free.depth_kind)
        free_space_payload = FreeSpacePayload(
            method="near_field_bands",
            depth_kind=free.depth_kind,
            units=units,  # type: ignore[arg-type]
            obstacle_count=int(free.obstacle_count),
            obstacles=wire_obstacles,
            bands=dict(free.bands) if free.bands else None,
            # width/height/roi not always on product — omit unless present
            width=None,
            height=None,
            roi_bottom_frac=None,
        )

    # Merge detections: fixed first, then OV (ensure source tags).
    merged_detections = None
    if det is not None or ov is not None:
        merged: list[Any] = []
        if det is not None:
            merged.extend(list(det.detections))
        if ov is not None:
            for d in ov.detections:
                # Ensure source tag on wire (worker already tags; re-assert).
                if getattr(d, "source", "fixed") != "open_vocab":
                    from sentry_ai.schemas.perception import Detection as DetSchema

                    d = DetSchema(
                        class_name=d.class_name,
                        confidence=d.confidence,
                        bbox_xyxy=d.bbox_xyxy,
                        source="open_vocab",
                    )
                merged.append(d)
        merged_detections = merged

    return PerceptionFrame(
        schema_version=1,
        frame_id=primary.frame_id,
        camera_id=primary.camera_id,
        t_capture=primary.t_capture,
        t_publish=wall if now is not None else time.time(),
        completeness=Completeness(
            detections=detections_complete,
            depth=depth_good,
            free_space=free_good,
        ),
        depth=depth_payload,
        detections=merged_detections,
        free_space=free_space_payload,
        stats=stats if stats else None,
    )
