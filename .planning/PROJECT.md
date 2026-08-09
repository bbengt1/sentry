# Sentry AI

## What This Is

Sentry AI is an open-source, camera-only perception stack for maker robotics — vision-based spatial awareness and object recognition without LiDAR or radar. It runs local open-source models, exposes a realtime Live Preview with overlays and developer controls, and ships a versioned perception stream (depth, detections, free-space / obstacles, optional open-vocab) that robots consume via REST/WebSocket. Multi-target runtime profiles (desktop GPU, Jetson-class, CPU/lite), headless API mode, and extension stubs (ROS2, multi-cam `camera_id`, voice no-op) are included for post-v1 growth.

## Core Value

Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

## Current State

**Shipped: v1.0 Camera-only perception MVP** (2026-08-09)

- Installable `sentry-ai` / CLI `sentry` with one-command local start
- USB / file / synthetic / RTSP capture → keep-latest FrameBus → model workers
- Fixed-class YOLO26 + monocular DAV2 Small depth + free-space/obstacles
- Open-vocab YOLOE (on-demand / lower rate; default off)
- Live Preview (MJPEG overlays + stage toggles + thresholds + telemetry)
- `/v1/snapshot` + `/v1/stream` PerceptionFrame contract; perception-only boundary
- Profiles: `desktop-gpu`, `jetson`, `cpu-fallback`; `sentry serve --no-ui`
- Export recipes (ONNX/TensorRT docs + scripts); safety/privacy docs
- ~7.4k LOC Python under `src/`; 18 plans across 7 phases

**Audit at close:** tech_debt (46/46 requirements; residual operator UAT on phases 2–4) — see `milestones/v1.0-MILESTONE-AUDIT.md`.

## Requirements

### Validated

- ✓ Camera-only spatial awareness (monocular depth + free-space/obstacles) — v1.0
- ✓ Off-the-shelf cameras (USB, network/IP, file, synthetic) — v1.0
- ✓ Local development workflow with live camera or synthetic sources — v1.0
- ✓ Realtime web Live Preview with video + overlays — v1.0
- ✓ Interactive developer controls (stages, thresholds, telemetry) — v1.0
- ✓ Local open-source models only on the core path — v1.0
- ✓ Fixed-class detection + optional open-vocabulary queries — v1.0
- ✓ Perception stream API for robots (no motor commands) — v1.0
- ✓ Single-camera pipeline with multi-cam `camera_id` extension hooks — v1.0
- ✓ Multi-target runtime: desktop GPU + Jetson/CPU profiles + export recipes — v1.0
- ✓ Extensible architecture stubs (ROS2 bridge, voice no-op, plugins) — v1.0

### Active

- [ ] Live ONNX Runtime path for fixed-class YOLO (profile-selected)
- [ ] Live TensorRT path for fixed-class YOLO on NVIDIA / Jetson-class
- [ ] Profiles wire preferred_backend to real loaders (not advisory-only)
- [ ] Honest fallback when ORT/TRT engine/model missing (clear error or torch fallback)
- [ ] Edge docs: Jetson on-device engine build + serve with tensorrt/onnxruntime profiles
- [ ] CI-safe tests without Jetson hardware

### Out of Scope

- LiDAR / radar / ultrasonic as required sensors — camera-only product thesis
- Full robot control / motion planning — consumers own control
- Dense SLAM / full 3D mapping — depth + obstacles only in core product
- Multi-camera fusion (runtime) — single active source; schema hooks only
- Cloud-only or proprietary model dependency — local OSS required
- Voice / scene chat as primary UI — stubs only in v1.0
- Commercial fleet SaaS / mandatory cloud camera upload
- FSD / autonomous vehicle claims — hobby monocular ≠ vehicle-grade

## Context

**Problem:** Maker robotics often depends on expensive depth sensors. There was no approachable OSS camera-only stack with off-the-shelf cameras, local models, interactive dev UI, and a clean robot API.

**Users:** Maker / hobbyist roboticists, students, small teams.

**Shipped stack:** Python 3.11, FastAPI, Pydantic 2, OpenCV capture, Ultralytics YOLO26/YOLOE, HF Depth Anything V2 Small, static Live Preview, profile-driven serve.

**Known residual tech debt (non-blocking):** optional human UAT (USB/browser/real weights); free-space product after depth disable; `/v1` bus metrics parity; YOLOE not in plugin registry; Nyquist VALIDATION.md flags.

## Constraints

- **Sensors**: Cameras only for spatial awareness — no LiDAR/radar requirement
- **Models**: Local open-source models required; cloud optional only as non-default extension
- **Cameras**: USB UVC, RTSP/network, file/synthetic
- **Runtime**: Multi-target — desktop GPU primary path; Jetson/CPU profiles + export recipes
- **Interface**: Web Live Preview for developers; headless API for robots
- **Architecture**: Plugin / extension-friendly
- **License**: Apache-2.0 application code; third-party model licenses documented
- **Privacy**: On-device default; localhost bind; no mandatory upload

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Camera-only perception (no LiDAR/radar) | Core product thesis | ✓ Good — v1.0 |
| Spatial v1 = depth + obstacles, not full SLAM | Ship useful signal without mapping complexity | ✓ Good — v1.0 |
| Single camera first | v1 complexity; multi-cam hooks only | ✓ Good — v1.0 |
| Static Live Preview (not full React rewrite) | Ship overlays/controls faster | ✓ Good — v1.0 |
| Live overlays + controls (not chat-first) | Developer tooling first | ✓ Good — v1.0 |
| Fixed-class + open-vocab detection | Reliability + flexible queries | ✓ Good — v1.0 |
| Perception stream only (no robot control) | Clean safety boundary | ✓ Good — v1.0 |
| Multi-target: desktop + edge profiles | Dev ergonomics + deploy path | ✓ Good — v1.0 (live TRT deferred; recipes only) |
| Local OSS models only for core path | Offline, no vendor lock-in | ✓ Good — v1.0 |
| Extensible plugin architecture | Voice/ROS2/multi-cam without rewrite | ✓ Good — stubs shipped |
| Depth honesty via `depth_kind` | Never sell relative as meters | ✓ Good — v1.0 |
| CUDA request falls back to MPS/CPU | Maker machines without CUDA | ✓ Good — post-v1 fix included |

## Current Milestone: v0.2 Edge Runtime

**Goal:** Make Jetson/desktop edge deployment run **live** detection on real backends (ONNX Runtime + TensorRT), not export recipes alone — while keeping PyTorch as the default desktop path.

**Target features:**
- Live **ONNX Runtime** inference path for fixed-class YOLO (profile-selected)
- Live **TensorRT** inference path for fixed-class YOLO on NVIDIA (desktop/Jetson), on-device engines
- Backend selection via existing profiles (`preferred_backend` / device policy) with honest fallbacks
- Jetson-class first-class packaging notes + measured path (no fake FPS guarantees)
- Depth stays **PyTorch/HF** this milestone (YOLO fixed-class edge only)
- Open-vocab remains PyTorch/on-demand (not edge live dual-model)
- CI: mock ORT/TRT paths; no Jetson required in GitHub Actions
- Keep perception-only, localhost default, CUDA→MPS/CPU fallback honesty

**Out of this milestone (deferred):**
- Metric depth calibration UX  
- Production ROS2 package  
- Multi-cam fusion  
- Live ORT/TRT for depth / YOLOE  
- Pi-class published dual-model FPS as first-class claim  

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-09 — started milestone v0.2 Edge Runtime*
