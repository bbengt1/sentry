# Phase 4: Monocular Depth - Context

**Gathered:** 2026-08-07  
**Status:** Ready for planning  
**Source:** ROADMAP + research + Phase 1–3 shipped contracts (YOLO mode)

<domain>
## Phase Boundary

Add the **spatial awareness primitive**: local monocular depth with **honest semantics** (relative by default), depth on the perception stream with `depth_kind`, depth colormap on the dashboard, optional metric mode clearly labeled, and depth stage latency telemetry.

**In scope:**
- Local monocular depth model (Depth Anything V2 **Small** Apache-2.0 default)
- Per-frame depth map production on live stream (parallel to detection pattern)
- Stream/snapshot includes depth with explicit `depth_kind` (DEPTH-02)
- Dashboard depth colormap (overlaid or side-by-side) (DEPTH-03)
- Optional metric mode labeled; never conflate with relative (DEPTH-04)
- Stage latency for depth in telemetry
- Extend PerceptionStore / PerceptionFrame for depth products
- Model cache reuse for depth weights
- Mock-friendly CI (no weight download / heavy GPU required in default tests)

**Out of scope for this phase:**
- Free-space / obstacles derivation (Phase 5)
- Full `/v1` WS robot stream polish (Phase 5) — extend snapshot OK
- Open-vocab, full stage toggles (Phase 6)
- TensorRT export (Phase 7)
- Stereo / multi-cam depth
- Full metric calibration UX (optional metric mode only; calibration later)

</domain>

<decisions>
## Implementation Decisions

### Locked from project / research
- Default depth: **DAV2 Small** (Apache-2.0) — never default NC Base/Large/Giant
- Relative by default; metric only when explicitly enabled with correct `depth_kind` + unit
- No `depth_m` field on relative paths; existing `DepthPayload` + validators
- Depth worker never opens cameras; FrameBus → worker → store (mirror DetectionLoop)
- UI and API share one depth product truth
- Local OSS only; cache after first download

### From Phase 1–3 shipped code
- `DepthKind`, `DepthPayload`, `PerceptionFrame`, `Completeness.depth`
- `DetectionLoop` / `PerceptionStore` / `YoloDetectionWorker` patterns
- Model cache (`SENTRY_MODEL_CACHE`)
- FastAPI snapshot + MJPEG overlay pattern
- optional-extra pattern for heavy deps (`detect`)

### Claude's Discretion
- HF transformers vs native DAV2 repo load path
- Depth product storage: full float map in process vs downsampled for JSON
- Colormap: side-by-side vs alpha blend vs toggle
- Whether depth is optional-extra `depth` (recommended, mirror detect)
- Metric indoor vs outdoor head selection UX (config flag)

</decisions>

<canonical_refs>
## Canonical References

- `src/sentry_ai/schemas/enums.py` — DepthKind
- `src/sentry_ai/schemas/perception.py` — DepthPayload, PerceptionFrame
- `src/sentry_ai/schemas/validators.py` — relative forbids meters
- `src/sentry_ai/models/detection/loop.py`, `yolo_worker.py` — worker/loop analogs
- `src/sentry_ai/state/perception_store.py`
- `src/sentry_ai/models/cache.py`
- `src/sentry_ai/api/routes_preview.py`, `routes_detection.py`
- `src/sentry_ai/policy/models.py` — DEFAULT_DEPTH_WEIGHT_KEY
- `THIRD_PARTY_MODELS.md`
- `.planning/research/STACK.md`, `PITFALLS.md`, `SUMMARY.md`
- Phase 3 SUMMARYs / plans for pattern parity

</canonical_refs>

<specifics>
## Specific Ideas

Roadmap plans (2):
1. 04-01: Depth worker (DAV2 Small) + preprocess + golden tests
2. 04-02: Depth stream payload, colormap UI, optional metric labeling

Success: synthetic/USB stream produces depth; snapshot has depth_kind; UI shows colormap; relative never labeled meters; latency in status.

</specifics>

<deferred>
## Deferred Ideas

- Free-space Spatial Post → Phase 5
- Open-vocab → Phase 6
- Edge TensorRT depth → Phase 7
- Full metric calibration tools → v2

</deferred>

---
*Phase: 04-monocular-depth*
