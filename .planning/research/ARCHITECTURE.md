# Architecture: Live ORT / TRT into Existing Sentry Spine

**Domain:** Edge runtime plug-in for fixed-class detection (v0.2)  
**Project:** Sentry AI  
**Researched:** 2026-08-09  
**Overall confidence:** HIGH for plug-in boundary (code-verified); MEDIUM for native TRT binding shape on Jetson SKUs  

## Executive answer

| Question | Answer |
|----------|--------|
| **ORT/TRT without rewrite?** | Yes. Plug in at **worker construction** (`cli.serve` + factory). The hot-path spine already treats the detector as a duck-typed `ModelWorker`. |
| **New modules?** | Yes — small: worker factory, artifact path resolution, optional `InferenceBackend` adapters, shared YOLO postprocess if native ORT/TRT. |
| **DetectionLoop unchanged?** | **Yes. Do not touch it.** It already only calls `worker.process(frame)` + optional `get_conf` / `name`. |
| **Engine path config?** | Extend profile / env resolution: explicit path → cache-derived `.engine`/`.onnx` from detector tier → honest fallback. |
| **Fallback chain?** | Prefer configured backend artifact; on missing artifact or runtime → log clearly → torch `.pt` (or CPU) when `fallback_to_torch` is on; never silent “tensorrt” while running PyTorch. |

**Do not rewrite:** `FrameBus`, `DetectionLoop`, `PerceptionStore`, `assemble_perception_frame`, `/v1`, Live Preview overlays, free-space / depth loops.

**Rewrite surface for v0.2:** serve-time factory + profile honesty + artifact paths + (optional) backend packages. Depth and YOLOE stay PyTorch this milestone.

---

## Current spine (code truth)

Verified from `cli.serve`, detection loop, YOLO worker, profile runtime, backend stubs:

```
CameraSource
    │
    ▼
CaptureLoop ──publish──► FrameBus (depth-1, keep-latest)
                              │
                              ├──► DetectionLoop ──► worker.process(frame)
                              │         │                 │
                              │         │                 ▼
                              │         │          list[Detection]
                              │         ▼
                              │    PerceptionStore.set_detections(...)
                              │
                              ├──► DepthLoop → DepthAnythingWorker (PyTorch/HF)  [unchanged]
                              └──► OpenVocabLoop → YoloeOpenVocabWorker (PyTorch) [unchanged]
                                        │
                                        ▼
                               FreeSpaceLoop (store depth only)
                                        │
                                        ▼
                         assemble_perception_frame → /v1 + Live Preview
```

### Contracts that already enable plug-in

| Layer | Contract | Backend-aware? |
|-------|----------|----------------|
| `DetectionLoop` | `worker.process(frame) → list[Detection]`; optional `get_conf()`, `name` | **No** — backend-agnostic |
| API conf | duck-typed `set_conf` / `get_conf` on `app.state.detection_worker` | **No** |
| `ModelWorker` Protocol | `name` + `process` | **No** |
| `InferenceBackend` Protocol | `load` / `infer` / `close` + `name: BackendName` | **Yes, but unused by YOLO today** |
| `profile_runtime` | tiers + `preferred_backend` + live `device` string | Policy only (v1 honesty) |
| `YoloDetectionWorker` | Ultralytics `YOLO(weights).predict(...)` | Torch `.pt` path only in practice |

**Key property:** `DetectionLoop` never imports Ultralytics, never reads `preferred_backend`, never opens cameras. Any object with `process` + conf duck-typing is a valid detector.

### What “honest not live” means today

```text
jetson profile:     preferred_backend=tensorrt  → device_for_backend → "cuda:0"
                    serve still constructs YoloDetectionWorker(weights="yolo26n.pt")
                    banner: "live path is still PyTorch CUDA"

cpu-fallback:       preferred_backend=onnxruntime → device="cpu"
                    still YoloDetectionWorker(.pt on CPU)
                    banner: "ORT is the export target"
```

v0.2 goal: make `preferred_backend` select a **real live loader**, with explicit fallback language when artifacts/runtimes are missing.

---

## Recommended architecture (opinionated)

### Design thesis

