---
phase: 20-online-sample-fit-reject
plan: 02
subsystem: control
tags: [calibration, online, fit, onl-03, onl-04]

requires:
  - phase: 20-01
    provides: OnlineSampler window, consent anchors, replace_draft_samples
provides:
  - fit_scale_median on a full window
  - set_draft_params only when ok is True
  - clear_draft_params when ok is False
affects:
  - Phase 21 auto-commit (still must not treat draft params as applied)

tech-stack:
  added: []
  patterns:
    - Full window fits with the shipped scale-median gates
    - ok=True stages draft; snapshot.scale stays the applied scale
    - ok=False clears draft params and leaves samples and applied scale

key-files:
  created:
    - .planning/phases/20-online-sample-fit-reject/20-02-SUMMARY.md
  modified:
    - src/sentry_ai/control/online_sampler.py
    - src/sentry_ai/control/calibration_state.py
    - tests/test_online_sampler.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Fit only when the deque length reaches window_n after an accept"
  - "Draft fingerprint is a copy of the applied fingerprint; created_at is time.time()"
  - "A later fit_rejected clears params staged by an earlier draft_staged"
  - "In-range scale 1000 may stage and must not replace applied scale. Horizon refuse stays a Phase 21 question"

patterns-established:
  - "Reject is clear_draft_params, not Cancel (clear_draft) and not Clear"
  - "online_status stays online_draft through both outcomes"

requirements-completed: [ONL-03, ONL-04]

duration: session
completed: 2026-10-05
---

# Phase 20 Plan 02: Draft fit and reject

**ONL-04 and the fit half of ONL-03: a full window runs `fit_scale_median`. A pass stages draft params. A failure clears those params and leaves the consented scale applied.**

## Performance

- **Duration:** one session
- **Completed:** 2026-10-05
- **Tasks:** 2/2
- **Files modified:** sampler, state, tests, planning docs

## Accomplishments

- `clear_draft_params` drops `_draft_params` only
- `consider` calls `fit_scale_median(..., method="known_distance")` once the window holds `window_n` frames
- `ok=True` builds `CalibrationParams` from the fit plus a copy of the applied fingerprint and calls `set_draft_params`
- `ok=False` calls `clear_draft_params`. Samples, anchors, applied scale, and the online flag stay
- Shorter windows still return `window_short` and do not fit
- The 9th consistent frame refits the last 8 and stays `draft_staged`
- No edits to `spatial/calibration.py`, DepthLoop, routes, or `pyproject.toml`

## Task Commits

1. **RED** — `test(20-02): failing draft-staged and fit-rejected tests`
2. **GREEN** — implementation commit on `cursor/phase-20-02-fit-reject-b90b`

## Files Created/Modified

- `src/sentry_ai/control/online_sampler.py` — fit branch `draft_staged` / `fit_rejected`
- `src/sentry_ai/control/calibration_state.py` — `clear_draft_params`
- `tests/test_online_sampler.py` — accept, residual reject, absurd reject, in-range draft, slide, yaml

## Decisions Made

- Did not add a horizon gate for in-range scales. Scale 1000 stages draft and leaves `snapshot.scale` on the consented value. Whether Phase 21 should refuse that before auto-commit is still Brent's open question
- Did not assign `auto_committed` or `rejected`

## Deviations from Plan

- `test_eighth_accept_stays_window_short_without_fit` now expects `draft_staged` and keeps the applied scale at 4.0. A full consistent window fits. Partial windows still assert `window_short` and `fit_ok is None`
- `rg "auto_committed|rejected"` matches the required reason token `fit_rejected` once. The module does not contain `auto_committed` and does not call `set_online_status`

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- Phase 20 requirements ONL-03 and ONL-04 are met
- Phase 21 still owns `apply_params`, the five-conjunct gate, smoother reset, and the status enum writes
- Restart support for anchors stays out of scope

## Verification

```text
uv run ruff check src tests
uv run pytest -q
```

915 passed, 1 skipped. `spatial/calibration.py` and `models/depth/loop.py` are unchanged. `pyproject.toml` version is still `0.1.0`.

## Self-Check: PASSED

- Passed fit is draft only
- Failed fit does not change the applied scale
- In-range scale 1000 does not go live
- No auto-commit and no hot-path hook

---
*Phase: 20-online-sample-fit-reject*
*Completed: 2026-10-05*
