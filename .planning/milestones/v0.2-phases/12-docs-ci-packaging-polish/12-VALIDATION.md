---
phase: 12
slug: docs-ci-packaging-polish
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-10
---

# Phase 12 — Validation Strategy

> Source: `12-RESEARCH.md` § Validation Architecture (and related maps).

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_export_docs.py tests/test_detection_factory.py tests/test_backend_honesty_status.py tests/test_pyproject_onnx_extra.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **CI** | `.github/workflows/ci.yml` — ruff + pytest + `sentry health` on ubuntu-latest, `uv sync --extra dev` only |
| **Hardware policy** | No Jetson / no TensorRT GPU / no real `.engine` load in default GHA |

---

## Sampling Rate

- **Per task commit:** keyword/docs + factory/honesty subset
- **Per wave:** full quick set + ruff
- **Phase gate:** full suite green

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-* | 01 | 1 | EDGE-DOC-01 | keyword | `pytest tests/test_export_docs.py -q` | ⚠️ extend | ⬜ pending |
| 12-01-* | 01 | 1 | EDGE-DOC-02 | keyword/static | THIRD_PARTY + export lineage tests | ⚠️ extend | ⬜ pending |
| 12-02-* | 02 | 1+ | EDGE-CI-01 | unit | factory + honesty + artifact tests | ✅ keep | ⬜ pending |
| 12-02-* | 02 | 1+ | EDGE-CI-02 | static | workflow no Jetson/GPU job assert | ❌ W0 | ⬜ pending |

---

## Wave 0 Requirements

- [ ] Extend `tests/test_export_docs.py` — export→serve narrative; no “export-only TRT”; no fake FPS in edge docs
- [ ] AGPL lineage keywords for derived `.onnx`/`.engine` in THIRD_PARTY_MODELS / docs
- [ ] Static test on `.github/workflows/ci.yml` — no tensorrt GPU runner, no Jetson required
- [ ] Keep packaging tests: no tensorrt optional extra; wheel hygiene
- [ ] Existing factory/honesty matrix remains green (EDGE-CI-01)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Instructions |
|----------|-------------|------------|--------------|
| Real Jetson export→serve path | EDGE-DOC-01 | Hardware | Follow docs on device; not CI |

---

## Validation Sign-Off

- [ ] All tasks automated or Wave 0
- [ ] `nyquist_compliant: true` after plans pass Dim 8

**Approval:** pending
