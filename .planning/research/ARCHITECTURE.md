# Architecture Research

**Domain:** Camera-only robotics perception (maker / open-source stack)  
**Researched:** 2026-08-07  
**Confidence:** HIGH for component topology and data flow; MEDIUM for free-space derivation details and exact process-vs-thread tradeoffs on Pi-class hardware  

## System Overview

Open-source camera-only perception systems converge on the same shape: a **directed pipeline graph** of stages that turn raw frames into structured spatial products (depth, detections, free space), then **fan out** those products to consumers (robot API, developer UI, optional ROS2).

Industry reference patterns:

| System | Core pattern | Relevance to Sentry |
|--------|--------------|---------------------|
| **DepthAI (Luxonis)** | Pipeline of linked **nodes** exchanging **messages**; host device is a thin control plane | Best mental model for stage boundaries and typed messages |
| **Isaac ROS DNN** | Image → resize → **encoder** → inference (TensorRT/Triton) → **decoder** → app results; multi-target x86 + Jetson | Encode/decode separation; desktop + edge as first-class |
| **ROS 2 composition** | Composable nodes in a **component container**; pub/sub contracts; multi-threaded executors | Extension path for ROS2 without rewriting core |
| **Autoware perception** | Many small packages (detect, classify, track, BEV, TensorRT backends) behind stable interfaces | Plugin-per-capability, not one monolith model |
| **Foxglove / image_transport** | Live viz + compressed image transport as **side channels**, not control loop | Web UI is a subscriber, not in the hot path |

**Recommended Sentry shape (opinionated):** a single **perception process** hosting a **frame bus** and **plugin workers**, with a thin **API/UI server** that only reads published state and writes config. Do **not** put robot control inside Sentry. Do **not** require ROS2 for v1 — expose clean WebSocket/REST contracts first; ROS2 is a bridge plugin later.

```
┌─────────────┐     ┌──────────────────────────────────────────────────┐
│ Camera      │     │                 Perception Runtime               │
│ Sources     │────▶│  Frame Bus ──▶ Model Workers (depth/det/…)       │
│ USB/RTSP/   │     │      │              │                            │
│ File/Synth  │     │      │              ▼                            │
└─────────────┘     │      │     Spatial Post (free-space, obstacles)  │
                    │      │              │                            │
                    │      ▼              ▼                            │
                    │  Perception State Store (latest + ring)          │
                    │      │              │                            │
                    └──────┼──────────────┼────────────────────────────┘
                           │              │
              ┌────────────▼──┐    ┌──────▼────────────┐
              │ Web Dev UI    │    │ Perception Stream │
              │ (overlays +   │    │ API (WS/REST)     │
              │  controls)    │    │ → robot consumer  │
              └───────▲───────┘    └───────────────────┘
                      │ config / thresholds / toggles
                      └──── Control plane (not hot path)
```

**Design thesis:** treat every stage as a **message producer/consumer** with a stable schema. Swap models, cameras, and sinks without rewriting the graph. Prefer **latest-frame drop** over backlog for realtime.

---

## Major Components

### Component Boundaries

| Component | Responsibility | Owns | Does NOT own | Communicates with |
|-----------|----------------|------|--------------|-------------------|
| **Camera Source** | Acquire frames from USB UVC, RTSP/IP, file, synthetic | Capture handles, source config | Models, UI | Frame Bus |
| **Frame Bus** | Timestamp, frame_id, fan-out, drop policy, optional resize/undistort | Latest frame + short ring buffer | Inference | Sources, all workers, UI preview |
| **Preprocess** | Resize, color convert, normalize, ROI crop per model | Model-specific tensors | Model weights | Frame Bus → Model Workers |
| **Depth Worker** | Monocular (later stereo) depth estimation | Depth map + confidence if available | Metric scale truth (unless calibrated) | Frame Bus → Spatial Post + State |
| **Detection Worker** | Fixed-class detector (+ optional open-vocab query path) | Boxes/masks, labels, scores | Tracking identity (optional later) | Frame Bus → State |
| **Spatial Post** | Free-space / occupied regions, obstacle cues from depth (+ detections) | Free-space mask/grid, obstacle list | Path planning, control | Depth/Det → State |
| **Perception State Store** | Coherent latest snapshot + short history for API/UI | `PerceptionFrame` documents | Persistence/DB in v1 | Workers, API, UI |
| **Perception Stream API** | REST + WebSocket stream for robots | Wire protocol, auth (local), rate limits | Robot motion | State Store → external clients |
| **Web Dev UI** | Live video, overlays, thresholds, model toggles | Presentation + control RPC | Inference compute | State Store, Control plane |
| **Control / Config plane** | Apply runtime params (thresholds, model on/off, camera select) | Config schema, hot-reload rules | Frame timing | UI → Runtime |
| **Plugin Registry** | Discover/load sources, models, sinks, bridges | Entry points, capability metadata | Business logic of plugins | Runtime bootstrap |
| **ROS2 Bridge (later)** | Publish Sentry topics/msgs; optional subscribe | Adapter only | Core pipeline | State Store ↔ ROS graph |
| **Voice I/O (later)** | Speech in/out as plugins | Audio paths | Perception correctness | Control plane / optional query worker |

