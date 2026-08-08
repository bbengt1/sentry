# Edge export (ONNX / TensorRT)

Offline **export recipes** for makers who want ONNX or TensorRT engines on
edge hardware. This is **not** a live TensorRT/ONNX Runtime inference backend
inside Sentry v1.

## What this is

| Surface | Role |
|---------|------|
| `docs/export/*` | Honesty-first recipes and packaging notes |
| `scripts/export/export_yolo.py` | Thin Ultralytics CLI wrapper (maker machine) |
| Live `sentry serve` | Remains **PyTorch** profiles (`desktop-gpu`, `jetson`, `cpu-fallback`) |

**Live inference stays PyTorch** unless a future backend ships. Export is an
**offline tool path** — run on a developer machine or **on-device** on Jetson,
then deploy the resulting artifacts yourself. CI does **not** require Jetson,
TensorRT, or real weight downloads.

## Index

| Doc | Contents |
|-----|----------|
| [yolo26-onnx-tensorrt.md](yolo26-onnx-tensorrt.md) | YOLO26 → ONNX and TensorRT `engine` via Ultralytics |
| [yoloe-export.md](yoloe-export.md) | YOLOE export (experimental) + PyTorch open-vocab fallback |
| [depth-anything-v2.md](depth-anything-v2.md) | Depth export feasibility notes; live path stays HF Small |
| [jetson-packaging.md](jetson-packaging.md) | JetPack / on-device engine build + profile honesty |

Scripts: [`scripts/export/README.md`](../../scripts/export/README.md).

## Hard rules (read first)

1. **Build TensorRT engines on the target device** (same GPU architecture +
   TensorRT / JetPack). Engines are **not portable**.
2. **Never copy** `.engine` files across JetPack SKUs or from desktop → Jetson
   as a supported path.
3. **Do not ship prebuilt engines** in this repo or the wheel.
4. **Measure FPS on device** — docs do not invent dual-model realtime numbers.
5. **AGPL caution** for Ultralytics YOLO / YOLOE — see
   [`THIRD_PARTY_MODELS.md`](../../THIRD_PARTY_MODELS.md).

## Primary desktop path (still PyTorch)

Export is optional. For day-to-day development use profiles and the existing
detect/depth extras:

```bash
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --profile desktop-gpu --source synthetic
# or: --profile jetson | cpu-fallback
```

Full desktop-GPU walkthrough is covered in a later release doc (Phase 7 plan
07-03). Edge packaging details live in [jetson-packaging.md](jetson-packaging.md).

## Quick export (YOLO26 ONNX)

Requires the **detect** extra (Ultralytics). Does **not** add a `tensorrt` pip
extra to the project.

```bash
uv sync --extra detect
uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx
```

TensorRT `engine` format needs NVIDIA GPU + system TensorRT on **that**
machine — prefer building **on-device** on Jetson. See
[yolo26-onnx-tensorrt.md](yolo26-onnx-tensorrt.md).
