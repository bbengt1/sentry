# Edge export (ONNX / TensorRT)

Offline **export recipes** for makers who want ONNX or TensorRT engines on
edge hardware, plus honesty notes for **live fixed-class ORT and TRT** serve
paths.

## What this is

| Surface | Role |
|---------|------|
| `docs/export/*` | Honesty-first recipes and packaging notes |
| `scripts/export/export_yolo.py` | Thin Ultralytics CLI wrapper (maker machine) |
| Live `sentry serve` | **Torch** by default; **fixed-class ORT live** when preferred + `.onnx` + `onnx` extra; **fixed-class TRT live** when preferred + allowlisted `.engine` + system TensorRT |

**Default live path is PyTorch.** Fixed-class YOLO can run live via ONNX
Runtime when `preferred_backend=onnxruntime`, a valid allowlisted `.onnx`
artifact is present, and the optional `onnx` extra is installed
(`uv sync --extra detect --extra onnx`). Fixed-class YOLO can also run live
via TensorRT when `preferred_backend=tensorrt`, a valid allowlisted `.engine`
is present, and **system / JetPack TensorRT** is importable — build engines
**on-device** only; there is **no** project `tensorrt` pip extra. CI does
**not** require Jetson, GPU ORT, TensorRT, or real weight downloads.

## Index

| Doc | Contents |
|-----|----------|
| [yolo26-onnx-tensorrt.md](yolo26-onnx-tensorrt.md) | YOLO26 → ONNX and TensorRT `engine` via Ultralytics + live ORT/TRT conditions |
| [yoloe-export.md](yoloe-export.md) | YOLOE export (experimental) + PyTorch open-vocab fallback |
| [depth-anything-v2.md](depth-anything-v2.md) | Depth export feasibility notes; live path stays HF Small |
| [jetson-packaging.md](jetson-packaging.md) | JetPack / on-device engine build + live TRT packaging honesty |

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

## Primary desktop path (PyTorch default)

Export is optional. For day-to-day development use profiles and the existing
detect/depth extras:

```bash
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --profile desktop-gpu --source synthetic
# or: --profile jetson | cpu-fallback
```

### Live fixed-class ORT (optional)

```bash
uv sync --extra dev --extra detect --extra onnx
# Place/export an allowlisted yolo26n.onnx, or set SENTRY_DETECTOR_ONNX
uv run sentry serve --profile cpu-fallback --source synthetic
```

If the artifact or `onnxruntime` dependency is missing, serve **soft-falls** to
torch and reports an honest reason — it never claims live ORT silently.

### Live fixed-class TRT (optional, on-device)

```bash
uv sync --extra detect   # NO --extra tensorrt
# On Jetson / target NVIDIA box with system TensorRT:
#   python -c "import tensorrt"
#   uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format engine --device 0
#   export SENTRY_DETECTOR_ENGINE=/allowlisted/path/yolo26n.engine
uv run sentry serve --profile jetson --source usb --device 0
```

If the `.engine` artifact, system `tensorrt` dep, or path is missing/rejected,
serve **soft-falls** to torch with `trt_artifact_missing` / `trt_dep_missing` /
`path_rejected` — it never claims live TRT silently.

Full desktop-GPU walkthrough is covered in a later release doc (Phase 7 plan
07-03). Edge packaging details live in [jetson-packaging.md](jetson-packaging.md).

## Quick export (YOLO26 ONNX)

Requires the **detect** extra (Ultralytics). Does **not** add a `tensorrt` pip
extra to the project. For **live** ORT serve, also install the **onnx** extra.

```bash
uv sync --extra detect
uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx
```

TensorRT `engine` format needs NVIDIA GPU + system TensorRT on **that**
machine — prefer building **on-device** on Jetson. See
[yolo26-onnx-tensorrt.md](yolo26-onnx-tensorrt.md).
