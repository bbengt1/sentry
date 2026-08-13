# Phase 16: Free-Space Metric Path - Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 11 (create/extend)
**Analogs found:** 11 / 11

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/spatial/free_space.py` | utility | transform | same file (`compute_free_space`, `depth_to_nearness`, `ObstacleCue`) | exact |
| `src/sentry_ai/spatial/loop.py` | loop | consume→store | same file (`FreeSpaceLoop._run`, `_obstacles_for_store`) | exact |
| `src/sentry_ai/spatial/smoothing.py` | utility | state | same file (`OccupancySmoother.reset` already exists) | exact |
| `src/sentry_ai/state/perception_store.py` | store | keep-latest | same file (`FreeSpaceProduct`, `set_free_space`) | exact |
| `src/sentry_ai/api/assemble.py` | merge | snapshot→wire | same file (`_units_for_depth_kind`, `_obstacle_to_wire`) | exact |
| `src/sentry_ai/schemas/perception.py` | schema | request-response | same file (`ObstacleCue`, `FreeSpacePayload`, `extra=forbid`) | exact |
| `src/sentry_ai/schemas/validators.py` | schema | honesty | same file (`assert_free_space_units` Phase 13 grace) | exact |
| `src/sentry_ai/api/routes_calibration.py` | endpoint | optional reset | same file apply/clear (belt-and-suspenders only) | role-match |
| `tests/test_free_space_bands.py` | test | — | same file ordinal + `metric_estimated` still ordinal | exact |
| `tests/test_free_space_loop.py` | test | — | same file synthetic depth → product | exact |
| `tests/test_assemble_perception_frame.py` | test | — | same file units ordinal + dict obstacles | exact |
| `tests/test_calibration_validators.py` | test | — | same file calibrated+ordinal currently OK | exact |
| `tests/test_free_space_smoothing.py` | test | — | same file EMA; add reset-on-kind via loop tests | exact |

**Out of phase (do not pattern-map implementation):** YAML persist I/O, wizard REST redesign, DetectionLoop, FrameBus, ORT-TRT factory, `kind_for_mode`, RANSAC, docs polish, FSD/motor fields.

---

## Pattern Assignments

### `src/sentry_ai/spatial/free_space.py` (utility) — EXTEND (16-01)

**Analog:** existing `compute_free_space` always `units="ordinal"`; `depth_to_nearness` min–max + `auto` polarity; `ObstacleCue` has no `distance_m`.

**Target additions:**

```python
DEFAULT_METRIC_NEAR_CUT_M = 1.5
DEFAULT_METRIC_MID_CUT_M = 3.0

def _meters_to_nearness(depth_m: np.ndarray) -> np.ndarray:
    """Fixed-horizon nearness ∈ [0, 1]. 0 m → 1.0; d >= 3.0 m → 0.0.
    NOT per-frame min–max. Calibrated path only.
    """

def compute_free_space(
    depth_map: np.ndarray,
    *,
    kind: DepthKind,
    nearness_polarity: NearnessPolarity = "auto",
    roi_bottom_frac: float = DEFAULT_ROI_BOTTOM_FRAC,
    near_cut: float = DEFAULT_NEAR_CUT,          # ordinal 0..1; ignored if calibrated
    mid_cut: float = DEFAULT_MID_CUT,
    min_area_frac: float = DEFAULT_MIN_AREA_FRAC,
    smoother: OccupancySmoother | None = None,
    occupied_mask: np.ndarray | None = None,
    apply_morphology: bool = True,
    metric_near_cut_m: float = DEFAULT_METRIC_NEAR_CUT_M,
    metric_mid_cut_m: float = DEFAULT_METRIC_MID_CUT_M,
) -> FreeSpaceResult:
```

**Branch (lock #1, #2, #5):**

| `kind` | units | Band logic | Polarity | Nearness 0..1 |
|--------|-------|------------|----------|----------------|
| `METRIC_CALIBRATED` | `"m"` | `d < 1.5` near; `1.5 ≤ d < 3.0` mid; `d ≥ 3.0` far on **raw meters** (finite ROI) | pinned `higher_is_farther` (ignore `nearness_polarity`) | `_meters_to_nearness` |
| `RELATIVE` | `"ordinal"` | existing 0.72/0.45 on `depth_to_nearness` | `auto` default | `depth_to_nearness` |
| `METRIC_ESTIMATED` | `"ordinal"` | same as relative | `auto` default | `depth_to_nearness` |

Occupied seed on metric path: finite pixels with `d < metric_near_cut_m` inside ROI (then morphology/smoother as today).

Non-finite / non-positive meters: not occupied; excluded from band numerators; ROI denominator = finite ROI pixels (document in tests).

`metric_near_cut_m >= metric_mid_cut_m` → `FreeSpaceResult(error=..., units="ordinal", depth_kind=kind)` — do not claim meters on a broken cut pair.

Error/exception path: keep `units="ordinal"` (no meter claim if compute failed). Wire assemble already skips `error is not None` products.

**Do not (16-01):** add `distance_m` (16-02); edit loop/assemble/validators; call `apply_map`; min–max the meter map; treat ordinal `near_cut` as meters.

**Do (16-02 on this file):** optional `ObstacleCue.distance_m: float | None = None`; `_extract_obstacles` fills mean depth when `kind==METRIC_CALIBRATED`.

---

### `src/sentry_ai/spatial/loop.py` (loop) — EXTEND (16-02)

**Analog:** `_run` already passes `kind=depth.kind` but **ignores** `result.units`; ordinal sliders `_near_cut`/`_mid_cut` in `[0,1]`; no kind tracking; no `reset_smoother`.

**Target:**

```python
def reset_smoother(self) -> None:
    """Drop OccupancySmoother EMA (apply↔clear / kind change)."""
    self._smoother.reset()

