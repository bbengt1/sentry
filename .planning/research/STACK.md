# Stack Research

**Domain:** Camera-only robotics perception (monocular depth, fixed-class + open-vocab detection, realtime web UI, perception API)  
**Researched:** 2026-08-07  
**Confidence:** HIGH (versions verified on PyPI / official Ultralytics & ONNX Runtime docs; model selection grounded in 2025–2026 Ultralytics docs + Depth Anything V2 repo)

## Recommended Stack

### Core Runtime (prescriptive)

| Layer | Technology | Version (verified) | Purpose | Why |
|-------|------------|--------------------|---------|-----|
| Language | **Python** | **3.11** (3.12 OK desktop) | Perception backend | Dominant CV/ML ecosystem; Jetson/Pi wheels mature; async web + inference in one process |
| Web API | **FastAPI** | **0.141.x** | REST + WebSocket perception API | Async, OpenAPI free, first-class WebSockets, typed models via Pydantic |
| ASGI server | **Uvicorn** `[standard]` | **0.52.x** | Serve API + UI static | Production-ready, WebSocket-capable, simple deploy |
| Validation | **Pydantic** | **2.13.x** | API schemas / config | FastAPI native; strict perception message contracts |
| Array/math | **NumPy** | **2.x** (pin carefully on Jetson) | Tensors, depth maps | Universal; watch Jetson wheels that still need NumPy 1.x |
| Images | **OpenCV** `opencv-python-headless` | **4.10+ / 5.0.x** | Capture, decode, draw, free-space morph | Standard; headless for servers (no GUI deps) |
| Video I/O (advanced) | **PyAV** (`av`) | **18.x** | RTSP/file demux when OpenCV flaky | FFmpeg bindings; better network camera reliability |
| ML framework (dev) | **PyTorch** + **torchvision** | **2.13.x** / **0.28.x** | Train, prototype, export | Default for Ultralytics + Depth Anything |
| Detection suite | **Ultralytics** | **8.4.x** (≥8.4.33 for YOLO26 Jetson benches) | YOLO26 / YOLOE / export | One package: detect, open-vocab, export to ONNX/TRT/OpenVINO |
| Depth models | **Depth Anything V2** (HF Transformers or native weights) | V2 Small/Base + metric variants | Monocular depth | SOTA open monocular depth; Small is realtime-capable; metric heads for meters |
| HF tooling | **transformers** + **huggingface-hub** | **5.14.x** / **1.26.x** | Load Depth Anything V2 cleanly | Official `DepthAnythingV2` / `AutoModelForDepthEstimation` path |
| Annotation draw | **supervision** | **0.30.x** | Boxes, masks, labels on frames | Cleaner than hand-rolled OpenCV drawing |
| Tracking (optional v1.1) | **BoxMOT** or Ultralytics built-in track | **BoxMOT 22.x** | Temporal ID stability | Better robot “same object” continuity; not required for v1 depth+detect |
| Serialization | **orjson** | **3.11.x** | Fast JSON for WS API | Perception streams are high-frequency |

### Detection Models (fixed-class)

| Model | Default size | Role | Why this, not alternatives |
|-------|--------------|------|----------------------------|
| **YOLO26** (`yolo26n` / `yolo26s`) | n = edge, s = desktop default | Fixed-class COCO-style detection | **Current Ultralytics flagship** (2026): NMS-free end-to-end, DFL-free head, simpler export, strong Jetson TensorRT numbers (Orin Nano Super: TRT FP16 ~4.6 ms/im for n) |
| YOLO11 | fallback if YOLO26 regressions | Same tasks | Mature; still fully supported — use only if a specific export path breaks on YOLO26 |

**Size policy:**  
- Desktop GPU: `yolo26s` (or `m` if accuracy matters more than FPS)  
- Jetson Orin: `yolo26n` TensorRT FP16; `s` if headroom  
- Pi-class: `yolo26n` ONNX/OpenVINO INT8; expect low teens FPS at best  

**Do not default to RT-DETR** for maker robotics: transformer decoder is heavier, export/edge story weaker for hobby deploy, Ultralytics YOLO ecosystem is better for multi-format export.

### Open-Vocabulary Detection

