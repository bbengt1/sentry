# Architecture: Metric Depth Calibration UX into Existing Sentry Spine

**Domain:** User-guided monocular metric scale (known heights / markers) for honest `depth_kind` promotion  
**Project:** Sentry AI  
**Milestone:** **v0.3 Metric Depth Calibration UX**  
**Researched:** 2026-08-11  
**Overall confidence:** HIGH for plug-in boundaries (code-verified spine); MEDIUM for exact sample-fit algorithm UX details (wizard interaction)

## Executive answer

| Question | Answer |
|----------|--------|
| **Calibration without spine rewrite?** | Yes. Add a **runtime `CalibrationState` + pure fit helpers**, apply affine scale **after** `DepthAnythingWorker.process` and **before** `PerceptionStore.set_depth`. Free-space, MJPEG, `/v1` all inherit the calibrated map + kind. |
| **New modules?** | Yes — small: calibration model/fit, `CalibrationState`, persist I/O, API routes, wizard UI. |
| **DetectionLoop / FrameBus unchanged?** | **Yes. Do not touch them.** |
| **PerceptionStore contract?** | Keep slots/writers; **optionally** extend `DepthProduct` with calibration metadata fields (or put metadata only on API status / `stats`). Prefer **minimal store change**. |
| **When is `metric_calibrated` allowed?** | Only when an **applied, validated** calibration is active (finite scale in range, ≥N samples or explicit scale, matching `camera_id`). Never from `depth_mode` alone. |
| **`metric_estimated` still valid?** | Yes — DAV2 metric indoor/outdoor heads remain a separate path (`kind_for_mode`). Calibration can refine **relative or estimated** maps; promotion to `metric_calibrated` is user-grounded scale, not model marketing. |

**Do not rewrite:** `FrameBus`, `DetectionLoop`, `OpenVocabLoop`, edge ORT/TRT factory, free-space algorithm core (near-field bands), perception-only API boundary.

**Rewrite / extend surface for v0.3:** DepthLoop post-process hook, free-space units honesty when calibrated, `assemble` units helper, depth calibration API + Live Preview wizard, serve-time load of persisted calibration, docs + synthetic tests.

---

## Current spine (code truth)

Verified from `cli.serve`, `DepthLoop`, `DepthAnythingWorker`, `FreeSpaceLoop`, `PerceptionStore`, `assemble_perception_frame`, `routes_depth`, Live Preview:

```
CameraSource
    │
    ▼
CaptureLoop ──publish──► FrameBus (depth-1, keep-latest)
                              │
                              ├──► DetectionLoop → PerceptionStore.set_detections   [FROZEN]
                              ├──► OpenVocabLoop → set_open_vocab                  [FROZEN]
                              └──► DepthLoop → DepthAnythingWorker.process
                                        │            │
                                        │            ▼
                                        │     DepthResult {depth_map, kind, unit}
                                        │            │
                                        │            ▼  ← ★ v0.3 insert: CalibrationState.apply_map
                                        │     kind/unit may promote to metric_calibrated
                                        ▼
                               PerceptionStore.set_depth(DepthProduct)
                                        │
                                        ▼
                               FreeSpaceLoop (snapshot_depth only; no FrameBus)
                                        │
                                        ▼
                               PerceptionStore.set_free_space(FreeSpaceProduct)
                                        │
                                        ▼
                    assemble_perception_frame → /v1 + MJPEG overlays + /api/status
```

### Honesty contracts already shipped (do not weaken)

