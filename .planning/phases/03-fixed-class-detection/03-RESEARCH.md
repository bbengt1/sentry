# Phase 3: Fixed-Class Detection - Research

**Researched:** 2026-08-07  
**Domain:** Local fixed-class object detection (YOLO26 / Ultralytics), detection worker + FrameBus, UI/API parity overlays  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Fixed-class first: **YOLO26** via Ultralytics (n edge / s desktop); YOLO11 fallback only if needed
- Local OSS only; no cloud required after cache (MODEL-01 already, MODEL-02 this phase)
- UI and API share one truth (no dual detection paths)
- Workers never open cameras; read from FrameBus / ImageFrame
- Ultralytics AGPL: document in THIRD_PARTY_MODELS; default weight choice still YOLO for maker OSS path with AGPL disclosure
- Perception-only: no motor/control fields

### From Phase 1–2 shipped code (must respect)
- `ModelWorker` protocol: `process(frame) -> ...`
- `Detection` schema exists with `class_name`, `confidence`, `bbox_xyxy`
- `PerceptionFrame` + `Completeness.detections`
- `FrameBus` + `CaptureLoop` + FastAPI MJPEG/status at localhost
- `InferenceBackend` Protocol + NullBackend stubs
- Live Preview static HTML + MJPEG

### Claude's Discretion
- Detection worker thread vs sync on capture path
- Overlay: draw on JPEG in MJPEG path vs canvas JS boxes from JSON
- Exact API paths for snapshot (`/api/snapshot` vs `/v1/snapshot`)
- Model weight default (`yolo26n` vs `yolo26s`)
- Whether to add `supervision` for drawing or use OpenCV only

### Deferred Ideas (OUT OF SCOPE)
- Depth, free-space, open-vocab, full control plane, edge TRT → later phases
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DET-01 | Fixed-class object detector runs locally (YOLO26 or equivalent OSS) on the live camera stream | `YoloDetectionWorker` + `DetectionLoop` thread reads `FrameBus.get_latest()`; `ultralytics-opencv-headless` + `YOLO("yolo26n.pt")` on numpy BGR |
| DET-02 | Detections include class, confidence, and bounding box in image coordinates | Map `result.boxes.xyxy/conf/cls` + `result.names` → `Detection(class_name, confidence, bbox_xyxy)` |
| DET-03 | Confidence threshold adjustable at runtime without restart | Thread-safe `conf` on worker; `predict(..., conf=self.conf)`; `PATCH /api/detection/config` |
| DET-04 | Detections on dashboard overlay and perception stream (same truth) | Single `PerceptionStore` latest detections; MJPEG draws from store; snapshot JSON returns same list |
| MODEL-02 | Models cacheable for offline use after first download | Project-local `weights_dir` via Ultralytics `settings` + `YOLO_CONFIG_DIR`; document offline re-run |
</phase_requirements>

## Summary

Phase 3 adds the first robot-usable AI signal: a **local YOLO26 fixed-class detector** consuming the Phase 2 FrameBus, publishing structured `Detection`s into a keep-latest **perception store**, and exposing them with **UI/API parity** (server-drawn overlays + JSON snapshot). Capture stays isolated: workers never open cameras. Inference runs on a **dedicated detection thread** with keep-latest drop (skip frame if busy), so slow CPU inference cannot stall capture or the FastAPI event loop.

Use **Ultralytics 8.4.x** with the **headless** package (`ultralytics-opencv-headless`) so OpenCV stays headless and does not conflict with `opencv-python-headless`. Weights `yolo26n.pt` / `yolo26s.pt` download once from GitHub assets (`ultralytics/assets` release `v8.4.0`) into a Sentry-controlled cache directory; subsequent runs are offline. Default conf is **0.25** (Ultralytics predict default); runtime PATCH updates the worker without restart. AGPL obligations for Ultralytics must be documented in `THIRD_PARTY_MODELS.md` (already stubbed).

**Primary recommendation:** Implement `YoloDetectionWorker` (`ModelWorker`) + `DetectionLoop` thread + `PerceptionStore` (latest detections / partial `PerceptionFrame`); draw boxes server-side into MJPEG; expose `GET /api/snapshot` + `PATCH /api/detection/config`; optional-extra install for ML deps; unit tests mock YOLO (no GPU, no weight download in CI).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| YOLO load + inference | API / Backend (detection thread) | — | Blocking torch; never in request handlers or capture thread |
| FrameBus read (keep-latest) | API / Backend | — | Workers subscribe; sources already publish |
| Detection → schema mapping | API / Backend | — | Own mapping layer; keep Ultralytics types out of wire schema |
| Runtime conf threshold | API / Backend (worker state) | Browser / Client (slider) | Worker owns hot conf; UI posts control |
| Model weight cache / offline | API / Backend + filesystem | — | MODEL-02; process-local path under cache dir |
| PerceptionStore (latest dets) | API / Backend | — | Single truth for UI + JSON |
| Overlay boxes on preview | API / Backend (MJPEG encode) | Browser / Client (`<img>`) | Option A: draw before JPEG → DET-04 parity without frame_id sync in JS |
| Detection JSON snapshot | API / Backend | Browser / Client (status poll) | Same store as overlay |
| Live Preview HTML controls | CDN / Static (packaged HTML) | Browser / Client | Extend Phase 2 static page |
| Capture / reconnect | API / Backend (unchanged) | — | Phase 2 CaptureLoop stays sole camera owner |
| AGPL / license disclosure | Docs / policy | — | THIRD_PARTY_MODELS + UI first-run note |

