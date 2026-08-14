# API reference

Default base URL: **`http://127.0.0.1:8000`** (localhost only).

All JSON perception bodies are built by `assemble_perception_frame` from a
single `PerceptionStore`. Full schema: [perception-frame.md](perception-frame.md).

## Perception (robots)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/v1/snapshot` | Latest merged `PerceptionFrame` JSON |
| `WS` | `/v1/stream` | Keep-latest JSON frames at ~**10 Hz** (no per-client queue) |
| `GET` | `/api/snapshot` | Alias of `/v1/snapshot` (same assembler) |

**Status codes (`/v1/snapshot`):**

| Code | Meaning |
|------|---------|
| 200 | Frame assembled |
| 404 | No detection, depth, or free-space product yet |
| 503 | Perception store not available |

**WebSocket:** Accepts even when empty; sends when products appear. Breaks on
server shutdown. Never runs inference inside the stream task.

**Not on the wire:** bulk `depth_map`, `free_mask`, `occupied_mask` arrays.

### Client sketch

```python
import httpx

r = httpx.get("http://127.0.0.1:8000/v1/snapshot", timeout=5.0)
if r.status_code == 200:
    frame = r.json()
    assert "completeness" in frame
    # Always check stale / completeness before acting
    if frame.get("stats", {}).get("products_stale"):
        ...  # do not treat as live clearance

# Streaming
from websockets.sync.client import connect

with connect("ws://127.0.0.1:8000/v1/stream") as ws:
    msg = ws.recv()  # JSON PerceptionFrame
```

## Status and Live Preview

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Live Preview HTML (404 JSON if `--no-ui`) |
| `GET` | `/preview/mjpeg` | Multipart MJPEG stream with overlays |
| `GET` | `/api/status` | Capture + stage metrics (FPS, latency, conf, ages) |

MJPEG draw order: depth colormap → free-space → fixed + open-vocab boxes.

## Pipeline control

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/pipeline/config` | Stage enables + free-space near/mid cuts |
| `PATCH` | `/api/pipeline/config` | Toggle stages / update cuts without restart |

Example:

```json
{
  "detection_enabled": true,
  "depth_enabled": true,
  "free_space_enabled": true,
  "near_cut": 0.72,
  "mid_cut": 0.45
}
```

Validation: cuts in `[0, 1]`; require `near_cut > mid_cut` or **422**.  
Disable semantics: skip worker compute and clear that stage’s product once.

## Detection (fixed-class)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/detection/config` | conf, weights, device (when loaded) |
| `PATCH` | `/api/detection/config` | e.g. `{"conf": 0.4}` |

Requires `detect` extra for a live worker.

## Depth

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/depth/config` | `depth_mode`, model id |
| `PATCH` | `/api/depth/config` | `{"depth_mode":"relative"|"metric_indoor"|"metric_outdoor"}` |

Requires `depth` extra. Relative mode never claims meters.

## Calibration

Operator wizard + persist. Numbered path: [calibration.md](calibration.md).
Request bodies use `extra=forbid`. **503** if `CalibrationState` is missing.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/depth/calibration` | Wizard snapshot (no depth maps) |
| `POST` | `/api/depth/calibration/freeze` | Pin current depth for stable ROI samples |
| `POST` | `/api/depth/calibration/sample` | Append draft sample (known distance primary) |
| `POST` | `/api/depth/calibration/compute` | Fit draft (median/affine); UI **Fit** |
| `POST` | `/api/depth/calibration/apply` | Commit draft; optional `{"persist": true}` |
| `POST` | `/api/depth/calibration/save` | Write applied params to YAML |
| `POST` | `/api/depth/calibration/cancel` | Discard **draft only** (no file delete) |
| `POST` | `/api/depth/calibration/clear` | Clear applied + **delete** YAML |

`GET /api/status` additive fields: `calibration_active`, `calibration_scale`,
`calibration_method`, `calibration_persist` (`none` / `applied` / `ignored_mismatch` / `error`), optional `calibration_persist_reason`.
Persist status is **separate from** `depth.kind`.

## Open-vocabulary

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/open-vocab/config` | mode, classes, conf, every_n |
| `PATCH` | `/api/open-vocab/config` | Update prompts/mode (no inference) |
| `POST` | `/api/open-vocab/run` | Arm one-shot run on the OV loop thread |

Modes: `off` (default), `on_demand`, `continuous` (`every_n` default 3).  
Prompt limits: ≤32 classes, ≤64 chars each.

## Perception-only boundary

Responses **must not** include motor/control fields such as `cmd`, `cmd_vel`,
`twist`, `velocity`, `path_plan`, `safe_to_drive`, `go_nogo`. Schemas use
`extra=forbid`. See [safety-and-privacy.md](safety-and-privacy.md).

## Headless

```bash
uv run sentry serve --no-ui ...
```

- `GET /` → 404 JSON (no Live Preview HTML)  
- `/v1/*`, `/api/*`, and `/preview/mjpeg` remain available  

Headless does **not** add authentication.
