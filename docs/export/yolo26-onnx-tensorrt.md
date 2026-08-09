# YOLO26 → ONNX / TensorRT

Export fixed-class **YOLO26** weights with Ultralytics `model.export`, and run
**live fixed-class detection via ONNX Runtime** when serve conditions are met.

| Path | When |
|------|------|
| **Live ORT** | `preferred_backend=onnxruntime` + allowlisted `.onnx` present + `onnx` extra installed → `backend_live=onnxruntime` (Ultralytics-native `YOLO("*.onnx")`) |
| **Soft torch fallback** | Missing artifact, missing `onnxruntime` dep, or rejected path → live stays **torch** with an honest reason (`ort_artifact_missing` / `ort_dep_missing` / `path_rejected`) |
| **Offline export** | Recipes below produce `.onnx` / on-device `.engine` artifacts for edge packaging |
| **TensorRT** | Still **non-live** in serve (policy / export target until a future TRT phase); build **on-device** only |

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

### Offline export

```bash
uv sync --extra detect
# TensorRT engine export additionally needs NVIDIA GPU + system TensorRT
# on the same machine that will run the engine (JetPack on Jetson).
```

Do **not** install a project `tensorrt` pip extra — use JetPack / system TRT.

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
(and matching `.onnx` stems via artifact resolution —
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

## Profile alignment

| Profile | Detector tier | Live serve | Export starting point |
|---------|---------------|------------|------------------------|
| `jetson` | `n` → `yolo26n.pt` | Soft torch until live TRT ships; `preferred_backend=tensorrt` is policy | Build **on-device** engine on Jetson |
| `desktop-gpu` | `s` → `yolo26s.pt` | Live **torch** | Desktop ONNX/engine for lab only; rebuild TRT on edge |
| `cpu-fallback` | `n` → `yolo26n.pt` | Live **onnxruntime** when `.onnx` + `onnx` extra present; else soft torch | Prefer ONNX; TRT not applicable |

`preferred_backend: tensorrt` on the jetson profile remains a **device policy /
export target hint** — live TensorRT is not claimed until a future phase.

`preferred_backend: onnxruntime` on `cpu-fallback` **can be live** when an
allowlisted `.onnx` resolves and the `onnx` extra (onnxruntime) is installed.
Missing artifact or dependency does **not** silently claim ORT — serve soft-falls
to torch with a stable reason code.

## Deferred (not in this release)

- Live TensorRT `InferenceBackend` inside Sentry (future phase)
- Prebuilt engines on GitHub Releases
- CI jobs that require Jetson, system TensorRT, or GPU ORT
- Custom ORT `InferenceSession` + hand-written YOLO26 decoder (live path uses
  Ultralytics-native `YOLO("*.onnx")` instead)
