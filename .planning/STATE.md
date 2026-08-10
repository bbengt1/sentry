---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: Edge Runtime
status: verifying
stopped_at: Completed 12-01-PLAN.md
last_updated: "2026-08-10T21:29:11.888Z"
last_activity: 2026-08-10
progress:
  total_phases: 5
  completed_phases: 5
  total_plans: 10
  completed_plans: 10
  percent: 100
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-09)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** Phase 12 — Docs, CI & Packaging Polish

## Current Position

Phase: 12 (Docs, CI & Packaging Polish) — EXECUTING
Plan: 2 of 2
Status: Phase complete — ready for verification
Last activity: 2026-08-10

Progress: [██████████] 100%

## Performance Metrics

**Velocity:**

- Total plans completed: 18 (v1.0) + 2 (v0.2 Phase 8) + 2 (v0.2 Phase 9) + 2 (v0.2 Phase 10) + 2 (v0.2 Phase 11)
- Average duration: —
- Total execution time: ~21 min plans (v0.2 Phases 8–11)

**By Phase (v0.2):**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 8 | 2/2 | 6min | 3min |
| 9 | 2/2 | 5min | 2.5min |
| 10 | 2/2 | 6min | 3min |
| 11 | 2/2 | 6min | 3min |
| 12 | 0/2 | - | - |

**Recent Trend:**

- Phase 8 verified 2026-08-09 (5/5 must-haves)
- Phase 9 plan 01 complete 2026-08-09 (live ORT factory + onnx extra + docs)
- Phase 9 plan 02 complete 2026-08-09 (ORT parity/golden + status honesty)
- Phase 10 plan 01 complete 2026-08-10 (live TRT factory + parity + status honesty)
- Phase 11 plan 01 complete 2026-08-10 (sticky soft/strict fallback BACK-03)
- Phase 11 plan 02 complete 2026-08-10 (operator surface + EDGE-RT-04 dual-model docs)
- Trend: —

| Phase 08 P01 | 3min | 3 tasks | 7 files |
| Phase 08 P02 | 3min | 2 tasks | 8 files |
| Phase 09 P01 | 3min | 3 tasks | 10 files |
| Phase 09 P02 | 2min | 2 tasks | 2 files |
| Phase 10 P01 | 4min | 3 tasks | 4 files |
| Phase 10 P02 | 2min | 2 tasks | 7 files |
| Phase 11 P01 | 3min | 3 tasks | 9 files |
| Phase 11 P02 | 3min | 2 tasks | 12 files |
| Phase 12 P02 | 1min | 3 tasks | 3 files |
| Phase 12 P01 | 3min | 3 tasks | 12 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. v0.2 roadmap-binding:

