---
phase: 19-online-consent-honesty-state
plan: 01
subsystem: control
tags: [calibration, online, honesty, onl-01, onl-02]

requires:
  - phase: 18
    provides: CalibrationState apply / apply_params / try_reapply + persist
provides:
  - CalibrationState.is_online / set_online session flag (default off)
  - CalibrationSnapshot.online
  - first-scale lock (online_requires_applied)
affects:
  - Phase 19-02 Cancel/Clear/disable matrix + four-way online_status + REST POST

tech-stack:
  added: []
  patterns:
    - Session flag on CalibrationState (not a new OnlineRecalState)
    - set_online(True) refused unless already applied
    - apply / apply_params / try_reapply do not flip online on
    - clear_applied forces online off; set_online(False) does not clear applied

key-files:
  created:
    - .planning/phases/19-online-consent-honesty-state/19-01-SUMMARY.md
  modified:
    - src/sentry_ai/control/calibration_state.py
    - src/sentry_ai/schemas/calibration.py
    - tests/test_calibration_state.py
    - tests/test_calibration_persist.py
    - .planning/STATE.md

key-decisions:
  - "is_online() / set_online(enabled) -> CalibrationSnapshot; _online_enabled default False"
  - "ValueError message is exactly online_requires_applied (REST 409 maps this in 19-02)"
  - "No _online_status on snapshot yet; 19-02 owns the four-way enum"
  - "Flag is session-only — no YAML / env / CLI"

patterns-established:
  - "Enable-while-unapplied is refuse, not idle-on"
  - "Disable-online ≠ Clear (unit-level; YAML/REST matrix is 19-02)"

requirements-completed: [ONL-02]
requirements-partial: [ONL-01]

duration: 25min
completed: 2026-08-17
---

# Phase 19 Plan 01: Online Consent Flag + First-Scale Lock

**ONL-01 (flag half) + ONL-02: `CalibrationState()` boots online-off. `set_online(True)` cannot invent the first metric scale. First `metric_calibrated` still requires `apply()` or matching persist `try_reapply`. Zero new packages. No REST toggle (19-02). No sampler / auto-commit / DepthLoop edits.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-17T10:09:00Z
- **Completed:** 2026-08-17T10:35:00Z
- **Tasks:** 2/2
- **Files modified:** 5 (+ this summary)

## Accomplishments

- `CalibrationSnapshot.online: bool = False` (`extra=forbid` unchanged)
- `CalibrationState._online_enabled` default False; `is_online()` / `set_online(enabled)`
- `set_online(True)` while unapplied raises `ValueError("online_requires_applied")`
- `apply()` / `apply_params()` / matching `try_reapply` leave online off
- `clear_applied` forces online off; `set_online(False)` leaves applied + scale
- Synthetic ONL-01/ONL-02 tests on existing modules
- No routes / DepthLoop / DetectionLoop / FrameBus / pyproject edits

## Task Commits

MCP push commits on `feat/19-01-online-consent-flag`.

## Files Created/Modified

- `src/sentry_ai/schemas/calibration.py` — `CalibrationSnapshot.online`
- `src/sentry_ai/control/calibration_state.py` — `is_online` / `set_online` + clear_applied reset
- `tests/test_calibration_state.py` — default-off, refuse-unapplied, apply-does-not-enable, disable-does-not-clear
- `tests/test_calibration_persist.py` — try_reapply match leaves online off
- `.planning/STATE.md` — 19-01 done; next 19-02

## Decisions Made

- API mirrors persist helpers: `is_online()` + `set_online(enabled) -> snapshot`
- Did not add internal `_online_status` yet (19-02 snapshot + REST job)
- ONL-01 status half (`online_status` four-way + POST) stays 19-02

## Deviations from Plan

- Combined RED+GREEN in one implementation PR (tests + product together). Plan allowed TDD locally; MCP landing is one branch.

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- 19-01 ONL-02 complete; ONL-01 flag half complete
- 19-02: Cancel/Clear/disable-online matrix + four-way `online_status` + thin `POST /api/depth/calibration/online`

## Verification

```text
uv run pytest tests/test_calibration_state.py tests/test_calibration_persist.py \
  tests/test_calibration_fit.py tests/test_api_calibration.py \
  tests/test_cli_calibration_inject.py -q --tb=short
```

## Self-Check: PASSED

- Target APIs match plan (`is_online` / `set_online` / `snapshot.online`)
- `apply_map` formula unchanged (`scale * map + offset`)
- No DetectionLoop / FrameBus / ORT-TRT / kind_for_mode / routes / UI edits
- No pyproject version bump
- No sampler / auto-commit / YAML online key

---
*Phase: 19-online-consent-honesty-state*
*Completed: 2026-08-17*
