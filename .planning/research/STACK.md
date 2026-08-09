# Technology Stack — v0.2 Edge Runtime

**Project:** Sentry AI  
**Milestone:** v0.2 Edge Runtime (live ORT + TRT for fixed-class YOLO only)  
**Researched:** 2026-08-09  
**Scope:** Stack **additions** for live ONNX Runtime and TensorRT inference. Depth and YOLOE stay on existing PyTorch paths this milestone.  
**Overall confidence:** HIGH for package names/versions and Ultralytics native load path; MEDIUM for exact JetPack↔Python wheel pins (device-specific; verify on board).

---

## Decision (one-liner)

**Keep Ultralytics `YOLO(weights)` + `predict()` for live ORT/TRT; add optional `onnx` extra (`onnxruntime`); never add a project `tensorrt` pip extra — use system / JetPack TensorRT and load `.engine` via Ultralytics.**

---

## Recommended Stack Additions

### Core (unchanged from v1.0)

| Technology | Version | Role | Notes |
|------------|---------|------|-------|
| Python | **3.11** (`requires-python >=3.11`) | Runtime | [VERIFIED] `pyproject.toml` |
| `ultralytics-opencv-headless` | **≥8.4.33,<9** (locked **8.4.116** in env) | Fixed-class YOLO + export/predict for `.pt`/`.onnx`/`.engine` | [VERIFIED] installed package + PyPI |
| `detect` extra | existing | Required for any live YOLO path | ORT/TRT still go through Ultralytics |

### New / explicit for live edge backends

| Technology | Version pin | Purpose | Why |
|------------|-------------|---------|-----|
| **`onnxruntime`** | **`>=1.20,<1.29`** (prefer **1.28.x**) | Live CPU ONNX for `preferred_backend=onnxruntime` | [VERIFIED] PyPI `onnxruntime==1.28.0`, `requires_python>=3.11`; Ultralytics export-base for py≥3.11 wants `onnxruntime>=1.20.0` |
| **`onnxruntime-gpu`** | **same band 1.20–1.28** (prefer **1.28.x**) | Optional desktop CUDA ORT | [VERIFIED] PyPI `onnxruntime-gpu==1.28.0`; **x86_64 Linux + win_amd64 only** — **no aarch64 Jetson wheels on PyPI** [CITED] Ultralytics Jetson guide + ORT install table |
| **System TensorRT** (JetPack / NVIDIA host) | Match host JetPack/CUDA | Deserialize Ultralytics `.engine` | [VERIFIED] project docs already ban `tensorrt` pip extra; Ultralytics `TensorRTBackend` does `import tensorrt as trt` |
| **Ultralytics AutoBackend** | via `detect` extra | `*.onnx` → `ONNXBackend`, `*.engine` → `TensorRTBackend` | [VERIFIED] `ultralytics/nn/autobackend.py` + `nn/backends/onnx.py` / `tensorrt.py` |

### Not packages — artifacts and policy

| Artifact / policy | Version / rule | Purpose |
|-------------------|----------------|---------|
| Fixed-class ONNX | `yolo26n.onnx` / `yolo26s.onnx` (imgsz=640, simplify) | Portable live graph for ORT |
| Fixed-class TensorRT engine | `yolo26n.engine` / `yolo26s.engine` built **on device** | Live TRT path |
| Profile `preferred_backend` | `torch` \| `onnxruntime` \| `tensorrt` \| `cpu` | Selects loader + weight suffix |
| Depth / YOLOE | **no new stack** this milestone | Stay PyTorch/HF + PyTorch Ultralytics |

---

## 1. Recommended packages (detail)

### ONNX Runtime — CPU (default portable live path)

```text
onnxruntime>=1.20,<1.29   # pin resolved to 1.28.x when locking
```

| Claim | Tag | Evidence |
|-------|-----|----------|
| Latest stable is 1.28.0 | [VERIFIED] | PyPI JSON 2026-08-09 |
| Supports Python 3.11 | [VERIFIED] | `requires_python>=3.11`; wheels `cp311` manylinux x86_64 **and** aarch64, macOS arm64, win |
| Import name | [VERIFIED] | `import onnxruntime` |
| Fits `cpu-fallback` profile | [ASSUMED] product mapping | Profile already sets `preferred_backend: onnxruntime` |

**Install (makers / CI):**

```bash
uv sync --extra dev --extra detect --extra onnx
```

