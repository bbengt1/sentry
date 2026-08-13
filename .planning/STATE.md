---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: Metric Depth Calibration UX
status: plans_ready
stopped_at: Phase 14 plans written (14-01, 14-02)
last_updated: "2026-08-12T23:57:00.000Z"
last_activity: 2026-08-12
progress:
  total_phases: 6
  completed_phases: 1
  total_plans: 4
  completed_plans: 2
  percent: 17
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-11)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** Phase 14 plans written — ready to execute 14-01 (pure fit/reject); then 14-02 (apply_map + DepthLoop plug-in)

## Current Position

Phase: 14 (Scale Math + DepthLoop Plug-in) — PLANNED  
Plan: 0 of 2  
Status: Research + plans landed — ready to execute 14-01  
Last activity: 2026-08-12

Progress: [░░░░░░░░░░] 0% of Phase 14

## Performance Metrics

**Velocity:**

- Total plans completed (v0.3): 2 (Phase 13)
- v1.0 + v0.2 history: 28 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*
| Phase 13 P01 | 3min | 2 tasks | 7 files |
| Phase 13 P02 | 2min | 2 tasks | 5 files |

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions (v0.2 factory / ORT / TRT / soft-strict / torch-only depth-OV).

v0.3 roadmap locks (from research):

- Zero new pip dependencies (numpy fit only)
- Post-process scale in DepthLoop (not worker, not free-space, not UI)
- Primary GT = known distance; height feeds same fitter with documented assumptions
- `metric_calibrated` + `unit="m"` only when applied and valid
- Free-space meters only after real metric path (not label-only)
- Persist per camera_id with fingerprint refuse
- Static wizard + REST — no React, no FSD claims
- [Phase 13]: relative_depth_forbids_unit delegates to assert_depth_kind_unit for single matrix
- [Phase 13]: FreeSpacePayload allows metric_calibrated + ordinal until Phase 16
- [Phase 13]: kind_for_mode production mapping left unchanged; never-calibrated is test-only
- [Phase 13]: Clear draft on successful apply (wizard Apply semantics)
- [Phase 13]: get_applied_params() exposed for Phase 14 consumers
- [Phase 13]: CalibrationSnapshot includes scale/method/fingerprint when applied
- [Phase 13]: manual_scale skips sample_count floor; other methods require >= 1
- [Phase 14]: Fit default = scale-only median of D_i/d_i
- [Phase 14]: Optional affine lstsq when N>=2; store scale+offset
- [Phase 14]: Apply map' = scale*map + offset (not inverse-depth)
- [Phase 14]: No polarity flip; reject non-positive observations
- [Phase 14]: residual_rms reject if > max(0.15*median(D), 0.05); absurd scale outside (1e-4, 1e4); fit-time reject before draft
- [Phase 14]: Same apply for relative and metric_estimated; fingerprint depth_mode+model_id; no undo of metric prior
- [Phase 14]: Core fitter = (observed_raw, known_meters) pairs; height helper optional/minimal
- [Phase 14]: Module spatial/calibration.py; state apply_map in control/calibration_state.py
- [Phase 14]: Zero new deps; freeze DetectionLoop/FrameBus/ORT-TRT; synthetic tests; no wizard/YAML/free-space meters; CoW float32; lock in apply_map

### Pending Todos

- Execute 14-01 (pure fit/reject)
- Execute 14-02 (apply_map + DepthLoop + CLI inject)

### Blockers/Concerns

- Phase 16 needs research: free-space meter band semantics (absolute cuts vs distance_m fields)
- Persist path: prefer `$SENTRY_MODEL_CACHE/calibration/*.yaml` (STACK) — resolve in Phase 17 plan

## Deferred Items

From v1.0 / v0.2 close (carried forward; non-blocking for v0.3):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02–04 human_needed UAT | acknowledged |
| integration | Free-space after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | Most VALIDATION.md still nyquist_compliant false | docs debt |
| hardware | ORT/TRT E2E remains operator checklist | v0.2 residual |

See also: `milestones/v1.0-MILESTONE-AUDIT.md`, `milestones/v0.2-MILESTONE-AUDIT.md`.

## Session Continuity

Last session: 2026-08-12T23:57:00.000Z
Stopped at: Phase 14 research + plans written
Resume file: None
Next: `/gsd:execute-phase 14` (start with 14-01)
