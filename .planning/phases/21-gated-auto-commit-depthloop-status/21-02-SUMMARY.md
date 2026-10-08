---
phase: 21-gated-auto-commit-depthloop-status
plan: 02
subsystem: depth-loop
tags: [calibration, online, depthloop, serve, smoother, onl-05, onl-07]

requires:
  - phase: 21-01
    provides: OnlineSampler(auto_commit, on_auto_commit), consider(live_fingerprint=)
provides:
  - DepthLoop online_sampler kwarg + set_online_sampler + contained _consider_online
  - serve wiring via cli._attach_online_sampler (auto_commit=True, on_auto_commit=reset_smoother)
affects:
  - Phase 22 (persist policy, operator docs, synthetic online gate matrix)

tech-stack:
  added: []
  patterns:
    - Raw map + live fingerprint + time.monotonic() reach the sampler after refuse_if_mismatch, before promote/apply
    - Sampler errors logged once per distinct message (bounded) and never stop the frame
    - Smoother reset only through the commit callback

key-files:
  created:
    - tests/test_depth_loop_online.py
    - .planning/phases/21-gated-auto-commit-depthloop-status/21-02-SUMMARY.md
  modified:
    - src/sentry_ai/models/depth/loop.py
    - src/sentry_ai/cli.py
    - .planning/STATE.md
    - .planning/ROADMAP.md
    - .planning/REQUIREMENTS.md

key-decisions:
  - "Hook inside `if depth_map is not None`, right after refuse_if_mismatch; promote_kind_unit / apply_map / set_depth lines unchanged"
  - "_attach_online_sampler imports OnlineSampler lazily and is called right after FreeSpaceLoop(store)"
  - "Status uses the existing /api/status calibration_online_status field; no route or field added"

patterns-established:
  - "A commit on frame N is visible in frame N's stored depth"

requirements-completed: [ONL-05, ONL-07, ONL-09]

duration: session
completed: 2026-10-08
---

# Phase 21 Plan 02: DepthLoop hook, serve wiring, status

**ONL-07, and the runtime half of ONL-05. Live frames now drive the 21-01 gated auto-commit. DepthLoop is still the only `apply_map` site. A commit resets the free-space smoother; a refusal or `within_deadband` skip does not. The decision shows on the existing `/api/status` field. Phase 21 is complete.**

## Performance

- **Duration:** one session
- **Completed:** 2026-10-08
- **Tasks:** 2/2
- **Files modified:** DepthLoop, cli, one new test module, planning docs

## Accomplishments

- `DepthLoop(..., online_sampler=None)`, `set_online_sampler()` (under the loop lock), and `_consider_online()`.
  - Passes the worker's pre-apply map, `frame_id`, `time.monotonic()`, and the live fingerprint.
  - Catches every `Exception` and logs each distinct message once. The log set is capped at 32 messages.
- In `_run`, the hook runs after `refuse_if_mismatch` and before the unchanged `promote_kind_unit` → `apply_map` → `set_depth`.
- `cli._attach_online_sampler(depth_loop, calibration_state, free_space_loop)` attaches `OnlineSampler(auto_commit=True, on_auto_commit=free_space_loop.reset_smoother)`. It's a no-op without a depth loop or calibration state, and `serve` calls it right after `FreeSpaceLoop(store)`.
- Online stays default off (Phase 19): the sampler returns `online_off` until the maker enables it.
- No edits to `control/`, `spatial/`, `schemas/`, `config/`, `api/`, `calibration_persist.py`, or `pyproject.toml`.

## Task Commits

1. **RED**: `test(21-02): failing DepthLoop online hook, serve wiring, and status tests`. 10 failed on main: no `online_sampler` kwarg, `set_online_sampler`, or `_attach_online_sampler`. 3 passed:
   - the status-plane characterization test, since the field already exists;
   - the no-sampler regression test;
   - the sole-site guard.
2. **GREEN**: `feat(21-02): DepthLoop online hook and serve auto-commit wiring`

## Files Created/Modified

- `src/sentry_ai/models/depth/loop.py`: hook, setter, contained call
- `src/sentry_ai/cli.py`: `_attach_online_sampler` and its call in `serve`
- `tests/test_depth_loop_online.py`: 13 cases (hook inputs and order, commit on frame N, contained exception, mismatch, wiring, reset only on commit, status plane, sole `apply_map`)

## Decisions Made

- The tests inject the clock by wrapping the real sampler and replacing `now_s` with `frame_id`. The loop itself always passes `time.monotonic()`. Monkeypatching `time.monotonic` would also break the test wait helper.
- The error-log set is capped at 32 entries (security review, hardening).

## Deviations from Plan

- The `/api/status` test passes on main. The field and the 21-01 status writes already exist, so it is a characterization test, not a RED test.
- I added a bounded error-log set. The plan only said "log once per distinct message".

## Issues Encountered

- **Follow-up, not fixed here:** sources reset `frame_id` to 0 on reopen (`opencv_source.open`, AVFoundation warm-up). The sampler's Phase 20 strictly-increasing-`frame_id` rule then returns `frame_not_advanced` after a capture reconnect, until the new ids pass the old high-water mark. That fails closed (no commit), but online refine can stall after a reconnect. Changing it would reopen a Phase 20 lock, so it is raised for Brent.

## User Setup Required

None

## Next Phase Readiness

- ONL-05, ONL-07, and ONL-09 are met. Phase 21 is complete.
- Phase 22 owns the persist policy docs, operator docs, and the synthetic online gate matrix.
- Restart support stays out of scope.

## Verification

```text
uv run ruff check src tests
uv run pytest -q
uv run sentry health
```

956 passed, 1 skipped. The only `apply_map(` caller under `src/` is `models/depth/loop.py` (AST test). `pyproject.toml` version is still `0.1.0`.

## Self-Check: PASSED

- Raw map and live fingerprint reach the sampler before `apply_map`
- A sampler exception never stops a frame from publishing
- Smoother resets on commit only
- Mismatch is still refused first; no YAML; no new route or field

---
*Phase: 21-gated-auto-commit-depthloop-status*
*Completed: 2026-10-08*
