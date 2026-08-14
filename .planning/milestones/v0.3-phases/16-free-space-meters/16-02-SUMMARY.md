---
phase: 16-free-space-meters
plan: 02
subsystem: spatial
tags: [free-space, loop, smoother, fs-03, fs-01]

requires:
  - phase: 16-01
    provides: compute_free_space METRIC_CALIBRATED branch with absolute 1.5/3.0 m cuts
provides:
  - FreeSpaceLoop consume kind+map; never re-scale; units passthrough
  - reset_smoother on kind apply↔clear + OccupancySmoother.reset
  - assemble._units_for_depth_kind METRIC_CALIBRATED → m
  - FreeSpaceProduct.units + set_free_space
  - assert_free_space_units calibrated must be m (Phase 13 grace ended)
  - optional ObstacleCue.distance_m (mean blob meters when calibrated)
affects:
  - Phase 17 persist/re-apply (next)

tech-stack:
  added: []
  patterns:
    - consume DepthLoop scaled map + kind; never apply_map in free-space
    - loop-owned EMA reset on kind != _last_kind
    - store units win on assemble; helper fallback
    - belt-and-suspenders POST apply/clear reset_smoother (not cancel)

key-files:
  created:
    - .planning/phases/16-free-space-meters/16-02-SUMMARY.md
    - tests/test_api_calibration_smoother.py
  modified:
    - src/sentry_ai/spatial/free_space.py
    - src/sentry_ai/spatial/loop.py
    - src/sentry_ai/spatial/smoothing.py
    - src/sentry_ai/state/perception_store.py
    - src/sentry_ai/api/assemble.py
    - src/sentry_ai/schemas/perception.py
    - src/sentry_ai/schemas/validators.py
    - src/sentry_ai/api/routes_calibration.py
    - tests/test_free_space_loop.py
    - tests/test_free_space_smoothing.py
    - tests/test_assemble_perception_frame.py
    - tests/test_calibration_validators.py
    - tests/test_free_space_bands.py
    - tests/test_schemas_perception.py
    - .planning/STATE.md

key-decisions:
  - "Loop never re-scales; kind=depth.kind into compute_free_space"
  - "FreeSpaceProduct.units copied through set/snapshot; assemble prefers store units"
  - "reset_smoother on kind != _last_kind; safe without cuts lock"
  - "POST apply/clear call reset_smoother when loop present; cancel does not"
  - "calibrated must emit units=m; Phase 13 calibrated+ordinal grace removed"
  - "distance_m = mean finite depth in blob, calibrated only; nearness stays 0..1"

patterns-established:
  - "Kind-change detect is loop-owned (CalibrationState has no listeners)"
  - "Error products may stay units=ordinal; wire skips error products"

requirements-completed: [FS-03, FS-01]

duration: 20min
completed: 2026-08-13
---

# Phase 16 Plan 02: Free-Space Loop Wire + Smoother Reset Summary

**FS-03 + FS-01 on the wire: FreeSpaceLoop consumes DepthLoop kind+scaled map, publishes `units="m"` only when calibrated, resets occupancy EMA on apply↔clear, and optionally fills `distance_m`. Phase 13 calibrated+ordinal grace is gone.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-08-13T23:57:00Z
- **Completed:** 2026-08-14T00:04:00Z
- **Tasks:** 1/1
- **Files modified:** 18 (+ this summary)

## Accomplishments

- `FreeSpaceLoop` tracks `_last_kind`, calls `reset_smoother()` on kind change, passes `kind=depth.kind` and `units=result.units` into the store
- `FreeSpaceLoop.reset_smoother()` is public; `OccupancySmoother.reset()` is documented as safe anytime
- `FreeSpaceProduct.units` + `set_free_space(..., units=)` + snapshot copy
- `assemble._units_for_depth_kind(METRIC_CALIBRATED) → "m"`; else `"ordinal"`; store units preferred
- `assert_free_space_units`: calibrated must be `"m"`; relative/estimated still forbid `"m"`
- Optional `ObstacleCue.distance_m` (spatial dataclass + wire schema); mean finite blob depth when calibrated
- Belt-and-suspenders: POST apply/clear call `reset_smoother` when `app.state.free_space_loop` has it; cancel does not
- Zero new pip deps; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` frozen; no YAML; no FSD

## Task Commits

MCP push commits on `feat/16-02-free-space-loop-wire`.

## Files Created/Modified

- `src/sentry_ai/spatial/free_space.py` - `ObstacleCue.distance_m`; `_extract_obstacles` mean blob meters
- `src/sentry_ai/spatial/loop.py` - `reset_smoother`, `_last_kind`, units passthrough, no re-scale
- `src/sentry_ai/spatial/smoothing.py` - reset docstring (apply↔clear)
- `src/sentry_ai/state/perception_store.py` - `FreeSpaceProduct.units`
- `src/sentry_ai/api/assemble.py` - helper flip + `distance_m` copy
- `src/sentry_ai/schemas/perception.py` - optional wire `distance_m`; extra=forbid
- `src/sentry_ai/schemas/validators.py` - calibrated must emit `"m"`
- `src/sentry_ai/api/routes_calibration.py` - apply/clear smoother reset
- tests listed above + `.planning/STATE.md`

## Decisions Made

- `units` field sits after `obstacle_count` so the dataclass keeps required-then-default order
- Store does **not** call `assert_free_space_units` (error products may stay ordinal)
- `_obstacles_for_store` includes `distance_m` only when not None (relative dicts stay key-absent)
- Belt-and-suspenders included as plan discretion; required path remains loop kind-detect

## Deviations from Plan

- Updated `tests/test_schemas_perception.py` (not in the plan file list) because SPACE-02 still asserted `distance_m` was forbidden on the wire schema
- `FreeSpaceProduct.units` placed after `obstacle_count` (dataclass default-order), not immediately after `depth_kind`
- Belt-and-suspenders apply/clear test lives in new `tests/test_api_calibration_smoother.py` rather than appending to the existing 23KB `test_api_calibration.py`

## Issues Encountered

- Dataclass `TypeError: non-default argument 'obstacle_count' follows default argument` when `units` was inserted before `obstacle_count` — fixed by field reorder

## User Setup Required

None

## Next Phase Readiness

- Phase 16 complete. Phase 17 can persist applied calibration per `camera_id` with fingerprint refuse and re-apply on `sentry serve`
- Do not add YAML I/O, wizard REST redesign, or FSD/motor fields here

## Verification

```text
uv run pytest tests/test_free_space_bands.py tests/test_free_space_loop.py \
  tests/test_free_space_smoothing.py tests/test_calibration_validators.py \
  tests/test_assemble_perception_frame.py tests/test_api_calibration.py \
  tests/test_api_calibration_smoother.py tests/test_depth_loop.py -q
uv run pytest -q
uv run ruff check src tests
```

Box: 126 targeted passed; full suite 735 passed, 1 skipped; ruff clean.

## Self-Check: PASSED

- Key files present
- Target APIs match plan (`reset_smoother`, `_units_for_depth_kind`, `distance_m`, tightened validator)
- No edits to DetectionLoop, FrameBus, ORT-TRT, `kind_for_mode`, YAML, or wizard REST redesign
- No `apply_map` in `spatial/loop.py`

---
*Phase: 16-free-space-meters*
*Completed: 2026-08-13*
