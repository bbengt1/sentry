# Roadmap: Sentry AI

## Milestones

- ✅ **v1.0 Camera-only perception MVP** — Phases 1–7 (shipped 2026-08-09)
- ✅ **v0.2 Edge Runtime** — Phases 8–12 (shipped 2026-08-10)
- 📋 **Next milestone** — not started (`/gsd:new-milestone`)

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

<details>
<summary>✅ v0.2 Edge Runtime (Phases 8–12) — SHIPPED 2026-08-10</summary>

- [x] Phase 8: Backend Selection & Honesty (2/2 plans) — completed 2026-08-09
- [x] Phase 9: Live ORT Fixed-Class YOLO (2/2 plans) — completed 2026-08-09
- [x] Phase 10: Live TensorRT Fixed-Class YOLO (2/2 plans) — completed 2026-08-10
- [x] Phase 11: Sticky Fallback & Dual-Model Guardrails (2/2 plans) — completed 2026-08-10
- [x] Phase 12: Docs, CI & Packaging Polish (2/2 plans) — completed 2026-08-10

Full phase detail: [milestones/v0.2-ROADMAP.md](milestones/v0.2-ROADMAP.md)  
Requirements archive: [milestones/v0.2-REQUIREMENTS.md](milestones/v0.2-REQUIREMENTS.md)  
Audit: [milestones/v0.2-MILESTONE-AUDIT.md](milestones/v0.2-MILESTONE-AUDIT.md)

</details>

### 📋 Next milestone (not started)

Define scope with `/gsd:new-milestone` (questioning → research → requirements → roadmap).  
Continue phase numbering from **13** (never restart at 01).

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1–7 | v1.0 | 18/18 | Complete | 2026-08-09 |
| 8. Backend Selection & Honesty | v0.2 | 2/2 | Complete | 2026-08-09 |
| 9. Live ORT Fixed-Class YOLO | v0.2 | 2/2 | Complete | 2026-08-09 |
| 10. Live TensorRT Fixed-Class YOLO | v0.2 | 2/2 | Complete | 2026-08-10 |
| 11. Sticky Fallback & Dual-Model Guardrails | v0.2 | 2/2 | Complete | 2026-08-10 |
| 12. Docs, CI & Packaging Polish | v0.2 | 2/2 | Complete | 2026-08-10 |

**Coverage:** v0.2 20/20 requirements mapped and shipped ✓

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

**v0.2 plug-in point:** `build_detection_worker(profile_runtime)` at serve construction — torch / ORT / TRT loaders for fixed-class YOLO. DetectionLoop, FrameBus, PerceptionStore, `/v1` frozen.

## Stack Snapshot

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file/RTSP); synthetic for tests; Continuity uniqueID on macOS |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE; live ORT/TRT for fixed-class |
| Depth | Depth Anything V2 Small (Apache-2.0 default) — PyTorch/HF |
| Free-space | NumPy/OpenCV postprocess |
| Frontend | Static Live Preview (MJPEG + controls) |
| Edge | Live ORT + live TRT for fixed-class YOLO; soft/strict fallback; Jetson-free CI |

