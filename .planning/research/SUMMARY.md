# Research Summary: Sentry AI

**Date:** 2026-08-07  
**Domain:** Camera-only (vision-only) robotics perception for open-source maker tools  
**Confidence:** HIGH

## Executive Summary

Sentry AI is a **product-shaped, camera-only perception layer** for maker robots: commodity USB/IP cameras in, monocular depth + free-space/obstacles + object detections out, via a local OSS pipeline with a realtime web developer console and a clean robot-facing stream API. Experts in this space (DepthAI pipelines, Isaac ROS DNN graphs, Ultralytics multi-source predict, Nav2 costmap consumers) converge on the same shape — a **directed stage pipeline** with typed messages, latest-frame drop policy, UI as subscriber not control loop, and a hard boundary that **perception never owns motion control**.

**Recommended approach:** Python 3.11 + FastAPI single process hosting a Frame Bus and plugin workers (YOLO26 fixed-class, YOLOE open-vocab, Depth Anything V2 Small depth), Spatial Post for free-space, Vite/React overlays, WebSocket/REST `/v1` perception stream. Develop on desktop GPU (PyTorch); export ONNX → TensorRT for Jetson; degrade gracefully on Pi-class. Ship **relative depth honestly labeled**, metric as optional/calibrated mode; free-space as simple occupancy/obstacles — not SLAM, not Nav2, not FSD.

**Key risks:** (1) calling relative depth “meters,” (2) UI FPS ≠ robot latency, (3) desktop-only pipeline that cannot reach Jetson/Pi, (4) naive free-space thresholds without extrinsics/temporal logic, (5) FSD branding that overpromises autonomy. Mitigate with explicit depth typing in the API schema, dual-rate latest-frame pipeline, runtime profiles from day one, Spatial Post as the sole free-space semantic owner, and perception-only product language.

---

## Recommended Stack

Condensed from [STACK.md](./STACK.md). Full versions and install notes live there.

| Layer | Choice | Rationale |
|-------|--------|-----------|
| Language | **Python 3.11** | CV/ML + async web in one process; Jetson/Pi wheels mature |
| API | **FastAPI 0.141 + Uvicorn + Pydantic 2** | REST controls + WebSocket stream; OpenAPI free |
| Capture | **OpenCV headless** first; **PyAV/GStreamer** when RTSP/CSI hurts | Maker DX first; reliability upgrade path |
| Fixed detect | **YOLO26** (`s` desktop / `n` edge) via **Ultralytics 8.4.x** | Current flagship; NMS-free; strong Jetson TRT path |
| Open-vocab | **YOLOE** (YOLO-World fallback) | Realtime open-vocab; not Grounding DINO on live path |
| Depth | **Depth Anything V2 Small** (+ metric indoor/outdoor heads) | SOTA open monocular; Small is realtime-capable |
| Free-space | **NumPy/OpenCV** postprocess (threshold / ground plane / morphology) | No second dense occupancy net in v1 |
| Backends | Dev **PyTorch** → portable **ONNX** → NVIDIA **TensorRT FP16** | Multi-target without rewrite |
| Frontend | **Vite + React 19 + TS**; MJPEG/WS JPEG preview; canvas overlays | Localhost dashboard; WebRTC later if lag hurts |
| Packaging | `uv` + `pyproject.toml`; JetPack-matched on Jetson | Pin locks; engines built **on device** |

**Opinionated defaults:** single process; device-abstracted backends; commercially friendly default weights (DAV2 Small is Apache-2.0; Base/Large are CC-BY-NC — do not default to NC weights); Ultralytics AGPL documented for commercial forks.

**Do not use as core:** cloud CV APIs, MediaPipe as perception spine, Detectron2/MMDetection runtime, Kafka/Redis bus, Electron shell, required ROS2, LiDAR SDKs.

---

## Product Scope

Condensed from [FEATURES.md](./FEATURES.md).

### v1 table stakes (must ship)

