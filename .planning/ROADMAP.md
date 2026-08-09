# Roadmap: Sentry AI

## Milestones

- ✅ **v1.0 Camera-only perception MVP** — Phases 1–7 (shipped 2026-08-09)
- 📋 **Next** — define via `/gsd:new-milestone`

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

## Stack Snapshot

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file/RTSP); synthetic for tests |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE |
| Depth | Depth Anything V2 Small (Apache-2.0 default) |
| Free-space | NumPy/OpenCV postprocess |
| Frontend | Static Live Preview (MJPEG + controls) |
| Edge | Profiles + ONNX/TensorRT export recipes; live path PyTorch |

## Out of Scope (product thesis)

- LiDAR/radar required sensors  
- Full SLAM / multi-cam fusion  
- Robot control / motion planning  
- Voice I/O and scene chat as primary UI  
- Mandatory cloud inference  

---
*v1.0 archived 2026-08-09 — next milestone via `/gsd:new-milestone`*
