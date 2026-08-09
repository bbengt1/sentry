# Phase 5: Free-Space & Unified Stream - Pattern Map

**Mapped:** 2026-08-08  
**Files analyzed:** 16 (new + modified)  
**Analogs found:** 15 / 16

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/spatial/__init__.py` | config | — | `src/sentry_ai/models/depth/__init__.py` | role-match |
| `src/sentry_ai/spatial/free_space.py` | utility | transform | `src/sentry_ai/models/depth/preprocess.py` | role-match |
| `src/sentry_ai/spatial/smoothing.py` | utility | transform | `src/sentry_ai/models/depth/colormap.py` (pure CV helpers) | partial |
| `src/sentry_ai/spatial/overlay.py` | utility | transform | `src/sentry_ai/models/detection/overlay.py` | exact |
| `src/sentry_ai/spatial/loop.py` | service | event-driven | `src/sentry_ai/models/depth/loop.py` | exact |
| `src/sentry_ai/schemas/perception.py` | model | request-response | *(self — expand FreeSpacePayload)* | exact |
| `src/sentry_ai/state/perception_store.py` | store | CRUD | *(self — dual product → triple)* | exact |
| `src/sentry_ai/api/assemble.py` | utility | transform | `src/sentry_ai/api/routes_detection.py` (`api_snapshot`) | exact |
| `src/sentry_ai/api/routes_v1.py` | route | request-response | `src/sentry_ai/api/routes_detection.py` | exact (REST); partial (WS) |
| `src/sentry_ai/api/routes_detection.py` | route | request-response | *(self — thin alias to assembler)* | exact |
| `src/sentry_ai/api/routes_preview.py` | route | streaming | *(self — depth→boxes draw order)* | exact |
| `src/sentry_ai/api/app.py` | config | request-response | *(self — include_router)* | exact |
| `src/sentry_ai/api/deps.py` | config | — | *(self — AppState fields)* | exact |
| `src/sentry_ai/cli.py` | config | event-driven | *(self — DepthLoop lifecycle)* | exact |
| `src/sentry_ai/capture/status.py` | model | request-response | *(self — depth_* optional fields)* | exact |
| `src/sentry_ai/ui/static/index.html` | component | request-response | *(self — depth footer metrics)* | exact |

## Pattern Assignments

### `src/sentry_ai/spatial/loop.py` (service, event-driven) — FreeSpaceLoop

**Analog:** `src/sentry_ai/models/depth/loop.py` (primary) + `src/sentry_ai/models/detection/loop.py` (twin)

**Key delta vs DepthLoop:** FreeSpaceLoop does **not** read `FrameBus`. It polls `store.snapshot_depth()`, skips when `frame_id == last_id` or depth missing/error/no map, then `store.set_free_space(...)`. Structural lifecycle (daemon thread, start/stop, keep-latest, exception → product error) is identical.

**Imports + class skeleton** (DepthLoop lines 1–39):
```python
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.state.perception_store import PerceptionStore

logger = logging.getLogger(__name__)

class FreeSpaceLoop:
    def __init__(self, store: PerceptionStore) -> None:
        self._store = store
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None
```

**start/stop idempotent daemon** (DepthLoop lines 49–71):
```python
def start(self) -> None:
    with self._lock:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="free-space",  # was "depth"
            daemon=True,
        )
        self._thread.start()

def stop(self) -> None:
    self._stop.set()
    thread = None
    with self._lock:
        thread = self._thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=5.0)
    with self._lock:
        self._thread = None
```

**Keep-latest poll + drop metric + try/except product write** (DepthLoop lines 88–138 — adapt bus→store depth):
```python
def _run(self) -> None:
    while not self._stop.is_set():
        depth = self._store.snapshot_depth()
        if (
            depth is None
            or depth.error is not None
            or depth.depth_map is None
            or depth.frame_id == self._last_frame_id
        ):
            self._stop.wait(0.005)
            continue

        if self._last_frame_id is not None:
            gap = depth.frame_id - self._last_frame_id - 1
            if gap > 0:
                self._store.record_free_space_drop(gap)

        t0 = time.perf_counter()
        try:
            result = compute_free_space(  # pure Spatial Post
                depth.depth_map,
                kind=depth.kind,
                # ...
            )
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._last_frame_id = depth.frame_id
            self._store.set_free_space(
                frame_id=depth.frame_id,
                camera_id=depth.camera_id,
                t_capture=depth.t_capture,
                latency_ms=latency_ms,
                # ... result fields
                error=None,
            )
        except Exception as exc:  # noqa: BLE001 — keep thread alive
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._last_frame_id = depth.frame_id
            logger.exception(
                "Free-space failed frame_id=%s: %s",
                depth.frame_id,
                exc,
            )
            self._store.set_free_space(
                frame_id=depth.frame_id,
                camera_id=depth.camera_id,
                t_capture=depth.t_capture,
                latency_ms=latency_ms,
                error=str(exc),
                # empty obstacles / null masks
            )
