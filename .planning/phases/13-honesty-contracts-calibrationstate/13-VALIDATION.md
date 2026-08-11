---
phase: 13
slug: honesty-contracts-calibrationstate
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-11
---

# Phase 13 — Validation Strategy

> Source: `13-RESEARCH.md` § Validation Architecture + plans 13-01 / 13-02.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_calibration_validators.py tests/test_calibration_state.py tests/test_perception_store_depth_honesty.py tests/test_schemas_depth_kind.py tests/test_depth_mapping.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Hardware policy** | Synthetic only — no room, no real depth weights for honesty unit tests |

---

## Sampling Rate

- Per task commit: honesty + CalibrationState unit tests (quick command)
- Per wave: full suite + ruff
- Phase gate: full suite green before `/gsd:verify-work`

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Tests: relative never pairs with `unit="m"` on depth payload validators — `tests/test_schemas_depth_kind.py` + `tests/test_calibration_validators.py` (13-01)
- [ ] Tests: free-space rejects relative + meters and estimated + meters — `tests/test_calibration_validators.py` (13-01)
- [ ] Tests: `metric_calibrated` requires `unit="m"` — depth_kind + calibration_validators (13-01)
- [ ] Tests: store rejects dishonest kind/unit — `tests/test_perception_store_depth_honesty.py` (13-01)
- [ ] Tests: CalibrationState draft vs applied; draft not calibrated — `tests/test_calibration_state.py` (13-02)
- [ ] Tests: promotion helper only for applied+valid — validators pure + state wrapper (13-01/02)
- [ ] Tests: fingerprint fields on params — `tests/test_calibration_state.py` (13-02)
- [ ] Tests: `kind_for_mode` never calibrated — `tests/test_depth_mapping.py` (13-01)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| CAL-05 | DepthPayload rejects relative + m | test_schemas_depth_kind / test_calibration_validators | 13-01 |
| CAL-05 | FreeSpacePayload rejects uncalibrated + m | test_calibration_validators | 13-01 |
| CAL-05 | Store rejects relative + m | test_perception_store_depth_honesty | 13-01 |
| CAL-05 | Draft does not promote | test_calibration_state | 13-02 |
| CAL-04 | Calibrated requires unit=m | test_schemas_depth_kind / test_calibration_validators | 13-01 |
| CAL-04 | promote only applied+valid | test_calibration_validators + test_calibration_state | 13-01/02 |
| CAL-04 | Applied+valid → pair | test_calibration_state | 13-02 |
| Success #4 | Fingerprint fields | test_calibration_state | 13-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green

**Approval:** plans validated; execute pending
