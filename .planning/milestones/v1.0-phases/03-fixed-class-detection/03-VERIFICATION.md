---
phase: 03-fixed-class-detection
verified: 2026-08-07T19:29:41Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Install detect extra and run live preview with synthetic (or USB) source"
    expected: "Boxes + class labels + confidences drawn on MJPEG; conf slider changes filtering without restart; /api/snapshot detections match overlay content"
    why_human: "Real YOLO weight download and visual overlay quality cannot be asserted in CI (mock path by design)"
  - test: "After first weight download, disconnect network and re-run serve"
    expected: "Detection still works from SENTRY_MODEL_CACHE / ~/.cache/sentry-ai/weights without re-download"
    why_human: "Offline re-run after real Ultralytics download is an operator path; unit tests only verify cache path policy"
---

# Phase 3: Fixed-Class Detection Verification Report

**Phase Goal:** Deliver the first robot-usable AI signal — local fixed-class detection on the live stream with UI/API parity.
**Verified:** 2026-08-07T19:29:41Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | Local OSS fixed-class detector runs on live frames without cloud | ✓ VERIFIED | `YoloDetectionWorker` + `DetectionLoop` on `FrameBus.get_latest()` only; no cloud URLs; `allow_cloud` rejected in serve; optional `detect` extra (`ultralytics-opencv-headless`); injectable `model=` for CI |
| 2 | Boxes + labels + confidences appear on the dashboard overlay | ✓ VERIFIED | `draw_detections` draws `{class} {conf:.2f}`; MJPEG path calls `store.snapshot()` → `draw_detections` before `imencode`; Live Preview `<img src="/preview/mjpeg">` |
| 3 | Same detections available on stream/snapshot endpoint | ✓ VERIFIED | Single `PerceptionStore` in serve injected into `create_app`; `GET /api/snapshot` and MJPEG both read `store.snapshot()`; parity test asserts snapshot detections match store product |
| 4 | Confidence threshold changes at runtime without process restart | ✓ VERIFIED | `PATCH /api/detection/config` → `worker.set_conf`; conf re-read each `process()` under lock; UI slider debounced 150ms; tests prove worker conf updates without reload |
| 5 | Models cache locally for offline re-runs after first download | ✓ VERIFIED | `configure_model_cache` sets Ultralytics `weights_dir` to `SENTRY_MODEL_CACHE` or `~/.cache/sentry-ai/weights`; docs in README + THIRD_PARTY_MODELS; called before YOLO load in worker/serve |

**Score:** 5/5 truths verified

### Plan-Level Truths (supporting)

