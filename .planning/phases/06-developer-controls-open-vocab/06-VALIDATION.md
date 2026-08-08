---
phase: 6
slug: developer-controls-open-vocab
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-08
---

# Phase 6 — Validation Strategy

## Test Infrastructure

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 |
| Quick | `uv run pytest tests/test_pipeline_config.py tests/test_open_vocab*.py -q` |
| Full | `uv run pytest -q` |
| Weights | Mock YOLO/YOLOE in unit tests |

## Wave 0

- [ ] `tests/test_pipeline_config.py` — stage flags + free-space cutoffs API
- [ ] `tests/test_loop_enable_flags.py` — workers skip when disabled
- [ ] `tests/test_open_vocab_worker.py` — mock YOLOE set_classes/predict
- [ ] `tests/test_open_vocab_loop.py` — on_demand / continuous / off
- [ ] `tests/test_assemble_open_vocab.py` — merge source tags
- [ ] UI contract tests or fixture HTML checks for controls panel

## Threats

| ID | Pattern | Mitigation |
|----|---------|------------|
| T-6-01 | Dual writer thrash on detections | Separate OpenVocabProduct; assembler merges |
| T-6-02 | Teardown race enable/disable | Flags not stop/start threads |
| T-6-03 | Always-on YOLOE GPU thrash | Default off; on_demand / every_n |
| T-6-04 | AGPL undisclosed YOLOE | THIRD_PARTY_MODELS + README |
| T-6-05 | Motor/control language in UI | Copy review |

**Approval:** pending