| Layer | Today | Implication for v0.3 |
|-------|-------|----------------------|
| `DepthKind` enum | `relative` \| `metric_estimated` \| `metric_calibrated` | **`metric_calibrated` is reserved but never produced** |
| `kind_for_mode` | relative → `RELATIVE`+`unit=None`; metric_* → `METRIC_ESTIMATED`+`"m"` | Mode alone must **never** emit `METRIC_CALIBRATED` |
| `DepthPayload` validator | relative forbids `unit="m"` | Calibrated path must set both kind + unit correctly |
| Free-space | `units="ordinal"` always, even for `metric_estimated` | Explicit Phase 5 decision: **no meters without calibration** |
| `assemble._units_for_depth_kind` | Returns `"ordinal"` even for `METRIC_CALIBRATED` (stub comment) | **Must flip** when real calibrated free-space path lands |
| `ObstacleCue` | Intentionally **no** `distance_m` | Additive optional field only when kind is calibrated |
| UI badge | Shows `depth_kind` + unit `m` only for estimated/calibrated | Wizard must not paint meters until apply succeeds |

### Writer ownership (unchanged)

| Writer | Slot | v0.3 rule |
|--------|------|-----------|
| DetectionLoop | detections | No calibration code |
| OpenVocabLoop | open_vocab | No calibration code |
| DepthLoop | depth | **Sole place** that applies scale to `depth_map` and sets product `kind`/`unit` |
| FreeSpaceLoop | free_space | **Consumes** calibrated depth; may label units / optional `distance_m`; never invents scale |
| API / UI | snapshots only | Never recompute free-space or invent depth |

---

## Recommended architecture (opinionated)

### Design thesis

Treat calibration as a **runtime affine scale on monocular depth**, not a new neural stage and not a second free-space path:

```
depth_metric ≈ scale * depth_raw + offset
```

- **Scale** is fit from user ground truth (known object height in meters vs observed depth at the object, or known marker distance).
- **Offset** defaults to `0` for v0.3 (optional advanced; most maker flows are pure scale).
- **Promotion** to `DepthKind.METRIC_CALIBRATED` + `unit="m"` happens **only** when `CalibrationState` is applied and valid.
- **Cancel / clear** reverts to worker-native kind from `depth_mode` (`relative` or `metric_estimated`).

This mirrors v0.2’s “factory at construction, loop frozen” pattern: **put diversity under a thin post-process owned by DepthLoop**, not inside DetectionLoop or FreeSpaceLoop ownership.

### Why apply in DepthLoop (not FreeSpaceLoop, not worker)

| Placement | Verdict | Why |
|-----------|---------|-----|
| **DepthLoop after `worker.process`** | **Recommended** | Single truth: store depth_map, kind, stats, MJPEG colormap, free-space input all agree |
| Inside `DepthAnythingWorker` | Avoid | Couples user calib to model load; cancel requires worker API pollution; harder tests |
| FreeSpaceLoop only | Avoid | Dual truth: depth product still relative while free-space claims meters |
| assemble / API handlers | Forbidden | Handlers must never run Spatial Post or invent maps (existing rule) |
| Browser-only scale | Forbidden | UI/API parity (UI-06) — robots must see same kind |

### Component diagram (v0.3)

```
┌──────────────────────── spine (mostly frozen) ──────────────────────────┐
│ FrameBus → DetectionLoop / OpenVocabLoop → PerceptionStore              │
│ FrameBus → DepthLoop → set_depth → FreeSpaceLoop → set_free_space       │
│ assemble → /v1 · MJPEG · /api/status                                    │
└──────────────────────────────────▲──────────────────────────────────────┘
                                   │ calibrated DepthProduct
┌──────────────────────────────────┴──────────────────────────────────────┐
│ DepthLoop (MODIFIED carefully)                                          │
│   result = worker.process(frame)                                        │
│   if calib.is_applied(): map, kind, unit = calib.transform(result)      │
│   else: kind, unit from result (mode mapping)                           │
│   store.set_depth(...)                                                  │
└──────────────────────────────────▲──────────────────────────────────────┘
                                   │ read/write (thread-safe)
┌──────────────────────────────────┴──────────────────────────────────────┐
│ CalibrationState (NEW, in-process)                                      │
│   draft samples · fit scale · apply/cancel · valid flag · camera_id     │
│   apply_map(depth) → float32 HxW                                        │
└──────────────────────────────────▲──────────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
 routes_calibration (NEW)   persist JSON (NEW)        Live Preview wizard
 GET/POST sample/apply      per camera_id             (static index.html)
```