### ONNX Runtime — GPU (desktop CUDA only)

```text
onnxruntime-gpu>=1.20,<1.29   # 1.28.x; CUDA 12.x default since ORT 1.19
```

| Claim | Tag | Evidence |
|-------|-----|----------|
| PyPI GPU package default CUDA 12.x since 1.19.0 | [CITED] | https://onnxruntime.ai/docs/install/ |
| 1.28.0 extras pull CUDA 13 nvidia-* packages when using `[cuda,cudnn]` | [VERIFIED] | PyPI `requires_dist` on `onnxruntime-gpu==1.28.0` |
| **Do not** install desktop `onnxruntime-gpu` on Jetson | [CITED] | Ultralytics Jetson guide: PyPI has no Jetson aarch64 GPU wheels |
| Mutually exclusive with `onnxruntime` in one env | [ASSUMED] common ORT practice | Same top-level module; document “pick one” |

**Install (desktop CUDA ORT):**

```bash
# Prefer documenting as manual / environment-specific, not a co-installed extra with CPU ORT:
uv pip install "onnxruntime-gpu>=1.20,<1.29"
# Optional CUDA/cuDNN wheels (when system CUDA missing):
# uv pip install "onnxruntime-gpu[cuda,cudnn]>=1.20,<1.29"
```

Ultralytics `ONNXBackend` already selects providers: CUDA EP if CUDA device + provider present, else CoreML on MPS, else CPU. [VERIFIED] `ultralytics/nn/backends/onnx.py`.

### ONNX Runtime — Jetson

| Rule | Detail | Tag |
|------|--------|-----|
| Use **JetPack-matched** `onnxruntime-gpu` wheel (Jetson Zoo / Ultralytics assets), **not** generic PyPI GPU wheel | aarch64 + JetPack CUDA ABI | [CITED] Ultralytics nvidia-jetson guide; ORT install table “TensorRT (Jetson): Jetson Zoo” |
| Example pins (illustrative — verify on device) | JP6 + py3.10: `onnxruntime_gpu-1.23.0-cp310-...`; JP7.2 + py3.12: `1.24.0-cp312-...` | [CITED] Ultralytics guide (wheel URLs change; do not hardcode into Sentry lockfile as universal) |
| Python on Jetson may be **3.10 / 3.12**, not 3.11 | JetPack image dependent | [CITED] Ultralytics guide tables |
| Sentry product Python target remains **3.11** on desktop; Jetson docs must say “match board Python” | Packaging honesty | [ASSUMED] product policy |

**Do not** put Jetson-specific wheel URLs into `pyproject.toml` extras — document install in `docs/export/jetson-packaging.md`.

### TensorRT Python bindings / JetPack matrix

| Platform | How to get `import tensorrt` | Tag |
|----------|------------------------------|-----|
| **Jetson** | JetPack-bundled TensorRT (`sudo apt install nvidia-jetpack` / system `tensorrt` packages). **No** project pip extra. | [VERIFIED] existing Sentry export docs; [CITED] Ultralytics Jetson guide |
| **Desktop NVIDIA** | System TensorRT **or** Ultralytics auto-`check_tensorrt()` which installs `tensorrt-cu{N}` from PyPI (`N` = major of `torch.version.cuda`) | [VERIFIED] `ultralytics/utils/checks.py` `check_tensorrt` |
| PyPI metapackage `tensorrt==11.2.1.2` | Depends on `tensorrt_cu13==11.2.1.2` — CUDA 13 oriented; wrong for many JetPack 6 (TRT 10.x) hosts | [VERIFIED] PyPI metadata |
| Ultralytics TRT version constraints | `>=7.0.0`, **reject `10.2.0`** | [VERIFIED] `TensorRTBackend` + `check_tensorrt` |
| Engines non-portable | Build on **same GPU arch + TRT/JetPack** as serve; never copy desktop→Jetson or cross-SKU | [VERIFIED] project `docs/export/yolo26-onnx-tensorrt.md` + Ultralytics warning |

**JetPack orientation (verify on device — do not treat as lockfile pins):**

| JetPack family | Typical TRT lineage | Live path note |
|----------------|---------------------|----------------|
| JetPack 5.x | TRT 8.x era | Older; still `YOLO("*.engine")` if TRT≥7 |
| JetPack 6.x | TRT 10.x (e.g. 10.3 / 10.7+) | Preferred Orin path; INT8 end2end caveats on 10.3 | [CITED] Ultralytics Jetson FAQ |
| JetPack 7.x | TRT 11.x + CUDA 13 torch wheels | Strongly-typed TRT; DLA unsupported in TRT 11.0 | [CITED] Ultralytics TensorRT/Jetson docs |

