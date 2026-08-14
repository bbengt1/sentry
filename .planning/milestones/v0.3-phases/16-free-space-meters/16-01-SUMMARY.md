---
phase: 16-free-space-meters
plan: 01
subsystem: spatial
tags: [free-space, metric-bands, fs-01, fs-02]

requires:
  - phase: 14-02
    provides: DepthLoop-scaled maps + metric_calibrated kind (consume only)
provides:
  - compute_free_space METRIC_CALIBRATED branch with absolute 1.5/3.0 m cuts
  - DEFAULT_METRIC_NEAR_CUT_M / DEFAULT_METRIC_MID_CUT_M + _meters_to_nearness
  - units="m" only when meter cuts ran (FS-01 / FS-02)
affects:
  - 16-02 FreeSpaceLoop consume, smoother reset, assemble/validator/store, distance_m

tech-stack:
  added: []
  patterns:
    - two-mode compute_free_space (ordinal percentile vs absolute meters)
    - pin higher_is_farther on calibrated path; never min-max meters
    - consume already-scaled maps; never apply_map in free-space
    - error/invalid-cut results stay units="ordinal"

key-files:
  created:
    - .planning/phases/16-free-space-meters/16-01-SUMMARY.md
  modified:
    - src/sentry_ai/spatial/free_space.py
    - tests/test_free_space_bands.py
    - .planning/STATE.md

key-decisions:
  - "units=m iff kind=METRIC_CALIBRATED and absolute meter cuts ran"
  - "Default metric cuts 1.5 m near / 3.0 m mid; ordinal 0.72/0.45 ignored when calibrated"
  - "nearness_0_1 = clip((3.0 - d) / 3.0, 0, 1) constant horizon"
  - "RELATIVE and METRIC_ESTIMATED stay ordinal; metric_estimated is not calibrated"
  - "No distance_m / loop / assemble / validator / YAML in 16-01"

patterns-established:
  - "Calibrated occupancy seed = finite ROI pixels with d < metric_near_cut_m"
  - "Band denominator = finite ROI pixels (non-finite excluded)"

requirements-completed: [FS-01, FS-02]

duration: 25min
completed: 2026-08-13
---

# Phase 16 Plan 01: Metric Free-Space Compute Path Summary

**FS-01/FS-02: pure `compute_free_space` metric-band path. `units="m"` only when calibrated via absolute 1.5/3.0 m cuts on an already-scaled map. Relative and `metric_estimated` stay ordinal percentile nearness. No loop/wire/validator/`distance_m` (16-02).**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-13T23:33:00Z
- **Completed:** 2026-08-13T23:45:00Z
- **Tasks:** 1/1
- **Files modified:** 3 (+ this summary)

## Accomplishments

- `DEFAULT_METRIC_NEAR_CUT_M = 1.5` / `DEFAULT_METRIC_MID_CUT_M = 3.0` exported from `free_space.py`
- `_meters_to_nearness`: fixed 3.0 m horizon, finite-only; not per-frame min-max
- `compute_free_space(..., metric_near_cut_m=, metric_mid_cut_m=)`: calibrated branch pins `higher_is_farther`, never calls `depth_to_nearness`, occupied seed = finite ROI `d < 1.5 m`
- Invalid `metric_near_cut_m >= metric_mid_cut_m` and exception paths keep `units="ordinal"`
- Honesty tests: 0.5 m blob -> `"m"`; 4-5 m hallway far in metric / near in ordinal (FS-02); uniform 2.0 m stays mid; ordinal sliders ignored; polarity pin; estimated still ordinal
- Zero new pip deps; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` frozen; no YAML; no FSD claims

## Task Commits

MCP push commits on `feat/16-01-free-space-metric-compute`.

## Files Created/Modified

- `src/sentry_ai/spatial/free_space.py` - metric band branch + constants + `_meters_to_nearness`
- `tests/test_free_space_bands.py` - FS-01/FS-02 honesty matrix including 4-5 m smoking-gun
- `.planning/STATE.md` - 16-01 done; next 16-02

## Decisions Made

- Meter->nearness uses `DEFAULT_METRIC_MID_CUT_M` as a **constant** horizon
- Occupied seed on metric path is near-meter pixels (then existing morphology/smoother)
- `occupied_mask` override still honored on both paths
- `ObstacleCue.distance_m` omitted (16-02); existing no-`distance_m` tests stay green
- Validator `metric_calibrated` + `ordinal` grace left in place until assemble flips (16-02)

## Deviations from Plan

- Extra tests beyond the plan bullets: invalid metric cuts, occupied-mask override, non-finite band denominator, ordinal path ignores metric kwargs, source-level check that calibrated branch does not call `depth_to_nearness`
- Empty ROI on a valid calibrated call now returns `units="m"` (metric path ran; no pixels) rather than always `"ordinal"`
- Did not re-export the new constants from `spatial/__init__.py` (plan `__all__` is `free_space.py` only)

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- 16-02 can wire `FreeSpaceLoop` to pass `depth.kind` / `result.units`, `reset_smoother` on kind change, assemble `_units_for_depth_kind` -> `"m"`, store `units`, tighten `assert_free_space_units`, optional `distance_m`
- Do not flip assemble/validator until this compute path is on main (or the same PR wave)

## Verification

```text
uv run pytest tests/test_free_space_bands.py tests/test_free_space_loop.py \
  tests/test_free_space_smoothing.py tests/test_calibration_validators.py \
  tests/test_assemble_perception_frame.py -q
uv run pytest -q
uv run ruff check src tests
```

Box: 78 targeted passed; full suite 718 passed, 1 skipped; ruff clean.

## Self-Check: PASSED

- Key files present
- Target APIs match plan (`DEFAULT_METRIC_*`, `_meters_to_nearness`, `compute_free_space` kwargs)
- No edits to DetectionLoop, FrameBus, ORT-TRT, `kind_for_mode`, loop/assemble/validators/store, YAML, or wizard REST

---
*Phase: 16-free-space-meters*
*Completed: 2026-08-13*
