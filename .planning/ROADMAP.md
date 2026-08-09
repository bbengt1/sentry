# Roadmap: Sentry AI

## Milestones

- ✅ **v1.0 Camera-only perception MVP** — Phases 1–7 (shipped 2026-08-09)
- 🚧 **v0.2 Edge Runtime** — Phases 8–12 (in progress)

## Phases

<details>
<summary>✅ v1.0 Camera-only perception MVP (Phases 1–7) — SHIPPED 2026-08-09</summary>

- [x] Phase 1: Foundations & Contracts (3/3 plans) — completed 2026-08-07
- [x] Phase 2: Camera Ingest & Live Preview (3/3 plans) — completed 2026-08-07
- [x] Phase 3: Fixed-Class Detection (2/2 plans) — completed 2026-08-07
- [x] Phase 4: Monocular Depth (2/2 plans) — completed 2026-08-08
- [x] Phase 5: Free-Space & Unified Stream (3/3 plans) — completed 2026-08-08
- [x] Phase 6: Developer Controls & Open-Vocab (2/2 plans) — completed 2026-08-08
- [x] Phase 7: Edge Profiles & Extension Stubs (3/3 plans) — completed 2026-08-08

Full phase detail: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)  
Requirements archive: [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)  
Audit: [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

</details>

### 🚧 v0.2 Edge Runtime (In Progress)

**Milestone Goal:** Fixed-class YOLO runs **live** on ONNX Runtime and TensorRT (profile-selected) on desktop and Jetson-class NVIDIA — not export recipes alone. Depth and open-vocab stay PyTorch. Perception spine (DetectionLoop / FrameBus / PerceptionStore / `/v1`) stays frozen.

- [x] **Phase 8: Backend Selection & Honesty** - Factory wires `preferred_backend` to real loaders; status shows requested vs live (completed 2026-08-09)
- [ ] **Phase 9: Live ORT Fixed-Class YOLO** - Profile-selected ONNX Runtime path produces schema-identical detections
- [ ] **Phase 10: Live TensorRT Fixed-Class YOLO** - On-device `.engine` path for Jetson/desktop NVIDIA
- [ ] **Phase 11: Sticky Fallback & Dual-Model Guardrails** - Documented sticky fail/fallback; depth/OV remain torch
- [ ] **Phase 12: Docs, CI & Packaging Polish** - Export→serve narrative, AGPL lineage, CI without Jetson

## Phase Details

### Phase 8: Backend Selection & Honesty
**Goal**: Operators and robots see honest backend identity; serve constructs the fixed-class detector via a factory driven by `preferred_backend`, with safe artifact path resolution — torch path still works end-to-end
**Depends on**: Phase 7 (v1.0 shipped profiles + export recipes)
**Requirements**: BACK-01, BACK-02, BACK-04, EDGE-RT-01, EDGE-RT-02, EDGE-RT-03
**Success Criteria** (what must be TRUE):
  1. `sentry serve` constructs the fixed-class detection worker through a factory from `profile_runtime` (not hard-coded torch-only construction)
  2. `preferred_backend` selects among torch / onnxruntime / tensorrt **loader branches** (torch branch fully live; ORT/TRT branches may still stub until later phases, but selection is real wiring)
  3. Status / serve banner expose both `backend_requested` and `backend_live` (and never claim ORT/TRT when torch is running)
  4. Artifact paths for `.onnx` / `.engine` resolve from config/env/cache with a safe allowlist (no path traversal)
  5. DetectionLoop / FrameBus / PerceptionStore / `/v1` remain the perception spine unchanged; desktop-gpu stays torch-default
**Plans**: 2 plans
**UI hint**: yes

Plans:
- [x] 08-01-PLAN.md — Factory + artifact resolution + profile wiring
- [x] 08-02-PLAN.md — Status/banner honesty (`backend_requested` / `backend_live`)

### Phase 9: Live ORT Fixed-Class YOLO
**Goal**: Makers can run fixed-class YOLO live via ONNX Runtime when the profile prefers `onnxruntime` and a valid `.onnx` artifact is present — same Detection wire contract as PyTorch
**Depends on**: Phase 8
**Requirements**: ORT-01, ORT-02, ORT-03, ORT-04
**Success Criteria** (what must be TRUE):
  1. With `preferred_backend=onnxruntime` and a valid `.onnx` artifact + optional `onnx` extra, fixed-class YOLO runs live (not torch-only under an ORT label)
  2. ORT path produces the same `Detection` wire contract (class, conf, bbox_xyxy, source=fixed) as the PyTorch path
  3. Optional `onnx` (or equivalent) extra is documented for install; CI does not require GPU ORT
  4. Golden/parity tests (mock session or fixture) prove postprocess mapping without Jetson hardware
**Plans**: 2 plans

Plans:
- [ ] 09-01-PLAN.md — Live Ultralytics-native ORT worker path + `onnx` extra
- [ ] 09-02-PLAN.md — Detection parity / golden tests (CPU ORT or mocks)

### Phase 10: Live TensorRT Fixed-Class YOLO
**Goal**: Jetson-class and NVIDIA desktop can run fixed-class YOLO live via TensorRT from an on-device `.engine` — no multi-SKU engines in the wheel, no pip `tensorrt` app dependency
**Depends on**: Phase 8 (factory + honesty); Phase 9 (Detection contract proven on edge path)
**Requirements**: TRT-01, TRT-02, TRT-03, TRT-04
**Success Criteria** (what must be TRUE):
  1. With `preferred_backend=tensorrt` and a valid on-device `.engine`, fixed-class YOLO runs live via system/JetPack TensorRT
  2. Docs require **on-device** engine build; project does not ship multi-SKU prebuilt engines in the wheel/repo
  3. Jetson-class packaging notes cover JetPack/system TensorRT (no generic `tensorrt` pip pin as required app dep)
  4. TRT path maps results into the same `Detection` contract; conf remains adjustable at runtime when supported
**Plans**: 2 plans

Plans:
- [ ] 10-01: Live Ultralytics-native TRT worker path (system TensorRT)
- [ ] 10-02: On-device engine lifecycle + Jetson packaging notes

### Phase 11: Sticky Fallback & Dual-Model Guardrails
**Goal**: Missing ORT/TRT artifacts or deps never thrash or silently lie; depth and open-vocab stay on existing PyTorch paths this milestone
**Depends on**: Phase 9, Phase 10
**Requirements**: BACK-03, EDGE-RT-04
**Success Criteria** (what must be TRUE):
  1. When preferred ORT/TRT artifact or dependency is missing, behavior is documented and sticky (fail-closed or explicit torch fallback with reason logged once — never thrash every frame)
  2. Soft vs strict fallback modes are documented; live backend + reason remain visible when they differ from requested
  3. Depth and open-vocab continue on existing PyTorch paths (no live ORT/TRT for those stages this milestone)
  4. Dual-model guidance exists for TRT YOLO + torch depth (no continuous open-vocab + TRT+DAV2 as a first-class claim)
**Plans**: 2 plans

Plans:
- [ ] 11-01: Sticky resolve + soft/strict fallback policy
- [ ] 11-02: Dual-model scope lock (depth/OV torch) + operator status surface

### Phase 12: Docs, CI & Packaging Polish
**Goal**: Makers can follow export → engine/onnx → `sentry serve` on desktop/Jetson without fake FPS claims; contributors merge safely without Jetson hardware
**Depends on**: Phase 11
**Requirements**: EDGE-DOC-01, EDGE-DOC-02, EDGE-CI-01, EDGE-CI-02
**Success Criteria** (what must be TRUE):
  1. Jetson/desktop edge serve docs cover export → engine/onnx → `sentry serve --profile …` (with or without UI)
  2. AGPL Ultralytics remains documented for ORT/TRT artifacts derived from YOLO weights (`THIRD_PARTY_MODELS` lineage)
  3. Unit tests cover backend selection, missing-artifact honesty, and factory wiring without NVIDIA Jetson in CI
  4. Default GitHub Actions does not require Jetson or TensorRT GPU
**Plans**: 2 plans

Plans:
- [ ] 12-01: Edge serve docs + AGPL/export lineage refresh
- [ ] 12-02: CI selection/fallback matrix hardening (no Jetson in GHA)

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1. Foundations & Contracts | v1.0 | 3/3 | Complete | 2026-08-07 |
| 2. Camera Ingest & Live Preview | v1.0 | 3/3 | Complete | 2026-08-07 |
| 3. Fixed-Class Detection | v1.0 | 2/2 | Complete | 2026-08-07 |
| 4. Monocular Depth | v1.0 | 2/2 | Complete | 2026-08-08 |
| 5. Free-Space & Unified Stream | v1.0 | 3/3 | Complete | 2026-08-08 |
| 6. Developer Controls & Open-Vocab | v1.0 | 2/2 | Complete | 2026-08-08 |
| 7. Edge Profiles & Extension Stubs | v1.0 | 3/3 | Complete | 2026-08-08 |
| 8. Backend Selection & Honesty | v0.2 | 2/2 | Complete   | 2026-08-09 |
| 9. Live ORT Fixed-Class YOLO | v0.2 | 0/2 | Not started | - |
| 10. Live TensorRT Fixed-Class YOLO | v0.2 | 0/2 | Not started | - |
| 11. Sticky Fallback & Dual-Model Guardrails | v0.2 | 0/2 | Not started | - |
| 12. Docs, CI & Packaging Polish | v0.2 | 0/2 | Not started | - |

## Coverage Map (v0.2)

| Requirement | Phase |
|-------------|-------|
| BACK-01 | 8 |
| BACK-02 | 8 |
| BACK-03 | 11 |
| BACK-04 | 8 |
| ORT-01 | 9 |
| ORT-02 | 9 |
| ORT-03 | 9 |
| ORT-04 | 9 |
| TRT-01 | 10 |
| TRT-02 | 10 |
| TRT-03 | 10 |
| TRT-04 | 10 |
| EDGE-RT-01 | 8 |
| EDGE-RT-02 | 8 |
| EDGE-RT-03 | 8 |
| EDGE-RT-04 | 11 |
| EDGE-DOC-01 | 12 |
| EDGE-DOC-02 | 12 |
| EDGE-CI-01 | 12 |
| EDGE-CI-02 | 12 |

**Coverage:** 20/20 v0.2 requirements mapped ✓

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

**v0.2 plug-in point:** `build_detection_worker(profile_runtime)` at serve construction — torch / ORT / TRT loaders only for fixed-class YOLO. DetectionLoop, FrameBus, PerceptionStore, `/v1` frozen.

## Stack Snapshot

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file/RTSP); synthetic for tests |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE |
| Depth | Depth Anything V2 Small (Apache-2.0 default) |
| Free-space | NumPy/OpenCV postprocess |
| Frontend | Static Live Preview (MJPEG + controls) |
| Edge (v0.2 target) | Live ORT + live TRT for fixed-class YOLO; depth/OV stay PyTorch |

## Out of Scope (product thesis + v0.2 lock)

- LiDAR/radar required sensors  
- Full SLAM / multi-cam fusion  
- Robot control / motion planning  
- Voice I/O and scene chat as primary UI  
- Mandatory cloud inference  
- Live ORT/TRT for depth or open-vocab (v0.2)  
- Prebuilt multi-SKU `.engine` in wheel/repo  
- Production ROS2 package / OpenVINO first-class  

---
*v0.2 roadmap created 2026-08-09 — phases 8–12*
