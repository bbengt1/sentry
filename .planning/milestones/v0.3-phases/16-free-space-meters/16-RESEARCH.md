# Phase 16: Free-Space Metric Path - Research

**Researched:** 2026-08-13
**Domain:** Honest meter bands for free-space only when depth is `metric_calibrated`; ordinal otherwise; smoother reset on apply/clear
**Confidence:** HIGH

## Summary

Phase 15 shipped wizard REST + static Live Preview. DepthLoop already applies scale (`CalibrationState.apply_map` after `worker.process`, before `set_depth`). Free-space still runs **per-frame min–max nearness + 0.72/0.45 percentile cuts** and always emits `units="ordinal"` — including when `kind=metric_calibrated`. `assemble._units_for_depth_kind` is a stub that returns `"ordinal"` even for `METRIC_CALIBRATED`. Phase 13 left `metric_calibrated` + `units="ordinal"` as a grace on `assert_free_space_units`. [VERIFIED: `spatial/free_space.py` `compute_free_space` always `units="ordinal"`; `depth_to_nearness` min–max normalizes; `FreeSpaceLoop` copies `depth.kind` but never units; `OccupancySmoother.reset()` exists but is never called on calib transitions; `FreeSpaceProduct` has no `units` field; wire `ObstacleCue` has no `distance_m`.]

Phase 16 must deliver:

1. **Pure metric compute path** (FS-01 / FS-02) — absolute meter cuts on the **already-scaled** map when `kind=metric_calibrated`; never a label-only flip of ordinal percentile cuts.
2. **Loop + wire + smoother** (FS-03) — consume kind/units from the DepthLoop product; reset occupancy EMA on apply↔clear; assemble/store/schema honesty; optional additive `distance_m`.

**Primary recommendation:** Two explicit modes inside `compute_free_space`. Calibrated → `units="m"` **iff** bands use absolute meter thresholds (default near 1.5 m / mid 3.0 m) on scaled depth with pinned `higher_is_farther` and **no** min–max normalize. Relative and `metric_estimated` stay `units="ordinal"` with existing percentile nearness + `auto` polarity. `nearness_*` remain 0..1. Optional `distance_m` = mean scaled depth in the blob, calibrated only. Free-space **never re-scales** (DepthLoop is the sole apply site). Smoother reset is loop-detected from kind change (`CalibrationState` has no listeners).

---

## Locked Decisions (authoritative)

| # | Decision | Value |
|---|----------|-------|
| 1 | When `units="m"` | Calibrated → `units="m"` **iff** the metric band path used **absolute meter cuts** on scaled depth (`higher_is_farther`). **Never** a label-only flip of 0.72/0.45 percentile cuts |
| 2 | Relative + estimated | `units="ordinal"`; existing percentile nearness + `auto` polarity. `metric_estimated` is **not** calibrated — no meter bands |
| 3 | Cue fields | `nearness_*` remain 0..1 on every path. Optional additive `distance_m` on cues **only when calibrated** (mean depth in blob) |
| 4 | Default metric cuts | near **1.5 m** / mid **3.0 m** (module constants, not FSD, not Live Preview sliders). **Do not reuse ordinal 0..1 sliders as meters** |
| 5 | Polarity / normalize | Pin `higher_is_farther` on the calibrated path. **Never min–max normalize meters**. Ordinal path keeps `depth_to_nearness` |
| 6 | Smoother reset | `OccupancySmoother.reset()` on kind transition apply↔clear. Expose `FreeSpaceLoop.reset_smoother()`. Loop detects kind/generation change (`CalibrationState` has no listeners). Optional belt-and-suspenders from routes apply/clear is OK, not required |
| 7 | Assemble helper | `_units_for_depth_kind`: `METRIC_CALIBRATED` → `"m"`; else `"ordinal"` |
| 8 | Validator grace | After the metric path exists, calibrated+ordinal is **no longer** the Phase 13 grace. **Calibrated must emit `"m"`** |
| 9 | Consume, don't scale | Free-space **consumes** DepthLoop scaled map + kind — never re-applies `scale*map+offset` |
| 10 | Constraints | Zero new deps; freeze DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; synthetic tests only; no YAML (17); no wizard REST redesign; no FSD / interlock / motor; no RANSAC; docs polish is Phase 18 |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Rationale |
|------------|--------------|-----------|
| Metric vs ordinal band math | `spatial/free_space.py` `compute_free_space` | Pure NumPy/OpenCV; golden tests without a loop |
| Ordinal nearness | `depth_to_nearness` | Unchanged; **not called** on calibrated path |
| Meter→nearness 0..1 | New fixed-horizon helper in `free_space.py` | Constant 3.0 m horizon — not per-frame min–max |
| Loop consume kind | `spatial/loop.py` `FreeSpaceLoop` | Passes `depth.kind` + ordinal sliders (ordinal only) or metric constants |
| Smoother reset | `OccupancySmoother.reset` (exists) + `FreeSpaceLoop.reset_smoother` | Loop-owned EMA; no CalibrationState listeners |
| Store units | `FreeSpaceProduct.units` + `set_free_space` | Keep-latest product must carry honesty, not just kind |
| Wire units | `assemble._units_for_depth_kind` + payload | FS-01 on `/v1` |
| Wire `distance_m` | `schemas.perception.ObstacleCue` additive | extra=forbid; default None |
| Validator | `assert_free_space_units` | Calibrated must be `"m"`; relative/estimated forbid `"m"` |
| Depth scale | DepthLoop `apply_map` (Phase 14) | **Do not duplicate** |
| YAML / wizard redesign / docs | Phases 17 / 15-done / 18 | Out of phase 16 |

