---
phase: 21
slug: gated-auto-commit-depthloop-status
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-10-08
---

# Phase 21 — Validation Strategy

> Source: `21-RESEARCH.md` + plans 21-01 / 21-02. Hardware policy: **synthetic / static only**.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run (21-01)** | `uv run pytest tests/test_online_auto_commit.py tests/test_online_sampler.py tests/test_calibration_state.py -q` |
| **Quick run (21-02)** | `uv run pytest tests/test_depth_loop_online.py tests/test_depth_loop.py tests/test_api_calibration_online.py -q` |
| **Full suite** | `uv run ruff check src tests && uv run pytest -q` (CI: `uv sync --extra dev`) |
| **Hardware policy** | No room, no Jetson, no CUDA, no `--extra depth`. Inject `now_s` / monkeypatch `time.monotonic`; do not sleep. |

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Commit only when online, applied, fit ok, residual, `fingerprints_match`, horizon all pass (21-01)
- [ ] Horizon: `scale * median(finite>0 raw) + offset >= 3.0` refuses; exactly 3.0 refuses; empty valid set refuses (21-01)
- [ ] Scale 1000 on raw 1.0 (the Phase 20 in-range case) is refused and the consented scale stays (21-01)
- [ ] Strict: deep scene whose consented scale already gives median >= 3 m is still refused (21-01)
- [ ] Deadband: 0.5% skipped (no apply, no smoother reset, status unchanged); 1.5% commits; exactly 1% commits (21-01; reset spy re-checked in 21-02)
- [ ] Offset ≠ 0 candidate refused (21-01)
- [ ] Every refuse: applied object identical, draft params cleared, status `rejected` only while online (21-01)
- [ ] Clear/disable racing a commit wins (`auto_commit_stale`) (21-01)
- [ ] Wizard `apply()` and default `apply_params` unchanged; no horizon gate there (21-01)
- [ ] Phase 20 sampler tests unmodified and green with `auto_commit=False` (21-01)
- [ ] DepthLoop passes the raw map + live fingerprint before `apply_map`; sole `apply_map` site (21-02)
- [ ] Commit resets the free-space smoother; reject does not (21-02)
- [ ] Mismatch still refused by `refuse_if_mismatch`; no commit (21-02)
- [ ] `/api/status` shows `auto_committed` / `rejected` separate from `depth.kind` and persist (21-02)
- [ ] No YAML bytes change on auto-commit (21-01, 21-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| ONL-05 | Five conjuncts gate `apply_params` | `test_online_auto_commit.py` | 21-01 |
| ONL-05 | Failed gates leave applied unchanged | `test_online_auto_commit.py` | 21-01 |
| ONL-09 | Horizon refuse incl. boundary and scale 1000 | `test_online_auto_commit.py` | 21-01 |
| ONL-05 | 1% deadband skip vs commit, boundary | `test_online_auto_commit.py` | 21-01 |
| ONL-09 | Strict deep-scene refuse | `test_online_auto_commit.py` | 21-01 |
| ONL-09 | Wizard Apply has no horizon gate | `test_online_auto_commit.py` / `test_calibration_state.py` | 21-01 |
| ONL-07 | Sole `apply_map`; raw map to sampler | `test_depth_loop_online.py` | 21-02 |
| ONL-07 | Smoother reset on auto-commit | `test_depth_loop_online.py` | 21-02 |
| ONL-07 | Persist fingerprint refuse unchanged | `test_depth_loop_online.py` + existing persist tests | 21-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green (`uv sync --extra dev` only)

**Approval:** plans validated; execute pending
