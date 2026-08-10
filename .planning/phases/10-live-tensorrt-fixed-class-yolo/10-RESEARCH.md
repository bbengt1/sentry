# Phase 10: Live TensorRT Fixed-Class YOLO - Research

**Researched:** 2026-08-10  
**Domain:** Live Ultralytics-native TensorRT path for fixed-class YOLO (factory soft-stub → real `.engine` loader; on-device engine lifecycle; Jetson packaging honesty)  
**Confidence:** HIGH (code-verified Phase 8/9 factory + Ultralytics 8.4.116 `TensorRTBackend`; no Jetson hardware in this session — CI strategy intentionally mock-only)

> **Note:** No `*-CONTEXT.md` for this phase (discuss-phase not run). Locked decisions below are taken from `.planning/STATE.md`, ROADMAP, REQUIREMENTS, and Phase 8–9 shipped patterns.

<user_constraints>
## User Constraints (from STATE / ROADMAP / prior phase locks)

### Locked Decisions
- v0.2 = live ORT + live TRT for **fixed-class YOLO only**; depth / open-vocab stay PyTorch
- Plug-in at serve factory (`build_detection_worker`); DetectionLoop / FrameBus / PerceptionStore / `/v1` **frozen**
- Ultralytics-native load path (`YOLO("*.engine")`) — **no** custom TRT decode / raw TensorRT API in v0.2
- **No** `tensorrt` pip extra; **no** pip `tensorrt` as required app dependency — system / JetPack TensorRT only
- **No** multi-SKU prebuilt `.engine` files in wheel / repo / Releases
- On-device engine build required (same GPU arch + TRT / JetPack as production)
- Soft torch fallback default (loud reason codes); sticky resolve policy is Phase 11
- Factory remains sole author of `backend_live` (Phase 8)
- Artifact resolution via existing `resolve_detector_artifact` + env `SENTRY_DETECTOR_ENGINE` (Phase 8 BACK-04)
- Reuse `YoloDetectionWorker` with `weights=` path (Phase 9 ORT pattern — no thin TRT wrapper class)
- Dep probe via `importlib.util.find_spec` only; **no** module-level `import tensorrt` / `import onnxruntime`
- Default CI never loads real `.engine` graphs, downloads weights, or requires Jetson / system TensorRT

### Claude's Discretion
- Exact soft-fallback reason vocabulary for TRT (`trt_artifact_missing` / `trt_dep_missing` vs keep partial legacy codes)
- Whether live TRT is gated only on `find_spec("tensorrt")` or also probes CUDA availability at factory time
- How deeply Jetson JetPack matrix is documented (SKU table depth vs “verify on device”)
- Whether parity tests live in new `tests/test_trt_parity.py` or extend factory/status modules only
- Optional opt-in real-engine marker (must remain non-default / non-CI-required)
- Doc surface split across `jetson-packaging.md` vs `yolo26-onnx-tensorrt.md` vs `architecture.md` / `configuration.md`

### Deferred Ideas (OUT OF SCOPE)
- Sticky thrash-free fallback modes + soft vs strict policy (Phase 11 / BACK-03)
- Dual-model VRAM guardrails as first-class claims (Phase 11)
- Live ORT/TRT for depth or YOLOE
- Full edge-serve narrative polish + AGPL lineage refresh (Phase 12 EDGE-DOC-*)
- CI selection matrix hardening beyond TRT-specific unit tests (Phase 12 EDGE-CI-*)
- Prebuilt multi-SKU engines on GitHub Releases
- Custom TensorRT `Runtime` / binding / NMS decoder outside Ultralytics
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRT-01 | Fixed-class YOLO can run live via TensorRT when profile prefers `tensorrt` and a valid on-device `.engine` is present | Factory TRT branch: resolve `.engine` → probe system `tensorrt` → `YoloDetectionWorker(weights=str(engine_path))` → `backend_live=tensorrt` only on that path |
| TRT-02 | Docs require **on-device** engine build; project does not ship multi-SKU prebuilt engines in the wheel | Docs honesty + keyword tests; hatch wheel already force-includes only profiles + UI static (no engines); no `.engine` in repo today |
| TRT-03 | Jetson-class packaging notes cover JetPack/system TensorRT (no generic `tensorrt` pip pin as required app dep) | Update `docs/export/jetson-packaging.md` + pyproject static assert remains “no tensorrt extra”; document system/JetPack binding path |
| TRT-04 | TRT path maps results into the same `Detection` contract; conf still adjustable at runtime when supported | Same worker `predict` + `results_to_detections`; conf via `set_conf` → `predict(conf=…)`; Ultralytics NMS postprocess applies conf for non-baked engines; mock parity proves contract without hardware |
</phase_requirements>

## Summary

Phase 8 wired the tensorrt **loader branch** as a soft-stub: `preferred_backend=tensorrt` always returns `backend_live=torch` with reason `trt_loader_not_implemented` (or `path_rejected`). Artifact resolution for `.engine` (`SENTRY_DETECTOR_ENGINE`, cache/cwd allowlist) already exists and is tested. Phase 9 flipped the ORT branch to a live Ultralytics-native path and proved Detection parity with mocks. **Phase 10 does for TensorRT what Phase 9 did for ORT**: when preferred is `tensorrt`, an allowlisted `.engine` resolves, and the system `tensorrt` Python package is importable, construct `YoloDetectionWorker(weights=<engine path>)` so Ultralytics AutoBackend loads `TensorRTBackend` (`YOLO("yolo26n.engine")` → `predict` → existing `results_to_detections`). Only then may `backend_live` be `tensorrt`.

Unlike ORT, **there is no new pip extra**. TRT-03 forbids a project `tensorrt` pin; makers use JetPack-bundled or NVIDIA system TensorRT. CI stays free of Jetson/GPU by monkeypatching resolve + dep probe and injecting `model=FakeModel` (mirror `tests/test_ort_parity.py`). Docs must stop saying TRT is “export target only” and instead state live conditions + on-device engine lifecycle + soft-fallback honesty.