| Feature | Notes |
|---------|-------|
| Commodity camera ingest | USB UVC + file/synthetic P0; RTSP P1 |
| Monocular depth map stream | Relative OK if labeled; metric optional |
| Free-space / obstacle regions | From depth — not full costmaps/SLAM |
| Fixed-class object detection | COCO-class YOLO26; conf + class filters |
| Live web overlays | RGB + boxes + depth colormap + free-space |
| Interactive controls | Thresholds, stage toggles, depth cutoffs |
| Perception stream API | Depth + detections + free-space; `frame_id` + timestamps |
| Local OSS inference | Offline after model cache; no mandatory cloud |
| FPS / stage latency telemetry | UI + API metadata |
| Graceful camera failure | Reconnect; clear error states |

**Quality bar:** overlay parity with API (single truth); coordinate honesty; safe defaults.

### v1 differentiators (product story)

1. **Any camera first** — not OAK/RealSense/ZED lock-in  
2. **Integrated depth + free-space + detection product** — composed pipeline, not glue-your-own  
3. **Realtime interactive web developer console** — controls, not passive viz  
4. **Schema-stable robot API** (`/v1`, completeness flags) — HTTP/WS before ROS2  
5. **Fixed-class + open-vocab together** — open-vocab is P1, not P0 blocker  
6. **Desktop + edge path** — model tiers and backend abstraction from day one  
7. **Honest monocular limits** — relative vs metric, known failure modes in-product  

### Deferred (post-v1 / never as core)

| Later | Never as core |
|-------|----------------|
| Jetson TensorRT / Pi lite packs (after desktop correctness) | Required LiDAR/radar/ultrasonic |
| Metric depth + scale calibration helpers | Full SLAM / dense mapping (v1) |
| Optional stereo / RealSense-as-source adapters | Robot control / motion planning |
| ROS2 bridge package | Multi-camera fusion (v1) |
| Multi-cam, lightweight occupancy history | Mandatory cloud inference |
| Scene chat / VLM, voice I/O | Fleet SaaS / FSD product claims |
| Segmentation / pose plugins | Training/labeling platform |

---

## Architecture Blueprint

Condensed from [ARCHITECTURE.md](./ARCHITECTURE.md).

### Components

```
Camera Sources → Frame Bus → Model Workers (depth || detection || open-vocab)
                      │              │
                      │              ▼
                      │       Spatial Post (free-space / obstacles)
                      │              │
                      ▼              ▼
               Perception State Store (latest + short ring)
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   Web Dev UI              Perception Stream API
   (overlays+controls)     (WS/REST → robots)
```

| Component | Owns | Does not own |
|-----------|------|--------------|
| **Camera Source** | USB/RTSP/file/synthetic capture | Models, UI |
| **Frame Bus** | `frame_id`, timestamps, keep-latest drop | Inference |
| **Depth / Detection Workers** | Model outputs per frame | Free-space semantics, UI |
| **Spatial Post** | Free-space masks, obstacle cues | Path planning |
| **State Store** | Merged `PerceptionFrame` + completeness | Persistence DB (v1) |
| **Stream API** | `/v1` wire protocol | Motor commands |
| **Web UI** | Presentation + config RPC | Hot-path inference |
| **Plugin Registry** | Sources/models/sinks entry points | Business logic |

**Hard rules:** sources → bus only; workers never open cameras; UI/robots read State only; Spatial Post is sole free-space definition; UI overlays derive from the same `PerceptionFrame` robots see.

### Data flow

- **Hot path:** Frame → parallel workers → Spatial Post → State merge (same-frame timeout) → WS/REST + UI  
- **Cold path:** UI/REST config → Control plane → workers reconfigure next frames  
- **Queue policy:** keep-latest depth 1 everywhere that matters; count drops; never unbounded capture queues  
- **Async rates OK:** e.g. det 15 Hz, depth 8 Hz with completeness flags  

### Schema direction

```text
PerceptionFrame {
  frame_id, camera_id, timestamps,
  completeness: {depth, detections, free_space},
  depth?: {kind: relative|metric, unit?, data},
  detections?: [...],
  free_space?: {obstacles, masks?},
  stats: {fps, latency, dropped_frames}
}
```

### Build order (dependency-driven)

1. Schemas + plugin stubs + config  
2. Camera ingest + Frame Bus  
3. API shell + live preview  
4. Fixed-class detection worker + overlays  
5. Depth worker + colormap stream  
6. Free-space / obstacles (Spatial Post)  
7. Unified perception stream polish  
8. Developer controls polish  
9. Open-vocab path  
10. Edge packaging  
11. Extension stubs (ROS2, multi-cam `camera_id`, voice no-op)  

