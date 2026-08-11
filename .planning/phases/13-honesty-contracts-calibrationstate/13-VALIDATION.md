---
phase: 13
slug: honesty-contracts-calibrationstate
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-08-11
---

# Phase 13 — Validation Strategy

> Source: `13-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_depth_kind.py tests/test_calibration_state.py tests/test_perception_contracts.py -q` (adjust to actual filenames) |
| **Full suite command** | `uv run pytest -q` |
| **Hardware policy** | Synthetic only — no room, no real depth weights required for honesty unit tests |

---

## Sampling Rate

- Per task commit: honesty + CalibrationState unit tests
- Per wave: full suite + ruff
- Phase gate: full suite green

---

## Wave 0 Requirements

- [ ] Tests: relative never pairs with `unit="m"` on depth payload validators
- [ ] Tests: free-space rejects relative + meters (or equivalent honesty matrix)
- [ ] Tests: `metric_calibrated` requires `unit="m"`
- [ ] Tests: CalibrationState draft vs applied; draft not `is_calibrated`
- [ ] Tests: promotion helper only for applied+valid
- [ ] Tests: store rejects dishonest kind/unit if assert added

---

## Validation Sign-Off

- [ ] All tasks have automated verify
- [ ] `nyquist_compliant: true` after plan Dimension 8 pass

**Approval:** pending
