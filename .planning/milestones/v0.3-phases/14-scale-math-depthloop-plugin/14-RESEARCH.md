# Phase 14: Scale Math + DepthLoop Plug-in - Research

**Researched:** 2026-08-12
**Domain:** Pure monocular scale/affine fit + DepthLoop post-worker apply before PerceptionStore
**Confidence:** HIGH

## Summary

Phase 13 shipped honesty contracts and in-process `CalibrationState` (draft vs applied, fingerprint, `promote_kind_unit`). `metric_calibrated` is reachable in policy but **no scale math or DepthLoop hook exists yet** - `apply_map` is documented only as a Phase 14 handoff. [VERIFIED: `control/calibration_state.py` docstring; `models/depth/loop.py` still does worker.process -> set_depth with no calibration.]

Phase 14 must deliver:

1. **Pure fit/reject** (CAL-01 / CAL-02) in `src/sentry_ai/spatial/calibration.py` - NumPy only, zero new deps.
2. **`CalibrationState.apply_map` + DepthLoop plug-in** (CAL-03) - transform after worker, before `set_depth`; CLI injects state; synthetic FakeDepthWorker tests.

**Primary recommendation:** Default fit = **scale-only median** of D_i/d_i; optional **affine lstsq** when N>=2; apply as map' = scale*map + offset (not inverse-depth); reject non-positive observations, absurd scales, and high residual_rms **at fit time** before draft; same apply path for relative and metric_estimated; fingerprint `depth_mode` + `model_id`; copy-on-write float32 under lock in `apply_map`.

---

## Locked Decisions (authoritative)

| # | Decision | Value |
|---|----------|-------|
| 1 | Fit default | **Scale-only median** of D_i/d_i for valid pairs |
| 2 | Optional affine | `numpy.linalg.lstsq` when N>=2; store `scale` + `offset` |
| 3 | Apply formula | map' = scale*map + offset - **not** inverse-depth |
| 4 | Polarity / observations | **No polarity flip**; reject non-positive `observed_raw` and non-positive `known_meters` |
| 5 | Reject gates | residual_rms > max(0.15*median(D), 0.05) -> reject; absurd scale outside (1e-4, 1e4) -> reject; **fit-time reject before draft** |
| 6 | Base kinds | Same apply for relative and metric_estimated; fingerprint includes depth_mode+model_id; **no undo** of metric prior |
| 7 | Fitter core | (observed_raw, known_meters) pairs; height helper **optional/minimal** |
| 8 | Modules | Fit: `src/sentry_ai/spatial/calibration.py`; state: `control/calibration_state.py` |
| 9 | Constraints | Zero new deps; freeze DetectionLoop/FrameBus/ORT-TRT; synthetic tests only; no wizard/YAML/free-space meters; **copy-on-write float32**; lock in apply_map |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Rationale |
|------------|--------------|-----------|
| Pure fit / residual reject | spatial/calibration.py | CI-pure math; no FastAPI, no DepthLoop |
| apply_map | control/calibration_state.py | Hot-path read of applied scale/offset |
| DepthLoop hook | models/depth/loop.py | Sole writer of calibrated store depth |
| Serve inject | cli.py | Construct CalibrationState; pass into DepthLoop |
| Wizard / YAML / free-space meters | later phases | Out of phase 14 |

---

## Standard Stack

Zero new packages. Use existing Python >=3.11, NumPy (median, lstsq, float32), Pydantic CalibrationParams from Phase 13, threading/dataclasses, pytest. No scipy.

```bash
uv sync --extra dev
```

---

## Architecture Patterns

```
FrameBus -> DepthAnythingWorker.process
              |  depth_map_raw, kind_mode, unit_mode
              v
         CalibrationState.promote_kind_unit(kind, unit)
         CalibrationState.apply_map(depth_map)   * NEW Phase 14
              |  if applied+valid: map' = scale*map + offset (copy float32)
              v
         PerceptionStore.set_depth(...)
```

Cold fit: (observed_raw, known_meters)[] -> filter positive finite -> fit_scale_median OR fit_affine_lstsq -> residual/scale gates -> FitResult (ok) before set_draft_params.

