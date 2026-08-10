---
phase: 11
slug: sticky-fallback-dual-model-guardrails
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-10
---

# Phase 11 — Validation Strategy

> Per-phase validation contract. Source: `11-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_detection_factory.py tests/test_backend_honesty_status.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Estimated runtime** | ~15–40s quick; full suite per project baseline |
| **Hardware policy** | No Jetson / no real `.engine` / no weight download in default CI |

---

## Sampling Rate

- **After every task commit:** quick run command
- **After every plan wave:** factory + honesty + export docs + cli_serve subset
- **Before `/gsd:verify-work`:** full suite green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|----------------|-----------------|-----------|-------------------|-------------|--------|
| 11-01-W0 | 01 | 0 | BACK-03 | T-11-01 | Sticky resolve; no silent TRT/ORT claim | unit | factory + honesty | ⚠️ extend | ⬜ pending |
| 11-01-* | 01 | 1+ | BACK-03 | T-11-01 | Soft/strict policy + log once | unit | `pytest -k soft_fallback or strict or log_once` | ❌ W0 | ⬜ pending |
| 11-02-* | 02 | 1+ | EDGE-RT-04 | T-11-02 | Depth/OV torch-only; dual-model docs | unit/keyword | edge_rt04 + export_docs | ❌ W0 | ⬜ pending |
| 11-02-* | 02 | 1+ | BACK-03 | — | Status pass-through mode/reason | unit | honesty status | ✅ extend | ⬜ pending |

---

## Wave 0 Requirements

- [ ] `tests/test_detection_factory.py` — strict mode matrix + log-once (caplog) + sticky single-resolve contract
- [ ] `tests/test_edge_rt04_torch_only.py` — depth/OV never use factory ORT/TRT
- [ ] `tests/test_export_docs.py` — soft vs strict keywords; dual-model non-claims; sticky language
- [ ] `tests/test_backend_honesty_status.py` — fallback_mode if shipped; soft reason fixtures current
- [ ] Framework install already present via `uv sync --extra dev`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Dual-model VRAM on Jetson (TRT YOLO + torch depth) | EDGE-RT-04 | Device-specific | Measure on device; docs say measure-on-device only |
| Strict mode fail-closed UX on serve | BACK-03 | Optional smoke | Set strict, omit engine, confirm non-zero exit / clear banner |

---

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 deps
- [ ] Sampling continuity OK
- [ ] Wave 0 covers MISSING refs
- [ ] `nyquist_compliant: true` after plans pass Dimension 8

**Approval:** pending