**Primary recommendation:** Reuse `YoloDetectionWorker` with `weights=<resolved .engine path>`; probe `importlib.util.find_spec("tensorrt")` **before** live claim; set `backend_live="tensorrt"` only on that success path; retire `trt_loader_not_implemented` for the implemented branch; reason codes `trt_artifact_missing` | `trt_dep_missing` | `path_rejected`; docs for on-device build + JetPack/system TRT; parity tests mock-only.

### Top recommendations for planner

1. **10-01 — Live Ultralytics-native TRT worker path (system TensorRT)**  
   - Implement live TRT only in `factory.py` (spine frozen).  
   - Mirror ORT branch structure 1:1: resolve → reject / missing → dep probe → live worker.  
   - `YoloDetectionWorker(weights=str(engine_path), conf=…, device=rt.device, model=…)`.  
   - Reason vocabulary: drop default `trt_loader_not_implemented`; use `trt_artifact_missing` | `trt_dep_missing` | `path_rejected`.  
   - Factory matrix + import hygiene tests (still no top-level `import tensorrt`).  
   - Status honesty fixture for live TRT triple (mirror live ORT).  
   - **Do not** add `tensorrt` to `pyproject.toml` extras.

2. **10-02 — On-device engine lifecycle + Jetson packaging notes**  
   - Update `docs/export/jetson-packaging.md`, `yolo26-onnx-tensorrt.md`, `docs/export/README.md`, `docs/architecture.md`, `docs/configuration.md`, `jetson.yaml` comments.  
   - Live conditions: `preferred_backend=tensorrt` + allowlisted `.engine` + system `tensorrt` importable → `backend_live=tensorrt`.  
   - On-device build recipe (existing `scripts/export/export_yolo.py --format engine`) + never-copy / no-prebuilt rules.  
   - Document env `SENTRY_DETECTOR_ENGINE` / `SENTRY_ARTIFACT_ROOT`.  
   - Keyword tests in `tests/test_export_docs.py` + keep `test_no_tensorrt_optional_extra`.  
   - Conf caveat: runtime conf works via Ultralytics postprocess NMS for default (non-`nms=True` baked) engines; export script already uses `quantize=16` without embedding NMS.

3. **Honesty invariants (both plans)**  
   - `backend_live=="tensorrt"` **iff** worker weights end with `.engine` (not `.pt` under a TRT label).  
   - Factory sole author of `backend_*`; status/UI pass-through unchanged.  
   - Never import `tensorrt` at factory module top-level; never call Ultralytics `check_tensorrt()` from factory (it can auto-pip-install `tensorrt-cu*`).

4. **Do not** hand-roll TRT bindings, ship engines in the wheel, add pip `tensorrt` extra, touch DetectionLoop, or claim live TRT when artifact/deps missing.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| TRT live loader selection | API / Backend (factory at serve construct) | — | One-shot sticky resolve; never per-frame |
| `.engine` artifact resolve | API / Backend (`artifact_paths`) | Filesystem / cache | Phase 8 allowlist; env `SENTRY_DETECTOR_ENGINE` |
| Ultralytics `YOLO("*.engine")` load + predict | API / Backend (`YoloDetectionWorker`) | Ultralytics `TensorRTBackend` → system TRT + CUDA | Native path; preprocess/NMS/Results owned by Ultralytics |
| Detection wire mapping | API / Backend (`mapping.results_to_detections`) | — | Shared torch/ORT/TRT; pure transform |
| Runtime conf adjust | API / Backend (worker `set_conf`/`get_conf`) | API routes (existing) | Conf is worker state passed into `predict`; backend-agnostic when NMS is postprocess |
| `backend_live` honesty | API / Backend (factory sole author) | CLI banner + `/api/status` + Live Preview | Pass-through only (Phase 8) |
| Detection scheduling | API / Backend (DetectionLoop) | — | **Frozen** |
| FrameBus / PerceptionStore / `/v1` | API / Backend | — | **Frozen** |
| Depth / open-vocab | API / Backend | — | **Out of scope** — stay torch |
| On-device engine build | Operator / edge host (export CLI) | Docs | Offline `export_yolo.py --format engine`; not serve |
| System / JetPack TensorRT install | OS / JetPack packaging | Docs only | No app-level pip pin (TRT-03) |
| Dual-model VRAM (TRT YOLO + torch DAV2) | Docs / Phase 11 | — | Measure on device; no FPS claims this phase |

## Current Codebase State

### Factory TRT branch (soft-stub today)

[VERIFIED: `src/sentry_ai/models/detection/factory.py`]

```181:189:src/sentry_ai/models/detection/factory.py
    if requested == "tensorrt":
        _path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
        reason = reject or "trt_loader_not_implemented"
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason=reason,
        )
```

- Artifact resolve already maps `preferred=="tensorrt"` → env `SENTRY_DETECTOR_ENGINE` and suffix `.engine`.  
- Path is discarded (`_path`); live claim never happens.  
- ORT live branch (lines 144–179) is the **exact structural template** to copy.

### ORT live pattern (mirror target)

| Step | ORT (shipped Phase 9) | TRT (Phase 10) |
|------|----------------------|----------------|
| Resolve | `_try_resolve_artifact(..., "onnxruntime")` | same, `"tensorrt"` |
| Reject | `path_rejected` | same |
| Missing artifact | `ort_artifact_missing` | `trt_artifact_missing` |
| Dep probe | `_onnxruntime_available()` via `find_spec("onnxruntime")` | `_tensorrt_available()` via `find_spec("tensorrt")` |
| Live worker | `YoloDetectionWorker(weights=str(onnx_path), …)` | `weights=str(engine_path)` |
| Live claim | `backend_live="onnxruntime"` | `backend_live="tensorrt"` |
| Soft fall worker | `_torch_worker` with `.pt` | same |
| Pip extra | `onnx` extra pins CPU ORT | **None** — system TRT only |

