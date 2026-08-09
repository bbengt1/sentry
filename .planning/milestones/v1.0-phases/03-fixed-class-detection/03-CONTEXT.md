# Phase 3: Fixed-Class Detection - Context

**Gathered:** 2026-08-07  
**Status:** Ready for planning  
**Source:** ROADMAP + project research + Phase 1–2 shipped contracts (YOLO mode, no separate discuss-phase)

<domain>
## Phase Boundary

Deliver the **first robot-usable AI signal**: local fixed-class object detection on the live camera stream, with **UI and API parity** (same detections), runtime confidence control, and offline-capable model cache.

**In scope:**
- Local OSS fixed-class detector on live frames (YOLO26 / Ultralytics or equivalent)
- Detection products: class, confidence, bbox in image coordinates
- Runtime confidence threshold without process restart
- Model download + local cache for offline re-runs after first pull (MODEL-02)
- Dashboard overlays: boxes + labels on live preview
- Stream/snapshot endpoint exposing same detections as UI (DET-04 parity)
- Wire `Detection` / `PerceptionFrame` completeness for detections
- Detection worker as ModelWorker plugin; integrate with FrameBus + capture pipeline
- Stage latency / FPS telemetry for detection path

**Out of scope for this phase:**
- Open-vocabulary detection (Phase 6)
- Monocular depth (Phase 4)
- Free-space (Phase 5)
- Full `/v1` robot perception stream polish (Phase 5) — partial stream/snapshot for detections is OK
- Interactive multi-stage toggles dashboard (Phase 6) — conf threshold is required
- TensorRT export / edge packaging (Phase 7)
- Training / fine-tuning

</domain>

<decisions>
## Implementation Decisions

### Locked from research / project
- Fixed-class first: **YOLO26** via Ultralytics (n edge / s desktop); YOLO11 fallback only if needed
- Local OSS only; no cloud required after cache (MODEL-01 already, MODEL-02 this phase)
- UI and API share one truth (no dual detection paths)
- Workers never open cameras; read from FrameBus / ImageFrame
- Ultralytics AGPL: document in THIRD_PARTY_MODELS; default weight choice still YOLO for maker OSS path with AGPL disclosure
- Perception-only: no motor/control fields

### From Phase 1–2 shipped code (must respect)
- `ModelWorker` protocol: `process(frame) -> ...`
- `Detection` schema exists with `class_name`, `confidence`, `bbox_xyxy`
- `PerceptionFrame` + `Completeness.detections`
- `FrameBus` + `CaptureLoop` + FastAPI MJPEG/status at localhost
- `InferenceBackend` Protocol + NullBackend stubs
- Live Preview static HTML + MJPEG

### Claude's Discretion
- Detection worker thread vs sync on capture path
- Overlay: draw on JPEG in MJPEG path vs canvas JS boxes from JSON
- Exact API paths for snapshot (`/api/snapshot` vs `/v1/snapshot`)
- Model weight default (`yolo26n` vs `yolo26s`)
- Whether to add `supervision` for drawing or use OpenCV only

</decisions>

<canonical_refs>
## Canonical References

### Phase 1–2 code
- `src/sentry_ai/schemas/perception.py` — Detection, PerceptionFrame
- `src/sentry_ai/plugins/protocols.py` — ModelWorker
- `src/sentry_ai/backend/protocols.py` — InferenceBackend
- `src/sentry_ai/bus/frame_bus.py` — FrameBus
- `src/sentry_ai/capture/` — ImageFrame, CaptureLoop
- `src/sentry_ai/api/` — FastAPI preview routes
- `src/sentry_ai/ui/static/index.html` — Live Preview
- `THIRD_PARTY_MODELS.md` — Ultralytics AGPL note

### Planning
- `.planning/PROJECT.md`, `REQUIREMENTS.md` (DET-01..04, MODEL-02)
- `.planning/ROADMAP.md` Phase 3
- `.planning/research/SUMMARY.md`, `STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`
- Phase 2 CONTEXT / SUMMARYs

</canonical_refs>

<specifics>
## Specific Ideas

Roadmap plans (2):
1. Detection worker + backend protocol + model cache
2. Overlays, stream JSON, runtime conf, telemetry

Success: synthetic or USB stream shows labeled boxes; JSON endpoint matches; conf slider/API without restart; model cached after first download.

</specifics>

<deferred>
## Deferred Ideas

- Depth, free-space, open-vocab, full control plane, edge TRT → later phases

</deferred>

---
*Phase: 03-fixed-class-detection*