## Standard Stack

### Core

| Library | Version (verified 2026-08-07) | Purpose | Why Standard |
|---------|------------------------------|---------|--------------|
| Python | **3.11+** (CI 3.11; project `>=3.11`) | Runtime | Phase 1–2 lock [CITED: pyproject.toml] |
| **ultralytics-opencv-headless** | **8.4.116** | YOLO26 detect API, weight download | Same API as `ultralytics` but depends on `opencv-python-headless` — avoids GUI OpenCV conflict with project [VERIFIED: PyPI + docs.ultralytics.com/quickstart headless install] |
| **torch** | **2.13.0** (CPU wheel for CI/desktop CPU; CUDA from pytorch.org for GPU) | YOLO backend | Required by ultralytics (`torch>=1.8.0`) [VERIFIED: PyPI] |
| **torchvision** | **0.28.0** | Ultralytics dependency | Paired with torch 2.13 [VERIFIED: PyPI] |
| **opencv-python-headless** | already **≥4.10,<6** | Draw boxes, JPEG encode | Already in project; reuse for overlay [VERIFIED: pyproject.toml] |
| **numpy** | already **≥2.0,<2.5** | BGR arrays | Ultralytics accepts `np.ndarray` HWC BGR uint8 [CITED: docs.ultralytics.com/modes/predict] |
| fastapi / uvicorn / pydantic | already present | Control + snapshot API | Phase 2 shell |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **supervision** | **0.30.0** | Fancy box drawing | **Do not add in Phase 3** — OpenCV is enough; optional later [VERIFIED: PyPI] |
| pytest / httpx | already in dev | ASGI tests | Extend preview tests |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `ultralytics-opencv-headless` | `ultralytics` | Pulls `opencv-python` (GUI) → conflicts with headless install / libGL issues on servers — **reject** |
| YOLO26 | YOLO11 | Mature fallback only if YOLO26 regresses (CONTEXT lock) |
| Server-side overlay | Canvas JS + JSON | Needs frame_id sync; more UI work; acceptable if parity tested — **prefer server draw for Phase 3 static HTML** |
| `supervision` draw | OpenCV `rectangle`/`putText` | Extra dep for modest gain — defer |
| Sync infer in MJPEG handler | Dedicated detection thread | Blocks event loop; couples UI FPS to model — **reject** |
| Process-on-publish in CaptureLoop | DetectionLoop subscriber | Violates “workers never open cameras” spirit and stalls capture — **reject** |

**Installation:**

```bash
# Prefer headless Ultralytics to match project OpenCV
uv add "ultralytics-opencv-headless>=8.4.33,<9"

# Torch: install platform-appropriate wheel FIRST if CUDA desired
# CPU (CI / cpu-fallback):
#   uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
# CUDA desktop: follow https://pytorch.org/get-started/locally/

# Optional grouping (recommended):
# [project.optional-dependencies]
# detect = ["ultralytics-opencv-headless>=8.4.33,<9"]
# CI: uv sync --extra dev --extra detect
```

**Version verification notes:**
- Ultralytics **8.4.116** on PyPI (2026-08-07); YOLO26 requires **≥8.4** line (assets release `v8.4.0` ships `yolo26n.pt`) [VERIFIED: PyPI + GitHub ultralytics/assets]
- Default predict conf **0.25**, imgsz **640** [CITED: docs.ultralytics.com/usage/cfg + default.yaml]
- Do **not** pin a CUDA-specific torch in `pyproject.toml` core deps — document CUDA index install; CI uses CPU torch or mocks

## Package Legitimacy Audit

> slopcheck was **not available** in this environment. Packages below are long-standing ecosystem libraries confirmed on PyPI with official docs/source. Planner should gate first install behind a quick human glance if policy requires slopcheck.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| ultralytics-opencv-headless | PyPI | Ultralytics line ~years; headless variant current | High (mirrors ultralytics) | github.com/ultralytics/ultralytics | N/A | Approved — prefer over `ultralytics` |
| ultralytics | PyPI | ~3+ yrs | Very high | github.com/ultralytics/ultralytics | N/A | Approved as alias; **do not install alongside** headless project OpenCV |
| torch | PyPI / pytorch.org | 8+ yrs | Very high | github.com/pytorch/pytorch | N/A | Approved (transitive via ultralytics) |
| torchvision | PyPI / pytorch.org | 8+ yrs | Very high | github.com/pytorch/vision | N/A | Approved (transitive) |
| supervision | PyPI | mature | High | github.com/roboflow/supervision | N/A | **Not installed Phase 3** |

**Packages removed due to slopcheck [SLOP]:** none  
**Packages flagged as suspicious [SUS]:** none  
**Packages deferred:** `supervision` (drawing), TensorRT/ONNX export tooling (Phase 7)

*All packages tagged with registry verification; without slopcheck treat install as `[ASSUMED]` clean for planner checkpoint if required.*

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────┐
│ CameraSource     │  (Phase 2 — unchanged)
│ USB/file/synth/  │
│ RTSP             │
└────────┬─────────┘
         │ ImageFrame
         ▼
