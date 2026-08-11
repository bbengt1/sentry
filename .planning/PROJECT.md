# Sentry AI

## What This Is

Sentry AI is an open-source, camera-only perception stack for maker robotics — vision-based spatial awareness and object recognition without LiDAR or radar. It runs local open-source models, exposes a realtime Live Preview with overlays and developer controls, and ships a versioned perception stream (depth, detections, free-space / obstacles, optional open-vocab) that robots consume via REST/WebSocket. Multi-target runtime profiles (desktop GPU, Jetson-class, CPU/lite), headless API mode, and extension stubs (ROS2, multi-cam `camera_id`, voice no-op) are included for post-v1 growth.

## Core Value

Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

## Current State

**Shipped: v1.0 Camera-only perception MVP** (2026-08-09) + **v0.2 Edge Runtime** (2026-08-10)

### v1.0 (MVP)

- Installable `sentry-ai` / CLI `sentry` with one-command local start
- USB / file / synthetic / RTSP capture → keep-latest FrameBus → model workers
- Fixed-class YOLO26 + monocular DAV2 Small depth + free-space/obstacles
- Open-vocab YOLOE (default off); Live Preview + `/v1` perception stream
- Profiles: `desktop-gpu`, `jetson`, `cpu-fallback`; headless `--no-ui`

### v0.2 (Edge Runtime)

- **Live ONNX Runtime** fixed-class YOLO when preferred + allowlisted `.onnx` + `onnx` extra
- **Live TensorRT** fixed-class YOLO when preferred + on-device `.engine` + system/JetPack TensorRT
- Factory `build_detection_worker` with honest `backend_requested` / `backend_live` / `backend_reason`
- Soft-default sticky fallback + opt-in strict fail-closed (`fallback_to_torch` / `SENTRY_FALLBACK_TO_TORCH`)
- Depth + open-vocab remain PyTorch; dual-model measure-on-device docs
- Operator hub `docs/edge-serve.md`; AGPL lineage for derived ORT/TRT artifacts
- Jetson-free GitHub Actions + packaging hygiene
- ~9.3k LOC Python under `src/`; 10 plans across phases 8–12

**Audit at close:** passed (20/20 requirements) — see `milestones/v0.2-MILESTONE-AUDIT.md`.

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
- ✓ Live ONNX Runtime path for fixed-class YOLO (profile-selected) — v0.2
- ✓ Live TensorRT path for fixed-class YOLO on NVIDIA / Jetson-class — v0.2
- ✓ Profiles wire preferred_backend to real loaders (not advisory-only) — v0.2
- ✓ Honest sticky soft/strict fallback when ORT/TRT artifact/dep missing — v0.2
- ✓ Edge docs: export → onnx/engine → serve hub + Jetson packaging honesty — v0.2
- ✓ CI-safe tests without Jetson hardware; GHA Jetson-free locks — v0.2

### Active

- [ ] Metric depth calibration UX via Live Preview wizard (known heights / markers)
- [ ] Persist and re-apply per-camera (or per-profile) calibration at serve
- [ ] Honest `depth_kind` / unit labeling: relative by default; metric only when calibrated
- [ ] Free-space / obstacle near-field distances use metric scale when calibrated
- [ ] Clear uncalibrated honesty in UI, snapshot, and `/v1` (never label relative as meters)
- [ ] Docs for calibration flow; automated tests without physical hardware

### Out of Scope

- LiDAR / radar / ultrasonic as required sensors — camera-only product thesis
- Full robot control / motion planning — consumers own control
- Dense SLAM / full 3D mapping — depth + obstacles only in core product
- Multi-camera fusion (runtime) — single active source; schema hooks only *(revisit as Active if prioritized)*
- Cloud-only or proprietary model dependency — local OSS required
- Voice / scene chat as primary UI — stubs only in v1.0
- Commercial fleet SaaS / mandatory cloud camera upload
- FSD / autonomous vehicle claims — hobby monocular ≠ vehicle-grade
- Prebuilt multi-SKU TensorRT engines in the wheel/repo — on-device build only
- Continuous open-vocab + TRT + DAV2 as first-class dual-model claim

## Context

**Problem:** Maker robotics often depends on expensive depth sensors. There was no approachable OSS camera-only stack with off-the-shelf cameras, local models, interactive dev UI, and a clean robot API.

**Users:** Maker / hobbyist roboticists, students, small teams.

**Shipped stack:** Python 3.11, FastAPI, Pydantic 2, OpenCV capture (incl. Continuity uniqueID on macOS), Ultralytics YOLO26/YOLOE, HF Depth Anything V2 Small, static Live Preview, profile-driven serve with live torch/ORT/TRT fixed-class detection.

**Known residual tech debt (non-blocking):** Nyquist VALIDATION.md frontmatter hygiene; residual live-load honesty after construct claim; hardware ORT/TRT E2E is operator checklist (see v0.2 audit).

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
| Multi-target: desktop + edge profiles | Dev ergonomics + deploy path | ✓ Good — v1.0 recipes; **v0.2 live ORT/TRT** |
| Local OSS models only for core path | Offline, no vendor lock-in | ✓ Good — v1.0 |
| Extensible plugin architecture | Voice/ROS2/multi-cam without rewrite | ✓ Good — stubs shipped |
| Depth honesty via `depth_kind` | Never sell relative as meters | ✓ Good — v1.0 |
| CUDA request falls back to MPS/CPU | Maker machines without CUDA | ✓ Good — post-v1 fix included |
| Factory sole author of backend_live | Prevent status lies | ✓ Good — v0.2 |
| Live ORT via Ultralytics YOLO(*.onnx) | Match Detection contract without custom decoder | ✓ Good — v0.2 |
| Live TRT via system TensorRT (no pip pin) | JetPack reality; multi-SKU engines unsafe | ✓ Good — v0.2 |
| Soft-default sticky fallback + opt-in strict | Maker ergonomics vs fail-closed deploy | ✓ Good — v0.2 |
| Depth/OV stay torch this milestone | Dual-model VRAM + scope control | ✓ Good — v0.2 |

## Current Milestone: v0.3 Metric Depth Calibration UX

**Goal:** Makers can turn monocular relative depth into honest metric distances using a Live Preview calibration wizard based on known heights/markers — without claiming vehicle-grade accuracy.

**Target features:**
- Live Preview wizard for ground-truth scale (known object heights / floor markers)
- Apply / cancel with visual feedback on depth overlay and free-space
- Persist calibration (file or profile) and re-apply on `sentry serve`
- Wire calibrated scale into depth products with honest `depth_kind` / units
- Free-space near-field bands use meters when calibrated; stay honest when not
- Operator docs + CI-safe unit/integration tests (synthetic frames; no real room required)

**Out of this milestone (deferred):**
- Full camera intrinsic calibration suite (chessboard photogrammetry as primary path)
- Stereo / multi-view depth
- Live ORT/TRT for depth models
- ROS2 metric TF frames package
- Published dual-model FPS claims

---
*Last updated: 2026-08-11 after starting v0.3 milestone*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state
