---
phase: 17-persist-reapply-on-serve
plan: 01
subsystem: control
tags: [calibration, persist, fingerprint, per-01, per-03]

requires:
  - phase: 16
    provides: Phase 16 complete on main; CalibrationParams + CalibrationState
provides:
  - YAML calibration store keyed by sanitized camera_id
  - fingerprints_match hard-refuse (camera_id / mode / model; W×H when both known)
  - apply_params load path (no fake wizard samples)
  - try_reapply / persist_applied / clear_persisted / refuse_if_mismatch
affects:
  - 17-02 serve re-apply, REST save/clear, status banner, late W×H

tech-stack:
  added: []
  patterns:
    - yaml.safe_load / safe_dump only; Pydantic CalibrationParams round-trip
    - STACK path: SENTRY_CALIBRATION_DIR or {cache_root}/calibration/{stem}.yaml
    - atomic temp + os.replace; no platformdirs
    - CalibrationState stays I/O-free; I/O in config/calibration_store.py

key-files:
  created:
    - src/sentry_ai/config/calibration_store.py
    - src/sentry_ai/control/calibration_persist.py
    - tests/test_calibration_store.py
    - tests/test_calibration_persist.py
    - .planning/phases/17-persist-reapply-on-serve/17-01-SUMMARY.md
  modified:
    - src/sentry_ai/schemas/calibration.py
    - src/sentry_ai/control/calibration_state.py
    - tests/test_calibration_state.py
    - .planning/STATE.md

key-decisions:
  - "Path = SENTRY_CALIBRATION_DIR or {SENTRY_MODEL_CACHE|default_cache_root()}/calibration"
  - "safe_camera_stem rejects empty / .. / separators / leading dot; allow [A-Za-z0-9._-]+"
  - "Hard-refuse camera_id always; depth_mode/model_id when saved non-None; W×H when both non-None"
  - "apply_params is the load path; apply() still requires a wizard draft"
  - "clear_applied resets persist to none; refuse_if_mismatch then sets ignored_mismatch"
  - "No CLI/REST/DepthLoop/wizard HTML in 17-01"

patterns-established:
  - "try_reapply: none | applied | ignored_mismatch | error; never invent metric_calibrated"
  - "persist status additive on CalibrationSnapshot (extra=forbid unchanged)"

requirements-completed: [PER-01, PER-03]

duration: 25min
completed: 2026-08-14
---

# Phase 17 Plan 01: YAML Calibration Store + Fingerprint Refuse Summary

**PER-01/PER-03: pure YAML store + fingerprint-gated `try_reapply`. Matching file calls `apply_params` (no draft samples). Mismatch/corrupt/missing stay inactive. No CLI serve hook, REST save/clear, status banner, or `--calibration-file` (17-02).**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-14T08:10:00Z
- **Completed:** 2026-08-14T08:35:00Z
- **Tasks:** 1/1
- **Files modified:** 8 (+ this summary)

## Accomplishments

- `config/calibration_store.py`: STACK path resolve, `safe_camera_stem`, atomic YAML save/load/delete, `fingerprints_match`
- `control/calibration_persist.py`: `try_reapply` / `persist_applied` / `clear_persisted` / `refuse_if_mismatch`
- `CalibrationState.apply_params` + persist status on snapshot (`none|applied|ignored_mismatch|error`)
- Synthetic tests: path/sanitize/round-trip/atomic/corrupt + match matrix + try_reapply honesty
- Zero new pip deps; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` frozen; no CLI/REST/DepthLoop/wizard HTML

## Task Commits

MCP push commits on `feat/17-01-calibration-store`.

## Files Created/Modified

- `src/sentry_ai/config/calibration_store.py` - path, sanitize, fingerprints, atomic YAML
- `src/sentry_ai/control/calibration_persist.py` - try_reapply orchestration
- `src/sentry_ai/control/calibration_state.py` - apply_params + persist status
- `src/sentry_ai/schemas/calibration.py` - snapshot persist_status / persist_reason
- `tests/test_calibration_store.py` - PER-01 / PER-03 store matrix
- `tests/test_calibration_persist.py` - try_reapply honesty
- `tests/test_calibration_state.py` - apply_params + persist snapshot
- `.planning/STATE.md` - 17-01 done; next 17-02

## Decisions Made

- Reject (do not rewrite) illegal camera_id stems including leading `.`
- `try_reapply` catches `apply_params` ValueError (e.g. scale<=0 in YAML) as `error`
- `clear_applied` always resets persist to `none`; callers overwrite after (refuse)
- Store module not re-exported from `config/__init__.py` (plan lists the module APIs)

## Deviations from Plan

- `try_reapply` treats structurally invalid-but-parseable params (scale<=0) as `error` rather than raising through to the caller
- Extra tests: saved mode vs live None is a mismatch; persist_applied inactive raises; refuse noop when inactive

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- 17-02 can wire `cli.serve` `try_reapply` + `--calibration-file` + banner
- REST save / `persist:true` / Clear-deletes-file / `/api/status` `calibration_persist`
- DepthLoop late W×H `refuse_if_mismatch` before `apply_map`

## Verification

```text
uv run pytest tests/test_calibration_store.py tests/test_calibration_persist.py \
  tests/test_calibration_state.py tests/test_calibration_fit.py \
  tests/test_api_calibration.py tests/test_cli_calibration_inject.py -q
uv run pytest -q
uv run ruff check src tests
```

Box: 143 targeted passed; full suite 790 passed, 1 skipped; ruff clean.

## Self-Check: PASSED

- Key files present
- Target APIs match plan (store + persist + apply_params)
- No edits to cli.py, routes, DepthLoop, DetectionLoop, FrameBus, ORT-TRT, kind_for_mode, or wizard HTML

---
*Phase: 17-persist-reapply-on-serve*
*Completed: 2026-08-14*