Use **Isaac-style encode → infer → decode** at the *worker interior*, but keep the **loop boundary** as “ModelWorker only.”  
Do **not** push ORT/TRT into `DetectionLoop`, `PerceptionStore`, or `/v1`.

```
┌──────────────────────────────── spine (frozen) ─────────────────────────────────┐
│  FrameBus → DetectionLoop → PerceptionStore → assemble /v1 / preview            │
└──────────────────────────────────────▲──────────────────────────────────────────┘
                                       │ list[Detection]
┌──────────────────────────────────────┴──────────────────────────────────────────┐
│  Fixed-class ModelWorker (swap implementations)                                 │
│    • YoloDetectionWorker          (torch / .pt)           — keep                │
│    • OrtYoloDetectionWorker       (onnxruntime / .onnx)   — new                 │
│    • TrtYoloDetectionWorker       (TensorRT / .engine)    — new                 │
│    (or one EdgeYoloDetectionWorker parameterized by InferenceBackend)           │
└──────────────────────────────────────▲──────────────────────────────────────────┘
                                       │ optional tensor I/O
┌──────────────────────────────────────┴──────────────────────────────────────────┐
│  InferenceBackend                                                               │
│    • NullBackend (tests)                                                        │
│    • OrtBackend  — onnxruntime.InferenceSession                                 │
│    • TrtBackend  — system TensorRT engine (no pip tensorrt extra)               │
│    • (Torch remains inside YoloDetectionWorker via Ultralytics; no need for     │
│       TorchBackend unless you want symmetry later)                              │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### DetectionLoop: unchanged

`DetectionLoop` already:

1. Polls `FrameBus.get_latest()`
2. Skips same `frame_id`
3. Calls `worker.process(frame)`
4. Writes `PerceptionStore.set_detections(...)` with latency / conf / model_name / error
5. Survives worker exceptions (empty dets + `error` string)

**No loop changes required** for ORT/TRT. Do not add backend switches inside the loop.

### Serve construction: the only wiring change

Today (`cli.serve`):

```python
worker = YoloDetectionWorker(
    weights=rt.detector_weights,
    conf=0.25,
    device=rt.device,
)
det_loop = DetectionLoop(bus, worker, store)
```

Target:

```python
worker = build_detection_worker(rt, conf=0.25)  # NEW factory
det_loop = DetectionLoop(bus, worker, store)    # UNCHANGED
```

Open-vocab and depth workers stay as-is (PyTorch) for this milestone.

---

## New modules (minimal set)

### Must-add

| Module | Responsibility |
|--------|----------------|
| `sentry_ai.models.detection.factory` | `build_detection_worker(rt, *, conf, …) → ModelWorker` |
| `sentry_ai.config.artifact_paths` (or extend `profile_runtime`) | Resolve `.pt` / `.onnx` / `.engine` paths from tier + config + env + cache |
| `sentry_ai.backend.onnx_runtime` | `OrtBackend` implementing `InferenceBackend` |
| `sentry_ai.backend.tensorrt` | `TrtBackend` implementing `InferenceBackend` (system TRT only) |

### Should-add (shared edge worker)

| Module | Responsibility |
|--------|----------------|
| `sentry_ai.models.detection.edge_worker` | One `EdgeYoloDetectionWorker` that owns conf, letterbox, conf filter, and calls `backend.infer` |
| `sentry_ai.models.detection.postprocess` | Raw model outputs → `list[Detection]` (class names from COCO map / metadata sidecar) |

### Keep as-is

| Module | Why |
|--------|-----|
| `models/detection/loop.py` | Backend-agnostic |
| `models/detection/yolo_worker.py` | Default desktop torch path |
| `models/detection/mapping.py` | Ultralytics Results → Detection (torch path) |
| `backend/protocols.py` | Protocol already exists; extend helpers only |
| `backend/null.py` | CI / smoke |
| `state/perception_store.py`, `api/assemble.py` | Product merge unchanged |

### Optional plugin entry points

```toml
# pyproject.toml — additive only
[project.entry-points."sentry_ai.workers"]
yolo-fixed = "…:YoloDetectionWorker"           # existing
yolo-fixed-ort = "…:OrtYoloDetectionWorker"    # optional
yolo-fixed-trt = "…:TrtYoloDetectionWorker"    # optional
```

Serve should **not** require entry-point discovery for the default path; factory is enough. Entry points help external packs later.

---

## Worker shapes

### Shared duck-type contract (API + loop)

Every fixed-class detector used by serve **must** expose:

```python
name: str                          # e.g. "yolo-fixed", "yolo-fixed-ort", "yolo-fixed-trt"
def process(frame) -> list[Detection]
def get_conf() -> float
def set_conf(conf: float) -> None  # routes_detection + preview
```

Optional (already duck-typed in routes): `weights` / `_weights`, `device` for `/api/detection/config`.

### Option A — three workers (clear, recommended for v0.2)

```text
YoloDetectionWorker     # Ultralytics + .pt     (desktop default)
OrtYoloDetectionWorker  # ORT session + .onnx
TrtYoloDetectionWorker  # TRT engine + .engine
```

**Pros:** explicit imports/extras; easy CI mocks per class.  
**Cons:** some conf/preprocess duplication unless shared base/mixin.

### Option B — one edge worker + InferenceBackend (cleaner long-term)

```text
EdgeYoloDetectionWorker(backend: InferenceBackend, meta: YoloMeta)
  process:
    tensor = preprocess(frame.image_bgr, meta.imgsz)
    raw = backend.infer(tensor)
    return postprocess(raw, meta, conf=self.get_conf())
