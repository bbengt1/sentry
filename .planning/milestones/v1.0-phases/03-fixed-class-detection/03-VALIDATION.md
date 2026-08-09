---
phase: 3
slug: fixed-class-detection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-07
---

# Phase 3 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 |
| **Quick run** | `uv run pytest tests/test_detection_mapping.py tests/test_detection_worker.py -q` |
| **Full suite** | `uv run pytest -q` |
| **Lint** | `uv run ruff check src tests` |
| **CI note** | Mock YOLO; no weight download in default CI |

## Sampling Rate

- Per task: quick module tests  
- Per wave: full pytest + ruff  
- Phase gate: full suite green  

## Wave 0 Requirements

- [ ] `tests/test_detection_mapping.py`
- [ ] `tests/test_detection_worker.py`
- [ ] `tests/test_detection_loop.py`
- [ ] `tests/test_detection_overlay.py`
- [ ] `tests/test_api_detection.py`
- [ ] `tests/test_model_cache.py`
- [ ] fixtures/fake YOLO results in conftest
- [ ] optional-dependencies `detect` for ultralytics

## Threats (for plans)

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-3-01 | Malicious/arbitrary weights | Known filenames only; resolve under cache root |
| T-3-02 | Unauthenticated conf change on LAN | Localhost default |
| T-3-03 | Dual detection truth UI≠API | Single PerceptionStore |
| T-3-04 | Capture/UI stall from inference | DetectionLoop keep-latest separate thread |
| T-3-05 | AGPL undisclosed | THIRD_PARTY_MODELS + README |

## Manual-Only

| Behavior | Why |
|----------|-----|
| Real YOLO on synthetic/USB | Optional; network + weights |
| First-download then offline | Manual network off after cache |

**Approval:** pending
