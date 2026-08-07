# Phase 4: Monocular Depth - Research

**Researched:** 2026-08-07  
**Domain:** Local monocular depth (Depth Anything V2 Small), depth worker + PerceptionStore, honest `depth_kind`, colormap UI/API parity  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Default depth: **DAV2 Small** (Apache-2.0) — never default NC Base/Large/Giant
- Relative by default; metric only when explicitly enabled with correct `depth_kind` + unit
- No `depth_m` field on relative paths; existing `DepthPayload` + validators
- Depth worker never opens cameras; FrameBus → worker → store (mirror DetectionLoop)
- UI and API share one depth product truth
- Local OSS only; cache after first download

### From Phase 1–3 shipped code
- `DepthKind`, `DepthPayload`, `PerceptionFrame`, `Completeness.depth`
- `DetectionLoop` / `PerceptionStore` / `YoloDetectionWorker` patterns
- Model cache (`SENTRY_MODEL_CACHE`)
- FastAPI snapshot + MJPEG overlay pattern
- optional-extra pattern for heavy deps (`detect`)

### Claude's Discretion
- HF transformers vs native DAV2 repo load path
- Depth product storage: full float map in process vs downsampled for JSON
- Colormap: side-by-side vs alpha blend vs toggle
- Whether depth is optional-extra `depth` (recommended, mirror detect)
- Metric indoor vs outdoor head selection UX (config flag)

### Deferred Ideas (OUT OF SCOPE)
- Free-space / obstacles derivation (Phase 5)
- Full `/v1` WS robot stream polish (Phase 5) — extend snapshot OK
- Open-vocab, full stage toggles (Phase 6)
- TensorRT export (Phase 7)
- Stereo / multi-cam depth
- Full metric calibration UX (optional metric mode only; calibration later)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| DEPTH-01 | Monocular depth model runs locally (Depth Anything V2 Small or equivalent OSS) | `DepthAnythingWorker` + `DepthLoop` on FrameBus; HF `depth-anything/Depth-Anything-V2-Small-hf` (Apache-2.0); optional-extra `depth` |
| DEPTH-02 | Depth map available in perception stream with explicit `depth_kind` | Extend snapshot/`PerceptionFrame.depth` (`DepthPayload.kind` + unit); store `DepthProduct`; `completeness.depth=true` |
| DEPTH-03 | Depth colormap on web dashboard | Server-side OpenCV `COLORMAP_TURBO` composite into MJPEG (parity with detection overlay) |
| DEPTH-04 | Optional metric mode labeled; never conflated with relative | Config `depth_mode`; metric → `DepthKind.METRIC_ESTIMATED` + `unit="m"` + UI badge; relative forbids unit/`m` labels |
</phase_requirements>

## Summary

Phase 4 adds the **spatial awareness primitive**: a local monocular depth worker that consumes the Phase 2 FrameBus (parallel to Phase 3 detection), publishes a keep-latest depth product into an extended **PerceptionStore**, and exposes honest depth semantics via existing `DepthKind` / `DepthPayload` contracts. Default path is **Depth Anything V2 Small relative** (Apache-2.0). Optional metric mode loads indoor (Hypersim, max≈20 m) or outdoor (VKITTI, max≈80 m) Small metric heads and labels them `metric_estimated` with `unit="m"` — never as calibrated truth. Dashboard shows a **server-drawn depth colormap** on the MJPEG stream; JSON snapshot carries **metadata + stats**, not giant float arrays.

**Primary recommendation:** Mirror detection architecture (`DepthLoop` + injectable `DepthAnythingWorker` + store methods) using **Hugging Face Transformers** load path (`AutoImageProcessor` + `AutoModelForDepthEstimation` for `depth-anything/Depth-Anything-V2-Small-hf`), optional-extra `depth`, HF cache rooted under `SENTRY_MODEL_CACHE`, and CI tests that inject fake models (no HF download).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| DAV2 load + inference | API / Backend (depth thread) | — | Blocking torch; never in request handlers or capture |
| FrameBus read (keep-latest) | API / Backend | — | Workers subscribe; sources already publish |
| Preprocess (BGR→RGB, resize, normalize) | API / Backend (worker) | — | Model-specific; pure helpers unit-testable |
| Relative vs metric kind mapping | API / Backend | — | Own `DepthKind`/`unit`; never trust model marketing |
| Full float depth map (in-process) | API / Backend (store) | — | Needed for colormap + Phase 5 free-space; not wire bulk |
| Depth metadata JSON | API / Backend | Browser (status poll) | `DepthPayload` + stats; single truth |
| Colormap composite on preview | API / Backend (MJPEG encode) | Browser (`<img>`) | Server draw → DET-04-style parity without frame_id sync in JS |
| Depth latency / FPS telemetry | API / Backend (store metrics) | Browser status bar | Mirror `det_latency_ms` pattern |
| Metric mode config | API / Backend (worker config) | Browser (optional control) | Explicit enable only; badge must match kind |
| Model weight cache (HF) | API / Backend + filesystem | — | MODEL-02 under `SENTRY_MODEL_CACHE` |
| License default (Apache Small) | Docs / policy | — | THIRD_PARTY_MODELS + never NC Base/Large default |
| Capture / reconnect | API / Backend (unchanged) | — | Phase 2 CaptureLoop stays sole camera owner |

## Standard Stack

### Core