┌──────────────────┐     publish keep-latest
│ CaptureLoop      │──────────────────────────┐
│ (capture thread) │                          │
└──────────────────┘                          ▼
                                    ┌──────────────────┐
                                    │ FrameBus         │
                                    │ get_latest()     │
                                    └───┬──────────┬───┘
                                        │          │
                    ┌───────────────────┘          └──────────────────┐
                    ▼                                                 ▼
         ┌─────────────────────┐                           ┌─────────────────────┐
         │ DetectionLoop       │  skip if busy             │ MJPEG generator     │
         │ (worker thread)     │  (drop + count)           │ (async, ~30 FPS)    │
         │  get_latest()       │                           │  get_latest RGB     │
         │  worker.process()   │                           │  + store detections │
         └──────────┬──────────┘                           │  draw boxes         │
                    │ list[Detection] + stats              │  imencode JPEG      │
                    ▼                                      └──────────┬──────────┘
         ┌─────────────────────┐                                      │
         │ PerceptionStore     │◄──── single truth ───────────────────┤
         │ latest dets,        │                                      │
         │ conf, latency,      │                                      ▼
         │ completeness        │                           ┌─────────────────────┐
         └──────────┬──────────┘                           │ Browser Live Preview│
                    │                                      │ <img mjpeg>         │
          ┌─────────┴─────────┐                            │ conf slider → PATCH │
          ▼                   ▼                            │ status poll         │
   GET /api/snapshot   PATCH /api/detection/config         └─────────────────────┘
   GET /api/status     (extends Phase 2 metrics)
```

### Recommended Project Structure

Align with ARCHITECTURE.md logical layout while keeping Phase 1–2 packages:

```
src/sentry_ai/
├── models/                      # NEW — model workers (detection now; depth later)
│   ├── __init__.py
│   └── detection/
│       ├── __init__.py
│       ├── yolo_worker.py       # YoloDetectionWorker (ModelWorker)
│       ├── mapping.py           # Ultralytics Results → list[Detection]
│       └── loop.py              # DetectionLoop thread (FrameBus → store)
├── state/                       # NEW — process-local perception products
│   ├── __init__.py
│   └── perception_store.py      # keep-latest dets + conf + stage metrics
├── backend/
│   ├── protocols.py             # existing InferenceBackend
│   ├── null.py                  # existing
│   └── torch_device.py          # OPTIONAL thin helper: resolve cpu/cuda/mps
├── api/
│   ├── app.py                   # inject store + detection loop handles
│   ├── routes_preview.py        # MJPEG draws overlays from store
│   └── routes_detection.py      # snapshot + conf control
├── ui/static/index.html         # conf slider, det count, det ms
├── plugins/
│   └── ...                      # register worker entry point yolo-fixed
├── config/models.py             # extend ModelsConfig: conf, weights, cache_dir
└── schemas/perception.py        # Detection already exists — use as-is
```

**Entry point:**

```toml
[project.entry-points."sentry_ai.workers"]
noop = "sentry_ai.plugins.builtins:NoopWorker"
yolo-fixed = "sentry_ai.models.detection.yolo_worker:YoloDetectionWorker"
```

### Pattern 1: DetectionLoop as FrameBus subscriber (keep-latest)

**What:** Daemon thread loop: `frame = bus.get_latest()` → if same `frame_id` as last processed, sleep briefly → else `worker.process(frame)` → `store.publish_detections(...)`. If still processing, skip intermediate frames (count `det_frames_dropped`).

**When to use:** Always for live detection. Never call YOLO inside `CaptureLoop` or FastAPI handlers.

**Example:**

```python
# Pattern derived from ARCHITECTURE.md worker pool + Phase 2 CaptureLoop style
class DetectionLoop:
    def __init__(self, bus: FrameBus, worker: YoloDetectionWorker, store: PerceptionStore):
        self._bus = bus
        self._worker = worker
        self._store = store
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="detection", daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            frame = self._bus.get_latest()
            if frame is None or frame.frame_id == self._last_frame_id:
                self._stop.wait(0.005)
                continue
            t0 = time.perf_counter()
            dets = self._worker.process(frame)  # list[Detection]
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._last_frame_id = frame.frame_id
            self._store.set_detections(
                frame_id=frame.frame_id,
                camera_id=frame.camera_id,
                t_capture=frame.meta.t_capture,
                detections=dets or [],
                latency_ms=latency_ms,
            )
```

### Pattern 2: Ultralytics Results → Detection schema

**What:** Convert boxes in **original image pixel space** (xyxy) to Pydantic `Detection`.

**Example:**

```python
# Source: docs.ultralytics.com/tasks/detect + schemas/perception.py
from ultralytics import YOLO
from sentry_ai.schemas.perception import Detection

def results_to_detections(result) -> list[Detection]:
    if result.boxes is None or len(result.boxes) == 0:
        return []
    names = result.names  # dict[int, str]
    out: list[Detection] = []
    xyxy = result.boxes.xyxy.cpu().numpy()
    confs = result.boxes.conf.cpu().numpy()
    clss = result.boxes.cls.cpu().numpy().astype(int)
    for box, conf, cls_id in zip(xyxy, confs, clss, strict=True):
        out.append(
            Detection(
                class_name=str(names.get(int(cls_id), str(cls_id))),
                confidence=float(conf),
                bbox_xyxy=(float(box[0]), float(box[1]), float(box[2]), float(box[3])),
            )
        )
    return out
