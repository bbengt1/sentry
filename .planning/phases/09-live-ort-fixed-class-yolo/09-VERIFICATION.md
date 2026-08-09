---
phase: 09-live-ort-fixed-class-yolo
verified: 2026-08-09T22:23:47Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 0
re_verification: false
gaps: []
deferred: []
human_verification: []
---

# Phase 9: Live ORT Fixed-Class YOLO — Verification Report

**Phase Goal:** Makers can run fixed-class YOLO live via ONNX Runtime when the profile prefers `onnxruntime` and a valid `.onnx` artifact is present — same Detection wire contract as PyTorch  
**Verified:** 2026-08-09T22:23:47Z  
**Status:** passed  
**Re-verification:** No — initial verification  

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | With `preferred_backend=onnxruntime` and a valid `.onnx` artifact + optional `onnx` extra, fixed-class YOLO runs live (not torch-only under an ORT label) | ✓ VERIFIED | `factory.py` live ORT branch: resolve path → dep probe → `YoloDetectionWorker(weights=str(path))` with `backend_live="onnxruntime"`, `backend_reason=None`. Soft-falls: `ort_artifact_missing` / `ort_dep_missing` / `path_rejected` → `backend_live="torch"`. Tests: `test_live_ort_success_with_artifact_and_dep`, soft-fallback matrix, honesty weight guard. |
| 2 | ORT path produces the same `Detection` wire contract (class, conf, bbox_xyxy, source=fixed) as the PyTorch path | ✓ VERIFIED | Live ORT factory path + `FakeModel` → `process()` → `results_to_detections` → `Detection(class_name, confidence, bbox_xyxy)` with schema default `source="fixed"`. `test_ort_process_detection_contract`, `test_ort_set_conf_applies_on_next_process`, `test_ort_empty_predict_returns_empty_list`. Mapping golden suite green (shared postprocess). |
| 3 | Optional `onnx` (or equivalent) extra is documented for install; CI does not require GPU ORT | ✓ VERIFIED | `pyproject.toml` optional-deps: `onnx = ["onnxruntime>=1.20,<1.29"]`; no `tensorrt` extra; no `onnxruntime-gpu`. Docs: `docs/export/yolo26-onnx-tensorrt.md`, `docs/export/README.md`, architecture/configuration honesty + `uv sync --extra detect --extra onnx`. Tests: `test_pyproject_onnx_extra.py`, `test_export_docs_live_ort_conditions_and_onnx_extra`. |
| 4 | Golden/parity tests (mock session or fixture) prove postprocess mapping without Jetson hardware | ✓ VERIFIED | `tests/test_ort_parity.py`: monkeypatch `_try_resolve_artifact` + `_onnxruntime_available`, inject `model=FakeModel` — never real `YOLO("*.onnx")`, no Jetson, no GPU ORT. `test_detection_mapping.py` unchanged shared path. Default suite green without edge hardware. |

**Score:** 4/4 truths verified

### Plan-Level Truths (supporting detail — all verified)

