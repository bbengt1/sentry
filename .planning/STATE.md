---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: Online Re-calibration
status: plans_ready
last_updated: "2026-08-15"
last_activity: 2026-08-15
progress:
  total_phases: 4
  completed_phases: 0
  total_plans: 2
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** v0.4 Phase 19 plans written — ready to execute 19-01 (opt-in flag + first-scale lock).

## Current Position

Phase: 19 of 22 (Online consent & honesty state) — v0.4 phases 19–22  
Plan: 19-01  
Status: Ready to execute  
Last activity: 2026-08-15 — Phase 19 research + plans written (19-01, 19-02)

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed (v0.4): 0
- v1.0 + v0.2 + v0.3 history: 40 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19. Online consent & honesty state | 0/2 | 2 | - |

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

### Pending Todos

- Execute 19-01 (opt-in flag + honesty state machine)
- Then execute 19-02 (Cancel/Clear/disable-online + status fields)

### Blockers/Concerns

- Phase 20 needs plan-phase lock for N-sample / throttle defaults (reuse fit as-is)
- Do not start Phase 20 until 19-01 and 19-02 merge

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

Last session: 2026-08-15 — Phase 19 plans written (research + 19-01/19-02)  
Stopped at: `.planning/phases/19-online-consent-honesty-state/` + STATE/ROADMAP updated (plans written, not executed)  
Resume file: `.planning/phases/19-online-consent-honesty-state/19-01-PLAN.md`  
Next: execute 19-01
