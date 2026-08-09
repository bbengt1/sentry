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
| `dev` | pytest, ruff, httpx |

Missing extras: `sentry serve` still runs capture + Live Preview and logs an
install hint.

## Profiles vs live inference

Built-in profiles (`desktop-gpu`, `jetson`, `cpu-fallback`) select:

- detector / open-vocab weight tiers  
- depth tier (Small only for commercial-friendly defaults)  
- **device policy** (`preferred_backend` + `device_id`)

Live inference remains **PyTorch / Ultralytics / HF**. `preferred_backend:
tensorrt` or `onnxruntime` is **policy + export target**, not a silent live
TensorRT/ORT runtime in v0.1.0. CUDA requests fall back to MPS or CPU when
unavailable. Export packaging: [export/](export/).

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
