---
phase: 09-live-ort-fixed-class-yolo
plan: 02
subsystem: detection
tags: [onnxruntime, yolo, parity, golden, backend-honesty, testing]

requires:
  - phase: 09-live-ort-fixed-class-yolo
    provides: "Live ORT factory branch (backend_live=onnxruntime on path+dep+.onnx weights)"
provides:
  - "ORT-02 Detection wire-contract parity on factory live ORT path (mocks only)"
  - "Runtime set_conf reflected in predict conf on ORT-path worker"
  - "Empty predict → [] on ORT factory path"
  - "Status honesty pass-through for live=onnxruntime"
  - "ORT-04 golden/parity suite without Jetson/GPU ORT/real ONNX load"
affects:
  - 10-live-tensorrt
  - 11-sticky-fallback
  - phase-09-verification

tech-stack:
  added: []
  patterns:
    - "Parity via resolve/dep monkeypatch + FakeModel inject — never real YOLO(*.onnx) in default CI"
    - "Assert backend_live=onnxruntime + .onnx weights before process asserts (T-09-07)"
    - "Status honesty inject live ORT triple without recomputing from preferred"

key-files:
  created:
    - tests/test_ort_parity.py
  modified:
    - tests/test_backend_honesty_status.py

key-decisions:
  - "Local FakeModel/_FakeBoxes in parity module (no shared-fixture churn)"
  - "Live path helper fails loud if factory soft-stubs instead of live ORT"
  - "No opt-in real ORT integration test in default suite this plan"

patterns-established:
  - "Parity suite always injects model=FakeModel; forbid real ONNX load in CI"
  - "Honesty live=onnxruntime fixture mirrors soft-stub inject style"

requirements-completed: [ORT-02, ORT-04]

duration: 2min
completed: 2026-08-09
---

# Phase 9 Plan 02: ORT Process Parity + Status Honesty Summary

**Mock-only golden suite proves factory live ORT path yields schema-identical Detections (class/conf/bbox/source=fixed), runtime conf, and status honesty for live=onnxruntime — no Jetson, GPU ORT, or real ONNX load.**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-09T22:19:38Z
- **Completed:** 2026-08-09T22:21:00Z
- **Tasks:** 2/2
- **Files modified:** 2

## Accomplishments

- Added `tests/test_ort_parity.py` covering Detection wire contract, `set_conf` → predict conf, empty `[]`, and live weights honesty guards
- Extended backend honesty status with live ORT triple (`requested=onnxruntime`, `live=onnxruntime`, `reason=None`) on `/api/status` + StatusSnapshot
- Phase 9 automated dimension suite green (53 focused + full suite 488 passed, 1 skipped)
- Spine freeze intact — no DetectionLoop / FrameBus / PerceptionStore / `/v1` edits

## Task Commits

Each task was committed atomically:

1. **Task 1: ORT process parity + conf golden tests (ORT-02, ORT-04)** - `cb582f6` (test)
2. **Task 2: Status honesty fixture for live ORT + phase suite gate** - `55bbdab` (test)

**Plan metadata:** (see final docs commit on branch)

## Files Created/Modified

- `tests/test_ort_parity.py` — Live ORT factory parity: process contract, conf, empty list, weights guard
- `tests/test_backend_honesty_status.py` — Live ORT status pass-through + StatusSnapshot fields

## Decisions Made

- **Local fakes:** Prefer file-local `FakeModel` / `_FakeBoxes` over shared helpers to avoid cross-suite churn
- **Fail-loud live path:** `_live_ort_build` asserts `backend_live=="onnxruntime"` + `.onnx` weights before any process asserts (mitigates soft-stub spoof)
- **No real ORT load:** Default suite never constructs `ultralytics.YOLO` on onnx files; no `@pytest.mark` integration requiring onnxruntime package

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Pre-existing ruff F841 warnings in `tests/test_artifact_paths.py` are out of scope (not introduced by this plan).

## User Setup Required

None for CI/default path.

## Known Stubs

None. Production live ORT path remains from 09-01; this plan is test-only. TensorRT remains intentional Phase 8 soft-stub for Phase 10.

## Threat Flags

None — no new network endpoints, auth paths, file access, or schema changes. Test doubles only.

## Verification Results

| Check | Result |
|-------|--------|
| Phase gate pytest (7 modules) | 53 passed |
| Full `pytest -q` | 488 passed, 1 skipped |
| `ruff check` on new/modified tests | All checks passed |
| No `InferenceSession` in `src/sentry_ai` | empty |
| Spine freeze (loop/bus/store/routes_v1) | intact |
| Default suite requires onnxruntime install | no |

## Ready for Phase Verification

Yes. ORT-01..04 automated dimensions are green under the combined suite. Phase 9 is ready for `/gsd:verify-phase` (or equivalent).

## Self-Check: PASSED

- FOUND: `tests/test_ort_parity.py`
- FOUND: `tests/test_backend_honesty_status.py` (live ORT fixtures)
- FOUND: `cb582f6`
- FOUND: `55bbdab`