### Component contracts (what talks to what)

1. **Sources → Frame Bus only.** Never wire a model directly to OpenCV `VideoCapture`.
2. **Workers read frames; they do not open cameras.**
3. **Workers write results to State Store (or Spatial Post), never to the UI directly.**
4. **UI and robot clients are pure consumers** of State (+ control RPC for UI).
5. **Spatial Post is the only place free-space semantics are defined** (so depth model swaps don’t redefine obstacle meaning).

### Recommended internal package layout (logical)

```
sentry/
  sources/          # USB, RTSP, file, synthetic
  bus/              # Frame, FrameBus, drop policies
  preprocess/       # shared resize/normalize helpers
  models/
    depth/
    detection/
    open_vocab/     # optional path
  spatial/          # free-space, obstacles
  state/            # PerceptionFrame store
  api/              # REST + WebSocket
  ui/               # web dashboard (or separate package)
  control/          # config schema + apply
  plugins/          # entry-point registry
  bridges/          # ros2, voice (stubs in v1)
```

---

## Data Flow

### Forward path (hot path)

```
Camera Source
  → Frame {frame_id, t_capture, t_ingest, camera_id, image, camera_info?}
  → Frame Bus (drop-oldest / keep-latest per consumer)
  → Parallel workers (same frame_id):
        Depth Worker  → DepthResult
        Detection Worker → DetectionResult
        [Open-vocab Worker on demand / lower rate]
  → Spatial Post:
        DepthResult (+ optional DetectionResult)
        → FreeSpaceResult + ObstacleCues
  → Perception State Store:
        PerceptionFrame = merge by frame_id / latest complete set
  → Fan-out:
        WebSocket perception stream (robot)
        Web UI overlay stream (developer)
        [ROS2 bridge]
```

### Control path (cold path)

```
Web UI / REST
  → ConfigUpdate {thresholds, model toggles, camera source, rates}
  → Control plane validates + applies
  → Workers reconfigure (non-blocking; next frames use new config)
  → State Store emits ConfigApplied event to UI
```

### Timing and synchronization rules

| Rule | Why |
|------|-----|
| Every message carries `frame_id` + `t_capture` | Correlate depth + detections even if workers finish out of order |
| Prefer **same-frame merge** with timeout (e.g. 1–2 frame periods) | Partial results still useful; don’t block forever |
| UI can show **latest partial**; robot API documents completeness flags | Developers want snappy UI; robots need honest quality bits |
| Camera capture rate ≥ model rate; **drop intermediate frames** | Classic realtime CV: never grow unbounded queues |
| Separate preview resolution from model resolution | UI at 720p stream; models at 320–640 class inputs (Isaac ROS resize pattern) |

### Free-space derivation (v1 recommendation)

Monocular depth models (MiDaS / Depth Anything family) produce **relative** depth unless metric models / calibration are used. Architecture should:

1. Store **raw depth map** + `depth_kind: relative | metric`.
2. Derive free-space in **image plane** first (near/mid/far bands, ground assumption optional).
3. Optionally project a coarse **occupancy strip / bird’s-eye band** if camera_info + height/pitch known — mark as approximate.
4. **Never claim LiDAR-grade metric free-space** in the API schema without calibration metadata.

```
Depth map → threshold/band → free vs occupied mask
         → optional: ground plane / pitch prior → BEV occupancy strip
         → obstacle blobs (connected components + depth stats)
         → publish FreeSpaceResult
```

### Data shapes (conceptual)