```

**Pros:** matches existing `InferenceBackend` Protocol; swaps ORT↔TRT without new worker types.  
**Cons:** need solid preprocess/postprocess for YOLO26 (NMS-free helps).

**Opinionated choice:** **Option B interior + thin factory aliases.**  
Ship `EdgeYoloDetectionWorker` + `OrtBackend` / `TrtBackend`. Factory returns either `YoloDetectionWorker` (torch) or `EdgeYoloDetectionWorker` (ort/trt). Avoid three full copies of conf locking.

### Ultralytics-as-ORT/TRT loader (anti-pattern for “first-class,” OK as spike)

`YOLO("yolo26n.onnx")` / `YOLO("yolo26n.engine")` can run exported graphs via Ultralytics.  
**Do not** treat that as the final architecture: it still couples edge to the detect extra, muddies honesty logs, and leaves `InferenceBackend` dead. Use only as a **spike** to validate export artifacts before native backends.

---

## Engine / ONNX path config

### Resolution order (detector artifacts)

For a resolved `ProfileRuntime` with `detector_weights` stem (e.g. `yolo26n` from tier `n`):

```text
1. Explicit config / CLI / env
     models.detector_engine  |  SENTRY_DETECTOR_ENGINE
     models.detector_onnx    |  SENTRY_DETECTOR_ONNX
2. Sentry cache weights dir (configure_model_cache)
     {weights_dir}/{stem}.engine
     {weights_dir}/{stem}.onnx
3. CWD / allowlisted basenames (makers who exported next to project)
     ./{stem}.engine | ./{stem}.onnx
4. Miss → fallback policy (below), never invent a path
```

### Suggested config extensions

Keep `DeviceConfig.preferred_backend` as the **selector**. Add optional artifact fields (do not overload `device_id` with paths):

```yaml
# jetson.yaml (target shape)
profile: jetson
device:
  preferred_backend: tensorrt
  device_id: "0"
models:
  detector_tier: n          # → yolo26n stem
  # optional overrides:
  # detector_engine: /opt/sentry/engines/yolo26n.engine
  # detector_onnx: null
  # fallback_to_torch: true   # default true for maker UX
```

`ProfileRuntime` gains (illustrative):

```python
@dataclass(frozen=True)
class ProfileRuntime:
    # existing fields...
    preferred_backend: str
    device: str | None
    device_id: str
    detector_weights: str          # .pt basename (torch / fallback)
    detector_onnx_path: Path | None
    detector_engine_path: Path | None
    fallback_to_torch: bool = True
    live_backend: str              # resolved AFTER probe+artifact check
