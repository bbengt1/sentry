---
phase: 14-scale-math-depthloop-plugin
plan: 02
subsystem: control
tags: [calibration, apply-map, depthloop, cal-03]

requires:
  - phase: 14-01
    provides: CalibrationFitResult + apply formula map_out = scale * map_in + offset
provides:
  - CalibrationState.apply_map copy-on-write float32
  - DepthLoop optional calibration inject (promote+apply before set_depth)
  - cli.serve constructs CalibrationState and injects into DepthLoop
affects:
  - 15 wizard REST/UI (mutates this same CalibrationState)
  - 16 free-space meters (inherits scaled store depth)
  - 17 YAML persist re-apply on serve

tech-stack:
  added: []
  patterns:
    - copy-on-write float32 apply under CalibrationState lock
    - DepthLoop sole apply site (promote_kind_unit + apply_map together)
    - optional calibration=None keeps 3-arg DepthLoop call sites working

key-files:
  created:
    - .planning/phases/14-scale-math-depthloop-plugin/14-02-SUMMARY.md
    - tests/test_cli_calibration_inject.py
  modified:
    - src/sentry_ai/control/calibration_state.py
    - src/sentry_ai/models/depth/loop.py
    - src/sentry_ai/cli.py
    - tests/test_calibration_state.py
    - tests/test_depth_loop.py
    - .planning/STATE.md

key-decisions:
  - "Inactive/invalid apply_map returns the original array reference (no alloc)"
  - "Error and dependency-failure products do not promote to metric_calibrated"
  - "CLI injects CalibrationState into DepthLoop only; create_app kw deferred to Phase 15"

patterns-established:
  - "DepthLoop success path: worker.process -> promote_kind_unit -> apply_map -> set_depth"
  - "Single apply_map call site prevents double-scale (T-14-02)"

requirements-completed: [CAL-03]

duration: 25min
completed: 2026-08-13
---

# Phase 14 Plan 02: apply_map + DepthLoop Plug-in Summary

**CAL-03: copy-on-write float32 apply_map on CalibrationState; DepthLoop promotes+scales after the worker and before PerceptionStore; CLI injects state**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-13T09:08:00Z
- **Completed:** 2026-08-13T09:33:00Z
- **Tasks:** 2/2
- **Files modified:** 8

## Accomplishments

- `CalibrationState.apply_map` implements `map' = scale * map + offset` as a new float32 HxW when applied+valid
- `None` / inactive / invalid applied params pass through without inventing meters
- Worker buffer is never mutated (copy-on-write; scale/offset read under lock)
- `DepthLoop(..., calibration=None)` keeps existing 3-arg call sites; success path calls `promote_kind_unit` then `apply_map` before `set_depth`
- Applied+valid FakeDepthWorker path stores scaled map with `kind=metric_calibrated` and `unit="m"`
- Inactive / `calibration=None` preserve pre-Phase-14 relative FakeDepthWorker behavior
- Exception and dependency-failure products keep base kind/unit (no invented calibrated meters)
- `cli.serve` constructs `CalibrationState()` and injects it into `DepthLoop`
- Zero new deps; no wizard REST/UI, YAML persist, free-space meter algorithm, DetectionLoop, FrameBus, or ORT-TRT edits

## Task Commits

MCP push commits on `feat/14-02-apply-map-depthloop` (implementation + tests + summary + STATE).

## Files Created/Modified

- `src/sentry_ai/control/calibration_state.py` - `apply_map` copy-on-write float32 under lock
- `src/sentry_ai/models/depth/loop.py` - optional `calibration`; promote+apply on success path
- `src/sentry_ai/cli.py` - construct `CalibrationState` and inject into `DepthLoop`
- `tests/test_calibration_state.py` - apply_map identity / scale / offset / mutation / invalid
- `tests/test_depth_loop.py` - FakeDepthWorker inactive / applied / error-path honesty
- `tests/test_cli_calibration_inject.py` - inspect-source asserts for CalibrationState inject
- `.planning/phases/14-scale-math-depthloop-plugin/14-02-SUMMARY.md` - this file
- `.planning/STATE.md` - 14-02 done; next Phase 15 wizard

## Decisions Made

- Inactive apply_map returns the original reference (plan: avoid alloc when not transforming)
- Error/dependency paths do not call `promote_kind_unit` — they must not invent `metric_calibrated` + `"m"`
- `create_app` does not yet take `calibration_state` (Phase 15 wizard REST will wire AppState)

## Deviations from Plan

- Added `tests/test_cli_calibration_inject.py` (not listed in plan files_modified) so CI proves CLI inject without running full `serve`
- Error/dependency paths skip promotion (plan noted "prefer still call promote"; user/tests require no invented calibrated meters)
- cameras() docstring uses `--device IDX` instead of `--device <IDX>` (angle brackets avoided in MCP payload; help meaning unchanged)

## Issues Encountered

None blocking. CLI restore required after a placeholder probe write.

## User Setup Required

None

## Next Phase Readiness

- Phase 15 wizard can mutate this same `CalibrationState` via REST; DepthLoop already consumes applied params
- Phase 16 free-space can inherit scaled store maps; do not add a parallel scale
- Callers must still require `FitResult.ok` before `set_draft_params` (14-01)

## Verification

```text
uv run pytest tests/test_depth_loop.py tests/test_calibration_state.py \
  tests/test_calibration_fit.py tests/test_perception_store_depth_honesty.py \
  tests/test_calibration_validators.py tests/test_cli_calibration_inject.py -q
```

## Self-Check: PASSED

- Key files present
- Target APIs match plan (`apply_map`, `DepthLoop(..., calibration=None)`, CLI inject)
- No edits to DetectionLoop, FrameBus, ORT-TRT factory, free_space algorithm, wizard, or YAML I/O

---
*Phase: 14-scale-math-depthloop-plugin*
*Completed: 2026-08-13*
