# PerceptionFrame wire contract

Versioned robot-facing envelope produced by `assemble_perception_frame`.

## Identity and timestamps

| Field | Type | Notes |
|-------|------|-------|
| `frame_id` | string | Stable id for the merged frame |
| `camera_id` | string | Source identity (multi-cam extension key; v0.1 single active source) |
| `t_capture` | float | Epoch seconds |
| `t_publish` | float | Epoch seconds when assembled |
| `schema_version` | string | Contract version string |

## Completeness

```json
"completeness": {
  "depth": true,
  "detections": true,
  "free_space": false
}
```

Booleans mean “product present in the store,” **not** “safe to drive.”

## Detections

```json
"detections": [
  {
    "class_name": "person",
    "confidence": 0.87,
    "bbox_xyxy": [10.0, 20.0, 100.0, 200.0],
    "source": "fixed"
  }
]
```

| Field | Notes |
|-------|-------|
| `bbox_xyxy` | Image coordinates, pixel space |
| `source` | `"fixed"` (YOLO) or `"open_vocab"` (YOLOE) |

Open-vocab may also appear as a separate store product merged into the list
with `source: "open_vocab"`.

## Depth (metadata only)

```json
"depth": {
  "kind": "relative",
  "unit": null,
  "width": 640,
  "height": 480
}
```

| `kind` | Meaning |
|--------|---------|
| `relative` | Ordinal / inverse-depth style — **never** meters |
| `metric_estimated` | Approximate meters without full calibration (**not** calibrated) |
| `metric_calibrated` | Meters after **applied+valid** calibration (wizard or persist), not the default path |

**No `depth_map` array on the wire.** Relative + `unit: "m"` is rejected by
validators. Draft wizard numbers never claim `metric_calibrated`.

## Free-space / obstacles

```json
"free_space": {
  "method": "near_field_bands",
  "depth_kind": "relative",
  "units": "ordinal",
  "obstacle_count": 1,
  "obstacles": [
    {
      "bbox_xyxy": [1, 2, 3, 4],
      "nearness_mean": 0.8,
      "nearness_max": 0.95,
      "area_px": 1200,
      "band": "near"
    }
  ]
}
```

| Rule | Detail |
|------|--------|
| Units | `units="m"` **iff** `depth.kind=metric_calibrated` and absolute 1.5 m / 3.0 m cuts; else ordinal |
| Nearness | `nearness_*` stay 0..1 (not meters) |
| Optional `distance_m` | On obstacle cues **only when calibrated** (mean finite blob depth) |
| No masks | Full free/occupied masks not serialized |

See [calibration.md](calibration.md) for the operator wizard and persist path.

## Stats / staleness

Typical fields (see live responses for full set):

- Stage latency and FPS (`det_*`, `depth_*`, `free_space_*`)  
- Ages: `*_age_ms`  
- Stale flags: `*_stale`, `products_stale`  
- Drop counts where applicable  

**Consumers must honor stale/TTL.** Missing or stale free-space is **not** a
clear path. Free-space is **not a safety interlock**.

## Forbidden fields (perception-only)

Never emitted: `cmd`, `cmd_vel`, `twist`, `velocity`, `path_plan`,
`safe_to_drive`, `go_nogo`, and related control keys.

## Python models

Authoritative types: `src/sentry_ai/schemas/perception.py`  
(`extra=forbid` on wire models).