### Worker / mapping

- `YoloDetectionWorker` is format-agnostic: `YOLO(self._weights)` + `predict(conf=…)` + `results_to_detections`. [VERIFIED: `yolo_worker.py`]  
- Conf duck-type (`get_conf` / `set_conf`) already thread-safe; no TRT-specific changes required for TRT-04 mock path.  
- Mapping module has no ultralytics import — golden fixtures reuse Phase 9 FakeModel style.

### Artifact / device policy

- Stems: `yolo26n|s|m`; suffixes: `.onnx`, `.engine`. [VERIFIED: `artifact_paths.py`]  
- `device_for_backend("tensorrt", "0")` → `"cuda:0"` (never fake `"tensorrt"` torch device). [VERIFIED: `profile_runtime.py`]  
- Jetson profile: `preferred_backend: tensorrt`, `device_id: "0"`, detector tier `n`. Comments still say export-only. [VERIFIED: `jetson.yaml`]

### Packaging / docs debt

- `pyproject.toml`: `onnx` extra present; **no** `tensorrt` extra; hatch wheel force-includes only profiles + UI static. [VERIFIED]  
- `tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra` must stay green.  
- Docs still claim TRT non-live: `yolo26-onnx-tensorrt.md`, `jetson-packaging.md`, `architecture.md`, `configuration.md`, export README.  
- Export CLI already supports `--format engine` with on-device warnings. [VERIFIED: `scripts/export/export_yolo.py`]  
- No `*.engine` files in repo. [VERIFIED: find]

### Tests that must change

| Test | Today | Phase 10 |
|------|-------|----------|
| `test_jetson_tensorrt_soft_stub` | expects `trt_loader_not_implemented` | soft-fall without fixtures → `trt_artifact_missing`; live success separate |
| `test_backend_live_not_ort_or_trt_without_fixtures` | ok | keep “without fixtures” wording |
| `test_factory_module_does_not_import_ort_trt` | forbids top-level TRT import | keep |
| `test_backend_honesty_status` TRT soft-stub fixtures | reason `trt_loader_not_implemented` | update soft-stub reason; add live TRT triple |
| New parity module | — | `tests/test_trt_parity.py` (recommended mirror of `test_ort_parity.py`) |
| `test_export_docs.py` | TRT export-only honesty | live TRT conditions + still on-device / no prebuilt |
| `test_no_tensorrt_optional_extra` | no tensorrt in extras | **must remain** |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | ≥3.11 | Runtime | [VERIFIED: pyproject.toml] |
| `ultralytics-opencv-headless` (detect extra) | ≥8.4.33,<9 (env **8.4.116**) | `YOLO("*.engine")` + AutoBackend → `TensorRTBackend` | [VERIFIED: installed package `nn/backends/tensorrt.py` + `_BACKEND_MAP["engine"]`] |
| System / JetPack `tensorrt` Python package | TRT ≥7 (Ultralytics hard check); not a project pin | Deserialize/run `.engine` | [VERIFIED: Ultralytics `TensorRTBackend.load_model` imports `tensorrt`; TRT-03 forbids pip pin] |
| CUDA-capable torch (detect/depth extras pull torch transitively via ultralytics) | existing depth/detect path | Device tensors for TRT I/O bindings | [VERIFIED: TensorRTBackend uses `torch` + forces CUDA if CPU] |
| Existing factory / artifact_paths / yolo_worker / mapping | Phase 8–9 | Selection, paths, process, Detection map | [VERIFIED: codebase] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pytest | ≥8 | Factory / parity unit tests | Existing `dev` extra |
| `importlib.util` (stdlib) | — | Probe `tensorrt` without factory-level hard import | Soft-fallback `trt_dep_missing` |
| `scripts/export/export_yolo.py` | in-repo | On-device engine build via Ultralytics `export(format="engine")` | Makers on Jetson / NVIDIA desktop |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reuse `YoloDetectionWorker` with `.engine` weights | New `TrtYoloDetectionWorker` class | Zero API difference; Ultralytics already switches backend by suffix [VERIFIED: AutoBackend] |
| Ultralytics-native path | Custom `tensorrt.Runtime` + bindings + NMS | High drift; breaks metadata/letterbox/Results; roadmap forbids |
| Soft torch fallback on miss | Hard-fail serve | Breaks jetson serve without engine; sticky policy is Phase 11 |
| Project `tensorrt` pip extra | System/JetPack only | **Forbidden** by TRT-03 / STATE; pip TRT wheels are CUDA-SKU specific and wrong for many Jetsons |
| Claim live only after first successful `process` | Claim live at factory when path+dep ok | Matches Phase 9 ORT honesty: path + dep + `.engine` weights = live intent |

**Installation (no new app deps):**

```bash
# Desktop torch primary (unchanged)
uv sync --extra dev --extra detect --extra depth

# Jetson / NVIDIA edge: detect (+ depth if dual-model); TensorRT from JetPack/system
uv sync --extra detect --extra depth
# Ensure `python -c "import tensorrt"` works via JetPack, NOT via project extra

# On-device engine build (same host that will serve)
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt --format engine --imgsz 640 --device 0

# Live serve when .engine is allowlisted (cache/cwd/env)
export SENTRY_DETECTOR_ENGINE=/path/under/allowlist/yolo26n.engine  # optional
uv run sentry serve --profile jetson --source usb --device 0
```

**Version verification (2026-08-10):**

| Package | Verified version | Source |
|---------|------------------|--------|
| ultralytics (via detect) | 8.4.116 in workspace `.venv` | [VERIFIED: `uv run` import] |
| `tensorrt` (PyPI / system) | **not installed** in research env; not a project dependency | [VERIFIED: `find_spec` None; TRT-03] |
| onnxruntime | optional `onnx` extra only (Phase 9) | unchanged |