```

**Test analog:** `tests/test_depth_loop.py` — FakeDepthWorker + `_wait_until` + start/stop finally. FreeSpaceLoop tests inject synthetic `store.set_depth(...)` (no FrameBus/worker).

---

### `src/sentry_ai/spatial/free_space.py` (utility, transform) — Spatial Post core

**Analog:** `src/sentry_ai/models/depth/preprocess.py` (pure NumPy/OpenCV, no ML imports)

**Module style** (preprocess lines 1–14):
```python
"""Pure free-space helpers for FreeSpaceLoop + golden tests.

No torch/transformers — OpenCV + numpy only.
"""

from __future__ import annotations

import cv2
import numpy as np

__all__ = [
    "compute_free_space",
    # FreeSpaceResult dataclass
]
```

**Result dataclass analog:** `DepthResult` in `src/sentry_ai/models/depth/worker.py` lines 31–40:
```python
@dataclass
class DepthResult:
    depth_map: np.ndarray | None
    kind: DepthKind
    unit: str | None
    width: int = 0
    height: int = 0
    error: str | None = None
```

Mirror as `FreeSpaceResult` with: `obstacles`, `bands`, `free_mask` / `occupied_mask`, `method`, `depth_kind`, `units`, `width`/`height`, `error`.

**Stats-style pure function** (preprocess lines 23–32):
```python
def depth_stats(depth: np.ndarray) -> dict[str, float]:
    finite = depth[np.isfinite(depth)]
    if finite.size == 0:
        return {"min": 0.0, "max": 0.0, "mean": 0.0}
    return {
        "min": float(finite.min()),
        "max": float(finite.max()),
        "mean": float(finite.mean()),
    }
```

**Algorithm body:** RESEARCH Pattern 1 (near-field percentile bands) — no existing codebase free-space math. Use OpenCV morphology/CC:
- `cv2.morphologyEx` open/close
- `cv2.connectedComponentsWithStats`
- Do **not** invent meters on relative maps

---

### `src/sentry_ai/spatial/smoothing.py` (utility, transform)

**Analog:** partial — pure helper style from `colormap.py` / `preprocess.py`; temporal EMA is new.

**Copy conventions:**
- Module-level defaults as named constants (like `DEPTH_BLEND_ALPHA = 0.45` in routes_preview)
- Pure functions: input occupancy → smoothed occupancy; no store/thread I/O
- RESEARCH defaults: open 3×3, close 5×5, EMA α=0.35, min area 0.15% ROI

**Stateful smoother (loop-owned):** keep last EMA float mask as instance field on FreeSpaceLoop or a small `OccupancySmoother` class — same ownership model as `_last_frame_id` on DepthLoop (loop-local state, not store).

---

### `src/sentry_ai/spatial/overlay.py` (utility, transform) — draw_free_space

**Analog:** `src/sentry_ai/models/detection/overlay.py` (primary) + `blend_depth` for alpha-blend

**Pure copy-in/copy-out** (overlay lines 1–51):
```python
"""Server-side free-space overlay drawing (SPACE-03).

Pure OpenCV helper — no models, no camera I/O. Used by MJPEG encode
and unit-tested with synthetic arrays.
"""

from __future__ import annotations

import cv2
import numpy as np

__all__ = ["draw_free_space"]

def draw_free_space(
    image_bgr: np.ndarray,
    free_mask: np.ndarray | None = None,
    occupied_mask: np.ndarray | None = None,
    obstacles: Sequence[...] | None = None,
    *,
    alpha: float = 0.35,
) -> np.ndarray:
    """Return a copy of ``image_bgr`` with free-space / obstacles drawn.

    Does not mutate ``image_bgr`` or masks.
    """
    out = image_bgr.copy()
    # semi-transparent free (green) / occupied (amber-red) via addWeighted
    # optional obstacle bboxes
    return out
