# Stack Research — v0.3 Metric Depth Calibration UX

**Domain:** Monocular depth scale calibration (known height / marker → metric scale)  
**Project:** Sentry AI — milestone **v0.3 Metric Depth Calibration UX**  
**Researched:** 2026-08-11  
**Scope:** Stack **additions/changes only** for Live Preview calibration wizard, ground-truth scale from known heights/markers, persist + re-apply calibration, honest metric scale on depth + free-space.  
**Out of scope for this file:** YOLO/ORT/TRT/edge factory (shipped v0.2); stereo/SLAM; full camera intrinsic photogrammetry as primary path.  
**Overall confidence:** **HIGH** for “no new third-party packages” and reuse of existing FastAPI/static/numpy/OpenCV stack (code-verified); **MEDIUM** for exact free-space meter band UX details (product design, not package choice).

---

## Decision (one-liner)

**Add zero new pip dependencies.** Implement metric depth calibration as in-repo pure Python (numpy least-squares + existing OpenCV + Pydantic 2 + PyYAML + FastAPI REST + static Live Preview wizard). Persist a per-`camera_id` affine scale (and optional shift) file; apply post-DAV2; promote `DepthKind` to `metric_calibrated` only when a valid calibration is active. Do **not** pull SLAM, React, scipy, or a new depth model.

---

## Recommended Stack

### Core (unchanged — already ship)

| Technology | Version (project pin) | Purpose | Why |
|------------|----------------------|---------|-----|
| Python | **≥3.11** | Runtime | [VERIFIED] `pyproject.toml` |
| FastAPI | **≥0.141,<1** | REST wizard API + status | Existing control-plane pattern (`/api/depth/config`, `/api/pipeline/config`) |
| Uvicorn | **≥0.52,<1** | ASGI serve | Unchanged |
| Pydantic 2 | **≥2.13,<3** | Calibration record + request bodies (`extra=forbid`) | Matches all wire/config models |
| PyYAML | **≥6.0.3** | Persist calibration files | Already core; same family as profiles |
| NumPy | **≥2.0,<2.5** | Scale/shift LS fit + map apply | Already used for depth maps / free-space |
| OpenCV headless | **≥4.10,<6** | Optional marker detect; freeze-frame JPEG; overlays | Already core; ArUco lives in main `cv2.aruco` since OpenCV 4.7 [CITED: OpenCV 4.x ArUco tutorial] |
| Static Live Preview | `ui/static/index.html` | Calibration wizard UI | Project decision: static HTML, not React rewrite [VERIFIED] `PROJECT.md` Key Decisions |

### Depth / free-space path (unchanged models)

| Technology | Role in v0.3 | Notes |
|------------|--------------|-------|
| HF DAV2 Small (`depth` extra) | Source of **relative** (default) or **metric_estimated** maps | Calibration is a **post-process**, not a new model |
| `DepthKind` enum | Honesty spine | `relative` → (cal apply) → `metric_calibrated` + `unit="m"` |
| Free-space loop | Consume scaled depth when calibrated | Keep near-field bands; set `units="m"` only when kind is calibrated |
| PerceptionStore | Hold calibrated map + kind/unit | Same keep-latest product; no bulk depth on `/v1` wire |

### Supporting (stdlib / already present — use these, do not re-invent elsewhere)

| Library / tool | Purpose | When |
|----------------|---------|------|
| `pathlib` + `threading.Lock` | Calibration file paths + runtime apply state | Mirror `PipelineState` / depth mode lock patterns |
| `dataclasses` / Pydantic models | In-process `CalibrationState` + on-disk record | Validate on load; reject bad files honestly |
| `pytest` + `httpx` (`dev` extra) | Unit + ASGI tests without a real room | Synthetic depth maps + fake click samples |
| Existing MJPEG + `/api/status` | Visual feedback after apply/cancel | Server-drawn colormap already reflects store depth |

### Development tools (unchanged)

| Tool | Purpose | Notes |
|------|---------|-------|
| `uv` | Install / lock | No new extras required for calibration |
| `ruff` | Lint | Keep new modules under `src/sentry_ai/` |
| Synthetic source | CI-safe wizard math tests | Already default for headless CI |

---

## What to build (stack shape — not packages)

These are **in-repo modules**, not new dependencies:

| Module (suggested) | Responsibility | Stack used |
|--------------------|----------------|------------|
| `sentry_ai/spatial/calibration/` or `models/depth/calibration.py` | Pure scale math: sample → fit → apply | **numpy only** |
| `sentry_ai/schemas/calibration.py` | On-disk + API Pydantic models | **pydantic** |
| `sentry_ai/config/calibration_store.py` | Load/save/delete per `camera_id` YAML | **pyyaml** + pathlib |
| `sentry_ai/control/calibration_state.py` | Thread-safe active scale/shift + status | stdlib lock (mirror `PipelineState`) |
| `sentry_ai/api/routes_calibration.py` | Wizard REST: freeze, sample, fit, apply, cancel, persist | **FastAPI** |
| `ui/static/index.html` | Wizard panel + click coords + apply/cancel | Vanilla JS (no npm) |

**Hot-path integration (minimal):**

```
DepthAnythingWorker.process → raw depth_map + kind/unit
        │
        ▼
CalibrationState.apply_if_active(depth_map, kind, unit)
        │  if active: map' = scale * map + shift; kind=metric_calibrated; unit="m"
        ▼
PerceptionStore.set_depth(...)
        │
        ▼
FreeSpaceLoop (reads store depth; inherits kind; units honesty in assemble)
```

Do **not** re-run DAV2 when applying/cancelling calibration — only re-label and re-scale the latest map (and let free-space recompute from the next depth product).

---

## Calibration math (stack implication)

### Recommended model: affine scale (+ optional shift)

Monocular relative depth is typically recovered **up to scale (and often shift)**. Maker-grade recovery:

```text
d_metric = scale * d_raw + shift     # shift default 0 when samples thin
```

| Fit | Formula | When |
|-----|---------|------|
| **Scale-only** (MVP default) | `scale = median(D_i / d_i)` over known-distance samples | 1–N point distances; robust to outliers with median |
| **Scale + shift** | numpy `lstsq` / normal equations on `d_i → D_i` | ≥2 diverse distances; better for affine-invariant relative heads |
| **Reject** | `scale <= 0`, non-finite, or residual above threshold | Stay `relative` / prior kind; never claim meters |

**numpy is enough** — `np.median`, `np.linalg.lstsq`. **Do not add scipy** for one linear fit.

### Ground-truth sample types (product → stack)

| Sample method | User input | Stack need | Milestone role |
|---------------|------------|------------|----------------|
| **Known distance** (tape to wall / floor mark) | Click pixel + `distance_m` | Sample depth at `(u,v)` on **frozen** frame | **Primary** — simplest, most honest |
| **Known object height** | Click top+bottom + `height_m` | Depth samples along segment; optional default FOV→`fy` for geometric Z | **Primary UX label**; implement carefully (see pitfalls below) |
| **Printed marker (ArUco)** | Known side length (m) | `cv2.aruco` detect + optional `solvePnP` if intrinsics present | **Optional stretch** — **no new package**; needs intrinsics story for true metric pose |

**Opinionated default path for v0.3:**  
Wizard collects **≥1 known-distance sample** (tape measure). Height/marker UX can *produce* distance samples under the hood, but the fitter always sees `(d_raw, D_meters)` pairs. That keeps the math module tiny and testable with synthetic maps.

### Known-height without full intrinsics

| Approach | Stack | Honesty |
|----------|-------|---------|
| **A. Tape distance preferred** | None extra | Best accuracy for makers |
| **B. Height + assumed FOV** | numpy only: `fy = (H_px/2) / tan(fov_h/2)` from image width + default FOV (e.g. 60–70°) | Label as approximate; still `metric_calibrated` only after residual checks |
| **C. Full `calibrateCamera` chessboard** | OpenCV already has it | **Deferred** by milestone (PROJECT.md out-of-scope) |

Do **not** block the wizard on a full intrinsic suite.

### Optional ArUco (no pip add)

OpenCV ≥4.7 includes ArUco in main modules (`cv2.aruco.ArucoDetector`, `getPredefinedDictionary`) [CITED: https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html].  
`opencv-python-headless` already in core deps — **if** the installed wheel includes `cv2.aruco` (true for modern 4.10+ main builds), marker assist is free.

| Rule | Detail |
|------|--------|
| Primary wizard | Manual click + known distance/height — works without markers |
| ArUco | Optional sample source only; never required for CI or synthetic tests |
| Pose metric | `solvePnP` needs camera matrix — without user intrinsics, use marker only as a **clickable ROI** + user-entered distance, **or** document crude default FOV intrinsics |
| Do not add | `pupil-apriltags`, `dt-apriltags`, `aruco` pip packages |