```text
Frame:
  frame_id: u64
  camera_id: str
  t_capture: float (epoch or monotonic; document which)
  image: HWC uint8 (or GPU handle later)
  camera_info?: {fx,fy,cx,cy,distortion,width,height}

DepthResult:
  frame_id, t_infer
  depth: HxW float32
  depth_kind: "relative" | "metric"
  unit?: "m" | null
  confidence?: HxW

DetectionResult:
  frame_id, t_infer
  detections: [{bbox_xyxy, score, class_id, class_name, track_id?}]
  masks?: optional

FreeSpaceResult:
  frame_id
  free_mask?: HxW uint8
  occupied_mask?: HxW uint8
  obstacles: [{bbox or contour, depth_stats, label?}]
  grid_bev?: optional coarse grid

PerceptionFrame:   # API document
  frame_id, camera_id, timestamps
  completeness: {depth, detections, free_space}
  depth?, detections?, free_space?
  preview_jpeg? / overlay hooks
```

---

## Process / Concurrency Model

### Recommended v1: single process, multi-threaded workers

Mirrors ROS 2 **component_container_mt** and DepthAI’s “one pipeline, many nodes” without requiring ROS.

| Thread / async role | Work | Notes |
|---------------------|------|-------|
| **Capture thread** | Blocking camera I/O | Never do inference here |
| **Worker pool (depth)** | GPU/CPU inference | 1 outstanding job typical (drop if busy) |
| **Worker pool (detection)** | GPU/CPU inference | Share GPU carefully; serialize GPU submits if needed |
| **Spatial post** | CPU light | Can run inline after depth or dedicated thread |
| **API event loop** | asyncio (FastAPI/Starlette) | Publish from state; don’t run models in request handlers |
| **UI static + WS** | Same server process or reverse-proxied | Dev simplicity on desktop |

**GPU policy:** one process owns the GPU. If depth + detection both GPU-bound, use **round-robin or priority** (depth for nav safety, detection for UI) rather than two processes fighting VRAM.

### Queue policies (critical)

| Queue | Depth | Policy |
|-------|-------|--------|
| Capture → Bus | 1–2 | Keep latest, drop old |
| Bus → Worker | 1 | If worker busy, skip frame (count drops) |
| Worker → State | unbounded short | Results are smaller; still cap ring (e.g. 8–32) |
| State → WS clients | per-client 1–2 | Slow clients drop; never backpressure capture |

### Latency budget (targets, not guarantees)

| Stage | Desktop GPU | Edge (Jetson-class) | Pi-class + accelerator |
|-------|-------------|---------------------|-------------------------|
| Capture | 5–15 ms | 10–30 ms | 15–40 ms |
| Detection | 5–25 ms | 15–50 ms | 50–200 ms |
| Depth | 10–40 ms | 30–80 ms | 80–300 ms |
| Spatial post | <5 ms | <10 ms | <20 ms |
| WS publish | <5 ms | <10 ms | <15 ms |

**Implication:** edge may run depth and detection at different rates (e.g. det 15 Hz, depth 8 Hz). Architecture must allow **asynchronous rates** with completeness flags.

### When to multi-process later

Split only if measured need:

- Crash isolation for experimental models
- Separate GPU contexts / TensorRT engines that conflict
- Edge: offload API/UI to host machine, perception on robot

Use IPC via shared memory frames + Unix sockets / ZMQ for results — not for v1.

---

## Extension Points

Design these **now** as interfaces even if stubs:

### 1. Multi-camera (post-v1)

```
CameraSource (camera_id)
  → FrameBus (keyed by camera_id)
  → Workers: either per-camera instances or batched
  → Fusion plugin (later): multi-view free-space
  → State: multi-camera PerceptionScene
```

**Extension rule:** all schemas include `camera_id`. Never assume one global frame.

### 2. Voice I/O (post-v1)

Voice is a **control / query plugin**, not a perception stage:

- Speech-to-text → Control plane (“enable open-vocab: person with red hat”)
- Optional TTS from events (“obstacle within 1 m”) — **event subscriber only**

Do not put audio on the frame bus.

### 3. ROS2 bridge (non-blocking, post-v1)

```
Perception State Store
  → ros2_bridge plugin
      /sentry/color/image_raw
      /sentry/depth/image
      /sentry/detections
      /sentry/free_space
```

Core remains ROS-free. Bridge is optional package; use standard message types where possible (`sensor_msgs`, `vision_msgs`) so Foxglove/RViz work without custom plugins.

### 4. Model backend swap

Isaac ROS pattern: **encoder / inference / decoder** split.

```
ModelBackend protocol:
  name, device_targets, load(), infer(tensor) -> tensor
  backends: torch, onnxruntime, tensorrt, openvino, ...

TaskHead protocol:
  preprocess(Frame) -> tensor
  postprocess(tensor, Frame) -> Result
```

