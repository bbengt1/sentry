---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: Online Re-calibration
status: planning
last_updated: "2026-08-15"
last_activity: 2026-08-15
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** v0.4 Online Re-calibration — defining (research → requirements → roadmap).

## Current Position

Milestone: **v0.4 started** (v0.3 shipped; phases 13–18 archived)  
Phase: Not started (defining requirements)  
Plan: —  
Status: Defining requirements  
Last activity: 2026-08-15 — Milestone v0.4 started

Progress: [░░░░░░░░░░] 0%

## Accumulated Context

**Decisions:** See PROJECT.md Key Decisions (v0.3 DepthLoop apply_map / wizard / free-space meters iff calibrated / YAML persist). v0.4 locks: consent-once gated auto-commit; online default off; first scale still Apply or persist `try_reapply`; draft ≠ meters; same fit/reject; auto-commit via `apply_params` only when already applied + fit ok + residual + fingerprints_match; sticky scale; Cancel/Clear unchanged; auto-commit session-only; status separate from `depth.kind` / persist.

**Open blockers:** None for milestone start.

## Deferred Items

From v1.0 / v0.2 / v0.3 close (non-blocking):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02–04 human_needed UAT | acknowledged |
| integration | Free-space after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | VALIDATION.md still wave_0_complete false (v0.2 + v0.3) | docs debt |
| hardware | ORT/TRT E2E remains operator checklist | v0.2 residual |
| verification | Phases 14–18 SUMMARY only (no VERIFICATION.md) | v0.3 residual |

See also: `milestones/v1.0-MILESTONE-AUDIT.md`, `milestones/v0.2-MILESTONE-AUDIT.md`, `milestones/v0.3-MILESTONE-AUDIT.md`.

## Session Continuity

Last session closed milestone v0.3. Resume: define v0.4 research, then REQUIREMENTS, then ROADMAP phases 19–22. Do not create `.planning/phases/` until `/gsd:plan-phase 19`.