```

**Predict call (BGR numpy from ImageFrame):**

```python
# Source: docs.ultralytics.com/modes/predict — OpenCV/NumPy HWC BGR uint8 supported
results = model.predict(
    source=frame.image_bgr,
    conf=self._conf,       # runtime threshold (DET-03)
    imgsz=640,
    device=self._device,   # "cpu" | "cuda:0" | "mps"
    verbose=False,
    save=False,
)
return results_to_detections(results[0])
```

### Pattern 3: Model cache + offline (MODEL-02)

**What:** Point Ultralytics `weights_dir` at a Sentry-owned cache before first `YOLO(...)` load. After first download, files exist on disk; no network needed.

**How Ultralytics resolves weights** [CITED: ultralytics/utils/downloads.py `attempt_download_asset`]:
1. Local path if exists  
2. Else `SETTINGS["weights_dir"] / filename`  
3. Else download from `github.com/ultralytics/assets` release (YOLO26 → **v8.4.0**)

**Config dir:** `YOLO_CONFIG_DIR` env overrides Ultralytics user config dir (`~/.config/Ultralytics` on Linux) [CITED: ultralytics/utils/__init__.py `get_user_config_dir`].

**Recommended Sentry policy:**

```python
# Call once at process start before YOLO load
from pathlib import Path
import os
from ultralytics import settings