| Library | Version (verified 2026-08-07) | Purpose | Why Standard |
|---------|------------------------------|---------|--------------|
| Python | **3.11+** (project `>=3.11`) | Runtime | Phase 1–3 lock [CITED: pyproject.toml] |
| **transformers** | **5.14.1** (require `>=4.45,<6`) | Load DAV2 HF models + processors | Official DAV2 support; metric HF models need ≥4.45 [VERIFIED: pypi.org + HF model cards] |
| **huggingface-hub** | **1.27.0** (require `>=0.23,<2`) | Weight download / cache | Transitive of transformers; control cache root [VERIFIED: pypi.org] |
| **torch** | **2.13.0** (CPU or CUDA wheels) | Inference backend | Required by transformers depth models [VERIFIED: pypi.org] |
| **pillow** | **12.3.0** (require `>=10`) | RGB image for HF processor | HF path expects PIL; OpenCV is BGR [VERIFIED: pypi.org] |
| **opencv-python-headless** | already **≥4.10,<6** | Colormap + MJPEG + BGR frames | Already in core deps [CITED: pyproject.toml] |
| **numpy** | already **≥2.0,<2.5** | Depth arrays HxW float | Store + stats + colormap normalize [CITED: pyproject.toml] |
| fastapi / uvicorn / pydantic | already present | Status / snapshot / config | Phase 2–3 shell |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **safetensors** | **0.8.0** (transitive) | Weight format for HF models | Auto via transformers [VERIFIED: pypi.org] |
| **timm** / **einops** | n/a for HF path | Native DAV2 repo deps | **Do not add** if using transformers path |
| pytest / httpx | already in dev | Unit + ASGI tests | Extend Phase 3 patterns |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| **HF transformers** (recommended) | Native `DepthAnythingV2` + `.pth` from official repo | Native matches paper OpenCV path exactly; requires vendoring `depth_anything_v2` code + `timm`; worse maker DX. Authors note slight upsample difference HF vs native [CITED: github.com/DepthAnything/Depth-Anything-V2] |
| Relative Small default | Metric Small default | Metric is domain-split and still estimated; product honesty prefers relative default [CITED: PITFALLS.md] |
| Alpha-blend colormap | Side-by-side dual MJPEG | Dual stream more UI work; blend reuses single `/preview/mjpeg` |
| Full float map in JSON | Metadata + stats only | 640×480 float32 ≈ 1.2 MB/frame JSON — kills status poll and snapshot; Phase 5 can add binary later |
| Optional-extra `depth` | Core deps | Pulls torch/transformers into default CI — **reject** (mirror `detect`) |
| Base/Large for quality | Small only | Base/Large are **CC-BY-NC-4.0** — never default [CITED: DAV2 LICENSE + HF Base-hf license] |

**Installation:**

```bash
# Recommended optional extra (mirror detect)
# [project.optional-dependencies]
# depth = [
#   "torch>=2.2,<3",
#   "transformers>=4.45,<6",
#   "huggingface-hub>=0.23,<2",
#   "pillow>=10,<13",
# ]
uv sync --extra dev --extra depth
# Combined with detection:
uv sync --extra dev --extra detect --extra depth

# CUDA desktop: install platform torch first (same as Phase 3)
#   uv pip install torch --index-url https://pytorch.org/whl/cu124  # example; follow pytorch.org
```

**Version verification notes:**
- `transformers` **5.14.1**, `huggingface-hub` **1.27.0**, `torch` **2.13.0**, `pillow` **12.3.0** on PyPI (2026-08-07) [VERIFIED: pypi.org]
- Metric HF models document `transformers>=4.45.0` [CITED: huggingface.co/depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf]
- Do **not** pin CUDA-specific torch in core `pyproject.toml` — document index install; CI uses mocks / CPU

### Model IDs (prescriptive)

| Mode | HF model id | Params | License | DepthKind | unit |
|------|-------------|--------|---------|-----------|------|
| **Default relative** | `depth-anything/Depth-Anything-V2-Small-hf` | 24.8M | **apache-2.0** [VERIFIED: HF API] | `relative` | `None` |
| Metric indoor (opt) | `depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf` | 24.8M | Verify before ship (HF card license field empty) [ASSUMED: inherits Small Apache] | `metric_estimated` | `"m"` |
| Metric outdoor (opt) | `depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf` | 24.8M | Verify before ship [ASSUMED] | `metric_estimated` | `"m"` |
| Base/Large any | `…-Base-hf` / `…-Large-hf` | 97.5M / 335M | **cc-by-nc-4.0** [VERIFIED: HF Base-hf] | — | **Never default** |

Native checkpoint names (if native path chosen later): `depth_anything_v2_vits.pth`; metric `depth_anything_v2_metric_hypersim_vits.pth` / `…_vkitti_vits.pth` with `max_depth=20|80` [CITED: metric_depth README].

**Policy key:** `DEFAULT_DEPTH_WEIGHT_KEY = "depth-anything-v2-small"` already exists in `policy/models.py` — map it to the relative HF id above.

## Package Legitimacy Audit

> slopcheck was **not available** in this environment. Packages below are long-standing ecosystem libraries confirmed on PyPI with official docs/source. Planner should gate first install behind a quick human glance if policy requires slopcheck.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| transformers | PyPI | 6+ yrs | Very high | github.com/huggingface/transformers | N/A | Approved — Apache-2.0 |
| huggingface-hub | PyPI | 4+ yrs | Very high | github.com/huggingface/huggingface_hub | N/A | Approved — Apache-2.0 |
| torch | PyPI / pytorch.org | 8+ yrs | Very high | github.com/pytorch/pytorch | N/A | Approved |
| pillow | PyPI | 10+ yrs | Very high | github.com/python-pillow/Pillow | N/A | Approved |
| safetensors | PyPI | mature | High | github.com/huggingface/safetensors | N/A | Approved (transitive) |
| timm / einops | PyPI | mature | High | — | N/A | **Not installed** (HF path) |

**Packages removed due to slopcheck [SLOP]:** none  
**Packages flagged as suspicious [SUS]:** none  
**Packages deferred:** native DAV2 vendored code, TensorRT/ONNX depth export (Phase 7)

