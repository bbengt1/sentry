---
phase: 19-online-consent-honesty-state
plan: 02
subsystem: api
tags: [calibration, online, honesty, onl-01, onl-06]

requires:
  - phase: 19-01
    provides: CalibrationState.is_online / set_online + snapshot.online + first-scale lock
provides:
  - CalibrationSnapshot.online_status four-way literal
  - Cancel/Clear/disable-online as three distinct operations
  - POST /api/depth/calibration/online thin REST toggle
  - GET /api/status calibration_online + calibration_online_status
affects:
  - Phase 20 online sample + fit/reject (plans not started)

tech-stack:
  added: []
  patterns:
    - Session online_status on CalibrationState (not persist_status, not depth.kind)
    - set_online(True) after applied → online_draft; set_online(False) → online_off
    - clear_applied forces online_off; clear_draft leaves online unchanged
    - POST extra=forbid; unapplied enable → 409 online_requires_applied
    - Phase 19 never assigns auto_committed or rejected

key-files:
  created:
    - .planning/phases/19-online-consent-honesty-state/19-02-SUMMARY.md
    - tests/test_api_calibration_online.py
    - tests/test_api_calibration_rest.py
    - tests/test_api_calibration_persist_rest.py
  modified:
    - src/sentry_ai/schemas/calibration.py
    - src/sentry_ai/control/calibration_state.py
    - src/sentry_ai/api/routes_calibration.py
    - src/sentry_ai/api/routes_preview.py
    - tests/test_calibration_state.py
    - tests/test_calibration_persist.py
    - tests/test_api_calibration.py
    - .planning/STATE.md
    - .planning/REQUIREMENTS.md
    - .planning/ROADMAP.md

key-decisions:
  - "online_status Literal online_off|online_draft|auto_committed|rejected default online_off"
  - "set_online(True) always sets online_draft; set_online(False) sets online_off without YAML I/O"
  - "409 detail is exactly online_requires_applied"
  - "GET /api/status always emits calibration_online + calibration_online_status when calib exists"
  - "No sampler / auto-commit / YAML persist of the flag"

patterns-established:
  - "Cancel = draft only; Clear = applied+YAML (online_off); disable-online ≠ Clear"
  - "Four-way online_status is a third plane beside depth.kind and persist_status"

requirements-completed: [ONL-01, ONL-06]
requirements-partial: []

duration: 30min
completed: 2026-08-30
---

# Phase 19 Plan 02: Cancel/Clear/disable-online + online_status REST

**ONL-06 + ONL-01 status half: Cancel, Clear, and disable-online are three operations. Four-way `online_status` is representable and is not `depth.kind` or persist. Thin REST POST toggle cannot invent the first scale. Zero new packages. No sampler / auto-commit / YAML persist of the flag.**

## Performance

- **Duration:** ~30 min
- **Started:** 2026-08-31T00:57:00Z
- **Completed:** 2026-08-31T01:25:00Z
- **Tasks:** 2/2
- **Files modified:** 13 (+ this summary)

## Accomplishments

- `CalibrationSnapshot.online_status` four-way Literal, default `online_off` (`extra=forbid`)
- `CalibrationState._online_status`; `set_online(True)` → `online_draft`; disable / `clear_applied` → `online_off`
- `clear_draft` leaves online flag + status put; disable does not `clear_applied` or touch YAML
- `POST /api/depth/calibration/online` `{enabled: bool}` extra=forbid; unapplied enable → 409
- `GET /api/status` additive `calibration_online` + `calibration_online_status` (never writes `depth_kind`)
- Synthetic ONL-06 matrix at state, persist, and REST layers
- No DepthLoop / DetectionLoop / FrameBus / apply_map / index.html / pyproject edits

## Task Commits

MCP push commits on `feat/19-02-online-status-rest`.

## Files Created/Modified

- `src/sentry_ai/schemas/calibration.py` — `CalibrationSnapshot.online_status`
- `src/sentry_ai/control/calibration_state.py` — `_online_status` transitions + optional `set_online_status`
- `src/sentry_ai/api/routes_calibration.py` — `POST /api/depth/calibration/online`
- `src/sentry_ai/api/routes_preview.py` — `/api/status` online additives
- `tests/test_calibration_state.py` — status enum + Cancel/disable vs clear_applied
- `tests/test_calibration_persist.py` — disable leaves YAML; Clear forces online_off
- `tests/test_api_calibration.py` — GET snapshot online keys + POST /online 503
- `tests/test_api_calibration_online.py` — REST 409/200/422 + Cancel/Clear/disable + status plane
- `tests/test_api_calibration_rest.py` — restored compute/apply/cancel/clear cases
- `tests/test_api_calibration_persist_rest.py` — restored persist/save/clear YAML cases
- `.planning/STATE.md` — 19-02 done; Phase 19 complete; next plan Phase 20
- `.planning/REQUIREMENTS.md` — ONL-01 + ONL-06 complete
- `.planning/ROADMAP.md` — Phase 19 checkbox complete

## Decisions Made

- REST body is FastAPI `CalibrationOnlineBody(enabled: bool)` so extra/missing → 422
- Production paths never assign `auto_committed` or `rejected` (`set_online_status` exists for Phase 21 tests)
- Online reset lives inside `clear_applied` so REST Clear / `clear_persisted` stay consistent

## Deviations from Plan

- Combined RED+GREEN in one implementation PR (tests + product together). Plan allowed TDD locally; MCP landing is one branch.
- REST cases split across companion modules so GitHub MCP `push_files` could land the full suite without truncating `test_api_calibration.py`.

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- Phase 19 complete (ONL-01, ONL-02, ONL-06)
- Next: **plan** Phase 20 (online sample + fit/reject). Do not execute 20 yet.

## Verification

```text
uv run pytest tests/test_calibration_state.py tests/test_calibration_persist.py \
  tests/test_api_calibration.py tests/test_api_calibration_online.py \
  tests/test_api_calibration_rest.py tests/test_api_calibration_persist_rest.py \
  tests/test_cli_calibration_inject.py tests/test_calibration_fit.py -q --tb=short
```

## Self-Check: PASSED

- Target APIs match plan (`online_status`, POST `/online`, `/api/status` additives)
- `apply_map` formula unchanged (`scale * map + offset`)
- No DetectionLoop / FrameBus / ORT-TRT / kind_for_mode / index.html edits
- No pyproject version bump
- No sampler / auto-commit / YAML online key
- Production routes do not assign `auto_committed` or `rejected`

---
*Phase: 19-online-consent-honesty-state*
*Completed: 2026-08-30*
