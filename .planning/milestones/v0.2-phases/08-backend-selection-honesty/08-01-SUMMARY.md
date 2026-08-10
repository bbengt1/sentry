---
phase: 08-backend-selection-honesty
plan: 01
subsystem: detection-factory
tags: [backend-selection, artifact-paths, yolo, factory, honesty, onnxruntime, tensorrt]

# Dependency graph
requires:
  - phase: 07-export-recipes
    provides: KNOWN_WEIGHTS allowlist + export_yolo validate_weights pattern
  - phase: 02-profile-runtime
    provides: ProfileRuntime preferred_backend + device_for_backend
provides:
  - "WorkerBuild + build_detection_worker(rt) serve-time factory"
  - "resolve_detector_artifact allowlisted .onnx/.engine paths"
  - "Honest soft stubs: ORT/TRT → live=torch + stable reason codes"
  - "cli.serve constructs fixed-class detection only via factory"
affects:
  - 08-02-status-banner-honesty
  - 09-live-ort
  - 10-live-trt

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "WorkerBuild{worker, backend_requested, backend_live, backend_reason}"
    - "Soft torch stub for unimplemented loaders (never claim live ORT/TRT)"
    - "Path.resolve + is_relative_to allowlisted roots for artifacts"

key-files:
  created:
    - src/sentry_ai/config/artifact_paths.py
    - src/sentry_ai/models/detection/factory.py
    - tests/test_artifact_paths.py
    - tests/test_detection_factory.py
  modified:
    - src/sentry_ai/cli.py
    - src/sentry_ai/config/profile_runtime.py
    - tests/test_cli_serve.py

key-decisions:
  - "Soft stub ORT/TRT with torch worker + reason codes (not construct-time raise)"
  - "path_rejected raises on explicit/env; cache/CWD miss returns None"
  - "Factory sole author of backend_live; Phase 8 never emits live ORT/TRT"
  - "Stash backend_* locals in serve for 08-02 without create_app kwargs yet"

patterns-established:
  - "Factory at serve construction only — DetectionLoop frozen"
  - "Reason codes: ort_loader_not_implemented, trt_loader_not_implemented, unsupported_backend, path_rejected"
  - "model= injection forwarded for unit tests without weight download"

requirements-completed: [BACK-01, BACK-04, EDGE-RT-01, EDGE-RT-02, EDGE-RT-03]

# Metrics
duration: 3min
completed: 2026-08-09
---

# Phase 8 Plan 01: Backend Selection Factory Summary

**Serve-time `build_detection_worker` factory with allowlisted artifact paths; torch live, ORT/TRT soft-stub to torch with honest reason codes**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-08-09T19:37:07Z
- **Completed:** 2026-08-09T19:40:25Z
- **Tasks:** 3
- **Files modified:** 7

## Accomplishments

- Pure `resolve_detector_artifact` with stem/suffix allowlist and root confinement (BACK-04)
- `WorkerBuild` + `build_detection_worker(rt)` maps all three profiles honestly (BACK-01, EDGE-RT-03)
- `cli.serve` constructs fixed-class detection only through the factory; DetectionLoop unchanged (EDGE-RT-01/02)
- Full pytest suite green: 465 passed, 1 skipped; no new packages; no ORT/TRT imports

## Task Commits

Each task was committed atomically (TDD: test → feat):

1. **Task 1: Artifact path resolver** — `cdd5e8c` (test) + `f4d01bf` (feat)
2. **Task 2: build_detection_worker factory** — `c348bd4` (test) + `a4d9871` (feat)
3. **Task 3: Wire cli.serve to factory** — `c1f2fc7` (test) + `a1cfa4f` (feat)

**Plan metadata:** `eea5f79` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/config/artifact_paths.py` — `resolve_detector_artifact` + allowlists
- `src/sentry_ai/models/detection/factory.py` — `WorkerBuild` + `build_detection_worker`
- `src/sentry_ai/config/profile_runtime.py` — docstring: preferred selects factory branch
- `src/sentry_ai/cli.py` — serve uses factory; stashes `backend_*` locals
- `tests/test_artifact_paths.py` — traversal + allowlist coverage
- `tests/test_detection_factory.py` — profile matrix + soft-stub honesty
- `tests/test_cli_serve.py` — factory wiring inspect asserts

## Decisions Made

- Soft torch return for ORT/TRT (not hard-fail) so jetson/cpu-fallback serve still starts
- Explicit/env path outside roots → `ValueError` / factory reason `path_rejected`; cache miss → `None`
- Env vars: `SENTRY_DETECTOR_ONNX`, `SENTRY_DETECTOR_ENGINE`, optional `SENTRY_ARTIFACT_ROOT`
- `backend_*` locals only in serve for now — create_app / banner rewrite deferred to 08-02

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for **08-02**: surface `backend_requested` / `backend_live` / `backend_reason` on banner + `/api/status`
- Factory + artifact resolver ready for Phases 9–10 live ORT/TRT loaders
- Perception spine files unmodified (`loop.py`, FrameBus, PerceptionStore, `/v1`)

## Self-Check: PASSED

- All key files present
- All task commits found in git log
- No stub/placeholder patterns in new modules
- Verification: `uv run pytest tests/test_artifact_paths.py tests/test_detection_factory.py tests/test_cli_serve.py -q` green; full suite 465 passed

---
*Phase: 08-backend-selection-honesty*
*Completed: 2026-08-09*
