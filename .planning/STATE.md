---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: Metric Depth Calibration UX
status: executing
stopped_at: Completed 13-01-PLAN.md
last_updated: "2026-08-11T14:02:31.724Z"
last_activity: 2026-08-11
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 2
  completed_plans: 1
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-11)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** Phase 13 — Honesty Contracts & CalibrationState

## Current Position

Phase: 13 (Honesty Contracts & CalibrationState) — EXECUTING
Plan: 2 of 2
Status: Ready to execute
Last activity: 2026-08-11

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**

- Total plans completed (v0.3): 0
- v1.0 + v0.2 history: 28 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*
| Phase 13 P01 | 3min | 2 tasks | 7 files |

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

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 14 needs plan-phase research: pure scale vs affine; residual gates; metric_estimated double-scale
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

Last session: 2026-08-11T14:02:31.442Z
Stopped at: Completed 13-01-PLAN.md
Resume file: None
Next: `/gsd:plan-phase 13`