*Without slopcheck, treat install as `[ASSUMED]` clean for planner checkpoint if required.*

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
                                    └───┬──────┬───────┘
                    ┌───────────────────┘      └──────────────────┐
                    ▼                                             ▼
         ┌─────────────────────┐                       ┌─────────────────────┐
         │ DetectionLoop       │  (Phase 3, optional)  │ DepthLoop           │
         │ worker.process()    │                       │ (NEW daemon thread) │
         └──────────┬──────────┘                       │  get_latest()       │
                    │                                  │  worker.process()   │
                    │                                  └──────────┬──────────┘
                    │ list[Detection]                             │ DepthProduct
                    ▼                                             ▼
         ┌──────────────────────────────────────────────────────────┐
         │ PerceptionStore (EXTENDED)                               │
         │  DetectionProduct  |  DepthProduct                       │
         │  det_* metrics     |  depth_* metrics (latency, fps)     │
         │  single truth for UI + snapshot                          │
         └───────────────────────────┬──────────────────────────────┘
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          ▼                          ▼                          ▼
   GET /api/snapshot          GET /api/status            MJPEG generator
   PerceptionFrame:           det_* + depth_*            bus RGB
     completeness.depth       depth_kind badge fields    + draw_detections
     depth: DepthPayload                                 + colorize_depth blend
     stats: depth_latency_ms                             → imencode JPEG
          ▼
   Browser Live Preview
   colormap in stream + status: Depth kind | Depth ms
```

### Recommended Project Structure

```
src/sentry_ai/
├── models/
│   ├── cache.py                 # EXTEND: HF cache under SENTRY_MODEL_CACHE
│   ├── detection/               # Phase 3 (unchanged contract)
│   └── depth/                   # NEW
│       ├── __init__.py
│       ├── worker.py            # DepthAnythingWorker (ModelWorker)
│       ├── preprocess.py        # pure BGR→RGB / optional letterbox helpers
│       ├── mapping.py           # tensor/array → store fields + DepthPayload
│       ├── colormap.py          # pure OpenCV colorize + alpha blend
│       └── loop.py              # DepthLoop (DetectionLoop twin)
├── state/
│   └── perception_store.py      # EXTEND: DepthProduct + set_depth + metrics
├── api/
│   ├── app.py                   # inject depth_worker
│   ├── deps.py                  # AppState.depth_worker
│   ├── routes_preview.py        # MJPEG depth blend + status depth fields
│   ├── routes_detection.py      # EXTEND snapshot completeness.depth
│   └── routes_depth.py          # OPTIONAL GET/PATCH depth config (mode)
├── cli.py                       # serve: start DepthLoop when depth extra OK
├── policy/models.py             # already has DEFAULT_DEPTH_WEIGHT_KEY
└── ui/static/index.html         # depth kind badge + depth latency
```

### Pattern 1: DepthLoop (DetectionLoop twin)
**What:** Daemon thread: `FrameBus.get_latest()` → skip same `frame_id` → `worker.process(frame)` → `store.set_depth(...)`; count gaps as drops; on exception store product with `error=` and keep thread alive.  
**When to use:** Always for live depth — never infer in FastAPI handlers.  
**Example:**
```python
# Source: Phase 3 DetectionLoop pattern (src/sentry_ai/models/detection/loop.py)
# Structural twin — rename fields only
t0 = time.perf_counter()
try:
    result = self._worker.process(frame)  # returns DepthResult / map + kind
    latency_ms = (time.perf_counter() - t0) * 1000.0
    self._store.set_depth(
        frame_id=frame.frame_id,
        camera_id=frame.camera_id,
        t_capture=frame.meta.t_capture,
        depth_map=result.depth_map,  # HxW float32 in-process only
        kind=result.kind,
        unit=result.unit,
        latency_ms=latency_ms,
        model_name=self._worker.name,
        error=None,
    )
except Exception as exc:
    # keep thread alive; surface error on product
    ...
```

### Pattern 2: Injectable DepthAnythingWorker (CI-safe)
**What:** Constructor accepts optional `model=` + `processor=` (or single callable) so unit tests never call `from_pretrained`. Lazy load only when both None.  
**When to use:** All default tests; real load only in optional integration / manual serve.  
**Example:**
```python
# Source: Phase 3 YoloDetectionWorker + HF docs
# https://huggingface.co/docs/transformers/main/en/model_doc/depth_anything_v2
class DepthAnythingWorker:
    name: str = "depth-anything-v2-small"

    def __init__(
        self,
        model_id: str = "depth-anything/Depth-Anything-V2-Small-hf",
        depth_mode: str = "relative",  # relative | metric_indoor | metric_outdoor
        device: str | None = None,
        model: Any | None = None,
        processor: Any | None = None,
    ) -> None: ...

    def process(self, frame: ImageFrame) -> DepthResult:
        # 1) image_bgr → RGB PIL/numpy
        # 2) processor(images=..., return_tensors="pt")
        # 3) model(**inputs) → predicted_depth
        # 4) interpolate to original H×W
        # 5) map mode → DepthKind + unit
        ...
```

### Pattern 3: HF load path (recommended for makers)
**What:** Use transformers Auto classes; set HF cache under Sentry cache root before load.  
**When to use:** Default implementation (Claude's discretion resolved here).  
**Example:**
```python
# Source: https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf
from transformers import AutoImageProcessor, AutoModelForDepthEstimation
import torch

processor = AutoImageProcessor.from_pretrained(model_id)
model = AutoModelForDepthEstimation.from_pretrained(model_id)
model.to(device).eval()

inputs = processor(images=pil_rgb, return_tensors="pt")
inputs = {k: v.to(device) for k, v in inputs.items()}
with torch.no_grad():
    outputs = model(**inputs)