| Model | Weights example | Role | Why |
|-------|-----------------|------|-----|
| **YOLOE** (primary) | `yoloe-11s-seg.pt` / YOLOE-26 when available | Promptable open-vocab detect (+ seg) | Ultralytics “Real-Time Seeing Anything”; text/image/prompt-free modes; docs claim **+3.5 AP vs YOLO-Worldv2 on LVIS** at realtime speeds |
| **YOLO-World** (fallback) | `yolov8s-world.pt` / `yolov8s-worldv2.pt` | Prompt set_classes open-vocab | Still documented; simpler class-list API; use if YOLOE export/edge path is immature for a target |

**Not for realtime core path:**  
- **Grounding DINO** — excellent zero-shot accuracy, too heavy for continuous edge FPS  
- **OWL-ViT / OWLv2** — research-quality, not maker realtime  
Use Grounding DINO only as an **offline labeling / rare-query** plugin, not the live stream detector.

### Monocular Depth

| Model | Variant | Role | Why |
|-------|---------|------|-----|
| **Depth Anything V2** | **Small (24.8M)** | Live depth @ camera rate | Best open realtime monocular depth foundation (NeurIPS 2024 lineage; still SOTA open baseline in 2026 maker stacks) |
| Depth Anything V2 | **Base (97.5M)** | Desktop quality mode | Better detail when GPU allows |
| Depth Anything V2 **Metric** | Indoor (Hypersim) / Outdoor (Virtual KITTI) Small/Base | Depth in **meters** for free-space | Relative depth alone is weak for obstacle distance; metric fine-tunes are the robotics-relevant path |
| Depth Anything V2 Large / Giant | deferred | Offline / research | Too slow for edge live pipeline |

**Deprioritize for v1 live path:**  
- **MiDaS** — superseded quality/detail by Depth Anything V2  
- **ZoeDepth** — metric pioneer but heavier and less maintained for edge export than DAV2 metric  
- Apple **Depth Pro** — quality high, not designed as multi-platform OSS edge realtime default  

**Free space / obstacles:** derive from metric (or relative + calibrated scale) depth via ground-plane / near-field thresholding + morphology (OpenCV) — do **not** require a second dense occupancy network in v1.

### Inference Backends (multi-target)

| Backend | When | Package / notes |
|---------|------|-----------------|
| **PyTorch CUDA** | Desktop development, model iteration | `torch` 2.13 + CUDA wheels from pytorch.org |
| **TensorRT** (`.engine`) | NVIDIA desktop **and Jetson production** | Ultralytics `model.export(format="engine", quantize=16)`; **highest Jetson FPS** per Ultralytics Jetson guide |
| **ONNX Runtime** | Portable intermediate + non-NVIDIA GPU/CPU | `onnxruntime` 1.28.x CPU; `onnxruntime-gpu` 1.28.x desktop CUDA; Jetson: **Jetson Zoo / JetPack-matched** ORT wheels (not generic PyPI GPU wheel) |
| **OpenVINO** | Intel NUC / some Pi-class CPU paths | Ultralytics `format="openvino"`; `openvino` 2026.3.x |
| **NCNN / MNN** | Extreme Pi/mobile experiments | Ultralytics export supported; secondary, higher friction |
| **CoreML** | Optional macOS/iOS hobby path only | Not a primary Sentry target |

**Backend selection policy (opinionated):**

```
Develop:     PyTorch (CUDA if available)
Export once: ONNX (portable artifact)
Deploy NVIDIA desktop/Jetson: TensorRT FP16 (INT8 after calibration)
Deploy CPU / Pi: ONNX Runtime or OpenVINO, nano models
Never ship: raw research checkpoints without an export path
```

**Critical Jetson constraint (HIGH confidence):** TensorRT engines are **device-architecture + TRT-version specific**. Build on the target Jetson (or validated same GPU/TRT), not on a desktop RTX and copy blindly.

### Camera Capture

| Source | Primary API | Fallback | Notes |
|--------|-------------|----------|-------|
| USB UVC | **OpenCV** `VideoCapture` (V4L2) | GStreamer pipeline string in OpenCV | Simple; pin resolution/FPS; MJPG over YUYV for bandwidth |
| RTSP / IP | OpenCV FFmpeg backend **or PyAV** | **GStreamer** `rtspsrc ! ... appsink` | OpenCV RTSP drops frames; GStreamer wins production reliability |
| File / synthetic | OpenCV / PyAV | — | Tests and demos |
| CSI (Jetson) | **GStreamer** `nvarguscamerasrc` / libcamera | OpenCV only if vendor pipeline documented | Prefer GStreamer on Jetson CSI |

**v1 recommendation:** Abstract a `CameraSource` interface with OpenCV implementation first; add GStreamer backend when RTSP/CSI reliability becomes the bottleneck. Do **not** start with a pure GStreamer graph — slower iteration for makers.

