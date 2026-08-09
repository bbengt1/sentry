# Phase 5: Free-Space & Unified Stream - Research

**Researched:** 2026-08-08  
**Domain:** Monocular free-space / obstacle post-process + versioned perception stream API (WS/REST) with UI/API parity  
**Confidence:** HIGH (architecture & codebase fit); MEDIUM (depth nearness polarity defaults; exact TTL numbers)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Free-space from depth via NumPy/OpenCV postprocess only (no second dense net)
- Spatial Post is sole free-space semantic owner
- Relative depth free-space is **image-space / ordinal** occupancy — not fake metric meters unless depth is metric
- Perception stream only; e-stop/control is consumer’s job
- UI overlays derive from same store robots read
- Localhost default bind preserved

### From Phase 1–4 shipped code
- `PerceptionStore` dual products (det + depth); extend for free-space
- `DepthProduct.depth_map` in-process for Spatial Post
- `FreeSpacePayload` placeholder exists — expand
- `/api/snapshot` already merges det+depth — evolve to `/v1/snapshot` + WS stream
- MJPEG overlay pipeline (depth blend → boxes) — add free-space draw
- Clean serve shutdown patterns

### Claude's Discretion
- Free-space algorithm: near-field percentile bands vs ground-plane vs BEV strip (research will pick default)
- Whether Spatial Post runs in DepthLoop after depth or separate FreeSpaceLoop
- Wire encoding for free-space mask (RLE, downsampled PNG, obstacle list only)
- WS framing: JSON vs binary for masks
- Keep `/api/snapshot` as alias to `/v1/snapshot` for back-compat

### Deferred Ideas (OUT OF SCOPE)
- Full stage toggles / conf cutoffs UI matrix → Phase 6  
- Open-vocab → Phase 6  
- Edge export → Phase 7  
- Metric-calibrated free-space in meters → needs calibration (v2)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| SPACE-01 | Free-space / obstacle regions from depth (simple occupancy / near-field bands — not SLAM) | Near-field percentile bands + morphology; pure NumPy/OpenCV Spatial Post |
| SPACE-02 | Obstacle cues machine-readable on perception stream | Expanded `FreeSpacePayload` + obstacle list on `/v1/stream` and snapshot |
| SPACE-03 | Free-space / obstacle overlay on web dashboard | Server-side `draw_free_space` in MJPEG path (same store as API) |
| SPACE-04 | Stale / incomplete signaling; no “safe to proceed” | Product ages + TTL + completeness flags; forbid go/nogo language |
| API-01 | WebSocket `/v1/stream` merged `PerceptionFrame` | FastAPI WebSocket + keep-latest JSON publisher |
| API-02 | REST snapshot latest `PerceptionFrame` | `GET /v1/snapshot` (+ `/api/snapshot` alias) |
| API-03 | Completeness for depth, detections, free-space | Extend merge assembler; `Completeness.free_space` from FreeSpaceProduct |
| API-04 | Stream metadata: FPS, stage latency, drops | Extend `stats` from store + bus metrics |
| API-05 | Never emit motor/velocity/path plans | `extra=forbid` + field denylist tests on v1 envelopes |
| UI-02 | Dashboard overlays detections, depth colormap, free-space | MJPEG draw order: depth → free-space → boxes |
| UI-06 | UI and robot API same perception state | Single PerceptionStore; no UI-only free-space path |
</phase_requirements>

## Summary

Phase 5 closes the product thesis: turn monocular depth into **actionable free-space / obstacles**, and expose a **versioned, perception-only** stream robots can trust for structure (not safety). The codebase already has the right spine — dual-product `PerceptionStore`, multi-product `GET /api/snapshot`, server-side MJPEG overlays from store, and optional DepthLoop/DetectionLoop wiring in `sentry serve`. Phase 5 extends that spine with a third product (`FreeSpaceProduct`), a pure Spatial Post stage, merged-frame assembly, `/v1` REST+WS contracts, stale/TTL honesty, and free-space drawing on Live Preview.

**Primary recommendation:** Ship **near-field percentile bands** (image-space ordinal occupancy) as the v1 free-space algorithm; run Spatial Post as a **separate FreeSpaceLoop** that consumes in-process `DepthProduct.depth_map`; put **obstacle lists + band stats** on the wire (not full masks); keep **full free-space mask in-process only** for MJPEG; publish **JSON** on `WS /v1/stream` with keep-latest backpressure; alias `/api/snapshot` → `/v1/snapshot`.

No second neural net, no SLAM, no BEV-as-default, no motor fields, no “safe to drive” UI.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Free-space derivation from depth | API / Backend (Spatial Post CPU) | — | Sole semantic owner; pure postprocess on depth maps |
| Temporal smoothing / morphology | API / Backend (Spatial Post) | — | Frame-to-frame CPU state on free-space product |
| Depth map storage (full float) | API / Backend (PerceptionStore) | — | In-process only; never bulk-serialize on wire (Phase 4 contract) |
| Free-space mask storage (full) | API / Backend (PerceptionStore) | Browser / Client | In-process for MJPEG; optional coarse mask on wire later |
| Obstacle list / bands wire payload | API / Backend | Browser / Client | Robot consumers + footer metrics |
| Merged `PerceptionFrame` assembly | API / Backend | — | Single assembler for REST + WS + (indirect) UI parity |
| WebSocket `/v1/stream` | API / Backend (FastAPI asyncio) | Robot client | Keep-latest fan-out; no inference in handlers |
| REST `/v1/snapshot` | API / Backend | — | Point-in-time merge of store products |
| Stale / TTL evaluation | API / Backend | Consumer | Server reports ages + flags; consumer invalidates |
| MJPEG free-space overlay | API / Backend (OpenCV draw) | Browser (display only) | Same store as snapshot (UI-06) |
| Live Preview footer free-space metrics | Browser / Client | API `/api/status` | Poll status JSON; no second truth |
| Perception-only boundary (API-05) | API / Backend (schema + tests) | Docs | `extra=forbid` + denylist; no control fields |