# Prefer processor.post_process_depth_estimation when available;
# else F.interpolate predicted_depth to original size (HF model card).
```

**Why not native first:** makers avoid git-cloning DAV2 + managing `.pth` + `timm`; HF id maps cleanly to `DEFAULT_DEPTH_WEIGHT_KEY`; offline cache via hub. Native remains Phase 7 export-adjacent option if TensorRT community exporters expect `.pth`.

### Pattern 4: PerceptionStore depth extension (unified store, dual products)
**What:** Keep **one** `PerceptionStore` instance (Phase 5 merge friendliness). Add `DepthProduct` + `set_depth` / `snapshot_depth` + depth metrics fields. Detection methods unchanged.  
**When to use:** Phase 4 — do **not** wait for full PerceptionFrame merge service (Phase 5).  
**Why not separate DepthStore class:** API/UI already inject one store; dual stores force dual injection and drift.  
**Why not full merge-by-frame_id yet:** Phase 5 owns Spatial Post + completeness TTL; Phase 4 may show det/depth from different `frame_id`s (same intentional skew as RGB vs det today).

```python
@dataclass
class DepthProduct:
    frame_id: int
    camera_id: str
    t_capture: float
    kind: DepthKind
    unit: Literal["m"] | None
    width: int
    height: int
    latency_ms: float
    depth_map: Any  # np.ndarray HxW float32 — in-process only
    # Optional wire stats (computed at set time):
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    model_name: str | None = None
    error: str | None = None
```

**JSON isolation rule:** `snapshot_depth()` for API must **not** require serializing `depth_map`. Either:
- store separates wire fields from array, or
- snapshot builder copies metadata only into `DepthPayload` + stats dict.

### Pattern 5: Snapshot completeness + DepthPayload
**What:** Extend `GET /api/snapshot` to merge detection + depth products when present.  
**When to use:** DEPTH-02 / UI-API parity.  

```python
# Conceptual — extend routes_detection.api_snapshot or shared builder
depth_product = store.snapshot_depth()
detections_product = store.snapshot()  # existing DetectionProduct

completeness = Completeness(
    detections=detections_product is not None,
    depth=depth_product is not None and depth_product.error is None,
    free_space=False,
)
depth_payload = None
if depth_product is not None and depth_product.error is None:
    depth_payload = DepthPayload(
        kind=depth_product.kind,
        unit=depth_product.unit,  # None for relative — validator enforces
        width=depth_product.width,
        height=depth_product.height,
    )
