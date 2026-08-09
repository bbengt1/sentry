# Phase 5: Free-Space & Unified Stream - Context

**Gathered:** 2026-08-08  
**Status:** Ready for planning  
**Source:** ROADMAP + project research + Phase 1–4 shipped contracts (YOLO mode)

<domain>
## Phase Boundary

Deliver the **core product thesis**: free-space / obstacles derived from monocular depth, plus a **unified versioned perception stream** robots can consume — with UI/API overlay parity and honest stale/TTL signaling.

**In scope:**
- Free-space / obstacle regions from depth (simple occupancy / near-field bands / image-space — **not** SLAM or Nav2 costmaps) (SPACE-01)
- Machine-readable obstacle cues on the stream (SPACE-02)
- Free-space / obstacle overlay on Live Preview (SPACE-03, UI-02)
- Stale / incomplete signaling (TTL + completeness); **no** “safe to proceed” language (SPACE-04)
- WebSocket `/v1/stream` merged `PerceptionFrame` (API-01)
- REST snapshot latest merged frame — extend/replace `/api/snapshot` under `/v1` (API-02)
- Completeness for depth, detections, free-space (API-03)
- Stream metadata: FPS, stage latency, drops (API-04)
- Perception-only boundary: no motor/velocity/commands (API-05)
- Single PerceptionStore truth for UI + robot API (UI-06)
- Temporal smoothing of free-space (reduce flicker)
- Expand `FreeSpacePayload` schema as needed

**Out of scope:**
- Stage enable toggles matrix / open-vocab (Phase 6)
- Edge TensorRT packaging (Phase 7)
- Full metric calibration UX, multi-cam fusion, ROS2 production bridge
- Robot control / path planning
- Dense mesh / NeRF / Gaussian splats

</domain>

<decisions>
## Implementation Decisions

### Locked from research / product
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

</decisions>

<canonical_refs>
## Canonical References

- `src/sentry_ai/schemas/perception.py` — FreeSpacePayload, PerceptionFrame, Completeness
- `src/sentry_ai/state/perception_store.py` — dual products
- `src/sentry_ai/models/depth/` — DepthProduct, depth_map
- `src/sentry_ai/api/routes_detection.py` — snapshot merge pattern
- `src/sentry_ai/api/routes_preview.py` — MJPEG overlays
- `.planning/research/SUMMARY.md` Phase 5 section
- `.planning/research/ARCHITECTURE.md` Spatial Post
- `.planning/research/PITFALLS.md` free-space / safety
- Phase 4 SUMMARYs

</canonical_refs>

<specifics>
## Specific Ideas

Roadmap plans (3):
1. 05-01 Spatial Post free-space/obstacle derivation + temporal smoothing
2. 05-02 Perception state store + merged frame assembly
3. 05-03 `/v1` WebSocket + REST docs, stale contract, full overlay parity

Success: depth → free-space overlay + obstacles JSON; WS `/v1/stream` + REST; stale flags; no motor fields.

</specifics>

<deferred>
## Deferred Ideas

- Full stage toggles / conf cutoffs UI matrix → Phase 6  
- Open-vocab → Phase 6  
- Edge export → Phase 7  
- Metric-calibrated free-space in meters → needs calibration (v2)

</deferred>

---
*Phase: 05-free-space-unified-stream*
