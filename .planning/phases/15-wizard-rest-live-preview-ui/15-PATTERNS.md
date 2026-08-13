# Phase 15: Wizard REST + Live Preview UI - Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 12 (create/extend)
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/schemas/calibration.py` | schema | request-response | same file (`CalibrationParams` / `CalibrationSnapshot`, `extra=forbid`) | exact |
| `src/sentry_ai/control/calibration_state.py` | store | request-response | same file (`_draft_samples`, `set_draft_params`, `clear_draft`, `apply`, `clear_applied`) | exact |
| `src/sentry_ai/spatial/calibration.py` | utility | transform | same file (`fit_scale_median` / `fit_affine_lstsq`) + optional height helper | exact |
| `src/sentry_ai/api/routes_calibration.py` | endpoint | request-response | `api/routes_pipeline.py` + `api/routes_depth.py` | role-match |
| `src/sentry_ai/api/app.py` | config | construct | same file `pipeline_state=` inject | exact |
| `src/sentry_ai/api/deps.py` | config | construct | same file `AppState.pipeline_state` | exact |
| `src/sentry_ai/cli.py` | config | construct | same file DepthLoop `calibration=` + `create_app(pipeline_state=)` | exact |
| `src/sentry_ai/api/routes_preview.py` | endpoint | request-response | same file additive `/api/status` keys (depth, pipeline, backend) | exact |
| `src/sentry_ai/ui/static/index.html` | ui | request-response | same file OV/pipeline control-row + depth badge | exact |
| `tests/test_api_calibration.py` | test | — | `tests/test_api_depth.py` + `tests/test_pipeline_config.py` | role-match |
| `tests/test_cli_calibration_inject.py` | test | — | same file inspect-source inject | exact |
| `tests/test_api_preview.py` | test | — | same file `test_root_serves_live_preview_html` string contracts | exact |

**Out of phase (do not pattern-map implementation):** YAML persist I/O, free-space meter algorithm / `assemble._units_for_depth_kind`, DetectionLoop, FrameBus, ORT-TRT factory, React/npm.

---

## Pattern Assignments

### `src/sentry_ai/schemas/calibration.py` (schema) — EXTEND

**Analog:** existing `CalibrationParams` / `CalibrationSnapshot` with `ConfigDict(extra="forbid")`.

**Target addition:**

```python
class CalibrationSample(BaseModel):
    """One wizard GT sample. Extra fields rejected."""
    model_config = ConfigDict(extra="forbid")

    point_uv: tuple[float, float] | None = None
    bbox_xyxy: tuple[float, float, float, float] | None = None
    known_meters: float
    observed_raw: float | None = None  # filled at sample time
    frame_id: int | None = None
    note: str | None = None
```

**Request bodies** (may live in `routes_calibration.py` like `PipelineConfigUpdate`):

```python
class CalibrationSampleBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    point_uv: tuple[float, float] | None = None
    bbox_xyxy: tuple[float, float, float, float] | None = None
    known_meters: float | None = None
    known_height_m: float | None = None  # optional FOV helper path
    hfov_deg: float | None = None
    note: str | None = None

class CalibrationComputeBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fit: Literal["median", "affine"] = "median"
    method: str = "known_distance"
```

Empty bodies for freeze/apply/cancel/clear: `BaseModel` with `extra="forbid"` or no body.

**Do not:** add persist path, motor/safety fields, or bulk `depth_map`.

---

### `src/sentry_ai/control/calibration_state.py` (store) — EXTEND

**Analog:** same file. `_draft_samples: list[Any]` already exists and is cleared by `clear_draft` / `apply`. **No public writer today.**

**Target additions:**

```python
def add_draft_sample(self, sample: Any) -> CalibrationSnapshot:
    """Append a draft sample under lock; does not apply."""

def get_draft_samples(self) -> list[Any]:
    """Return a shallow copy of draft samples."""

def clear_draft_samples(self) -> CalibrationSnapshot:
    """Clear samples only (keep draft params unless caller also clear_draft)."""
```

**Do not:** change `apply_map` / `promote_kind_unit` / apply formula. **Do not** import FastAPI.

**Cancel vs Clear (lock #1):** `clear_draft` already matches Cancel; `clear_applied` already matches Clear. Routes must call the right one — do not merge them.

---

### `src/sentry_ai/spatial/calibration.py` (utility) — EXTEND optionally

**Analog:** same file fitters. Optional thin helper only:

```python
def known_height_to_distance_m(
    *,
    known_height_m: float,
    bbox_xyxy: tuple[float, float, float, float],
    image_width_px: int,
    hfov_deg: float = 70.0,
) -> float:
    """Weak pinhole: d = (H * fy) / h_px. Documented FOV assumption, not intrinsics."""
