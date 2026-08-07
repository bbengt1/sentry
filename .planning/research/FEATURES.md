# Features Research

**Domain:** Camera-only (vision-only) robotics perception for open-source maker tools  
**Researched:** 2026-08-07  
**Confidence:** HIGH (ecosystem patterns validated against DepthAI/OAK, RealSense, ZED, YOLO/Ultralytics, MiDaS/Depth Anything/ZoeDepth, Nav2, Foxglove/Rerun, MediaPipe; product gap analysis vs Sentry PROJECT.md)

## Ecosystem Context

Maker spatial awareness today clusters into three imperfect options:

| Cluster | Examples | What makers get | What they don't get |
|---------|----------|-----------------|---------------------|
| **Specialized depth cameras** | Luxonis OAK-D / DepthAI, Intel RealSense, StereoLabs ZED | Metric stereo/structured-light depth, often with onboard NN | Works only with *their* hardware; cost & form-factor lock-in |
| **CV model libraries** | Ultralytics YOLO, MediaPipe, MiDaS / Depth Anything V2, Grounding DINO / YOLO-World | Detection, tracking, open-vocab, monocular depth *as components* | No integrated robot-facing product (API + free space + dashboard) |
| **Full robot stacks** | ROS2 + Nav2, Isaac ROS, Autoware-class perception | Costmaps, planning hooks, fleet-grade tooling | Heavy install, sensor-suite assumptions, not "plug in a webcam" |

**Sentry AI's gap:** a product-shaped, camera-only perception layer that runs local OSS models on commodity USB/IP cameras, produces depth + free-space/obstacles + detections, and exposes both a realtime web developer UI and a clean robot consumption API — without requiring LiDAR, proprietary depth hardware, or a full navigation stack.

---

## Table Stakes

Features users expect. Missing any of these makes the product feel incomplete or unusable as a maker perception tool.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Commodity camera ingest** | Makers already own USB webcams / Pi cams / IP cams; competitors lock to OAK/RealSense/ZED | Med | USB UVC, RTSP/HTTP network, file/synthetic for tests. YOLO-style multi-source ingest is the market baseline. |
| **Live video + perception overlays** | Debugging vision without overlays is blind; Foxglove/Rerun/DepthAI demos all show this | Med | RGB frame + boxes, depth colormap, free-space/obstacle highlight. Table stakes is *visible correctness*, not pretty UI. |
| **Monocular depth map stream** | "Camera-only spatial awareness" is the core promise; depth is the primitive | High | Relative depth is acceptable for v1 free-space; metric depth is harder (ZoeDepth-class / metric DA-V2 heads, calibration). Label outputs clearly as relative vs metric. |
| **Free space / obstacle regions** | Robots need actionable occupancy, not raw depth alone; Nav2 costmaps set this expectation | Med–High | Derive from depth (threshold near-field, ground plane heuristic, or simple occupancy grid). Not full SLAM. |
| **Fixed-class object detection** | Every maker vision demo has boxes; MediaPipe/YOLO set the floor | Med | COCO-class or similar; conf scores + bboxes; score threshold + class filter. |
| **Confidence / threshold controls** | MediaPipe, YOLO, DepthAI all expose score thresholds; makers tune for false positives | Low | Runtime adjustable: detection conf, depth cutoffs, overlay toggles. |
| **Machine-readable perception API** | Without a stream, it's a demo not a robot component | Med | Depth map + detections + free-space/obstacles over REST and/or WebSocket; stable schema + timestamps/frame IDs. |
| **Local OSS inference path** | Privacy, offline workshops, no cloud bill; PROJECT constraint | Med | No mandatory cloud. Models downloadable/cacheable offline after first pull. |
| **Realtime performance feedback** | FPS / latency is how makers judge "will this drive my bot?" | Low | Per-stage timing (capture, depth, detect, encode) + overall FPS in UI and API metadata. |
| **One-command local dev start** | Maker tools die on 20-step installs | Med | Desktop GPU path first; documented camera plug-in. |
| **Deterministic test / replay source** | File/video input for CI and bug repro; Ultralytics `stream` patterns | Low | Video file + synthetic frames as first-class sources. |
| **Graceful camera failure handling** | USB unplug / RTSP drop is normal | Low | Reconnect, clear error states in UI/API, no silent freeze. |

