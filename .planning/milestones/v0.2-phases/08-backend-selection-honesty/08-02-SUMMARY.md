---
phase: 08-backend-selection-honesty
plan: 02
subsystem: status-honesty
tags: [backend-selection, status, banner, live-preview, honesty, onnxruntime, tensorrt]

# Dependency graph
requires:
  - phase: 08-backend-selection-honesty
    provides: WorkerBuild + build_detection_worker with backend_requested/live/reason
provides:
  - "StatusSnapshot optional backend_requested/backend_live/backend_reason"
  - "create_app app.state injection + /api/status pass-through merge"
  - "Serve banner structured honesty fields"
  - "Live Preview footer metric-backend requested → live"
affects:
  - 09-live-ort
  - 10-live-trt
  - phase-08-verification

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "app.state pass-through for factory-authored backend identity"
    - "api_status best-effort getattr merge (pipeline_state pattern)"
    - "Banner prints requested/live; reason on stderr when set"

key-files:
  created:
    - tests/test_backend_honesty_status.py
  modified:
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - tests/test_cli_serve.py

key-decisions:
  - "Route never recomputes live from preferred_backend — pass-through only"
  - "Missing injection leaves backend fields None (backward compatible)"
  - "Structured banner fields replace prose-only export-target notes"
  - "Footer shows requested → live; appends reason when they differ"

patterns-established:
  - "Factory sole author of backend_live; status/UI display only"
  - "Honesty fixtures: tensorrt|onnxruntime → torch + reason codes on /api/status"

requirements-completed: [BACK-02, EDGE-RT-01, EDGE-RT-03]

# Metrics
duration: 3min
completed: 2026-08-09
---

# Phase 8 Plan 02: Status, Banner & Live Preview Honesty Summary

**End-to-end backend honesty: StatusSnapshot + `/api/status` + serve banner + Live Preview footer expose factory-authored `backend_requested` vs `backend_live` (with reason)**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-08-09T19:42:20Z
- **Completed:** 2026-08-09T19:45:00Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- StatusSnapshot schema + create_app/AppState inject factory backend metadata (BACK-02)
- `/api/status` merges backend_* pass-through only — never invents live ORT/TRT
- Serve banner prints structured `backend_requested` / `backend_live` / `backend_reason`
- Live Preview footer `metric-backend` shows `requested → live` (reason when mismatch)
- Full pytest suite green: 473 passed, 1 skipped; no new packages; DetectionLoop /v1 unchanged

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1: StatusSnapshot + create_app + /api/status honesty** — `014154f` (test) + `1110bc1` (feat)
2. **Task 2: Serve banner + Live Preview footer honesty** — `bbac54a` (test) + `5493e35` (feat)

**Plan metadata:** `6df0515` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/capture/status.py` — optional backend_requested/live/reason on StatusSnapshot
- `src/sentry_ai/api/app.py` — create_app kwargs → app.state
- `src/sentry_ai/api/deps.py` — AppState mirrors three optional fields
- `src/sentry_ai/api/routes_preview.py` — api_status best-effort merge from app.state
- `src/sentry_ai/cli.py` — create_app wiring + structured banner (replaced export-target-only prose)
- `src/sentry_ai/ui/static/index.html` — metric-backend footer + applyStatus update
- `tests/test_backend_honesty_status.py` — StatusSnapshot + TestClient honesty fixtures
- `tests/test_cli_serve.py` — create_app kwargs + banner inspect asserts

## Decisions Made

- Pass-through only: route layer never derives `backend_live` from `preferred_backend`
- Null-safe: create_app without backend kwargs leaves fields None; status does not raise
- Banner reason on stderr when set (same channel as prior honesty notes)
- Footer format `torch → torch` or `tensorrt → torch (trt_loader_not_implemented)` when mismatch

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 8 plans complete — ready for **phase verification**
- Live ORT (Phase 9) / TRT (Phase 10) can flip `backend_live` in factory; status/UI already display it
- Perception spine unmodified (DetectionLoop, FrameBus, store, `/v1`)

## Self-Check: PASSED

- All key files present
- All task commits found in git log
- No stub/placeholder patterns blocking plan goals (input `placeholder=` attr on OV prompt is intentional UI)
- Verification: `uv run pytest tests/test_backend_honesty_status.py tests/test_cli_serve.py tests/test_api_preview.py tests/test_detection_factory.py -q` green; full suite 473 passed, 1 skipped

---
*Phase: 08-backend-selection-honesty*
*Completed: 2026-08-09*