```

**Alpha blend helper** (colormap lines 49–73 — reuse pattern for mask tint):
```python
def blend_depth(rgb_bgr, depth_map, alpha: float = 0.45) -> np.ndarray:
    base = np.asarray(rgb_bgr)
    # ...
    a = float(alpha)
    a = max(0.0, min(1.0, a))
    out = cv2.addWeighted(base, 1.0 - a, color, a, 0.0)
    return out
```

**Test analog:** `tests/test_depth_colormap.py` + `tests/test_detection_overlay.py` — assert copy, shape, dtype, no mutation.

---

### `src/sentry_ai/state/perception_store.py` (store, CRUD) — FreeSpaceProduct

**Analog:** self — extend dual-product pattern with third product identical to depth slot.

**Product dataclass** (DepthProduct lines 40–61):
```python
@dataclass
class DepthProduct:
    frame_id: int
    camera_id: str
    t_capture: float
    kind: DepthKind
    unit: Literal["m"] | None
    width: int
    height: int
    latency_ms: float
    depth_map: Any  # np.ndarray — in-process only
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    model_name: str | None = None
    error: str | None = None
```

**Mirror as FreeSpaceProduct:**
```python
@dataclass
class FreeSpaceProduct:
    frame_id: int
    camera_id: str
    t_capture: float
    t_compute: float
    latency_ms: float
    depth_kind: DepthKind
    obstacle_count: int
    obstacles: list  # ObstacleCue or plain dicts
    bands: dict[str, float]
    free_mask: Any | None   # in-process only
    occupied_mask: Any | None
    method: str = "near_field_bands"
    error: str | None = None
```

**set + metrics + snapshot** (set_depth / snapshot_depth / metrics pattern lines 151–257):
```python
# In __init__:
self._latest_free_space: FreeSpaceProduct | None = None
self._free_space_fps_window_t0 = time.monotonic()
self._free_space_fps_count = 0
# StoreMetrics gains: free_space_frames, free_space_frames_dropped,
# free_space_fps, last_free_space_latency_ms

def set_free_space(...) -> None:
    product = FreeSpaceProduct(...)
    with self._lock:
        self._latest_free_space = product
        self._metrics.free_space_frames += 1
        self._metrics.last_free_space_latency_ms = latency_ms
        # 1s FPS window (copy det/depth)

def record_free_space_drop(self, n: int = 1) -> None:
    with self._lock:
        self._metrics.free_space_frames_dropped += max(0, n)

def snapshot_free_space(self) -> FreeSpaceProduct | None:
    with self._lock:
        if self._latest_free_space is None:
            return None
        p = self._latest_free_space
        return FreeSpaceProduct(
            # copy fields; masks may share array ref (immutable after set)
            free_mask=p.free_mask,
            occupied_mask=p.occupied_mask,
            obstacles=list(p.obstacles),
            bands=dict(p.bands),
            ...
        )
```

**Wire honesty:** masks stay in-process like `depth_map` — never bulk-serialize in assembler.

**Test analog:** `tests/test_perception_store.py` depth section (`test_set_depth_*`, `test_snapshot_depth_isolates_product`).

---

### `src/sentry_ai/schemas/perception.py` (model) — FreeSpacePayload expansion

**Analog:** self — expand placeholder at lines 58–63; mirror Detection / DepthPayload style.

**Existing placeholder** (lines 58–63):
```python
class FreeSpacePayload(BaseModel):
    """Minimal free-space placeholder reserved for Phase 5."""

    model_config = ConfigDict(extra="forbid")

    obstacle_count: int | None = None
```

**Expand using Detection pattern** (lines 48–55) + DepthPayload honesty:
```python
class ObstacleCue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bbox_xyxy: tuple[float, float, float, float] | list[float]
    nearness_mean: float
    nearness_max: float
    area_px: int
    band: Literal["near", "mid", "far"] = "near"
    # Intentionally NO distance_m

class FreeSpacePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["near_field_bands"] = "near_field_bands"
    depth_kind: DepthKind
    units: Literal["ordinal", "m"] = "ordinal"
    obstacle_count: int = 0
    obstacles: list[ObstacleCue] = Field(default_factory=list)
    bands: dict[str, float] | None = None
    width: int | None = None
    height: int | None = None
    roi_bottom_frac: float | None = None
```

**Perception-only / extra=forbid** already on PerceptionFrame (lines 66–81). Keep `free_space: FreeSpacePayload | None = None`.

**Export:** add `ObstacleCue` to `schemas/__init__.py` if public.

**Test analog:** `tests/test_schemas_perception.py` — `extra=forbid`, motor denylist (`test_no_motor_velocity_cmd_fields`), completeness defaults.

---

### `src/sentry_ai/api/assemble.py` (utility, transform) — assemble_perception_frame

**Analog:** extract merge body from `src/sentry_ai/api/routes_detection.py` lines 59–134

**Current multi-product merge** (copy structure, add free_space + TTL):
```python
# routes_detection.py — extract this into assemble_perception_frame
store = _require_store(request)
det = store.snapshot()
depth = store.snapshot_depth()
# NEW: free = store.snapshot_free_space()

if det is None and depth is None:  # NEW: and free is None
    raise HTTPException(status_code=404, detail="no perception product yet")

depth_good = depth is not None and depth.error is None
det_present = det is not None
# NEW: free_good = free is not None and free.error is None

# Prefer identity from product with latest t_capture (extend to 3-way)
if det is not None and depth is not None:
    primary = det if det.t_capture >= depth.t_capture else depth
elif det is not None:
    primary = det
else:
    primary = depth

stats: dict[str, float | int | str] = {}
# det_* and depth_* stats as today...
# NEW: free_space_latency_ms, free_space_frame_id, free_space_fps, ages, stale flags

depth_payload = DepthPayload(...) if depth_good else None
# NEW: free_space_payload = FreeSpacePayload(...) if free_good else None
#      — obstacles/bands only; never free_mask / occupied_mask

frame = PerceptionFrame(
    schema_version=1,
    frame_id=primary.frame_id,
    camera_id=primary.camera_id,
    t_capture=primary.t_capture,
    t_publish=time.time(),
    completeness=Completeness(
        detections=det_present,
        depth=depth_good,
        free_space=free_good,  # was hardcoded False
    ),
    depth=depth_payload,
    detections=list(det.detections) if det is not None else None,
    free_space=free_space_payload,
    stats=stats if stats else None,
)
return frame
```

**Target pure function signature (RESEARCH):**
```python
def assemble_perception_frame(
    store: PerceptionStore,
    *,
    now: float | None = None,
    ttl: TtlConfig | None = None,
) -> PerceptionFrame | None:
    ...
```

- Return `None` when no products (callers map to 404 or skip WS send)
- Completeness = presence + no error (availability)
- Stale = age_ms > TTL (freshness) — separate stats bits
- Default TTL: det 500 / depth 750 / free_space 750 ms (RESEARCH)

**Do not fork merge logic** in REST vs WS — both call this one function.

---

### `src/sentry_ai/api/routes_v1.py` (route, request-response + streaming)

**Analog REST:** `routes_detection.py` `api_snapshot`  
**Analog app wiring:** `app.py` include_router  
**WS:** no in-repo WebSocket analog — use FastAPI `WebSocket` + `shutdown_flag` pattern from MJPEG

**Router + store access** (routes_detection lines 19–45):
```python
from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect

router = APIRouter()

def _store(request: Request) -> Any:
    return getattr(request.app.state, "perception_store", None)

def _require_store(request: Request) -> Any:
    store = _store(request)
    if store is None:
        raise HTTPException(status_code=503, detail="perception store not available")
    return store
```

**GET /v1/snapshot:**
```python
@router.get("/v1/snapshot")
async def v1_snapshot(request: Request) -> dict[str, Any]:
    store = _require_store(request)
    frame = assemble_perception_frame(store)
    if frame is None:
        raise HTTPException(status_code=404, detail="no perception product yet")
    return frame.model_dump()