```

`fy = (image_width_px / 2) / tan(radians(hfov_deg) / 2)`. Non-positive inputs → `ValueError`. Core sample path remains `(observed_raw, known_meters)`.

**Do not:** change fit gates, MIN/MAX_SCALE, or apply formula.

---

### `src/sentry_ai/api/routes_calibration.py` (endpoint) — NEW

**Analog:** `routes_pipeline.py` (`_require_pipeline_state` → 503; `extra=forbid`; never `worker.process`).

```python
"""Calibration wizard control plane (WIZ-01/02/04).

Handlers only snapshot PerceptionStore depth and mutate CalibrationState.
They never open cameras or run model inference.
"""

router = APIRouter()

def _require_calibration_state(request: Request) -> Any:
    state = getattr(request.app.state, "calibration_state", None)
    if state is None:
        raise HTTPException(status_code=503, detail="calibration state not available")
    return state
```

**Routes (lock #8):**

| Method | Path | Behavior |
|--------|------|----------|
| GET | `/api/depth/calibration` | Snapshot + sample summaries (no maps) + `frozen` |
| POST | `/api/depth/calibration/freeze` | Pin current `snapshot_depth()` in-memory |
| POST | `/api/depth/calibration/sample` | Fill `observed_raw`; `add_draft_sample`; 409 if applied |
| DELETE | `/api/depth/calibration/samples` | `clear_draft_samples` (and drop stale draft params) |
| POST | `/api/depth/calibration/compute` | `fit_*`; `ok=True` → `set_draft_params`; else 422 |
| POST | `/api/depth/calibration/apply` | `state.apply()`; 422 on ValueError |
| POST | `/api/depth/calibration/cancel` | **`clear_draft` only** |
| POST | `/api/depth/calibration/clear` | **`clear_applied`** (+ `clear_draft` for cleanliness) |

**Sampling observed_raw:**

- Prefer freeze pin if set; else `store.snapshot_depth()`.
- Point: clamp UV to map; read that pixel (finite, >0).
- BBox: median of finite positive pixels in integer ROI.
- Missing/error map → 422 (`no_depth_product` / `empty_roi`).
- Applied → 409 (`calibration_already_applied`).

**Fingerprint** when building `CalibrationParams`: `camera_id` / width / height from depth product; `depth_mode` / `model_id` from `depth_worker` if present.

**Freeze pin:** hold a copied `DepthProduct` (or `{depth_map, width, height, frame_id, camera_id, kind}`) on `app.state` (e.g. `calibration_freeze_pin`). Not YAML. Cancel/clear/apply should drop the pin. Do not put FastAPI types on `CalibrationState`.

**Do not:** `worker.process`, `VideoCapture`, write `PerceptionStore`, YAML I/O, free-space units.

---

### `src/sentry_ai/api/app.py` + `deps.py` + `cli.py` (construct) — EXTEND

**Analog:** `pipeline_state=` pass-through.

```python
# AppState
calibration_state: Any | None = None

# create_app(..., calibration_state: Any | None = None)
app.state.calibration_state = calibration_state
app.state.deps = AppState(..., calibration_state=calibration_state)
app.include_router(calibration_router)

# cli.serve — hoist so the SAME object reaches both sites:
from sentry_ai.control.calibration_state import CalibrationState
calibration_state = CalibrationState()  # even if depth extra missing
# depth try:
depth_loop = DepthLoop(bus, depth_worker, store, calibration=calibration_state)
# create_app:
create_app(..., calibration_state=calibration_state)
```

Today `CalibrationState()` is constructed **inside** the depth-extra try and **not** passed to `create_app`. Phase 15 must hoist and inject. `tests/test_cli_calibration_inject.py` inspect-source must assert both `calibration=calibration_state` on DepthLoop **and** `calibration_state=calibration_state` on `create_app`.

Existing `create_app` callers without the kw keep working (default None → 503 on wizard routes).

---

### `src/sentry_ai/api/routes_preview.py` `/api/status` — EXTEND

**Analog:** additive pipeline / backend fields (`is not None` guards).

```python
calib = getattr(request.app.state, "calibration_state", None)
if calib is not None:
    snap = calib.snapshot()
    data["calibration_active"] = bool(snap.applied and snap.valid)
    data["calibration_sample_count"] = int(snap.draft_sample_count)
    if snap.applied:
        data["calibration_scale"] = snap.scale
        data["calibration_method"] = snap.method
        if snap.fingerprint is not None:
            data["calibration_camera_id"] = snap.fingerprint.camera_id
    else:
        data["calibration_active"] = False
