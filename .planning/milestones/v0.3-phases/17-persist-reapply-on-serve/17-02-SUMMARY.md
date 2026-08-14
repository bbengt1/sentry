---
phase: 17-persist-reapply-on-serve
plan: 02
subsystem: control
tags: [calibration, persist, serve, rest, per-02, per-04]

requires:
  - phase: 17-01
    provides: YAML store + try_reapply + apply_params + refuse_if_mismatch
provides:
  - cli.serve try_reapply + --calibration-file + persist banner
  - POST save / apply persist:true / Clear deletes YAML
  - GET /api/status calibration_persist additive
  - DepthLoop late W×H refuse_if_mismatch before apply_map
affects:
  - Phase 18 docs + synthetic CI polish

tech-stack:
  added: []
  patterns:
    - try_reapply after source + depth worker; W×H None at serve start
    - persist via POST save and optional persist:true; apply-without-persist session-only
    - Clear = clear_persisted (unlink); Cancel = clear_draft only
    - DepthLoop sole apply_map site; refuse before promote+apply

key-files:
  created:
    - .planning/phases/17-persist-reapply-on-serve/17-02-SUMMARY.md
  modified:
    - src/sentry_ai/cli.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_calibration.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/models/depth/loop.py
    - tests/test_api_calibration.py
    - tests/test_cli_calibration_inject.py
    - tests/test_depth_loop.py
    - .planning/STATE.md

key-decisions:
  - "Live fingerprint at serve: camera_id from source; mode/model from depth_worker; W×H None"
  - "Optional apply body parsed from raw JSON so empty POST apply stays persist=false"
  - "Path fallback: app.state.calibration_path else calibration_path(applied camera_id)"
  - "Clear deletes file when path known; Cancel never touches disk"
  - "Status calibration_persist additive; never sets depth_kind from persist"

patterns-established:
  - "Serve banner: calibration: {status} [reason=...]"
  - "Headless --no-ui still calls try_reapply before create_app"

requirements-completed: [PER-02, PER-04]

duration: 40min
completed: 2026-08-14
---

# Phase 17 Plan 02: Serve Re-apply + REST Persist/Clear Summary

**PER-02/PER-04: `sentry serve` calls `try_reapply` for a matching YAML; REST save / `persist:true` write the file; Clear deletes it so restart cannot resurrect; Cancel stays draft-only. Late W×H mismatch refuses before `apply_map`. Persist status is additive and separate from `depth.kind`.**

## Performance

- **Duration:** ~40 min
- **Started:** 2026-08-14T09:52:00Z
- **Completed:** 2026-08-14T10:30:00Z
- **Tasks:** 1/1
- **Files modified:** 10 (+ this summary)

## Accomplishments

- `cli.serve`: `--calibration-file`, `try_reapply` after source + depth worker, banner, `calibration_path` into `create_app` (headless `--no-ui` still loads)
- REST: POST `/save`; apply optional `{persist:true}`; Clear calls `clear_persisted`; Cancel unchanged
- `/api/status`: `calibration_persist` + optional reason; does not invent `depth_kind`
- DepthLoop: `refuse_if_mismatch` before promote + `apply_map` (sole scale site)
- Synthetic ASGI + CLI inspect + DepthLoop size tests
- Zero new pip deps; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` frozen; no wizard HTML / FSD

## Task Commits

MCP push commits on `feat/17-02-serve-reapply-persist`.

## Files Created/Modified

- `src/sentry_ai/cli.py` - `--calibration-file` + try_reapply + banner
- `src/sentry_ai/api/app.py` - `calibration_path` inject
- `src/sentry_ai/api/deps.py` - AppState.calibration_path
- `src/sentry_ai/api/routes_calibration.py` - save / persist:true / clear_persisted
- `src/sentry_ai/api/routes_preview.py` - additive persist status
- `src/sentry_ai/models/depth/loop.py` - late W×H refuse
- `tests/test_api_calibration.py` - PER-04 save/clear/cancel/status
- `tests/test_cli_calibration_inject.py` - PER-02 inspect + help
- `tests/test_depth_loop.py` - late size refuse / match / skip
- `.planning/STATE.md` - 17-02 done; Phase 17 complete; next Phase 18

## Decisions Made

- Empty POST apply stays session-only (manual JSON parse, not FastAPI required body)
- `set_persist_status("applied")` after successful save / persist:true
- FakeDepthWorker in loop tests now exposes `get_depth_mode` + `model_id` so refuse does not false-mismatch existing apply tests

## Deviations from Plan

- Apply/save bodies parsed from `request.body()` so existing no-body apply clients stay green (plan allowed `None` body ⇒ persist false)
- `test_cli_serve.py` unchanged; `--calibration-file` help covered in `test_cli_calibration_inject.py`
- ROADMAP.md left for Phase 18 docs polish

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- Phase 17 complete (PER-01..04)
- Phase 18: operator docs, honesty docs, synthetic CI polish (no FSD)

## Verification

```text
uv run pytest tests/test_calibration_store.py tests/test_calibration_persist.py \
  tests/test_calibration_state.py tests/test_api_calibration.py \
  tests/test_api_calibration_smoother.py tests/test_cli_calibration_inject.py \
  tests/test_depth_loop.py tests/test_cli_serve.py -q
```

## Self-Check: PASSED

- Key files present
- Target APIs match plan (serve re-apply, save/persist:true, clear-file, status, late size)
- No DetectionLoop / FrameBus / ORT-TRT / kind_for_mode / wizard HTML / FSD edits
- No `apply_map` in cli.py or routes_calibration.py
- No `calibration_store` I/O in DepthLoop

---
*Phase: 17-persist-reapply-on-serve*
*Completed: 2026-08-14*
