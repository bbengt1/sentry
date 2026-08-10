# Jetson packaging notes

Honest packaging guidance for NVIDIA Jetson-class edge targets. **As of 2026-08
research** — verify JetPack, TensorRT, and CUDA versions **on device**. This
document does **not** invent FPS numbers.

Live Sentry inference is **PyTorch** by default. Fixed-class YOLO can run
**live TensorRT** when `preferred_backend=tensorrt`, an allowlisted `.engine`
is present, and **system / JetPack TensorRT** is importable. Depth and
open-vocab remain PyTorch / HF.

## Profile: `jetson`

```bash
uv sync --extra detect --extra depth
# NO --extra tensorrt — use JetPack / system TensorRT only
# On device, after building an engine (see below):
#   export SENTRY_DETECTOR_ENGINE=/allowlisted/path/yolo26n.engine
uv run sentry serve --profile jetson --source usb --device 0
# Headless robot consumer:
uv run sentry serve --profile jetson --source usb --device 0 --no-ui
```

| Capability | Jetson profile intent | Honest note |
|------------|----------------------|-------------|
| Detector | YOLO **n** (`yolo26n.pt`) | Prefer nano tier on shared GPU |
| Depth | DAV2 **Small** | HF Transformers live path |
| Open-vocab | **off** or **on-demand** | Not continuous dual-model by default |
| `preferred_backend` | `tensorrt` | Live TRT when allowlisted `.engine` + system TensorRT present; else soft torch + reason (`trt_artifact_missing` / `trt_dep_missing` / `path_rejected`) |
| UI | Optional `--no-ui` | Perception `/v1` + `/api` without Live Preview HTML |

## TensorRT / JetPack (on-device)

| Rule | Detail |
|------|--------|
| **On-device** engine build | Build `.engine` on the **same** Jetson + JetPack + TensorRT as production |
| **Never copy** engines | Desktop→Jetson or cross-SKU JetPack copies are **not portable** / not supported |
| **No prebuilt engines** | Do **not** ship `.engine` files in the repo, wheel, or multi-SKU Releases |
| System TRT | Use **JetPack-bundled or NVIDIA system TensorRT** — **no** project `tensorrt` pip extra / pin |
| Verify import | `python -c "import tensorrt"` on the target before claiming live TRT |
| Rebuild | Rebuild engines after JetPack / TensorRT upgrades |
| CI | **CI does not require Jetson** — unit tests are keyword + CLI parse only |

```bash
# On the Jetson (detect extra + system TensorRT — no project tensorrt pip extra):
uv sync --extra detect
python -c "import tensorrt"   # must succeed via JetPack / system install
uv run python scripts/export/export_yolo.py \
  --weights yolo26n.pt \
  --format engine \
  --imgsz 640 \
  --device 0
# Place under allowlist or set SENTRY_DETECTOR_ENGINE, then:
uv run sentry serve --profile jetson --source usb --device 0
```

See [yolo26-onnx-tensorrt.md](yolo26-onnx-tensorrt.md) for live TRT conditions
and [yoloe-export.md](yoloe-export.md) (YOLOE export remains **experimental**).

### Dual-model honesty

TRT YOLO + torch depth may share one GPU. **Measure on device** under your
thermal / power envelope — docs do not invent dual-model FPS. First-class
dual-model scheduling guardrails are Phase 11.

## Optional matrix (verify on device)

| Component | Research note (as of 2026-08 research; verify on device) |
|-----------|----------------------------------------------------------|
| JetPack | Match Ultralytics / torch wheel guidance for your SKU |
| TensorRT | JetPack-bundled or NVIDIA system install; rebuild engines after JetPack upgrades |
| YOLO26 | Start with **n**; measure latency under thermal load |
| Depth | DAV2 Small; shared-GPU scheduling with detect is device-specific |
| Open-vocab | Prefer off / on-demand; dual continuous load unmeasured |
| FPS | **Measure on device** — no published dual-model realtime claim here |

Do not invent JetPack apt package version pins without hardware verification.

## Pi / CPU (spatial awareness lite)

For Raspberry Pi and generic CPU (`--profile cpu-fallback`):

| Topic | Honest expectation |
|-------|--------------------|
| Detector | YOLO **n** (ONNX experiments optional) |
| Depth | DAV2 Small when the host can run it |
| Open-vocab | **off** |
| Language | **spatial awareness lite / best-effort** |
| Dual-model realtime | **No** unmeasured dual-model realtime FPS claim |

Prefer measuring end-to-end latency on the actual board. Do not assume Jetson
or desktop numbers transfer.

## Security & safety (edge)

- Default bind remains **localhost** (`127.0.0.1`). LAN bind is opt-in and
  **unauthenticated** camera exposure.
- Perception stream is **not** a safety interlock — honor stale/TTL flags.
- AGPL YOLO/YOLOE: [`THIRD_PARTY_MODELS.md`](../../THIRD_PARTY_MODELS.md).

## Deferred

- Prebuilt multi-SKU TensorRT engines
- Sticky thrash-free fallback policy (Phase 11)
- Guaranteed sustained FPS tables without on-device measurement
- Full ROS2 / multi-cam product (extension stubs are a separate plan)
