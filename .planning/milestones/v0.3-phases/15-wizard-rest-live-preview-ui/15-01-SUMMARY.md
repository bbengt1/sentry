---
phase: 15-wizard-rest-live-preview-ui
plan: 01
subsystem: api
tags: [calibration, wizard-rest, wiz-01, wiz-02, wiz-04, ops-01]

requires:
  - phase: 14-02
    provides: CalibrationState.apply_map + DepthLoop inject
provides:
  - CalibrationSample + public draft sample APIs on CalibrationState
  - routes_calibration freeze/sample/compute/apply/cancel/clear
  - create_app / AppState / CLI same CalibrationState instance
  - additive /api/status calibration_* fields
affects:
  - 15-02 static wizard UI (consumes this REST)
  - 16 free-space meters (inherits scaled store after apply + DepthLoop)
  - 17 YAML persist re-apply on serve

tech-stack:
  added: []
  patterns:
    - control-plane 503 when inject missing
    - extra=forbid request bodies
    - handlers never worker.process or open cameras
    - Cancel = clear_draft; Clear = clear_applied
    - same construct-time CalibrationState for DepthLoop + create_app

key-files:
  created:
    - src/sentry_ai/api/routes_calibration.py
    - tests/test_api_calibration.py
    - .planning/phases/15-wizard-rest-live-preview-ui/15-01-SUMMARY.md
  modified:
    - src/sentry_ai/schemas/calibration.py
    - src/sentry_ai/schemas/__init__.py
    - src/sentry_ai/control/calibration_state.py
    - src/sentry_ai/spatial/calibration.py
    - src/sentry_ai/spatial/__init__.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/cli.py
    - tests/test_calibration_state.py
    - tests/test_cli_calibration_inject.py
    - tests/test_calibration_fit.py
    - .planning/STATE.md

key-decisions:
  - "Cancel = clear_draft only; Clear = clear_applied + clear_draft"
  - "Sample while applied is HTTP 409 calibration_already_applied"
  - "Freeze pin lives on app.state, not CalibrationState"
  - "CLI hoists CalibrationState before depth extra try so create_app always gets it"
  - "Handlers never set_depth; live kind stays relative until DepthLoop writes"

patterns-established:
  - "Wizard REST analog of routes_pipeline: 503 / extra=forbid / never process"
  - "Draft samples public API; fit reuse with ok-gated set_draft_params"

requirements-completed: [WIZ-01, WIZ-02, WIZ-04, OPS-01]

duration: 40min
completed: 2026-08-13
---

# Phase 15 Plan 01: Calibration Wizard REST + AppState Inject Summary

**WIZ-01/02/04 + OPS-01 backend: in-memory freeze/sample/fit/apply/cancel/clear REST; same CalibrationState for DepthLoop and create_app; additive /api/status fields. No wizard HTML (15-02).**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-08-13T12:21:00Z
- **Completed:** 2026-08-13T13:05:00Z
- **Tasks:** 2/2
- **Files modified:** 16

## Accomplishments

- `CalibrationSample` (`extra=forbid`) plus public `add_draft_sample` / `get_draft_samples` (copy) / `clear_draft_samples` on `CalibrationState`
- Optional `known_height_to_distance_m` FOV helper (default HFOV 70° documented assumption)
- `create_app(..., calibration_state=)` and `AppState.calibration_state`; default None (503 on wizard routes)
- `cli.serve` hoists `CalibrationState()` outside the depth-extra ImportError path and passes the **same** instance to `DepthLoop` and `create_app`
- REST: GET snapshot; POST freeze (in-memory pin); POST sample; DELETE samples; POST compute (median/affine, ok-gated draft); POST apply; POST cancel (`clear_draft` only); POST clear (`clear_applied`)
- Sample while applied → 409; rejected fit → 422 with no draft; missing state → 503
- `/api/status` additive `calibration_active` / `calibration_sample_count` / scale / method / camera_id when state injected
- Live `depth_kind` stays store product until DepthLoop writes (WIZ-04); apply then next loop product is `metric_calibrated` + `"m"`
- Zero new pip deps; no YAML; no free-space meters; no index.html wizard chrome; DetectionLoop / FrameBus / ORT-TRT frozen

## Task Commits

MCP push commits on `feat/15-01-calibration-wizard-rest`.

## Files Created/Modified

- `src/sentry_ai/schemas/calibration.py` — `CalibrationSample`
- `src/sentry_ai/control/calibration_state.py` — public draft sample APIs
- `src/sentry_ai/spatial/calibration.py` — `known_height_to_distance_m`
- `src/sentry_ai/api/routes_calibration.py` — wizard REST
- `src/sentry_ai/api/app.py` / `deps.py` / `cli.py` — same-instance inject
- `src/sentry_ai/api/routes_preview.py` — additive status fields
- `tests/test_api_calibration.py` — ASGI WIZ-01/02/04 + OPS-01 matrix
- `.planning/STATE.md` — 15-01 done; next 15-02

## Decisions Made

- Freeze pin is `app.state.calibration_freeze_pin` (copied DepthProduct), not on CalibrationState
- DELETE samples calls `clear_draft()` (samples + stale draft params); pin may remain
- Compute default `fit="median"`; `fit="affine"` when requested
- Status omits scale/method/camera_id unless applied; always includes `calibration_active` when state is injected

## Deviations from Plan

- Re-exported `CalibrationSample` from `schemas/__init__.py` and `known_height_to_distance_m` from `spatial/__init__.py` (lazy) so package exports stay consistent
- Added a DepthLoop tick test after REST apply to prove the next depth product is `metric_calibrated` + `"m"` (handlers still never `set_depth`)
- Compute body is optional (`None` → median defaults) so POST without JSON still 503-checks state first when possible; tests send `json={}`

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- 15-02 can add static wizard chrome on `index.html` consuming this REST; must not locally claim `metric_calibrated`
- Phase 16/17 still out of scope (free-space meters / YAML persist)

## Verification

```text
uv run pytest tests/test_api_calibration.py tests/test_api_preview.py \
  tests/test_api_depth.py tests/test_cli_calibration_inject.py \
  tests/test_calibration_state.py tests/test_calibration_fit.py \
  tests/test_depth_loop.py tests/test_perception_store_depth_honesty.py \
  tests/test_calibration_validators.py -q
```

## Self-Check: PASSED

- Key files present
- Target APIs match plan
- No edits to DetectionLoop, FrameBus, ORT-TRT factory, free_space algorithm, index.html, or YAML I/O

---
*Phase: 15-wizard-rest-live-preview-ui*
*Completed: 2026-08-13*