**Why detection before depth:** faster validate worker pattern. **Why free-space after depth:** free-space consumes depth. **Why edge late but not last:** abstract `device` from phase 2 — do not hardcode desktop CUDA.

---

## Critical Pitfalls to Design Around

Top risks from [PITFALLS.md](./PITFALLS.md) — bake into phase plans, not docs-only.

1. **Relative depth sold as meters** — Type API as `relative | metric_estimated | metric_calibrated`; never name relative fields `depth_m`; indoor vs outdoor metric heads are different weights.  
2. **Demo FPS ≠ control-loop latency** — Separate preview path from robot stream; instrument capture→infer→emit age; latest-frame drop; dual-rate heavy models.  
3. **Desktop-only trap** — Runtime profiles (`desktop-gpu`, `jetson`, `cpu-fallback`); export path before locking models; TensorRT engines built on target SKU.  
4. **Naive free-space thresholds** — Extrinsics (height/pitch), temporal smoothing, obstacle likelihood over flickering binary masks; document glass/textureless failures.  
5. **FSD overclaim + safety misuse** — Perception stream only; no “safe to proceed”; stale-data TTL; localhost-first UI; e-stop is consumer’s job.  
6. **License landmines** — Default DAV2 **Small** (Apache-2.0); mark NC weights as research-only; document Ultralytics AGPL; `THIRD_PARTY_MODELS.md`.  
7. **Camera chaos** — Intrinsics/extrinsics profiles; support matrix; RTSP latency class honesty; `camera_id` from day one.  

**Highest-cost if deferred:** freezing a fake-metric API; UI-coupled pipeline; non-commercial default weights; free-space without temporal/extrinsics logic; autonomy branding.

---

## Implications for Requirements

Aligns with and refines [PROJECT.md](../PROJECT.md) Active requirements:

| Keep / refine | Decision |
|---------------|----------|
| Camera-only depth + free-space | **Keep.** v1 free-space = simple occupancy/obstacles from depth, not Nav2-grade costmaps. |
| USB / network / file sources | **Keep.** USB + file P0; RTSP P1. |
| Local OSS models | **Keep.** Offline after cache; no cloud-required path. |
| Web overlays + interactive controls | **Keep.** Developer-first, not chat-first. |
| Fixed-class + open-vocab | **Keep.** Fixed-class P0; open-vocab P1 (not MVP blocker). |
| Perception stream API | **Keep.** HTTP/WebSocket first; ROS2 later plugin. |
| Single-cam + extension points | **Keep.** `camera_id` in schemas from day one; no fusion in v1. |
| Desktop + edge multi-target | **Keep.** Profiles + backend abstraction early; full Jetson pack after correctness. |
| Extensibility (voice, multi-cam, ROS2) | **Keep as stubs only** in v1. |

**Clarify in requirements language:**

1. **Depth contract:** relative monocular is acceptable for v1; metric is optional/experimental with explicit `depth_kind` labeling.  
2. **Free-space contract:** image-plane / coarse occupancy from depth — not metric LiDAR-grade without calibration metadata.  
3. **Boundary:** Sentry never sends velocity/commands; consumers own control and e-stop.  
4. **Do not expand v1** into SLAM, multi-cam fusion, voice, cloud-mandatory, or control stack.  

---

## Implications for Roadmap Phases

Suggested **7 phases** at standard granularity. Order follows architecture build order + feature critical path + pitfall prevention.

### Phase 1: Foundations & Contracts
**Goal:** Repo skeleton, shared schemas, plugin registry stubs, config schema, license-aware model policy.  
**Delivers:** `Frame` / `PerceptionFrame` types, `camera_id` + timestamps, depth_kind enum, `THIRD_PARTY_MODELS.md` stub, device-abstract backend protocols, CI smoke with synthetic frames.  
**Features:** Schema-stable API foundation; extensibility hooks (stubs).  
**Avoids:** Ad-hoc dicts; non-commercial default weights; process-global “the frame.”  
**Research flag:** Standard patterns — skip deep research.