## Package Legitimacy Audit

> Phase 10 installs **no new external packages**. Live TRT depends on system/JetPack TensorRT already present on the target device.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| *(none new)* | — | — | — | — | n/a | No install step |
| `tensorrt` / `tensorrt-cu*` | PyPI / NVIDIA | mature | high | NVIDIA | n/a | **OMITTED** from project extras (locked TRT-03) |
| `onnxruntime` | PyPI | mature | high | microsoft/onnxruntime | n/a | Unchanged Phase 9 extra — not required for TRT |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*slopcheck unavailable this session. No new pins to audit. Planner: do **not** add `tensorrt` to optional-dependencies even if Ultralytics docs suggest `pip install tensorrt-cu*`. Document system install only.*

**Pyproject hygiene to preserve:**

```toml
# Keep: no tensorrt key under [project.optional-dependencies]
# Keep tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra
```

## Architecture Patterns

### System Architecture Diagram

```
ProfileRuntime.preferred_backend == "tensorrt"
        │
        ▼
build_detection_worker(rt, conf, model=?)
        │
        ├─ resolve_detector_artifact(.engine)
        │         │
        │         ValueError ──► soft torch + path_rejected
        │         None ──► soft torch + trt_artifact_missing
        │         Path(.engine)
        │         │
        ├─ probe find_spec("tensorrt")?
        │         │
        │         no ──► soft torch + trt_dep_missing
        │         │
        │         yes
        │         ▼
        │   YoloDetectionWorker(weights=str(engine_path), conf, device=rt.device [, model])
        │   backend_requested=tensorrt
        │   backend_live=tensorrt
        │   backend_reason=None
        │
        ▼
DetectionLoop (UNCHANGED) ── worker.process(frame)
        │                         │
        │                         ▼
        │              YOLO AutoBackend format=engine → TensorRTBackend
        │              system tensorrt Runtime.deserialize_cuda_engine
        │              CUDA bindings / execute
        │              Ultralytics DetectionPredictor.postprocess (NMS + conf)
        │              Results
        │                         │
        │                         ▼
        │              results_to_detections → list[Detection]
        │              (class_name, confidence, bbox_xyxy, source=fixed)
        ▼
PerceptionStore → /v1 + Live Preview overlays
        │
        └── Status/banner: backend_requested / backend_live / backend_reason
```

### On-device engine lifecycle (docs / 10-02)

```
Maker machine (target Jetson or NVIDIA desktop)
        │
        ▼
uv sync --extra detect
        │
        ▼
export_yolo.py --weights yolo26n.pt --format engine --device 0
   (Ultralytics: ONNX intermediate → onnx2engine → yolo26n.engine)
        │
        ▼
Place engine under allowlisted root:
  - $SENTRY_MODEL_CACHE/weights/yolo26n.engine
  - cwd/yolo26n.engine
  - or SENTRY_DETECTOR_ENGINE=<allowlisted path>
        │
        ▼
sentry serve --profile jetson
        │
        └── factory live TRT if tensorrt importable
```

**Hard rules:** build on same GPU arch + TRT/JetPack; never copy across SKUs; never commit `.engine`; rebuild after JetPack upgrades.

### Recommended Project Structure

```
src/sentry_ai/models/detection/
├── factory.py          # LIVE TRT branch (primary code change)
├── yolo_worker.py      # unchanged (format-agnostic YOLO load)
├── mapping.py          # unchanged
└── loop.py             # FROZEN

src/sentry_ai/config/
├── artifact_paths.py   # already resolves .engine
├── profile_runtime.py  # already maps tensorrt → cuda device
└── profiles/jetson.yaml  # comment honesty update

docs/export/
├── jetson-packaging.md       # live TRT + JetPack/system notes (TRT-03)
├── yolo26-onnx-tensorrt.md   # live TRT conditions (TRT-01/02)
└── README.md                 # export + live matrix

scripts/export/export_yolo.py # already --format engine (docs only)

tests/
├── test_detection_factory.py     # TRT matrix (live + soft-fall)
├── test_trt_parity.py            # NEW — Detection/conf parity mocks
├── test_backend_honesty_status.py
├── test_export_docs.py
└── test_pyproject_onnx_extra.py  # keep no-tensorrt assert
```

### Pattern 1: Live TRT factory branch (mirror ORT)

**What:** Replace soft-stub with resolve + dep probe + Ultralytics-native worker.  
**When to use:** `preferred_backend` normalizes to `tensorrt`.  
**Example:**

```python
# Source: Phase 9 factory ORT branch (factory.py) — adapt for tensorrt
def _tensorrt_available() -> bool:
    """True when the system tensorrt package is importable (no hard import)."""
    return importlib.util.find_spec("tensorrt") is not None


if requested == "tensorrt":
    path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
    if reject:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason=reject,  # path_rejected
        )
    if path is None:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_artifact_missing",
        )
    if not _tensorrt_available():
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_dep_missing",
        )
    trt_worker = YoloDetectionWorker(
        weights=str(path),
        conf=conf,
        device=rt.device,  # cuda:N from device_for_backend
        model=model,
    )
    return WorkerBuild(
        worker=trt_worker,
        backend_requested="tensorrt",
        backend_live="tensorrt",
        backend_reason=None,
    )
```

### Pattern 2: Parity without Jetson (mirror ORT)

**What:** Monkeypatch resolve + dep probe; inject FakeModel; assert Detection contract.  
**When to use:** Default CI / merge gate.  
**Example:** copy `tests/test_ort_parity.py` → `tests/test_trt_parity.py` with jetson profile + `.engine` path + `_tensorrt_available`.

### Pattern 3: Docs keyword honesty

**What:** State live TRT conditions; keep on-device / never-copy / no-prebuilt; no FPS invention; no pip tensorrt requirement.  
**When to use:** All export + architecture + configuration surfaces that still say “TRT not live”.

### Anti-Patterns to Avoid

