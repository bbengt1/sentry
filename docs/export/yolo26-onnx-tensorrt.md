# YOLO26 → ONNX / TensorRT

Export fixed-class **YOLO26** weights with Ultralytics `model.export`. Live
Sentry detection still runs the **PyTorch** Ultralytics path; these recipes are
for offline edge packaging.

**Licenses:** Ultralytics YOLO26 is **AGPL-3.0**. Read
[`THIRD_PARTY_MODELS.md`](../../THIRD_PARTY_MODELS.md) before redistribution.

## Prerequisites

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
| CPU / Pi | Useful for experiments; **spatial awareness lite / best-effort** — no unmeasured dual-model realtime FPS claim |
| CI | Default pytest never runs real `model.export` or weight downloads |

Known allowlisted basenames: `yolo26n.pt`, `yolo26s.pt`, `yolo26m.pt`
(see `sentry_ai.models.cache.KNOWN_WEIGHTS`).

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

| Profile | Detector tier | Export starting point |
|---------|---------------|------------------------|
| `jetson` | `n` → `yolo26n.pt` | Build **on-device** engine on Jetson |
| `desktop-gpu` | `s` → `yolo26s.pt` | Desktop ONNX/engine for lab only; rebuild on edge |
| `cpu-fallback` | `n` → `yolo26n.pt` | Prefer ONNX; TRT not applicable |

`preferred_backend: tensorrt` on the jetson profile is a **device policy /
export target hint**. Live `sentry serve` still uses PyTorch unless a future
InferenceBackend ships.

## Deferred (not in v1 product)

- First-class ONNX Runtime / TensorRT `InferenceBackend` inside Sentry
- Prebuilt engines on GitHub Releases
- CI jobs that require Jetson or system TensorRT
