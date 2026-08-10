---
phase: 10-live-tensorrt-fixed-class-yolo
plan: 01
subsystem: detection
tags: [tensorrt, yolo, factory, backend-selection, parity, status-honesty]

requires:
  - phase: 09-live-ort-fixed-class-yolo
    provides: "Live ORT factory branch pattern, WorkerBuild honesty, FakeModel parity suite"
  - phase: 08-backend-selection-honesty
    provides: "Artifact resolve, soft-stub TRT, status pass-through"
provides:
  - "Live TRT factory branch (backend_live=tensorrt on path+dep+.engine weights)"
  - "Soft-fallback reasons trt_artifact_missing / trt_dep_missing / path_rejected"
  - "TRT Detection contract parity suite via mocks (no Jetson/system TRT)"
  - "Status honesty live TRT triple pass-through"
affects:
  - 10-02-on-device-docs
  - 11-sticky-fallback

tech-stack:
  added: []
  patterns:
    - "Ultralytics-native YOLO(*.engine) via YoloDetectionWorker weights= path"
    - "find_spec('tensorrt') dep probe without module-level tensorrt import"
    - "backend_live=tensorrt only with resolved .engine worker weights"
    - "No tensorrt pip extra; system/JetPack only"

key-files:
  created:
    - tests/test_trt_parity.py
  modified:
    - src/sentry_ai/models/detection/factory.py
    - tests/test_detection_factory.py
    - tests/test_backend_honesty_status.py

key-decisions:
  - "Reuse YoloDetectionWorker with weights=str(engine_path); no thin TRT wrapper"
  - "Dep probe via importlib.util.find_spec('tensorrt') only; no hard factory import"
  - "Retire trt_loader_not_implemented; reason codes trt_artifact_missing|trt_dep_missing|path_rejected"
  - "No CUDA probe at factory; mirror ORT find_spec only"
  - "No tensorrt pip extra added this plan"

patterns-established:
  - "Live claim iff path + dep + worker._weights ends with .engine"
  - "Pre-build torch worker only on soft-fallback branches; live path constructs engine weights worker"
  - "Parity suite asserts backend_live=tensorrt + .engine before process asserts"

requirements-completed: [TRT-01, TRT-04]

duration: 4min
completed: 2026-08-10
---

# Phase 10 Plan 01: Live TensorRT Factory + Parity + Status Honesty Summary

**Factory claims live TensorRT only when allowlisted `.engine` + system `tensorrt` find_spec succeed with Ultralytics-native `YoloDetectionWorker(weights=*.engine)`; soft-fallback reason codes match VALIDATION; Detection parity and status honesty proven with mocks only (no Jetson/system TRT/real engine load).**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-10T14:54:58Z
- **Completed:** 2026-08-10T14:58:40Z
- **Tasks:** 3/3
- **Files modified:** 4

## Accomplishments

- Flipped Phase 8 TRT soft-stub into live factory branch: `backend_live=tensorrt` only with resolved `.engine` weights + `_tensorrt_available()` True
- Soft-fallback matrix: `trt_artifact_missing` / `trt_dep_missing` / `path_rejected` → torch; retired `trt_loader_not_implemented` as default
- TRT parity suite (`tests/test_trt_parity.py`) proves Detection contract + set_conf + empty list on factory live path with FakeModel
- Status honesty: live TRT triple pass-through; soft fixtures use `trt_artifact_missing`
- Full plan suite green: 58 passed; spine freeze intact; no tensorrt pip extra; no module-level TRT import

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Live factory TRT honesty matrix tests** - `2274c4c` (test)
2. **Task 1 GREEN: Live TensorRT factory branch** - `e52472b` (feat)
3. **Task 2: TRT process parity + conf golden suite (TRT-04)** - `c968ce0` (test)
4. **Task 3: Live TRT status honesty triple + soft reason fixtures** - `294c3cf` (test)