stats = {
    "det_latency_ms": ...,
    "depth_latency_ms": depth_product.latency_ms if depth_product else None,
    "depth_min": depth_product.min_value,
    "depth_max": depth_product.max_value,
    "depth_mean": depth_product.mean_value,
}
# frame_id: prefer max(t_capture) product or document "primary" as capture latest
```

**404 policy:** Prefer: empty store (no det AND no depth) → 404; partial products OK with completeness flags. (Detection-only 404 today when no det product — extend carefully so depth-only still returns 200.)

### Pattern 6: Colormap rendering (OpenCV)
**What:** Pure helper `colorize_depth(depth_map, kind) -> BGR uint8`; `blend_depth(rgb, colorized, alpha=0.45)`.  
**When to use:** MJPEG path only (DEPTH-03).  

```python
# OpenCV COLORMAP_TURBO (perceptually ordered). Document: near = warm (yellow/red)
# after min-max normalize of valid finite values to 0..255 uint8.
norm = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
norm_u8 = norm.astype(np.uint8)
color = cv2.applyColorMap(norm_u8, cv2.COLORMAP_TURBO)
out = cv2.addWeighted(rgb_bgr, 1.0 - alpha, color, alpha, 0)
```

**Relative vs metric visualization:** Same colormap code path. **Never** draw unit text `"m"` when `kind == relative`. Optional scale bar only for metric kinds (optional Phase 4 polish).

**Default UI mode:** **alpha blend** on the single MJPEG stream (simplest; matches detection overlay). Side-by-side deferred unless time remains (UI-SPEC allows either).

### Pattern 7: Latency telemetry (mirror detection)
**What:** Store tracks `depth_frames`, `depth_frames_dropped`, `depth_fps`, `last_depth_latency_ms`. Status merges:

| Status field | Source |
|--------------|--------|
| `depth_latency_ms` | product / metrics |
| `depth_fps` | metrics window |
| `depth_frame_id` | product |
| `depth_kind` | product.kind value string |
| `depth_unit` | product.unit or omit when null |
| `depth_error` | product.error if set |

UI footer: `Depth: relative | Latency: n ms` — never show meters for relative (UI-SPEC).

### Pattern 8: Model cache for HF under SENTRY_MODEL_CACHE
**What:** Extend `configure_model_cache` (or add `configure_hf_cache`) so hub downloads land under Sentry root, not only `~/.cache/huggingface`.

```python
# Recommended resolution
root = Path(os.environ.get("SENTRY_MODEL_CACHE") or default_cache_root())
hf_home = root / "hf"
hf_home.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(hf_home))
# Optionally also:
# os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_home / "hub"))
# os.environ.setdefault("TRANSFORMERS_CACHE", str(hf_home / "transformers"))  # legacy
```

Call **before** first `from_pretrained`. Document offline re-run after first download (MODEL-02). Ultralytics `weights_dir` path remains for YOLO; HF is sibling dir under same root.

### Pattern 9: Device selection
**What:** Reuse Phase 3 `resolve_device` logic (cuda → mps → cpu); move to shared helper `sentry_ai.models.device.resolve_device` **or** duplicate thin copy in depth worker to avoid churn (planner discretion: prefer shared util if both import it).

### Anti-Patterns to Avoid
- **Infer in MJPEG/status handlers** — blocks event loop; couples UI FPS to model
- **Opening cameras in depth worker** — architecture violation
- **Defaulting Base/Large** — NC license landmine
- **Labeling relative as meters** / field `depth_m` — FOUND-03 / DEPTH-04
- **Shipping full HxW float arrays in JSON snapshot** — bandwidth + latency trap
- **Silent metric mode** without badge / kind change
- **Downloading weights in unit tests** — CI flaky / offline fail
- **Free-space derivation in Phase 4** — Phase 5 only
- **Hardcoding CUDA** — macOS MPS and CPU makers must work

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DAV2 architecture + weights | Custom ViT-DPT | transformers `AutoModelForDepthEstimation` | Research quality model; HF packaging |
| Image net normalize / resize for DAV2 | Ad-hoc letterbox math only | `AutoImageProcessor` | Matches checkpoint training preprocess |
| Depth colormap | Custom gradient tables | `cv2.applyColorMap(..., COLORMAP_TURBO)` | Perceptual maps already validated |
| Thread keep-latest loop | New async framework | Copy DetectionLoop | Proven in Phase 3 |
| Schema for depth kind | New string fields | Existing `DepthKind` / `DepthPayload` | FOUND-03 already enforced |
| Weight download/cache | Custom HTTP downloader | huggingface-hub + `HF_HOME` under SENTRY_MODEL_CACHE | Offline + resume + etag |
| Relative/metric honesty | Hope UI copy is careful | Pydantic validators + tests | Already reject `unit="m"` on relative |

**Key insight:** Phase 4 is **plumbing + honesty**, not a new depth algorithm. The hard product bugs are semantic (meters lies) and systems (latency, JSON size, CI downloads) — not reinventing DPT.

## What NOT to Build

| Item | Why not in Phase 4 |
|------|---------------------|
| Free-space / obstacles / morphology | Phase 5 Spatial Post |
| Full `/v1` WebSocket perception stream polish | Phase 5 |
| Stage toggles control plane (enable/disable depth live) | Phase 6 UI-03 (config at serve start OK) |
| TensorRT / ONNX depth export | Phase 7 |
| Stereo / multi-cam depth | Out of v1 monocular path |
| Full metric calibration UX / `metric_calibrated` pipeline | Deferred / v2; enum value reserved only |
| Grounding DINO / VLM scene chat | Out of scope |
| Binary depth wire protocol (PNG16 / msgpack) | Optional later; metadata + colormap sufficient for Phase 4 |
| Side-by-side dual video players | Optional; alpha blend is enough |
| Vendoring full Depth-Anything-V2 git repo | Prefer HF path |
| Default NC Base/Large weights | License policy |
| `depth_m` field on payloads | Explicitly forbidden by schema design |
| Second PerceptionStore process or Redis | Single-process keep-latest |

## Common Pitfalls

### Pitfall 1: Relative depth sold as meters
**What goes wrong:** UI or API shows `"m"` or names fields `depth_m` for relative maps; robots plan false distances.  
**Why it happens:** Colormaps look metric; HF pipeline returns pretty images.  
**How to avoid:** Always set `DepthKind` from **configured mode**, not from float range heuristics. Relative → `unit=None`. Existing validator + tests. UI badge exact: “Relative depth (not meters)”.  
**Warning signs:** Snapshot has `unit: "m"` with `kind: "relative"` (must fail validation).

### Pitfall 2: Full depth map in JSON
**What goes wrong:** Snapshot/status multi-MB; browser freezes; robot clients choke.  
**Why it happens:** Naïve `depth_map.tolist()` in Pydantic dump.  
**How to avoid:** Wire `DepthPayload` stays metadata-only (already designed Phase 1). Stats only: min/max/mean/shape. Keep ndarray in store for colormap.  
**Warning signs:** Snapshot response > ~50 KB with depth enabled.

### Pitfall 3: HF download in default CI
**What goes wrong:** Tests hang, fail offline, or hit rate limits.  
**Why it happens:** `from_pretrained` in fixture without mock.  
**How to avoid:** Injectable model/processor; never call hub in unit tests; optional marked integration test. Set `HF_HUB_OFFLINE=1` in CI job env for safety.  
**Warning signs:** pytest opens network; first-run CI 5+ minutes.

### Pitfall 4: BGR vs RGB silent quality loss
**What goes wrong:** Depth edges wrong / inverted channels.  
**Why it happens:** OpenCV frames are BGR; HF/PIL expect RGB.  
**How to avoid:** Explicit `cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)` in preprocess; golden test asserts channel swap called / RGB order on fixture.  
**Warning signs:** Depth looks “plausible but wrong” on color-coded objects.

### Pitfall 5: Metric indoor vs outdoor head mismatch
**What goes wrong:** Outdoor scene with indoor head saturates at ~20 m; indoor with outdoor head mis-scales.  
**Why it happens:** Domain-specific fine-tunes (Hypersim vs VKITTI).  
**How to avoid:** Explicit config `depth_mode: relative | metric_indoor | metric_outdoor`; document choice; default relative. UI label includes indoor/outdoor when metric.  
**Warning signs:** Everything “far” clamps; ground plane meters fail tape test.

### Pitfall 6: GPU contention with detection
**What goes wrong:** Depth + YOLO on same GPU → latency spikes, OOM on 8 GB.  
**Why it happens:** Two threads submit large models concurrently.  
**How to avoid:** Accept dual loops (architecture); document desktop VRAM; optional later serial lock. Prefer Small depth + nano/small YOLO. Count drops rather than queue.  
**Warning signs:** Both latencies climb together; CUDA OOM logs.

### Pitfall 7: NC weights as “quality upgrade” default
**What goes wrong:** Commercial makers inherit CC-BY-NC Base/Large.  
**How to avoid:** Allowlist only Small ids for default tier; profiles `depth_tier: small`; refuse Base/Large unless explicit research flag (not Phase 4 default).  
**Warning signs:** Auto-download of `…-Base-hf` without user intent.

### Pitfall 8: Snapshot 404 when only depth is ready
**What goes wrong:** Depth-only path returns 404 because snapshot still requires detection product.  
**How to avoid:** Snapshot builds from **either** product; completeness flags tell the truth.  
**Warning signs:** Depth colormap works but `/api/snapshot` 404s without detect extra.

## Code Examples

### Relative load + kind mapping
```python
# Source: HF model card + project DepthKind
MODE_TO_MODEL = {
    "relative": "depth-anything/Depth-Anything-V2-Small-hf",
    "metric_indoor": "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf",
    "metric_outdoor": "depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf",
}

