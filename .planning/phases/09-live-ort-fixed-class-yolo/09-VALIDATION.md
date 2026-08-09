---
phase: 9
slug: live-ort-fixed-class-yolo
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 9 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (workspace 9.1.1) |
| Config | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick | `uv run pytest tests/test_detection_factory.py tests/test_ort_parity.py tests/test_detection_mapping.py tests/test_detection_worker.py -q` |
| Full | `uv run pytest -q` |
| Lint | `uv run ruff check src tests` |
| Hardware | **No Jetson / no GPU ORT / no weight download** in default CI |
| Optional real ORT | Only if `onnxruntime` installed **and** explicit opt-in marker; never required for merge |

## Dimension Coverage

| Req | Dimension | Wave 0 file | Assert |
|-----|-----------|-------------|--------|
| ORT-01 | Live ORT when preferred + artifact + dep | `tests/test_detection_factory.py` (extend) | `backend_requested=onnxruntime`, `backend_live=onnxruntime`, `backend_reason is None`, `worker._weights` ends with `.onnx` |
| ORT-01 | Soft fallback artifact missing | same | resolve None → `backend_live=torch`, reason=`ort_artifact_missing` |
| ORT-01 | Soft fallback dep missing | same | available False → `backend_live=torch`, reason=`ort_dep_missing` |
| ORT-01 | Soft fallback path_rejected | same | invalid env path → reason=`path_rejected`, live=torch |
| ORT-01 | Never claim ORT while torch weights | same | if live=onnxruntime then weights suffix `.onnx`; if weights `.pt` then live≠onnxruntime |
| ORT-01 | TRT still soft-stub | same | jetson → live=torch, `trt_loader_not_implemented` |
| ORT-02 | Detection wire contract | `tests/test_ort_parity.py` + mapping | `class_name`, `confidence`, `bbox_xyxy`, `source=="fixed"` |
| ORT-02 | Mapping golden unchanged | `tests/test_detection_mapping.py` | existing box→Detection cases still green |
| ORT-03 | `onnx` extra pin | static test or factory docs test | `pyproject.toml` has `onnx` extra with `onnxruntime>=1.20,<1.29` |
| ORT-03 | CI no GPU ORT | suite policy | no test requires `onnxruntime-gpu` or Jetson; factory import has no module-level ORT |
| ORT-03 | Docs install path | `tests/test_export_docs.py` (extend) | live ORT + `uv sync --extra onnx` (or equivalent) mentioned; not “export target only” for fixed-class ORT |
| ORT-04 | Parity without Jetson | `tests/test_ort_parity.py` | FakeModel inject on factory ORT live path; process returns Detection list |
| conf | Runtime conf on ORT path | `tests/test_ort_parity.py` | `set_conf` reflected in next FakeModel.predict conf kwarg |
| EDGE-RT-01 | Spine frozen | ownership + existing loop tests | no edits to DetectionLoop/bus/store/`/v1` for ORT |
| Honesty | Status pass-through | `tests/test_backend_honesty_status.py` (optional extend) | fixture with live=onnxruntime still round-trips `/api/status` |

## Wave 0 Checklist

- [ ] Rewrite/extend `tests/test_detection_factory.py`
  - Remove or narrow `test_backend_live_never_ort_or_trt` (Phase 8 global ban is obsolete)
  - Add live ORT success (monkeypatch resolve + dep probe + FakeModel)
  - Add `ort_artifact_missing`, `ort_dep_missing` cases
  - Keep `path_rejected`, torch desktop, TRT soft-stub, factory no top-level ORT import
- [ ] Add `tests/test_ort_parity.py`
  - Factory ORT live + FakeModel → Detection fields + `source=="fixed"`
  - `set_conf` applies on next process
  - Empty predict → `[]`
- [ ] Extend `tests/test_export_docs.py` (and/or small pyproject pin test)
  - Live ORT language for fixed-class when artifact present
  - `onnx` extra / `onnxruntime` install documented
  - Still forbid multi-SKU engine copy (TRT rules unchanged)
- [ ] Optional: honesty status fixture `requested=onnxruntime, live=onnxruntime, reason=None`
- [ ] Ensure default suite does **not** call real `YOLO("*.onnx")` load

## Threats

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-9-01 | Status claims live ORT while `.pt` runs | Assert weights suffix ↔ backend_live coupling |
| T-9-02 | Path traversal via `SENTRY_DETECTOR_ONNX` | Existing artifact allowlist tests remain green |
| T-9-03 | CI requires GPU ORT / Jetson | Mocks only; no gpu package in extra |
| T-9-04 | Truncated `.onnx` in tests causes load errors | Inject FakeModel; never real load in default CI |
| T-9-05 | Factory module imports onnxruntime at import time | Source inspect test forbids `import onnxruntime` / `from onnxruntime` |
| T-9-06 | DetectionLoop backend coupling | Do not edit `loop.py` |
| T-9-07 | conf ignored on ORT path | Parity test set_conf → predict kwargs |
| T-9-08 | Ultralytics auto-install side effect | Dep probe before live claim; document extra |

## Reason-code contract (assertable)

| Condition | backend_requested | backend_live | backend_reason |
|-----------|-------------------|--------------|----------------|
| preferred torch | torch | torch | None |
| preferred ORT + valid `.onnx` + dep OK | onnxruntime | **onnxruntime** | None |
| preferred ORT + no artifact | onnxruntime | torch | `ort_artifact_missing` |
| preferred ORT + no onnxruntime | onnxruntime | torch | `ort_dep_missing` |
| preferred ORT + path_rejected | onnxruntime | torch | `path_rejected` |
| preferred TRT (Phase 9) | tensorrt | torch | `trt_loader_not_implemented` |

**Retired:** `ort_loader_not_implemented` as the default ORT outcome (Phase 8). Tests must not require it for the success path.

## Sampling

- **Per task:** targeted quick tests for touched req (`-k ort` / parity file)
- **Per wave:** `uv run pytest -q` + `uv run ruff check src tests`
- **Phase gate:** all ORT-01..04 rows green; full suite green; no Jetson/GPU required before `/gsd:verify-work`

## Success criteria mapping (roadmap)

| Roadmap success item | Automated proof |
|----------------------|-----------------|
| Live ORT when preferred + artifact + onnx extra | Factory unit: live=onnxruntime + weights `.onnx` |
| Same Detection contract | Parity + mapping tests |
| Optional onnx extra documented; CI no GPU ORT | pyproject/docs tests + suite policy |
| Golden/parity without Jetson | `test_ort_parity.py` with FakeModel |

## Nyquist compliance notes

- Feedback per task: automated pytest < 30s for ORT slice  
- No dimension is manual-only for ORT-01..04  
- Real CPU ORT end-to-end with exported `yolo26n.onnx` is **optional manual** / opt-in — not phase gate  

**Approval:** planner + plan-check after Wave 0 test files land in plan tasks