# __init__: self._last_kind: DepthKind | None = None

# _run after a usable depth snapshot, before compute:
if self._last_kind is not None and depth.kind != self._last_kind:
    self.reset_smoother()
self._last_kind = depth.kind

result = compute_free_space(
    depth.depth_map,
    kind=depth.kind,
    smoother=self._smoother,
    near_cut=near_cut,   # ordinal sliders; compute_free_space ignores when calibrated
    mid_cut=mid_cut,
    # do NOT pass slider values as metric_near_cut_m
)
# set_free_space(..., units=result.units, obstacles=_obstacles_for_store(...))
```

`_obstacles_for_store`: include `distance_m` when the cue has a non-None value.

`set_near_cut` / `set_mid_cut` stay `[0,1]` ordinal. **Do not** change the validator to allow 1.5.

**Do not:** re-scale `depth.depth_map`; import CalibrationState; open cameras; touch FrameBus.

---

### `src/sentry_ai/spatial/smoothing.py` — KEEP API (16-02 tests)

**Analog:** `OccupancySmoother.reset()` already drops `_ema`. No code change required unless a docstring note that free-space calls it on kind transition.

**Do not:** store EMA on PerceptionStore.

---

### `src/sentry_ai/state/perception_store.py` (store) — EXTEND (16-02)

**Analog:** `DepthProduct` already carries `unit`. `FreeSpaceProduct` does **not** carry `units` today — assemble re-derives from kind (always ordinal).

**Target:**

```python
@dataclass
class FreeSpaceProduct:
    ...
    depth_kind: DepthKind
    units: str = "ordinal"  # "ordinal" | "m"
    ...
```

`set_free_space(..., units: str = "ordinal")` and `snapshot_free_space` copy the field.

**Do not:** call `assert_free_space_units` inside the store unless existing depth-style honesty is desired. Prefer wire validator + loop passing `result.units`. If adding a store gate, mirror `assert_depth_kind_unit` and test it — optional, not required.

---

### `src/sentry_ai/api/assemble.py` — EXTEND (16-02)

**Analog:** stub:

```python
def _units_for_depth_kind(kind: DepthKind) -> str:
    if kind == DepthKind.METRIC_CALIBRATED:
        return "ordinal"  # still ordinal bands without calibrated free-space path
    return "ordinal"
```

**Target (lock #7):**

```python
def _units_for_depth_kind(kind: DepthKind) -> str:
    if kind == DepthKind.METRIC_CALIBRATED:
        return "m"
    return "ordinal"  # relative AND metric_estimated
```

Prefer `getattr(free, "units", None) or _units_for_depth_kind(free.depth_kind)` so store units win when present.

`_obstacle_to_wire`: pass `distance_m=data.get("distance_m")` (None default). Mapping and dataclass/attr paths.

**Do not:** attach masks or depth_map; invent meters when kind is not calibrated.

---

### `src/sentry_ai/schemas/perception.py` + `validators.py` — EXTEND (16-02)

**ObstacleCue (lock #3):**

```python
class ObstacleCue(BaseModel):
    model_config = ConfigDict(extra="forbid")
    bbox_xyxy: tuple[float, float, float, float] | list[float]
    nearness_mean: float  # 0..1 ordinal; NOT meters
    nearness_max: float
    area_px: int
    band: Literal["near", "mid", "far"] = "near"
    distance_m: float | None = None  # calibrated only; omit/None otherwise