def kind_for_mode(mode: str) -> tuple[DepthKind, str | None]:
    if mode == "relative":
        return DepthKind.RELATIVE, None
    if mode in ("metric_indoor", "metric_outdoor"):
        return DepthKind.METRIC_ESTIMATED, "m"
    raise ValueError(f"unknown depth_mode: {mode}")
```

### Preprocess golden strategy (no full model)
```python
# Pure functions — unit test without torch weights
def bgr_to_rgb_uint8(image_bgr: np.ndarray) -> np.ndarray:
    assert image_bgr.ndim == 3 and image_bgr.shape[2] == 3
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

def depth_stats(depth: np.ndarray) -> dict[str, float]:
    finite = depth[np.isfinite(depth)]
    return {
        "min": float(finite.min()) if finite.size else 0.0,
        "max": float(finite.max()) if finite.size else 0.0,
        "mean": float(finite.mean()) if finite.size else 0.0,
    }

# Fake model returns fixed HxW; mapping asserts kind/unit and shape match input frame
```

### Colormap empty / error path
```python
# MJPEG: if depth product is None or error set → draw RGB only (or "Depth: unavailable"
# is status-bar only; do not crash stream — UI-SPEC)
if depth_product is not None and depth_product.error is None and depth_product.depth_map is not None:
    image = blend_depth(image, depth_product.depth_map, alpha=0.45)
if det_product is not None:
    image = draw_detections(image, det_product.detections)
```

### Relative unit rejection (already exists — keep green)
```python
# tests/test_schemas_depth_kind.py — do not regress
DepthPayload(kind=DepthKind.RELATIVE, unit="m")  # must ValidationError
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| MiDaS relative only | Depth Anything V2 foundation + metric fine-tunes | 2024 (NeurIPS lineage) | Better detail; Small realtime |
| Manual clone + `.pth` | HF Transformers official support | 2024-07-06 | Maker-friendly load |
| Single “depth” float API | Typed `relative \| metric_estimated \| metric_calibrated` | Sentry Phase 1 | Honesty contract |
| Demo FPS marketing | Stage latency + keep-latest drops | Architecture research | Robot-usable timestamps |

**Deprecated/outdated for this phase:**
- MiDaS / ZoeDepth as default live path — superseded for maker stacks [CITED: STACK.md]
- Defaulting research NC large models for demos
- Putting depth arrays in JSON for v1 dashboard

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Metric Small HF weights are commercially OK (inherit Apache from relative Small); HF card license field currently empty | Standard Stack / License | If NC, optional metric must be research-only flag and docs update |
| A2 | Alpha-blend colormap is preferred UX over side-by-side for Phase 4 | Patterns / Discretion | Planner may choose toggle if user prefers UI-SPEC dual layout |
| A3 | Extending one PerceptionStore is better than a separate DepthStore | Architecture | Low — dual store still workable but more injection churn |
| A4 | `GET /api/snapshot` can return depth-only (no detections) with 200 | Snapshot policy | May need explicit product-presence rules if clients assume detections always present |
| A5 | Shared `resolve_device` extraction is optional (copy-paste OK) | Device | Duplication only |
| A6 | torch 2.13 + transformers 5.14 work together on makers’ machines | Stack | May need pin matrix if ABI issues; CI mocks avoid this |

**If metric license (A1) is wrong:** ship relative-only in Phase 4; gate metric behind research flag until license verified on model card / upstream LICENSE.

## Open Questions

1. **Metric Small commercial license confirmation**  
   - What we know: Relative Small is `apache-2.0` on HF; Base is `cc-by-nc-4.0`; metric Small card has no license field in API. Upstream README licenses Small vs Base/Large by scale.  
   - What's unclear: Explicit license tag for metric fine-tunes.  
   - **Recommendation:** Default relative only. Optional metric: document “verify license”; prefer treating metric Small as Apache-derived but add THIRD_PARTY row “check per weight” until confirmed. Do not block Phase 4 relative path.

2. **Snapshot `frame_id` when det and depth disagree**  
   - What we know: Phase 3 accepts RGB/det skew; snapshot uses det product frame_id.  
   - What's unclear: Multi-product identity for one PerceptionFrame.  
   - **Recommendation:** Use latest product by `t_capture` for top-level `frame_id`, include `det_frame_id` / `depth_frame_id` in stats; Phase 5 hardens merge timeout.

3. **Depth config API path**  
   - What we know: Detection uses `PATCH /api/detection/config`.  
   - What's unclear: Need runtime metric toggle in Phase 4 or serve-time only.  
   - **Recommendation:** Serve-time / profile config for `depth_mode` is enough for DEPTH-04; optional `GET/PATCH /api/depth/config` if low cost (mirror detection). Full stage toggle → Phase 6.

4. **HF vs native numerical golden tests**  
   - What we know: Authors warn OpenCV vs Pillow upsample differences.  
   - What's unclear: Whether makers care about bit-exact paper parity.  
   - **Recommendation:** Golden tests lock **preprocess + kind mapping + colormap**, not bit-exact DAV2 outputs. Optional integration fixture later.