---

## Standard Stack

Zero new packages. Existing NumPy + OpenCV (already used by free-space) + Pydantic 2 wire models + pytest. No scipy, no RANSAC, no new frontend.

```bash
uv sync --extra dev
uv run pytest tests/test_free_space_bands.py tests/test_free_space_loop.py tests/test_free_space_smoothing.py tests/test_calibration_validators.py tests/test_assemble_perception_frame.py -q
```

---

## Architecture Patterns

```
DepthAnythingWorker.process
  → CalibrationState.promote_kind_unit + apply_map     # Phase 14; sole scale site
  → PerceptionStore.set_depth (kind, unit, scaled map)
           │
           ▼
FreeSpaceLoop.snapshot_depth()                         # consume only
  → if kind changed (esp. calibrated ↔ not): reset_smoother()
  → compute_free_space(map, kind=depth.kind, ...)
       RELATIVE | METRIC_ESTIMATED:
         depth_to_nearness (min–max, auto polarity)
         bands via 0.72 / 0.45 nearness cuts
         units = "ordinal"
       METRIC_CALIBRATED:
         NO min–max; polarity pinned higher_is_farther
         near: d < 1.5 m; mid: 1.5 ≤ d < 3.0; far: d ≥ 3.0
         nearness_0_1 = clip((3.0 - d) / 3.0, 0, 1)   # fixed horizon
         optional distance_m = mean(d) in blob
         units = "m"
  → PerceptionStore.set_free_space(..., units=result.units)
           │
           ▼
assemble_perception_frame
  → _units_for_depth_kind(METRIC_CALIBRATED) = "m"
  → ObstacleCue.distance_m pass-through when present
```

Anti-patterns: flip assemble helper to `"m"` while `compute_free_space` still min–maxes; treat 0.72/0.45 as meters; reuse `set_near_cut` [0,1] sliders as 1.5/3.0; min–max a calibrated map; `auto` polarity on meters; re-scale inside FreeSpaceLoop; `distance_m` on relative/estimated cues; calibrated+ordinal grace after this phase; RANSAC ground plane; DetectionLoop/FrameBus/ORT-TRT/`kind_for_mode` edits; YAML; wizard REST redesign; FSD copy.

---

## Common Pitfalls

