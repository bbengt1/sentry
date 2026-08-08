# YOLOE export (experimental)

Open-vocabulary **YOLOE** export is **experimental**. The supported edge path
for open-vocab in Sentry v1 remains **PyTorch YOLOE**, typically **off** or
**on-demand** (one-shot Run), not continuous dual-model load.

**Licenses:** Ultralytics YOLOE is **AGPL-3.0**. See
[`THIRD_PARTY_MODELS.md`](../../THIRD_PARTY_MODELS.md).

## Supported edge path (recommended)

| Setting | Honest expectation |
|---------|--------------------|
| Live runtime | PyTorch via `detect` extra (`YoloeOpenVocabWorker`) |
| Mode on Jetson / CPU | **off** or **on-demand** — not continuous dual-model by default |
| Weights | `yoloe-26n-seg.pt` (edge) / `yoloe-26s-seg.pt` (desktop default) |
| Text prompts | Runtime `set_classes` path on PyTorch YOLOE |

```bash
uv sync --extra detect
uv run sentry serve --profile jetson --source synthetic
# Live Preview: set prompts → Run (on-demand); continuous optional
```

## Experimental ONNX / TensorRT try path

Ultralytics exposes `.export` on YOLOE (same exporter surface as YOLO). Makers
may try:

```bash
uv run python scripts/export/export_yolo.py \
  --weights yoloe-26n-seg.pt \
  --format onnx \
  --imgsz 640
```

```python
from ultralytics import YOLOE

YOLOE("yoloe-26n-seg.pt").export(format="onnx", imgsz=640, simplify=True)
# engine format: NVIDIA + TensorRT on that host only; build on-device
```

| Topic | Honest expectation |
|-------|--------------------|
| Maturity | **Experimental** — text-prompt open-vocab may break or differ after export |
| Fallback | If export fails or prompts stop working, keep **PyTorch YOLOE** |
| Engines | Same rules as YOLO26: **on-device** TensorRT build; **never copy** `.engine` across SKUs |
| Prebuilt | Do **not** ship prebuilt YOLOE engines in the repo |

## Hard rules

1. Document export as **experimental**, not the default production OV path.
2. **PyTorch on-demand OV** remains the supported edge fallback.
3. **AGPL** obligations apply to Ultralytics weights and derivatives — see
   [`THIRD_PARTY_MODELS.md`](../../THIRD_PARTY_MODELS.md).
4. CI does not run real YOLOE export or download weights.

## Deferred

- Guaranteed open-vocab prompt parity on TensorRT engines
- First-class YOLOE ONNX Runtime backend inside Sentry
