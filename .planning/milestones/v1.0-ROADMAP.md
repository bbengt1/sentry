# Roadmap: Sentry AI

## Overview

Build an open-source, camera-only perception product for maker robotics: start with schemas, camera ingest, and a live preview, then layer fixed-class detection, monocular depth, free-space/obstacles, and a unified perception stream. Finish with interactive developer controls, open-vocabulary detection, and multi-target edge profiles plus extension stubs. Each phase is a runnable vertical slice — makers never wait until “the end” to see something real.

## Phases

- [x] **Phase 1: Foundations & Contracts** — Repo skeleton, schemas, plugins, licenses, device abstraction (completed 2026-08-07)
- [x] **Phase 2: Camera Ingest & Live Preview** — USB/file/synthetic/RTSP sources, frame bus, web preview (completed 2026-08-07)
- [x] **Phase 3: Fixed-Class Detection** — Local YOLO detection worker, overlays, stream detections (completed 2026-08-07)
- [x] **Phase 4: Monocular Depth** — Depth Anything V2 pipeline with honest depth typing (completed 2026-08-08)
- [x] **Phase 5: Free-Space & Unified Stream** — Spatial post, merged PerceptionFrame API, obstacle overlays (completed 2026-08-08)
- [x] **Phase 6: Developer Controls & Open-Vocab** — Interactive console + promptable detection (completed 2026-08-08)
- [x] **Phase 7: Edge Profiles & Extension Stubs** — Desktop/Jetson/CPU profiles, export recipes, future hooks (completed 2026-08-08)

## Phase Details

### Phase 1: Foundations & Contracts
**Goal**: Establish the product skeleton and non-negotiable contracts so every later phase shares types, plugins, licenses, and multi-target hooks.  
**Depends on**: Nothing (first phase)  
**Requirements**: FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, MODEL-01  
**Success Criteria** (what must be TRUE):
  1. Developer can install the package and run a health/smoke command against synthetic frames
  2. `Frame` / `PerceptionFrame` schemas include `frame_id`, `camera_id`, timestamps, and `depth_kind` enum
  3. Plugin registry stubs exist for sources, model workers, and sinks
  4. `THIRD_PARTY_MODELS.md` documents default model licenses; defaults exclude NC-only weights
  5. Config supports runtime profile names (`desktop-gpu`, `jetson`, `cpu-fallback`) even if only desktop is implemented
**Plans**: 3 plans

Plans:
- [x] 01-01: Project scaffold (package layout, tooling, CI smoke, one-command start skeleton)
- [x] 01-02: Core schemas + PerceptionFrame contracts + config system
- [x] 01-03: Plugin registry stubs, device/backend protocols, model license policy docs

### Phase 2: Camera Ingest & Live Preview
**Goal**: Prove “any camera works” with a realtime capture loop, keep-latest frame bus, and browser preview — no models yet.  
**Depends on**: Phase 1  
**Requirements**: CAM-01, CAM-02, CAM-03, CAM-04, CAM-05, CAM-06, UI-01, MODEL-03  
**Success Criteria** (what must be TRUE):
  1. USB camera and file/video source produce live frames with stable `frame_id`s
  2. Synthetic source powers automated tests without hardware
  3. RTSP/network camera source works or is documented with known limits
  4. Frame bus drops oldest under load and reports drop metrics (no unbounded queue growth)
  5. Browser shows live preview; camera unplug surfaces a clear error and recovery path
  6. Default server bind is localhost
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Camera source adapters (USB, file, synthetic) + reconnect policy foundation
- [x] 02-02-PLAN.md — Frame bus (keep-latest), timestamps, drop metrics + capture loop
- [x] 02-03-PLAN.md — FastAPI shell + MJPEG preview + static Live Preview + RTSP + localhost serve CLI

### Phase 3: Fixed-Class Detection
**Goal**: Deliver the first robot-usable AI signal — local fixed-class detection on the live stream with UI/API parity.  
**Depends on**: Phase 2  
**Requirements**: DET-01, DET-02, DET-03, DET-04, MODEL-02  
**Success Criteria** (what must be TRUE):
  1. Local OSS fixed-class detector runs on live frames without cloud
  2. Boxes + labels + confidences appear on the dashboard overlay
  3. Same detections are available on a stream/snapshot endpoint
  4. Confidence threshold changes at runtime without process restart
  5. Models cache locally for offline re-runs after first download
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Detection worker (YOLO26) + backend protocol + model cache
- [x] 03-02-PLAN.md — Detection overlays, stream/snapshot JSON, runtime conf control, telemetry

### Phase 4: Monocular Depth
**Goal**: Add the spatial awareness primitive with honest monocular depth semantics (relative by default).  
**Depends on**: Phase 3  
**Requirements**: DEPTH-01, DEPTH-02, DEPTH-03, DEPTH-04  
**Success Criteria** (what must be TRUE):
  1. Local monocular depth model produces a per-frame depth map
  2. Stream includes depth with explicit `depth_kind` (relative vs metric modes)
  3. Dashboard shows depth colormap overlaid or side-by-side with RGB
  4. Relative depth is never exposed as meters; optional metric mode is clearly labeled
  5. Stage latency for depth is reported in telemetry
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Depth worker (DAV2 Small) + preprocess contract + golden tests + DepthLoop + store extension + cache
- [x] 04-02-PLAN.md — Depth stream payload, colormap UI, optional metric mode labeling, telemetry, serve wiring