v1 can ship PyTorch/ONNX; TensorRT/OpenVINO as edge acceleration path without changing Spatial Post or API.

### 5. Open-vocabulary detection

Separate worker with **on-demand or lower-rate** schedule:

- Fixed-class YOLO-style runs every frame (table stakes).
- Open-vocab (e.g. OWL-ViT / Grounding-DINO class) runs on query change or 1–5 Hz.

Expose via control plane: `set_queries(["cone", "dog"])`.

### 6. Navigation cues (future, still perception-only)

Optional plugin that turns free-space into **hints** (e.g. preferred heading sector). Still **not** a controller — publish advisory only.

---

## Suggested Build Order

Order is dependency-driven: each step produces a demoable vertical slice.

| Phase | Build | Unlocks | Avoids |
|-------|-------|---------|--------|
| **1. Skeleton + contracts** | Repo layout, `Frame`/`PerceptionFrame` schemas, plugin registry stubs, config schema | Shared types for all later work | Ad-hoc dicts between modules |
| **2. Camera ingestion + Frame Bus** | USB + file + synthetic sources; keep-latest bus; drop metrics | Realtime loop without models | Binding models to OpenCV capture |
| **3. API shell + live preview** | FastAPI REST health + WebSocket raw/preview frames; minimal web page | End-to-end “camera works” demo | Building UI without data path |
| **4. Detection worker** | Fixed-class detector plugin; overlay boxes on UI; stream detections JSON | First robot-usable signal | Depth complexity first |
| **5. Depth worker** | Monocular depth model; depth viz colormap; stream depth (downsampled / encoded) | Spatial awareness path | Full metric calibration rabbit hole |
| **6. Free-space / obstacles** | Spatial post from depth; masks + obstacle list; UI overlay | Core product thesis | SLAM / full map |
| **7. Perception stream completeness** | Merged `PerceptionFrame`, completeness flags, REST snapshot + WS stream docs | Stable robot integration | Ad-hoc multi-endpoint soup |
| **8. Developer controls** | Thresholds, model toggles, source switch, rate limits — control plane | Interactive debugging | Restart-to-tune workflow |
| **9. Open-vocab path** | Query-driven secondary worker | Differentiator | Replacing fixed-class as primary |
| **10. Edge packaging** | Jetson/Pi deploy profile, lighter models, rate defaults, optional headless | Multi-target claim | Designing only for desktop GPU |
| **11. Extension stubs** | ROS2 bridge scaffold, multi-cam `camera_id` tests, voice plugin no-op | Future without rewrite | Premature full ROS/voice |

### Build-order dependency graph

```
Schemas ──▶ Frame Bus ──▶ Preview API/UI
                │
                ├────▶ Detection ──┐
                │                  ├─▶ State merge ──▶ Robot stream polish
                └────▶ Depth ──▶ Free-space ──┘
                                      │
                                      └──▶ Controls (can start earlier but polish late)
```

**Why detection before depth:** faster to ship, easier to validate overlays, teaches worker pattern with simpler outputs.  
**Why free-space after depth:** free-space is a **consumer** of depth (and optionally detections).  
**Why controls after streams exist:** need something to control; wire config early as stubs, polish after outputs visible.  
**Why edge late but not last:** architecture must not hardcode CUDA desktop paths in phases 2–6 (abstract `device`).

---

## Interface Contracts (perception stream, UI events)

### Perception Stream API

**Transport:**

| Channel | Use | Format |
|---------|-----|--------|
| `GET /v1/health` | Liveness, device, model status | JSON |
| `GET /v1/snapshot` | Latest complete/partial `PerceptionFrame` | JSON (+ optional binary parts) |
| `WS /v1/stream` | Continuous perception | Multipart or typed JSON messages |
| `GET /v1/config` / `PUT /v1/config` | Runtime config | JSON |
| `WS /v1/events` (optional) | Control acks, drops, errors | JSON |

**WebSocket message envelope (recommended):**

