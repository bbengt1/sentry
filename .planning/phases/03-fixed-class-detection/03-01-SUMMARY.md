---
phase: 03-fixed-class-detection
plan: 01
subsystem: detection
tags: [yolo26, ultralytics, modelworker, framebus, perception-store, model-cache, det-01, det-02, model-02]

# Dependency graph
requires:
  - phase: 02-camera-ingest-live-preview
    provides: FrameBus, CaptureLoop, ImageFrame, ModelWorker protocol, Detection schema
provides:
  - YoloDetectionWorker (injectable ModelWorker for YOLO26)
  - results_to_detections pure mapper (DET-02)
  - DetectionLoop FrameBus subscriber thread
  - PerceptionStore keep-latest detection product
  - configure_model_cache / tier_to_weight (MODEL-02)
  - optional-dependencies.detect (ultralytics-opencv-headless)
  - yolo-fixed plugin entry point
affects:
  - 03-02-overlays-api-ui
  - phase-04-depth
  - phase-06-open-vocab

# Tech tracking
tech-stack:
  added:
    - ultralytics-opencv-headless>=8.4.33,<9 (optional extra detect)
  patterns:
    - Injectable model for CI (no weight download in tests)
    - Duck-typed Ultralytics Results → Detection mapping
    - CaptureLoop-shaped DetectionLoop (bus get_latest → store)
    - FrameBus-shaped PerceptionStore keep-latest isolation
    - Lazy ultralytics import; pure path helpers always work

key-files:
  created:
    - src/sentry_ai/models/cache.py
    - src/sentry_ai/models/detection/mapping.py
    - src/sentry_ai/models/detection/yolo_worker.py
    - src/sentry_ai/models/detection/loop.py
    - src/sentry_ai/state/perception_store.py
    - tests/test_model_cache.py
    - tests/test_detection_mapping.py
    - tests/test_detection_worker.py
    - tests/test_detection_loop.py
    - tests/test_perception_store.py
    - tests/test_detection_overlay.py
    - tests/test_api_detection.py
  modified:
    - pyproject.toml
    - uv.lock
    - THIRD_PARTY_MODELS.md
    - README.md
    - src/sentry_ai/plugins/registry.py
    - src/sentry_ai/config/profiles/desktop-gpu.yaml
    - tests/conftest.py
    - tests/test_plugins_registry.py
    - tests/test_third_party_models_doc.py

key-decisions:
  - "ultralytics-opencv-headless optional extra only — never plain ultralytics (OpenCV GUI conflict)"
  - "InferenceBackend stays stubs; YOLO not wrapped in infer(tensor)"
  - "desktop-gpu detector_tier m→s (RESEARCH recommendation)"
  - "Thread-safe conf read each process() for DET-03 foundation"
  - "API/overlay/serve wiring deferred to 03-02"

patterns-established:
  - "ModelWorker with injectable model= for unit tests without torch/weights"
  - "DetectionLoop: FrameBus.get_latest → worker.process → PerceptionStore.set_detections"
  - "configure_model_cache before real YOLO load; SENTRY_MODEL_CACHE / ~/.cache/sentry-ai"
  - "results_to_detections duck-types boxes.xyxy/conf/cls + names; empty → []"

requirements-completed: [DET-01, DET-02, MODEL-02]

# Metrics
duration: 6min
completed: 2026-08-07
---

# Phase 3 Plan 01: Fixed-Class Detection Core Summary

**YOLO26 ModelWorker + DetectionLoop + PerceptionStore with Sentry-owned model cache and CI-safe mocks — DET-01/DET-02/MODEL-02 at the pipeline layer.**

## Performance

- **Duration:** 6 min
- **Started:** 2026-08-07T19:12:48Z
- **Completed:** 2026-08-07T19:18:48Z
- **Tasks:** 3/3
- **Files modified:** ~25

## Accomplishments

- Optional `detect` extra installs `ultralytics-opencv-headless` without forcing torch on default/dev CI path
- Pure `results_to_detections` maps fake/real YOLO boxes to schema-valid `Detection` (class_name, confidence, bbox_xyxy)
- `DetectionLoop` daemon reads only `FrameBus.get_latest()`, skips same `frame_id`, writes keep-latest `PerceptionStore`
- `YoloDetectionWorker` supports injectable model, runtime conf under lock, lazy YOLO load after `configure_model_cache`
- AGPL + offline cache documented; Wave 0 skip stubs for 03-02 overlay/API tests

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 detect extra, package skeleton, model cache, AGPL docs, test stubs** - `e7c9dd1` (feat)
2. **Task 2: Detection mapping (DET-02) + PerceptionStore keep-latest** - RED `4f0394b` (test) → GREEN `56cf63f` (feat)
3. **Task 3: YoloDetectionWorker + DetectionLoop + plugin registration (DET-01)** - RED `653ab19` (test) → GREEN `53185b5` (feat)

