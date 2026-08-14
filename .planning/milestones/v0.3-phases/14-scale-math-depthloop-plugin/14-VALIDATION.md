---
phase: 14
slug: scale-math-depthloop-plugin
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-12
---

# Phase 14 — Validation Strategy

> Source: `14-RESEARCH.md` § Validation Architecture + plans 14-01 / 14-02.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_calibration_fit.py tests/test_calibration_state.py tests/test_depth_loop.py tests/test_calibration_validators.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Hardware policy** | Synthetic only — no room, no real depth weights for new Phase 14 tests |

---

## Sampling Rate

- Per task commit: fit + state + depth_loop targeted tests
- Per wave: full suite + ruff
- Phase gate: full suite green before `/gsd:verify-work`

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Tests: scale-only median recovers known scale — `tests/test_calibration_fit.py` (14-01)
- [ ] Tests: affine lstsq recovers scale+offset for N≥2 — `tests/test_calibration_fit.py` (14-01)
- [ ] Tests: reject non-positive observations / insufficient samples — `tests/test_calibration_fit.py` (14-01)
- [ ] Tests: reject absurd scale outside (1e-4, 1e4) — `tests/test_calibration_fit.py` (14-01)
- [ ] Tests: reject residual_rms above max(0.15*median(D), 0.05) — `tests/test_calibration_fit.py` (14-01)
- [ ] Tests: `apply_map` copy-on-write float32 when applied+valid — `tests/test_calibration_state.py` (14-02)
- [ ] Tests: DepthLoop + FakeDepthWorker promotes kind and scales map — `tests/test_depth_loop.py` (14-02)
- [ ] Tests: inactive calibration leaves relative product unchanged — `tests/test_depth_loop.py` (14-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| CAL-01 | Median / affine fit recovers params | test_calibration_fit | 14-01 |
| CAL-02 | Invalid fits rejected with reason codes | test_calibration_fit | 14-01 |
| CAL-03 | apply_map transforms when applied | test_calibration_state | 14-02 |
| CAL-03 | DepthLoop hook before set_depth | test_depth_loop | 14-02 |
| Guard | Honesty regression still green | test_calibration_validators / store honesty | 14-02 verify |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green

**Approval:** plans validated; execute pending
