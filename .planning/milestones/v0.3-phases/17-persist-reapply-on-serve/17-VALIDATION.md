---
phase: 17
slug: persist-reapply-on-serve
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-13
---

# Phase 17 — Validation Strategy

> Source: `17-RESEARCH.md` § Validation Architecture + plans 17-01 / 17-02.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_calibration_store.py tests/test_calibration_persist.py tests/test_calibration_state.py tests/test_api_calibration.py tests/test_cli_calibration_inject.py tests/test_depth_loop.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Hardware policy** | Synthetic only — tmp_path YAML; no room; no real depth weights for new Phase 17 tests |

---

## Sampling Rate

- Per task commit: targeted store / persist / state / API / CLI inspect tests
- Per wave: full suite + ruff
- Phase gate: full suite green before `/gsd:verify-work`

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Tests: `save_params` / `load_params` round-trip `CalibrationParams` (scale, offset, fingerprint) with no `depth_map` / samples keys — `tests/test_calibration_store.py` (17-01)
- [ ] Tests: path = `{default_cache_root() or SENTRY_MODEL_CACHE}/calibration/{safe_id}.yaml`; `SENTRY_CALIBRATION_DIR` wins; `--calibration-file` / `explicit_file` wins — `tests/test_calibration_store.py` (17-01)
- [ ] Tests: `safe_camera_stem` rejects `..`, `/`, `\\`, empty — `tests/test_calibration_store.py` (17-01)
- [ ] Tests: atomic write (destination is complete YAML; no leftover `.tmp` after success) — `tests/test_calibration_store.py` (17-01)
- [ ] Tests: `fingerprints_match` refuses camera_id / depth_mode / model_id mismatch; W×H only when both sides non-None; live W×H None + saved W×H still matches — `tests/test_calibration_store.py` (17-01)
- [ ] Tests: missing file → `none`; corrupt YAML / extra-forbid fail → `error`; never `apply_params` — `tests/test_calibration_persist.py` (17-01)
- [ ] Tests: matching file → `try_reapply` calls `apply_params` (no draft samples); `is_applied` True — `tests/test_calibration_persist.py` (17-01)
- [ ] Tests: mismatch → `ignored_mismatch`, state inactive, no `metric_calibrated` promotion — `tests/test_calibration_persist.py` (17-01)
- [ ] Tests: `apply()` still requires draft (existing); `apply_params` does not — `tests/test_calibration_state.py` (17-01)
- [ ] Tests: `try_reapply` matching path applied on a helper used by serve (PER-02) — `tests/test_calibration_persist.py` + CLI inspect (17-02)
- [ ] Tests: POST save writes YAML; apply without persist does not; apply `{persist:true}` does — `tests/test_api_calibration.py` (17-02)
- [ ] Tests: POST clear unlinks file so a subsequent `try_reapply` is `none`; POST cancel leaves file — `tests/test_api_calibration.py` (17-02)
- [ ] Tests: `/api/status` `calibration_persist` in {none, applied, ignored_mismatch, error}; does not overwrite `depth_kind` — `tests/test_api_calibration.py` (17-02)
- [ ] Tests: DepthLoop late W×H mismatch clears applied; next map is unscaled / not `metric_calibrated` — `tests/test_depth_loop.py` (17-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| PER-01 | Save keyed by sanitized `camera_id` | test_calibration_store | 17-01 |
| PER-03 | Mismatch refuses auto-apply | test_calibration_store + persist | 17-01 |
| PER-02 | Serve / `try_reapply` matching file without wizard | test_calibration_persist + CLI inspect | 17-02 |
| PER-04 | Clear deletes file; Cancel does not | test_api_calibration + persist | 17-02 |
| Guard | Corrupt/missing soft inactive | persist | 17-01 |
| Guard | No maps on disk; safe_load; path traversal | store | 17-01 |
| Guard | Late resolution refuse | test_depth_loop | 17-02 |
| Guard | Additive persist status ≠ depth.kind | API status | 17-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green

**Approval:** plans validated; execute pending
