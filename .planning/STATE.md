---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: Online Re-calibration
status: executing
last_updated: "2026-08-30"
last_activity: 2026-08-30
progress:
  total_phases: 4
  completed_phases: 1
  total_plans: 2
  completed_plans: 2
  percent: 25
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** v0.4 Phase 19 complete (online consent + honesty state). Next: plan Phase 20.

## Current Position

Phase: 19 of 22 complete (Online consent & honesty state) — v0.4 phases 19–22  
Plan: 19-02 done  
Status: Phase 19 complete; next is plan Phase 20  
Last activity: 2026-08-30 — 19-02 implemented (Cancel/Clear/disable-online + four-way online_status + thin REST POST)

Progress: [██░░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed (v0.4): 2
- v1.0 + v0.2 + v0.3 history: 40 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19. Online consent & honesty state | 2/2 | 2 | - |

*Updated after each plan completion*

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions (v0.3 DepthLoop apply_map / wizard / free-space meters iff calibrated / YAML persist).

v0.4 roadmap locks (from research):
- First `metric_calibrated` still needs explicit Apply or matching persist `try_reapply`
- Online mode default off
- Draft ≠ meters (WIZ-04 holds until apply()/apply_params of a passed fit)
- Same fit-time reject gates; `ok=False` never becomes applied
- Auto-commit only if: online on AND already applied AND fit ok AND residual gate AND fingerprints_match — use `apply_params`; DepthLoop sole `apply_map`; reset free-space smoother on auto-commit like Apply
- No per-frame unguarded refit — sticky scale; throttle / N-sample window
- Cancel = draft only; Clear = applied + YAML; disable-online ≠ Clear
- Auto-commit is session-only; YAML only on explicit save / persist:true / documented opt-in
- Status distinguishes `online_off` / `online_draft` / `auto_committed` / `rejected` from `depth.kind` and persist status
- Zero new deps; freeze DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; synthetic CI; no FSD

Phase 19 plan locks (2026-08-15):
- Home for the flag: `CalibrationState` (not a new `OnlineRecalState`)
- Flag is **session-only** (no YAML / env / CLI this phase)
- Enable while unapplied: refuse (`online_requires_applied` / REST 409)
- 19-01: flag + first-scale lock; 19-02: Cancel/Clear/disable matrix + four-way status + thin POST `/api/depth/calibration/online`
- Phase 19 never sets `auto_committed` or `rejected` (enum exists for 21)
- No sampler / auto-commit / persist-policy / DepthLoop `apply_map` in Phase 19

19-01 shipped (2026-08-17):
- `is_online()` / `set_online(enabled) -> CalibrationSnapshot`
- `CalibrationSnapshot.online` defaults False
- `set_online(True)` unapplied → `ValueError("online_requires_applied")`
- `apply` / `apply_params` / matching `try_reapply` do not enable online
- `clear_applied` forces online off; `set_online(False)` does not clear applied

19-02 shipped (2026-08-30):
- `CalibrationSnapshot.online_status` four-way enum (default `online_off`)
- Cancel = `clear_draft` only (online unchanged); Clear forces `online_off` via `clear_applied`
- `set_online(False)` / POST enabled=false does not clear applied or delete YAML
- `POST /api/depth/calibration/online` extra=forbid; unapplied enable → 409
- `GET /api/status` additive `calibration_online` + `calibration_online_status`
- Phase 19 never assigns `auto_committed` or `rejected`

### Pending Todos

- Plan Phase 20 (online sample + fit/reject). Do not start 20 execution yet.

### Blockers/Concerns

- Phase 20 needs plan-phase lock for N-sample / throttle defaults (reuse fit as-is)
- Do not start Phase 20 plans until 19-02 merges

## Deferred Items

From v1.0 / v0.2 / v0.3 close (non-blocking for v0.4):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02–04 human_needed UAT | acknowledged |
| integration | Free-space after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | VALIDATION.md still wave_0_complete false (v0.2 + v0.3) | docs debt |
| hardware | ORT/TRT E2E remains operator checklist | v0.2 residual |
| verification | Phases 14–18 SUMMARY only (no VERIFICATION.md) | v0.3 residual |

See also: `milestones/v1.0-MILESTONE-AUDIT.md`, `milestones/v0.2-MILESTONE-AUDIT.md`, `milestones/v0.3-MILESTONE-AUDIT.md`.

## Session Continuity

Last session: 2026-08-30 — 19-02 implemented (Cancel/Clear/disable + online_status REST)  
Stopped at: `feat/19-02-online-status-rest`  
Resume file: `.planning/ROADMAP.md` (Phase 20 not planned yet)  
Next: plan Phase 20