```

**WS /v1/stream keep-latest** (RESEARCH Pattern 5 + preview shutdown):
```python
@router.websocket("/v1/stream")
async def v1_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    store = getattr(websocket.app.state, "perception_store", None)
    shutdown_flag = getattr(websocket.app.state, "shutdown_flag", None)
    try:
        while True:
            if shutdown_flag is not None and shutdown_flag.is_set():
                break
            if store is not None:
                frame = assemble_perception_frame(store)
                if frame is not None:
                    await websocket.send_json(frame.model_dump())
            await asyncio.sleep(0.1)  # ~10 Hz default
    except WebSocketDisconnect:
        return
```

**Handler purity rules (from routes_detection / routes_preview docstrings):**
- Never open cameras
- Never run Spatial Post / inference in handlers
- Only snapshot store + assemble

**Test analog:** `tests/test_api_detection.py` + `tests/test_api_depth.py` multi-product snapshot; new `tests/test_api_v1.py` with TestClient WS.

---

### `src/sentry_ai/api/routes_detection.py` (route) — /api/snapshot alias

**Pattern:** thin alias after assembler extraction:

```python
@router.get("/api/snapshot")
async def api_snapshot(request: Request) -> dict[str, Any]:
    """Back-compat alias of GET /v1/snapshot (same assembler)."""
    store = _require_store(request)
    frame = assemble_perception_frame(store)
    if frame is None:
        raise HTTPException(status_code=404, detail="no perception product yet")
    return frame.model_dump()
```

Keep detection config GET/PATCH handlers unchanged.

---

### `src/sentry_ai/api/routes_preview.py` (route, streaming) — free-space overlay

**Analog:** self — MJPEG draw order and status enrichment

**Draw order (lines 167–184 today → insert free-space):**
```python
# 1) bus RGB
image = item.image_bgr
if store is not None:
    # 2) depth blend
    depth_product = store.snapshot_depth()
    if (
        depth_product is not None
        and depth_product.error is None
        and depth_product.depth_map is not None
    ):
        image = blend_depth(image, depth_product.depth_map, alpha=DEPTH_BLEND_ALPHA)

    # 3) NEW free-space draw from store product only (UI-06)
    free_product = store.snapshot_free_space()
    if free_product is not None and free_product.error is None:
        image = draw_free_space(
            image,
            free_mask=free_product.free_mask,
            occupied_mask=free_product.occupied_mask,
            obstacles=free_product.obstacles,
        )

    # 4) detection boxes last
    product = store.snapshot()
    if product is not None:
        image = draw_detections(image, product.detections)
```

**Status free_space_* fields** (mirror depth block lines 97–112):
```python
free_product = store.snapshot_free_space()
data["free_space_fps"] = metrics.free_space_fps
if free_product is not None:
    data["free_space_latency_ms"] = free_product.latency_ms
    data["free_space_frame_id"] = free_product.frame_id
    data["obstacle_count"] = free_product.obstacle_count
    if free_product.error is not None:
        data["free_space_error"] = free_product.error
    # optional: free_space_stale / age_ms from assembler TTL helpers
```

**Never invent free-space from raw depth in MJPEG** — only store products (test pattern: `test_routes_preview_uses_blend_depth` source-order assert).

**Shutdown / disconnect:** keep `_interruptible_sleep` + `shutdown_flag` + `QuietStreamingResponse` unchanged.

---

### `src/sentry_ai/api/app.py` + `deps.py` (config)

**include_router** (app.py lines 69–71):
```python
app.include_router(preview_router)
app.include_router(detection_router)
app.include_router(depth_router)
# NEW:
app.include_router(v1_router)
```

**Optional FreeSpaceLoop is not on AppState** (loops owned by CLI like det/depth). Store remains single truth.

**shutdown_flag** already set on lifespan exit (lines 38–59) — WS stream must honor it same as MJPEG.

No new create_app kwargs required unless tests need free-space loop injection (prefer store-only seeding).

---

### `src/sentry_ai/cli.py` (config, event-driven) — FreeSpaceLoop lifecycle

**Analog:** depth/det optional extras block lines 339–426 — **but free-space has no ML extra**.

**Difference from depth:** FreeSpaceLoop starts whenever `store` exists (always, after store creation). No ImportError gate for Spatial Post.

**Start order today:** capture → det → depth  
**Phase 5 start order:** capture → det → depth → free_space  
**Stop reverse:** free_space → depth → det → capture

```python
# After store = PerceptionStore() and optional det/depth loops:
from sentry_ai.spatial.loop import FreeSpaceLoop

