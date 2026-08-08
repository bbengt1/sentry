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
}


@dataclass(frozen=True)
class TtlConfig:
    """Per-product TTL overrides in milliseconds."""

    detections: float = 500.0
    depth: float = 750.0
    free_space: float = 750.0

    @classmethod
    def from_mapping(cls, mapping: dict[str, float] | None) -> TtlConfig:
        if mapping is None:
            return cls()
        return cls(
            detections=float(mapping.get("detections", DEFAULT_TTL_MS["detections"])),
            depth=float(mapping.get("depth", DEFAULT_TTL_MS["depth"])),
            free_space=float(mapping.get("free_space", DEFAULT_TTL_MS["free_space"])),
        )


def _age_ms(now: float, t_capture: float) -> float:
    return max(0.0, (now - t_capture) * 1000.0)


def _obstacle_to_wire(cue: Any) -> ObstacleCue:
    """Copy product obstacle (dataclass or model) into wire ObstacleCue."""
    if isinstance(cue, ObstacleCue):
        return cue
    if hasattr(cue, "model_dump"):
        return ObstacleCue.model_validate(cue.model_dump())
    return ObstacleCue(
        bbox_xyxy=tuple(cue.bbox_xyxy),  # type: ignore[arg-type]
        nearness_mean=float(cue.nearness_mean),
        nearness_max=float(cue.nearness_max),
        area_px=int(cue.area_px),
        band=getattr(cue, "band", "near") or "near",
    )


def _units_for_depth_kind(kind: DepthKind) -> str:
    # v1 free-space stays ordinal even for metric_estimated (no calibration).
    if kind == DepthKind.METRIC_CALIBRATED:
        return "ordinal"  # still ordinal bands without calibrated free-space path
    return "ordinal"


def assemble_perception_frame(
    store: Any,
    *,
    now: float | None = None,
    ttl: TtlConfig | dict[str, float] | None = None,
    bus_metrics: dict[str, Any] | None = None,
) -> PerceptionFrame | None:
    """Merge det + depth + free_space store products into one PerceptionFrame.

    Returns ``None`` when all three products are absent (callers map to 404
    or skip WS send). Completeness = presence and ``error is None``.
    Stale flags live in ``stats`` and are independent of completeness.
    """
    det = store.snapshot()
    depth = store.snapshot_depth()
    free = store.snapshot_free_space()

    if det is None and depth is None and free is None:
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
    # Error on det product still counts as present for identity; completeness
    # follows presence (historical snapshot behavior used det_present only).
    det_present = det is not None

    # Primary identity = product with max t_capture among present products.
    candidates: list[Any] = [
        p for p in (det, depth, free) if p is not None
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
        stats["det_stale"] = det_age > ttl_cfg.detections

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
        stats["depth_stale"] = depth_age > ttl_cfg.depth

    if free is not None:
        stats["free_space_frame_id"] = free.frame_id
        stats["free_space_latency_ms"] = free.latency_ms
        stats["free_space_obstacle_count"] = free.obstacle_count
        free_age = _age_ms(wall, free.t_capture)
        stats["free_space_age_ms"] = free_age
        stats["free_space_stale"] = free_age > ttl_cfg.free_space

    products_stale = bool(
        stats.get("det_stale")
        or stats.get("depth_stale")
        or stats.get("free_space_stale")
    )
    stats["products_stale"] = products_stale

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
        if getattr(metrics, "det_frames_dropped", None) is not None:
            stats["det_frames_dropped"] = int(metrics.det_frames_dropped)
        if getattr(metrics, "depth_frames_dropped", None) is not None:
            stats["depth_frames_dropped"] = int(metrics.depth_frames_dropped)
        if getattr(metrics, "free_space_frames_dropped", None) is not None:
            stats["free_space_frames_dropped"] = int(metrics.free_space_frames_dropped)

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
        free_space_payload = FreeSpacePayload(
            method="near_field_bands",
            depth_kind=free.depth_kind,
            units=_units_for_depth_kind(free.depth_kind),  # type: ignore[arg-type]
            obstacle_count=int(free.obstacle_count),
            obstacles=wire_obstacles,
            bands=dict(free.bands) if free.bands else None,
            # width/height/roi not always on product — omit unless present
            width=None,
            height=None,
            roi_bottom_frac=None,
        )

    return PerceptionFrame(
        schema_version=1,
        frame_id=primary.frame_id,
        camera_id=primary.camera_id,
        t_capture=primary.t_capture,
        t_publish=wall if now is not None else time.time(),
        completeness=Completeness(
            detections=det_present,
            depth=depth_good,
            free_space=free_good,
        ),
        depth=depth_payload,
        detections=list(det.detections) if det is not None else None,
        free_space=free_space_payload,
        stats=stats if stats else None,
    )