5. **torch dependency when both detect and depth extras installed**  
   - What we know: detect pulls torch via ultralytics; depth needs torch too.  
   - **Recommendation:** List `torch` in `depth` extra explicitly so `uv sync --extra depth` works without detect.

## Environment Availability

| Dependency | Required By | Available (research host) | Version | Fallback |
|------------|------------|---------------------------|---------|----------|
| Python | runtime | ✓ | 3.14.6 (project targets 3.11+) | CI 3.11 |
| uv | install | ✓ | 0.11.23 | pip |
| pytest | tests | ✓ | 8.4.2 | — |
| torch | depth extra | ✗ on research host | — | mocks in unit tests; install extra on serve |
| transformers | depth extra | ✗ | — | mocks |
| opencv / numpy | colormap + frames | via project venv | project pins | core deps |
| CUDA GPU | realtime desktop | not required | — | CPU/MPS slower path |
| HF network | first weight download | env-dependent | — | offline after cache; CI never downloads |
| slopcheck | package audit | ✗ | — | human glance / ASSUMED tags |
| graph.json | graphify context | ✗ | — | skipped |

**Missing dependencies with no fallback:** none for planning — Phase 4 design assumes optional extra + mocks.

**Missing dependencies with fallback:** torch/transformers → injectable fakes for CI; real weights only for manual/GPU serve.

## Validation Architecture

> `workflow.nyquist_validation` is enabled (true) in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (dev extra) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=`tests` |
| Quick run command | `uv run pytest tests/test_depth_*.py tests/test_schemas_depth_kind.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DEPTH-01 | Worker returns depth map from frame via injectable model | unit | `uv run pytest tests/test_depth_worker.py -q` | ❌ Wave 0 |
| DEPTH-01 | DepthLoop reads bus, writes store, no camera I/O | unit | `uv run pytest tests/test_depth_loop.py -q` | ❌ Wave 0 |
| DEPTH-01 | Architecture: loop/worker source has no VideoCapture | unit | assert in loop tests | ❌ Wave 0 |
| DEPTH-02 | Snapshot includes `depth.kind` + completeness.depth | unit/ASGI | `uv run pytest tests/test_api_depth.py -q` | ❌ Wave 0 |
| DEPTH-02 | Relative `DepthPayload` rejects unit m | unit | `uv run pytest tests/test_schemas_depth_kind.py -q` | ✅ |
| DEPTH-03 | `colorize_depth` / blend pure OpenCV on synthetic map | unit | `uv run pytest tests/test_depth_colormap.py -q` | ❌ Wave 0 |
| DEPTH-03 | MJPEG path calls blend when depth product present | unit | `uv run pytest tests/test_api_preview.py -q` (extend) | ✅ extend |
| DEPTH-04 | Metric mode sets kind=metric_estimated unit=m; relative never m | unit | worker + schema tests | ❌ Wave 0 |
| DEPTH-04 | Status/UI fields never label relative as meters | unit | status merge tests | ❌ Wave 0 |
| MODEL-02 | HF cache root under SENTRY_MODEL_CACHE | unit | `uv run pytest tests/test_model_cache.py -q` (extend) | ✅ extend |
| FOUND-05 | THIRD_PARTY docs depth Apache default | unit | `uv run pytest tests/test_third_party_models_doc.py -q` | ✅ extend |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_depth_*.py tests/test_schemas_depth_kind.py -q`
- **Per wave merge:** `uv run pytest -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_depth_worker.py` — injectable model; kind/unit mapping; no HF download (DEPTH-01/04)
- [ ] `tests/test_depth_loop.py` — bus → store; drop gaps; error keeps thread (DEPTH-01)
- [ ] `tests/test_depth_preprocess.py` — BGR→RGB + stats pure (DEPTH-01 golden)
- [ ] `tests/test_depth_colormap.py` — TURBO colorize + blend; relative has no m labels in helper API (DEPTH-03)
- [ ] `tests/test_perception_store.py` — extend for `set_depth` / `snapshot_depth` isolation
- [ ] `tests/test_api_depth.py` or extend `test_api_detection.py` — snapshot completeness.depth + DepthPayload
- [ ] Extend `tests/test_api_preview.py` — status `depth_latency_ms` / `depth_kind`; MJPEG still 200 when depth empty
- [ ] Extend `tests/test_model_cache.py` — HF_HOME under SENTRY_MODEL_CACHE
- [ ] Extend `tests/test_cli_serve.py` — depth loop start when extra importable; degrade message when not
- [ ] Extend `tests/test_third_party_models_doc.py` — Phase 4 depth active wording
- [ ] Framework install: `uv sync --extra dev` (depth extra **not** required for unit tests)

**CI rule:** Default GitHub Actions must **not** set tokens that pull HF weights; unit tests inject fakes. Optional job `depth-integration` (manual/nightly) may download Small relative once with cache.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Localhost-first serve (MODEL-03); no new auth |
| V3 Session Management | no | — |
| V4 Access Control | partial | Default bind 127.0.0.1; warn on 0.0.0.0 (existing) |
| V5 Input Validation | yes | Pydantic `DepthPayload` / config enums; conf-style mode validation |
| V6 Cryptography | no | No new crypto; don't hand-roll |
| V10 Malicious Code | yes | Optional extras only; no untrusted model URLs — allowlisted HF ids |
| V14 Config | yes | `allow_cloud` remains false; depth local-only |

### Known Threat Patterns for monocular depth stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Supply-chain weight tampering | Tampering | Pin model id; prefer safetensors via HF; cache under known dir |
| Accidental NC license ship | Elevation / compliance | Default allowlist Small Apache only |
| Path traversal via model path | Tampering | Allowlist HF ids / known keys — no arbitrary local path in v1 |
| Unauthenticated LAN camera+depth exposure | Info disclosure | Localhost default; existing bind warning |
| Prompt/path injection in config | Tampering | Enum `depth_mode` only |
| Resource exhaustion (huge JSON depth) | Denial of service | Metadata-only wire payload |