### Table-stakes quality bar (non-negotiable UX)

- **Frame identity:** every perception packet carries `frame_id` + timestamp so robots can fuse/sync.
- **Coordinate honesty:** document image-frame coords (origin, axis, units); depth units/scale semantics explicit.
- **Overlay parity:** what the API reports is what the dashboard draws (no dual truth).
- **Configurable but safe defaults:** works out of the box; advanced knobs available without editing code.

---

## Differentiators

Features that set Sentry AI apart from libraries (YOLO alone), hardware SDKs (OAK/ZED/RealSense), and heavy stacks (Nav2/Isaac). Not all must ship day one, but they define competitive advantage.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Works with *any* camera first** | Competitors sell depth *cameras*; Sentry sells perception for cameras you already have | Med | Primary differentiator vs OAK/RealSense/ZED. Optional stereo later must not become required. |
| **Integrated depth + free-space + detection product** | Libraries force glue code; Sentry ships the composed pipeline | High | Single process/service: capture → models → fused perception state → API + UI. |
| **Realtime interactive web developer console** | ROS viz / Foxglove assume ROS ecosystem; makers want browser localhost | Med | Live overlays **and** model/threshold controls — not a passive viewer. Developer-first, not chat-first. |
| **Fixed-class + open-vocabulary detection together** | YOLO-World / Grounding DINO enable "find the red toolbox" without retrain | Med–High | Fixed detector for reliable baseline FPS; open-vocab as optional/query path. |
| **Perception-only clean boundary** | Avoids competing with Nav2/ArduPilot; plugs into *any* control stack | Low (discipline) | Output obstacles/free space; never claim path planning or motor control. |
| **Multi-target runtime: desktop GPU + edge** | Dev on laptop, deploy Jetson/Pi-class — Jetson YOLO guides prove demand | High | Model size tiers (nano/small/base); TensorRT/ONNX/NCNN export path later. Edge is first-class, not "maybe someday." |
| **Free-space signal designed for consumers** | Makers want "is path clear?" not only a pretty depth heatmap | Med | Simple occupancy / near-obstacle masks or bird's-eye free-space strip suitable for reactive avoidance. |
| **Model toggle / A-B inspection UI** | Research tools rarely let makers flip depth vs detect models live | Med | Enable/disable stages, swap model variants, inspect intermediate tensors/maps. Builds trust in monocular depth. |
| **Schema-stable robot API with versioning** | Libraries change outputs freely; robots need contracts | Med | `/v1` perception messages; semver; optional ROS2 bridge later without rewriting core. |
| **Extensibility hooks without bloat** | Voice, multi-cam, ROS2 as plugins — not v1 scope creep | Med | Plugin interfaces designed early; implementations deferred. |
| **Privacy-default / offline-first** | Cloud CV APIs (Roboflow hosted, etc.) are non-starters for many makers | Low | No telemetry required; models local. Cloud only as explicit non-default extension. |
| **Honest monocular limitations surfaced in UI** | Differentiates from marketing FSD cosplay | Low | Confidence, relative-vs-metric labels, failure modes (textureless walls, glare) documented in-product. |

### Differentiator priority for v1 product story

1. Commodity camera + monocular depth + free-space (the "Tesla-like for makers" claim, scoped honestly)  
2. Live web overlays + interactive controls  
3. Perception stream API robots can consume  
4. Fixed + open-vocab detection  
5. Desktop + edge path  

---

## Anti-Features / Deliberate Non-Goals

