# Edge serve — export → artifact → `sentry serve`

Numbered path for makers who want **live fixed-class ORT / TRT** on edge
hardware (desktop NVIDIA or Jetson). This hub links into export recipes; it
does **not** invent dual-model FPS.

| Backend | Live when |
|---------|-----------|
| **Torch** (default) | Always available with `detect` extra |
| **ONNX Runtime** | `preferred_backend=onnxruntime` + allowlisted `.onnx` + `uv sync --extra onnx` |
| **TensorRT** | `preferred_backend=tensorrt` + allowlisted `.engine` + system/JetPack TensorRT (**no** pip extra) |
| **Miss** | Soft torch + reason (default); strict fail-closed via `SENTRY_FALLBACK_TO_TORCH=false` |

## 1. Install extras

```bash
# From repo root
uv sync --extra detect
# Optional live ORT:
uv sync --extra detect --extra onnx
# Optional dual-model depth (torch DAV2):
uv sync --extra detect --extra depth
# Optional ORT + depth:
uv sync --extra detect --extra onnx --extra depth
```

**NO `--extra tensorrt`** — use system / JetPack TensorRT on the target device
only. There is no project `tensorrt` pip extra.

## 2. Export artifact (on-device for `.engine`)

```bash
# ONNX graph (may be produced on desktop for later ORT serve)
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format onnx

# TensorRT engine — build on the SAME device / JetPack SKU as production
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format engine \
  --device 0
```

Engines are **not portable**. Never copy `.engine` across JetPack SKUs or
desktop → Jetson as a supported path. Do not ship prebuilt engines in the repo
or wheel. Details: [export/yolo26-onnx-tensorrt.md](export/yolo26-onnx-tensorrt.md).

## 3. Place artifact / set env

Allowlisted stems only (`yolo26n`, `yolo26s`, `yolo26m` under cache/cwd, or
explicit env paths):

| Env | Use |
|-----|-----|
| `SENTRY_DETECTOR_ONNX` | Path to allowlisted `.onnx` for ORT |
| `SENTRY_DETECTOR_ENGINE` | Path to allowlisted `.engine` for TRT |
| `SENTRY_ARTIFACT_ROOT` | Optional allowlisted root for artifact resolution |

Profiles set `preferred_backend` (`cpu-fallback` → onnxruntime intent;
`jetson` → tensorrt intent). See [configuration.md](configuration.md).

## 4. Serve with profile

```bash
# ORT-oriented (cpu-fallback prefers onnxruntime when artifact+dep present)
uv run sentry serve --profile cpu-fallback --source synthetic

# Jetson / TRT-oriented (live TRT when .engine + system TensorRT)
uv run sentry serve --profile jetson --source usb --device 0

# Desktop GPU (torch default; export still optional)
uv run sentry serve --profile desktop-gpu --source usb --device 0
```

## 5. Headless (optional)

```bash
# Perception API without Live Preview HTML
uv run sentry serve --profile jetson --source usb --device 0 --no-ui
# → GET /v1/snapshot  ·  WS /v1/stream  ·  GET /api/status
```

Headless does **not** add authentication — see
[safety-and-privacy.md](safety-and-privacy.md).

## 6. Confirm honesty

After serve starts, check the banner and/or:

```bash
curl -s http://127.0.0.1:8000/api/status | python -m json.tool
```

Compare **`backend_requested`** vs **`backend_live`** (+ **`backend_reason`**
when soft-fallen). Live ORT reports `backend_live=onnxruntime`; live TRT
reports `backend_live=tensorrt`. Missing artifact/dep never claims live
silently.

## 7. Soft vs strict fallback

| Mode | Behavior |
|------|----------|
| **Soft** (default) | `fallback_to_torch=true` → torch + honest reason (`ort_artifact_missing`, `trt_dep_missing`, …) |
| **Strict** | `SENTRY_FALLBACK_TO_TORCH=false` → fail-closed (no worker / serve exit) |

Backend selection is **sticky** once at serve start — not re-probed every frame.

## 8. Dual-model (measure on device)

Fixed-class TRT or torch YOLO + torch DAV2 Small may share a GPU — **measure
on device**. Continuous open-vocab + TRT + DAV2 is **not a first-class**
configuration. Docs publish **no dual-model FPS claim** and do not invent
realtime numbers.

## On-device validation checklist (manual)

1. Export engine **on this SKU** (`export_yolo.py --format engine`)
2. `python -c "import tensorrt"` succeeds via JetPack / system install
3. Place allowlisted `.engine` or set `SENTRY_DETECTOR_ENGINE`
4. `uv run sentry serve --profile jetson --source usb --device 0`
5. Confirm `backend_live=tensorrt` (or honest soft reason if miss)

## Related docs

| Doc | Role |
|-----|------|
| [export/README.md](export/README.md) | Export index + live ORT/TRT conditions |
| [export/yolo26-onnx-tensorrt.md](export/yolo26-onnx-tensorrt.md) | YOLO26 export + live condition table |
| [export/jetson-packaging.md](export/jetson-packaging.md) | Jetson profile + dual-model honesty |
| [desktop-gpu.md](desktop-gpu.md) | Primary desktop PyTorch maker path |
| [../THIRD_PARTY_MODELS.md](../THIRD_PARTY_MODELS.md) | AGPL YOLO + derived `.onnx`/`.engine` lineage |
| [../scripts/export/README.md](../scripts/export/README.md) | CLI wrapper commands |
