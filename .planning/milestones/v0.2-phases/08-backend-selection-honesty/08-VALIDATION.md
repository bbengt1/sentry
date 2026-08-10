---
phase: 8
slug: backend-selection-honesty
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-09
---

# Phase 8 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Config | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick | `uv run pytest tests/test_detection_factory.py tests/test_artifact_paths.py tests/test_backend_honesty_status.py -q` |
| Full | `uv run pytest -q` |
| Hardware | **No Jetson / no GPU / no weight download** in default CI |

## Dimension Coverage

| Req | Dimension | Wave 0 file | Assert |
|-----|-----------|-------------|--------|
| BACK-01 | Factory branch select | `tests/test_detection_factory.py` | preferred torch → live torch; ORT/TRT preferred → live torch + reason (Phase 8 stub) |
| BACK-01 | Never false live | same | `backend_live` never `onnxruntime`/`tensorrt` in Phase 8 |
| BACK-02 | Status honesty | `tests/test_backend_honesty_status.py` | StatusSnapshot + `/api/status` include requested + live |
| BACK-02 | Banner | `tests/test_cli_serve.py` (extend) | serve source/banner includes backend_live / factory |
| BACK-04 | Path allowlist | `tests/test_artifact_paths.py` | rejects `..`, out-of-root; accepts allowlisted stem+suffix under cache |
| EDGE-RT-01 | Spine frozen | `tests/test_detection_loop.py` + plan file ownership | DetectionLoop still process→store; no bus redesign |
| EDGE-RT-02 | Serve factory | `tests/test_cli_serve.py` | `inspect.getsource(serve)` uses `build_detection_worker` |
| EDGE-RT-03 | Profile honesty | `tests/test_detection_factory.py` | desktop-gpu → torch/torch; jetson → tensorrt requested, torch live |

## Wave 0 Checklist

- [ ] `tests/test_detection_factory.py`
- [ ] `tests/test_artifact_paths.py`
- [ ] `tests/test_backend_honesty_status.py`
- [ ] Update `tests/test_cli_serve.py` for factory + banner honesty
- [ ] Optional: Live Preview footer asserts if UI shows backend pair

## Threats

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-8-01 | Path traversal via env artifact path | resolve + is_relative_to + stem/suffix allowlist |
| T-8-02 | Status claims live TRT when torch | Factory sole author of backend_live; unit tests |
| T-8-03 | Hard-fail serve when ORT preferred | Soft stub torch + reason (Phase 8) |
| T-8-04 | DetectionLoop backend coupling | Do not edit loop.py |

## Sampling

- **Per task:** targeted quick tests for touched req  
- **Per wave:** `uv run pytest -q` + `uv run ruff check src tests`  
- **Phase gate:** all BACK/EDGE-RT rows green before verify-work  

**Approval:** planner + plan-check