## Project Constraints (from CLAUDE.md / repo)

No project-root `CLAUDE.md` / `AGENTS.md` found in workspace. Applicable constraints from shipped code + policy:

- Apache-2.0 application license; model weights separate (`THIRD_PARTY_MODELS.md`)
- `CORE_PATH_LOCAL_OSS_ONLY`; `DEFAULT_ALLOW_CLOUD = false`
- `DEFAULT_DEPTH_WEIGHT_KEY = "depth-anything-v2-small"`
- Workers never open cameras; handlers never run inference
- Ruff lint; pytest in `tests/`
- Optional heavy ML deps as extras (`detect` pattern)

## Recommended Discretion Resolutions (for planner)

| Discretion item | Recommendation | Confidence |
|-----------------|----------------|------------|
| HF vs native load | **HF transformers** Small-hf | HIGH |
| Store shape | **Extend PerceptionStore** with DepthProduct | HIGH |
| JSON depth | **Metadata + min/max/mean only** | HIGH |
| Colormap layout | **Alpha blend TURBO** on MJPEG | HIGH |
| optional-extra | **`depth` extra** (torch, transformers, hf-hub, pillow) | HIGH |
| Metric UX | Config `depth_mode`; default `relative`; indoor/outdoor explicit | HIGH |
| Runtime metric PATCH | Optional thin mirror of detection config; not required for DEPTH-04 | MEDIUM |

## Plan Shape Hint (not a plan)

Roadmap expects **2 plans**:

1. **04-01:** `depth` extra + cache HF + preprocess/mapping/worker + DepthLoop + store extension + golden unit tests (DEPTH-01 foundation)
2. **04-02:** snapshot DepthPayload + completeness, MJPEG colormap, status/UI kind+latency, optional metric mode labeling, serve lifecycle, docs (DEPTH-02/03/04)

## Sources

### Primary (HIGH confidence)
- [Depth Anything V2 GitHub README](https://github.com/DepthAnything/Depth-Anything-V2) — Small Apache vs Base/Large NC; native vs HF note; input size 518
- [Metric depth README](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth) — indoor max_depth 20 / outdoor 80; Small metric checkpoints
- [HF Depth-Anything-V2-Small-hf](https://huggingface.co/depth-anything/Depth-Anything-V2-Small-hf) — load snippets; license apache-2.0
- [HF transformers depth_anything_v2 docs](https://huggingface.co/docs/transformers/main/en/model_doc/depth_anything_v2) — AutoModel, relative vs metric config, post_process
- [HF Base-hf license](https://huggingface.co/depth-anything/Depth-Anything-V2-Base-hf) — cc-by-nc-4.0
- PyPI versions: transformers 5.14.1, huggingface-hub 1.27.0, torch 2.13.0, pillow 12.3.0 (curl pypi JSON 2026-08-07)
- In-repo: `schemas/perception.py`, `enums.py`, `validators.py`, `detection/loop.py`, `yolo_worker.py`, `cache.py`, `perception_store.py`, `routes_*`, `cli.py`, `policy/models.py`, `THIRD_PARTY_MODELS.md`, Phase 3 SUMMARYs / 03-RESEARCH.md
- `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS}.md`

### Secondary (MEDIUM confidence)
- Metric Indoor/Outdoor Small-hf model cards — usage; license field incomplete
- STACK.md depth section — transformers + DAV2 pairing

### Tertiary (LOW confidence)
- Exact metric Small license inheritance [ASSUMED]
- Combined YOLO+DAV2 VRAM budgets on specific GPUs [ASSUMED]

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — versions verified on PyPI; HF load path from official docs
- Architecture: **HIGH** — mirrors shipped Phase 3 patterns in-repo
- Pitfalls: **HIGH** — aligned with PITFALLS.md + schema already enforcing honesty
- Metric license for optional mode: **MEDIUM/LOW** — needs confirmation (A1)

**Research date:** 2026-08-07  
**Valid until:** ~2026-09-07 (transformers/torch move quickly; re-check versions at plan execute)

---

## RESEARCH COMPLETE

**Phase:** 4 - Monocular Depth  
**Confidence:** HIGH

### Key Findings
- Prefer **HF Transformers** `depth-anything/Depth-Anything-V2-Small-hf` (Apache-2.0) over vendoring native DAV2 for maker DX; metric indoor/outdoor Small heads optional with `metric_estimated` + `unit="m"`.
- Mirror Phase 3: **DepthLoop + injectable worker + extended PerceptionStore**; never infer in HTTP handlers; never open cameras in workers.
- Wire path: **DepthPayload metadata + stats only**; full float map stays in-process for **OpenCV TURBO alpha-blend** on MJPEG.
- Ship optional-extra **`depth`** (`torch`, `transformers>=4.45`, `huggingface-hub`, `pillow`); redirect **HF_HOME** under `SENTRY_MODEL_CACHE`; CI uses mocks (no HF download).
- Never default NC Base/Large; relative must never show meters; latency fields mirror `det_*` as `depth_latency_ms` / `depth_kind`.

### File Created
`.planning/phases/04-monocular-depth/04-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | PyPI + official HF/DAV2 docs |
| Architecture | HIGH | In-repo Phase 3 twin patterns |
| Pitfalls | HIGH | Schema + PITFALLS + load-path gotchas |

### Open Questions
- Metric Small commercial license confirmation (A1)
- Snapshot frame_id multi-product policy (recommend stats dual ids)
- Whether runtime PATCH for depth_mode is in 04-02 or serve-only

### Ready for Planning
Research complete. Planner can now create PLAN.md files.
