---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: Metric Depth Calibration UX
status: ready_to_execute
last_updated: "2026-08-11T12:00:00.000Z"
last_activity: 2026-08-11
progress:
  total_phases: 6
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-11)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** Phase 13 planned (2026-08-11) — ready for `/gsd:execute-phase 13`

## Current Position

Phase: 13 of 18 (Honesty Contracts & CalibrationState) — v0.3 phases 13–18  
Plan: —  
Status: Ready to plan  
Last activity: 2026-08-11 — v0.3 roadmap created (phases 13–18)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed (v0.3): 0
- v1.0 + v0.2 history: 28 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

*Updated after each plan completion*

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

Last session: 2026-08-11 — created v0.3 roadmap (phases 13–18)  
Stopped at: ROADMAP.md + STATE.md + REQUIREMENTS traceability written  
Resume file: None  
Next: `/gsd:plan-phase 13`
