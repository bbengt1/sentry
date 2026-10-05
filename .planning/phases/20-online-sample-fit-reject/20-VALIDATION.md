---
phase: 20
slug: online-sample-fit-reject
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-01
---

# Phase 20 — Validation Strategy

> Source: `20-RESEARCH.md` + plans 20-01 / 20-02. Hardware policy: **synthetic / static only**.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run (20-01)** | `uv run pytest tests/test_online_sampler.py tests/test_calibration_state.py tests/test_calibration_persist.py -q` |
| **Quick run (20-02)** | `uv run pytest tests/test_online_sampler.py tests/test_calibration_fit.py tests/test_calibration_state.py -q` |
| **Full suite** | `uv run pytest -q` |
| **Hardware policy** | No room, no Jetson, no CUDA, no `--extra depth` in default CI. Pass `now_s`; do not sleep. |

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Default window is 8 accepts and 1.0 s; same timestamp does not fill the window (20-01)
- [ ] Online off, unapplied, and no-anchors `consider` write no draft samples (20-01)
- [ ] Successful `apply()` captures anchors and does not enable online; `apply_params` does not invent anchors (20-01)
- [ ] Cancel clears the window only; Clear clears anchors and applied; disable-online clears neither applied nor anchors (20-01)
- [ ] `map_space="applied"` stores pre-apply `observed_raw` (20-01)
- [ ] Sampler does not call `apply` / `apply_params` / `apply_map` (20-01, re-checked 20-02)
- [ ] Full consistent window stages draft params only; applied scale and `online_status` stay put (20-02)
- [ ] `ok=False` (residual or absurd scale) does not stage draft params and does not change applied (20-02)
- [ ] Phase 20 never sets `auto_committed` or `rejected` (20-02)
- [ ] `DepthLoop` does not import the sampler (20-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| ONL-03 | Samples are draft; kind/unit stay on applied | `test_online_sampler.py` | 20-01, 20-02 |
| ONL-03 | Throttle and frame gate; no hot-path hook | `test_online_sampler.py` | 20-01 |
| ONL-03 | Cancel / Clear / disable stay distinct around the window | `test_online_sampler.py` + `test_calibration_state.py` | 20-01 |
| ONL-04 | `ok=True` is `set_draft_params` only | `test_online_sampler.py` | 20-02 |
| ONL-04 | `ok=False` never becomes applied | `test_online_sampler.py` | 20-02 |
| ONL-04 | Gates reused (`absurd_scale`, residual); fit module unchanged | `test_online_sampler.py` + existing `test_calibration_fit.py` | 20-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green (`uv sync --extra dev` only)

**Approval:** plans validated; execute pending