### Phase 2: Camera Ingest + Frame Bus + Preview
**Goal:** Realtime capture loop without models; prove “camera works.”  
**Delivers:** USB + file + synthetic sources; keep-latest Frame Bus; drop metrics; FastAPI health + WS/MJPEG preview; minimal web page.  
**Features:** Commodity camera ingest; graceful failure handling; one-command local start path.  
**Avoids:** Models bound to OpenCV capture; unbounded queues; `0.0.0.0` default bind.  
**Research flag:** Light research if RTSP/GStreamer reliability bites; OpenCV path is standard.

### Phase 3: Fixed-Class Detection
**Goal:** First robot-usable signal + worker pattern.  
**Delivers:** YOLO26 detection worker; boxes on UI; detections in stream JSON; conf threshold control; FPS telemetry.  
**Features:** Fixed-class detection; live detection overlays; partial stream API.  
**Avoids:** Open-vocab as primary; UI-only detection path.  
**Research flag:** Standard (Ultralytics predict well documented).

### Phase 4: Monocular Depth
**Goal:** Spatial awareness primitive with honest semantics.  
**Delivers:** Depth Anything V2 Small worker; depth colormap UI; depth in stream with `depth_kind`; optional metric indoor/outdoor mode labeled; preprocess golden tests.  
**Features:** Monocular depth map stream; local OSS depth path.  
**Avoids:** Silent “meters” on relative models; letterbox pollution; preprocess mismatch.  
**Research flag:** **Needs research** — model size vs FPS on desktop; metric head selection; export path spike.

### Phase 5: Free-Space / Obstacles + Unified Stream
**Goal:** Core product thesis: actionable occupancy robots can consume.  
**Delivers:** Spatial Post (threshold/bands + optional ground prior); obstacle list; free-space overlay; merged `PerceptionFrame` with completeness; REST snapshot + WS `/v1/stream` docs; stale/TTL contract.  
**Features:** Free-space/obstacles; machine-readable perception API; frame identity quality bar.  
**Avoids:** Naive binary thresholds only; SLAM scope creep; “safe to proceed” language.  
**Research flag:** **Needs research** — free-space algorithm spike (near-field vs ground-plane vs BEV strip); binary WS vs PNG16 depth encoding.

### Phase 6: Developer Controls + Open-Vocab
**Goal:** Interactive console differentiator + flexible detection.  
**Delivers:** Full control plane (thresholds, stage toggles, source switch, rates); open-vocab worker (on-demand / lower rate); schema versioning polish; known-failure docs in UI.  
**Features:** Interactive controls; open-vocabulary detection; model toggle / A-B inspection.  
**Avoids:** Restart-to-tune; always-on heavy open-vocab on edge; chat/VLM as primary UI.  
**Research flag:** Medium — YOLOE export/edge maturity; prompt UX.

### Phase 7: Edge Profiles + Extension Stubs
**Goal:** Multi-target claim real; future-proof without rewrite.  
**Delivers:** `desktop` / `jetson` / `cpu` profiles; YOLO26n + DAV2-Small edge path; ONNX/TensorRT export recipes; headless mode; ROS2 bridge scaffold; multi-cam schema tests; voice plugin no-op; safety/privacy disclaimers finalized.  
**Features:** Multi-target runtime; plugin extension points; optional ROS2 later path.  
**Avoids:** Copying TRT engines across SKUs; claiming Pi full-pipeline realtime without honest FPS; building full ROS2/voice products.  
**Research flag:** **Needs research** — Jetson shared-GPU scheduling; JetPack matrix; sustained thermal FPS.

### Phase ordering rationale

```
Schemas → Bus → Preview → Detection → Depth → Free-space → Unified API
                                                              ↓
                                                    Controls + Open-vocab
                                                              ↓
                                                         Edge + stubs
```

- **Dependencies:** free-space needs depth; unified stream needs ≥2 products; controls need something to control; edge needs stable models.  
- **Demo value:** each phase is a vertical slice makers can run.  
- **Pitfall timing:** depth typing and licenses in Phase 1; latency architecture in Phase 2; free-space quality in Phase 5; edge rewrite risk deferred only after abstraction exists.

### Research flags summary