cache_root = Path(os.environ.get("SENTRY_MODEL_CACHE", Path.home() / ".cache" / "sentry-ai"))
weights_dir = cache_root / "weights"
weights_dir.mkdir(parents=True, exist_ok=True)
# Optional: isolate Ultralytics settings.json too
os.environ.setdefault("YOLO_CONFIG_DIR", str(cache_root / "ultralytics"))
settings.update({"weights_dir": str(weights_dir), "sync": False})  # sync=False reduces analytics
```

**Offline contract:** After `yolo26n.pt` is present under `weights_dir`, `YOLO("yolo26n.pt")` must not require network. Document in README + Live Preview copy (“model may download on first run”).

**Also disable Ultralytics auto-telemetry noise:** `settings.update({"sync": False})` and/or env patterns Ultralytics respects; keep verbose off in worker.

### Pattern 4: Server-side overlay (DET-04 parity)

**What:** When encoding MJPEG, copy latest BGR, draw boxes from `PerceptionStore` detections, then `cv2.imencode`. UI remains a single `<img src="/preview/mjpeg">` — no canvas.

**Why recommended over canvas:** Phase 2 UI is static HTML; UI-SPEC Option A guarantees the pixels match the detection list used by snapshot JSON without frame_id JS sync.

```python
# OpenCV draw — no supervision
def draw_detections(image_bgr: np.ndarray, detections: list[Detection]) -> np.ndarray:
    out = image_bgr.copy()
    for d in detections:
        x1, y1, x2, y2 = map(int, d.bbox_xyxy)
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 180), 2)
        label = f"{d.class_name} {d.confidence:.2f}"
        cv2.putText(out, label, (x1, max(0, y1 - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 180), 1, cv2.LINE_AA)
    return out
```

**Temporal skew:** Detection may lag RGB by 1–N frames. Accept for UI; include `frame_id` of detection product in status/snapshot so consumers see age. Do **not** run a second model for overlays.

### Pattern 5: Runtime conf control (DET-03)

```python
# Worker
class YoloDetectionWorker:
    def __init__(self, ..., conf: float = 0.25):
        self._lock = threading.Lock()
        self._conf = conf

    def set_conf(self, conf: float) -> None:
        if not 0.0 <= conf <= 1.0:
            raise ValueError("conf must be in [0, 1]")
        with self._lock:
            self._conf = conf

    def get_conf(self) -> float:
        with self._lock:
            return self._conf

    def process(self, frame: ImageFrame) -> list[Detection]:
        with self._lock:
            conf = self._conf
        # model.predict(..., conf=conf)
```

**API (recommended paths — Claude discretion locked here):**

| Method | Path | Body / response |
|--------|------|-----------------|
| `GET` | `/api/snapshot` | Partial `PerceptionFrame` JSON (`completeness.detections=true` when store has result) |
| `GET` | `/api/status` | Extend Phase 2 with `detections_count`, `det_latency_ms`, `det_conf`, `det_fps` |
| `PATCH` | `/api/detection/config` | `{"conf": 0.35}` → updates worker; returns applied conf |
| `GET` | `/api/detection/config` | Current conf + weight name + device |

Use `/api/*` in Phase 3 (not full `/v1` robot stream — Phase 5). Snapshot is the DET-04 API surface.

### Pattern 6: PerceptionFrame assembly

```python
from sentry_ai.schemas.perception import Completeness, PerceptionFrame

def build_detection_frame(store: PerceptionStore) -> PerceptionFrame | None:
    snap = store.snapshot()
    if snap is None:
        return None
    return PerceptionFrame(
        schema_version=1,
        frame_id=snap.frame_id,
        camera_id=snap.camera_id,
        t_capture=snap.t_capture,
        t_publish=time.time(),
        completeness=Completeness(detections=True, depth=False, free_space=False),
        detections=snap.detections,  # may be empty list — still complete
        stats={
            "det_latency_ms": snap.latency_ms,
            "det_conf": snap.conf,
            "det_model": snap.model_name,
        },
    )
```

**Completeness rule:** `detections=True` means the detection stage **ran** for this product (including zero boxes), not “objects present.” Empty list + `detections=True` is valid.

### How ModelWorker / InferenceBackend evolve

| Component | Phase 1–2 | Phase 3 change |
|-----------|-----------|----------------|
| `ModelWorker.process` | Noop returns `None` | `YoloDetectionWorker.process(ImageFrame) -> list[Detection]` |
| `InferenceBackend` | Protocol + `NullBackend` | Keep Protocol; **do not force YOLO through `infer(tensor)`** yet — Ultralytics owns preprocess. Optional `TorchDeviceBackend` only resolves device string / warmup. Full tensor backend abstraction waits for multi-backend export (Phase 7). |
| Plugin registry | `noop` worker | Add `yolo-fixed` entry point |
| `cli.serve` | bus + capture only | Also start `DetectionLoop`, inject store into `create_app` |
| `create_app` | bus + capture_loop | + `perception_store` (+ optional detection_worker for conf PATCH) |

**Do not** expand `InferenceBackend.infer` to wrap Ultralytics in Phase 3 — it adds indirection without multi-backend value. Keep NullBackend for unit tests.

### Weight / tier mapping

| Profile `detector_tier` | Weight file | When |
|-------------------------|-------------|------|
| `n` (cpu-fallback, jetson) | `yolo26n.pt` | Default edge / CI / CPU |
| `s` | `yolo26s.pt` | Desktop quality (CONTEXT + STACK) |
| `m` | `yolo26m.pt` | Current `desktop-gpu.yaml` tier — heavier |

**Discretion recommendation:** Map tiers as above. For Phase 3 **default serve profile `cpu-fallback` → `yolo26n`**. Note inconsistency: `desktop-gpu.yaml` has `detector_tier: m` while STACK/CONTEXT prefer **s** for desktop — either change profile to `s` in this phase or honor `m` via mapping. **Recommend changing desktop-gpu profile to `s`** for maker FPS; document `m` as opt-in.

### Anti-Patterns to Avoid

- **Infer inside MJPEG or `/api/snapshot` handlers** — latency spikes; event-loop block  
- **Second detector path for UI** — DET-04 violation  
- **Unbounded detection queue** — use keep-latest; count skips  
- **Installing plain `ultralytics` next to headless OpenCV** — dual OpenCV packages  
- **Calling relative depth / free-space** — out of scope  
- **Motor/command fields** on PerceptionFrame — forbidden  
- **Downloading weights in unit tests** — mock `YOLO` / inject fake worker  
- **Assuming CUDA always available** — probe and fall back to CPU  

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Object detector | Custom CNN / from-scratch NMS stack | Ultralytics YOLO26 | Training, export, NMS-free head, ecosystem |
| Weight download + cache | Custom HTTP downloader | Ultralytics `attempt_download_asset` + `weights_dir` | Resume, release pin, path resolution |
| Preprocess letterbox | Manual resize math | `model.predict` internal preprocess | Easy to get wrong stride/padding |
| Fancy annotation UI kit | New canvas framework | OpenCV draw + static HTML | Phase 3 scope; React later |
| Full perception merge bus | Kafka/Redis | In-process `PerceptionStore` | Single process; Phase 5 expands |
| Device abstraction rewrite | New plugin OS | Thin device string + existing `InferenceBackend` stub | Phase 7 owns TRT/ORT |

**Key insight:** Phase 3 value is **wiring + contracts + parity**, not reinventing detection. Keep Ultralytics behind a thin worker boundary so Phase 6 open-vocab and Phase 7 export can swap implementations.

## Common Pitfalls

### Pitfall 1: Capture-thread inference
**What goes wrong:** FPS collapses; reconnect logic delayed; UI freezes.  
**Why:** YOLO on CPU can be 50–200 ms+/frame.  
**How to avoid:** Dedicated `DetectionLoop`; CaptureLoop only publishes.  
**Warning signs:** `capture_fps` drops when detection enabled.

### Pitfall 2: Dual truth (UI draws ≠ API)
**What goes wrong:** Robot client sees different boxes than developer.  
**Why:** Separate conf filters or re-infer for overlay.  
**How to avoid:** One store; MJPEG and snapshot read it.  
**Warning signs:** Snapshot conf list differs from visible labels.

### Pitfall 3: OpenCV package conflict
**What goes wrong:** libGL errors, import fights, bloated images.  
**Why:** `ultralytics` depends on `opencv-python`.  
**How to avoid:** Install **`ultralytics-opencv-headless`**.  
**Warning signs:** Both `opencv-python` and `opencv-python-headless` in lockfile.

### Pitfall 4: Network on every start / CI
**What goes wrong:** Flaky CI; offline makers fail after first success claim.  
**Why:** Weights re-download if cache path not stable.  
**How to avoid:** Fixed `SENTRY_MODEL_CACHE` / `weights_dir`; tests never call real download.  
**Warning signs:** First-frame multi-second stall every run.

### Pitfall 5: Conf update ignored
**What goes wrong:** Slider moves; boxes unchanged.  
**Why:** Conf captured once at load; not passed per `predict`.  
**How to avoid:** Read conf under lock each `process()`.  
**Warning signs:** PATCH returns new conf but detections identical.

### Pitfall 6: Completeness misuse
**What goes wrong:** Consumers treat `detections=false` as “no objects.”  
**Why:** Flag means stage missing, not empty scene.  
**How to avoid:** Empty list + `detections=true` after stage runs; document.  

### Pitfall 7: AGPL surprise
**What goes wrong:** Commercial fork ships AGPL stack without compliance.  
**Why:** Ultralytics is AGPL-3.0; Enterprise license is paid alternative.  
**How to avoid:** Update `THIRD_PARTY_MODELS.md`; README note; keep policy tags.  
**Warning signs:** Marketing claims “permissive OSS detection” without AGPL callout.

### Pitfall 8: Torch install size / CI time
**What goes wrong:** CI minutes explode; smoke path requires CUDA.  
**Why:** Full torch wheel is large.  
**How to avoid:** optional-extra `detect`; mock YOLO in unit tests; CPU torch only if integration test needs real model.  
**Warning signs:** `uv sync` downloads GB on every clean CI without cache.

### Pitfall 9: BGR vs RGB
**What goes wrong:** Colors wrong; accuracy drop if converted twice.  
**Why:** OpenCV is BGR; PIL is RGB. Ultralytics documents OpenCV/NumPy as **BGR**.  
**How to avoid:** Pass `image_bgr` directly; never `cvtColor` before predict unless documented.

### Pitfall 10: Desktop-gpu tier `m` on weak hardware
**What goes wrong:** Poor FPS on laptop GPU.  
**Why:** Profile currently `detector_tier: m`.  
**How to avoid:** Prefer `s` desktop / `n` CPU; document.

## Code Examples

### Load YOLO26 + single-frame detect

```python
# Source: https://docs.ultralytics.com/models/yolo26/
from ultralytics import YOLO

model = YOLO("yolo26n.pt")  # downloads once into weights_dir
results = model.predict(source=image_bgr, conf=0.25, verbose=False, save=False)
```

### Runtime conf without reload

```python
# conf is a predict argument — no model reload required
# Source: https://docs.ultralytics.com/modes/predict/ (conf default 0.25)
results = model.predict(source=image_bgr, conf=new_conf, verbose=False, save=False)
```

### Settings weights_dir

```python
# Source: https://docs.ultralytics.com/quickstart/ (Ultralytics Settings)
from ultralytics import settings
settings.update({"weights_dir": "/path/to/weights", "sync": False})
print(settings["weights_dir"])
```

### FastAPI PATCH conf (sketch)

```python
from pydantic import BaseModel, Field
from fastapi import APIRouter, Request, HTTPException

class DetectionConfigUpdate(BaseModel):
    conf: float = Field(ge=0.0, le=1.0)

@router.patch("/api/detection/config")
async def patch_detection_config(body: DetectionConfigUpdate, request: Request):
    worker = request.app.state.detection_worker
    if worker is None:
        raise HTTPException(503, "detection worker not running")
    worker.set_conf(body.conf)
    return {"conf": worker.get_conf()}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| YOLOv8 / YOLO11 + NMS | **YOLO26** NMS-free end-to-end head | Ultralytics 8.4 / assets v8.4.0 (2026) | Simpler export; use `yolo26n/s.pt` |
| `ultralytics` + system OpenCV GUI | `ultralytics-opencv-headless` | Documented headless install path | Correct for server/CI |
| Research scripts open camera in model | FrameBus + worker thread | Sentry Phase 2 architecture | Latency isolation |
| UI-only detection demos | Single PerceptionStore | Product requirement DET-04 | Robot/API parity |

**Deprecated/outdated for this phase:**
- Hand-rolled NMS postprocess for YOLO26 default head (model is NMS-free by default)  
- Grounding DINO / heavy transformer detectors on live path  
- Vite/React for Phase 3 overlays (static HTML extension is enough)

## What NOT to Build

| Out of scope | Why | Phase |
|--------------|-----|-------|
| Full `/v1` WebSocket perception stream | Partial snapshot OK now | 5 |
| Depth / free-space / open-vocab | Roadmap later | 4–6 |
| Multi-stage enable matrix UI | Conf only required | 6 |
| TensorRT / ONNX export recipes | Edge packaging | 7 |
| Tracking IDs / ByteTrack | Not DET-* | later |
| `supervision` dependency | OpenCV sufficient | optional later |
| Canvas overlay architecture | Prefer server draw | optional if parity held |
| Training / fine-tuning UI | Explicit out of scope | never v1 |
| Dual model paths (UI vs API) | DET-04 | never |
| Cloud inference | MODEL-01 | never core |
| Motor/velocity fields | API-05 spirit | never |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `ultralytics-opencv-headless` remains API-identical to `ultralytics` for YOLO detect | Standard Stack | Import path or missing extras — verify on install |
| A2 | Desktop default weight should be `yolo26s` (profile currently `m`) | Weight mapping | FPS vs accuracy tradeoff — user may want `m` |
| A3 | Snapshot path `/api/snapshot` (not `/v1/snapshot`) is correct for Phase 3 | API | Phase 5 may rename; avoid hard client coupling |
| A4 | Empty detections + `completeness.detections=true` is the intended completeness semantics | PerceptionFrame | Consumer misinterpretation if docs lag |
| A5 | Disabling Ultralytics `sync` is enough privacy for local maker path | Cache / settings | Residual network calls (font/check) may remain — monitor first run |
| A6 | Optional-extra `detect` is preferred over hard core dep | Installation | Users may miss install; serve should fail clearly |

**If empty verification needed:** Confirm A1 on first `uv add` in plan Wave 0.

## Open Questions

1. **Core dep vs optional-extra for ultralytics?**  
   - What we know: Phase 2 CI is lean; torch is heavy; detection is Phase 3 success criteria.  
   - What's unclear: Whether every `pip install sentry-ai` must pull torch.  
   - **Recommendation:** `optional-dependencies.detect` + `sentry serve` enables detection when importable; clear error if missing. CI runs unit tests with mocks always; one optional job or local manual with real weights.

2. **Default weight for `sentry serve` without profile override?**  
   - **Recommendation:** `yolo26n.pt` (cpu-fallback profile default tier `n`) for reliable first run; desktop-gpu profile maps to `s` after profile fix.

3. **Should `/api/status` grow detection fields or only `/api/snapshot`?**  
   - **Recommendation:** Both — status for UI poll (count, latency, conf); snapshot for full `PerceptionFrame` JSON (DET-04).

4. **Warmup on start?**  
   - **Recommendation:** Yes — one dummy `predict` on zeros after load to avoid first-live-frame multi-second stall; log “model ready”.

5. **MPS on Apple Silicon?**  
   - What we know: Ultralytics `device` accepts `mps`. Local machine is M1 Pro.  
   - **Recommendation:** Auto-select `cuda` > `mps` > `cpu`; document MPS as best-effort.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | runtime | ✓ (local 3.14; CI 3.11) | 3.11+ required | CI pins 3.11 |
| uv | install | ✓ | 0.11.23 | pip |
| pytest | tests | ✓ | 8.4.2 | — |
| opencv-python-headless | capture + draw | ✓ (project) | lock 5.0.0.93 | — |
| ultralytics / torch | detection | ✗ not installed locally | — | install via optional extra; mock in tests |
| CUDA GPU | desktop-gpu profile | unknown / not required | — | CPU / MPS |
| Network (first weight pull) | MODEL-02 first run | assume ✓ for makers | — | pre-seed cache dir in airgap |
| slopcheck | package audit | ✗ | — | manual PyPI review |

**Missing dependencies with no fallback:** none for planning — torch/ultralytics are install tasks.

**Missing dependencies with fallback:** CUDA → CPU/MPS; real weights in CI → mocks.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (project) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=`tests` |
| Quick run command | `uv run pytest tests/test_detection_mapping.py tests/test_detection_worker.py -q` |
| Full suite command | `uv run pytest -q` |
| Lint | `uv run ruff check src tests` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| DET-01 | Worker process on ImageFrame returns list (mock model) | unit | `pytest tests/test_detection_worker.py::test_process_returns_detections -q` | ❌ Wave 0 |
| DET-01 | DetectionLoop reads bus, does not open camera | unit | `pytest tests/test_detection_loop.py::test_uses_bus_only -q` | ❌ Wave 0 |
| DET-02 | Mapping xyxy/conf/cls → Detection schema | unit | `pytest tests/test_detection_mapping.py -q` | ❌ Wave 0 |
| DET-02 | bbox in image coordinates (fixture known box) | unit | `pytest tests/test_detection_mapping.py::test_bbox_xyxy_values -q` | ❌ Wave 0 |
| DET-03 | set_conf changes threshold used on next process | unit | `pytest tests/test_detection_worker.py::test_runtime_conf -q` | ❌ Wave 0 |
| DET-03 | PATCH `/api/detection/config` updates conf | integration | `pytest tests/test_api_detection.py::test_patch_conf -q` | ❌ Wave 0 |
| DET-04 | Snapshot JSON detections == store used for draw helper | unit | `pytest tests/test_detection_overlay.py::test_draw_uses_same_list -q` | ❌ Wave 0 |
| DET-04 | GET `/api/snapshot` completeness.detections true | integration | `pytest tests/test_api_detection.py::test_snapshot_completeness -q` | ❌ Wave 0 |
| MODEL-02 | weights_dir / cache helper points at Sentry path | unit | `pytest tests/test_model_cache.py -q` | ❌ Wave 0 |
| MODEL-02 | THIRD_PARTY_MODELS documents YOLO AGPL + cache | unit | `pytest tests/test_third_party_models_doc.py -q` (extend) | ✅ exists (extend) |
| — | No torch import in non-detect smoke path | unit | `pytest tests/test_cli_smoke.py -q` | ✅ exists |
| — | MJPEG still works with empty detections | integration | `pytest tests/test_api_preview.py -q` | ✅ exists |

### Sampling Rate

- **Per task commit:** quick module tests above  
- **Per wave merge:** `uv run pytest -q` + `uv run ruff check src tests`  
- **Phase gate:** full suite green; manual USB/synthetic with real YOLO optional  

### Wave 0 Gaps

- [ ] `tests/test_detection_mapping.py` — DET-02 mapping pure functions  
- [ ] `tests/test_detection_worker.py` — mock YOLO / injectable predict  
- [ ] `tests/test_detection_loop.py` — bus subscriber + skip same frame_id  
- [ ] `tests/test_detection_overlay.py` — draw_detections pure  
- [ ] `tests/test_api_detection.py` — snapshot + PATCH conf via TestClient  
- [ ] `tests/test_model_cache.py` — cache path helper (no network)  
- [ ] `tests/fixtures/fake_yolo_result.py` or conftest factory for Boxes-like objects  
- [ ] Extend `tests/test_third_party_models_doc.py` for YOLO Phase 3 status  
- [ ] Optional: `optional-dependencies.detect` + CI note (mocks do not require extra)

**CI strategy without GPU:**  
- Default unit/integration tests **mock** `ultralytics.YOLO` (or inject a `FakeDetectionWorker`).  
- Never download `yolo26n.pt` in GitHub Actions unless a separate scheduled job with cache.  
- Real-model manual check: `sentry serve --source synthetic` after local weight download.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no (localhost default) | MODEL-03; document LAN opt-in unauthenticated |
| V3 Session Management | no | — |
| V4 Access Control | partial | Bind 127.0.0.1; conf PATCH only local |
| V5 Input Validation | yes | Pydantic `conf` in [0,1]; reject extra fields |
| V6 Cryptography | no | — |
| V10 Malicious Code | yes | slopcheck/PyPI review; no dynamic `exec` of model code beyond torch load |
| V14 Configuration | yes | `allow_cloud` stays false; cache path not world-writable secrets |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious model weights | Tampering | Load only known filenames (`yolo26n.pt` etc.); pin release source; no arbitrary URL weights in v1 |
| Unauthenticated LAN conf change | Elevation | Default localhost; warn on `--host 0.0.0.0` |
| Path traversal in weight path | Tampering | Resolve under cache root; reject `..` |
| DoS via conf thrash / huge frames | Denial | Debounce UI 100–200ms; keep-latest drops; imgsz cap 640 |
| AGPL compliance gap | (legal) | THIRD_PARTY_MODELS + README |
| Prompt/injection N/A | — | Fixed-class only; no text prompts until Phase 6 |
| Camera privacy | Information Disclosure | Localhost; no cloud upload; analytics sync off |

## Project Constraints (from CLAUDE.md / project skills)

- No project-root `CLAUDE.md` / `AGENTS.md` found in repo; follow Phase 1–2 conventions already established:
  - Package layout under `src/sentry_ai/`
  - Ruff lint; pytest; `uv` for deps
  - Optional deps under `[project.optional-dependencies]` not uv dependency-groups (Phase 2 lesson)
  - Handlers never open cameras; inject bus/state via `create_app`
  - Perception-only; no autonomy language in UI
- User-level note: graphify skill exists globally — not required for this phase research

## Sources

### Primary (HIGH confidence)

- Ultralytics YOLO26 docs — https://docs.ultralytics.com/models/yolo26/  
- Ultralytics Predict mode — https://docs.ultralytics.com/modes/predict/  
- Ultralytics Detect task results — https://docs.ultralytics.com/tasks/detect/  
- Ultralytics cfg defaults — https://docs.ultralytics.com/usage/cfg/ + `ultralytics/cfg/default.yaml`  
- Ultralytics Settings / weights_dir — https://docs.ultralytics.com/quickstart/  
- Ultralytics source: `attempt_download_asset`, `SettingsManager`, `YOLO_CONFIG_DIR` — github.com/ultralytics/ultralytics  
- GitHub assets release **v8.4.0** ships `yolo26n.pt` [VERIFIED: HTTP 302 asset]  
- PyPI: ultralytics 8.4.116, ultralytics-opencv-headless 8.4.116, torch 2.13.0, torchvision 0.28.0, supervision 0.30.0  
- In-repo: `schemas/perception.py`, `plugins/protocols.py`, `bus/frame_bus.py`, `api/*`, `cli.py`, `THIRD_PARTY_MODELS.md`, Phase 2 summaries  
- Planning: `STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `REQUIREMENTS.md`, `ROADMAP.md`, `03-CONTEXT.md`, `03-UI-SPEC.md`

### Secondary (MEDIUM confidence)

- STACK.md version pins (partially re-verified; ultralytics now 8.4.116 vs researched 8.4.115)  
- MPS device behavior on Apple Silicon for YOLO26 [ASSUMED best-effort]  

### Tertiary (LOW confidence)

- Residual Ultralytics network calls beyond weight download after `sync=False` — not fully audited this session  

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — PyPI + official Ultralytics docs + assets release verified  
- Architecture: **HIGH** — aligns with shipped FrameBus/CaptureLoop and ARCHITECTURE.md  
- Pitfalls: **HIGH** — latency, dual-truth, OpenCV conflict, AGPL known  
- Offline cache edge cases: **MEDIUM** — depends on Ultralytics download internals remaining stable  
- Optional-extra packaging choice: **MEDIUM** — product preference  

**Research date:** 2026-08-07  
**Valid until:** ~2026-09-07 (Ultralytics/torch move quickly; re-check versions at plan execution)

---

## RESEARCH COMPLETE

**Phase:** 3 - Fixed-Class Detection  
**Confidence:** HIGH

### Key Findings
- Use **`ultralytics-opencv-headless` 8.4.x** + **YOLO26** (`yolo26n` default / `yolo26s` desktop); predict on BGR numpy with **`conf` per call** (default 0.25).
- **DetectionLoop thread** + **PerceptionStore** (keep-latest) isolates latency; never infer in capture or FastAPI handlers.
- Map `boxes.xyxy/conf/cls` + `names` → existing `Detection` schema; assemble `PerceptionFrame` with `completeness.detections=true`.
- **Server-side OpenCV overlay** on MJPEG + **`GET /api/snapshot`** share one store (DET-04); **`PATCH /api/detection/config`** for runtime conf (DET-03).
- Cache via Ultralytics **`weights_dir`** + optional **`YOLO_CONFIG_DIR`** / `SENTRY_MODEL_CACHE` (MODEL-02); document AGPL; **mock YOLO in CI**.

### File Created
`.planning/phases/03-fixed-class-detection/03-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | PyPI + Ultralytics official docs verified |
| Architecture | HIGH | Fits Phase 2 bus/API; ARCHITECTURE.md worker pattern |
| Pitfalls | HIGH | Latency, dual-truth, OpenCV/AGPL well documented |

### Open Questions
- optional-extra vs core torch install  
- desktop-gpu tier `m` vs recommended `s`  
- residual Ultralytics network after cache  

### Ready for Planning
Research complete. Planner can now create PLAN.md files (03-01 worker/cache, 03-02 overlays/API/telemetry).