---

## New vs modified components

### NEW (must-add)

| Component | Path (suggested) | Responsibility |
|-----------|------------------|----------------|
| **Calibration models** | `sentry_ai/spatial/calibration.py` (or `models/depth/calibration.py`) | Pure dataclasses: `CalibrationSample`, `CalibrationParams`, `CalibrationFitResult`; fit `scale` (+ optional `offset`) from samples; validation ranges |
| **CalibrationState** | same module or `state/calibration_state.py` | Thread-safe draft vs applied params; `is_applied()`, `apply_map()`, `clear()`, `snapshot()` for API |
| **Persist I/O** | `sentry_ai/spatial/calibration_store.py` (or `config/calibration_io.py`) | Load/save JSON keyed by `camera_id` (and optional profile); refuse corrupt files honestly |
| **API routes** | `sentry_ai/api/routes_calibration.py` | Sample / compute / apply / cancel / persist / status — **no inference, no cameras** |
| **Wizard UI** | extend `ui/static/index.html` | Multi-step panel; status badge honesty; apply/cancel |
| **Unit tests** | `tests/test_calibration_*.py` | Synthetic depth maps + known scale; no physical room |

### MODIFIED (careful, minimal)

| Component | Change | Do not |
|-----------|--------|--------|
| **`DepthLoop`** | Hold optional `CalibrationState`; after process, transform map + promote kind when applied | Change bus poll, enable gate, dependency-failure path structure |
| **`cli.serve`** | Construct `CalibrationState`; load persisted file for `camera_id`; inject into DepthLoop + `create_app` | Touch DetectionLoop / ORT factory |
| **`create_app` / `AppState`** | `app.state.calibration_state = …` | Recompute live backend fields |
| **`FreeSpaceLoop` / `compute_free_space`** | When `kind == METRIC_CALIBRATED`, set `units="m"`; optionally fill `distance_m` on obstacles from map | Rewrite band algorithm; invent meters on relative/estimated |
| **`assemble_perception_frame`** | `_units_for_depth_kind`: `METRIC_CALIBRATED` → `"m"`; pass through optional `distance_m` | Bulk depth arrays on wire |
| **`ObstacleCue` schema** | Optional `distance_m: float \| None = None` (additive) | Required field breaking old clients |
| **`routes_depth` / status** | Expose calibration summary on `/api/status` or calibration routes only | Overload `PATCH /api/depth/config` with scale |
| **Live Preview HTML** | Wizard + badge for `metric_calibrated` | React rewrite |
| **Docs** | `docs/perception-frame.md`, calibration operator guide | Claim vehicle-grade accuracy |

### UNCHANGED (frozen checklist)

| Component | Why frozen |
|-----------|------------|
| `FrameBus` | Keep-latest capture mailbox |
| `DetectionLoop` / fixed-class / OV workers | No depth scale role |
| `DepthAnythingWorker` core infer | Still owns model + `depth_mode` → estimated/relative only |
| `kind_for_mode` semantics for modes | Still never returns `METRIC_CALIBRATED` |
| Perception-only boundary | No motor fields |
| Free-space near-field band math (ordinal nearness) | Still valid on scaled maps (monotonic affine) |
| ORT/TRT detection factory | Orthogonal milestone |

---

## Data model

### CalibrationParams (runtime + persist)

```python
@dataclass(frozen=True)
class CalibrationParams:
    version: int = 1
    camera_id: str = ""
    scale: float = 1.0          # meters per raw-depth unit (or multiplier on metric map)
    offset: float = 0.0         # meters; default 0
    method: str = "known_height"  # known_height | floor_marker | manual_scale
    sample_count: int = 0
    residual_rms: float | None = None  # honesty / quality hint
    depth_mode_at_fit: str | None = None  # relative | metric_indoor | ...
    model_id_at_fit: str | None = None
    created_at: float | None = None
    # NOT a safety certificate — operator-provided scale only
```

