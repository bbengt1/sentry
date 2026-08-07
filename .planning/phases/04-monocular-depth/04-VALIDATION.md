---
phase: 4
slug: monocular-depth
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-07
---

# Phase 4 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Quick | `uv run pytest tests/test_depth_worker.py tests/test_depth_mapping.py -q` |
| Full | `uv run pytest -q` |
| CI | Mock depth model; no HF download |

## Wave 0

- [ ] `tests/test_depth_worker.py`
- [ ] `tests/test_depth_loop.py`
- [ ] `tests/test_depth_mapping.py` / preprocess golden
- [ ] `tests/test_depth_overlay.py`
- [ ] `tests/test_api_depth.py` or extend snapshot tests
- [ ] `tests/test_depth_kind_honesty.py` (relative never meters in UI/payload)
- [ ] optional-dependencies `depth`

## Threats

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-4-01 | Relative sold as meters | DepthKind + validators + UI badge |
| T-4-02 | NC weights as default | Apache Small only default |
| T-4-03 | Dual truth UI≠API | Single store product |
| T-4-04 | Capture stall from depth | DepthLoop keep-latest thread |
| T-4-05 | Path traversal cache | Resolve under SENTRY_MODEL_CACHE |

## Manual

| Real DAV2 on synthetic/USB | Optional after `uv sync --extra depth` |
| Offline after first HF cache | Manual |

**Approval:** pending
