# YOLO26 → ONNX / TensorRT

Export fixed-class **YOLO26** weights with Ultralytics `model.export`, and run
**live fixed-class detection** via ONNX Runtime or TensorRT when serve
conditions are met.

| Path | When |
|------|------|
| **Live ORT** | `preferred_backend=onnxruntime` + allowlisted `.onnx` present + `onnx` extra installed → `backend_live=onnxruntime` (Ultralytics-native `YOLO("*.onnx")`) |
| **Live TRT** | `preferred_backend=tensorrt` + allowlisted `.engine` present + system `tensorrt` importable → `backend_live=tensorrt` (Ultralytics-native `YOLO("*.engine")`) |
| **Soft torch fallback** | Missing artifact, missing dep (`onnxruntime` / system `tensorrt`), or rejected path → live stays **torch** with an honest reason (`ort_artifact_missing` / `ort_dep_missing` / `trt_artifact_missing` / `trt_dep_missing` / `path_rejected`) |
| **Offline export** | Recipes below produce `.onnx` / on-device `.engine` artifacts for edge packaging |

**Licenses:** Ultralytics YOLO26 is **AGPL-3.0**. Read
[`THIRD_PARTY_MODELS.md`](../../THIRD_PARTY_MODELS.md) before redistribution.

## Prerequisites

### Live fixed-class ORT (serve)

```bash
uv sync --extra detect --extra onnx
# Optional: point at an allowlisted artifact
#   export SENTRY_DETECTOR_ONNX=/path/to/yolo26n.onnx
#   # or place yolo26n.onnx under the model cache / cwd (allowlisted stems)
uv run sentry serve --profile cpu-fallback --source synthetic
```

CPU `onnxruntime` (the `onnx` extra) is enough for makers and CI. GPU ORT is
an optional system install — **not** required in CI. Default pytest never
loads real `.onnx` graphs or downloads weights.

### Live fixed-class TensorRT (serve, on-device)

```bash
uv sync --extra detect   # (+ depth if dual-model); NO --extra tensorrt
# Verify system / JetPack TensorRT is importable on this machine:
python -c "import tensorrt"
# Build engine on this same device (see TensorRT section), then either place
# the allowlisted stem under cache/cwd or:
#   export SENTRY_DETECTOR_ENGINE=/allowlisted/path/yolo26n.engine
# Optional artifact root for resolution:
#   export SENTRY_ARTIFACT_ROOT=/path/to/artifacts
uv run sentry serve --profile jetson --source usb --device 0
```

Do **not** install a project `tensorrt` pip extra — use JetPack / system TRT.
Default pytest never loads real `.engine` files or requires Jetson / system
TensorRT.

### Offline export

```bash
uv sync --extra detect
# TensorRT engine export additionally needs NVIDIA GPU + system TensorRT
# on the same machine that will run the engine (JetPack on Jetson).
```

## ONNX (portable intermediate)

```bash
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format onnx \
  --imgsz 640
```

Equivalent Ultralytics API:

```python
from ultralytics import YOLO

YOLO("yolo26n.pt").export(format="onnx", imgsz=640, simplify=True)
```

| Topic | Honest expectation |
|-------|--------------------|
| Portability | ONNX is the portable graph; still validate ops on the target runtime |
| Live serve | With `cpu-fallback` (preferred `onnxruntime`) + this artifact + `onnx` extra → live ORT; otherwise soft torch fallback |
| CPU / Pi | Useful for experiments; **spatial awareness lite / best-effort** — no unmeasured dual-model realtime FPS claim |
| CI | Default pytest never runs real `model.export` or weight downloads; live ORT unit tests mock the load path |

Known allowlisted basenames: `yolo26n.pt`, `yolo26s.pt`, `yolo26m.pt`
(and matching `.onnx` / `.engine` stems via artifact resolution —
see `sentry_ai.models.cache.KNOWN_WEIGHTS` / `resolve_detector_artifact`).

## TensorRT engine (GPU only)

```bash
# Prefer on the Jetson / target NVIDIA box:
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format engine \
  --imgsz 640 \
  --device 0
```

Equivalent:

```python
from ultralytics import YOLO

YOLO("yolo26n.pt").export(format="engine", imgsz=640, quantize=16, device=0)
```

### On-device build (required)

**Build TensorRT engines on the target device** — same GPU architecture and
TensorRT / JetPack version as production.