## Standard Stack

### Core

| Library | Version (verified) | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| Python | 3.11+ (project `.venv` 3.11.15) | Runtime | Project baseline |
| NumPy | 2.4.6 [VERIFIED: project venv] | Depth/mask arrays, percentiles, EMA | Already core dep; free-space math |
| OpenCV (headless) | 5.0.0 [VERIFIED: project venv] | Morphology, contours, overlay draw, optional PNG encode | Already core dep; matches detection/depth overlays |
| FastAPI | 0.141.1 [VERIFIED: project venv] | REST + WebSocket `/v1` | Already core; official WS support |
| Pydantic | 2.13.4 [VERIFIED: project venv] | `FreeSpacePayload` / `PerceptionFrame` contracts | Already core; `extra=forbid` |
| Uvicorn | 0.52.1 [VERIFIED: project venv] | ASGI server | Already core (`uvicorn[standard]`) |
| websockets | 17.0.1 [VERIFIED: project venv] | WS protocol backend for Starlette/FastAPI | Present via env; needed for FastAPI WS [CITED: fastapi.tiangolo.com/advanced/websockets/] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest + httpx | already in `dev` extra | REST + TestClient WS tests | All Phase 5 tests |
| Starlette WebSocket | via FastAPI/Starlette 1.4.1 | `WebSocket`, `WebSocketDisconnect` | Stream endpoint + disconnect handling |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Near-field percentile bands | Ground-plane RANSAC + height/pitch | Better on flat floors when extrinsics known; fails without mount calibration; out of honest relative-depth v1 default |
| Near-field percentile bands | BEV occupancy strip | Needs intrinsics + extrinsics; fake metric risk; defer as optional later |
| Separate FreeSpaceLoop | Inline free-space inside DepthLoop | Fewer threads, but couples Spatial Post to depth thread and hurts synthetic depth testing |
| JSON obstacle list on wire | Full HxW mask every WS frame | Bandwidth + JSON bloat; robots rarely need full mask at 15 Hz |
| JSON WS | msgpack/protobuf binary | Better for bulk depth/masks; overkill for v1 obstacle lists; defer |
| Server-side free-space draw | Client canvas from mask | Breaks current Option A parity (server OpenCV before JPEG); Phase 2–4 pattern is server draw |

**Installation:**

```bash
# No new packages required for Phase 5 free-space path.
# Core already includes numpy + opencv-python-headless + fastapi + uvicorn[standard].
# websockets is already available in the project venv (17.0.1).
# Optional explicit pin if planner wants guaranteed WS dep:
#   add websockets>=12,<18 to project dependencies (already transitive via uvicorn[standard] path in practice)

uv sync --extra dev --extra detect --extra depth   # full demo path
uv run pytest -q
```

**Version verification:** Confirmed in project `.venv` on 2026-08-08 via `uv run python -c "import …"`. Training data versions not used as truth.

## Package Legitimacy Audit

> Phase 5 **does not require installing new external packages**. Free-space is NumPy/OpenCV postprocess; stream uses FastAPI WebSocket already supported by the stack.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none new)* | — | — | — | — | — | N/A — reuse core deps |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*If a future plan pins `websockets` explicitly: it is a well-known Encode/Starlette ecosystem package already present at 17.0.1 in the venv — still run registry + slopcheck before adding to `pyproject.toml`.*

## Architecture Patterns

### System Architecture Diagram

```
Camera Source
    │
    ▼
FrameBus (keep-latest)
    │
    ├──────────────────┬──────────────────┐
    ▼                  ▼                  │
DetectionLoop      DepthLoop              │
    │                  │                  │
    │                  ▼                  │
    │            PerceptionStore          │
    │            .set_depth(DepthProduct  │
    │             + in-process depth_map) │
    │                  │                  │
    │                  ▼                  │
    │            FreeSpaceLoop  ◄─────────┘ (reads depth only; not FrameBus)
    │            Spatial Post (NumPy/CV)
    │                  │
    ▼                  ▼
PerceptionStore
  DetectionProduct | DepthProduct | FreeSpaceProduct
                  │
        assemble_perception_frame()
                  │
      ┌───────────┼──────────────┐
      ▼           ▼              ▼
 GET /v1/snapshot  WS /v1/stream  MJPEG /preview/mjpeg
 (+ /api/snapshot)  (JSON PF)     (draw from store)
      │           │              │
      └───────────┴──────────────┘
              same truth (UI-06)
```

### Recommended Project Structure

