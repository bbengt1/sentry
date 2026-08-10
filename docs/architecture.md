# Architecture

## Spine

```
Camera Sources (synthetic | usb | file | rtsp)
        │
        ▼
   CaptureLoop ──publish──► FrameBus (depth-1, keep-latest)
        │                         │
        │                         ├──► DetectionLoop  (YOLO26 fixed-class)
        │                         ├──► DepthLoop      (DAV2 Small)
        │                         └──► OpenVocabLoop  (YOLOE, default off)
        │                                   │
        │                                   ▼
        │                          PerceptionStore
        │                          (keep-latest products)
        │                                   │
        │                          FreeSpaceLoop
        │                          (Spatial Post from depth only)
        │                                   │
        ▼                                   ▼
   Live Preview (MJPEG + UI)     assemble_perception_frame
   /api/status, controls         GET /v1/snapshot · WS /v1/stream
```

**Single truth:** Live Preview overlays and robot APIs both read
`PerceptionStore` via the same assembler. Workers never open cameras;
capture owns the source lifecycle.

## Processes and threads

| Component | Role |
|-----------|------|
| `CaptureLoop` | Daemon thread; open source, publish `ImageFrame` to bus, reconnect on disconnect |
| `DetectionLoop` | Poll bus `get_latest()`; write `set_detections` |
| `DepthLoop` | Poll bus; write `set_depth` |
| `OpenVocabLoop` | Poll bus; write `set_open_vocab` only (never dual-write detections) |
| `FreeSpaceLoop` | Poll `snapshot_depth()`; write `set_free_space` (no FrameBus) |
| Uvicorn / FastAPI | HTTP, WebSocket, MJPEG; inject store + loops + `PipelineState` |

Stage toggles use **enable flags** inside loops (skip compute) — they do not
`stop()`/`start()` worker threads for UI toggles.

## Packages and extras

| Extra | Contents |
|-------|----------|
| *(core)* | FastAPI, OpenCV headless, capture, free-space, API, UI static |
| `detect` | Ultralytics YOLO26 + YOLOE |
| `depth` | torch + transformers + HF hub (DAV2 Small) |
| `onnx` | CPU ONNX Runtime for live fixed-class YOLO ORT path |
| `dev` | pytest, ruff, httpx |

Missing extras: `sentry serve` still runs capture + Live Preview and logs an
install hint.

## Profiles vs live inference

Built-in profiles (`desktop-gpu`, `jetson`, `cpu-fallback`) select:

- detector / open-vocab weight tiers  
- depth tier (Small only for commercial-friendly defaults)  
- **device policy** (`preferred_backend` + `device_id` + `fallback_to_torch`)

Live inference is **PyTorch / Ultralytics / HF** by default. Fixed-class YOLO
may run **live via ONNX Runtime** when `preferred_backend=onnxruntime`, an
allowlisted `.onnx` artifact resolves, and the optional `onnx` extra is
installed. Fixed-class YOLO may run **live via TensorRT** when
`preferred_backend=tensorrt`, an allowlisted `.engine` resolves, and system /
JetPack `tensorrt` is importable. Engines are built **on-device** only — see
[export/](export/) for lifecycle and packaging. CUDA requests fall back to
MPS or CPU when unavailable.

### Fallback chain (sticky soft default / strict opt-in)

Resolve happens **once** at serve via `build_detection_worker` (factory is the
sole author of `backend_live` / `backend_reason`). DetectionLoop never
re-selects the preferred backend.

| Step | Outcome |
|------|---------|
| Preferred torch/cpu | Live torch worker; reason none |
| Preferred ORT/TRT + artifact + dep | Live `backend_live=onnxruntime` or `tensorrt` |
| Preferred ORT/TRT miss, soft (`fallback_to_torch=true`, **default**) | Torch worker + reason; serve continues |
| Preferred ORT/TRT miss, strict (`fallback_to_torch=false`) | `worker=None`, `backend_live=None`, reason set; serve exits non-zero |

Soft remains the global default (including jetson package profiles). Operators
opt into strict with `device.fallback_to_torch: false` or
`SENTRY_FALLBACK_TO_TORCH=false`. See [configuration.md](configuration.md).

**Residual risk:** if the factory claims live ORT/TRT (artifact + dep present)
but Ultralytics later fails to load a corrupt engine at first inference, operators
may still see load errors until process restart. Sticky factory resolve does not
rewrite DetectionLoop load-failure pause — document and restart after fixing
artifacts.

## Boundaries (non-negotiable)

| In scope | Out of scope |
|----------|--------------|
| Camera-only sensing | Required LiDAR / radar |
| Perception stream | Motor commands, path plans, e-stop |
| Relative depth (+ optional metric labels) | Selling relative depth as meters |
| Single active camera | Multi-cam fusion |
| ROS2 / voice **stubs** | Production ROS2 node / ASR-TTS product |

See [safety-and-privacy.md](safety-and-privacy.md).

## Extension points

| Extension | Status in v0.1.0 |
|-----------|------------------|
| Plugin sources / workers / sinks | Entry points + registry |
| Multi-cam `camera_id` | Schema identity tests; single source at serve |
| ROS2 | `sentry_ai.extensions.ros2.Ros2PerceptionBridge` — NotImplemented |
| Voice | `VoiceNullSink` (`voice-null`) no-op sink |

## Key modules

| Path | Responsibility |
|------|----------------|
| `src/sentry_ai/cli.py` | `health`, `cameras`, `smoke`, `serve` |
| `src/sentry_ai/bus/frame_bus.py` | Keep-latest frame bus |
| `src/sentry_ai/state/perception_store.py` | Product store |
| `src/sentry_ai/api/assemble.py` | Merge → `PerceptionFrame` |
| `src/sentry_ai/api/routes_*.py` | HTTP/WS surface |
| `src/sentry_ai/config/profile_runtime.py` | Profile → weights/device |
| `src/sentry_ai/models/device.py` | Device availability resolution |
| `src/sentry_ai/control/pipeline_state.py` | Stage flags + free-space cuts |