| Rule | Why |
|------|-----|
| **On-device** engine build | Engines bind to GPU arch + TRT/JetPack |
| **Never copy** `.engine` across JetPack SKUs | Not portable; desktop→Jetson copies fail or misbehave |
| **Do not ship prebuilt** multi-SKU engines in the repo | No `.engine` artifacts in git or the wheel |
| **Measure** latency/FPS on device | Docs do not invent sustained dual-model FPS |

Cross-SKU “copy the engine file” is **not** a supported deployment path.

### Runtime conf (when supported)

Default engine export (without baked `nms=True`) keeps runtime confidence
thresholds working via Ultralytics postprocess NMS — `set_conf` on the live
TRT path behaves like the torch / ORT workers. If you export with NMS baked
into the engine, conf may not be adjustable at serve time; prefer the default
export unless you have measured the trade-off on device.

### Env placement

| Variable | Role |
|----------|------|
| `SENTRY_DETECTOR_ENGINE` | Explicit allowlisted path to a fixed-class `.engine` |
| `SENTRY_ARTIFACT_ROOT` | Optional root searched for allowlisted detector stems |
| `SENTRY_DETECTOR_ONNX` | Explicit allowlisted path to a fixed-class `.onnx` (ORT) |

Only allowlisted env / cache / cwd paths are accepted — arbitrary remote
download of engines is not a supported deployment path.

## Profile alignment

| Profile | Detector tier | Live serve | Export starting point |
|---------|---------------|------------|------------------------|
| `jetson` | `n` → `yolo26n.pt` | Live **tensorrt** when allowlisted `.engine` + system `tensorrt` present; else soft torch + reason | Build **on-device** engine on Jetson |
| `desktop-gpu` | `s` → `yolo26s.pt` | Live **torch** | Desktop ONNX/engine for lab only; rebuild TRT on edge |
| `cpu-fallback` | `n` → `yolo26n.pt` | Live **onnxruntime** when `.onnx` + `onnx` extra present; else soft torch | Prefer ONNX; TRT not applicable |

`preferred_backend: tensorrt` on the jetson profile **can be live** when an
allowlisted `.engine` resolves and system / JetPack `tensorrt` is importable.
Missing artifact or dependency does **not** silently claim TRT — serve soft-falls
to torch with a stable reason code (`trt_artifact_missing` / `trt_dep_missing` /
`path_rejected`). Rebuild engines on the edge after JetPack upgrades.

`preferred_backend: onnxruntime` on `cpu-fallback` **can be live** when an
allowlisted `.onnx` resolves and the `onnx` extra (onnxruntime) is installed.
Missing artifact or dependency does **not** silently claim ORT — serve soft-falls
to torch with a stable reason code.

## Dual-model guardrails (shipped)

**Supported (measure on device):** fixed-class TRT or torch YOLO + torch DAV2
Small may share one GPU. Measure VRAM / latency / thermal headroom on the
target board — **no dual-model FPS claim** and no published dual-model FPS
tables without on-device methodology.

**Not a first-class configuration:** continuous open-vocab + TRT YOLO + DAV2
together this milestone. Prefer open-vocab **off** or **on-demand**; keep depth
and fixed-class detect as the dual-model pair.

**Sticky soft / strict policy (factory once at serve):**

| Mode | How | Miss behavior |
|------|-----|---------------|
| Soft (default) | `fallback_to_torch=true` (default) | torch worker + honest reason; serve continues |
| Strict (opt-in) | `fallback_to_torch=false` or `SENTRY_FALLBACK_TO_TORCH=false` | fail-closed; serve exits — no silent torch under preferred ORT/TRT |

Factory resolves preferred backend **once** at `sentry serve` construct
(sticky) — DetectionLoop never re-resolves mid-process.

**Operator knobs when GPU is tight:** disable depth, open-vocab off/on-demand,
nano detector tier, `--no-ui`, watch `nvidia-smi`. Depth and open-vocab remain
**PyTorch-only** (no live ORT/TRT claim for those stages).

## Deferred (not in this release)

- Custom TensorRT `InferenceBackend` class (live path uses factory
  Ultralytics-native `YOLO("*.engine")` instead)
- Prebuilt engines on GitHub Releases
- CI jobs that require Jetson, system TensorRT, or GPU ORT
- Custom ORT `InferenceSession` + hand-written YOLO26 decoder (live path uses
  Ultralytics-native `YOLO("*.onnx")` instead)
- Runtime VRAM governor / dual-model sequential GPU scheduler rewrite