```
src/sentry_ai/
├── spatial/                      # NEW — Spatial Post owns free-space semantics
│   ├── __init__.py
│   ├── free_space.py             # pure: depth_map → FreeSpaceResult (bands, obstacles, mask)
│   ├── smoothing.py              # EMA / morphology / persistence helpers
│   ├── overlay.py                # draw_free_space(image_bgr, product) pure OpenCV
│   └── loop.py                   # FreeSpaceLoop daemon thread
├── schemas/
│   └── perception.py             # expand FreeSpacePayload (+ ObstacleCue)
├── state/
│   └── perception_store.py       # FreeSpaceProduct + set/snapshot + metrics
├── api/
│   ├── routes_v1.py              # NEW — /v1/snapshot, /v1/stream, optional /v1/health
│   ├── routes_detection.py       # keep /api/snapshot as thin alias OR shared assembler
│   ├── routes_preview.py         # MJPEG free-space draw + status free_space_* fields
│   ├── assemble.py               # NEW — single PerceptionFrame merge + stale/TTL
│   └── app.py                    # include v1 router
├── capture/
│   └── status.py                 # optional free_space_* telemetry fields
├── cli.py                        # FreeSpaceLoop lifecycle (always-on when store exists)
└── ui/static/index.html          # footer free_space / obstacles / STALE badge
```

### Pattern 1: Near-field percentile bands (v1 default free-space)

**What:** Convert monocular depth to **image-space nearness**, threshold the lower FOV into near/mid/far bands, extract obstacle blobs via connected components, smooth temporally.  
**When to use:** Always for relative depth; also as metric fallback when extrinsics unknown.  
**Why not ground-plane / BEV first:** Makers rarely have accurate height/pitch/intrinsics; relative depth cannot honestly claim meters; PITFALLS.md marks naive meter thresholds and missing extrinsics as critical. [CITED: .planning/research/PITFALLS.md §6, ARCHITECTURE.md free-space derivation]

**Algorithm (prescriptive):**

1. **Input:** `depth_map` HxW float32, `depth_kind`, optional finite mask.  
2. **Nearness polarity:** map depth → nearness ∈ [0,1] (1 = nearer).  
   - Prefer config `nearness_polarity`: `higher_is_farther` | `higher_is_nearer` | `auto`.  
   - **Default `auto`:** compare median of bottom 20% strip vs top 20% strip; bottom should be nearer for a typical robot-facing camera — choose polarity so bottom median nearness > top. [ASSUMED for DAV2 Small default orientation; golden test locks behavior]  
3. **ROI:** only evaluate free-space in lower fraction of image (default `roi_bottom_frac=0.55`) — sky/ceiling is not navigable free-space for ground robots.  
4. **Bands (ordinal, not meters):**  
   - `near`: nearness ≥ `near_cut` (default 0.72)  
   - `mid`: `mid_cut` ≤ nearness < `near_cut` (default 0.45)  
   - `far`: nearness < `mid_cut`  
5. **Occupied seed:** near band inside ROI (optionally dilate).  
6. **Morphology:** open then close (3×3 or 5×5) to kill speckles.  
7. **Obstacles:** connected components on occupied; filter `min_area_px`; emit bbox_xyxy + nearness_mean/max + area + band=`near`.  
8. **Free mask:** ROI pixels not occupied (or inverse of occupied after smoothing).  
9. **Honesty fields:** `method="near_field_bands"`, `depth_kind` copy, `units="ordinal"` when relative; **never** `distance_m` on relative paths.

### Pattern 2: Temporal smoothing (reduce flicker)

**What:** Stabilize binary occupancy across frames.  
**When to use:** Always on live free-space product (SPACE-01 quality bar).  

**Prescriptive stack (cheap, sufficient for v1):**

| Stage | Default | Role |
|-------|---------|------|
| Spatial morphology | open 3×3, close 5×5 | Remove salt/pepper before temporal |
| EMA on occupancy float | α = 0.35 | Soft history; then re-threshold at 0.5 |
| Persistence (optional) | N = 2 frames | Require occupied for N consecutive frames before publish as obstacle |
| Min area | 0.15% of ROI pixels | Drop tiny blobs |

**Do not** EMA the raw depth map as the primary smoother (costs more, couples to depth noise differently). Smooth **occupancy**. [ASSUMED: α/N defaults; expose as constants/config for Phase 6 knobs]

### Pattern 3: Separate FreeSpaceLoop (Spatial Post placement)

**What:** Daemon thread mirrors DetectionLoop/DepthLoop: poll latest depth product, compute free-space, write store.  
**When to use:** Phase 5 default.

```python
# Pattern (structural twin of DepthLoop; not production code)
# FreeSpaceLoop:
#   while not stop:
#     depth = store.snapshot_depth()
#     if depth is None or depth.error or depth.depth_map is None: sleep; continue
#     if depth.frame_id == last_id: sleep; continue
#     result = compute_free_space(depth.depth_map, kind=depth.kind, ...)
#     store.set_free_space(frame_id=depth.frame_id, ..., result)
```

**Why separate (vs inline after DepthLoop.set_depth):**
- Spatial Post remains sole free-space owner (architecture hard rule)
- Tests inject synthetic `DepthProduct` without running DAV2
- Depth thread stays focused on inference latency
- CPU work does not inflate `depth_latency_ms`
- Matches ARCHITECTURE.md: “Spatial post — CPU light — dedicated thread OK”

**Wiring:** Always start FreeSpaceLoop when `PerceptionStore` exists (no new ML extra). Degrade only if depth product never arrives → `completeness.free_space=false`.

### Pattern 4: Single assembler for merged PerceptionFrame

**What:** One pure function builds `PerceptionFrame` from store snapshots + wall clock.  
**When to use:** `/v1/snapshot`, `/api/snapshot`, `/v1/stream` — no forked merge logic.

