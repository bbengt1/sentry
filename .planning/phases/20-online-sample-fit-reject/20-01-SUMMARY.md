---
phase: 20-online-sample-fit-reject
plan: 01
subsystem: control
tags: [calibration, online, sampler, onl-03]

requires:
  - phase: 19
    provides: online flag, first-scale refuse, Cancel/Clear/disable-online, four-way online_status
provides:
  - Consent anchors captured only on successful wizard apply()
  - OnlineSampler.consider throttled draft window (N=8, 1.0s, strictly increasing frame_id)
  - replace_draft_samples on CalibrationState
affects:
  - Phase 20-02 fit/reject (replaces window_short once the window is full)

tech-stack:
  added: []
  patterns:
    - Session ConsentAnchor tuple on CalibrationState, not a snapshot field and not YAML
    - OnlineSampler mutates draft samples only; it does not fit or commit
    - map_space raw by default; applied inverts (map - offset) / scale outside the state lock

key-files:
  created:
    - src/sentry_ai/control/online_sampler.py
    - tests/test_online_sampler.py
    - .planning/phases/20-online-sample-fit-reject/20-01-SUMMARY.md
  modified:
    - src/sentry_ai/control/calibration_state.py
    - tests/test_calibration_state.py
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Anchors only after wizard apply() in this process; try_reapply stays idle (Brent 2026-10-05)"
  - "20-01 never fits: the 8th accept still returns window_short and fit_ok is None"
  - "missing frame_id reason token is missing_frame_id"
  - "Cancel clears the sampler deque when draft samples are empty so the next accept cannot restore them"

patterns-established:
  - "Draft window lives in _draft_samples (note=online); Cancel already drops it"
  - "Clear drops anchors with applied; disable-online drops neither"

requirements-completed: []
requirements-partial: [ONL-03]

duration: session
completed: 2026-10-05
---

# Phase 20 Plan 01: Throttled draft window and consent anchors

**ONL-03 draft half: `OnlineSampler.consider` writes a throttled window of consented observations into draft samples only. No fit, no auto-commit, no DepthLoop hook, no new route.**

## Performance

- **Duration:** one session
- **Completed:** 2026-10-05
- **Tasks:** 2/2
- **Files modified:** product + tests + this summary

## Accomplishments

- `ConsentAnchor` is copied from wizard draft samples only after `apply()` passes validity, and before those samples are cleared
- `apply()` still does not enable online. `apply_params` does not read or write anchors. A raised `apply()` leaves the previous anchors in place
- `clear_applied` clears anchors and forces online off. `clear_draft` drops the window only. `set_online(False)` drops neither applied, anchors, nor existing draft
- `OnlineSampler` defaults are `ONLINE_WINDOW_N=8` and `ONLINE_MIN_INTERVAL_S=1.0`. Tests inject `now_s` (no sleep)
- Accepted frames become `CalibrationSample` rows with `note="online"`. `has_draft_params` stays false. `snapshot.scale` stays the applied scale
- `map_space="applied"` stores pre-apply `observed_raw`. `map_space="raw"` does not invert
- Not exported from `control/__init__.py`. `pyproject` version stays `0.1.0`

## Task Commits

1. **RED** — `test(20-01): failing draft-window and consent-anchor tests`
2. **GREEN** — implementation commit on `cursor/phase-20-01-online-sampler-b90b`

## Files Created/Modified

- `src/sentry_ai/control/online_sampler.py` — `consider` through `window_short`
- `src/sentry_ai/control/calibration_state.py` — anchors, `get_consent_anchors`, `replace_draft_samples`
- `tests/test_online_sampler.py` — throttle, honesty matrix, pre-apply read
- `tests/test_calibration_state.py` — anchor capture on apply / apply_params / clear_applied / failed apply

## Decisions Made

- Brent accepted idle-after-restart. No anchor persistence in this plan
- Reason token for a missing `frame_id` is `missing_frame_id` (RESEARCH named the check, not the token)
- A non-finite offset on an applied invert is `bad_applied_scale`, same as a non-finite or non-positive scale
- When Cancel has emptied draft samples, the sampler drops its deque before the next accept

## Deviations from Plan

- Extra tests beyond the behavior list: bbox median, `missing_frame_id`, `bad_applied_scale`, YAML bytes unchanged, and Cancel followed by one new frame (count stays 1). No fit, route, YAML key, or DepthLoop change
- `not_applied` is covered by setting the private flag after `set_online(True)` still raises `online_requires_applied`. The public unapplied path still returns `online_off`

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- 20-02 can replace the full-window `window_short` return with `fit_scale_median` / `set_draft_params` / `clear_draft_params`
- Do not assign `auto_committed` or `rejected`. Do not call `apply` / `apply_params` / `apply_map` from the sampler

## Verification

```text
uv run ruff check src tests
uv run pytest -q
```

907 passed, 1 skipped. `rg` of `online_sampler.py` has no `fit_scale_median`, `apply_params`, or `apply_map`. `models/depth/loop.py` does not reference the sampler. `pyproject.toml` version is still `0.1.0`.

## Self-Check: PASSED

- Anchors only on successful `apply()`; `apply_params` does not invent them
- Eighth accept is `window_short` with `fit_ok is None`
- Cancel ≠ Clear ≠ disable-online
- No new dependency, route, snapshot field, or YAML key

---
*Phase: 20-online-sample-fit-reject*
*Completed: 2026-10-05*