**Sentry policy (opinionated, continues v1.0):**

- **Do not** declare `tensorrt`, `tensorrt-cu12`, `tensorrt-cu13`, `nvidia-tensorrt`, or `torch-tensorrt` in `pyproject.toml` extras.
- Document: “system TensorRT must be importable where `preferred_backend=tensorrt`.”
- Export remains `scripts/export/export_yolo.py` + Ultralytics `format=engine` on the target machine.

---

## 2. Ultralytics native ORT/engine path vs custom ORT session

### Recommendation: **Native Ultralytics path** for v0.2

```python
from ultralytics import YOLO

# After export (offline):
# YOLO("yolo26n.pt").export(format="onnx", imgsz=640, simplify=True)
# YOLO("yolo26n.pt").export(format="engine", imgsz=640, quantize=16, device=0)

model = YOLO("yolo26n.onnx")     # → AutoBackend format=onnx → ONNXBackend (onnxruntime)
# or
model = YOLO("yolo26n.engine")   # → AutoBackend format=engine → TensorRTBackend (tensorrt)

results = model.predict(source=image_bgr, conf=0.25, imgsz=640, device=device, verbose=False)
```

[VERIFIED] Ultralytics docs/examples: load `.onnx` / `.engine` with `YOLO(...)` then `predict`.  
[VERIFIED] AutoBackend map: `"onnx": ONNXBackend`, `"engine": TensorRTBackend`.

### Why not a custom `onnxruntime.InferenceSession` this milestone

| Custom ORT session | Native Ultralytics |
|--------------------|--------------------|
| Must reimplement letterbox / color / normalize | Done inside Ultralytics |
| Must decode YOLO26 end-to-end outputs (or NMS graphs) | Done; Results API stable |
| Must carry class `names` metadata | Embedded in Ultralytics export metadata |
| Breaks existing `results_to_detections(results[0])` | [VERIFIED] mapper expects Results-like `.boxes` |
| Duplicates IO-binding / EP selection | ONNXBackend already selects CUDA/CoreML/CPU |
| Only wins if stripping Ultralytics/torch entirely | **Out of scope** — TRT backend still uses `torch` CUDA tensors [VERIFIED] `tensorrt.py` |

**Custom ORT is an anti-pattern for v0.2** except:

- Isolated unit tests that mock session I/O without Ultralytics, or  
- A future “slim CPU binary” milestone that deliberately drops Ultralytics (not this one).

### Minimal worker change shape (stack implication, not implementation)

Keep `YoloDetectionWorker` on Ultralytics; resolve weights path from `preferred_backend`:

| `preferred_backend` | Weight suffix / file | Runtime deps |
|---------------------|----------------------|--------------|
| `torch` / `cpu` | `.pt` | `detect` (+ torch via ultralytics) |
| `onnxruntime` | `.onnx` | `detect` + `onnx` extra (`onnxruntime` or gpu wheel) |
| `tensorrt` | `.engine` | `detect` + system `tensorrt` + CUDA torch |

Honest fallback when artifact missing: clear error **or** documented torch `.pt` fallback — product decision, but stack must not pretend ORT/TRT without files.

**Depth / YOLOE:** no `.onnx`/`.engine` live loaders this milestone. [ASSUMED] milestone scope from `PROJECT.md`.

---

## 3. Version pins + optional extras layout

### Compatible with Python 3.11

| Package | Pin | Py3.11 | Notes |
|---------|-----|--------|-------|
| `onnxruntime` | `>=1.20,<1.29` | Yes | 1.28.0 requires ≥3.11 |
| `onnxruntime-gpu` | `>=1.20,<1.29` | Yes (x86_64/win) | Not for Jetson aarch64 PyPI |
| `ultralytics-opencv-headless` | `>=8.4.33,<9` | Yes | Already in `detect` |
| `tensorrt` (pip) | **not pinned in project** | N/A | System / optional Ultralytics install only |
| `numpy` | existing core `<2.5` | Yes | Jetson JP5 may need older NumPy — document, don’t break desktop |

### Opinionated `pyproject.toml` extras (v0.2)