```json
{
  "type": "perception_frame",
  "schema_version": 1,
  "frame_id": 12345,
  "camera_id": "cam0",
  "t_capture": 1720000000.123,
  "t_publish": 1720000000.145,
  "completeness": {"depth": true, "detections": true, "free_space": true},
  "detections": {
    "items": [
      {"bbox_xyxy": [10, 20, 80, 200], "score": 0.91, "class_id": 0, "class_name": "person"}
    ]
  },
  "depth": {
    "kind": "relative",
    "width": 320,
    "height": 240,
    "encoding": "raw_f32_b64_or_png16",
    "data_ref": "inline|next_binary_frame"
  },
  "free_space": {
    "obstacles": [{"bbox_xyxy": [100, 120, 180, 240], "depth_mean": 0.42, "depth_kind": "relative"}],
    "mask_ref": "optional"
  },
  "stats": {"capture_fps": 30.0, "det_fps": 18.2, "depth_fps": 12.1, "dropped_frames": 4}
}
```

**Binary strategy:** JSON metadata + optional binary WebSocket frames for depth/mask/jpeg preview (Foxglove-like separation of structure vs bulk). For v1 simplicity, JPEG preview + downsampled depth PNG16 is acceptable; document upgrade path to raw binary.

**Robot consumer guarantees:**

- Sentry **never** sends velocity commands.
- Stream is **lossy** under load (latest wins).
- `completeness` tells clients what is trustworthy this frame.
- Schema versioned; additive fields only within major version.

### UI events

| Event | Direction | Payload |
|-------|-----------|---------|
| `preview_frame` | server → UI | jpeg/base64 or binary + frame_id |
| `overlays` | server → UI | detections, free-space contours, depth colormap toggle state |
| `metrics` | server → UI | fps, latency, drops, device temp if available |
| `set_config` | UI → server | thresholds, toggles, source id, queries |
| `config_applied` | server → UI | effective config echo |
| `error` | server → UI | recoverable vs fatal |

**UI architecture rule:** overlays are **derived client-side or server-side from the same PerceptionFrame** the robot sees — no private “UI-only” perception path. That keeps developer trust aligned with robot output.

### Control config schema (minimal)

```json
{
  "source_id": "usb0",
  "models": {
    "detection": {"enabled": true, "score_threshold": 0.35, "backend": "default"},
    "depth": {"enabled": true, "backend": "default"},
    "open_vocab": {"enabled": false, "queries": []}
  },
  "free_space": {"near_threshold": 0.3, "publish_mask": true},
  "stream": {"jpeg_quality": 70, "max_fps": 15, "include_depth": true}
}
```

---

## Deployment Topologies

### A. Desktop development (primary)

```
[USB / RTSP camera]
        │
        ▼
[Sentry process: capture + models on discrete GPU + API + UI static]
        │
        ├── browser → http://localhost:PORT  (dev UI)
        └── robot sim / scripts → WS /v1/stream
```

- Hot reload / verbose metrics on.
- Heavier models allowed.
- File/synthetic sources for CI.

### B. Edge robot (Jetson-class)

```
[CSI/USB camera] → [Sentry headless on Jetson]
                        │
                        ├── WS/REST on LAN → laptop browser (UI optional remote)
                        └── local robot stack consumes /v1/stream
```

- Prefer TensorRT/ONNX-optimized backends.
- Lower default resolutions and FPS.
- UI not required on-device; API is the product surface.

### C. Edge lite (Pi-class)

```
[Camera] → [Sentry with tiny models / NPU accel if present]
              │
              └── stream detections + coarse free-space only
                  (depth model optional / lower rate)
```

- Architecture must degrade gracefully: detection-only mode still valid.
- Completeness flags express missing depth.

### D. Split topology (optional later)

```
Robot: capture + inference + API
Dev laptop: UI only (connect to robot host)
```

Requires CORS/bind config and optional auth token for LAN. Design API host binding for this from phase 3.

### Multi-target implications (build into core)

| Concern | Approach |
|---------|----------|
| Device abstraction | `torch`/`ort` device string; no hardcoded `cuda:0` in bus |
| Model packs | `models/desktop` vs `models/edge` manifests |
| Feature flags | depth optional; open-vocab optional |
| Performance knobs | max_fps, input_size, which workers enabled — all config |
| CI | synthetic camera + CPU models smoke test |

---

## Patterns to Follow

### Pattern 1: Encode → Infer → Decode (Isaac ROS)

Keep model I/O conversion out of the inference backend. Swapping TensorRT vs ONNX should not rewrite bbox decoding.

### Pattern 2: Pipeline nodes + messages (DepthAI)

Every stage is a node with typed inputs/outputs. Host “device” is the runtime that schedules them.

### Pattern 3: Latest-frame realtime

If a stage is busy, drop frames. Count drops. Expose drops on `/health` and UI metrics.

### Pattern 4: UI as subscriber (Foxglove-like)

Visualization never drives perception timing. Controls are async config updates.