Things to **explicitly not build** in v1 (or ever as core product). Building these causes scope explosion, hardware lock-in, or identity blur.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Required LiDAR / radar / ultrasonic** | Contradicts camera-only thesis | Optional consumer-side fusion outside Sentry |
| **Full SLAM / dense 3D mapping (v1)** | Months of hard problems (loop closure, drift, map IO); delays useful depth+obstacles | Depth + free-space/obstacle signals only; mapping later |
| **Robot control / motion planning** | Competes with Nav2, custom firmware; unbounded safety scope | Perception stream only; document integration recipes |
| **Multi-camera fusion (v1)** | Calibration, sync, bandwidth complexity | Single camera + extension points |
| **Mandatory cloud inference** | Vendor lock-in, privacy, latency, workshop offline needs | Local OSS default |
| **Hardware-locked depth camera requirement** | Becomes "yet another OAK/ZED wrapper" | Commodity cameras first; optional stereo/depth-cam adapter later |
| **Fleet / multi-robot cloud dashboard** | Enterprise product, not maker core | Local single-robot developer UI |
| **Voice I/O (v1)** | Separate stack (ASR/TTS, wake word); dilutes perception MVP | Extension hooks only |
| **Chat / scene Q&A as primary UI (v1)** | Fun demo, poor for tuning thresholds and latency | Overlay + controls first; NL later |
| **End-to-end "FSD" / autonomous driving claims** | Liability, overpromise; monocular hobby systems are not vehicle-grade | Scoped spatial awareness + detection language |
| **Training / dataset labeling platform** | Roboflow/Ultralytics HUB territory; huge surface | Use pretrained OSS; document external fine-tune later |
| **Instance segmentation / pose / face ID as core (v1)** | Nice YOLO tasks; not needed for free-space + obstacles MVP | Optional later plugins if demand appears |
| **Metric depth guarantees without calibration** | Monocular metric is domain-sensitive (indoor/outdoor heads); false precision harms robots | Ship relative depth + optional metric models with caveats; calibration helpers later |
| **Dense mesh / NeRF / Gaussian splat reconstruction** | Research showpiece, not realtime robot perception | Out of scope |
| **Mandatory ROS2 dependency** | Alienates non-ROS makers (Arduino, custom Python, VEX-adjacent stacks) | HTTP/WebSocket first; optional ROS2 bridge later |
| **Proprietary model weights as core path** | License and reproducibility issues | OSS models only for default pipeline |
| **Always-on recording / cloud upload of camera** | Privacy landmine for home robots | Local optional record-to-disk only, off by default |

---

## Feature Dependencies

```
Camera sources (USB / RTSP / file)
    → Frame capture + timestamps
        → Live video preview
        → Monocular depth model
            → Depth map API
            → Free-space / obstacle derivation
                → Obstacle overlay + obstacle API
        → Fixed-class detector
            → Detection boxes API + overlay
        → Open-vocab detector (optional path)
            → Query-time classes / prompts
        → WebSocket/REST perception stream  ← requires all outputs above
        → Interactive controls (thresholds, toggles)
            → Overlay refresh / model enable flags
        → Performance metrics (FPS, stage latency)

Desktop GPU runtime
    → Model download/cache
    → Edge export / lighter models (later, depends on stable pipeline)

Plugin interface (early design)
    → Future: multi-cam, ROS2 bridge, voice, stereo depth adapter
```

**Critical path for usable MVP:**

1. Camera ingest + timestamps  
2. Depth model + depth stream  
3. Free-space/obstacles from depth  
4. Fixed-class detection  
5. Dashboard overlays + controls  
6. Perception API  

Open-vocab, edge optimization, ROS2, and metric depth refinement can layer on this spine.

---

## Complexity Matrix

| Feature | Complexity | Risk | Rationale |
|---------|------------|------|-----------|
| USB camera ingest | Low–Med | Driver quirks, formats, exposure | Well-trodden (OpenCV/V4L2); still platform-specific pain |
| RTSP / network cameras | Med | Latency, codec, reconnect | Common but flaky in the wild |
| File / synthetic sources | Low | — | Essential for tests |
| Monocular relative depth | Med–High | Quality varies by scene; model size | Depth Anything V2 / MiDaS-class; realtime on edge hard |
| Monocular metric depth | High | Domain shift indoor/outdoor; scale ambiguity | ZoeDepth archived; metric heads need careful model choice |
| Free-space / obstacles from depth | Med–High | Ground plane assumptions fail on stairs/ramps | Start simple (near-field occupancy); iterate |
| Fixed-class detection | Med | Mature (YOLO) | Mostly integration + performance |
| Open-vocabulary detection | Med–High | Heavier models; prompt UX | YOLO-World real-time path preferred over heavy Grounding DINO for makers |
| Multi-object tracking IDs | Med | Optional for v1 | YOLO track modes exist; not required for free-space MVP |
| Web live overlays | Med | Bandwidth, encode, browser FPS | MJPEG/WebRTC/canvas tradeoffs |
| Interactive model controls | Med | State sync UI ↔ pipeline | Core differentiator; design early |
| REST snapshot API | Low | — | Easy complement to stream |
| WebSocket perception stream | Med | Schema stability, backpressure | Primary robot interface |
| ROS2 bridge | Med–High | QoS, msgs, install matrix | Defer; design message shapes compatible |
| Edge (Jetson) optimization | High | TensorRT, power, thermal | First-class goal but phase after desktop correctness |
| Pi-class without accelerator | High | May not hit realtime full pipeline | Model tiering / stage disable required |
| Multi-camera fusion | High | Calibration, sync | Explicit non-goal v1 |
| SLAM / mapping | Very High | Research + product risk | Non-goal v1 |
| Stereo from dual commodity cams | High | Extrinsics calibration | Extension later |