1. **Label-only meters (FS-02 / PITFALLS #2)** — `_units_for_depth_kind` returns `"m"` while bands still use 0.72/0.45 on min–max nearness. A 4–5 m map would still grow a “near” blob. **Lock #1:** `units="m"` only when absolute meter cuts ran.
2. **Min–max destroying meters (lock #5)** — `depth_to_nearness` does `(arr-dmin)/(dmax-dmin)` per frame. On a calibrated map that **must not run**. Use a fixed 3.0 m horizon for 0..1 nearness stats.
3. **Ordinal sliders as meters (lock #4)** — `FreeSpaceLoop.set_near_cut` validates `[0,1]`. 1.5/3.0 are module constants on the metric path; sliders stay ordinal-only.
4. **`metric_estimated` dressed as calibrated (lock #2)** — estimated heads already have `unit="m"` on depth. Free-space stays ordinal until user GT apply.
5. **Smoother ghosting (FS-03)** — EMA occupancy from ordinal near-band survives into metric frames (or reverse). Reset on kind transition. `CalibrationState` has no listeners — loop compares `depth.kind` (and optional generation) to last processed.
6. **Re-scale in free-space (lock #9)** — multiplying again by `CalibrationParams.scale` double-scales. Consume the store map.
7. **Phase 13 grace left on (lock #8)** — `metric_calibrated` + `ordinal` was allowed until a real metric path existed. After 16-02, that pair is a validator error.
8. **Scope creep** — YAML (17), wizard REST redesign (15 done), RANSAC, FSD/interlock/motor, `kind_for_mode`, docs polish (18).

---

## Code Examples

See `16-PATTERNS.md` for full target APIs. Summary:

```python
DEFAULT_METRIC_NEAR_CUT_M = 1.5
DEFAULT_METRIC_MID_CUT_M = 3.0  # also the fixed nearness horizon

def _meters_to_nearness(depth_m: np.ndarray) -> np.ndarray:
    """0 m → 1.0; d >= 3.0 m → 0.0. Constant horizon — not min–max."""
    arr = np.asarray(depth_m, dtype=np.float32)
    finite = np.isfinite(arr)
    nearness = (DEFAULT_METRIC_MID_CUT_M - arr) / DEFAULT_METRIC_MID_CUT_M
    nearness = np.clip(nearness, 0.0, 1.0)
    return np.where(finite, nearness, 0.0).astype(np.float32)

# compute_free_space branch:
if kind == DepthKind.METRIC_CALIBRATED:
    # ignore nearness_polarity / ordinal near_cut / mid_cut
    units = "m"
    nearness = _meters_to_nearness(arr)
    near_band = finite_roi & (arr < metric_near_cut_m)
    mid_band = finite_roi & (arr >= metric_near_cut_m) & (arr < metric_mid_cut_m)
    far_band = finite_roi & (arr >= metric_mid_cut_m)
    raw_occ = near_band  # occupied seed = near meters inside ROI
else:
    units = "ordinal"
    # existing depth_to_nearness + percentile cuts
```

Smoking-gun FS-02 test: HxW map all in **4.0–5.0 m** with a slightly-nearer blob at 4.1 m. Metric path → `units="m"`, `near_frac≈0`, no near obstacles. Ordinal path on the same array (kind=relative) **would** still emit a near blob via percentile. Label-only flip would fail this test.

Loop:

```python
def reset_smoother(self) -> None:
    self._smoother.reset()

# in _run, after snapshot_depth:
if self._last_kind is not None and depth.kind != self._last_kind:
    self.reset_smoother()
self._last_kind = depth.kind
# then compute_free_space(..., kind=depth.kind)
# set_free_space(..., units=result.units, obstacles=... including distance_m)
```

Assemble:

```python
def _units_for_depth_kind(kind: DepthKind) -> str:
    if kind == DepthKind.METRIC_CALIBRATED:
        return "m"
    return "ordinal"
```

Validator (post metric path):

```python
def assert_free_space_units(depth_kind: DepthKind, units: str) -> None:
    if units not in ("ordinal", "m"):
        raise ValueError(...)
    if depth_kind == DepthKind.METRIC_CALIBRATED:
        if units != "m":
            raise ValueError("metric_calibrated free-space must use units='m'")
        return
    if units == "m":
        raise ValueError("free-space units='m' only allowed when depth_kind=metric_calibrated")
```

---

## Open Questions (RESOLVED)

1. Absolute meter cuts vs keep ordinal nearness + separate `distance_m`? → **Both:** metric **bands** use absolute cuts (required for `units="m"`); `nearness_*` stay 0..1; optional `distance_m` additive on calibrated cues.
2. Default thresholds? → **1.5 m / 3.0 m** constants. Not FSD. Not ordinal sliders.
3. Polarity on calibrated maps? → **Pin `higher_is_farther`**. Never min–max. Never `auto`.
4. How does the loop learn apply/clear? → **Detect `depth.kind` change**. No CalibrationState listeners. Optional routes belt-and-suspenders.
5. Phase 13 calibrated+ordinal grace? → **Remove** once the metric path ships (16-02 with assemble).
6. Re-scale in free-space? → **No.** Consume DepthLoop map.
7. `metric_estimated` meter bands? → **No.** Ordinal until `metric_calibrated`.
8. RANSAC ground plane / FSD interlock? → **No** (out of milestone / Phase 16).

---

## Validation Architecture

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| FS-01 | `units="m"` only when kind is `metric_calibrated` | `test_free_space_bands.py` (+ loop/assemble in 16-02) | 16-01 / 16-02 |
| FS-02 | No label-only flip; 4–5 m scene is far in metric, may be “near” in ordinal | `test_free_space_bands.py` | 16-01 |
| FS-03 | Smoother resets on apply↔clear kind transition | `test_free_space_loop.py` / `test_free_space_smoothing.py` | 16-02 |
| Guard | relative + estimated stay ordinal; calibrated must be `"m"` on wire | `test_calibration_validators.py` | 16-02 |
| Guard | assemble helper + optional `distance_m` | `test_assemble_perception_frame.py` | 16-02 |

Seed (must stay green while planning; execute uses the same plus new cases):

```bash
uv run pytest tests/test_free_space_bands.py tests/test_free_space_loop.py tests/test_free_space_smoothing.py tests/test_calibration_validators.py tests/test_assemble_perception_frame.py -q
```

---

## Security Domain

| Threat | Mitigation |
|--------|------------|
| Ordinal bands labeled meters | Gate `units="m"` on metric-cut implementation + FS-02 golden test |
| Min–max destroying meters | Calibrated path never calls `depth_to_nearness` |
| `metric_estimated` as calibrated | Kind switch only; estimated stays ordinal |
| Smoother ghost occupancy | Reset on kind transition |
| Double-scale | Consume store map; no apply_map in free-space |
| FSD / motor / interlock fields | extra=forbid; denylist; out of scope |
| New deps supply chain | Zero new packages (T-16-SC) |

---

## Phase Requirements

| ID | Research Support |
|----|------------------|
| FS-01 | `units="m"` only for `metric_calibrated` after real metric cuts |
| FS-02 | Absolute meter cuts; smoking-gun 4–5 m far scene |
| FS-03 | `reset_smoother` on kind apply↔clear |

### Must ship
1. `compute_free_space` metric branch (1.5 / 3.0 m, pinned polarity, no min–max)
2. Honesty tests: calibrated meters; relative/estimated ordinal; label-only would fail
3. `FreeSpaceLoop` consumes kind; ignores ordinal sliders on calibrated frames; `reset_smoother`
4. `assemble._units_for_depth_kind` flip; store `units`; validator tighten
5. Optional `distance_m` on calibrated cues only
6. Synthetic tests; zero new deps

### Must not ship
YAML persist; wizard REST redesign; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; RANSAC; FSD/interlock/motor; docs polish (18); re-scale in free-space; treating 0.72/0.45 as meters.

---

## RESEARCH COMPLETE

**Phase:** 16 - Free-Space Metric Path
**Confidence:** HIGH

Key findings: `units="m"` requires absolute meter cuts on the scaled map; ordinal percentile path stays for relative and estimated; pin `higher_is_farther` and never min–max meters; smoother reset is loop-detected kind change; calibrated must emit `"m"` (Phase 13 grace ends); consume DepthLoop — never re-scale.

Ready for planning.
