---
phase: 14-scale-math-depthloop-plugin
plan: 01
subsystem: spatial
tags: [calibration, scale-fit, affine, numpy, cal-01, cal-02]

requires:
  - phase: 13-honesty-contracts-calibrationstate
    provides: CalibrationParams schema, CalibrationState draft/apply (no apply_map yet)
provides:
  - CalibrationFitResult frozen ok/reason result
  - fit_scale_median (default CAL-01 median of D_i/d_i)
  - fit_affine_lstsq (optional N>=2 lstsq)
  - residual_rms + absurd_scale fit-time reject gates (CAL-02)
affects:
  - 14-02 CalibrationState.apply_map + DepthLoop plug-in
  - 15 wizard set_draft_params only when FitResult.ok

tech-stack:
  added: []
  patterns:
    - pure NumPy fitter in spatial/; no CalibrationState mutation
    - fit-time reject with stable reason codes before draft

key-files:
  created:
    - src/sentry_ai/spatial/calibration.py
    - tests/test_calibration_fit.py
    - .planning/phases/14-scale-math-depthloop-plugin/14-01-SUMMARY.md
  modified:
    - src/sentry_ai/spatial/__init__.py
    - .planning/STATE.md

key-decisions:
  - "Fit types live in spatial/calibration.py (not schemas) - CalibrationParams built by callers later"
  - "Lazy spatial __init__ exports for fit symbols matching free_space pattern"
  - "residual_rms_gate returns True when within threshold (passes)"

patterns-established:
  - "FitResult.ok must be True before Phase 15 set_draft_params"
  - "Apply formula documented for 14-02: map_out = scale * map_in + offset"

requirements-completed: [CAL-01, CAL-02]

duration: 8min
completed: 2026-08-13
---

# Phase 14 Plan 01: Scale/Affine Fit Summary

**Pure NumPy scale-only median + optional affine lstsq with fit-time reject gates (CAL-01/02)**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-08-13T01:35:00Z
- **Completed:** 2026-08-13T01:43:00Z
- **Tasks:** 1/1
- **Files modified:** 5

## Accomplishments

- `fit_scale_median` recovers scale from synthetic `(observed_raw, known_meters)` via `median(D_i/d_i)`
- `fit_affine_lstsq` recovers scale+offset for N>=2 via `numpy.linalg.lstsq`
- Non-positive / non-finite pairs filtered; empty/all-invalid -> `insufficient_valid_samples`
- Absurd scale outside `(1e-4, 1e4)` -> `absurd_scale`
- High residual -> `residual_rms_too_high` using `max(0.15*median(D), 0.05)`
- Affine with N<2 -> `affine_requires_n_ge_2`
- Zero new deps; no DepthLoop / apply_map / wizard / free-space meters

## Task Commits

Single MCP push commit on `feat/14-01-calibration-fit` (implementation + tests + summary + STATE).

## Files Created/Modified

- `src/sentry_ai/spatial/calibration.py` - `CalibrationFitResult`, `fit_scale_median`, `fit_affine_lstsq`, gates
- `tests/test_calibration_fit.py` - accept + reject matrix for CAL-01/CAL-02
- `src/sentry_ai/spatial/__init__.py` - lazy exports for fit symbols
- `.planning/phases/14-scale-math-depthloop-plugin/14-01-SUMMARY.md` - this file
- `.planning/STATE.md` - 14-01 done; next 14-02

## Decisions Made

- Kept `CalibrationFitResult` in the spatial module (plan discretion); schemas still own `CalibrationParams` + fingerprint
- Documented 14-02 apply formula in module docstring without implementing `apply_map`
- Exported fit helpers via existing lazy `__getattr__` pattern

## Deviations from Plan

None - plan executed as written. Fit types not added to schemas (plan preferred spatial unless required).

## Issues Encountered

None

## User Setup Required

None

## Next Phase Readiness

- Plan 14-02 can consume FitResult fields -> `CalibrationParams` and implement `CalibrationState.apply_map` + DepthLoop inject
- Callers must require `ok=True` before `set_draft_params`

## Verification

```text
# Local (box) smoke of new suite:
PYTHONPATH=src pytest tests/test_calibration_fit.py -q
# 19 passed

# Repo verify (after merge / CI):
uv run pytest tests/test_calibration_fit.py tests/test_calibration_state.py tests/test_calibration_validators.py -q
```

## Self-Check: PASSED

- Key files present
- Target APIs match plan
- No edits to DepthLoop, calibration_state apply_map, cli, free_space algorithm, routes, or index.html

---
*Phase: 14-scale-math-depthloop-plugin*
*Completed: 2026-08-13*
