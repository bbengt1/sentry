---
gsd_state_version: 1.0
milestone: v0.4
milestone_name: Online Re-calibration
status: executing
last_updated: "2026-10-08"
last_activity: 2026-10-08
progress:
  total_phases: 4
  completed_phases: 2
  total_plans: 6
  completed_plans: 5
  percent: 50
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-15)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** v0.4 Phase 21 in progress. 21-01 done (gated auto-commit, strict horizon, deadband on the control plane). Next: 21-02 DepthLoop hook.

## Current Position

Phase: 21 of 22 planned (Gated auto-commit + DepthLoop/status) — v0.4 phases 19–22  
Plan: 21-01 done; 21-02 next (wave 2)  
Status: Phase 21 in progress (1/2)  
Last activity: 2026-10-08 — 21-01 implemented (gated auto-commit, strict horizon, deadband)

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed (v0.4): 5
- v1.0 + v0.2 + v0.3 history: 40 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 19. Online consent & honesty state | 2/2 | 2 | - |
| 20. Online sample + fit/reject | 2/2 | 2 | - |
| 21. Gated auto-commit + DepthLoop/status | 1/2 | 2 | - |

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

Phase 20 plan locks (2026-10-01):
- Sampler is `OnlineSampler` over `CalibrationState` (not a second state object, not a DepthLoop hook)
- Consent anchors captured only on successful wizard `apply()`; session-only; `try_reapply` does not invent them
- Window `ONLINE_WINDOW_N=8`, `ONLINE_MIN_INTERVAL_S=1.0`, strictly increasing `frame_id`
- Map default `raw` (pre-`apply_map`); `map_space="applied"` inverts `(map - offset) / scale`
- Fit is `fit_scale_median` only; `ok=True` → `set_draft_params`; `ok=False` → `clear_draft_params`; never `apply` / `apply_params` / `apply_map`
- Phase 20 never assigns `auto_committed` or `rejected`
- Cancel drops the draft window, not anchors; Clear drops anchors with applied; disable-online drops neither
- CR-007 folded only as sampler locks (N, pre-apply raw, absurd scale does not stage). YAML / `manual_scale` / boot null width not in this phase
- 20-01 window; 20-02 fit/reject. No route, no UI, no YAML key

Brent 2026-10-05: anchors only after a wizard `apply()` in the same process. The sampler stays idle after restart (`no_anchors`). Restart support is out of scope for Phase 20.

20-01 shipped (2026-10-05):
- `ConsentAnchor` captured only on successful `apply()`, before draft samples are cleared
- `apply_params` does not invent anchors; `clear_applied` clears them and forces online off
- `OnlineSampler.consider` writes draft samples only (`N=8`, 1.0 s, strictly increasing `frame_id`)
- 20-01 stopped at `window_short`. 20-02 fits once the window is full
- Default `map_space="raw"`; `applied` inverts `(map - offset) / scale`
- Cancel drops the draft window; disable-online drops neither applied, anchors, nor existing draft
- No route, YAML key, snapshot field, DepthLoop hook, or dependency

20-02 shipped (2026-10-05):
- Full window calls `fit_scale_median` (`method="known_distance"`). Gates in `spatial/calibration.py` are unchanged
- `ok=True` → `set_draft_params` with the applied fingerprint. `snapshot.scale` stays applied
- `ok=False` → `clear_draft_params` only. Samples and applied scale stay. A later reject clears an earlier staged draft
- `online_status` stays `online_draft`. This phase does not assign `auto_committed` or `rejected`
- In-range scale 1000 may stage draft and does not replace the applied scale. Horizon refuse is still a Phase 21 question

Brent 2026-10-08 (CR-007, LOCKED): auto-commit refuses any scale that passes the v0.3 gates but would push the raw map past the 3 m free-space horizon (`DEFAULT_METRIC_MID_CUT_M`) once applied. On refuse, keep the last consented calibration applied. Wizard Apply is the override and does not get this gate.

Brent 2026-10-08 (LOCKED): horizon rule stays strict, so deep scenes are refused even when the consented scale already puts the median at or past 3 m. Commit deadband: a safe candidate within 1% of applied is skipped (no apply, no smoother reset, not rejected).

Phase 21 plan locks (2026-10-08):
- Commit only via `apply_params(candidate, expect_applied=applied)`; atomic online+identity check under the state lock; sets `auto_committed` there
- Six conjuncts: online, applied, fit ok, residual, `fingerprints_match` (live frame), horizon
- Horizon (ONL-09, strict): `scale * median(finite > 0 raw of the window-closing frame) + offset >= 3.0` → `horizon_refused`; no valid pixel → `horizon_unknown`; never consults the applied scale
- Deadband (after all safety gates): `abs(candidate - applied) < ONLINE_COMMIT_DEADBAND * applied`, `ONLINE_COMMIT_DEADBAND = 0.01` in `online_sampler.py`; exactly 1% commits. Skip → `within_deadband`: no `apply_params`, no smoother reset, `clear_draft_params`, `online_status` unchanged, window kept
- Online candidates scale-only (`offset_not_zero` refuse); commit the sampler's own fit, never `_draft_params`
- Every refuse: applied unchanged, `clear_draft_params`, `mark_online_rejected` (only while online)
- `online_status` = last commit-or-refuse decision; deadband skip / Cancel / wizard `apply()` do not change it
- `OnlineSampler(auto_commit=False)` default keeps Phase 20 contract; `serve` wires `auto_commit=True` + `on_auto_commit=free_space_loop.reset_smoother`
- DepthLoop hook after `refuse_if_mismatch`, before unchanged `promote_kind_unit` / `apply_map`; raw map; `time.monotonic()`
- No YAML on auto-commit; no route / snapshot field / YAML key / dep; version 0.1.0; restart out of scope; fit gates untouched
- 21-01 (wave 1): ONL-05 + ONL-09 control plane. 21-02 (wave 2): ONL-07 DepthLoop hook + serve wiring + status

21-01 shipped (2026-10-08):
- `apply_params(params, *, expect_applied=None)`: guarded commit (online + same applied object under the lock, else `auto_commit_stale`); sets `auto_committed`. Default path unchanged
- `mark_online_rejected()` sets `rejected` only while online
- `OnlineSampler(auto_commit=False, on_auto_commit=None)`, `consider(..., live_fingerprint=None)`; default stays Phase 20 draft-only
- Gate order: online, applied, residual, fingerprint, scale-only, strict horizon (`horizon_median_m` vs imported `DEFAULT_METRIC_MID_CUT_M`); then `within_deadband` (`ONLINE_COMMIT_DEADBAND = 0.01`); then commit
- Not yet wired to live frames: no DepthLoop hook, no serve wiring (21-02)

### Pending Todos

- Execute 21-02 when asked. Do not start Phase 22

### Blockers/Concerns

- None. CR-007 horizon decision resolved 2026-10-08 (ONL-09). Wizard/YAML half of CR-007 stays open by design (wizard is the override)

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

Last session: 2026-10-08 — 21-01 implemented  
Stopped at: `feat/21-01-gated-auto-commit`  
Resume file: `.planning/phases/21-gated-auto-commit-depthloop-status/21-02-PLAN.md`  
Next: execute 21-02