```python
# Conceptual — Source: Phase 4 routes_detection.py multi-product merge + ARCHITECTURE.md
def assemble_perception_frame(
    store: PerceptionStore,
    *,
    now: float | None = None,
    ttl: TtlConfig | None = None,
) -> PerceptionFrame | None:
    det = store.snapshot()
    depth = store.snapshot_depth()
    free = store.snapshot_free_space()
    if det is None and depth is None and free is None:
        return None
    # primary identity = latest t_capture among present products
    # completeness.depth = depth ok and not error
    # completeness.detections = det present
    # completeness.free_space = free present and not error
    # free_space payload from FreeSpaceProduct (obstacles, bands, counts)
    # stats: latencies, fps, drops, ages, stale flags
    ...
```

### Pattern 5: WebSocket keep-latest publisher

**What:** Per-client loop: assemble → `send_json` → sleep; never queue frames.  
**When to use:** `WS /v1/stream`.

```python
# Source: https://fastapi.tiangolo.com/advanced/websockets/
from fastapi import WebSocket, WebSocketDisconnect

@router.websocket("/v1/stream")
async def v1_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            if shutdown_flag.is_set():
                break
            frame = assemble_perception_frame(store)
            if frame is not None:
                try:
                    await websocket.send_json(frame.model_dump())
                except RuntimeError:
                    break  # client gone mid-send
            await asyncio.sleep(1.0 / stream_hz)  # default ~10–15 Hz
    except WebSocketDisconnect:
        return
```

**Backpressure rules:**
- No per-client queue of PerceptionFrames
- If send is slow, next iteration still sends **latest** only (sleep still bounds rate)
- Slow clients must not block capture / FreeSpaceLoop (they already do not — store is keep-latest)
- Cap default stream rate (e.g. 10 Hz) independent of capture FPS [ASSUMED default 10 Hz]

### Pattern 6: MJPEG free-space overlay

**What:** Server-side draw from store free-space product, same Option A as detection/depth.  
**Draw order (prescriptive):**

1. Bus RGB  
2. `blend_depth` if depth product good  
3. `draw_free_space` if free-space product good (semi-transparent green free / amber-red near obstacles)  
4. `draw_detections` boxes last (readable labels)

**Never** invent free-space from raw depth inside the MJPEG handler — only store products (UI-06 / T-04-05 pattern).

### Anti-Patterns to Avoid

- **Hardcoded `depth < 1.5 m ⇒ obstacle` on relative maps:** Fake metric; scene-dependent disaster. Use ordinal bands.  
- **UI-only free-space path:** Breaks UI-06; robots see different world.  
- **Full depth_map / free mask in every JSON WS message:** Latency + bandwidth trap (PITFALLS demo-FPS ≠ control latency).  
- **“safe” / “go” / “clear to proceed” fields or UI copy:** SPACE-04 / API-05 product boundary.  
- **Running free-space inside request handlers:** Blocks API event loop; violates Phase 3–4 handler purity.  
- **SLAM / costmap / Nav2 integration in Phase 5:** Explicit out of scope.  
- **Ground-plane as silent default without extrinsics:** Looks smart, fails on pitch/stairs; optional later only.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Connected components / morphology | Custom flood-fill from scratch | `cv2.morphologyEx`, `cv2.connectedComponentsWithStats` | Edge cases, speed, correctness [CITED: OpenCV imgproc] |
| WebSocket protocol | Raw sockets | FastAPI/Starlette `WebSocket` | Framing, disconnect, TestClient support |
| Schema validation | Manual dict checks | Pydantic `extra=forbid` models | Motor-field rejection, OpenAPI-ish contracts |
| Keep-latest mailbox | Unbounded queues | PerceptionStore depth-1 slots (existing) | Latency spiral prevention already proven in FrameBus |
| Colormap / blend | New viz stack | Existing `blend_depth` + new `draw_free_space` | Parity with Phase 3–4 overlays |
| JSON serialization | Custom encoder | `PerceptionFrame.model_dump()` | Single contract |

**Key insight:** Phase 5 is **composition and contracts**, not new ML. Hand-rolling free-space nets, binary protocols, or planners delays the product thesis.

## Common Pitfalls

### Pitfall 1: Relative depth sold as metric free-space
**What goes wrong:** API field `distance_m` on relative obstacles; robots stop at wrong ranges.  
**Why it happens:** Depth maps “look metric” after colormap.  
**How to avoid:** Copy `depth_kind` onto free-space payload; `units="ordinal"` when relative; forbid meter fields unless kind is metric_*; honesty tests.  
**Warning signs:** Docs say “meters” next to relative badge; UI shows `m` without metric mode.

### Pitfall 2: Free-space flicker
**What goes wrong:** Obstacle blobs flash; consumer chatters.  
**Why it happens:** Single-frame monocular noise + naive threshold.  
**How to avoid:** Morphology + EMA + min area + optional persistence (Pattern 2).  
**Warning signs:** Obstacle count oscillates wildly on static scene.

### Pitfall 3: Ground-as-obstacle / sky-as-free without ROI
**What goes wrong:** Entire floor painted occupied, or sky painted free and treated as path.  
**Why it happens:** Full-frame thresholds ignore camera pitch and FOV semantics.  
**How to avoid:** Bottom ROI for occupancy evaluation; document that free-space is **image-plane near-field cues**, not a drivability certificate.  
**Warning signs:** `obstacle_count` huge on empty floor; free mask covers ceiling.