| Truth | Status | Evidence |
|-------|--------|----------|
| Missing `.onnx` → `backend_live=torch` + `ort_artifact_missing` | ✓ | factory L153–159; `test_cpu_fallback_ort_soft_stub_artifact_missing` |
| Missing onnxruntime dep → `ort_dep_missing` | ✓ | factory L160–166; `test_ort_soft_fallback_dep_missing` |
| `path_rejected` → torch + reason | ✓ | factory L146–152; `test_ort_soft_fallback_path_rejected` |
| Live ORT only with resolved `.onnx` weights (not `.pt` under ORT label) | ✓ | factory L168–179; `test_never_live_ort_with_pt_weights`, `test_ort_live_weights_are_onnx_not_pt` |
| TRT remains Phase 8 soft-stub; no tensorrt pip extra | ✓ | factory L181–189; `test_jetson_tensorrt_soft_stub`; pyproject has no tensorrt extra |
| Factory sole author of `backend_live`; no module-level ort/trt import; spine frozen | ✓ | factory imports = stdlib + internal only; `test_factory_module_does_not_import_ort_trt`; phase 9 commits touch no DetectionLoop/FrameBus/PerceptionStore/`/v1` |
| Status honesty pass-through when `backend_live=onnxruntime` | ✓ | `test_api_status_honesty_onnxruntime_live`, `test_status_snapshot_accepts_live_onnxruntime` |
| `set_conf` on ORT-path worker reflected in next predict | ✓ | `test_ort_set_conf_applies_on_next_process` |
| Empty predict → `[]` not `None` | ✓ | `test_ort_empty_predict_returns_empty_list` |

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sentry_ai/models/detection/factory.py` | Live ORT branch + soft fallbacks + `_onnxruntime_available` | ✓ VERIFIED | ~198 lines; live claim only after path+dep; find_spec probe; TRT soft-stub retained |
| `pyproject.toml` | optional `onnx` extra pin | ✓ VERIFIED | `onnxruntime>=1.20,<1.29`; comment documents `--extra onnx` |
| `tests/test_detection_factory.py` | Live ORT success + soft-fallback matrix + import hygiene | ✓ VERIFIED | live success, dep/path/artifact soft-falls, never-live-with-pt, import hygiene |
| `tests/test_pyproject_onnx_extra.py` | Static pin assertion | ✓ VERIFIED | pin form, no tensorrt, no gpu ort |
| `docs/export/yolo26-onnx-tensorrt.md` | Live ORT conditions + install honesty | ✓ VERIFIED | Live/soft-fall table; uv sync path; CI honesty |
| `tests/test_export_docs.py` | Keyword asserts for live ORT + onnx extra | ✓ VERIFIED | `test_export_docs_live_ort_conditions_and_onnx_extra` |
| `tests/test_ort_parity.py` | ORT-02/04 process + conf + source=fixed | ✓ VERIFIED | 4 tests; mock-only live path |
| `tests/test_backend_honesty_status.py` | Live=onnxruntime status fixture | ✓ VERIFIED | `test_api_status_honesty_onnxruntime_live` + snapshot accept |
| `tests/test_detection_mapping.py` | Unchanged mapping golden | ✓ VERIFIED | Shared torch/ORT postprocess; suite green |
| `src/sentry_ai/config/profiles/cpu-fallback.yaml` | Comment honesty for live ORT conditions | ✓ VERIFIED | preferred onnxruntime; soft torch when missing |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `build_detection_worker` onnxruntime branch | `_try_resolve_artifact` / `resolve_detector_artifact` | consume Path; reject → path_rejected; None → ort_artifact_missing | ✓ WIRED | factory L145–159 |
| live ORT success | `YoloDetectionWorker(weights=str(path))` | Ultralytics-native YOLO("*.onnx"); `model=` inject for tests | ✓ WIRED | factory L168–173 |
| live ORT claim | `_onnxruntime_available` / `find_spec` | probe before `backend_live=onnxruntime`; no top-level import | ✓ WIRED | factory L72–74, L160–166 |
| `pyproject` onnx extra | docs/export install guidance | `uv sync --extra detect --extra onnx` | ✓ WIRED | pyproject comment + export docs + configuration.md |
| `tests/test_ort_parity.py` | live ORT factory branch | resolve/dep monkeypatch + FakeModel | ✓ WIRED | `_live_ort_build` asserts live before process |
| `YoloDetectionWorker.process` | `results_to_detections` | same predict → Results → Detection as torch | ✓ WIRED | yolo_worker L127–137 |
| Detection schema | `source=fixed` default | mapper omits source; schema supplies ORT-02 | ✓ WIRED | mapping L103–108; perception `source=…="fixed"` |
| `cli.serve` | `build_detection_worker` → create_app backend_* | factory sole author; status pass-through | ✓ WIRED | cli.py L368–382, L451–452 (Phase 8 wiring, still intact) |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `build_detection_worker` ORT branch | `backend_live` / `backend_reason` | preferred_backend + resolve + find_spec | Yes — branch decisions from real path/dep probes | ✓ FLOWING |
| Live ORT worker | `_weights` | resolved `.onnx` Path | Yes — `str(path)` only on live path | ✓ FLOWING |
| `YoloDetectionWorker.process` | `list[Detection]` | model.predict → results_to_detections | Yes — FakeModel inject in tests; real YOLO load when model=None | ✓ FLOWING |
| Detection.source | `source` | schema default `"fixed"` (mapper omits) | Yes — default applied at construct | ✓ FLOWING |
| `/api/status` backend_* | requested/live/reason | create_app app.state from WorkerBuild | Yes — pass-through; live ORT fixture asserts | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 9 verification suite | `uv run pytest tests/test_detection_factory.py tests/test_ort_parity.py tests/test_backend_honesty_status.py tests/test_pyproject_onnx_extra.py tests/test_export_docs.py tests/test_detection_mapping.py -q` | **47 passed**, 1 warning | ✓ PASS |
| Factory live claim + no hard ort import | `inspect` factory source | `backend_live="onnxruntime"` present; no `import onnxruntime` | ✓ PASS |
| Detection schema default | construct Detection without source | `source == "fixed"` | ✓ PASS |
| onnx extra pin | tomllib optional-dependencies | `['onnxruntime>=1.20,<1.29']` | ✓ PASS |
| Dep probe without package | `_onnxruntime_available()` in default env | `False` (soft path still tested via monkeypatch) | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| — | — | No phase-declared `scripts/*/tests/probe-*.sh` | SKIP (N/A) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ORT-01 | 09-01 | Live fixed-class YOLO via ORT when preferred + valid `.onnx` | ✓ SATISFIED | factory live branch + factory tests |
| ORT-02 | 09-02 | Same Detection wire contract as PyTorch | ✓ SATISFIED | test_ort_parity process contract + mapping golden |
| ORT-03 | 09-01 | Optional onnx extra documented; CI no GPU ORT | ✓ SATISFIED | pyproject + docs + pin/export tests |
| ORT-04 | 09-02 | Golden/parity without Jetson | ✓ SATISFIED | mock-only test_ort_parity; no hardware deps |

No orphaned Phase 9 requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/TODO/HACK/PLACEHOLDER in phase-touched production/test files | — | — |

Notes (info only, not gaps):
- `tests/test_backend_honesty_status.py` still includes a soft-stub fixture with reason `ort_loader_not_implemented` (Phase 8 label) for **status pass-through** coverage. Factory no longer emits that as the default ORT outcome; live path uses `ort_artifact_missing` / `ort_dep_missing` / `path_rejected` or live success. Not a debt marker and not dishonest factory behavior.
- Parity suite intentionally injects FakeModel — real CPU ORT load is opt-in/not merge gate per plan (ORT-04).

### Human Verification Required

None for phase gate. Real-device `YOLO("*.onnx")` with installed `onnx` extra is operator-path optional and explicitly out of default CI merge criteria.

### Gaps Summary

No gaps. All four roadmap success criteria and supporting plan must-haves are achieved in the codebase with green automated evidence.

---

_Verified: 2026-08-09T22:23:47Z_  
_Verifier: Claude (gsd-verifier)_