free_space_loop = FreeSpaceLoop(store)  # always-on CPU

# Start:
loop.start()
if det_loop is not None:
    det_loop.start()
if depth_loop is not None:
    depth_loop.start()
free_space_loop.start()

def _stop_workers() -> None:
    _signal_shutdown()
    free_space_loop.stop()
    if depth_loop is not None:
        depth_loop.stop()
    if det_loop is not None:
        det_loop.stop()
    loop.stop()
```

**Echo line:** `free-space: enabled (near-field bands)` — no extra install message.

Degrade path: if depth never arrives → completeness.free_space stays false (loop idles).

---

### `src/sentry_ai/capture/status.py` (model)

**Analog:** self — optional depth fields (lines 47–53)

```python
# Optional free-space telemetry (Phase 5); defaults keep Phase 2–4 callers valid.
free_space_latency_ms: float | None = None
free_space_fps: float | None = None
free_space_frame_id: int | None = None
obstacle_count: int | None = None
free_space_error: str | None = None
```

**Note:** Phase 4 already enriches status in `routes_preview.api_status` by mutating the dumped dict rather than only StatusSnapshot fields — free-space can follow that same routes_preview enrichment path; formal StatusSnapshot fields optional for OpenAPI/docs consistency.

---

### `src/sentry_ai/ui/static/index.html` (component)

**Analog:** self — depth footer metrics (lines 149–176, 243–264)

**Add footer cells:** Obstacles count, Free-space ms, optional STALE badge.  
**Poll:** existing `/api/status` every 500 ms — no second truth.  
**Language ban:** no “safe”, “go”, “clear to proceed” — only obstacles / free-space / incomplete / stale.

```javascript
// Mirror depth_kind honesty block for free-space:
elObstacles.textContent =
  (data && typeof data.obstacle_count === "number")
    ? String(data.obstacle_count)
    : "—";