Patterns: pure fitter (no state mutation); fit-time reject before draft; DepthLoop sole apply site; copy-on-write float32; optional CalibrationState on DepthLoop (None default).

Anti-patterns: inverse-depth fit; polarity flip; UI/free-space-only scale; double-scaling; scipy; wizard/YAML/FS meters; DetectionLoop/FrameBus/ORT edits; in-place map mutation; bypassing promote_kind_unit.

---

## Common Pitfalls

1. Inverse-depth fit then affine-on-depth apply -> wrong meters. Use locked formula on same domain as observed_raw.
2. Non-positive observations -> filter/reject.
3. Drafting rejected fits -> fit-time gates; do not set_draft_params on ok=False.
4. In-place map mutation -> always new float32 array.
5. metric_estimated double-scale confusion -> same apply; fingerprint mode/model; no undo; promote when applied+valid.
6. apply_map(None)/error products -> pass-through None.
7. Scope creep into wizard/persist/free-space meters -> out of scope.

---

## Code Examples

See `14-PATTERNS.md` for full target APIs. Summary:

- `fit_scale_median(observed_raw, known_meters) -> CalibrationFitResult` - median of k/o; offset 0; gates on absurd scale + residual_rms
- `fit_affine_lstsq(...)` - numpy.linalg.lstsq on [o, 1] when N>=2; same gates
- Observation filter: finite and strictly positive observed_raw and known_meters
- `CalibrationState.apply_map`: copy-on-write float32 scale*map+offset under lock; None->None; inactive pass-through
- DepthLoop: promote_kind_unit then apply_map after worker.process, before set_depth

Reason codes: insufficient_valid_samples, absurd_scale, residual_rms_too_high, affine_requires_n_ge_2.

---

## Open Questions (RESOLVED)

1. Pure scale vs affine? -> default scale-only median; optional affine lstsq when N>=2.
2. Residual gates? -> reject if residual_rms > max(0.15*median(D), 0.05); scale outside (1e-4, 1e4).
3. metric_estimated double-scale? -> same apply; fingerprint mode/model; no undo; promote when applied+valid.
4. Inverse-depth? -> no.
5. Fitter module? -> spatial/calibration.py; state stays in control/.

---

## Validation Architecture

| Req ID | Behavior | File |
|--------|----------|------|
| CAL-01 | Median/affine recover params | test_calibration_fit.py |
| CAL-02 | Reject invalid fits | test_calibration_fit.py |
| CAL-03 | apply_map + DepthLoop hook | test_calibration_state.py, test_depth_loop.py |

Quick: `uv run pytest tests/test_calibration_fit.py tests/test_calibration_state.py tests/test_depth_loop.py -q`

---

## Security Domain

| Threat | Mitigation |
|--------|------------|
| Absurd scale as meters | Fit-time scale clamp + residual reject |
| In-place map corruption | Copy-on-write float32 |
| Bypass promote_kind_unit | DepthLoop calls promote before set_depth |
| New deps supply chain | Zero new packages (T-14-SC) |

---

## Phase Requirements

| ID | Research Support |
|----|------------------|
| CAL-01 | median / affine fitters + tests |
| CAL-02 | residual/scale/observation gates at fit time |
| CAL-03 | apply_map + DepthLoop + CLI inject |

### Must ship
1. spatial/calibration.py fitters + CalibrationFitResult
2. tests/test_calibration_fit.py
3. CalibrationState.apply_map
4. DepthLoop optional calibration; promote+apply before set_depth
5. cli.serve constructs/injects CalibrationState
6. FakeDepthWorker tests

### Must not ship
Wizard REST/index.html; YAML; free-space meter path; new deps; DetectionLoop/FrameBus/ORT-TRT edits.

---

## RESEARCH COMPLETE

**Phase:** 14 - Scale Math + DepthLoop Plug-in
**Confidence:** HIGH

Key findings: scale-only median default; affine optional N>=2; apply scale*map+offset CoW float32; fit-time reject before draft; DepthLoop sole apply site; zero new deps.

Ready for planning.
