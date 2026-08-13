---
phase: 16
slug: free-space-meters
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-08-13
---

# Phase 16 — Validation Strategy

> Source: `16-RESEARCH.md` § Validation Architecture + plans 16-01 / 16-02.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest ≥8 (dev extra) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_free_space_bands.py tests/test_free_space_loop.py tests/test_free_space_smoothing.py tests/test_calibration_validators.py tests/test_assemble_perception_frame.py -q` |
| **Full suite command** | `uv run pytest -q` |
| **Hardware policy** | Synthetic only — no room, no real depth weights for new Phase 16 tests |

---

## Sampling Rate

- Per task commit: targeted free-space / assemble / validator tests
- Per wave: full suite + ruff
- Phase gate: full suite green before `/gsd:verify-work`

---

## Wave 0 Requirements (covered by plan tasks)

- [ ] Tests: calibrated map with 0.5 m blob → `units="m"`, occupied in blob, `depth_kind=metric_calibrated` — `tests/test_free_space_bands.py` (16-01)
- [ ] Tests: relative + `metric_estimated` still `units="ordinal"` on the same numeric array — `tests/test_free_space_bands.py` (16-01)
- [ ] Tests: 4.0–5.0 m scene (blob at 4.1 m) is **far** on metric path (`near_frac≈0`, no near obstacles) but ordinal path on the same array may still emit a near blob — `tests/test_free_space_bands.py` (16-01) **FS-02 smoking gun**
- [ ] Tests: calibrated path does not min–max (uniform 2.0 m map → mid, not a fake near/far split) — `tests/test_free_space_bands.py` (16-01)
- [ ] Tests: calibrated path ignores ordinal `near_cut=0.99` / `mid_cut=0.01` (still uses 1.5/3.0 m) — `tests/test_free_space_bands.py` (16-01)
- [ ] Tests: `nearness_*` in `[0, 1]` on metric path; no `distance_m` required in 16-01 — `tests/test_free_space_bands.py` (16-01)
- [ ] Tests: loop writes `units="m"` when store depth kind is calibrated; ordinal sliders unused — `tests/test_free_space_loop.py` (16-02)
- [ ] Tests: loop `reset_smoother` on kind transition relative↔calibrated; EMA does not ghost — `tests/test_free_space_loop.py` (16-02)
- [ ] Tests: loop never re-scales (constant 0.8 m calibrated map stays 0.8 occupancy, not `scale*map`) — `tests/test_free_space_loop.py` (16-02)
- [ ] Tests: assemble `_units_for_depth_kind(METRIC_CALIBRATED) == "m"`; estimated stays ordinal — `tests/test_assemble_perception_frame.py` (16-02)
- [ ] Tests: optional `distance_m` round-trip on calibrated cues; absent on relative — `tests/test_assemble_perception_frame.py` (16-02)
- [ ] Tests: `assert_free_space_units(calibrated, "ordinal")` raises; `(calibrated, "m")` OK — `tests/test_calibration_validators.py` (16-02)

## Phase Requirements → Test Map

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| FS-01 | Free-space `units="m"` only when kind is `metric_calibrated` | test_free_space_bands + loop + assemble | 16-01 / 16-02 |
| FS-02 | No label-only flip of percentile cuts | test_free_space_bands smoking-gun | 16-01 |
| FS-03 | Smoother/state resets on apply and clear | test_free_space_loop kind transition | 16-02 |
| Guard | Validator grace removed | test_calibration_validators | 16-02 |
| Guard | Consume scaled map; no re-scale | test_free_space_loop | 16-02 |
| Guard | `nearness_*` 0..1; `distance_m` calibrated-only | bands + assemble | 16-01 / 16-02 |

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] `nyquist_compliant: true` after plan Dimension 8 pass
- [ ] Wave 0 tests exist on disk after execute
- [ ] Phase gate: full suite green

**Approval:** plans validated; execute pending