- **`backend_live="tensorrt"` with `.pt` weights:** Silent lie — assert suffix coupling.  
- **`import tensorrt` at factory top-level:** Breaks CPU-only CI import graph; use `find_spec` only.  
- **Calling Ultralytics `check_tensorrt()` from Sentry factory:** On Linux it can auto-`pip install tensorrt-cu{N}` [VERIFIED: `ultralytics.utils.checks.check_tensorrt`] — violates TRT-03 and can break Jetson.  
- **Adding `tensorrt` optional-dependency:** Forbidden by TRT-03 / existing static test.  
- **Shipping `.engine` in wheel or git:** SKU non-portable; TRT-02.  
- **Custom TRT decoder / binding code:** Out of scope; use Ultralytics.  
- **Editing DetectionLoop for backend identity:** Factory-only.  
- **Real `YOLO("*.engine")` in default pytest:** Needs CUDA + system TRT + valid engine — not available in GHA; mock only.  
- **Documenting cross-device engine copy as supported:** Explicitly forbidden.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| TRT engine load + CUDA bindings | Custom `tensorrt.Runtime` + I/O tensor setup | Ultralytics `YOLO("*.engine")` / `TensorRTBackend` | TRT 7–11 API split, metadata header, DLA, dynamic shapes already handled [VERIFIED: ultralytics 8.4.116] |
| YOLO letterbox + NMS + Results | Hand decoder from engine outputs | Worker `predict` + `results_to_detections` | Same Detection contract as torch/ORT |
| Artifact path security | Ad-hoc path join | `resolve_detector_artifact` | Allowlist stems/suffixes/roots (BACK-04) |
| Backend honesty | Recompute live from preferred in routes | Factory `WorkerBuild` pass-through | Phase 8 invariant |
| Engine build pipeline | Custom ONNX→TRT builder | `scripts/export/export_yolo.py --format engine` | Thin Ultralytics wrapper already shipped |
| TRT packaging for Jetson | Pin `tensorrt` in pyproject | JetPack system packages + docs | TRT-03; wheels are CUDA-SKU specific |

**Key insight:** Phase 10 is almost entirely a **factory branch flip + docs honesty**, not a new inference stack. The ORT phase already proved the Detection contract and test strategy; TRT reuses both.

## Common Pitfalls

### Pitfall 1: Claiming live TRT without system `tensorrt`
**What goes wrong:** Ultralytics load raises ImportError mid-loop; or auto-installs wrong pip wheel.  
**Why it happens:** Factory skips dep probe and relies on first `process`.  
**How to avoid:** `find_spec("tensorrt")` before live claim; soft-fall `trt_dep_missing`.  
**Warning signs:** `backend_live=tensorrt` on hosts where `import tensorrt` fails.

### Pitfall 2: SKU-specific engines treated as portable
**What goes wrong:** Desktop-built `.engine` fails deserialize on Jetson (or wrong JetPack).  
**Why it happens:** Operators copy files across devices.  
**How to avoid:** Docs + keyword tests: on-device only, never copy, rebuild after JetPack upgrade.  
**Warning signs:** Ultralytics log “exported with a different version than expected”.

### Pitfall 3: `trt_loader_not_implemented` left as default after live ships
**What goes wrong:** Tests and status fixtures lie; operators see “not implemented” when artifact is simply missing.  
**Why it happens:** Incomplete Phase 8→10 reason migration (same class of bug fixed for ORT).  
**How to avoid:** Retire code for implemented branch; use `trt_artifact_missing` / `trt_dep_missing`.  
**Warning signs:** Grep still finds reason on happy path tests only.

### Pitfall 4: Conf appears “not adjustable” on baked-NMS engines
**What goes wrong:** Export with `nms=True` embeds conf threshold; runtime `set_conf` less effective.  
**Why it happens:** Export args differ from Sentry default script.  
**How to avoid:** Keep export script without `nms=True`; document “when supported” (TRT-04 wording); default Ultralytics detect postprocess applies `self.args.conf` via NMS [VERIFIED: `models/yolo/detect/predict.py`].  
**Warning signs:** Maker used third-party engine with embedded NMS.

### Pitfall 5: Dual-model VRAM thrash (TRT YOLO + torch DAV2)
**What goes wrong:** Jetson OOM or thermal throttle when depth + detect both continuous.  
**Why it happens:** Shared GPU; Phase 10 does not size budgets.  
**How to avoid:** Docs honesty only this phase; Phase 11 dual-model guardrails. Prefer nano detector + OV off (already jetson profile).  
**Warning signs:** Serve starts then dies on first dual-model frame.

### Pitfall 6: CI / GHA tries real TensorRT
**What goes wrong:** Jobs fail without NVIDIA hardware.  
**Why it happens:** Integration test without skip/marker.  
**How to avoid:** Mock path only in default suite; optional marker never required for merge (EDGE-CI-02 spirit).  
**Warning signs:** pytest imports fail on `tensorrt` or CUDA.

### Pitfall 7: Ultralytics auto-pip of `tensorrt-cu*`
**What goes wrong:** Silent pip install of desktop CUDA TRT on Jetson or wrong CUDA major.  
**Why it happens:** Lazy `import tensorrt` inside Ultralytics triggers `check_tensorrt()` → `check_requirements(..., install=True)`.  
**How to avoid:** Factory dep probe + soft-fall; docs tell makers to install JetPack TRT first; never invoke `check_tensorrt` from Sentry.  
**Warning signs:** Unexpected pip network during first TRT load.

### Pitfall 8: Device policy still says “tensorrt is export only” in comments
**What goes wrong:** Operators distrust live path; docs contradict code.  
**Why it happens:** Stale `jetson.yaml` / `profile_runtime` docstrings / architecture tables.  
**How to avoid:** Update all honesty surfaces in 10-02.  
**Warning signs:** `configuration.md` still says soft torch until future TRT phase after Phase 10 ships.

