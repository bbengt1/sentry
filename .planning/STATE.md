---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: Metric Depth Calibration UX
status: executing
stopped_at: Phase 16-01 complete on branch; next execute 16-02
last_updated: "2026-08-13T23:45:00.000Z"
last_activity: 2026-08-13
progress:
  total_phases: 6
  completed_phases: 3
  total_plans: 8
  completed_plans: 7
  percent: 58
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-11)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots - without proprietary sensors or cloud AI.  
**Current focus:** Phase 16-01 metric `compute_free_space` shipped (pure compute). Next is execute 16-02 (loop consume, smoother reset, assemble/validator/store, optional `distance_m`).

## Current Position

Phase: 16 (Free-Space Metric Path) - 16-01 done  
Plan: 1 of 2 (16-01 executed; 16-02 written, not executed)  
Status: Phase 15 complete on main; 16-01 on `feat/16-01-free-space-metric-compute`  
Last activity: 2026-08-13

Progress: [#########.] 58% of v0.3 executed plans (13-15 complete; 16-01 done; next 16-02)

## Performance Metrics

**Velocity:**

- Total plans completed (v0.3): 7 (Phase 13 + Phase 14 + Phase 15 + 16-01)
- v1.0 + v0.2 history: 28 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 13 P01 | 3min | 2 tasks | 7 files |
| Phase 13 P02 | 2min | 2 tasks | 5 files |
| Phase 14 P01 | 8min | 1 task | 5 files |
| Phase 14 P02 | 25min | 2 tasks | 7 files |
| Phase 15 P01 | 40min | 2 tasks | 16 files |
| Phase 15 P02 | 35min | 1 task | 4 files |
| Phase 16 P01 | 25min | 1 task | 3 files |

*Updated after each plan completion*

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions (v0.2 factory / ORT / TRT / soft-strict / torch-only depth-OV).

v0.3 roadmap locks (from research):

- Zero new pip dependencies (numpy fit only)
- Post-process scale in DepthLoop (not worker, not free-space, not UI)
- Primary GT = known distance; height feeds same fitter with documented assumptions
- metric_calibrated + unit="m" only when applied and valid
- Free-space meters only after real metric path (not label-only)
- Persist per camera_id with fingerprint refuse
- Static wizard + REST - no new frontend stack, no FSD claims
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
- [Phase 14-01]: CalibrationFitResult lives in spatial/calibration.py (not schemas); lazy spatial exports
- [Phase 14-02]: apply_map CoW float32 under lock; DepthLoop sole apply site; CLI injects CalibrationState; error paths do not invent calibrated meters
- [Phase 15]: Cancel = clear_draft only; explicit Clear = clear_applied
- [Phase 15]: Sample only when inactive (409 if applied)
- [Phase 15]: Same CalibrationState instance for DepthLoop and create_app
- [Phase 15]: REST in-memory only (no YAML); extra=forbid; 503 if state missing
- [Phase 15]: UI never locally claims metric_calibrated; preview numbers from draft until Apply
- [Phase 15-01]: CalibrationSample + public draft sample APIs; freeze pin on app.state
- [Phase 15-01]: CLI hoists CalibrationState for DepthLoop AND create_app
- [Phase 15-01]: REST in-memory freeze/sample/compute/apply/cancel/clear; status additive
- [Phase 15-02]: Static #calibration-wizard on index.html; click-to-sample via naturalWidth/Height
- [Phase 15-02]: Footer #metric-calibration from status calibration_active/scale/method/sample_count
- [Phase 15-02]: Draft numbers labeled draft (not live); badge still status depth_kind only
- [Phase 16]: Calibrated units="m" iff absolute meter cuts (1.5 m / 3.0 m) on scaled depth; never label-only 0.72/0.45 flip
- [Phase 16]: Relative + metric_estimated stay ordinal (percentile + auto polarity)
- [Phase 16]: nearness_* remain 0..1; optional distance_m on cues only when calibrated (mean blob depth)
- [Phase 16]: Pin higher_is_farther on calibrated path; never min-max normalize meters
- [Phase 16]: OccupancySmoother.reset on kind apply\u2194clear; FreeSpaceLoop.reset_smoother; loop detects kind change (no CalibrationState listeners)
- [Phase 16]: assemble METRIC_CALIBRATED \u2192 "m"; else "ordinal"; calibrated must emit "m" (Phase 13 grace ends)
- [Phase 16]: Consume DepthLoop scaled map + kind \u2014 never re-scale
- [Phase 16]: Split 16-01 pure compute honesty / 16-02 loop+wire+reset+distance_m
- [Phase 16-01]: compute_free_space metric branch shipped; wire still allows calibrated+ordinal until 16-02 assemble flip

### Pending Todos

- Execute 16-02 (loop consume, smoother reset, assemble/validator/store, optional `distance_m`)
- Then Phase 17 YAML persist

### Blockers/Concerns

- Phase 16-01 compute path exists; do not tighten `assert_free_space_units` until 16-02 flips assemble/store
- Persist path: prefer `$SENTRY_MODEL_CACHE/calibration/*.yaml` (STACK) - resolve in Phase 17 plan

## Deferred Items

From v1.0 / v0.2 close (carried forward; non-blocking for v0.3):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02-04 human_needed UAT | acknowledged |
| integration | Free-space after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | Most VALIDATION.md still nyquist_compliant false | docs debt |
| hardware | ORT/TRT E2E remains operator checklist | v0.2 residual |

See also: `milestones/v1.0-MILESTONE-AUDIT.md`, `milestones/v0.2-MILESTONE-AUDIT.md`.

## Session Continuity

Last session: 2026-08-13T23:45:00.000Z
Stopped at: 16-01 metric compute_free_space executed
Resume file: None
Next: Execute 16-02 per ROADMAP / `.planning/phases/16-free-space-meters/16-02-PLAN.md`