---

## Recommended v1 Scope vs Later

### v1 — Must ship (table stakes + core differentiators)

| Priority | Feature | Category |
|----------|---------|----------|
| P0 | USB + file camera sources | Table stakes |
| P0 | Monocular depth map (relative OK) | Table stakes |
| P0 | Free-space / obstacle regions from depth | Table stakes |
| P0 | Fixed-class object detection | Table stakes |
| P0 | Live web dashboard: video + depth + detection + obstacle overlays | Table stakes + differentiator |
| P0 | Interactive controls: conf thresholds, stage toggles, depth cutoff | Table stakes + differentiator |
| P0 | Perception stream API (depth, detections, free-space/obstacles) with frame_id/timestamps | Table stakes + differentiator |
| P0 | Local OSS models only; offline-capable after model cache | Table stakes |
| P0 | FPS / latency telemetry in UI + API metadata | Table stakes |
| P1 | Network/IP (RTSP) camera source | Table stakes (slightly softer if USB solid) |
| P1 | Open-vocabulary detection (promptable classes) | Differentiator |
| P1 | Desktop GPU primary path documented end-to-end | Table stakes |
| P1 | Schema versioning (`v1` messages) + clear depth semantics docs | Differentiator |
| P1 | Plugin/extension points (stubs) for multi-cam, ROS2, voice | Differentiator (hooks only) |

### v1 — Nice if cheap (do not block MVP)

- Simple local recording of annotated video for debugging  
- Detection class allow/deny lists  
- Depth colormap style options  
- Optional point-cloud-ish preview from depth (debug only, not mapping)  
- Basic multi-object tracking IDs (if YOLO track is nearly free)

### Later (post-v1) — Valuable, not MVP

| Feature | Why later |
|---------|-----------|
| Edge-optimized builds (Jetson TensorRT / ONNX Runtime) | Needs stable models + profiling after desktop pipeline works |
| Pi + accelerator tier with reduced pipeline | Hardware matrix expansion |
| Optional metric depth models + simple scale calibration | Harder correctness story |
| Optional stereo / depth-camera adapters (RealSense/OAK as *sources*, not requirements) | Extends hardware; must not invert product thesis |
| ROS2 bridge package | Ecosystem reach after API schema is stable |
| Multi-camera support | Calibration + fusion research |
| Lightweight mapping / occupancy grid history | Natural evolution of free-space |
| Scene chat / VLM Q&A | After developer console is solid |
| Voice I/O plugins | Explicitly deferred |
| Segmentation / pose plugins | Demand-driven |
| Model fine-tune documentation / export recipes | Power users only |

### Never as core (anti-features)

- Required non-camera depth sensors  
- Full autonomous control stack  
- Cloud-mandatory inference  
- Fleet SaaS  
- "Full self-driving" product positioning  

---

## Competitive Feature Checklist (what others ship)

| Capability | OAK/DepthAI | RealSense | ZED | YOLO alone | Nav2 | Foxglove/Rerun | **Sentry AI target** |
|------------|:-----------:|:---------:|:---:|:----------:|:----:|:--------------:|:--------------------:|
| Commodity USB/IP camera | — | — | — | ✓ | via drivers | viz only | **✓ core** |
| Metric stereo/structured depth | ✓ | ✓ | ✓ | — | consumes | viz | optional later |
| Monocular NN depth productized | partial | — | — | — | — | — | **✓ core** |
| Free-space / obstacles | DIY | DIY | DIY | — | ✓ costmaps | viz | **✓ core** |
| Fixed-class detection | ✓ | DIY | ✓ | ✓ | DIY | viz | **✓ core** |
| Open-vocab detection | DIY | — | — | ✓ (World) | — | — | **✓ v1** |
| Browser interactive controls | limited apps | — | — | — | — | panels | **✓ core** |
| Robot perception API (non-ROS) | SDK | SDK | SDK | DIY | ROS | — | **✓ core** |
| Local OSS, no proprietary HW | — | — | — | ✓ | ✓ | ✓ | **✓ core** |
| Full navigation / control | — | — | — | — | ✓ | — | **✗ anti** |
| SLAM / mapping | limited | DIY | tracking | — | stacks | viz | **✗ v1** |