### Pattern 5: Perception-only boundary

Clean product boundary: robots plan/control elsewhere. This matches Autoware-style stack layering without shipping the whole stack.

---

## Anti-Patterns to Avoid

| Anti-pattern | Why it hurts | Instead |
|--------------|--------------|---------|
| OpenCV capture inside model loop | Can’t multi-consume frames; untestable | Frame Bus |
| Unbounded queues “to be safe” | Latency spiral, OOM | Keep-latest depth 1 |
| UI-only detection path | Robot sees different world than developer | Single State Store |
| Metric free-space claims without calibration | Unsafe robot behavior | `depth_kind` + honesty in schema |
| Hard ROS2 dependency in v1 | Blocks makers who just want HTTP/WS | Optional bridge |
| One mega-model for all tasks | Hard to swap, hard to edge-tune | Parallel workers + plugins |
| Synchronous REST for every frame | Terrible latency | WebSocket stream |
| Putting planner/controller in Sentry | Scope creep; breaks “any robot” | Perception stream only |
| Ignoring `camera_id` / timestamps | Multi-cam rewrite later | Include from day one |

---

## Scalability Considerations

| Concern | 1 camera desktop | Edge robot | Multi-cam / multi-client |
|---------|------------------|------------|---------------------------|
| Capture | 1 thread | 1 thread | N sources → bus |
| Inference | 2 workers GPU | Rate-limit workers | Per-cam or batched |
| API clients | 1–2 WS | 1 robot + 1 UI | Fan-out with per-client drop |
| State | Latest + ring 16 | Latest + ring 8 | Scene graph later |
| Process model | Single process | Single process | Split UI host vs edge |

v1 success criterion is **not** 1M users — it is **stable ≤100 ms-class perception loop on desktop** and a **documented degraded profile on edge**.

---

## Implications for Roadmap Phases

1. **Ingest + bus + preview** before any model (proves realtime skeleton).  
2. **Detection** then **depth** then **free-space** (dependency + demo value).  
3. **Unified perception stream** as soon as two products exist (detections + depth).  
4. **Controls** once stream exists.  
5. **Edge pack** after correctness, with backend abstraction already in place.  
6. **ROS2 / multi-cam / voice** as explicit extension phases — interfaces reserved earlier.

---

## Sources

| Source | What it informed | Confidence |
|--------|------------------|------------|
| [Isaac ROS DNN Inference](https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_dnn_inference/index.html) | Encode → infer → decode graph; TensorRT/Triton; x86 + Jetson multi-target | HIGH |
| [Isaac ROS Image Pipeline](https://nvidia-isaac-ros.github.io/repositories_and_packages/isaac_ros_image_pipeline/index.html) | Resize/rectify as separate stages | HIGH |
| [DepthAI components / pipeline](https://docs.luxonis.com/software-v3/depthai/) | Nodes, messages, pipeline graph model | HIGH |
| [ROS 2 Composition](https://docs.ros.org/en/humble/Concepts/Intermediate/About-Composition.html) | Component containers, multi-threaded executors, intra-process | HIGH |
| [Autoware Universe perception tree](https://github.com/autowarefoundation/autoware_universe/tree/main/perception) | Modular detect/classify/track/TensorRT packages | MEDIUM (structure via tree, not full design docs) |
| [Ultralytics predict Results](https://docs.ultralytics.com/modes/predict/) | Detection result fields for API shape | HIGH |
| [MiDaS](https://github.com/isl-org/MiDaS) / monocular depth ecosystem | Relative depth, resize practices | HIGH |
| [FastAPI WebSockets](https://fastapi.tiangolo.com/advanced/websockets/) | API server pattern for stream | HIGH |
| [Foxglove ROS 2](https://docs.foxglove.dev/docs/connecting-to-data/frameworks/ros2) | Viz as bridge/subscriber | MEDIUM |
| [ROS image_pipeline](https://github.com/ros-perception/image_pipeline) | Classic camera → rectify → process layering | MEDIUM |

**Gaps / phase-specific research later:**

- Exact free-space algorithm (ground plane vs pure depth bands) needs a focused spike once depth model is chosen.
- Shared-GPU scheduling between depth and detection on Jetson needs measurement, not theory.
- Binary WS framing vs multipart HTTP for depth maps — decide at stream polish phase.
- Auth model for LAN robot exposure — only when leaving localhost.

---

*Architecture research for Sentry AI roadmap. Do not treat free-space as metric navigation truth without calibration metadata in the wire format.*