**Avoid as primary capture:** MediaPipe solutions camera helpers (product lock-in, limited robotics control).

### Realtime Web UI + Perception API

| Piece | Choice | Why |
|-------|--------|-----|
| API style | **FastAPI REST** (control, config, health) + **WebSocket** (perception stream) | REST for toggles/thresholds; WS for high-rate detections/depth metadata |
| Live video (v1) | **MJPEG** multipart (`multipart/x-mixed-replace`) **or** JPEG frames over WebSocket | Simplest browser path; works everywhere; good enough for developer dashboard |
| Live video (v1.5+) | **WebRTC** via **aiortc 1.15.x** | Lower latency, better multi-client; more complexity (ICE/codecs) — add when MJPEG lag hurts |
| Overlay protocol | JSON detections + optional PNG/JPEG depth preview; client-side canvas draw | Keep heavy drawing off GPU process when possible; send boxes as data |
| Frontend | **Vite 8.x + React 19.x + TypeScript** | Fast DX; canvas/SVG overlays; not Next.js (no SSR need for local dashboard) |
| Drawing | Canvas 2D (or **Konva 10.x** if interaction-heavy) | Boxes, free-space mask tint, depth colormap |
| Static serve | FastAPI `StaticFiles` from built `frontend/dist` | Single-port maker UX (`localhost:8000`) |

**API payload sketch (normative direction):**

```json
{
  "ts": 1720000000.123,
  "frame_id": 42,
  "detections": [{"cls": "person", "conf": 0.91, "xyxy": [10,20,100,200], "track_id": null}],
  "open_vocab": [{"label": "red cup", "conf": 0.67, "xyxy": [...]}],
  "depth": {"encoding": "png16", "scale_m": 0.001, "shape": [360,640]},
  "free_space": {"mask_rle": "...", "obstacle_nearest_m": 1.4}
}
```

Prefer **binary depth** (16-bit PNG or raw + msgpack) over base64 JSON for bandwidth.

### Packaging & Deploy

| Target | Packaging | Notes |
|--------|-----------|-------|
| Desktop dev | `uv` or `pip` + `pyproject.toml`; optional Docker CUDA image | Editable install; CUDA from pytorch.org index |
| Jetson | **L4T / JetPack-matched** container or venv; TensorRT system libs | Follow Ultralytics Jetson guide; install ORT from Jetson Zoo matrix |
| Pi-class | venv + ONNX Runtime CPU; optional Docker arm64 | Expect reduced model set; document FPS honestly |
| Models | Hugging Face cache / git-lfs / release assets | Download on first run; pin model SHAs in config |

**Container base images:**  
- Desktop: `nvidia/cuda:*-runtime-ubuntu22.04` (or 24.04 when torch wheels match)  
- Jetson: NVIDIA L4T base matching JetPack (do not use x86 CUDA images on device)

### Python vs Hybrid (decision)

**Use hybrid: Python perception backend + TypeScript web frontend.**

| Approach | Verdict |
|----------|---------|
| All-Python (Streamlit/Gradio) | **No** for product UI — poor overlay control, weak multi-client, not robot-API-first |
| All-JS (tfjs / onnxruntime-web) | **No** for core inference — model zoo, TensorRT, GStreamer, Jetson all Python/C++ native |
| Python + React (recommended) | **Yes** — standard for local robotics dashboards; single FastAPI process can host both |
| C++ core + thin Python | Later optimization only if profiling demands; not v1 |

---

## Supporting Libraries

| Library | Version | Purpose | When to use |
|---------|---------|---------|-------------|
| `python-multipart` | 0.0.32+ | Form/file uploads | Model/config upload endpoints |
| `websockets` | 17.x | WS stack (via uvicorn) | Perception stream |
| `httpx` | 0.28.x | Async HTTP client | Tests, IP camera APIs |
| `pyyaml` | 6.0.x | Human config | `sentry.yaml` profiles (desktop vs jetson vs pi) |
| `msgpack` | 1.2.x | Compact binary frames | Optional high-rate robot clients |
| `pillow` | 12.x | Image encode helpers | Depth PNG, thumbnails |
| `timm` / `einops` | as needed | Depth backbone deps | If using non-HF Depth Anything loaders |
| `lapx` / `scipy` | as needed | Tracking association | Only if enabling multi-object track |
| `aiortc` + `av` | 1.15 / 18.x | WebRTC path | Phase after MJPEG |
| `onnx` | 1.22.x | Export inspection | CI validate exported graphs |