```

**`live_backend` vs `preferred_backend`:**  
- `preferred_backend` = operator intent (profile)  
- `live_backend` = what serve actually loaded (`tensorrt` | `onnxruntime` | `torch`)  
Banner and `/api` status should print **both** when they differ.

### Cache layout (align with export recipes)

```text
~/.cache/sentry-ai/          # or $SENTRY_MODEL_CACHE
  weights/
    yolo26n.pt               # Ultralytics / torch
    yolo26n.onnx             # export recipe output
    yolo26n.engine           # on-device TRT build (never ship in wheel/git)
  hf/                        # depth (unchanged)
```

Export remains offline: `scripts/export/export_yolo.py --format onnx|engine`.  
Serve **never** runs `model.export` on the hot path.

### TensorRT path rules (non-negotiable)

| Rule | Why |
|------|-----|
| Build `.engine` **on target device** | GPU arch + JetPack/TRT bind |
| No prebuilt multi-SKU engines in repo/wheel | Not portable |
| No `tensorrt` pip extra in core product | System / JetPack TRT only |
| Missing engine → honest log + fallback | Never silent torch under `tensorrt` label |

---

## Fallback chain

### Policy (maker-friendly default)

```text
preferred = tensorrt
  try load engine at resolved path + TrtBackend
  if engine missing OR TRT runtime unavailable:
    log ERROR/WARN with path + reason
    if fallback_to_torch:
      live_backend = torch (CUDA if available else CPU)
      load .pt via YoloDetectionWorker
    else:
      fail serve (exit non-zero) OR start with detection disabled
      (prefer fail-closed when fallback_to_torch=false)

preferred = onnxruntime
  try load .onnx + OrtBackend (CPU EP default; CUDA EP if available and desired)
  if onnx missing OR onnxruntime not installed:
    log + fallback_to_torch → YoloDetectionWorker(.pt, device=cpu or auto)

preferred = torch | cpu
  YoloDetectionWorker(.pt) only — current path
  (cpu forces device=cpu)
```

### Strict vs soft modes

| Mode | Config | Behavior |
|------|--------|----------|
| **Soft (default)** | `fallback_to_torch: true` | Always get a detector if detect extra + `.pt` exist |
| **Strict edge** | `fallback_to_torch: false` | Serve refuses to claim jetson/TRT success without engine |

### Honesty requirements

| Bad (v1 residual) | Good (v0.2) |
|-------------------|-------------|
| `preferred_backend: tensorrt` banner while loading `.pt` without saying fallback | `preferred=tensorrt live=torch reason=engine_missing:/path` |
| Silent ORT claim on CPU torch | `preferred=onnxruntime live=torch reason=onnx_not_found` |
| Device string `"tensorrt"` passed to Ultralytics | Never — torch devices stay `cuda:N`/`cpu`/`mps` |

### Probe vs load

- `probe_device` stays **advisory** (never hard-fails serve alone).
- **Artifact existence + backend import** decide `live_backend` at worker build time.
- Extend probe later: `onnxruntime` importable; TRT builder/runtime present — still advisory.

---

## Data flow (edge detection only)

```
ImageFrame {frame_id, camera_id, image_bgr, meta.t_capture}
        │
        ▼
EdgeYoloDetectionWorker.process
        │
        ├─ conf = get_conf()          # thread-safe, API-writable
        ├─ preprocess:
        │     BGR→RGB, letterbox imgsz (default 640), normalize, NCHW float
        ├─ backend.infer(tensor)      # OrtBackend | TrtBackend
        ├─ postprocess:
        │     decode YOLO26 head → xyxy, cls, score
        │     filter score >= conf
        │     map cls → class_name (COCO names table / sidecar)
        └─ return list[Detection]
                │
                ▼
DetectionLoop → PerceptionStore.set_detections(...)   # unchanged
                │
                ▼