```

**`assert_free_space_units` (lock #8):** calibrated **must** be `"m"`; relative/estimated **must not** be `"m"`. Unknown units still error.

Update module docstring on `ObstacleCue` (“Intentionally NO distance_m” → optional additive when calibrated).

Flip tests currently named `test_assert_free_space_units_metric_calibrated_ordinal_ok` and `test_free_space_payload_metric_calibrated_ordinal_ok` to **raises**.

---

### `src/sentry_ai/api/routes_calibration.py` — OPTIONAL (16-02)

**Analog:** POST apply / POST clear already mutate `CalibrationState` only. `AppState.free_space_loop` already exists.

**Belt-and-suspenders (not required):** after successful apply/clear, if `getattr(request.app.state, "free_space_loop", None)` has `reset_smoother`, call it. Cancel (`clear_draft`) must **not** reset (kind unchanged).

Required path remains loop kind-change detection.

---

### Tests

| File | Plan | Analog behavior |
|------|------|-----------------|
| `tests/test_free_space_bands.py` | 16-01 | Keep relative ordinal + estimated ordinal. Add calibrated 1.5/3.0 bands, smoking-gun 4–5 m far scene, no min–max, polarity pin, ordinal sliders ignored |
| `tests/test_free_space_loop.py` | 16-02 | Kind consume; units on product; reset on relative↔calibrated; sliders not used as meters; no re-scale |
| `tests/test_free_space_smoothing.py` | 16-02 | `reset()` drops EMA (if not already covered) |
| `tests/test_assemble_perception_frame.py` | 16-02 | calibrated → units `"m"`; estimated stays ordinal; `distance_m` round-trip; relative dict obstacles still work |
| `tests/test_calibration_validators.py` | 16-02 | calibrated+ordinal **raises**; calibrated+m OK; relative/estimated + m still raise |

---

## Shared Patterns

### 1. Kind triad honesty
**Source:** `assert_depth_kind_unit` / Phase 13 free-space grace
**Apply to:** `assert_free_space_units` tighten; assemble helper; compute branch

### 2. Consume store products; never infer
**Source:** FreeSpaceLoop snapshots depth; calibration routes snapshot depth
**Apply to:** never `apply_map` / never `worker.process` in free-space

### 3. Loop-owned temporal state
**Source:** `OccupancySmoother` not on PerceptionStore
**Apply to:** `reset_smoother` on kind change

### 4. Additive optional wire fields
**Source:** Detection `source`, status `calibration_*`
**Apply to:** `ObstacleCue.distance_m` default None; extra=forbid

### 5. Synthetic NumPy fixtures
**Source:** `test_free_space_bands.py` `_synthetic_near_obstacle_depth`
**Apply to:** metric maps in **meters** (0.5 / 2.0 / 5.0), not normalized 0..1

### 6. Zero new dependencies
**Source:** ROADMAP lock
**Apply to:** all Phase 16 files

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `_meters_to_nearness` | transform | New; closest is `depth_to_nearness` which we must **not** reuse on meters |

**Closest:** `depth_to_nearness` inverted-scale idea, but with a **constant** 3.0 m horizon instead of `dmin`/`dmax`.

---

## Metadata

**Analog search scope:** `spatial/free_space.py`, `spatial/loop.py`, `spatial/smoothing.py`, `state/perception_store.py`, `api/assemble.py`, `schemas/perception.py`, `schemas/validators.py`, `api/routes_calibration.py`, `api/deps.py`, `tests/test_free_space_bands.py`, `tests/test_free_space_loop.py`, `tests/test_assemble_perception_frame.py`, `tests/test_calibration_validators.py`

**Pattern extraction date:** 2026-08-13

**Key planner constraints from analogs:**
1. `units="m"` only after absolute meter cuts, not assemble-only.
2. Ordinal sliders stay `[0,1]`; metric cuts are constants.
3. `OccupancySmoother.reset` already exists — wire it.
4. Do not edit DetectionLoop / FrameBus / ORT factory / `kind_for_mode` / YAML / wizard REST.