**ROS2:** optional plugin later (`rclpy` on Humble/Jazzy/Lyrical). Keep core API **ROS-agnostic** WebSocket/REST first so non-ROS makers are first-class.

---

## Development Tools

| Tool | Purpose |
|------|---------|
| **uv** or pip-tools | Fast, reproducible envs |
| **ruff** | Lint + format Python |
| **pytest** + golden frames | Regression on detection/depth fixtures |
| **Vite** + **TypeScript** | Frontend build |
| **Docker Compose** | Optional: API + mock camera |
| **GitHub Actions** | Lint, unit tests, export smoke (CPU ONNX) |
| **TensorBoard / simple FPS HUD** | Perf while developing — not a product dependency |

---

## Installation (example)

### Desktop GPU (CUDA) — development

```bash
# Python 3.11 recommended
uv venv --python 3.11
source .venv/bin/activate

# PyTorch CUDA (verify index URL against https://pytorch.org/get-started/locally/)
uv pip install torch torchvision --index-url https://download.pytorch.org/whl/cu128

uv pip install \
  ultralytics==8.4.115 \
  fastapi==0.141.1 \
  "uvicorn[standard]==0.52.1" \
  pydantic==2.13.4 \
  opencv-python-headless==4.10.0.84 \
  numpy \
  supervision==0.30.0 \
  transformers==5.14.1 \
  huggingface-hub==1.26.1 \
  onnxruntime-gpu==1.28.0 \
  onnx==1.22.0 \
  orjson==3.11.9 \
  pyyaml==6.0.3 \
  httpx==0.28.1 \
  pillow==12.3.0

# Optional WebRTC later
# uv pip install aiortc==1.15.0 av==18.0.0
```

### Export models for edge

```python
from ultralytics import YOLO

det = YOLO("yolo26n.pt")
det.export(format="onnx", imgsz=640, simplify=True)          # portable
det.export(format="engine", imgsz=640, quantize=16, device=0)  # NVIDIA TensorRT FP16

# Open-vocab (YOLOE) — confirm export support per weight; keep PyTorch path if export incomplete
ov = YOLO("yoloe-11s-seg.pt")
# ov.export(format="onnx", imgsz=640)
```

### Jetson (conceptual)

```bash
# On device, JetPack-matched PyTorch + system TensorRT
pip install ultralytics opencv-python-headless fastapi "uvicorn[standard]" ...
# Install onnxruntime-gpu from Jetson Zoo matching JetPack/Python — NOT desktop PyPI GPU wheel
# Build TensorRT engines ON DEVICE:
yolo export model=yolo26n.pt format=engine quantize=16 device=0
```

### Raspberry Pi-class (conceptual)

```bash
pip install ultralytics onnxruntime opencv-python-headless fastapi "uvicorn[standard]" ...
# Prefer yolo26n.onnx + Depth Anything V2 Small at reduced imgsz (e.g. 308–518)
# Skip open-vocab or run on-demand only
```

### Frontend