| Needs `/gsd:plan-phase` research | Standard patterns (skip) |
|----------------------------------|---------------------------|
| Phase 4 (depth model + metric) | Phase 1 (foundations) |
| Phase 5 (free-space algorithm + stream encoding) | Phase 2 (capture/bus — mostly) |
| Phase 7 (Jetson/Pi packaging) | Phase 3 (YOLO detection) |
| Phase 6 partial (YOLOE edge export) | — |

---

## Open Questions Remaining

Resolved only by phase spikes, not blockers for roadmap:

1. **Free-space v1 algorithm:** near-field depth threshold vs ground-plane RANSAC vs bird’s-eye occupancy strip — which is good enough for reactive avoidance?  
2. **Depth model runtime pick:** DAV2 Small relative-only first vs ship metric indoor head immediately; desktop + Jetson FPS budgets.  
3. **Open-vocab schedule:** always-on YOLOE vs on-demand query mode (prefer on-demand on edge).  
4. **Stream transport:** WebSocket JSON + PNG16/JPEG vs binary msgpack/protobuf for robot clients.  
5. **Edge floor:** minimum Jetson class for “full pipeline” first-class claim; Pi messaging as “spatial awareness lite.”  
6. **Calibration UX depth:** how much intrinsics/extrinsics onboarding is required before metric free-space is offered?  
7. **Shared GPU scheduling:** depth vs detection priority when both GPU-bound on Jetson (measure, don’t theorize).

---

## Confidence & Gaps

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Versions verified PyPI 2026-08-07; Ultralytics YOLO26/YOLOE + DAV2 well documented |
| Features | **HIGH** | Gap analysis vs OAK/RealSense/ZED/YOLO/Nav2/Foxglove; aligns with PROJECT.md |
| Architecture | **HIGH** topology; **MEDIUM** free-space algorithm & process-vs-thread on Pi | DepthAI/Isaac ROS patterns strong; free-space needs spike |
| Pitfalls | **HIGH** geometry/latency; **MEDIUM** product/legal edge cases | Metric scale, latency, licenses are well-sourced |

**Overall confidence:** **HIGH** for roadmap structure and stack direction.

### Gaps to address during planning

| Gap | Handle during |
|-----|----------------|
| Exact free-space derivation | Phase 5 research spike |
| Shared-GPU Jetson scheduling | Phase 7 measurement |
| Binary WS framing details | Phase 5 stream polish |
| YOLOE TensorRT export maturity | Phase 6; keep PyTorch/ONNX fallback |
| Pi sustained dual-model FPS | Phase 7; honest “lite” profile |
| LAN auth model | When leaving localhost (Phase 2 defaults + Phase 7 remote UI) |
| Exact CUDA index (`cu128` etc.) | Re-check pytorch.org at install time |
| Ultralytics AGPL commercial plan | Document for contributors; not a v1 OSS blocker |

---

## Sources

### Primary (HIGH)

- [Ultralytics YOLO26 / YOLOE / Export / Jetson guide](https://docs.ultralytics.com/) — detection, open-vocab, TRT, multi-source  
- [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) + [metric fine-tunes](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth) — depth + licenses + indoor/outdoor  
- [Isaac ROS DNN Inference](https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_dnn_inference/index.html) — encode/infer/decode multi-target  
- [DepthAI pipeline docs](https://docs.luxonis.com/) — node/message pipeline model  
- [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) — stream API pattern  
- [Nav2 concepts](https://docs.nav2.org/concepts/index.html) — free-space consumer expectations  
- [Metric3D](https://github.com/YvanYin/Metric3D) — intrinsics / point-cloud distortion  
- [OpenCV camera calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)  
- Sentry [PROJECT.md](../PROJECT.md) — product constraints  

### Secondary (MEDIUM)

- Foxglove / Rerun viz patterns — UI as subscriber  
- ROS 2 composition — extension path, not v1 core  
- Autoware perception package layout — modular workers  
- ZoeDepth (archived) — metric lineage context only  

### Research artifacts

- [STACK.md](./STACK.md)  
- [FEATURES.md](./FEATURES.md)  
- [ARCHITECTURE.md](./ARCHITECTURE.md)  
- [PITFALLS.md](./PITFALLS.md)  

---

*Research completed: 2026-08-07*  
*Ready for roadmap: yes*
