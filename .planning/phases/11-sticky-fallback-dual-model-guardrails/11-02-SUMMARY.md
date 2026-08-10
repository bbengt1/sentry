---
phase: 11-sticky-fallback-dual-model-guardrails
plan: 02
subsystem: operator-surface-edge-guardrails
tags: [fallback_to_torch, EDGE-RT-04, dual-model, status, BACK-03, depth, open-vocab, docs]

# Dependency graph
requires:
  - phase: 11-sticky-fallback-dual-model-guardrails
    provides: ProfileRuntime.fallback_to_torch + factory soft/strict + serve Exit(1)
  - phase: 10-live-tensorrt-fixed-class-yolo
    provides: live TRT factory + status honesty pass-through chain
provides:
  - StatusSnapshot.fallback_to_torch + create_app/AppState/routes pass-through (False preserved)
  - CLI injects rt.fallback_to_torch into create_app; banner already echoes policy
  - UI footer reason when live missing/differs + soft/strict hint
  - EDGE-RT-04 static lock: depth/OV not factory-routed; torch/HF + YOLOE .pt only
  - Dual-model docs: measure-on-device YOLO+DAV2; continuous OV+TRT+DAV2 not first-class
  - Phase 11 deferral language retired from export dual-model/sticky docs
affects:
  - Phase 12 edge docs polish (EDGE-DOC-*)
  - Phase 12 CI matrix (EDGE-CI-*)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Status pass-through uses is not None so bool False survives
    - EDGE-RT-04 proven by static source inspection (no Jetson/GPU)
    - Dual-model honesty: measure-on-device + explicit non-claim continuous OV

key-files:
  created:
    - tests/test_edge_rt04_torch_only.py
  modified:
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - tests/test_backend_honesty_status.py
    - tests/test_export_docs.py
    - docs/export/yolo26-onnx-tensorrt.md
    - docs/export/jetson-packaging.md
    - docs/export/README.md

key-decisions:
  - "fallback_to_torch is bool|None on StatusSnapshot (not string enum)"
  - "Pass-through if value is not None — never truthiness that drops False"
  - "Depth/OV remain separate constructors; factory only fixed-class detection"
  - "Dual-model: measure-on-device TRT/torch YOLO + torch DAV2; continuous OV+TRT+DAV2 not first-class"
  - "Retire Phase 11 deferred sticky/dual-model language from export docs"

patterns-established:
  - "Four-place status field mirror: StatusSnapshot + create_app + AppState + routes_preview"
  - "EDGE-RT-04 lock via cli/depth/yoloe source inspect tests"
  - "Export dual-model keyword suite forbids Phase 11 deferral lies"

requirements-completed: [EDGE-RT-04, BACK-03]

# Metrics
duration: 3min
completed: 2026-08-10
---

# Phase 11 Plan 02: Operator Surface + EDGE-RT-04 Dual-Model Guardrails Summary

**fallback_to_torch on status/banner/UI, EDGE-RT-04 torch-only depth/OV lock, dual-model measure-on-device docs with continuous OV non-claim**

## Performance

- **Duration:** 3 min
- **Started:** 2026-08-10T18:09:18Z
- **Completed:** 2026-08-10T18:12:20Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments

- Surfaced soft/strict `fallback_to_torch` on StatusSnapshot → create_app → AppState → `/api/status` (False preserved)
- CLI injects `rt.fallback_to_torch` into create_app; UI footer shows reason on live-null/mismatch + soft/strict hint
- EDGE-RT-04 automated: serve constructs DepthAnythingWorker / YoloeOpenVocabWorker outside factory; no ORT/TRT depth claims
- Dual-model export docs ship measure-on-device YOLO+DAV2, sticky soft/strict, and retire Phase 11 deferral language

## Task Commits

Each task was committed atomically:

1. **Task 1: Operator surface — fallback_to_torch status/banner/UI** - `871b158` (feat)
2. **Task 2 RED: EDGE-RT-04 + dual-model docs honesty tests** - `d4d3341` (test)
3. **Task 2 GREEN: dual-model docs + EDGE-RT-04 lock** - `06d01c3` (feat)

**Plan metadata:** docs commit on main (`docs(11-02): complete operator surface and dual-model guardrails plan`)

_Note: Task 2 followed TDD (RED test commit → GREEN docs/impl commit)._

## Files Created/Modified

- `src/sentry_ai/capture/status.py` — `fallback_to_torch: bool | None = None`
- `src/sentry_ai/api/app.py` — create_app kwarg + app.state + AppState mirror
- `src/sentry_ai/api/deps.py` — AppState.fallback_to_torch
- `src/sentry_ai/api/routes_preview.py` — honesty field loop includes fallback_to_torch
- `src/sentry_ai/cli.py` — inject fallback_to_torch into create_app
- `src/sentry_ai/ui/static/index.html` — reason when live missing/differs; soft/strict suffix
- `tests/test_backend_honesty_status.py` — True/False pass-through; retire ort_loader_not_implemented
- `tests/test_edge_rt04_torch_only.py` — EDGE-RT-04 static construction proofs
- `tests/test_export_docs.py` — dual-model + sticky + no Phase 11 deferral keywords
- `docs/export/yolo26-onnx-tensorrt.md` — shipped dual-model guardrails section
- `docs/export/jetson-packaging.md` — dual-model honesty + sticky; Phase 11 deferral removed
- `docs/export/README.md` — dual-model / measure-on-device hard rule pointer

## Decisions Made

- Used `bool | None` for status field (matches plan locked decision; not string enum)
- UI compact soft/strict suffix only when reason shown (soft) or always for strict — no FPS invention
- EDGE-RT-04 proofs are source-inspection only (no GPU/weight/Jetson) per plan

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None — no new secrets or external services.

## Known Stubs

None — no TODO/placeholder stubs that block plan goals.

## Threat Flags

None — no new trust-boundary surfaces beyond plan threat model (status pass-through + docs honesty).

## TDD Gate Compliance

- RED: `d4d3341` test(11-02) EDGE-RT-04 + export docs honesty (3 export tests failed before docs)
- GREEN: `06d01c3` feat(11-02) docs + lock (73 combined factory/honesty/edge_rt04/export tests green)
- REFACTOR: ruff format only (folded into GREEN commit)

## Verification

```text
uv run pytest tests/test_edge_rt04_torch_only.py tests/test_export_docs.py \
  tests/test_backend_honesty_status.py tests/test_detection_factory.py -q --tb=short
# 73 passed
```

## Self-Check: PASSED

- All key files FOUND
- Commits 871b158, d4d3341, 06d01c3 FOUND
- No blocking stubs
