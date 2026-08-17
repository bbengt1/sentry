---
phase: 19
slug: online-consent-honesty-state
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-15
---

# Phase 19 — Validation Strategy

> Source: `19-RESEARCH.md` + plans 19-01 / 19-02. Hardware policy: **synthetic / static only**.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run (19-01)** | `uv run pytest tests/test_calibration_state.py tests/test_calibration_persist.py tests/test_calibration_fit.py -q` |
| **Quick run (19-02)** | `uv run pytest tests/test_calibration_state.py tests/test_calibration_persist.py tests/test_api_calibration.py -q` |
| **Full suite** | `uv run pytest -q` |
| **Hardware policy** | No room, no Jetson, no CUDA, no `--extra depth` in default CI |

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] `CalibrationState()` boots `online=False` / not applied (19-01)
- [ ] `set_online(True)` while unapplied raises and does not apply / does not promote kind (19-01)
- [ ] First `metric_calibrated` still requires `apply()` or `apply_params` / `try_reapply`; enabling online after consent does not change scale (19-01)
- [ ] `try_reapply` match leaves `is_online() is False` (19-01)
- [ ] Cancel = draft only; applied + online unchanged (19-02)
- [ ] Clear = applied + YAML gone + online forced off (19-02)
- [ ] Disable-online leaves applied + YAML; status `online_off` (19-02)
- [ ] Snapshot / GET expose `online_off` (and the four-way enum) separate from `depth.kind` and persist (19-02)
- [ ] Phase 19 never transitions to `auto_committed` or `rejected` (19-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| ONL-01 | Online opt-in, default off | `test_calibration_state.py` | 19-01 |
| ONL-01 | Status can represent `online_off` (distinct plane) | `test_calibration_state.py` + `test_api_calibration.py` | 19-02 |
| ONL-02 | Enable unapplied does not invent first scale | `test_calibration_state.py` | 19-01 |
| ONL-02 | `try_reapply` / `apply` remain first-scale paths | `test_calibration_persist.py` + state tests | 19-01 |
| ONL-06 | Cancel = draft only | `test_calibration_state.py` + `test_api_calibration.py` | 19-02 |
| ONL-06 | Clear = applied + YAML; online forced off | `test_calibration_persist.py` + API | 19-02 |
| ONL-06 | Disable-online ≠ Clear | `test_calibration_persist.py` + API | 19-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green (`uv sync --extra dev` only)

**Approval:** plans validated; execute pending