---

## Implications for Requirements

Aligns with and refines `.planning/PROJECT.md` Active requirements:

1. **Keep** camera-only depth + free-space, USB/network/file sources, local OSS, web overlays+controls, fixed+open-vocab, perception API, single-cam first, desktop+edge, extensibility hooks.  
2. **Clarify v1 depth contract:** relative monocular depth is acceptable; metric is optional/experimental with explicit labeling.  
3. **Clarify free-space contract:** simple occupancy/obstacle regions from depth, not Nav2-grade costmaps.  
4. **API before ROS2:** HTTP/WebSocket is table stakes; ROS2 is differentiator later.  
5. **Open-vocab is P1 differentiator**, not P0 blocker — fixed-class detection must ship first.  
6. **Do not expand v1** into SLAM, control, multi-cam fusion, voice, or cloud-required paths.

---

## Sources

| Source | Use | Confidence |
|--------|-----|------------|
| [Ultralytics YOLO tasks / predict sources / YOLO-World / track / Jetson guide](https://docs.ultralytics.com/) | Detection, open-vocab, multi-source ingest, tracking, edge deploy baseline | HIGH |
| [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) | SOTA monocular depth + metric/point-cloud paths | HIGH |
| [MiDaS](https://github.com/isl-org/MiDaS) / [ZoeDepth](https://github.com/isl-org/ZoeDepth) (archived May 2025) | Relative vs metric monocular depth lineage | HIGH |
| [MediaPipe Object Detector](https://ai.google.dev/edge/mediapipe/solutions/vision/object_detector) | Edge detection feature set (threshold, top-k, allow/deny lists) | HIGH |
| [Nav2 concepts / costmaps](https://docs.nav2.org/concepts/index.html) | Free-space/occupancy expectations from robot stacks | HIGH |
| [DepthAI / Luxonis docs](https://docs.luxonis.com/) | Hardware-coupled maker depth+NN competitor shape | HIGH |
| [StereoLabs ZED object detection / depth / tracking](https://www.stereolabs.com/docs/) | Proprietary stereo product feature bundle | HIGH |
| [Intel RealSense ROS](https://github.com/IntelRealSense/realsense-ros) | Depth camera + ROS integration pattern | HIGH |
| [Foxglove Image / 3D panels](https://docs.foxglove.dev/) | Robotics visualization overlay expectations | HIGH |
| [Rerun](https://rerun.io/docs/getting-started/what-is-rerun) | Multimodal robotics viz / data layer | MEDIUM |
| [Grounding DINO](https://github.com/IDEA-Research/GroundingDINO) | Open-set detection alternative (heavier) | HIGH |
| [Raspberry Pi camera software](https://www.raspberrypi.com/documentation/computers/camera_software.html) | Maker camera + RTSP streaming reality | HIGH |
| Sentry `.planning/PROJECT.md` | Product constraints and v1 non-goals | HIGH |

---

## Open Questions (for phase research, not blockers)

1. **Free-space algorithm v1:** near-field depth threshold vs ground-plane RANSAC vs bird's-eye occupancy strip — which is good enough for reactive avoidance?  
2. **Depth model pick:** Depth Anything V2 small vs other realtime monocular options under desktop and Jetson budgets.  
3. **Open-vocab runtime cost:** always-on YOLO-World vs on-demand query mode.  
4. **Stream transport:** WebSocket binary (msgpack/protobuf) vs JSON frames vs dual REST snapshot + WS preview.  
5. **Edge floor:** which Jetson class is the minimum "first-class" target for full pipeline FPS?

---

*Research dimension: Features only. Stack, architecture, and pitfalls are covered by sibling research files.*