---

## Persistence (files, not a database)

### Format

**YAML** (preferred) or JSON — YAML matches profiles and is already a core dep.

```yaml
# Example shape (illustrative — schema owned by pydantic model)
schema_version: 1
camera_id: "usb-0"
depth_mode_base: "relative"   # mode when samples were taken
scale: 1.847
shift: 0.0
unit: "m"
method: "known_distance_lstsq"  # or known_height / aruco_assist
sample_count: 3
residual_rmse: 0.12
created_at: "2026-08-11T12:00:00Z"
samples: []   # optional audit; can omit bulky depth crops
```

### Path layout (opinionated)

Reuse the existing Sentry-owned root (no `platformdirs`):

| Path | Content |
|------|---------|
| `$SENTRY_MODEL_CACHE/calibration/{safe_camera_id}.yaml` | Default persist location |
| Default root | `~/.cache/sentry-ai` via existing `default_cache_root()` |
| Override | Optional `SENTRY_CALIBRATION_DIR` (mirror `SENTRY_MODEL_CACHE` style) |
| Explicit CLI | `sentry serve --calibration-file PATH` (optional) |

**Why under cache root, not a new XDG stack:** project already centralizes maker state under `~/.cache/sentry-ai` (weights, HF, AV helpers). Adding `platformdirs` / `appdirs` is pure dependency noise for one directory.

**Key by `camera_id`:** multi-cam is still extension-only, but schema already carries `camera_id` — calibration files must not silently apply across cameras.

### Load policy at `sentry serve`

1. Resolve `camera_id` from active source.  
2. If calibration file exists and validates → load into `CalibrationState` (inactive until “apply”, **or** auto-apply if file marks `auto_apply: true` — product choice; recommend **auto-apply on serve** when file present + valid so robots get meters without re-wizard).  
3. Invalid file → log warning, stay uncalibrated, never claim `metric_calibrated`.  
4. Cancel → clear runtime state; optional delete/persist “disabled” without deleting history.

---

## UI wizard stack

### Keep: static Live Preview

| Choice | Why |
|--------|-----|
| **Vanilla HTML/CSS/JS in `index.html`** | Matches shipped UI-01..UI-06 patterns; zero frontend build |
| **REST, not new WS protocol** | Mirror open-vocab / pipeline PATCH patterns |
| **Click → normalized or pixel coords on `<img>`** | `offsetX/Y` + `naturalWidth/Height` mapping is enough |
| **Freeze frame for samples** | Depth map must match the image the user clicked — live MJPEG alone is racey |

### Suggested API surface (stack, not full design)

| Method | Path | Role |
|--------|------|------|
| `GET` | `/api/depth/calibration` | Status: active?, scale, shift, kind, residual, path |
| `POST` | `/api/depth/calibration/freeze` | Capture `frame_id` + optional JPEG thumbnail for wizard |
| `POST` | `/api/depth/calibration/sample` | Body: coords + known `distance_m` or height segment |
| `POST` | `/api/depth/calibration/fit` | Compute scale/shift from samples (preview, not yet live) |
| `POST` | `/api/depth/calibration/apply` | Activate → products become `metric_calibrated` |
| `POST` | `/api/depth/calibration/cancel` | Deactivate; restore prior kind honesty |
| `POST` | `/api/depth/calibration/save` | Write YAML |
| `DELETE` | `/api/depth/calibration` | Clear runtime + optional file delete |

Handlers: **no camera open**, **no model inference** — only bus/store/calibration state (same rule as `routes_depth.py`).

### Visual feedback

Reuse server-side depth colormap on MJPEG. After apply, `/api/status` already surfaces `depth_kind` / `depth_unit` — extend badge copy for `metric_calibrated` (UI already special-cases that kind string). Free-space footer should show `units=m` when calibrated.

---

## Free-space / wire honesty (stack touchpoints)

| Layer | Today | v0.3 change |
|-------|-------|-------------|
| `DepthKind.METRIC_CALIBRATED` | Exists, unused on live path | Set when calibration active |
| `assemble._units_for_depth_kind` | Always `"ordinal"` even for calibrated | Return `"m"` when kind is `metric_calibrated` (and free-space path uses metric depth) |
| `ObstacleCue` | No `distance_m` | Keep optional absence as default; **additive** `distance_m` only if product wants it — do not break `extra=forbid` consumers without schema version discipline |
| Relative + unit `m` | Rejected by validators | Unchanged — calibration must flip **kind**, not just unit |

