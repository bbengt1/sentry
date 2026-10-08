---
phase: 21-gated-auto-commit-depthloop-status
plan: 01
subsystem: control
tags: [calibration, online, auto-commit, horizon, deadband, onl-05, onl-09]

requires:
  - phase: 20-02
    provides: OnlineSampler full-window fit, clear_draft_params
provides:
  - OnlineSampler(auto_commit=True, on_auto_commit=...) with six safety gates
  - horizon_median_m and the strict horizon refuse (ONL-09)
  - within_deadband and ONLINE_COMMIT_DEADBAND = 0.01
  - CalibrationState.apply_params(expect_applied=) atomic guard
  - CalibrationState.mark_online_rejected
affects:
  - 21-02 DepthLoop hook (passes raw map, live fingerprint, monotonic clock; wires on_auto_commit to reset_smoother)

tech-stack:
  added: []
  patterns:
    - Safety gates first, deadband last, guarded apply_params as the only commit door
    - Every refuse keeps the applied object, clears draft params, marks rejected only while online
    - Deadband skip is not a refusal (status unchanged)

key-files:
  created:
    - tests/test_online_auto_commit.py
    - .planning/phases/21-gated-auto-commit-depthloop-status/21-01-SUMMARY.md
  modified:
    - src/sentry_ai/control/online_sampler.py
    - src/sentry_ai/control/calibration_state.py
    - tests/test_calibration_state.py
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Gate order: online, applied, residual, fingerprint, scale-only, strict horizon; then deadband; then apply_params(expect_applied=)"
  - "Horizon threshold is the imported DEFAULT_METRIC_MID_CUT_M; the module has no literal 3.0"
  - "within_deadband uses abs(c - a) < ONLINE_COMMIT_DEADBAND * a so the exact 1% boundary is testable in floats"
  - "Candidate is the sampler's own fit object; _draft_params is never read on the auto-commit path"

patterns-established:
  - "apply_params(expect_applied=...) sets auto_committed under the state lock; Clear/disable win a race"
  - "mark_online_rejected never resurrects status after Clear/disable"

requirements-completed: [ONL-09]

duration: session
completed: 2026-10-08
---

# Phase 21 Plan 01: Gated auto-commit, strict horizon, deadband

**ONL-05 decision logic and ONL-09: with `auto_commit=True`, a passed online fit goes live only through `apply_params(candidate, expect_applied=applied)` when every safety gate holds. The strict horizon refuse and the 1% deadband are both in place. The default sampler is still Phase 20 draft-only.**

## Performance

- **Duration:** one session
- **Completed:** 2026-10-08
- **Tasks:** 2/2
- **Files modified:** sampler, state, two test modules, planning docs

## Accomplishments

- `CalibrationState.apply_params(params, *, expect_applied=None)`: with `expect_applied`, the commit requires online on and the same applied object under the lock. Otherwise it raises `ValueError("auto_commit_stale")`. On success it sets `auto_committed`. The default path is unchanged.
- `CalibrationState.mark_online_rejected()`: sets `rejected` only while online is on. It returns False after Clear or disable.
- `OnlineSampler(..., auto_commit=False, on_auto_commit=None)` and `consider(..., live_fingerprint=None)` are new keyword-only arguments.
- **Auto-commit path:**
  - `fit_rejected`: clears draft params and marks `rejected`.
  - Gates, in order: `gate_online_off`, `gate_not_applied`, `gate_residual`, `fingerprint_unavailable`, `fingerprint_mismatch`, `offset_not_zero`, `horizon_unknown`, `horizon_refused`. Any refuse clears draft params and marks `rejected`.
  - `within_deadband`: clears draft params only. No `apply_params`, no callback, status unchanged, window kept.
  - `committed`: guarded `apply_params`, window cleared, `on_auto_commit()` called. A callback error is logged and the commit stands.
  - `commit_stale`: the guard raised. The sampler marks `rejected`, which is a no-op once Clear has turned online off.
- `horizon_median_m(raw, scale, offset)` returns `scale * median(finite > 0 raw) + offset`, or None. The refuse fires at `>= DEFAULT_METRIC_MID_CUT_M`, and it never looks at the applied scale.
- `within_deadband(c, a)` checks `abs(c - a) < ONLINE_COMMIT_DEADBAND * a`, with `ONLINE_COMMIT_DEADBAND = 0.01`.
- No edits to `spatial/calibration.py`, `schemas/`, `config/`, `calibration_persist.py`, DepthLoop, routes, `cli.py`, or `pyproject.toml`.

## Task Commits

1. **RED**: `test(21-01): failing gated auto-commit, strict horizon, and deadband tests`. The new module failed at import (`ONLINE_COMMIT_DEADBAND` missing). 4 new state tests failed (`expect_applied` / `mark_online_rejected` missing). Phase 20 tests stayed green.
2. **GREEN**: `feat(21-01): gated online auto-commit with strict horizon and deadband`

## Files Created/Modified

- `src/sentry_ai/control/online_sampler.py`: auto-commit branch, `_commit_gate`, `_auto_commit`, `horizon_median_m`, `within_deadband`, `ONLINE_COMMIT_DEADBAND`
- `src/sentry_ai/control/calibration_state.py`: `apply_params(expect_applied=)`, `mark_online_rejected`
- `tests/test_online_auto_commit.py`: 22 tests, 23 cases with the parametrized deadband skip (gate matrix, horizon, deadband, honesty)
- `tests/test_calibration_state.py`: 5 tests (guarded commit and reject-status honesty)

## Decisions Made

- The horizon check runs before the deadband. A deep scene whose candidate equals the applied scale is `horizon_refused`, not `within_deadband`.
- A deadband skip keeps the sliding window, like a refuse, so the next accept refits it.

## Deviations from Plan

- `_commit_gate` is a method with the signature `(candidate, result, live_fingerprint, raw_map)`. It reads the current applied params from state instead of taking `applied` as an argument, so the gate always checks the live applied object.
- Added a defensive `commit_stale` return. It covers applied disappearing between the gate and the deadband check. There is no status write in that case, because Clear already set `online_off`.
- The exact-3.0 m boundary uses applied 1.5, raw 1.0, and known 3.0 (candidate 3.0, `d_med` 3.0). The 2.99 m case uses known 2.99.
- `tests/test_online_sampler.py` is unmodified.

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- ONL-09 is met on the control plane. ONL-05's decision logic is in place, and its live inputs arrive in 21-02.
- 21-02 must pass the pre-apply raw map, the live fingerprint, and `time.monotonic()`. It must also wire `on_auto_commit=free_space_loop.reset_smoother` in `serve`.
- Restart support stays out of scope.

## Verification

```text
uv run ruff check src tests
uv run pytest -q
uv run sentry health
```

943 passed, 1 skipped (the opt-in Ultralytics export test). `spatial/calibration.py`, `schemas/`, `config/`, and `models/depth/loop.py` are unchanged. `pyproject.toml` version is still `0.1.0`.

## Self-Check: PASSED

- Commits only through the guarded `apply_params`, and only when all gates pass
- Strict horizon refuse, including deep scenes and the 3.0 m boundary
- 0.5% is skipped (no apply, no reset, status unchanged), 1.5% commits, and exactly 1% commits
- Phase 20 default sampler unchanged; wizard Apply has no horizon gate; no YAML writes

---
*Phase: 21-gated-auto-commit-depthloop-status*
*Completed: 2026-10-08*
