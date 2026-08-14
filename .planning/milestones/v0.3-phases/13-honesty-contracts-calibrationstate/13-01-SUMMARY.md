---
phase: 13-honesty-contracts-calibrationstate
plan: 01
subsystem: schemas
tags: [depth-kind, honesty-contracts, calibration, pydantic, perception-store]

requires:
  - phase: 04-depth
    provides: DepthKind enum, kind_for_mode, DepthPayload relative honesty
  - phase: 05-free-space
    provides: FreeSpacePayload wire model
provides:
  - assert_depth_kind_unit full kind↔unit matrix
  - assert_free_space_units (meters only when metric_calibrated)
  - promote_kind_unit pure promotion gate
  - PerceptionStore.set_depth honesty gate
  - kind_for_mode never-calibrated test guard
affects:
  - 13-02 CalibrationState
  - 14 DepthLoop post-process scale / promote
  - 15 calibration wizard REST/UI
  - 16 free-space metric path

tech-stack:
  added: []
  patterns:
    - pure ValueError asserts in validators.py called from Pydantic model_validators and store mutators
    - promote only when applied and valid both True

key-files:
  created:
    - tests/test_calibration_validators.py
    - tests/test_perception_store_depth_honesty.py
  modified:
    - src/sentry_ai/schemas/validators.py
    - src/sentry_ai/schemas/perception.py
    - src/sentry_ai/state/perception_store.py
    - tests/test_schemas_depth_kind.py
    - tests/test_depth_mapping.py

key-decisions:
  - "relative_depth_forbids_unit delegates to assert_depth_kind_unit for single matrix"
  - "FreeSpacePayload allows metric_calibrated + ordinal until Phase 16"
  - "kind_for_mode production mapping left unchanged; never-calibrated is test-only"

patterns-established:
  - "Honesty asserts live in validators.py; wire models and store call them"
  - "promote_kind_unit is pure and ready for CalibrationState wrapping"

requirements-completed: [CAL-04, CAL-05]

duration: 3min
completed: 2026-08-11
---

# Phase 13 Plan 01: Honesty Contracts Summary

**Full kind↔unit honesty matrix on DepthPayload/FreeSpacePayload/PerceptionStore plus pure promote_kind_unit for CalibrationState**

## Performance

- **Duration:** 3 min
- **Started:** 2026-08-11T13:58:48Z
- **Completed:** 2026-08-11T14:01:30Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- `assert_depth_kind_unit` enforces relative→None, estimated/calibrated→`"m"`
- `assert_free_space_units` allows meters only when `depth_kind=metric_calibrated`
- `promote_kind_unit` returns `(METRIC_CALIBRATED, "m")` only when applied and valid
- `PerceptionStore.set_depth` rejects dishonest pairs before any product write
- `kind_for_mode` never returns calibrated (test guard; production mapping unchanged)

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 RED: Kind/unit + free-space honesty tests** - `7aef5bf` (test)
2. **Task 1 GREEN: validators + wire models** - `b9f1578` (feat)
3. **Task 2 RED: store honesty + never-calibrated guards** - `5fff0a6` (test)
4. **Task 2 GREEN: PerceptionStore.set_depth gate** - `a7d41df` (feat)

**Plan metadata:** `3205006` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/schemas/validators.py` — `assert_depth_kind_unit`, `assert_free_space_units`, `promote_kind_unit`; `relative_depth_forbids_unit` delegates
- `src/sentry_ai/schemas/perception.py` — DepthPayload `kind_unit_honesty`; FreeSpacePayload `free_space_units_honesty`
- `src/sentry_ai/state/perception_store.py` — `assert_depth_kind_unit` at start of `set_depth`
- `tests/test_calibration_validators.py` — pure helper + FreeSpacePayload matrix + promote truth table
- `tests/test_schemas_depth_kind.py` — calibrated/estimated unit=None rejection
- `tests/test_perception_store_depth_honesty.py` — store reject without partial write
- `tests/test_depth_mapping.py` — `test_kind_for_mode_never_calibrated`

## Decisions Made

- Implemented `relative_depth_forbids_unit` as a thin wrapper over `assert_depth_kind_unit` so FOUND-03 callers keep working while the full matrix is single-sourced
- Left production `kind_for_mode` unchanged; calibrated promotion is exclusively `promote_kind_unit` / future CalibrationState
- Free-space `metric_calibrated` + `units="ordinal"` remains allowed (Phase 16 owns real meter free-space path)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 13-02 can wrap `promote_kind_unit` in `CalibrationState`
- DepthLoop (Phase 14) can call store/promote with honest pairs only
- Zero new pip packages; no DepthLoop/wizard/YAML changes in this plan

## Verification

```text
uv run pytest tests/test_calibration_validators.py tests/test_schemas_depth_kind.py \
  tests/test_perception_store_depth_honesty.py tests/test_depth_mapping.py \
  tests/test_depth_kind_honesty.py tests/test_free_space_bands.py \
  tests/test_schemas_perception.py -q
# 85 passed
```

## Self-Check: PASSED

- All key files present
- Commits `7aef5bf`, `b9f1578`, `5fff0a6`, `a7d41df` exist
- `promote_kind_unit` importable
- No edits to DepthLoop, free_space algorithm, routes, or index.html

---
*Phase: 13-honesty-contracts-calibrationstate*
*Completed: 2026-08-11*
