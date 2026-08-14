# Roadmap: Sentry AI

## Milestones

- ✅ **v1.0 Camera-only perception MVP** — Phases 1–7 (shipped 2026-08-09)
- ✅ **v0.2 Edge Runtime** — Phases 8–12 (shipped 2026-08-10)
- ✅ **v0.3 Metric Depth Calibration UX** — Phases 13–18 (shipped 2026-08-14)

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

<details>
<summary>✅ v0.3 Metric Depth Calibration UX (Phases 13–18) — SHIPPED 2026-08-14</summary>

- [x] Phase 13: Honesty Contracts & CalibrationState (2/2 plans) — completed 2026-08-11
- [x] Phase 14: Scale Math + DepthLoop Plug-in (2/2 plans) — completed 2026-08-13
- [x] Phase 15: Wizard REST + Live Preview UI (2/2 plans) — completed 2026-08-13
- [x] Phase 16: Free-Space Metric Path (2/2 plans) — completed 2026-08-13
- [x] Phase 17: Persist & Re-apply on Serve (2/2 plans) — completed 2026-08-14
- [x] Phase 18: Docs + Synthetic CI Polish (2/2 plans) — completed 2026-08-14

Full phase detail: [milestones/v0.3-ROADMAP.md](milestones/v0.3-ROADMAP.md)  
Requirements archive: [milestones/v0.3-REQUIREMENTS.md](milestones/v0.3-REQUIREMENTS.md)  
Audit: [milestones/v0.3-MILESTONE-AUDIT.md](milestones/v0.3-MILESTONE-AUDIT.md)

</details>

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1–7 | v1.0 | 18/18 | Complete | 2026-08-09 |
| 8. Backend Selection & Honesty | v0.2 | 2/2 | Complete | 2026-08-09 |
| 9. Live ORT Fixed-Class YOLO | v0.2 | 2/2 | Complete | 2026-08-09 |
| 10. Live TensorRT Fixed-Class YOLO | v0.2 | 2/2 | Complete | 2026-08-10 |
| 11. Sticky Fallback & Dual-Model Guardrails | v0.2 | 2/2 | Complete | 2026-08-10 |
| 12. Docs, CI & Packaging Polish | v0.2 | 2/2 | Complete | 2026-08-10 |
| 13–18 | v0.3 | 12/12 | Complete | 2026-08-14 |

**Coverage:** v0.3 19/19 requirements mapped and shipped ✓

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
          ┌───────────┬───────────┐
          ▼                       ▼
   Web Dev UI              Perception Stream API
   (overlays+controls)     (WS/REST → robots)
```

**v0.2 plug-in point:** `build_detection_worker(profile_runtime)` at serve construction — torch / ORT / TRT loaders for fixed-class YOLO. DetectionLoop, FrameBus, PerceptionStore, `/v1` frozen.

**v0.3 plug-in point:** `CalibrationState.apply_map` **after** `DepthAnythingWorker.process` and **before** `PerceptionStore.set_depth` inside DepthLoop. Free-space, MJPEG, assemble, and `/v1` inherit calibrated map + kind. DetectionLoop / FrameBus / ORT-TRT factory remain frozen.

```
DepthAnythingWorker.process → raw map + kind/unit
  → CalibrationState.apply_if_active → scale*map (+shift); kind=metric_calibrated; unit="m"
  → PerceptionStore.set_depth
  → FreeSpaceLoop (units="m" only when metric_calibrated)
```

## Stack Snapshot

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file/RTSP); synthetic for tests; Continuity uniqueID on macOS |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE; live ORT/TRT for fixed-class |
| Depth | Depth Anything V2 Small (Apache-2.0 default) — PyTorch/HF |
| Calibration | Pure NumPy scale/shift fit + CalibrationState (zero new deps) |
| Free-space | NumPy/OpenCV postprocess; meters only when `metric_calibrated` |
| Frontend | Static Live Preview (MJPEG + controls + calibration wizard) |
| Edge | Live ORT + live TRT for fixed-class YOLO; soft/strict fallback; Jetson-free CI |
| Persist | Per-`camera_id` YAML under cache/config root; fingerprint-gated auto-load |