### CalibrationSample (wizard draft)

```python
@dataclass(frozen=True)
class CalibrationSample:
    # Image-space region used to read raw depth (mean of valid pixels)
    bbox_xyxy: tuple[float, float, float, float] | None = None
    # Or single point (u, v)
    point_uv: tuple[float, float] | None = None
    known_meters: float = 0.0          # ground truth distance or object height proxy
    observed_raw: float | None = None  # filled at sample time from depth_map
    frame_id: int | None = None
    note: str | None = None
```

### Validity rules (promotion gate)

`metric_calibrated` **only if all** hold:

1. `scale` finite, `scale > 0`, and within a sane clamp (e.g. reject absurd extremes — exact bounds phase-tuned).
2. `offset` finite.
3. `sample_count >= N` for fit methods (**recommend N=1** for MVP single known-height; **N≥2** optional multi-sample refine) **or** method=`manual_scale` with explicit operator scale.
4. `camera_id` matches active source (mismatch → do not auto-apply; warn).
5. Applied flag true (draft fit alone does **not** promote).

On failure: keep worker-native kind; API returns 422 with reason; UI shows uncalibrated honesty.

### DepthProduct (store) — preferred minimal change

**Option A (recommended):** No new store fields. Kind/unit already carry honesty; calibration detail lives in `CalibrationState.snapshot()` + `/api/status` keys (`calibration_active`, `calibration_scale`, …).

**Option B (if stats needed on `/v1`):** Add optional keys to `PerceptionFrame.stats` only (`calib_scale`, `calib_method`) — not new required schema fields on `DepthPayload` in v0.3 unless roadmap wants wire discoverability.

**Do not** put full sample lists on every `/v1` frame.

---

## Data flow

### A. Serve start (load)

```
cli.serve
  → camera_id from source
  → CalibrationState()
  → try load ~/.config/sentry-ai/calibration/{camera_id}.json  (path opinion below)
  → if valid: state.apply(params) silently or with banner line
  → DepthLoop(bus, worker, store, calibration=state)
  → create_app(..., calibration_state=state)
```

Banner honesty (mirror backend_live style):

```
depth: relative (DAV2 Small)
calibration: inactive
# or
calibration: applied scale=1.23 method=known_height camera_id=usb0
```

### B. Hot path (per depth frame)

```
ImageFrame
  → DepthAnythingWorker.process
       depth_map_raw, kind_mode, unit_mode
  → if CalibrationState.is_applied():
       depth_map = scale * depth_map_raw + offset   # float32, finite-safe
       kind = METRIC_CALIBRATED
       unit = "m"
    else:
       depth_map, kind, unit = raw, kind_mode, unit_mode
  → PerceptionStore.set_depth(...)   # stats recompute on calibrated map
  → FreeSpaceLoop.snapshot_depth()
       compute_free_space(map, kind=...)
       if kind == METRIC_CALIBRATED:
           units = "m"
           obstacles[].distance_m = mean(map[blob])  # optional additive
       else:
           units = "ordinal"
           no distance_m
  → assemble → DepthPayload(kind, unit) + FreeSpacePayload(units, …)
  → MJPEG: colormap on same store depth_map (visual feedback after apply)
```

### C. Wizard (cold path)

```
UI: open wizard
  → GET /api/depth/calibration  (status)
  → user places ROI / click on known object
  → POST .../sample  {bbox or uv, known_meters}
       handler: snapshot_depth() → mean raw depth in ROI → store sample
  → POST .../compute  → fit scale (draft)
  → UI shows preview numbers (draft only; kind still uncalibrated until apply)
  → POST .../apply   → CalibrationState.apply; next DepthLoop frames promote
  → optional POST .../persist → write JSON
  → POST .../cancel or DELETE → clear applied + draft; kind reverts next frame
```

**Critical:** Sample capture reads **raw or current** depth carefully:

