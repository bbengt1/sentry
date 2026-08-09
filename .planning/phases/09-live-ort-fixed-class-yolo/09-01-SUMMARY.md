---
phase: 09-live-ort-fixed-class-yolo
plan: 01
subsystem: detection
tags: [onnxruntime, yolo, factory, backend-selection, packaging, export-docs]

requires:
  - phase: 08-backend-selection-honesty
    provides: "WorkerBuild factory soft-stubs, artifact resolve, honesty pass-through"
provides:
  - "Live ORT factory branch (backend_live=onnxruntime on path+dep+.onnx weights)"
  - "Soft-fallback reasons ort_artifact_missing / ort_dep_missing / path_rejected"
  - "Optional onnx extra pin onnxruntime>=1.20,<1.29"
  - "Export/architecture/configuration honesty for live ORT conditions"
affects:
  - 09-02-parity-golden
  - 10-live-tensorrt
  - 11-sticky-fallback

tech-stack:
  added: ["onnxruntime>=1.20,<1.29 (optional onnx extra)"]
  patterns:
    - "Ultralytics-native YOLO(*.onnx) via YoloDetectionWorker weights= path"
    - "find_spec dep probe without module-level onnxruntime import"
    - "backend_live=onnxruntime only with resolved .onnx worker weights"

key-files:
  created:
    - tests/test_pyproject_onnx_extra.py
  modified:
    - src/sentry_ai/models/detection/factory.py
    - tests/test_detection_factory.py
    - pyproject.toml
    - docs/export/yolo26-onnx-tensorrt.md
    - docs/export/README.md
    - docs/architecture.md
    - docs/configuration.md
    - src/sentry_ai/config/profiles/cpu-fallback.yaml
    - tests/test_export_docs.py

key-decisions:
  - "Reuse YoloDetectionWorker with weights=str(onnx_path); no thin ORT wrapper"
  - "Dep probe via importlib.util.find_spec only; no hard factory import"
  - "Retire ort_loader_not_implemented; reason codes ort_artifact_missing|ort_dep_missing|path_rejected"
  - "onnx extra CPU pin only; no tensorrt or onnxruntime-gpu extra"

patterns-established:
  - "Live claim iff path + dep + worker._weights ends with .onnx"
  - "Pre-build torch worker only on soft-fallback branches; live path constructs onnx weights worker"
  - "Docs split live ORT conditions vs offline export vs non-live TRT"

requirements-completed: [ORT-01, ORT-03]

duration: 3min
completed: 2026-08-09
---

# Phase 9 Plan 01: Live ORT Factory + onnx Extra + Docs Honesty Summary

**Factory claims live ONNX Runtime only when allowlisted `.onnx` + dep probe succeed with Ultralytics-native `YoloDetectionWorker(weights=*.onnx)`; optional `onnx` extra pins CPU ORT; docs describe live conditions and soft-fallback honesty.**

## Performance

- **Duration:** 3 min
- **Started:** 2026-08-09T22:14:19Z
- **Completed:** 2026-08-09T22:16:54Z
- **Tasks:** 3/3
- **Files modified:** 10

## Accomplishments

- Flipped Phase 8 ORT soft-stub into live factory branch: `backend_live=onnxruntime` only with resolved `.onnx` weights + `_onnxruntime_available()` True
- Soft-fallback matrix: `ort_artifact_missing` / `ort_dep_missing` / `path_rejected` → torch; TRT remains `trt_loader_not_implemented`
- Shipped optional `onnx = ["onnxruntime>=1.20,<1.29"]` with static pin tests; no tensorrt/gpu-ort extra
- Export, architecture, configuration, and `cpu-fallback.yaml` honesty updated for live ORT + install path
- Full suite green: 482 passed, 1 skipped; no Jetson/GPU ORT/weight downloads required

## Task Commits

Each task was committed atomically:

1. **Task 1: Live factory ORT branch + honesty matrix tests (ORT-01)** - `a3978c7` (feat)
2. **Task 2: Optional onnx extra pin (ORT-03 packaging)** - `17002be` (feat)
3. **Task 3: Docs honesty for live ORT + export keyword tests (ORT-03)** - `4c392f3` (docs)

**Plan metadata:** `611e9e1` (docs: complete plan) + `177b8a3` (chore: uv.lock onnx extra)

## Files Created/Modified

- `src/sentry_ai/models/detection/factory.py` — Live ORT branch, `_onnxruntime_available`, reason chain
- `tests/test_detection_factory.py` — Live success + soft-fallback matrix + import hygiene
- `pyproject.toml` — Optional `onnx` extra pin + install comment
- `tests/test_pyproject_onnx_extra.py` — Static pin / no-tensorrt / no-gpu-ort asserts
- `docs/export/yolo26-onnx-tensorrt.md` — Live ORT conditions + soft-fallback + TRT non-live
- `docs/export/README.md` — Live ORT optional path; torch default; TRT export-only
- `docs/architecture.md` — ORT may be live; TRT policy/export; onnx extra row
- `docs/configuration.md` — onnxruntime can be live with artifact+extra
- `src/sentry_ai/config/profiles/cpu-fallback.yaml` — Comments: live ORT when .onnx+dep
- `tests/test_export_docs.py` — Keyword asserts for live ORT + `--extra onnx`

## Decisions Made

- **Worker reuse:** `YoloDetectionWorker(weights=str(path), …, model=model)` — no custom InferenceSession
- **Probe:** `importlib.util.find_spec("onnxruntime")` inside `_onnxruntime_available()` only
- **Reason vocabulary:** retired `ort_loader_not_implemented` from ORT branch; TRT keeps Phase 8 stub
- **Packaging:** CPU `onnxruntime` pin only; GPU ORT docs-only; no tensorrt extra

## Deviations from Plan

None - plan executed exactly as written.

Minor note (not a deviation): architecture optional-extras table gained an `onnx` row for honesty parity with detect/depth (within Task 3 docs scope).

## Issues Encountered

None

## User Setup Required

None for CI/default path. Makers who want live ORT:

```bash
uv sync --extra detect --extra onnx
# Place allowlisted yolo26n.onnx or set SENTRY_DETECTOR_ONNX
uv run sentry serve --profile cpu-fallback
```

## Known Stubs

None that block plan goals. TensorRT remains intentional Phase 8 soft-stub (`trt_loader_not_implemented`) for Phase 10.

## Verification Results

| Check | Result |
|-------|--------|
| `pytest` factory + pin + export + artifact | 42 passed |
| Full `pytest -q` | 482 passed, 1 skipped |
| `backend_live="onnxruntime"` only on success path | match |
| `ort_artifact_missing` / `ort_dep_missing` present | match |
| `ort_loader_not_implemented` retired from factory | empty |
| No `import onnxruntime` / `tensorrt` in factory | empty |
| `onnxruntime>=1.20,<1.29` in pyproject | match |
| Spine freeze (loop/bus/store/routes) | intact |

## Ready for 09-02

Yes. Factory live branch + reason codes + packaging/docs honesty are in place for parity/golden process tests (ORT-02 / ORT-04).

## Self-Check: PASSED

- FOUND: `src/sentry_ai/models/detection/factory.py`
- FOUND: `tests/test_detection_factory.py`
- FOUND: `pyproject.toml` onnx extra
- FOUND: `tests/test_pyproject_onnx_extra.py`
- FOUND: export/architecture/configuration docs + cpu-fallback.yaml
- FOUND: `a3978c7`, `17002be`, `4c392f3`