- v0.2 = live ORT + live TRT for **fixed-class YOLO only**; depth/OV stay PyTorch
- Plug-in at serve factory (`build_detection_worker`); DetectionLoop/FrameBus/`/v1` frozen
- Ultralytics-native load path (`YOLO("*.onnx|engine")`) — no custom ORT decode in v0.2
- No `tensorrt` pip extra; on-device engines only; no multi-SKU engines in wheel
- Soft torch fallback default (loud); sticky resolve; strict mode available
- Phases continue 8–12 (v1.0 used 1–7); standard granularity (5 phases)
- [Phase 08]: Soft stub ORT/TRT with torch worker + reason codes (not construct-time raise)
- [Phase 08]: Factory sole author of backend_live; Phase 8 never emits live ORT/TRT
- [Phase 08]: path_rejected raises on explicit/env; cache/CWD miss returns None
- [Phase 08]: Route never recomputes live from preferred_backend — pass-through only
- [Phase 09]: Live ORT via Ultralytics-native YOLO("*.onnx"); soft-fall ort_artifact_missing/ort_dep_missing/path_rejected
- [Phase 09]: verified 2026-08-09 — 4/4 roadmap SCs; ORT-01..04 satisfied
- [Phase 08]: Structured banner fields replace prose-only export-target notes
- [Phase 08]: Footer shows requested → live; appends reason when they differ
- [Phase 08 verified]: All roadmap SCs + BACK-01/02/04 + EDGE-RT-01..03 satisfied in code
- [Phase 09]: Reuse YoloDetectionWorker with weights=str(onnx_path); no thin ORT wrapper
- [Phase 09]: Dep probe via importlib.util.find_spec only; no hard factory import
- [Phase 09]: Retire ort_loader_not_implemented; reasons ort_artifact_missing|ort_dep_missing|path_rejected
- [Phase 09]: onnx extra CPU pin only; no tensorrt or onnxruntime-gpu extra
- [Phase 09]: Local FakeModel in parity module; live path asserts backend_live+onnx weights before process
- [Phase 09]: No real YOLO(*.onnx) in default CI parity suite (ORT-04 mocks only)
- [Phase 10]: Reuse YoloDetectionWorker with weights=str(engine_path); no thin TRT wrapper
- [Phase 10]: Dep probe via importlib.util.find_spec(tensorrt) only; no hard factory import
- [Phase 10]: Retire trt_loader_not_implemented; reasons trt_artifact_missing|trt_dep_missing|path_rejected
- [Phase ?]: Primary live TRT docs in yolo26; JetPack packaging separate
- [Phase 10]: Primary live TRT table in yolo26-onnx-tensorrt.md; JetPack/no-pip in jetson-packaging.md
- [Phase 10]: jetson.yaml comments only — YAML field values unchanged
- [Phase 10]: No FPS claims; dual-model measure-on-device with Phase 11 deferred
- [Phase 11]: Soft fallback_to_torch=True global default — Maker UX + jetson soft default lock
- [Phase 11]: Strict miss: worker=None, backend_live=None, reason set — Never silent torch under preferred ORT/TRT
- [Phase 11]: Strict serve Exit(1) + SENTRY_FALLBACK_TO_TORCH always-wins — Fail-closed robots; soft maker default via env/config
- [Phase 11]: fallback_to_torch is bool|None on StatusSnapshot with is-not-None pass-through (False preserved)
- [Phase 11]: EDGE-RT-04: depth/OV stay PyTorch constructors outside build_detection_worker
- [Phase 11]: Dual-model: measure-on-device YOLO+DAV2; continuous OV+TRT+DAV2 not first-class; Phase 11 deferral retired
- [Phase 12]: Leave ci.yml byte-identical — already Jetson/GPU-free; lock with tests only
- [Phase 12]: EDGE-CI-01 is verify-only — no factory rewrite; document matrix ownership in test docstring
- [Phase 12]: gitignore *.engine/*.onnx next to *.pt; zero tracked engines confirmed
- [Phase 12]: Ship thin docs/edge-serve.md hub rather than expanding only export/*
- [Phase 12]: AGPL derived-artifact section uses evaluate-obligations / same commercial caution tone — not compliance certification
- [Phase 12]: CHANGELOG Unreleased only; do not bump package 0.1.0 → 0.2.0

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 10 may need light JetPack/TRT research at plan time (SKU matrix)
- Soft vs strict default for jetson: **resolved in 11-01** — soft remains global default; strict opt-in via config/env

## Deferred Items

From v1.0 close (carried forward; non-blocking for v0.2):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02–04 human_needed UAT | acknowledged |
| integration | Free-space after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | Most VALIDATION.md still nyquist_compliant false | docs debt |

See also: `milestones/v1.0-MILESTONE-AUDIT.md`.

Live ORT/TRT inference deferred to Phases 9–10 (intentional Phase 8 soft-stub).

## Session Continuity

Last session: 2026-08-10T21:29:11.881Z
Stopped at: Completed 12-01-PLAN.md
Resume file: None
Next: Execute 11-02-PLAN.md (dual-model scope lock + operator status surface EDGE-RT-04)