```bash
cd frontend
npm create vite@latest . -- --template react-ts
npm install
# canvas overlays: no heavy 3D required for v1
npm run build   # output to backend static/
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why not default |
|----------|-------------|-------------|-----------------|
| Fixed detect | YOLO26 | YOLO11 / YOLOv8 | Older generation; still OK fallback |
| Fixed detect | YOLO26 | RT-DETR | Heavier; weaker maker export ergonomics |
| Open-vocab | YOLOE | YOLO-World | World still fine; YOLOE is current Ultralytics realtime OV push |
| Open-vocab | YOLOE | Grounding DINO | Accuracy ↑, realtime/edge ↓ |
| Depth | Depth Anything V2 | MiDaS / ZoeDepth | Superseded quality or worse edge story |
| Depth | DAV2 Metric | Stereo/SGBM only | Stereo optional later; monocular is product thesis |
| Capture | OpenCV → GStreamer | pure GStreamer first | Slower DX for makers |
| API | FastAPI | Flask / Django | Weaker async/WS story |
| API | FastAPI | pure ROS2 | Excludes non-ROS makers; add as plugin |
| Video UI | MJPEG/WS → WebRTC | WebRTC-only day one | ICE/NAT complexity before product value |
| Frontend | Vite+React | Streamlit/Gradio | Not a serious overlay/control surface |
| Frontend | Vite+React | Next.js | Unnecessary SSR for localhost tool |
| Edge NVIDIA | TensorRT | ONNX Runtime TensorRT EP only | Native Ultralytics `.engine` is simpler & documented for Jetson |
| Pi | ORT/OpenVINO | TensorFlow Lite-first | Secondary ecosystem for this model zoo |
| Tracking | none / BoxMOT later | DeepSORT-only custom | Reinventing association poorly |

---

## What NOT to Use

| Avoid | Why |
|-------|-----|
| **Cloud-only APIs** (Roboflow hosted, GPT-4V as core) | Violates local OSS requirement; latency/privacy |
| **LiDAR/radar SDKs as required deps** | Product is camera-only |
| **MediaPipe as core perception** | Limited depth/open-vocab; Google pipeline lock-in |
| **Detectron2 / MMDetection as runtime** | Research training stacks; heavy deploy footprint |
| **TensorFlow as primary training/inference** | Model zoo and Ultralytics path are PyTorch-first |
| **Grounding DINO / SAM-2 on every frame (edge)** | Great plugins; destroy FPS if always-on |
| **Full SLAM (ORB-SLAM, RTAB-Map) in v1** | Out of scope; depth+obstacles only |
| **Kafka/Redis as required bus** | Overkill for single-process maker robot; optional later |
| **Electron desktop shell** | Browser to `localhost` is enough |
| **Copying TensorRT engines across GPU architectures** | Silent wrong results / load failures |
| **Ultralytics AGPL surprises without license review** | Ultralytics is AGPL-3.0 — acceptable for many OSS apps; **commercial closed forks need a license plan**. Document this for contributors. |

---

## Stack Patterns by Variant

### Desktop NVIDIA GPU (primary development)

```
Camera (USB/RTSP) → OpenCV/PyAV
    → YOLO26s (PyTorch or TRT) + YOLOE (PyTorch)
    → Depth Anything V2 Base or Small (PyTorch / TensorRT if exported)
    → Free-space postprocess (NumPy/OpenCV)
    → FastAPI: REST controls + WS perception + MJPEG preview
    → Vite React dashboard
```

- Target: 20–30+ FPS pipeline with overlays  
- Use full-precision or FP16; iterate models in PyTorch  

### NVIDIA Jetson (Orin Nano / Orin / AGX)

```
CSI/USB/RTSP → GStreamer preferred for CSI/RTSP
    → YOLO26n TensorRT FP16 (INT8 after calib)
    → Depth Anything V2 Small (TensorRT or ORT)
    → YOLOE on-demand or every Nth frame (budget GPU)
    → FastAPI on device; dashboard over LAN
```

- Pin JetPack, CUDA, TensorRT, PyTorch builds together  
- Build engines on device  
- Ultralytics reference: Orin Nano Super YOLO26n TRT FP16 ~4.6 ms (infer only)  

### Raspberry Pi-class / CPU edge

```
USB camera → OpenCV
    → YOLO26n ONNX Runtime or OpenVINO INT8
    → Depth Anything V2 Small @ reduced resolution, every 2nd–3rd frame
    → Open-vocab: off by default or cloud-optional (not required)
    → FastAPI; expect 5–15 FPS combined depending on Pi 5 + accelerator
```

- Honest product messaging: “spatial awareness lite”  
- Coral/NPU plugins later — not v1 requirement  
- Prefer headless OpenCV; watch thermal throttling  

### Shared abstraction (required for multi-target)

```python
# Conceptual — implement behind interfaces
class Detector(Protocol):
    def predict(self, frame_bgr) -> list[Detection]: ...

class DepthEstimator(Protocol):
    def predict(self, frame_bgr) -> DepthMap: ...  # metric meters if available

class InferenceBackend(Protocol):
    # pytorch | onnxruntime | tensorrt | openvino
    ...