assemble_perception_frame → /v1/snapshot|stream + overlays
```

Torch path stays:

```
YoloDetectionWorker.process → ultralytics.predict → results_to_detections
```

Same `Detection` schema either way — **no API schema change**.

---

## Component boundaries after plug-in

| Component | Owns | Does not own |
|-----------|------|--------------|
| `build_detection_worker` | Backend selection, artifact resolve, fallback decision | Frame timing, store merge |
| `YoloDetectionWorker` | Torch/Ultralytics `.pt` | ORT session, TRT engine |
| `EdgeYoloDetectionWorker` | Conf, preprocess, postprocess, backend lifecycle | Capture, free-space |
| `OrtBackend` / `TrtBackend` | Session/engine load + raw `infer` | BGR letterbox, Detection schema |
| `DetectionLoop` | Bus poll, latency, store write, enable flag | Which backend |
| `profile_runtime` | Intent + path candidates + device policy | Actually loading engines |
| Export scripts | Produce `.onnx`/`.engine` offline | Runtime serve |

---

## Extras / packaging

| Extra | Role |
|-------|------|
| `detect` | Ultralytics — torch path + export tooling (existing) |
| `ort` (new) | `onnxruntime` (CPU wheel for CI/desktop CPU); document GPU/Jetson Zoo separately |
| *(no)* `tensorrt` pip extra | System TensorRT / JetPack only |
| `depth` | Unchanged; stays HF/torch |

Serve behavior when extras missing:

- No `detect` and no edge backend → detection disabled (current ImportError path).
- `preferred=onnxruntime` without `ort` extra → honesty log + torch fallback if detect present.
- `preferred=tensorrt` without system TRT → same.

---

## Patterns to follow

### Pattern 1: Loop stable, worker swappable

**What:** All backend diversity lives under `process()`.  
**When:** Always for detection, depth, open-vocab.  
**Why:** Proven by current `DetectionLoop` + injectable `model=` tests.

### Pattern 2: Encode → infer → decode

**What:** Keep letterbox/normalize and box decode out of `InferenceBackend`.  
**When:** ORT and TRT workers.  
**Why:** Backend swap without rewriting bbox math (Isaac ROS DNN pattern).

### Pattern 3: Preferred vs live backend

**What:** Two fields in runtime status.  
**When:** Any fallback can fire.  
**Why:** Fixes v1 honesty debt without blocking maker UX.

### Pattern 4: On-device engine build

**What:** Document + scripts only; serve loads prebuilt path.  
**When:** Jetson / NVIDIA edge.  
**Why:** Engines are arch+TRT specific (existing export docs).

### Pattern 5: CI without hardware

**What:** Mock `InferenceBackend.infer` to return canned tensors; never require Jetson in GHA.  
**When:** unit tests for factory, fallback, postprocess.  
**Why:** PROJECT.md CI constraint.

---

## Anti-patterns to avoid

| Anti-pattern | Why bad | Instead |
|--------------|---------|---------|
| `if backend == tensorrt` inside `DetectionLoop` | Couples scheduling to vendor; untestable | Factory at serve |
| Silent torch under tensorrt profile | Breaks operator trust | `live_backend` + reason |
| Shipping `.engine` in git/wheel | Wrong SKU crashes / silent wrong results | On-device build + path config |
| `pip install tensorrt` as required extra | Jetson/desktop TRT mismatch hell | System TRT |
| Rewriting `results_to_detections` for ORT only | Dual decode paths drift | Shared postprocess **or** keep Ultralytics Results adapter only for torch |
| Live export on first frame | Multi-minute stall, non-deterministic serve | Offline export recipes |
| ORT/TRT for depth + YOLOE in same milestone | Scope explosion | Fixed-class YOLO only |
| Passing device=`"tensorrt"` to Ultralytics | Invalid torch device | Separate backends |

---

## What stays frozen (checklist)

- [x] `FrameBus` keep-latest semantics  
- [x] `DetectionLoop` thread model / enable gate / error → store  
- [x] `PerceptionStore` product slots and writers  
- [x] `assemble_perception_frame` / `/v1` schema  
- [x] Live Preview reads store only  
- [x] Depth = PyTorch/HF DAV2 Small  
- [x] Open-vocab = PyTorch YOLOE, default off  
- [x] Free-space from depth product only  
- [x] Perception-only boundary (no control)  
- [x] Localhost default bind  

## What changes (checklist)

- [ ] `build_detection_worker` factory used by `cli.serve`  
- [ ] Artifact path resolution for `.onnx` / `.engine`  
- [ ] `OrtBackend` + `TrtBackend` (+ tests with mocks)  
- [ ] Edge worker implementing conf + `process`  
- [ ] `preferred_backend` → real load attempt  
- [ ] Fallback chain + `live_backend` banner  
- [ ] Docs: serve with jetson/cpu-fallback after on-device export  
- [ ] Optional `ort` extra; still no `tensorrt` pip extra  

---

## Suggested implementation order (for roadmap phases)

1. **Factory + path resolution + honesty fields** (still can return only `YoloDetectionWorker`, but structure is right)  
2. **ORT live path** (CPU EP; mockable; cpu-fallback profile)  
3. **TRT live path** (desktop/Jetson; system libs; engine path)  
4. **Strict fallback mode + status API fields**  
5. **Docs / packaging notes** (Jetson on-device engine → serve)  

Dependencies: (2) before claiming cpu-fallback is “live ORT”; (3) before claiming jetson is “live TRT.” DetectionLoop never appears in this list.

---

## Scalability / concurrency notes

| Concern | Guidance |
|---------|----------|
| GPU sharing with depth | Keep single-process; DetectionLoop + DepthLoop already alternate on bus; TRT engine + torch depth both use CUDA — measure VRAM; serialize if needed later, not in loop rewrite |
| Thread safety | Conf locks stay on worker; backend `infer` called only from DetectionLoop thread (one outstanding job) |
| Warm-up | Load + dummy infer in worker `_ensure_*` (mirror YOLO warm-up) so first real frame is not cold |
| imgsz | Export imgsz must match runtime preprocess (default 640); mismatch = silent wrong boxes |

---

## Confidence assessment

| Area | Level | Notes |
|------|-------|-------|
| DetectionLoop stability / duck typing | **HIGH** | Verified in `loop.py`, `routes_detection.py`, tests |
| Factory-at-serve plug-in | **HIGH** | Single construction site in `cli.serve` |
| InferenceBackend as ORT/TRT home | **HIGH** | Protocol exists; unused by YOLO today — intentional extension point |
| Native YOLO26 postprocess effort | **MEDIUM** | NMS-free helps; need validated decode against Ultralytics export |
| Jetson system TRT binding details | **MEDIUM** | SKU/JetPack specific; follow existing export docs + measure on device |
| Ultralytics YOLO(onnx/engine) as production path | **LOW** as final design | Fine as spike only |

---

## Gaps / phase-specific research later

- Exact YOLO26 ONNX I/O tensor names and decode layout after Ultralytics export (spike with one exported `yolo26n.onnx`).
- Whether `onnxruntime-gpu` on desktop vs Jetson Zoo ORT should be separate install docs only (likely yes).
- Status schema: expose `live_backend` / `fallback_reason` on `/api/status` or `/v1` stats (API additive).
- Multi-engine warm-up memory budget when depth torch + TRT det coexist on Orin Nano class.

---

## Sources (code + docs)

| Source | Informs | Confidence |
|--------|---------|------------|
| `src/sentry_ai/models/detection/loop.py` | Loop is backend-agnostic | HIGH |
| `src/sentry_ai/models/detection/yolo_worker.py` | Torch path + conf contract | HIGH |
| `src/sentry_ai/cli.py` (`serve`) | Single wiring site + honesty logs | HIGH |
| `src/sentry_ai/config/profile_runtime.py` | preferred_backend → device policy today | HIGH |
| `src/sentry_ai/backend/protocols.py` | InferenceBackend / probe_device | HIGH |
| `src/sentry_ai/plugins/protocols.py` | ModelWorker Protocol | HIGH |
| `docs/export/yolo26-onnx-tensorrt.md` | On-device engine rules; deferred live backends | HIGH |
| `docs/architecture.md` | Shipped spine diagram | HIGH |
| `.planning/PROJECT.md` (v0.2 Edge Runtime) | Milestone scope: fixed-class ORT/TRT only | HIGH |
| Isaac ROS DNN encode/infer/decode | Backend split pattern | HIGH (pattern) |

---

*Architecture research for Sentry AI v0.2 Edge Runtime. Plug ORT/TRT under ModelWorker; leave DetectionLoop and PerceptionStore alone; make preferred vs live backend honest.*