// STALE: if data.free_space_stale or products_stale → badge / pill class
```

---

### Tests (map to existing patterns)

| New test file | Analog test | Patterns to copy |
|---------------|-------------|------------------|
| `tests/test_free_space.py` | `test_depth_preprocess.py` / `test_depth_colormap.py` | synthetic arrays, pure function, no ML imports |
| `tests/test_free_space_overlay.py` | `test_detection_overlay.py` / `test_depth_colormap.py` | copy/mutation, shape |
| `tests/test_spatial_loop.py` | `test_depth_loop.py` | Fake product via store, `_wait_until`, start/stop |
| `tests/test_assemble_frame.py` | `test_api_depth.py` multi-product merge | completeness, stats, no depth_map on wire |
| `tests/test_api_v1.py` | `test_api_detection.py` + TestClient | 404 empty, parity store↔JSON, WS send_json |
| Extend `test_perception_store.py` | depth product tests | set/snapshot/metrics free_space |
| Extend `test_schemas_perception.py` | motor denylist | ObstacleCue, units ordinal, extra=forbid |
| Extend `test_api_preview.py` | `test_routes_preview_uses_blend_depth` | source-order: blend_depth < draw_free_space < draw_detections |
| Extend `test_cli_serve.py` | depth lifecycle | free_space_loop start/stop order |

## Shared Patterns

### Keep-latest depth-1 mailbox
**Source:** `src/sentry_ai/state/perception_store.py`, `src/sentry_ai/bus/frame_bus.py`  
**Apply to:** FreeSpaceProduct slot, FreeSpaceLoop, WS publisher  
- set overwrites; snapshot returns isolated copy  
- no unbounded queues; slow consumers never block producers  

### Handler purity (no inference in API)
**Source:** `routes_detection.py` lines 1–6, `routes_preview.py` lines 1–9  
**Apply to:** `/v1/snapshot`, `/v1/stream`, MJPEG, `/api/status`  
```python
# Handlers only read PerceptionStore / bus / build_status.
# They never open cameras or run model inference / Spatial Post.
```

### Dual → triple product completeness
**Source:** `routes_detection.py` lines 77–129  
**Apply to:** `assemble_perception_frame`  
- `depth_good = product is not None and error is None`  
- free_space uses same rule  
- partial frames return 200 with completeness flags  

### In-process bulk arrays stay off the wire
**Source:** DepthProduct docstring + snapshot merge “never attach depth_map” (T-04-03)  
**Apply to:** free_mask / occupied_mask  
- Wire: obstacles + bands + counts + method + depth_kind + units  
- MJPEG: in-process masks only  

### Depth honesty / ordinal free-space
**Source:** `schemas/perception.py` FOUND-03, `relative_depth_forbids_unit`, UI depth label  
**Apply to:** FreeSpacePayload.units, ObstacleCue (no distance_m), UI copy  
- relative → `units="ordinal"`  
- never label free-space as meters without metric calibration path  

### Perception-only boundary (API-05)
**Source:** `test_schemas_perception.py` `test_no_motor_velocity_cmd_fields` + `extra="forbid"`  
**Apply to:** PerceptionFrame, FreeSpacePayload, ObstacleCue, WS dumps  
```python
FORBIDDEN_TOP_LEVEL = {
    "cmd", "velocity", "motor", "path_plan", "motor_command",
    "twist", "cmd_vel", "steering", "throttle", "safe_to_drive", "go_nogo",
}
```

### Daemon loop lifecycle
**Source:** DepthLoop / DetectionLoop + cli serve  
**Apply to:** FreeSpaceLoop  
- threading.Event stop, daemon=True, join(timeout=5.0)  
- BLE001 catch keep-alive with product.error  
- 5 ms wait on no work  

### Server-side overlay Option A
**Source:** MJPEG path in routes_preview  
**Apply to:** free-space draw  
- OpenCV before JPEG; browser is display-only  
- Draw order: depth blend → free-space → boxes  

### Serve shutdown
**Source:** `cli.py` `_signal_shutdown` + `app.state.shutdown_flag` + MJPEG interruptible sleep  
**Apply to:** WS `/v1/stream`  
- Honor shutdown_flag; no hang on Ctrl+C  

### Test injection without ML
**Source:** FakeDepthWorker, store.set_depth in API tests  
**Apply to:** free-space unit/API tests  
- Synthetic float depth maps → set_depth → FreeSpaceLoop or pure compute  
- Never require torch/transformers/ultralytics for free-space CI  

## No Analog Found

| File / concern | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| Temporal EMA occupancy state | utility | transform | No existing temporal filter; invent small pure smoother using RESEARCH defaults |
| FastAPI WebSocket endpoint | route | streaming | No WS route in codebase yet — use FastAPI docs + MJPEG shutdown_flag conventions |
| Near-field band algorithm body | utility | transform | New Spatial Post domain math; OpenCV CC/morphology APIs only |

## Metadata

**Analog search scope:**  
`src/sentry_ai/{api,state,schemas,models/depth,models/detection,capture,cli,ui}` + `tests/test_{depth_*,detection_*,api_*,perception_store,schemas_perception}`

**Files scanned:** ~35 source + ~15 tests  
**Pattern extraction date:** 2026-08-08  

**Primary twins for planner:**
1. FreeSpaceLoop ← DepthLoop  
2. FreeSpaceProduct / set/snapshot ← DepthProduct  
3. assemble_perception_frame ← routes_detection.api_snapshot merge  
4. draw_free_space ← draw_detections + blend_depth  
5. /v1 routes ← routes_detection + app.include_router + shutdown_flag  
6. CLI lifecycle ← depth_loop start/stop reverse order  

---

## PATTERN MAPPING COMPLETE

**Phase:** 5 - Free-Space & Unified Stream  
**Files classified:** 16  
**Analogs found:** 15 / 16  

### Coverage
- Files with exact analog: 12  
- Files with role-match / partial analog: 3  
- Files with no analog: 1 concern area (EMA + WS protocol body; REST/loop fully covered)

### Key Patterns Identified
- Daemon loops: start/stop/Event.wait keep-latest + product.error on exception (DepthLoop twin)
- PerceptionStore third product mirrors depth slot (in-process masks; metrics FPS window)
- Single `assemble_perception_frame` extracted from multi-product `/api/snapshot` merge
- Server-side overlay Option A: depth → free-space → boxes from store only
- Handler purity: no Spatial Post / inference in REST, WS, or MJPEG
- Perception-only `extra=forbid` + motor/safety denylist tests
- FreeSpaceLoop always-on with store (no ML extra); start after depth, stop first

### File Created
`.planning/phases/05-free-space-unified-stream/05-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