## Code Examples

### Live claim honesty guard (test)

```python
# Source: mirror tests/test_ort_parity.py + test_detection_factory.py
def test_live_trt_success_with_artifact_and_dep(tmp_path, monkeypatch):
    engine = tmp_path / "yolo26n.engine"
    engine.write_bytes(b"fake-engine")
    monkeypatch.setattr(
        factory_mod, "_try_resolve_artifact",
        lambda rt, *, preferred: (engine, None),
    )
    monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: True)
    rt = profile_runtime(load_config(profile="jetson"))
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "tensorrt"
    assert build.backend_reason is None
    assert str(build.worker._weights).endswith(".engine")
    assert not str(build.worker._weights).endswith(".pt")
```

### Detection contract parity (test)

```python
# Source: tests/test_ort_parity.py pattern
dets = build.worker.process(frame)
assert dets[0].class_name == "person"
assert dets[0].confidence == pytest.approx(0.88)
assert dets[0].bbox_xyxy == (10.0, 20.0, 30.0, 40.0)
assert dets[0].source == "fixed"
build.worker.set_conf(0.5)
build.worker.process(frame)
assert model.calls[-1]["conf"] == pytest.approx(0.5)
```

### Ultralytics engine load (runtime, not CI)

```python
# Source: Ultralytics AutoBackend _BACKEND_MAP["engine"] = TensorRTBackend
# Official integration: https://docs.ultralytics.com/integrations/tensorrt/
from ultralytics import YOLO
model = YOLO("yolo26n.engine")  # requires system tensorrt + CUDA
results = model.predict(source=image_bgr, conf=0.25, device=0, verbose=False)
```

### On-device export (maker)