- Prefer sampling **pre-calibration raw** for refit (store last raw map only if needed), **or** document that samples must be taken with calibration inactive.
- Opinionated MVP: **require calibration inactive while sampling**; disable sample API when applied (force cancel first). Avoids double-scaling.

### D. Free-space when calibrated

Near-field **bands stay image-space ordinal** (nearness from map still works after positive scale). Honesty upgrade:

| Field | Uncalibrated | Calibrated |
|-------|--------------|------------|
| `FreeSpacePayload.units` | `ordinal` | `m` |
| `depth_kind` | relative / metric_estimated | `metric_calibrated` |
| `nearness_*` | 0..1 | 0..1 (still ordinal cue) |
| `distance_m` on obstacle | absent / null | mean calibrated depth in blob (meters) |
| band fractions | near/mid/far frac | unchanged semantics |

`assemble._units_for_depth_kind`:

```python
def _units_for_depth_kind(kind: DepthKind) -> str:
    if kind == DepthKind.METRIC_CALIBRATED:
        return "m"
    return "ordinal"  # relative AND metric_estimated stay ordinal for free-space
```

**Do not** set free-space `units="m"` for `metric_estimated` alone — Phase 5 research and tests already lock that (estimated ≠ calibrated).

---

## API surface

### Keep existing

| Route | Role in v0.3 |
|-------|----------------|
| `GET/PATCH /api/depth/config` | `depth_mode` only (relative / metric_indoor / metric_outdoor) |
| `GET /api/status` | Add calibration summary fields (active, scale, method, camera_id) |
| `GET /v1/snapshot` · `WS /v1/stream` | Inherit kind/units via assemble — no separate calib payload required |

### NEW router `routes_calibration.py` (suggested)

| Method | Path | Body / behavior |
|--------|------|-----------------|
| `GET` | `/api/depth/calibration` | Applied + draft snapshot (no secrets) |
| `POST` | `/api/depth/calibration/sample` | `{point_uv\|bbox_xyxy, known_meters, note?}` → observed_raw filled |
| `DELETE` | `/api/depth/calibration/samples` | Clear draft samples |
| `POST` | `/api/depth/calibration/compute` | Fit draft params from samples |
| `POST` | `/api/depth/calibration/apply` | Promote applied; optional `{persist: bool}` |
| `POST` | `/api/depth/calibration/cancel` | Clear applied + draft (runtime) |
| `POST` | `/api/depth/calibration/persist` | Write applied params to disk |
| `DELETE` | `/api/depth/calibration` | Clear runtime + delete file (explicit) |
| `PUT` | `/api/depth/calibration/manual` | Power-user `{scale, offset?}` without samples |

Handlers:

- Read `snapshot_depth()` for samples only.
- Mutate `CalibrationState` only.
- **Never** call `worker.process`, open cameras, or write PerceptionStore directly (DepthLoop owns writes).

### Status fields (additive on `/api/status`)

```json
{
  "depth_kind": "metric_calibrated",
  "depth_unit": "m",
  "calibration_active": true,
  "calibration_scale": 1.23,
  "calibration_offset": 0.0,
  "calibration_method": "known_height",
  "calibration_sample_count": 2,
  "calibration_camera_id": "usb0"
}
```

Omit or set `calibration_active: false` when inactive — never imply meters via UI copy alone.

---

## Persistence

### Recommended location

```
$SENTRY_CONFIG_DIR/calibration/{camera_id}.json
# default: ~/.config/sentry-ai/calibration/
# override: SENTRY_CALIBRATION_DIR
```

**Why not profile YAML:** Profiles are shared across cameras/machines; scale is **per-camera / per-mount**. Profile may later hold a *path* override, not the numbers themselves.

**Why not model cache:** Weights ≠ operator geometry; keep calibration under config.

### File schema (versioned JSON)

