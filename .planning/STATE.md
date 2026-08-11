---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: Metric Depth Calibration UX
status: planning
last_updated: "2026-08-11T09:56:24.438Z"
last_activity: 2026-08-11
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-10)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** v0.2 Edge Runtime shipped — plan next with `/gsd:new-milestone`

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-08-11 — Milestone v0.3 started

## Accumulated Context

**Decisions:** See PROJECT.md Key Decisions (v0.2 factory / ORT / TRT / soft-strict / torch-only depth-OV).

**Open blockers:** None for milestone close.

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

Last session closed milestone v0.2. Resume with `/gsd:new-milestone` or operator UAT via `docs/edge-serve.md`.
