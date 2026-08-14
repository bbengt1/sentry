---
phase: 15
slug: wizard-rest-live-preview-ui
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-13
---

# Phase 15 — Validation Strategy

> Source: `15-RESEARCH.md` § Validation Architecture + plans 15-01 / 15-02.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_api_calibration.py tests/test_api_preview.py tests/test_cli_calibration_inject.py tests/test_calibration_state.py tests/test_calibration_fit.py tests/test_depth_loop.py tests/test_api_depth.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Hardware policy** | Synthetic only — no room, no real depth weights for new Phase 15 tests |

---

## Sampling Rate

- Per task commit: targeted ASGI + state + inject tests
- Per wave: full suite + ruff
- Phase gate: full suite green before `/gsd:verify-work`

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Tests: GET/POST calibration 503 without inject — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: sample from seeded store fills `observed_raw` — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: sample while applied returns 409 — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: compute ok stages draft; rejected fit 422 and no draft — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: apply sets `calibration_active`; snapshot kind stays base until loop — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: cancel drops draft only; cancel after apply leaves applied — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: clear drops applied — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: extra=forbid 422; FakeDepthWorker.process never called — `tests/test_api_calibration.py` (15-01)
- [ ] Tests: `/api/status` additive calibration fields — `tests/test_api_calibration.py` / `tests/test_api_preview.py` (15-01)
- [ ] Tests: CLI injects same object into DepthLoop and create_app — `tests/test_cli_calibration_inject.py` (15-01)
- [ ] Tests: wizard panel strings + honesty denylist — `tests/test_api_preview.py` (15-02)
- [ ] Tests: HTML never locally assigns `metric_calibrated` — `tests/test_api_preview.py` (15-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| WIZ-01 | Collect samples + stage fit | test_api_calibration | 15-01 |
| WIZ-02 | Apply commits; Cancel = clear_draft; Clear = clear_applied | test_api_calibration | 15-01 |
| WIZ-03 | Count / residual / calibrated vs relative labeling | index.html + test_api_preview | 15-02 |
| WIZ-04 | Draft never claims metric_calibrated on live kind | test_api_calibration | 15-01 |
| OPS-01 | Status + Live Preview show active vs relative | routes_preview + index.html tests | 15-01/02 |
| Guard | Honesty + fit + DepthLoop regressions | test_calibration_* / test_depth_loop / test_api_depth | 15-01 verify |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green

**Approval:** plans validated; execute pending