```bash
# Source: scripts/export/export_yolo.py + docs/export/yolo26-onnx-tensorrt.md
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format engine \
  --imgsz 640 \
  --device 0
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| TRT = export target / soft-stub only | Live Ultralytics-native `YOLO("*.engine")` when artifact + system TRT present | Phase 10 | jetson profile can be live honest |
| `trt_loader_not_implemented` default reason | `trt_artifact_missing` / `trt_dep_missing` / `path_rejected` | Phase 10 | Actionable operator signals |
| Custom TRT InferenceBackend rewrite | Factory worker weights path only | v0.2 lock | Spine stays frozen |
| Ship multi-SKU engines | On-device build only | product thesis | No wheel bloat / SKU matrix |

**Deprecated/outdated (must leave docs):**
- Absolute “live TensorRT is not claimed until a future phase” after Phase 10 ships  
- “First-class TRT InferenceBackend deferred” as if Phase 10 is not that path (clarify: factory Ultralytics path, not a separate InferenceBackend class)  
- `jetson.yaml` comments that live path is always PyTorch CUDA under tensorrt preferred

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Runtime `predict(conf=…)` adjusts threshold for default Ultralytics engines (NMS in postprocess, not baked) | TRT-04 / conf | If maker engines bake NMS with fixed conf, TRT-04 “when supported” needs stronger docs/tests caveat |
| A2 | `find_spec("tensorrt")` is a sufficient factory dep probe for JetPack Python bindings | Standard Stack | Some Jetson images may need `PYTHONPATH` / apt package for `tensorrt` to be findable — docs should mention `python -c "import tensorrt"` verify step |
| A3 | No additional CUDA probe is required at factory beyond Ultralytics/torch device resolution | Architecture | Host with tensorrt importable but no GPU may soft-claim live then fail on first load — optional factory CUDA check is discretion |
| A4 | Phase 10 soft-fall (non-sticky thrash policy) remains acceptable until Phase 11 | Deferred | Operators may restart thrash if they alternate env paths — Phase 11 owns sticky |
| A5 | Dual-model TRT+DAV2 guidance stays docs-only this phase | Pitfalls | OOM on small Jetson SKUs without Phase 11 guardrails |

**If empty table were required for verified-only claims:** remaining factual stack claims are VERIFIED/CITED; rows above are the operational assumptions needing planner/user awareness.

## Open Questions

1. **CUDA availability at factory time?**  
   - What we know: `device_for_backend` returns `cuda:0` for jetson; TensorRTBackend forces CUDA if CPU.  
   - What's unclear: Should missing CUDA yield `trt_dep_missing` (or new `trt_cuda_missing`) instead of live claim?  
   - Recommendation: Start with tensorrt `find_spec` only (mirror ORT); document CUDA requirement; optional CUDA probe is discretion if easy.

2. **Where do parity tests live?**  
   - What we know: ORT used dedicated `tests/test_trt_parity.py` analog (`test_ort_parity.py`).  
   - Recommendation: New `tests/test_trt_parity.py` for symmetry and focused `-k trt` sampling.

3. **Opt-in real engine integration test?**  
   - What we know: Phase 9 skipped real ONNX load in default CI.  
   - Recommendation: Same — no real engine in default suite; optional `@pytest.mark.export` or env-gated test later (Phase 12), not required for TRT-01..04.

4. **JetPack version matrix depth?**  
   - What we know: Docs already say “verify on device”; Ultralytics notes TRT 10.2.0 blacklist and JetPack 6 INT8 end2end issues.  
   - Recommendation: Keep “verify on device” + link Ultralytics Jetson guide; do not invent FPS or pin JetPack versions without hardware verification.

5. **Desktop NVIDIA with preferred_backend override to tensorrt?**  
   - What we know: desktop-gpu profile prefers torch; operators can override preferred_backend.  
   - Recommendation: Live path should work for any profile if preferred=tensorrt + engine + dep; docs focus on jetson but do not hard-code profile==jetson in factory.

## Environment Availability

| Dependency | Required By | Available (research host) | Version | Fallback |
|------------|------------|---------------------------|---------|----------|
| Python 3.11+ (project) | Runtime | ✓ (uv `.venv` 3.11; host 3.14 also present) | 3.11 via uv | — |
| uv | Dev/test | ✓ | 0.11.23 | — |
| pytest | Validation | ✓ | via dev extra | — |
| ultralytics (detect) | Live TRT load path | ✓ in `.venv` | 8.4.116 | — |
| System `tensorrt` Python package | Live TRT (target device) | ✗ on research Mac | — | Soft-fall `trt_dep_missing`; CI mocks |
| NVIDIA GPU / CUDA | Engine build + TRT inference | ✗ (`nvidia-smi` absent) | — | Mock-only tests; on-device maker path |
| Jetson / JetPack | TRT-03 packaging validation | ✗ | — | Docs + keyword tests only |
| Real `.engine` artifact | End-to-end hardware proof | ✗ | — | Fake bytes + FakeModel inject |

**Missing dependencies with no fallback (for real live TRT on this Mac):**
- System TensorRT + NVIDIA GPU — **not blockers for Phase 10 code/docs/tests**; blockers only for optional hardware UAT

**Missing dependencies with fallback:**
- `tensorrt` import → factory soft-fall + mock tests  
- Jetson hardware → docs keyword tests + mock factory matrix

**Step 2.6 note:** Phase is implementable on this host for code + unit tests. Real TRT inference requires maker/Jetson hardware outside default CI (aligned with EDGE-CI-02).

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (workspace collects **511** tests) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) |
| Quick run command | `uv run pytest tests/test_detection_factory.py tests/test_trt_parity.py tests/test_backend_honesty_status.py tests/test_export_docs.py tests/test_pyproject_onnx_extra.py -q` |
| Full suite command | `uv run pytest -q` |
| Lint | `uv run ruff check src tests` |
| Hardware policy | **No Jetson / no system TensorRT / no real `.engine` load / no weight download** in default CI |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| TRT-01 | Live TRT when preferred + `.engine` + dep | unit | `uv run pytest tests/test_detection_factory.py -k trt -q` | ⚠️ extend existing |
| TRT-01 | Soft-fall artifact missing | unit | same | ⚠️ rewrite soft-stub |
| TRT-01 | Soft-fall dep missing | unit | same | ❌ Wave 0 |
| TRT-01 | Soft-fall path_rejected | unit | same | ⚠️ may share ORT path_rejected pattern |
| TRT-01 | Never claim TRT with `.pt` weights | unit | same | ❌ Wave 0 |
| TRT-01 | Factory no top-level tensorrt import | unit | `test_factory_module_does_not_import_ort_trt` | ✅ keep |
| TRT-02 | On-device / never-copy / no prebuilt in docs | keyword | `uv run pytest tests/test_export_docs.py -q` | ✅ extend |
| TRT-02 | No `.engine` in wheel packaging surface | static / keyword | docs + hatch force-include review | ✅ force-include already clean |
| TRT-03 | No `tensorrt` optional extra | static | `uv run pytest tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra -q` | ✅ keep |
| TRT-03 | Jetson packaging notes system TRT / no pip pin | keyword | `tests/test_export_docs.py` jetson + yolo26 | ⚠️ extend keywords |
| TRT-04 | Detection wire contract on TRT factory path | unit | `uv run pytest tests/test_trt_parity.py -q` | ❌ Wave 0 |
| TRT-04 | `set_conf` → next predict conf | unit | same | ❌ Wave 0 |
| TRT-04 | Empty predict → `[]` | unit | same | ❌ Wave 0 |
| Honesty | Status pass-through live=tensorrt | unit | `tests/test_backend_honesty_status.py` | ⚠️ extend |
| EDGE-RT-01 | Spine frozen | ownership / no edits | do not modify loop/bus/store/v1 | ✅ process |
| Mapping golden | Unchanged Detection mapper | unit | `tests/test_detection_mapping.py` | ✅ keep |

### Reason-code contract (assertable)

| Condition | backend_requested | backend_live | backend_reason |
|-----------|-------------------|--------------|----------------|
| preferred torch | torch | torch | None |
| preferred ORT + valid path + dep (Phase 9) | onnxruntime | onnxruntime | None |
| preferred TRT + valid `.engine` + tensorrt importable | tensorrt | **tensorrt** | None |
| preferred TRT + no artifact | tensorrt | torch | `trt_artifact_missing` |
| preferred TRT + no system tensorrt | tensorrt | torch | `trt_dep_missing` |
| preferred TRT + path_rejected | tensorrt | torch | `path_rejected` |
| preferred openvino | openvino | torch | `unsupported_backend` |

**Retired:** `trt_loader_not_implemented` as the default TRT outcome (Phase 8/9). Soft-stub tests must not require it after Phase 10.

### Sampling Rate

- **Per task commit:** quick command above (factory + trt parity + docs + no-tensorrt extra)  
- **Per wave merge:** `uv run pytest -q` + `uv run ruff check src tests`  
- **Phase gate:** TRT-01..04 rows green; full suite green; no Jetson/TRT GPU required before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Extend `tests/test_detection_factory.py` — live TRT success; `trt_artifact_missing`; `trt_dep_missing`; path_rejected; weights suffix honesty; rewrite `test_jetson_tensorrt_soft_stub`
- [ ] Add `tests/test_trt_parity.py` — Detection contract, set_conf, empty list, live weights guard (mirror ORT)
- [ ] Extend `tests/test_backend_honesty_status.py` — live TRT triple + update soft-stub reason fixtures
- [ ] Extend `tests/test_export_docs.py` — live TRT conditions + system TensorRT / no pip pin + keep on-device rules
- [ ] Keep `tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra`
- [ ] Ensure default suite does **not** call real `YOLO("*.engine")` load

### Roadmap success criteria → automated proof

| Roadmap success item | Automated proof |
|----------------------|-----------------|
| Live TRT when preferred + valid `.engine` + system TRT | Factory unit: live=tensorrt + weights `.engine` |
| Docs require on-device; no multi-SKU engines in wheel | Keyword tests + packaging hygiene |
| Jetson packaging: JetPack/system TRT; no pip pin | jetson-packaging keywords + pyproject no-tensorrt test |
| Same Detection contract; conf adjustable when supported | `test_trt_parity` process + set_conf |

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Local perception service; no new auth |
| V3 Session Management | no | — |
| V4 Access Control | partial | Existing localhost default bind; no TRT-specific change |
| V5 Input Validation | yes | Artifact allowlist (stem/suffix/root); conf range [0,1] |
| V6 Cryptography | no | — |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Path traversal via `SENTRY_DETECTOR_ENGINE` | Tampering | `resolve_detector_artifact` allowlist (BACK-04) |
| Malicious/corrupt `.engine` load | Tampering / DoS | Allowlisted stems only; load errors → loop sticky pause (existing); do not auto-download engines |
| Silent backend lie (torch under TRT label) | Spoofing | Factory sole author; suffix ↔ live coupling tests |
| Supply-chain pip install of TRT mid-serve | Tampering | No project tensorrt dep; factory never calls `check_tensorrt`; docs forbid relying on Ultralytics auto-pip |
| Unauthenticated LAN camera exposure | Information disclosure | Existing safety docs; default bind 127.0.0.1 (unchanged) |

## Project Constraints (from CLAUDE.md / project skills)

- No project-root `CLAUDE.md` / `AGENTS.md` found in workspace; user-level graphify skill is unrelated to this phase.  
- Honor existing Sentry conventions from shipped phases: factory honesty, spine freeze, mock-first CI, AGPL YOLO lineage via `THIRD_PARTY_MODELS.md`, no invented FPS.

## Sources

### Primary (HIGH confidence)
- [VERIFIED: codebase] `src/sentry_ai/models/detection/factory.py` — ORT live + TRT soft-stub  
- [VERIFIED: codebase] `yolo_worker.py`, `mapping.py`, `artifact_paths.py`, `profile_runtime.py`, `jetson.yaml`  
- [VERIFIED: ultralytics 8.4.116] `nn/backends/tensorrt.py`, `nn/autobackend.py` (`_BACKEND_MAP["engine"]`), `utils/checks.py` (`check_tensorrt` auto-install behavior), `models/yolo/detect/predict.py` (conf via NMS)  
- [VERIFIED: pyproject.toml] extras, hatch force-include, pytest config  
- [VERIFIED: tests] `test_detection_factory.py`, `test_ort_parity.py`, `test_export_docs.py`, `test_pyproject_onnx_extra.py`  
- [VERIFIED: docs] `docs/export/*`, `docs/architecture.md`, `docs/configuration.md`  
- [CITED: docs.ultralytics.com/integrations/tensorrt/] TensorRT export/integration (page shell fetched; code path verified in installed package)

### Secondary (MEDIUM confidence)
- [CITED: Ultralytics exporter] engine export path ONNX→`onnx2engine`; JetPack 6 INT8 end2end notes in exporter warnings  
- Phase 9 RESEARCH/PATTERNS/SUMMARIES as process analogs

### Tertiary (LOW confidence)
- Exact JetPack package names / apt packages for `python3-libnvinfer` across SKUs — **verify on device** (docs should not invent package pins) [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — Ultralytics engine backend verified in installed package; no new pins  
- Architecture: **HIGH** — Phase 9 ORT is near-isomorphic template; factory/artifact/device already wired  
- Pitfalls: **HIGH** for software pitfalls; **MEDIUM** for Jetson hardware/SKU matrix (no device this session)  
- Conf-at-runtime on all engine variants: **MEDIUM** — default path verified; baked-NMS engines [ASSUMED] caveat  

**Research date:** 2026-08-10  
**Valid until:** ~30 days for factory patterns; re-check Ultralytics TensorRT notes if upgrading detect extra major

## Recommended Plan Split (for planner)

### 10-01: Live Ultralytics-native TRT worker path (system TensorRT)
- Factory live branch + reason codes  
- Factory matrix tests + import hygiene  
- TRT parity module + status honesty live triple  
- Minimal docstring updates in factory module  

### 10-02: On-device engine lifecycle + Jetson packaging notes
- Docs: jetson-packaging, yolo26-onnx-tensorrt, export README, architecture, configuration, jetson.yaml  
- Keyword tests for live TRT + system TRT + no pip pin  
- Preserve no-tensorrt extra static test  
- Serve recipe: export → place engine → `sentry serve --profile jetson`

---

## RESEARCH COMPLETE

**Phase:** 10 - live-tensorrt-fixed-class-yolo  
**Confidence:** HIGH  

### Key Findings
- TRT factory soft-stub is a one-branch rewrite mirroring Phase 9 ORT; artifact resolve + device policy already exist.  
- Live path = `YoloDetectionWorker(weights=*.engine)` + system `tensorrt` via `find_spec` — **no** pip extra, **no** custom TRT decoder.  
- Ultralytics `TensorRTBackend` requires importable `tensorrt` and CUDA; conf applies in detect postprocess NMS for default exports.  
- CI strategy: mock resolve/dep + FakeModel only (same as ORT); never real engine in GHA.  
- Docs currently claim TRT non-live — 10-02 must flip honesty while keeping on-device / no multi-SKU / no pip pin rules.

### File Created
`.planning/phases/10-live-tensorrt-fixed-class-yolo/10-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | Ultralytics 8.4.116 engine backend + project pins verified |
| Architecture | HIGH | ORT isomorphism + existing factory/artifact wiring |
| Pitfalls | HIGH/MED | Software pitfalls verified; Jetson SKU matrix not hardware-tested |

### Open Questions
- Optional factory CUDA probe vs tensorrt-only dep probe  
- JetPack apt package naming left as “verify on device”  
- Whether to add opt-in real-engine marker (recommend no for Phase 10)

### Ready for Planning
Research complete. Planner can now create PLAN.md files for 10-01 and 10-02.