```json
{
  "version": 1,
  "camera_id": "usb0",
  "scale": 1.234,
  "offset": 0.0,
  "method": "known_height",
  "sample_count": 2,
  "residual_rms": 0.08,
  "depth_mode_at_fit": "relative",
  "model_id_at_fit": "depth-anything/Depth-Anything-V2-Small-hf",
  "created_at": 1730000000.0
}
```

Load rules:

- Missing file → inactive (normal).
- Corrupt / failed validation → log warning, start inactive (soft).
- `camera_id` mismatch → do not apply; log reason.
- Optional: refuse auto-apply if `model_id_at_fit` ≠ current model (warn + require re-confirm) — **recommended for honesty**, can be soft-warn in MVP.

---

## UI integration (Live Preview)

### Constraints

- Static `index.html` only (no React rewrite) — same as v1.0/v0.2.
- Server MJPEG remains single truth for depth colormap; wizard does not draw a second depth path.
- Badge already understands `metric_calibrated` string (UI checks estimated **or** calibrated for `m` display) — keep that; ensure backend only emits calibrated when applied.

### Wizard UX (MVP)

1. **Entry:** “Calibrate depth…” control near stage toggles / depth metrics.  
2. **Prereq check:** depth stage on + recent `depth_frame_id` + calibration inactive (or “Recalibrate” cancels first).  
3. **Method:** Known object height / distance (primary); manual scale (advanced).  
4. **Sample:** Click-to-sample or bbox + numeric meters (synthetic-testable via API without clicks).  
5. **Compute:** Show proposed scale + residual; **do not** change `depth_kind` yet.  
6. **Apply:** Runtime promotion; colormap/free-space update within ~1 depth frame.  
7. **Persist / Forget:** Explicit buttons; default apply-without-persist is OK for session-only.  
8. **Honesty copy:** “Hobby monocular scale — not vehicle-grade. Relative depth is never meters.”

### Visual feedback

- After apply: footer `Depth: metric_calibrated (m)` + optional scale readout.
- Free-space metric: show obstacle distances when `distance_m` present; otherwise keep obstacle count only.
- Cancel: badge reverts to `relative` or `metric_estimated` on next status poll.

---

## Integration points (explicit)

| Integration | How |
|-------------|-----|
| **Depth worker** | Unchanged output contract; still `kind_for_mode`. Calibration wraps **after** process. |
| **DepthLoop** | Inject `CalibrationState`; transform before `set_depth`. |
| **PerceptionStore** | No writer ownership change; depth slot receives calibrated maps. |
| **FreeSpaceLoop** | Reads `depth.kind`; sets units / optional `distance_m`. |
| **assemble** | Wire honesty for units + optional distance. |
| **routes_depth** | Leave mode-only; link docs to calibration routes. |
| **create_app** | Register calibration router; stash state on `app.state`. |
| **cli.serve** | Construct + load + inject; banner line. |
| **PipelineState** | No need to own calibration (separate control plane). Optional later: stage flag unused. |
| **Detection / OV / FrameBus** | Zero coupling. |

---

## Patterns to follow

### Pattern 1: Loop stable, post-process swappable

**What:** DepthLoop remains bus → process → store; calibration is a pure function on the result.  
**When:** Always for v0.3.  
**Why:** Same discipline as DetectionLoop + edge workers (v0.2).

### Pattern 2: Draft vs applied

**What:** Fitting samples never changes `depth_kind` until explicit apply.  
**When:** Wizard compute step.  
**Why:** Prevents accidental meter claims mid-wizard; matches soft/strict honesty culture.

### Pattern 3: Single store truth

**What:** UI, `/v1`, free-space all read PerceptionStore products after DepthLoop write.  
**When:** Always.  
**Why:** UI-06; no browser-side scale fiction.

### Pattern 4: Estimated ≠ calibrated

**What:** DAV2 metric heads → `metric_estimated`; user scale → `metric_calibrated`.  
**When:** Labeling and free-space units.  
**Why:** Enum designed for this; Phase 4/5 docs already distinguish.

### Pattern 5: CI without a room

