# Export scripts

Offline helpers for makers packaging YOLO weights. **Not** imported by the
`sentry_ai` runtime. Live fixed-class serve can use exported `.onnx` / `.engine`
when preferred backend + artifact + dep conditions are met (see
[`docs/export/README.md`](../../docs/export/README.md) and
[`docs/edge-serve.md`](../../docs/edge-serve.md)); otherwise soft-falls to torch.

## Requirements

```bash
# From repo root
uv sync --extra detect
```

- **ONNX** (`--format onnx`): Ultralytics + detect extra (may pull export deps).
- **TensorRT engine** (`--format engine`): NVIDIA GPU + **system** TensorRT on
  **that** machine. Prefer **on-device** build on Jetson (same JetPack).
- Do **not** add a project `tensorrt` pip extra.
- Default CI never runs real `model.export` or weight downloads.

Honesty / Jetson packaging: [`docs/export/README.md`](../../docs/export/README.md).

## Commands

```bash
# YOLO26 → ONNX
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format onnx \
  --imgsz 640

# TensorRT engine (on the target NVIDIA / Jetson host only)
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format engine \
  --imgsz 640 \
  --device 0

# YOLOE (experimental export — PyTorch OV remains supported edge path)
uv run python scripts/export/export_yolo.py \
  --weights yoloe-26n-seg.pt \
  --format onnx
```

`--weights` must be a **basename** from `KNOWN_WEIGHTS`
(`yolo26n.pt`, `yolo26s.pt`, `yolo26m.pt`, `yoloe-26n-seg.pt`,
`yoloe-26s-seg.pt`). Absolute paths and `../` traversal are rejected.

```bash
uv run python scripts/export/export_yolo.py --help
```

## Safety

| Rule | Detail |
|------|--------|
| Allowlist | Basenames only via `sentry_ai.models.cache.KNOWN_WEIGHTS` |
| Engines | Build on-device; never copy `.engine` across JetPack SKUs |
| Prebuilt | Do not commit `.engine` files to the repo |
| AGPL | Ultralytics YOLO/YOLOE — see `THIRD_PARTY_MODELS.md` |