```

Config profile selects weights + backend:

```yaml
profile: jetson-orin
detector: { model: yolo26n, backend: tensorrt, precision: fp16 }
open_vocab: { model: yoloe-11s, backend: pytorch, every_n: 3 }
depth: { model: depth-anything-v2-small-metric-indoor, backend: tensorrt, imgsz: 518 }
camera: { type: gstreamer, pipeline: "..." }
```

---

## Version Compatibility

| Component | Desktop | Jetson | Pi |
|-----------|---------|--------|-----|
| Python | 3.11–3.12 | 3.10–3.11 (JetPack-dependent) | 3.11 |
| PyTorch | 2.13 + CUDA wheel | JetPack-matched wheel / NVIDIA wheel | CPU torch only if needed; prefer ORT |
| Ultralytics | 8.4.x | 8.4.x | 8.4.x |
| ONNX Runtime | 1.28.x PyPI | Jetson Zoo build for JetPack | 1.28.x CPU PyPI |
| TensorRT | Host TRT with CUDA | **System TensorRT from JetPack** | N/A |
| OpenCV | 4.10+ / 5.x | 4.x headless often safer | 4.x |
| NumPy | 2.x | May need 1.26.x if older wheels | 1.26 or 2.x per wheel |
| Node (frontend) | 20 or 22 LTS | build on desktop; serve static | same |

**Pin strategy:** lock `ultralytics`, `torch`, `onnxruntime*`, `transformers` in `uv.lock` / `requirements.lock`. Re-benchmark Jetson after any Ultralytics minor bump (export graphs change).

---

## Confidence Assessment

| Area | Level | Notes |
|------|-------|-------|
| Python + FastAPI + React hybrid | **HIGH** | Standard local robotics/dev-tool pattern; versions on PyPI 2026-08-07 |
| YOLO26 as fixed-class default | **HIGH** | Official Ultralytics current gen; Jetson benches in docs (8.4.32–8.4.33) |
| YOLOE as open-vocab default | **HIGH** for desktop; **MEDIUM** for TensorRT edge export maturity | Prefer PyTorch/ONNX first on edge; verify export per weight |
| YOLO-World as fallback | **HIGH** | Stable Ultralytics API (`set_classes`) |
| Depth Anything V2 (+ metric) | **HIGH** | Official repo + HF Transformers integration |
| TensorRT on Jetson | **HIGH** | Ultralytics Jetson guide; engine device-specificity well documented |
| OpenCV-first capture | **HIGH** | Maker DX; GStreamer as upgrade path |
| MJPEG/WS before WebRTC | **HIGH** | Latency vs complexity tradeoff for v1 dashboard |
| Pi realtime dual-model | **MEDIUM** | Feasible with nano + frame-skip; FPS varies widely by board |
| Exact CUDA index (`cu128` etc.) | **MEDIUM** | Must re-check pytorch.org at install time |
| Ultralytics AGPL implications | **HIGH** (legal awareness) | Not a technical blocker for OSS; plan for commercial use |

---

## Sources

- Ultralytics YOLO26: https://docs.ultralytics.com/models/yolo26/  
- Ultralytics YOLOE: https://docs.ultralytics.com/models/yoloe/  
- Ultralytics YOLO-World: https://docs.ultralytics.com/models/yolo-world/  
- Ultralytics Export: https://docs.ultralytics.com/modes/export/  
- Ultralytics Jetson guide (YOLO26 / TensorRT benches): https://docs.ultralytics.com/guides/nvidia-jetson/  
- Depth Anything V2: https://github.com/DepthAnything/Depth-Anything-V2  
- Depth Anything V2 metric models: https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth  
- HF Transformers Depth Anything V2: https://huggingface.co/docs/transformers/en/model_doc/depth_anything_v2  
- ONNX Runtime Execution Providers: https://onnxruntime.ai/docs/execution-providers/  
- FastAPI WebSockets: https://fastapi.tiangolo.com/advanced/websockets/  
- aiortc: https://aiortc.readthedocs.io/  
- PyPI versions checked 2026-08-07: ultralytics 8.4.115, fastapi 0.141.1, torch 2.13.0, onnxruntime 1.28.0, transformers 5.14.1, openvino 2026.3.0, supervision 0.30.0, aiortc 1.15.0  

---

## Opinionated Defaults for Sentry AI v1

Ship these as the **default profile** unless a board forces otherwise:

1. **Python 3.11 + FastAPI + Uvicorn**  
2. **YOLO26s** desktop / **YOLO26n** edge — fixed classes  
3. **YOLOE** for open-vocab queries (toggle; not always-on on Pi)  
4. **Depth Anything V2 Small** (+ indoor metric weights for indoor robots)  
5. **PyTorch** dev → **ONNX** portable → **TensorRT FP16** NVIDIA deploy  
6. **OpenCV** capture; GStreamer when RTSP/CSI hurts  
7. **WebSocket perception stream + MJPEG preview**; Vite/React canvas overlays  
8. **Single process**, plugin interfaces for ROS2 / multi-cam / WebRTC later  

That stack matches the 2025–2026 open-source camera perception ecosystem, maximizes Jetson performance without abandoning Pi, and keeps the maker install path realistic.