```toml
[project.optional-dependencies]
# existing
detect = [
  "ultralytics-opencv-headless>=8.4.33,<9",
]
depth = [
  "torch>=2.2,<3",
  "transformers>=4.45,<6",
  "huggingface-hub>=0.23,<2",
  "pillow>=10,<13",
]
dev = [
  "pytest>=8",
  "ruff>=0.8",
  "httpx>=0.28",
]

# NEW — live ONNX Runtime (CPU). Requires detect for Ultralytics predict path.
onnx = [
  "onnxruntime>=1.20,<1.29",
]

# Intentionally OMITTED:
# - tensorrt / tensorrt-cu12 / tensorrt-cu13  (system / JetPack only)
# - onnxruntime-gpu as a co-extra with onnx (module clash; platform-specific)
# - onnx / onnxslim as runtime deps (export-only; optional maker tools)
# - openvino, torch-tensorrt, tensorrt lean/dispatch metapackages
```

### Install matrix

| Target | Command | Live detector backend |
|--------|---------|------------------------|
| CI / CPU fallback | `uv sync --extra dev --extra detect --extra onnx` | ORT CPU + `yolo26n.onnx` (or torch fallback) |
| Desktop GPU dev (torch) | `uv sync --extra dev --extra detect --extra depth` | `.pt` CUDA/MPS (unchanged) |
| Desktop ORT CUDA | detect + **replace** ORT with `onnxruntime-gpu` manually | `.onnx` + CUDA EP |
| Desktop TRT | detect + system/desktop TensorRT + CUDA torch | `.engine` via Ultralytics |
| Jetson TRT | detect + JetPack TRT + JetPack-matched torch | `.engine` on-device |
| Jetson ORT GPU | detect + Jetson Zoo / assets `onnxruntime-gpu` wheel | `.onnx` |

### Locking strategy

- Lock **`onnxruntime`** in `uv.lock` via the `onnx` extra (CI-reproducible).
- **Do not** lock Jetson GPU ORT wheels or TensorRT into the universal lockfile.
- Re-benchmark after Ultralytics minor bumps (export graph / AutoBackend changes).

---

## 4. What NOT to add

| Dependency / feature | Why avoid in v0.2 |
|----------------------|-------------------|
| **`tensorrt` pip extra in pyproject** | Breaks Jetson (system TRT); wrong CUDA major on many desktops; conflicts with project EDGE-03 policy already shipped |
| **`nvidia-tensorrt` (PyPI 99.0 redirect)** | Noise metapackage; not a real pin strategy |
| **`torch-tensorrt`** | Different product (FX/Dynamo compile); not Ultralytics `.engine` path |
| **Custom C++ ORT/TRT extension modules** | Unnecessary vs Ultralytics backends |
| **`onnx` + `onnxslim` as serve runtime deps** | Export/validation only; Ultralytics pulls as needed for export |
| **`onnxruntime-directml` / QNN / OpenVINO extras** | Out of milestone; OpenVINO remains advisory enum only |
| **Live ORT/TRT for Depth Anything V2** | Explicitly deferred |
| **Live ORT/TRT for YOLOE** | Explicitly deferred; OV stays PyTorch on-demand |
| **Prebuilt multi-SKU `.engine` in wheel/repo** | Non-portable; already forbidden |
| **Second detector stack (OpenCV DNN-only, TensorFlow, TFLite)** | Diverges from Ultralytics Results mapping |
| **Triton Inference Server as required runtime** | Optional later deploy; not maker one-process serve |
| **Forcing `onnxruntime-gpu` in default `onnx` extra** | Breaks CPU CI / macOS / Jetson; EP selection is environment-specific |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why not |
|----------|-------------|-------------|---------|
| Live ORT integration | Ultralytics `YOLO("*.onnx")` | Hand-rolled `InferenceSession` + custom decode | Loses Results mapping, metadata, preprocess; high rewrite risk |
| Live TRT integration | Ultralytics `YOLO("*.engine")` | ORT TensorRT EP only | Native `.engine` is Ultralytics/Jetson documented SOTA path; avoids dual TRT stacks |
| ORT CPU package | `onnxruntime` extra | Always install `onnxruntime-gpu` | No GPU on CI/mac; Jetson needs different wheel |
| TRT Python | System / JetPack | Pin `tensorrt==11.2.1.2` in extras | CUDA 13 metapackage; wrong for JP6; prior project ban |
| Engine build | On-device Ultralytics export | Ship engines in GitHub Releases | Arch/TRT-specific; silent load failures |
| Backend abstraction | Thin selection over Ultralytics load | Full custom `InferenceBackend.infer` tensor API first | Protocol stub exists; v0.2 value is **live detect**, not re-plumbing every tensor |