**No new serialization library.** Stay Pydantic + existing `/v1` envelope.

---

## Installation

```bash
# No new packages for calibration itself.
# Depth path still needs the existing depth extra (DAV2):
uv sync --extra dev --extra depth
# Typical maker with detect + depth:
uv sync --extra dev --extra detect --extra depth

# Unchanged edge extras (not required for this milestone):
# uv sync --extra onnx
```

**`pyproject.toml`:** **do not** add a `calibration` extra. There is nothing to install.

Optional docs-only note: if ArUco symbols are missing in a weird OpenCV build, document “upgrade opencv-python-headless ≥4.10” — still no separate package.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why not (this milestone) |
|----------|-------------|-------------|---------------------------|
| Scale fit | **numpy** median / `lstsq` | scipy.optimize / scikit-learn | Overkill for 1-parameter affine; new deps |
| Persist | **YAML file** per camera | SQLite / Redis / profile YAML merge | Files are greppable, CI-simple, match maker mental model; don’t bloat profiles with per-camera secrets |
| Config paths | **`$SENTRY_MODEL_CACHE/calibration`** | `platformdirs` XDG | Avoid new dep; consistent with existing cache root |
| UI | **Static HTML wizard** | React/Vue/Svelte SPA | Explicitly deferred rewrite cost; static already ships controls |
| Marker | **Manual click first**; optional `cv2.aruco` | pupil-apriltags / dedicated fiducial stack | OpenCV enough; markers optional |
| Metric depth model | **Calibrate relative (or refine metric_estimated)** | Switch default to metric Small head only | Metric heads still estimated domain-split; calibration is the honesty path to `metric_calibrated` |
| Intrinsics | **Default FOV optional; no chessboard primary** | Full OpenCV calibrateCamera suite UX | Out of milestone; large UX surface |
| Mapping | **Scale depth map only** | COLMAP / ORB-SLAM3 / Open3D TSDF | Explicit product anti-scope (no dense SLAM) |
| Apply site | **Post-worker pure function** | Bake scale into torch model | Unnecessary; harder to cancel; confuses HF weights |

---

## What NOT to Use / NOT to Add

| Avoid | Why | Use instead |
|-------|-----|-------------|
| **React / npm frontend build** | Breaks one-file Live Preview ship path; milestone is wizard UX not SPA | Extend `ui/static/index.html` |
| **scipy / sklearn / statsmodels** | One linear fit does not justify them | `numpy.linalg.lstsq`, `np.median` |
| **Open3D, trimesh, pyrender** | 3D mapping / meshing — out of product scope | HxW depth scale only |
| **COLMAP, hloc, ORB-SLAM, RTAB-Map, GTSAM** | Full SLAM / SfM — rewrite-class complexity | Known-distance scale recovery |
| **pupil-apriltags / dt-apriltags / separate aruco pip** | Duplicate OpenCV capability; wheel/platform pain | `cv2.aruco` if needed |
| **platformdirs / appdirs** | New dep for one directory | `default_cache_root() / "calibration"` |
| **SQLAlchemy / sqlite calibration DB** | Overkill for one record per camera | YAML file |
| **New depth network / Metric3D / ZoeDepth as required** | Different stack + honesty story; not needed for scale UX | Keep DAV2 Small + calibrate |
| **Live ORT/TRT for DAV2** | Deferred (v0.2 + PROJECT out-of-scope) | Torch/HF depth unchanged |
| **tensorrt / onnxruntime changes** | Unrelated to calibration | Leave v0.2 detection edge stack alone |
| **ROS2 metric TF package** | Deferred extension | Optional later; core is `/v1` honesty |
| **Full chessboard intrinsic suite as primary** | Out of milestone | Optional later; default FOV only if height geometry needs it |
| **WebRTC / canvas video re-architecture** | MJPEG + click mapping works | Keep `/preview/mjpeg` |
| **Storing full float depth maps on disk in calibration files** | Large, privacy-sensitive, unnecessary for re-apply | Store scale/shift + metadata only |
| **Labeling relative depth as meters without kind flip** | Violates FOUND-03 / validators | Always set `metric_calibrated` + `unit="m"` together |

---

## Stack Patterns by Variant

**If wizard samples are known distances only:**  
- Use scale-only or scale+shift numpy fit.  
- No OpenCV calib3d required on the critical path.