### Pitfall 4: Stale “all clear” after stream stall
**What goes wrong:** Last free-space remains complete while camera frozen.  
**Why it happens:** Completeness only checks presence, not age.  
**How to avoid:** Report `*_age_ms`, `stale` / `products_stale`, TTL defaults; UI STALE badge; docs: consumers must invalidate.  
**Warning signs:** Capture status reconnecting but free_space completeness still true with age_ms → large.

### Pitfall 5: Dual merge logic (REST vs WS vs MJPEG)
**What goes wrong:** Overlay obstacles ≠ snapshot obstacles.  
**Why it happens:** Copy-paste merge in three places.  
**How to avoid:** Single `assemble_perception_frame` + MJPEG reads same FreeSpaceProduct fields used to build payload.  
**Warning signs:** Tests pass snapshot but manual overlay count differs.

### Pitfall 6: WS backpressure into perception
**What goes wrong:** Slow robot client delays free-space updates.  
**Why it happens:** Blocking send or growing per-client queues.  
**How to avoid:** Keep-latest; fixed stream Hz; never call Spatial Post from WS task.  
**Warning signs:** free_space latency rises with extra WS clients.

### Pitfall 7: Motor / safety language creep
**What goes wrong:** Field `safe_to_drive` or UI “GO”.  
**Why it happens:** Product narrative pressure.  
**How to avoid:** Schema forbid + UI-SPEC + API-05 tests; language: obstacles / free_space / incomplete / stale only.  
**Warning signs:** PR copy says “navigation cleared”.

## Code Examples

### FreeSpacePayload expansion (target schema)

```python
# Target shape for Phase 5 — expand existing FreeSpacePayload placeholder
# Source: schemas/perception.py + ARCHITECTURE.md FreeSpaceResult

class ObstacleCue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bbox_xyxy: tuple[float, float, float, float] | list[float]
    nearness_mean: float  # 0..1 ordinal; NOT meters
    nearness_max: float
    area_px: int
    band: Literal["near", "mid", "far"] = "near"
    # Intentionally NO distance_m

class FreeSpacePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    method: Literal["near_field_bands"] = "near_field_bands"
    depth_kind: DepthKind
    units: Literal["ordinal", "m"] = "ordinal"  # "m" only if depth metric
    obstacle_count: int = 0
    obstacles: list[ObstacleCue] = Field(default_factory=list)
    bands: dict[str, float] | None = None  # e.g. near_frac, mid_frac, far_frac in ROI
    # Optional later: mask_encoding + mask_b64 — omit from default WS for v1
    width: int | None = None
    height: int | None = None
    roi_bottom_frac: float | None = None
```

### FreeSpaceProduct (in-process store)

```python
@dataclass
class FreeSpaceProduct:
    frame_id: int
    camera_id: str
    t_capture: float  # from source depth product
    t_compute: float  # time.time() when produced
    latency_ms: float
    depth_kind: DepthKind
    obstacle_count: int
    obstacles: list[ObstacleCue]
    bands: dict[str, float]
    free_mask: Any | None  # HxW uint8 in-process only (optional)
    occupied_mask: Any | None
    method: str = "near_field_bands"
    error: str | None = None
```

### Stale / TTL contract (product ages)

```python
# Recommended defaults [ASSUMED — tune after first live run]
DEFAULT_TTL_MS = {
    "detections": 500,
    "depth": 750,
    "free_space": 750,
}

# completeness.* = product present and error is None (availability)
# stale_* = age_ms > ttl_ms (freshness) — separate bits so partial frames stay useful
# stats example:
# {
#   "det_age_ms": 42.0,
#   "depth_age_ms": 80.0,
#   "free_space_age_ms": 85.0,
#   "det_stale": False,
#   "depth_stale": False,
#   "free_space_stale": False,
#   "products_stale": False,  # any true
#   "capture_fps": 30.0,
#   "det_fps": 15.0,
#   "depth_fps": 8.0,
#   "free_space_fps": 8.0,
#   "frames_dropped": 12,
#   "det_latency_ms": ...,
#   "depth_latency_ms": ...,
#   "free_space_latency_ms": ...,
# }
```

### Synthetic depth map for tests (no model)

```python
import numpy as np

def synthetic_near_obstacle_depth(h=120, w=160) -> np.ndarray:
    """Higher values = farther (higher_is_farther). Near blob in lower-center."""
    yy, xx = np.mgrid[0:h, 0:w]
    depth = 0.2 + 0.8 * (yy / max(h - 1, 1))  # bottom nearer if inverted later
    # Prefer explicit polarity in tests:
    # depth: larger = farther; obstacle = small values in lower center
    depth = np.full((h, w), 5.0, dtype=np.float32)
    depth[int(h * 0.55) : h, int(w * 0.35) : int(w * 0.65)] = 0.5  # near obstacle
    return depth
```

### Perception-only guard (API-05)

