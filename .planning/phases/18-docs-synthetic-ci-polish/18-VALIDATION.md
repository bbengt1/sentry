---
phase: 18
slug: docs-synthetic-ci-polish
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-14
---

# Phase 18 — Validation Strategy

> Source: `18-RESEARCH.md` + plans 18-01 / 18-02. Hardware policy: **synthetic / static only**.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run (18-01)** | `uv run pytest tests/test_calibration_docs.py tests/test_safety_docs.py tests/test_desktop_docs.py tests/test_edge_serve_docs.py -q` |
| **Quick run (18-02)** | `uv run pytest tests/test_v03_honesty_matrix.py tests/test_edge_ci_workflow.py tests/test_calibration_fit.py tests/test_calibration_store.py tests/test_calibration_persist.py tests/test_calibration_validators.py tests/test_free_space_bands.py -q` |
| **Full suite** | `uv run pytest -q` |
| **Hardware policy** | No room, no Jetson, no CUDA, no `--extra depth` in default CI |

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] `tests/test_calibration_docs.py` exists; forbids stale “always ordinal” / FSD-as-claim / “precise meters” / autonomous-as-claim on hub surfaces (18-01)
- [ ] `docs/calibration.md` exists with wizard + STACK persist path + honesty triad + Cancel/Clear + persist status (18-01)
- [ ] Root README + `docs/README.md` link the calibration hub (18-01)
- [ ] `perception-frame.md` / safety / desktop-gpu / architecture / api / cli / configuration no longer claim always-ordinal / omit persist (18-01)
- [ ] `tests/test_v03_honesty_matrix.py` documents existing fit/apply/honesty/persist suites; files exist (18-02)
- [ ] `ci.yml` still `ubuntu-latest` + `uv sync --extra dev` + ruff + pytest + `sentry health`; no `--extra depth` / jetson / cuda (18-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| OPS-02 | Operator hub: wizard, persist path, honesty, no vehicle-grade | `test_calibration_docs.py` | 18-01 |
| OPS-02 | No doc drift to “always ordinal” | same + `test_safety_docs.py` | 18-01 |
| OPS-03 | Fit/apply/honesty/persist covered synthetically | `test_v03_honesty_matrix.py` + existing suites | 18-02 |
| OPS-03 | Default CI hardware-free | `test_edge_ci_workflow.py` | 18-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green (`uv sync --extra dev` only)

**Approval:** plans validated; execute pending