### Phase 5: Free-Space & Unified Stream
**Goal**: Deliver the core product thesis — free-space/obstacles from depth plus a unified, versioned perception stream robots can consume.  
**Depends on**: Phase 4  
**Requirements**: SPACE-01, SPACE-02, SPACE-03, SPACE-04, API-01, API-02, API-03, API-04, API-05, UI-02, UI-06  
**Success Criteria** (what must be TRUE):
  1. Free-space / obstacle regions are derived from depth and shown on the dashboard
  2. WebSocket `/v1/stream` delivers merged `PerceptionFrame` with completeness flags
  3. REST snapshot returns the latest merged frame
  4. Stale or incomplete data is visible to consumers (TTL / completeness); no “safe to proceed” claims
  5. UI overlays match API content (single perception state store)
  6. Stream metadata includes FPS, stage latency, and drops
**Plans**: 3 plans

Plans:
- [x] 05-01-PLAN.md — Spatial Post free-space/obstacle derivation + temporal smoothing
- [x] 05-02-PLAN.md — Perception state store + merged frame assembly
- [x] 05-03-PLAN.md — `/v1` WebSocket + REST API docs, stale contract, full overlay parity

### Phase 6: Developer Controls & Open-Vocab
**Goal**: Make the developer console fully interactive and add open-vocabulary detection as the flexible query path.  
**Depends on**: Phase 5  
**Requirements**: UI-03, UI-04, UI-05, OVD-01, OVD-02, OVD-03  
**Success Criteria** (what must be TRUE):
  1. Developer can enable/disable detection, depth, and free-space stages live
  2. Thresholds (conf, depth/free-space cutoffs) adjust interactively from the UI
  3. Performance telemetry is visible in the dashboard
  4. Open-vocab prompts produce detections for custom classes via local OSS model
  5. Open-vocab can run on-demand or lower-rate without blocking the fixed-class path
**Plans**: 2 plans

Plans:
- [x] 06-01-PLAN.md — Control plane + full interactive UI (toggles, thresholds, telemetry)
- [x] 06-02-PLAN.md — Open-vocab worker (YOLOE) + prompt UX + stream/UI integration

### Phase 7: Edge Profiles & Extension Stubs
**Goal**: Make multi-target deployment real and leave clean extension points for post-v1 capabilities.  
**Depends on**: Phase 6  
**Requirements**: EDGE-01, EDGE-02, EDGE-03, EDGE-04, EDGE-05  
**Success Criteria** (what must be TRUE):
  1. Desktop GPU full pipeline is documented end-to-end as the primary maker path
  2. Runtime profiles select model tiers/backends for desktop, Jetson-class, and CPU/lite
  3. ONNX and/or TensorRT export recipes exist with on-device engine build notes
  4. Headless mode serves perception API without the UI
  5. Stubs/scaffolds exist for ROS2 bridge, multi-cam schema tests, and voice plugin no-op
  6. Safety/privacy disclaimers and non-autonomy positioning are finalized in docs
**Plans**: 3 plans

Plans:
- [x] 07-01-PLAN.md — Runtime profiles + edge model tiers + headless mode (EDGE-02, EDGE-05)
- [x] 07-02-PLAN.md — ONNX/TensorRT export recipes + Jetson packaging notes (EDGE-03)
- [x] 07-03-PLAN.md — Extension stubs + desktop GPU docs + safety/privacy (EDGE-04, EDGE-01)

## Progress

**Execution Order:**  
1 → 2 → 3 → 4 → 5 → 6 → 7

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundations & Contracts | 3/3 | Complete   | 2026-08-07 |
| 2. Camera Ingest & Live Preview | 3/3 | Complete   | 2026-08-07 |
| 3. Fixed-Class Detection | 2/2 | Complete   | 2026-08-07 |
| 4. Monocular Depth | 2/2 | Complete   | 2026-08-08 |
| 5. Free-Space & Unified Stream | 3/3 | Complete   | 2026-08-08 |
| 6. Developer Controls & Open-Vocab | 2/2 | Complete   | 2026-08-08 |
| 7. Edge Profiles & Extension Stubs | 3/3 | Complete   | 2026-08-08 |

## Architecture Spine (reference)

```
Camera Sources → Frame Bus → Model Workers (depth || detection || open-vocab)
                      │              │
                      │              ▼
                      │       Spatial Post (free-space / obstacles)
                      │              │
                      ▼              ▼
               Perception State Store
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   Web Dev UI              Perception Stream API
   (overlays+controls)     (WS/REST → robots)
```

## Stack Snapshot (from research)

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file); PyAV/GStreamer for RTSP/CSI when needed |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE |
| Depth | Depth Anything V2 Small (Apache-2.0 default) |
| Free-space | NumPy/OpenCV postprocess |
| Frontend | Vite + React + TS; MJPEG/WS preview + canvas overlays |
| Edge | PyTorch → ONNX → TensorRT FP16 (NVIDIA); CPU/ORT fallback |

## Key Risks & Mitigations

| Risk | Mitigation | Primary phase |
|------|------------|---------------|
| Relative depth sold as meters | `depth_kind` in schema from Phase 1 | 1, 4 |
| UI FPS ≠ robot latency | Keep-latest bus; dual-rate workers; telemetry | 2, 5 |
| Desktop-only lock-in | Profile/backend abstraction early | 1, 7 |
| Naive free-space flicker | Temporal smoothing + extrinsics notes | 5 |
| FSD overclaim / safety misuse | Perception-only API; stale TTL; docs language | 5, 7 |
| License landmines | Default Apache-friendly weights; THIRD_PARTY docs | 1 |

## Out of Scope (v1 reminder)

- LiDAR/radar required sensors  
- Full SLAM / multi-cam fusion  
- Robot control / motion planning  
- Voice I/O and scene chat as primary UI  
- Mandatory cloud inference  

---
*Roadmap created: 2026-08-07 after research synthesis*  
*Granularity: standard (7 phases)*  
*Next: `/gsd:plan-phase 1`*