**If known-height clicks without tape:**  
- Prefer converting height → approximate Z via default FOV, then treat as distance sample.  
- Document residual error; never claim vehicle-grade.

**If operator has a printed ArUco of known size:**  
- Optional: detect corners with `cv2.aruco`, sample median depth in marker ROI, combine with user distance **or** crude pose.  
- Gate behind “marker assist” — not required for CI.

**If `depth_mode` is already `metric_indoor` / `metric_outdoor`:**  
- Calibration still allowed as **scale refine** → kind becomes `metric_calibrated` (not `metric_estimated`).  
- Persist `depth_mode_base` so reload stays coherent.

**If headless robot (`--no-ui`):**  
- Load saved YAML at serve; no wizard required.  
- REST apply/save still available for automation.

**If synthetic / CI:**  
- Unit-test fit + apply with synthetic `HxW` arrays; HTTP tests with `httpx` ASGI client; no camera, no HF download.

---

## Version Compatibility

| Package A | Compatible with | Notes |
|-----------|-----------------|-------|
| `numpy>=2.0,<2.5` | Python 3.11 | LS fit + broadcasting on depth maps |
| `opencv-python-headless>=4.10,<6` | numpy 2.x | ArUco in main module for 4.7+; verify `import cv2.aruco` in env once |
| `pydantic>=2.13,<3` | FastAPI 0.141+ | Calibration request/response models |
| `pyyaml>=6.0.3` | pathlib write/read | Same as profile loader style |
| `depth` extra (torch/transformers) | Calibration post-process | Calibration does **not** import torch |
| Existing `DepthKind` / validators | Calibration apply | Relative forbids unit; calibrated must set `unit="m"` |

No lockfile changes expected for this milestone.

---

## Confidence Assessment

| Area | Level | Notes |
|------|-------|-------|
| No new pip deps required | **HIGH** | All primitives already in core + depth extra |
| numpy affine scale is sufficient | **HIGH** | Standard monocular scale recovery; LS is textbook |
| Static HTML wizard feasible | **HIGH** | Existing conf/pipeline/OV controls prove the pattern |
| YAML per-camera persist | **HIGH** | pyyaml + cache root already project-standard |
| ArUco without extra package | **MEDIUM** | OpenCV docs confirm main-module ArUco; confirm wheel has `cv2.aruco` in CI image once |
| Known-height geometry without intrinsics | **MEDIUM** | Prefer known-distance samples; height needs FOV assumptions |
| Free-space meter bands design | **MEDIUM** | Units flip is clear; band threshold semantics need phase design (not a package decision) |

---

## Sources

- In-repo stack truth: `pyproject.toml`, `src/sentry_ai/models/depth/mapping.py`, `schemas/enums.py` (`DepthKind`), `schemas/perception.py`, `spatial/free_space.py`, `api/assemble.py` (`_units_for_depth_kind`), `api/routes_depth.py`, `ui/static/index.html`, `models/cache.py` (`default_cache_root`), `docs/perception-frame.md`, `docs/export/depth-anything-v2.md`, `PROJECT.md` v0.3 scope  
- OpenCV ArUco (main module, detect + pose needs intrinsics): https://docs.opencv.org/4.x/d5/dae/tutorial_aruco_detection.html [CITED 2026-08-11]  
- Phase 4 depth research (relative default, metric_estimated honesty, no bulk float on wire): `.planning/milestones/v1.0-phases/04-monocular-depth/04-RESEARCH.md`  
- Product constraints: no LiDAR, no dense SLAM, static Live Preview, honest `depth_kind` — `PROJECT.md`

---

## Opinionated defaults for roadmap

1. **Zero new dependencies** — calibration is product logic on the existing Python/FastAPI/static stack.  
2. **Post-process scale/shift** on depth maps — never retrain or swap models for calibration.  
3. **Primary GT = known distance samples**; height/marker UX feeds the same fitter.  
4. **Persist YAML under `$SENTRY_MODEL_CACHE/calibration/{camera_id}.yaml`**; auto-load on serve.  
5. **Wizard in static HTML + REST**; freeze-frame before click samples.  
6. **`metric_calibrated` + `unit="m"` only when active and valid**; cancel restores prior honesty.  
7. **Do not** add SLAM, React, scipy, chessboard-primary intrinsics, or depth ORT/TRT this milestone.

---

*Stack research for: Sentry AI v0.3 Metric Depth Calibration UX*  
*Researched: 2026-08-11*