```

**Do not:** set `depth_kind` from draft. Kind stays store product (Phase 14 DepthLoop).

When `calibration_state` is missing, omit keys (do not force false in a way that pretends the control plane exists) **or** omit entirely — tests should accept omitted-or-false. Prefer omit when None; when present, always include `calibration_active`.

---

### `src/sentry_ai/ui/static/index.html` (ui) — EXTEND (plan 15-02)

**Analog:** `#open-vocab-controls` control-row + `applyStatus` depth-kind honesty.

**Target:**

- Panel `#calibration-wizard` with known-meters input, optional height note, Sample / Compute / Apply / Cancel / Clear.
- Footer `#metric-calibration` from `calibration_active` / scale / method / sample_count.
- Click-to-sample on `#preview` → `point_uv` in **natural** image pixels (not CSS box).
- Preview residual/scale from compute JSON **labeled draft** — do not rewrite `#metric-depth-kind` to `metric_calibrated` until status `depth_kind` says so.
- Honesty copy: hobby monocular, not vehicle-grade; relative is never meters; Cancel drops draft only; Clear drops applied.
- Banned strings unchanged: autonomous / safe_to_drive / go_nogo / motor.

---

### `tests/test_api_calibration.py` (test) — NEW

**Analog:** `test_api_depth.py` FakeDepthWorker + `_seed_depth`; `test_pipeline_config.py` 503 / extra=forbid / never process.

```python
class FakeDepthWorker:
    def process(self, frame):
        raise AssertionError("handlers must never call process")
```

Cover: 503 without state; sample fills observed_raw; 409 when applied; compute median ok → has_draft_params; rejected fit 422 and no draft; apply then status `calibration_active`; cancel after draft does not apply; cancel after apply **leaves applied**; clear drops applied; extra fields 422; snapshot after draft still `depth.kind == relative`.

---

### `tests/test_api_preview.py` / `test_cli_calibration_inject.py` — EXTEND

HTML contract: `calibration-wizard`, `api/depth/calibration`, Apply/Cancel/Clear, sample count, residual, `calibration_active`. CLI source: same object to DepthLoop and `create_app`.

---

## Shared Patterns

### 1. Control-plane 503 when inject missing
**Source:** `routes_pipeline._require_pipeline_state` / `routes_depth._require_worker`
**Apply to:** calibration routes

### 2. extra=forbid request bodies
**Source:** `PipelineConfigUpdate`, `DepthConfigUpdate`
**Apply to:** all wizard bodies

### 3. Handlers never infer or open cameras
**Source:** routes_pipeline / routes_depth docstrings + FakeWorker AssertionError
**Apply to:** routes_calibration

### 4. Additive /api/status keys
**Source:** pipeline flags, backend_live, depth_kind
**Apply to:** calibration_active / scale / method / sample_count / camera_id

### 5. Same construct-time inject object
**Source:** `PipelineState()` → loops + `create_app`
**Apply to:** `CalibrationState()` → DepthLoop + `create_app`

### 6. Draft vs applied
**Source:** Phase 13 `CalibrationState`; Phase 14 fit-time reject before draft
**Apply to:** compute gates; Cancel vs Clear

### 7. Static Live Preview chrome
**Source:** OV prompt row + status poll 500 ms
**Apply to:** wizard panel; no React

### 8. Zero new dependencies
**Source:** ROADMAP lock
**Apply to:** all Phase 15 files

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| In-memory freeze pin | session | New; keep as `app.state.calibration_freeze_pin` not disk |

**Closest:** PerceptionStore keep-latest snapshot — freeze is an optional extra pin of that snapshot for stable ROI sampling.

---

## Metadata

**Analog search scope:** `api/routes_pipeline.py`, `api/routes_depth.py`, `api/routes_preview.py`, `api/app.py`, `api/deps.py`, `cli.py`, `control/calibration_state.py`, `spatial/calibration.py`, `schemas/calibration.py`, `ui/static/index.html`, `tests/test_api_depth.py`, `tests/test_pipeline_config.py`, `tests/test_api_preview.py`, `tests/test_cli_calibration_inject.py`

**Pattern extraction date:** 2026-08-13

**Key planner constraints from analogs:**
1. 503 if inject missing; extra=forbid; never process.
2. One CalibrationState for loop + app.
3. Cancel = clear_draft; Clear = clear_applied.
4. Do not edit DetectionLoop / FrameBus / ORT factory / free-space algorithm / YAML.