**What:** Unit tests synthesize HxW depth + known scale + fake samples; API tests use injected store maps.  
**When:** Default pytest.  
**Why:** PROJECT.md — no physical hardware required.

---

## Anti-patterns to avoid

| Anti-pattern | Why bad | Instead |
|--------------|---------|---------|
| Setting `METRIC_CALIBRATED` from `depth_mode` | Lies — mode is model head, not user GT | Only `CalibrationState.apply` |
| Free-space `units="m"` on `metric_estimated` | Phase 5 explicitly forbade | Ordinal until calibrated |
| Applying scale only in UI colormap | Robots see relative; dual truth | DepthLoop transform |
| Double-scaling (sample on calibrated map, fit again) | Compound error | Sample only when inactive |
| Chessboard intrinsics as MVP gate | Out of milestone scope | Known height / marker scale first |
| `distance_m` on relative obstacles | Robot stops at wrong range | Field only when calibrated |
| Rewriting FreeSpaceLoop to ground-plane RANSAC | Scope + mount assumptions | Keep near-field bands; additive meters |
| Persisting under model cache as weights | Wrong lifecycle | Config dir per camera_id |
| Blocking DetectionLoop / FrameBus changes “while we’re here” | Spine freeze preference | Depth path only |
| Claiming ±cm accuracy in docs | Liability; monocular hobby | “Approximate operator scale” language |

---

## Suggested build order (roadmap-ready)

Dependencies flow **pure math → runtime state → depth wire-in → free-space honesty → API → UI → persist polish → docs/tests**.

### Phase order recommendation

1. **Calibration core (pure)**  
   - Samples, fit (`scale = known / observed_raw`), validation clamps, residual.  
   - Golden unit tests with synthetic arrays.  
   - **Avoids:** API/UI thrash before math is honest.

2. **CalibrationState + DepthLoop hook**  
   - Thread-safe apply/cancel; `apply_map`; inject from serve (inactive default).  
   - Tests: process → set_depth kind promotion with fake worker.  
   - **Avoids:** Dual truth if free-space/UI land first.

3. **Free-space + assemble honesty**  
   - `units="m"` only for `METRIC_CALIBRATED`; optional `distance_m`.  
   - Fix `_units_for_depth_kind` stub.  
   - Extend free-space unit tests (estimated still ordinal).  
   - **Avoids:** Wire lying about meters.

4. **API routes + `/api/status` fields**  
   - Sample from store depth; compute/apply/cancel; no inference in handlers.  
   - ASGI tests with preloaded depth product.  
   - **Avoids:** UI calling non-existent endpoints.

5. **Persist load/save + serve banner**  
   - Per-`camera_id` JSON; soft-fail corrupt; camera_id match.  
   - **Avoids:** Losing session calibration; wrong-camera auto-apply.

6. **Live Preview wizard**  
   - Static HTML/JS; draft vs applied; honesty copy; apply/cancel/persist buttons.  
   - **Avoids:** Building UI against unstable API.

7. **Docs + packaging polish**  
   - Operator calibration guide; update `perception-frame.md` free-space units table; README honesty.  
   - CI markers already green from 1–4.

### Parallelism notes

- (1) can start immediately offline.  
- (6) can mock API after (4) contract freezes.  
- Detection/edge code stays out of the critical path entirely.

### Research flags for later phases

| Topic | Flag | Why |
|-------|------|-----|
| Multi-sample robust fit (RANSAC / outlier reject) | Phase-specific if single-sample residual is poor | MVP may be 1–3 point mean scale |
| Intrinsics + height-from-bbox (true 3D height) | Deferred (out of milestone) | Needs fx,fy + pose; not required for affine depth scale |
| Metric band cutoffs in meters (vs ordinal cuts) | Optional follow-on | Current near/mid cuts are nearness 0..1; changing UX may confuse |
| Auto-invalidate calib on `depth_mode` change | Recommended small hook | Mode switch changes raw distribution — clear or warn |
| Per-profile calib path override | Low priority | camera_id file is enough for makers |