---

## Installation (v0.2 target)

### CPU / CI (live ORT)

```bash
uv sync --extra dev --extra detect --extra onnx
# Export once (or CI fixture path):
uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx --imgsz 640
# Serve with profile that prefers ORT (cpu-fallback already declares it):
uv run sentry serve --profile cpu-fallback --source synthetic
```

### Desktop torch (unchanged primary maker path)

```bash
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --profile desktop-gpu --source usb --device 0
```

### Desktop TensorRT (lab)

```bash
uv sync --extra dev --extra detect
# Ensure system TensorRT or allow Ultralytics to install tensorrt-cu* matching torch CUDA
uv run python scripts/export/export_yolo.py --weights yolo26s.pt --format engine --imgsz 640 --device 0
# preferred_backend=tensorrt + path to yolo26s.engine (product wiring in milestone plans)
```

### Jetson (on device)

```bash
# JetPack TensorRT already present — do NOT pip install tensorrt from PyPI for production Jetson
uv sync --extra detect
# Optional: JetPack-matched onnxruntime-gpu wheel from Jetson Zoo / Ultralytics assets (not PyPI)
uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format engine --imgsz 640 --device 0
uv run sentry serve --profile jetson --source usb --device 0 --no-ui
```

---

## Confidence Assessment

| Area | Level | Notes |
|------|-------|-------|
| `onnxruntime` / `onnxruntime-gpu` 1.28 + py3.11 | **HIGH** | PyPI metadata verified 2026-08-09 |
| Ultralytics native `.onnx`/`.engine` predict | **HIGH** | Installed 8.4.116 AutoBackend + official integration examples |
| No project `tensorrt` extra | **HIGH** | Matches shipped EDGE-03 docs + JetPack reality |
| Jetson wheel URL pins | **MEDIUM** | Guide examples drift; always verify Jetson Zoo / assets on board |
| ORT 1.28 CUDA 12 vs 13 host matching | **MEDIUM** | Defaults documented; makers must match local CUDA/torch |
| Custom ORT not needed | **HIGH** for fixed-class YOLO26 with existing mapper | |

---

## Sources

- PyPI: `onnxruntime` 1.28.0, `onnxruntime-gpu` 1.28.0, `tensorrt` 11.2.1.2, `ultralytics` / `ultralytics-opencv-headless` 8.4.116 — checked 2026-08-09  
- ONNX Runtime install: https://onnxruntime.ai/docs/install/  
- Ultralytics ONNX integration examples (export + `YOLO("*.onnx")`): https://docs.ultralytics.com/integrations/onnx/  
- Ultralytics TensorRT integration (`YOLO("*.engine")`, INT8 notes): https://docs.ultralytics.com/integrations/tensorrt/  
- Ultralytics Jetson guide (JetPack 5/6/7, ORT wheel caveats, TRT on-device): https://docs.ultralytics.com/guides/nvidia-jetson/  
- Local package truth:  
  - `ultralytics/nn/autobackend.py` (format → backend map)  
  - `ultralytics/nn/backends/onnx.py` (providers, `onnxruntime` import)  
  - `ultralytics/nn/backends/tensorrt.py` (`import tensorrt`, engine deserialize)  
  - `ultralytics/utils/checks.py` (`check_tensorrt` → `tensorrt-cu{cuda_major}`)  
- In-repo policy: `docs/export/yolo26-onnx-tensorrt.md`, `docs/export/jetson-packaging.md`, `pyproject.toml`, `PROJECT.md` v0.2 scope  

---

## Opinionated defaults for roadmap

1. **Extra `onnx`** = CPU `onnxruntime` only; document GPU/Jetson wheels outside the lockfile.  
2. **Live path** = Ultralytics AutoBackend via weight suffix; do **not** build a parallel custom ORT decoder in v0.2.  
3. **TRT** = system/JetPack only; engines on-device; profiles already name `tensorrt` — wire them to real `.engine` load.  
4. **Keep `detect` required** for ORT/TRT live detect (torch still used inside Ultralytics backends).  
5. **Do not** expand stack to depth/YOLOE edge backends, OpenVINO, Triton, or `torch-tensorrt` this milestone.