**Plan metadata:** `b088196` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/models/detection/factory.py` — Live TRT branch, `_tensorrt_available`, reason chain; ORT path untouched
- `tests/test_detection_factory.py` — Live TRT success + three soft-falls + import hygiene; jetson default → `trt_artifact_missing`
- `tests/test_trt_parity.py` — Detection contract, set_conf, empty list, honesty guard on `.engine` weights
- `tests/test_backend_honesty_status.py` — Live TRT triple + soft reason `trt_artifact_missing`

## Decisions Made

- Mirrored Phase 9 ORT live branch 1:1 for TRT (resolve → artifact missing → dep missing → live)
- No extra CUDA probe at factory; system TRT importability is the sole dep gate
- Reused `YoloDetectionWorker` (no TRT wrapper class); `model=` inject keeps CI free of real engines
- Honesty status fixtures migrated off `trt_loader_not_implemented` to VALIDATION soft codes

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Correctness] Docstring mentioned `check_tensorrt` string**
- **Found during:** Task 1 acceptance `rg`
- **Issue:** Module docstring said "Never calls Ultralytics `check_tensorrt()`" which failed the empty-`rg` acceptance gate
- **Fix:** Rephrased to "Never triggers Ultralytics auto-pip TRT install" without the forbidden identifier
- **Files modified:** `src/sentry_ai/models/detection/factory.py`
- **Committed in:** `e52472b` / docstring tweak retained in later ruff commit

**2. [Rule 3 - Blocking] Ruff E501 on module docstrings**
- **Found during:** Task 3 verification
- **Issue:** First-line module docstrings exceeded 88 chars after TRT-01 tagging
- **Fix:** Shortened factory + factory-test module docstrings
- **Files modified:** `factory.py`, `test_detection_factory.py`
- **Committed in:** `294c3cf`

**Total deviations:** 2 auto-fixed (Rule 2, Rule 3)
**Impact on plan:** Cosmetic/gate compliance only; no scope creep.

## Issues Encountered

None beyond the two auto-fixes above.

## User Setup Required

None — no new packages, env vars, or external services. On-device engine lifecycle + Jetson packaging honesty are 10-02.

## Known Stubs

None. Live TRT path is real factory logic; CI uses injectable FakeModel by design (not a production stub). Soft-fallback when artifact/dep missing is intentional honesty, not incomplete work.

## Threat Flags

None new beyond plan threat model. Mitigations applied:
- T-10-01: live only with path+dep+.engine weights (unit-asserted)
- T-10-04: find_spec only; no `import tensorrt` / no Ultralytics auto-pip call
- T-10-06/07: parity asserts live+engine before process; FakeModel only
- T-10-SC: no new pip packages

## Verification

```text
uv run pytest tests/test_detection_factory.py tests/test_trt_parity.py \
  tests/test_backend_honesty_status.py tests/test_detection_mapping.py \
  tests/test_detection_worker.py tests/test_artifact_paths.py -q
# 58 passed

uv run ruff check src/sentry_ai/models/detection/factory.py \
  tests/test_detection_factory.py tests/test_trt_parity.py \
  tests/test_backend_honesty_status.py
# All checks passed

rg -n 'trt_loader_not_implemented' src/sentry_ai/models/detection/factory.py  # empty
rg -n 'import tensorrt|from tensorrt' src/sentry_ai/models/detection/factory.py  # empty
rg -n 'check_tensorrt' src/sentry_ai  # empty
```

Spine freeze: no edits to `loop.py`, `frame_bus.py`, `perception_store.py`, `routes_v1.py`.

## Success Criteria Mapping

| Criterion | Status |
|-----------|--------|
| preferred TRT + valid `.engine` + dep → live=tensorrt + .engine weights | Met |
| Missing artifact / dep / path_rejected → torch + exact reasons | Met |
| Detection contract parity (class, conf, bbox, source=fixed) | Met |
| Runtime conf on TRT-path worker | Met |
| Status honesty live=tensorrt pass-through | Met |
| Mocks only — no Jetson/system TRT/real engine | Met |
| Spine freeze + sole factory author + no tensorrt extra | Met |

## Next Phase Readiness

- 10-02 can document on-device engine lifecycle + Jetson packaging honesty (TRT-02 / TRT-03)
- Sticky thrash-free fallback remains Phase 11

## Self-Check: PASSED

- FOUND: `src/sentry_ai/models/detection/factory.py`
- FOUND: `tests/test_detection_factory.py`
- FOUND: `tests/test_trt_parity.py`
- FOUND: `tests/test_backend_honesty_status.py`
- FOUND: commits `2274c4c`, `e52472b`, `c968ce0`, `294c3cf`