**Plan metadata:** (docs commit after this SUMMARY)

_Note: TDD tasks have test → feat commit pairs_

## Files Created/Modified

- `src/sentry_ai/models/cache.py` — `configure_model_cache`, `tier_to_weight`, `default_cache_root`, weight allowlist
- `src/sentry_ai/models/detection/mapping.py` — pure Ultralytics→Detection mapper
- `src/sentry_ai/models/detection/yolo_worker.py` — `YoloDetectionWorker` ModelWorker
- `src/sentry_ai/models/detection/loop.py` — `DetectionLoop` bus subscriber
- `src/sentry_ai/state/perception_store.py` — `PerceptionStore` + `DetectionProduct`
- `pyproject.toml` — `detect` optional dep + `yolo-fixed` entry point
- `THIRD_PARTY_MODELS.md` / `README.md` — Phase 3 active AGPL + cache offline notes
- `src/sentry_ai/plugins/registry.py` — register yolo-fixed when importable
- `src/sentry_ai/config/profiles/desktop-gpu.yaml` — detector_tier `s`
- Tests: mapping, store, worker, loop, model_cache; skip stubs for overlay/API

## Decisions Made

- Followed plan locked decisions: YOLO26 via Ultralytics headless package; DetectionLoop not CaptureLoop; InferenceBackend stubs untouched; overlays/API deferred to 03-02
- `desktop-gpu` tier `m` → `s` per RESEARCH discretion
- Worker conf is runtime-only on the worker (no ModelsConfig.detector_conf field yet)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff B011 on Wave 0 skip stubs**
- **Found during:** Task 3 (full `ruff check src tests`)
- **Issue:** `assert False` in skipped placeholder tests fails B011
- **Fix:** Replaced with `raise AssertionError("should be skipped")`
- **Files modified:** `tests/test_api_detection.py`, `tests/test_detection_overlay.py`
- **Verification:** ruff clean; suite 148 passed, 2 skipped
- **Committed in:** `53185b5`

**2. [Rule 1 - Bug] Loop docstring matched architecture assert**
- **Found during:** Task 3 (`test_loop_source_has_no_videocapture`)
- **Issue:** Docstring phrase `source.read` triggered `assert "source.read" not in source`
- **Fix:** Reworded docstring to avoid literal match while preserving intent
- **Files modified:** `src/sentry_ai/models/detection/loop.py`
- **Verification:** loop architecture test green
- **Committed in:** `53185b5`

**Total deviations:** 2 auto-fixed (Rule 1)
**Impact on plan:** Minor correctness/lint only; no scope creep. Overlays/API remain deferred.

## Issues Encountered

- `from tests.conftest import ...` fails collection (no `tests` package) — switched to pytest fixtures / local fakes (aligned with existing suite style)

## User Setup Required

None for unit tests. Real detection:

```bash
uv sync --extra dev --extra detect
# First run may download yolo26*.pt into SENTRY_MODEL_CACHE or ~/.cache/sentry-ai/weights
```

Commercial users must evaluate Ultralytics AGPL (see THIRD_PARTY_MODELS.md).

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| Overlay tests skipped | `tests/test_detection_overlay.py` | Plan 03-02 |
| API detection tests skipped | `tests/test_api_detection.py` | Plan 03-02 |
| serve / create_app DetectionLoop wiring | not started | Plan 03-02 |

No stubs block 03-01 goals (pipeline core without API/UI surface).

## TDD Gate Compliance

- Task 2: RED `4f0394b` → GREEN `56cf63f` ✓
- Task 3: RED `653ab19` → GREEN `53185b5` ✓

## Verification

- `uv run pytest -q` → 148 passed, 2 skipped
- `uv run ruff check src tests` → clean
- `grep -R VideoCapture src/sentry_ai/models` → no matches
- Unit path never downloads YOLO weights (injectable FakeModel)

## Next Plan Ready

Plan 03-02 can attach: OpenCV overlays, `/api/snapshot`, PATCH conf, MJPEG overlay, `sentry serve` DetectionLoop start, Live Preview conf telemetry.

## Self-Check: PASSED

- All key artifacts present on disk
- Commits e7c9dd1, 4f0394b, 56cf63f, 653ab19, 53185b5 exist
- Full pytest suite green without real YOLO weights