| Source | Truth | Status |
| ------ | ----- | ------ |
| 03-01 | `YoloDetectionWorker.process` returns `list[Detection]` without camera (mock YOLO) | ✓ VERIFIED |
| 03-01 | Mapping produces class_name, confidence, bbox_xyxy (DET-02) | ✓ VERIFIED |
| 03-01 | DetectionLoop reads bus, skips same frame_id, writes store; never VideoCapture | ✓ VERIFIED |
| 03-01 | Thread-safe conf read each process() | ✓ VERIFIED |
| 03-01 | optional-dependencies.detect; default/dev path no torch for unit tests | ✓ VERIFIED |
| 03-01 | yolo-fixed entry point; InferenceBackend remains stubs | ✓ VERIFIED |
| 03-02 | Snapshot completeness.detections true including empty list | ✓ VERIFIED |
| 03-02 | Status/UI det count, latency, conf; conf control ~100–200ms debounce | ✓ VERIFIED |
| 03-02 | serve starts DetectionLoop when detect available; degrades when missing | ✓ VERIFIED |
| 03-02 | Handlers never open cameras / run inference | ✓ VERIFIED |
| 03-02 | Localhost default bind; no autonomy/safety language in UI | ✓ VERIFIED |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sentry_ai/models/detection/yolo_worker.py` | YoloDetectionWorker | ✓ VERIFIED | 153 lines; injectable model; set/get_conf; lazy YOLO + cache |
| `src/sentry_ai/models/detection/mapping.py` | results_to_detections | ✓ VERIFIED | 110 lines; pure duck-typed mapper |
| `src/sentry_ai/models/detection/loop.py` | DetectionLoop | ✓ VERIFIED | 118 lines; bus→worker→store daemon |
| `src/sentry_ai/state/perception_store.py` | PerceptionStore single truth | ✓ VERIFIED | 123 lines; keep-latest + metrics |
| `src/sentry_ai/models/cache.py` | configure_model_cache | ✓ VERIFIED | 84 lines; weights_dir + tier_to_weight |
| `src/sentry_ai/models/detection/overlay.py` | draw_detections | ✓ VERIFIED | 51 lines; OpenCV boxes+labels |
| `src/sentry_ai/api/routes_detection.py` | snapshot + conf routes | ✓ VERIFIED | 117 lines; no predict/VideoCapture |
| `src/sentry_ai/api/routes_preview.py` | MJPEG + status det | ✓ VERIFIED | 149 lines; overlay from store |
| `src/sentry_ai/api/app.py` | inject store/worker | ✓ VERIFIED | perception_store + detection_worker |
| `src/sentry_ai/cli.py` | serve DetectionLoop lifecycle | ✓ VERIFIED | single store; det start/stop; degrade path |
| `src/sentry_ai/ui/static/index.html` | conf + det metrics | ✓ VERIFIED | slider, debounce 150ms, Detections/Det ms |
| Tests (mapping/worker/loop/cache/overlay/api/cli) | Coverage | ✓ VERIFIED | All present; suite green |

gsd-sdk `verify.artifacts`: 03-01 **9/9**, 03-02 **8/8**.

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `loop.py` | `FrameBus.get_latest` | DetectionLoop._run | ✓ WIRED | `get_latest` + frame_id skip |
| `loop.py` | `PerceptionStore.set_detections` | after process | ✓ WIRED | success + exception paths |
| `yolo_worker.py` | `results_to_detections` | map predict output | ✓ WIRED | after `model.predict` |
| `cache.py` | ultralytics `weights_dir` | configure_model_cache | ✓ WIRED | settings.update when importable |
| `pyproject.toml` | YoloDetectionWorker | yolo-fixed entry | ✓ WIRED | `sentry_ai.workers` |
| `routes_preview.py` | PerceptionStore | draw before imencode | ✓ WIRED | `store.snapshot` + `draw_detections` |
| `routes_detection.py` | PerceptionFrame | GET /api/snapshot | ✓ WIRED | completeness + detections from product |
| `routes_detection.py` | set_conf | PATCH config | ✓ WIRED | Field ge=0 le=1 extra=forbid |
| `index.html` | /api/detection/config | debounced PATCH | ✓ WIRED | CONF_DEBOUNCE_MS=150 |
| `cli.py` serve | DetectionLoop start/stop | lifecycle | ✓ WIRED | Manual: gsd path `"cli.py serve"` false-negative; code has DetectionLoop(bus, worker, store) + start/stop |

gsd-sdk `verify.key-links`: 03-01 **5/5**; 03-02 **4/5** (cli path label only — code verified manually).

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| DetectionLoop | detections | worker.process(frame) | FakeModel / YOLO predict → mapping | ✓ FLOWING |
| PerceptionStore | _latest product | set_detections from loop | Keep-latest product copy | ✓ FLOWING |
| GET /api/snapshot | PerceptionFrame.detections | store.snapshot() | Same product list | ✓ FLOWING |
| MJPEG overlay | product.detections | store.snapshot() → draw_detections | Same store as snapshot | ✓ FLOWING |
| /api/status det fields | detections_count, det_* | store.snapshot + metrics | Real product metrics | ✓ FLOWING |
| Conf slider | conf | PATCH → worker.set_conf → next predict conf= | Runtime, no restart | ✓ FLOWING |

**Single PerceptionStore (DET-04):** Production path constructs exactly one `PerceptionStore()` in `cli.serve`, passes the same instance to `DetectionLoop(..., store)` and `create_app(perception_store=store, ...)`. No second producer path for detections.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full unit suite | `uv run pytest -q` | 165 passed | ✓ PASS |
| Lint | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Health | `uv run sentry health` | status: ok; workers include yolo-fixed | ✓ PASS |
| Smoke | `uv run sentry smoke` | smoke ok: 3 synthetic frames | ✓ PASS |
| Mock CI (no weights) | suite uses FakeModel / FakeDetectionWorker | no YOLO download in tests | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No probe scripts declared for this phase | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| DET-01 | 03-01 | Fixed-class detector runs locally on live stream | ✓ SATISFIED | YoloDetectionWorker + DetectionLoop + serve wiring |
| DET-02 | 03-01 | Class, confidence, bbox in image coords | ✓ SATISFIED | mapping.py + Detection schema + tests |
| DET-03 | 03-02 | Conf adjustable at runtime without restart | ✓ SATISFIED | set_conf + PATCH + UI slider |
| DET-04 | 03-02 | Overlay + stream same truth | ✓ SATISFIED | Single store → MJPEG + snapshot |
| MODEL-02 | 03-01 | Cacheable for offline after first download | ✓ SATISFIED | configure_model_cache + docs |

No orphaned requirements for Phase 3.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/XXX/TODO in phase-modified source | — | — |
| — | — | No VideoCapture in models/detection or routes_detection | — | — |
| tests/test_api_preview.py | ~124 | MJPEG overlay test asserts JPEG validity only, not pixel delta | ℹ️ Info | Overlay pure-function tests cover drawing; wiring is source-verified |

**Debt-marker gate:** No unreferenced TBD/FIXME/XXX in phase files.

### Confirmation Bias Notes (disconfirmation pass)

1. **Weak integration assert:** `test_mjpeg_generator_with_store_overlay_still_jpeg` does not pixel-diff boxes — mitigated by `test_draw_detections_*` + source wiring of `draw_detections` in generator.
2. **Exception product.error:** Loop writes `error=str(exc)` on failure; survival test asserts next frame succeeds, not that frame-1 error field is set — acceptable for goal (thread stays alive).
3. **Real weight offline path:** Unit tests prove cache *path policy*, not actual Ultralytics download/offline reuse — flagged as human verification.

### Human Verification Required

### 1. Live YOLO overlay + conf (real detect extra)

**Test:** `uv sync --extra dev --extra detect` then `uv run sentry serve --source synthetic`; open http://127.0.0.1:8000/; move conf slider.
**Expected:** Labeled boxes on MJPEG; metrics update; conf changes filtering without restart; `GET /api/snapshot` detections match what is drawn.
**Why human:** Visual appearance + first-run weight download not in CI.

### 2. Offline cache re-run (MODEL-02 operator path)

**Test:** After first successful detection run, run again with network disabled (or offline machine) using same cache root.
**Expected:** Weights load from local cache; detection continues.
**Why human:** Requires real Ultralytics download once.

### Gaps Summary

No blocking gaps. Phase 3 roadmap success criteria and requirements DET-01..04 + MODEL-02 are implemented and wired with a mock-safe CI path. Remaining items are operator/visual checks for real YOLO weights (intentionally out of CI).

---

_Verified: 2026-08-07T19:29:41Z_
_Verifier: Claude (gsd-verifier)_
