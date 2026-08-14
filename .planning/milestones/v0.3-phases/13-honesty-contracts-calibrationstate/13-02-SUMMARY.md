---
phase: 13-honesty-contracts-calibrationstate
plan: 02
subsystem: control
tags: [calibration-state, draft-vs-applied, fingerprint, promote-kind-unit, pydantic]

requires:
  - phase: 13-01
    provides: promote_kind_unit pure helper, kind↔unit honesty matrix
provides:
  - CalibrationFingerprint / CalibrationParams / CalibrationSnapshot models
  - is_valid_calibration_params structural validity
  - CalibrationState draft/apply/clear machine with lock + snapshot
  - promote_kind_unit wrapper (applied+valid only → metric_calibrated+"m")
affects:
  - 14 DepthLoop post-process scale / promote
  - 15 calibration wizard REST/UI
  - 17 YAML persist fingerprint refuse

tech-stack:
  added: []
  patterns:
    - PipelineState twin: dataclass + threading.Lock + mutators return snapshot
    - draft params never is_applied; only applied+valid promotes
    - structural validity only in Phase 13 (residual thresholds Phase 14)

key-files:
  created:
    - src/sentry_ai/schemas/calibration.py
    - src/sentry_ai/control/calibration_state.py
    - tests/test_calibration_state.py
  modified:
    - src/sentry_ai/schemas/__init__.py
    - src/sentry_ai/control/__init__.py

key-decisions:
  - "Clear draft on successful apply (wizard Apply semantics)"
  - "get_applied_params() exposed for Phase 14 consumers"
  - "CalibrationSnapshot includes scale/method/fingerprint when applied"
  - "manual_scale skips sample_count floor; other methods require >= 1"

patterns-established:
  - "CalibrationState wraps validators.promote_kind_unit with live applied+valid flags"
  - "Fingerprint fields designed now for Phase 17 persist refuse"

requirements-completed: [CAL-04, CAL-05]

duration: 2min
completed: 2026-08-11
---

# Phase 13 Plan 02: CalibrationState Summary

**Thread-safe draft vs applied CalibrationState with fingerprint-bearing params; only applied+valid promotes to metric_calibrated+"m"**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-11T14:03:54Z
- **Completed:** 2026-08-11T14:06:07Z
- **Tasks:** 2/2
- **Files modified:** 5

## Accomplishments

- `CalibrationFingerprint` / `CalibrationParams` / `CalibrationSnapshot` with `extra=forbid`
- Structural `is_valid_calibration_params` (finite positive scale, finite offset, sample floor)
- `CalibrationState` draft/apply/clear machine; draft never reports applied or promotes
- `promote_kind_unit` returns `(METRIC_CALIBRATED, "m")` only when applied and valid
- Failed apply leaves prior applied params intact; `clear_draft` does not clear applied
- Phase 14 DepthLoop handoff documented in module docstring (no hook shipped)

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1 RED: Calibration model/validity tests** - `ca3ce3a` (test)
2. **Task 1 GREEN: Calibration Pydantic models + validity** - `722840a` (feat)
3. **Task 2 RED: CalibrationState draft/apply tests** - `362517b` (test)
4. **Task 2 GREEN: CalibrationState + package export** - `20ce564` (feat)

**Plan metadata:** `968c8fc` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/schemas/calibration.py` — Fingerprint/Params/Snapshot + `is_valid_calibration_params`
- `src/sentry_ai/schemas/__init__.py` — re-export calibration models
- `src/sentry_ai/control/calibration_state.py` — draft/applied state machine + promote wrapper
- `src/sentry_ai/control/__init__.py` — export `CalibrationState` alongside `PipelineState`
- `tests/test_calibration_state.py` — schema validity + full state machine coverage

## Decisions Made

- Clear draft on successful apply (matches wizard Apply semantics; draft is staging only)
- Expose `get_applied_params()` for Phase 14 map scale consumers without REST
- Snapshot includes optional applied `scale`/`method`/`fingerprint` (status-safe, no bulk arrays)
- `manual_scale` method may pass with `sample_count=0`; known_distance/known_height need ≥1

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 14 DepthLoop can call `state.promote_kind_unit` + implement `apply_map`
- Phase 15 wizard can mutate draft/apply via REST against this state
- Phase 17 persist can refuse on fingerprint mismatch using designed fields
- Zero new pip packages; no DepthLoop/wizard/YAML changes in this plan

## Verification

```text
uv run pytest tests/test_calibration_state.py tests/test_calibration_validators.py \
  tests/test_schemas_depth_kind.py tests/test_perception_store_depth_honesty.py \
  tests/test_depth_mapping.py tests/test_depth_kind_honesty.py -q
# 92 passed

uv run python -c "from sentry_ai.control import CalibrationState; from sentry_ai.schemas.calibration import CalibrationParams, CalibrationFingerprint"
# import ok
```

No edits to DepthLoop, free_space algorithm, routes, or index.html.

## Self-Check: PASSED

- All key files present
- Commits `ca3ce3a`, `722840a`, `362517b`, `20ce564` exist
- `CalibrationState` and calibration models importable
- No edits to DepthLoop, free_space algorithm, routes, or index.html

---
*Phase: 13-honesty-contracts-calibrationstate*
*Completed: 2026-08-11*