```python
FORBIDDEN_TOP_LEVEL = {
    "cmd", "velocity", "motor", "path_plan", "motor_command",
    "twist", "cmd_vel", "steering", "throttle", "safe_to_drive", "go_nogo",
}

def assert_perception_only(payload: dict) -> None:
    assert FORBIDDEN_TOP_LEVEL.isdisjoint(payload.keys())
    # also reject nested free_space.safe / go flags in tests
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Raw monocular depth only | Depth + Spatial Post free-space | Sentry Phase 5 | Robot-usable occupancy cues |
| Binary depth threshold in meters | Ordinal near-field bands + ROI | Maker monocular honesty | Avoids fake metric crashes |
| Full Nav2 costmaps for “free space” | Lightweight image-plane obstacles | Product scope | Ship weeks not months |
| UI-only overlays | Single PerceptionStore fan-out | Phase 3–4 pattern | UI/API parity |
| Unbounded frame queues | Keep-latest everywhere | Phase 2 bus | Bounded latency |

**Deprecated/outdated for this phase:**
- Ground-plane RANSAC as **required** v1 path without extrinsics UX  
- Binary msgpack perception stream as v1 blocker  
- Client-side free-space recompute from colormap JPEG (lossy, dual truth)

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | DAV2 Small relative maps are best handled via configurable nearness polarity with `auto` bottom/top heuristic | Free-space algorithm | Wrong polarity inverts free/occupied; mitigated by synthetic tests + polarity config |
| A2 | Default TTL 500/750/750 ms is acceptable for makers | Stale contract | Too tight → constant STALE; too loose → hazard; expose constants |
| A3 | Default WS stream rate 10 Hz is enough for robot consumers in v1 | WS design | High-rate control loops need consumer-side interpolation; document |
| A4 | Obstacle list + band fractions sufficient on wire; full mask not required on WS for v1 | Wire encoding | Some consumers want mask — can add optional `include_mask` later without breaking schema_version 1 if additive |
| A5 | EMA α=0.35 + open/close morphology is “good enough” vs Kalman | Temporal smoothing | Residual flicker — Phase 6 knobs |
| A6 | FreeSpaceLoop can always run without new extras (CPU-only) | Placement | Negligible CPU cost; if proven hot, downsample mask |

**If this table is empty:** All claims verified — not the case; A1–A6 need live validation but are safe defaults for planning.

## Open Questions

1. **Nearness polarity default for real DAV2 Small outputs**  
   - What we know: relative monocular maps are ordinal; Phase 4 stores float maps without unit semantics beyond `depth_kind`.  
   - What's unclear: exact higher=nearer vs higher=farther on HF Small relative in this preprocess path.  
   - **Recommendation:** Implement `auto` + unit tests with both polarities; lock with one golden synthetic + one optional live smoke note. Default config `auto`.

2. **Should `/api/snapshot` remain forever or soft-deprecate?**  
   - What we know: Phase 3–4 clients/tests use `/api/snapshot`.  
   - **Recommendation:** Keep as **alias** calling the same assembler as `/v1/snapshot` (Claude discretion locked toward back-compat). Document `/v1` as canonical.

3. **Include downsampled free mask on REST snapshot?**  
   - What we know: depth_map never on wire.  
   - **Recommendation:** v1 default **omit** mask on JSON; obstacles + bands only. Overlay uses in-process mask. Optional query `?include_mask=1` is Phase 6+ if needed.

4. **Free-space when depth is metric_estimated**  
   - What we know: metric modes exist via PATCH depth config.  
   - **Recommendation:** Still use ordinal bands by default; optionally expose nearness only — do **not** convert to meters without calibration metadata. Set `units="ordinal"` even if depth_kind is metric_estimated unless a future calibrated path exists.

5. **Same-frame merge timeout**  
   - What we know: det and depth already run async with different frame_ids.  
   - **Recommendation:** Continue latest-per-product merge (Phase 4); free_space attaches to **depth frame_id** (its parent). Do not block for same-frame det+depth match in v1.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | Runtime | ✓ | 3.11.15 (.venv) | — |
| NumPy | Free-space math | ✓ | 2.4.6 | — |
| OpenCV headless | Morphology + overlay | ✓ | 5.0.0 | — |
| FastAPI | REST/WS | ✓ | 0.141.1 | — |
| websockets | FastAPI WS | ✓ | 17.0.1 | Pin explicitly if missing on clean install |
| pytest + httpx | Tests | ✓ | pytest 8.x / httpx (dev) | — |
| torch / transformers | Depth product (optional) | optional extra | — | Synthetic DepthProduct in tests; free-space does not import HF |
| ultralytics | Detection product (optional) | optional extra | — | Not required for free-space tests |

**Missing dependencies with no fallback:** none for Phase 5 core path.

**Missing dependencies with fallback:** real DAV2 weights (manual smoke only; CI uses synthetic depth maps).

## Validation Architecture

> `workflow.nyquist_validation` is enabled in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (dev extra, ≥8) |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_free_space.py tests/test_spatial_loop.py tests/test_api_v1.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SPACE-01 | Synthetic depth → occupied near blob + free ROI | unit | `uv run pytest tests/test_free_space.py -q` | ❌ Wave 0 |
| SPACE-01 | Morphology/EMA reduces single-pixel flicker | unit | `uv run pytest tests/test_free_space.py::test_smoothing -q` | ❌ Wave 0 |
| SPACE-02 | FreeSpacePayload has obstacles list + counts | unit | `uv run pytest tests/test_schemas_perception.py -q` | ⚠️ extend existing |
| SPACE-02 | Snapshot/stream include free_space when product set | API | `uv run pytest tests/test_api_v1.py -q` | ❌ Wave 0 |
| SPACE-03 | `draw_free_space` paints without mutating input | unit | `uv run pytest tests/test_free_space_overlay.py -q` | ❌ Wave 0 |
| SPACE-03 | MJPEG path calls store free-space (no inference) | unit | `uv run pytest tests/test_api_preview.py -q` | ⚠️ extend |
| SPACE-04 | Age > TTL → stale flags true; completeness separate | unit | `uv run pytest tests/test_assemble_frame.py -q` | ❌ Wave 0 |
| SPACE-04 | No safe/go language in UI strings / payload keys | unit | `uv run pytest tests/test_api_v1.py tests/test_api_preview.py -q` | ⚠️ extend |
| API-01 | WS `/v1/stream` yields PerceptionFrame JSON | integration | `uv run pytest tests/test_api_v1.py::test_ws_stream -q` | ❌ Wave 0 |
| API-02 | GET `/v1/snapshot` matches store merge | API | `uv run pytest tests/test_api_v1.py::test_snapshot -q` | ❌ Wave 0 |
| API-02 | `/api/snapshot` alias parity | API | `uv run pytest tests/test_api_detection.py` + v1 parity test | ⚠️ extend |
| API-03 | completeness.free_space true only when product good | API | `uv run pytest tests/test_api_v1.py -q` | ❌ Wave 0 |
| API-04 | stats include fps/latency/drops/ages | API | `uv run pytest tests/test_api_v1.py -q` | ❌ Wave 0 |
| API-05 | PerceptionFrame rejects motor/velocity; dump keys clean | unit | `uv run pytest tests/test_schemas_perception.py tests/test_api_v1.py -q` | ⚠️ extend denylist |
| UI-02 | Status exposes free_space metrics for footer | API | `uv run pytest tests/test_api_preview.py -q` | ⚠️ extend |
| UI-06 | Overlay product fields match snapshot free_space | unit | `uv run pytest tests/test_api_v1.py::test_parity -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_free_space.py tests/test_spatial_loop.py tests/test_api_v1.py -q`  
- **Per wave merge:** `uv run pytest -q`  
- **Phase gate:** Full suite green before `/gsd:verify-work` + ruff

### Wave 0 Gaps

- [ ] `tests/test_free_space.py` — pure algorithm + polarity + ROI + synthetic obstacles (SPACE-01)
- [ ] `tests/test_free_space_smoothing.py` or section in above — EMA/morphology stability
- [ ] `tests/test_free_space_overlay.py` — draw helper (SPACE-03)
- [ ] `tests/test_spatial_loop.py` — FreeSpaceLoop keep-latest / error paths
- [ ] `tests/test_assemble_frame.py` — merge + TTL/stale + completeness (SPACE-04, API-03/04)
- [ ] `tests/test_api_v1.py` — `/v1/snapshot`, `/v1/stream` WS, alias parity, API-05 denylist
- [ ] Extend `tests/test_schemas_perception.py` — expanded FreeSpacePayload fields
- [ ] Extend `tests/test_perception_store.py` — FreeSpaceProduct set/snapshot metrics
- [ ] Extend `tests/test_api_preview.py` / `test_cli_serve.py` — free-space status + loop lifecycle
- [ ] Framework install: already present (`uv sync --extra dev`)

**Existing baseline:** 242 tests collected; free-space currently only placeholder completeness=false.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (localhost default; no auth in v1) | Document opt-in LAN risk (existing MODEL-03) |
| V3 Session Management | no | — |
| V4 Access Control | partial | Bind default 127.0.0.1; no motor API surface |
| V5 Input Validation | yes | Pydantic `extra=forbid` on config + payloads; WS JSON schema dump only outbound |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Fake metric free-space → robot collision | Tampering / elevation of privilege over physics | Ordinal units + depth_kind honesty tests |
| Stale free-space treated as live | Spoofing of environment state | TTL/age flags; consumer docs |
| Motor command injection via extra JSON fields | Elevation | `extra=forbid` + API-05 denylist tests |
| LAN exposure of camera + occupancy | Information disclosure | Localhost default; existing serve warning |
| Handler-side inference DoS | Denial of service | Handlers read store only; FreeSpaceLoop drop/keep-latest |
| “Safe to drive” social-engineering via UI | Repudiation / misuse | UI-SPEC ban; string tests |

## What NOT to Build (Phase 5)

| Do not build | Why |
|--------------|-----|
| Second dense free-space / occupancy network | Locked: NumPy/OpenCV only |
| SLAM, pose graph, dense map, Nav2 costmaps | Out of scope / roadmap v2 |
| Ground-plane RANSAC as required default | Needs extrinsics UX; discretionary later |
| BEV projection as default | Intrinsics/extrinsics; fake metric risk |
| Robot control, cmd_vel, path plans | API-05 |
| “Safe / go / nogo” API fields or UI | SPACE-04 |
| Full float depth or free mask on every WS frame | Bandwidth/latency |
| msgpack/protobuf binary framing | Defer; JSON sufficient for obstacles |
| Stage toggle matrix / free-space cutoff slider UX | Phase 6 (optional minimal footer only) |
| Open-vocab, edge TensorRT, multi-cam fusion | Later phases |
| Free-space recompute inside FastAPI handlers | Architecture purity |
| Dual UI-only free-space path | UI-06 |

## Recommended Defaults (planner-ready)

| Decision | Default | Rationale |
|----------|---------|-----------|
| Free-space algorithm | Near-field percentile bands + bottom ROI | Honest with relative depth; no calibration |
| Spatial Post placement | Separate `FreeSpaceLoop` | Testability; sole owner; CPU not on depth latency |
| Temporal smoothing | Morphology + EMA(α=0.35) + min area | Fixes flicker pitfall without heavy filters |
| Wire free-space body | Obstacles + bands + counts + method + depth_kind | SPACE-02 without bulk |
| In-process mask | Yes (`occupied_mask` / `free_mask`) for MJPEG | Overlay parity |
| WS framing | JSON text frames of `PerceptionFrame` | FastAPI-native; easy robot clients |
| WS rate | 10 Hz default | Independent of capture; keep-latest |
| REST | `GET /v1/snapshot` + alias `GET /api/snapshot` | Back-compat |
| Stale | Ages + per-product stale flags; TTL 500/750/750 ms | SPACE-04 without killing completeness usefulness |
| Draw order | depth blend → free-space → boxes | Readable labels |
| New packages | None | Reuse numpy/opencv/fastapi |
| FreeSpaceLoop start | With serve whenever store exists | No new ML extra |

## Suggested Plan Split (maps to roadmap)

1. **05-01 Spatial Post** — `spatial/free_space.py`, smoothing, FreeSpaceLoop, store FreeSpaceProduct, unit tests with synthetic depth  
2. **05-02 Merged assembly** — expand schemas, `assemble_perception_frame`, metrics/TTL, store completeness path  
3. **05-03 `/v1` + overlay parity** — routes_v1 WS/REST, alias, MJPEG draw, UI footer/STALE, serve lifecycle, API-05 tests, README

## Sources

### Primary (HIGH confidence)

- Codebase: `src/sentry_ai/schemas/perception.py`, `state/perception_store.py`, `models/depth/*`, `api/routes_detection.py`, `api/routes_preview.py`, `api/app.py`, `cli.py`, `bus/frame_bus.py`  
- Phase 3–4 SUMMARYs (overlay Option A, multi-product snapshot, optional extras)  
- `.planning/research/ARCHITECTURE.md` — Spatial Post, free-space derivation, WS envelope, queue policies  
- `.planning/research/PITFALLS.md` — relative-as-metric, naive free-space, stale perception, latency  
- `.planning/research/SUMMARY.md` / `FEATURES.md` — Phase 5 scope and non-goals  
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) — accept/send/disconnect patterns [CITED]  
- OpenCV morphology / connected components (project uses OpenCV 5.0.0) [VERIFIED: project venv]

### Secondary (MEDIUM confidence)

- Industry topology analogies (DepthAI nodes, Isaac ROS graphs, Nav2 free-space *expectations*) from project research — not copied as implementations  
- TTL/stream Hz defaults — operational assumptions pending live robot feedback

### Tertiary (LOW confidence)

- Exact DAV2 Small nearness polarity without live sample in this session — mitigated by `auto` + tests [ASSUMED]

## Project Constraints (from project docs)

- Camera-only perception; no required LiDAR/radar  
- Local OSS models; no mandatory cloud  
- Perception stream only — no robot control  
- Localhost default bind (MODEL-03)  
- Relative depth never labeled as meters (FOUND-03)  
- Single PerceptionStore truth for UI + API (UI-06)  
- Keep-latest drop policy; no unbounded queues (CAM-05 pattern)  
- Commercially friendly defaults; free-space adds **no** NC weights  

*(No project-local `CLAUDE.md` / skills directory in repo; followed GSD + `.planning` contracts.)*

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — verified in project venv; no new packages  
- Architecture: **HIGH** — matches locked research + shipped Phase 1–4 patterns  
- Free-space algorithm: **HIGH** for approach (near-field bands); **MEDIUM** for polarity/TTL knobs  
- Pitfalls: **HIGH** — well-documented in project PITFALLS + monocular literature  

**Research date:** 2026-08-08  
**Valid until:** ~2026-09-07 (30 days; stack stable; algorithm knobs may refine after first live demos)

---

## RESEARCH COMPLETE

**Phase:** 5 - Free-Space & Unified Stream  
**Confidence:** HIGH (implementation path); MEDIUM (polarity/TTL defaults)

### Key Findings

1. **v1 free-space = near-field percentile bands** (image-space ordinal), not ground-plane/BEV — honest with relative monocular depth and maker cameras.  
2. **Separate FreeSpaceLoop** consumes in-process `DepthProduct.depth_map`; expands store to a third product; pure NumPy/OpenCV Spatial Post owns semantics.  
3. **Wire = obstacle list + bands + completeness/stale stats**; full masks stay in-process for MJPEG (mirror depth_map policy).  
4. **`/v1/snapshot` + `WS /v1/stream` (JSON keep-latest)** with `/api/snapshot` alias; single `assemble_perception_frame` for UI/API parity.  
5. **No new packages**; test with synthetic depth maps; forbid motor/safety fields (API-05 / SPACE-04).

### File Created

`.planning/phases/05-free-space-unified-stream/05-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Verified versions; zero new deps |
| Architecture | HIGH | Extends proven store/loop/overlay patterns |
| Pitfalls | HIGH | Project research + monocular free-space failure modes |
| Algorithm knobs | MEDIUM | Polarity/TTL/α need live tuning |

### Open Questions

- DAV2 nearness polarity (mitigated by `auto`)  
- Optional mask on REST later  
- Exact stream Hz / TTL after first robot client

### Ready for Planning

Research complete. Planner can create PLAN.md files for 05-01 / 05-02 / 05-03.