---

## Scalability / concurrency

| Concern | Guidance |
|---------|----------|
| Thread safety | `CalibrationState` lock; DepthLoop reads applied params once per frame; API writers use same lock |
| Hot-path cost | One multiply+add on HxW float32 — negligible vs DAV2 |
| Store isolation | Continue immutable-after-set maps; write **new** array after transform (do not mutate worker output in place if shared) |
| Sample path | API may snapshot depth while DepthLoop writes — existing store lock already isolates snapshots |
| Multi-cam | Schema has `camera_id`; persist per id; single active source still v1 runtime |

---

## Confidence assessment

| Area | Level | Notes |
|------|-------|-------|
| Spine plug-in at DepthLoop | **HIGH** | Code-verified writer ownership + free-space consumer |
| Never promote via `depth_mode` alone | **HIGH** | `kind_for_mode` + enum docs + Phase 4 research |
| Free-space ordinal until calibrated | **HIGH** | Phase 5 tests + assemble stub comment |
| Affine scale sufficiency for maker UX | **MEDIUM** | Good enough for known-height; not photogrammetry |
| Exact wizard interaction (click vs bbox) | **MEDIUM** | Product UX; API can support both |
| Persist path conventions | **MEDIUM** | Opinionated; easy to adjust if config layout differs |

---

## Gaps / open questions

1. **Height vs distance ground truth:** Known *object height* needs intrinsics + vertical extent in image for true metric depth; known *distance to marker* maps 1:1 to depth scale. **MVP recommendation:** treat `known_meters` as **distance along the depth axis at the sample region** (marker / measured range), with UI copy that says “distance to target,” not “object height in cm” unless a later phase adds intrinsics.  
2. **Relative polarity:** Relative DAV2 maps are ordinal; scale still produces “metric-ish” values that are affine-correct at sample points but may be biased elsewhere — residual_rms + docs honesty.  
3. **Whether `DepthPayload` gains `scale` field** on the wire — optional; stats keys may be enough for v0.3.  
4. **Interaction with metric_indoor/outdoor heads:** Calibrating an already-metric head is a residual correction; still use `metric_calibrated` when user applies GT (stricter honesty than estimated).

---

## Sources (code + docs)

| Source | Informs | Confidence |
|--------|---------|------------|
| `src/sentry_ai/models/depth/loop.py` | DepthLoop write path; kind from worker | HIGH |
| `src/sentry_ai/models/depth/mapping.py` | Mode → kind; never calibrated | HIGH |
| `src/sentry_ai/models/depth/worker.py` | DepthResult contract | HIGH |
| `src/sentry_ai/state/perception_store.py` | Depth/FreeSpace products; writer ownership | HIGH |
| `src/sentry_ai/spatial/loop.py` + `free_space.py` | Ordinal free-space; kind copy | HIGH |
| `src/sentry_ai/api/assemble.py` | Units stub for METRIC_CALIBRATED | HIGH |
| `src/sentry_ai/api/routes_depth.py` | Mode-only config surface | HIGH |
| `src/sentry_ai/schemas/enums.py` + `perception.py` | DepthKind + validators + ObstacleCue | HIGH |
| `src/sentry_ai/cli.py` (`serve`) | Construction site for inject + load | HIGH |
| `src/sentry_ai/ui/static/index.html` | Badge already lists metric_calibrated | HIGH |
| `.planning/PROJECT.md` (v0.3 goals) | Milestone scope + out-of-scope | HIGH |
| Phase 4/5 research (metric calibration deferred) | Historical intent for this milestone | HIGH |
| `docs/perception-frame.md` | Wire honesty language to update | HIGH |

---

*Architecture research for Sentry AI v0.3 Metric Depth Calibration UX. Apply operator scale after depth inference in DepthLoop; promote `metric_calibrated` only when CalibrationState is applied and valid; free-space meters only then; leave DetectionLoop / FrameBus / PerceptionStore writer contracts frozen.*
