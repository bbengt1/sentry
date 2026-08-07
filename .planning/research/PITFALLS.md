# Pitfalls Research

**Domain:** Camera-only monocular depth + realtime object detection for maker robotics  
**Project:** Sentry AI  
**Researched:** 2026-08-07  
**Confidence:** HIGH (core geometric/latency pitfalls); MEDIUM (product-scope and licensing edge cases)

Camera-only spatial awareness is seductive because demos look great and hardware is cheap. The failure modes that kill maker products are rarely “model not SOTA enough” — they are **metric scale lies**, **end-to-end latency**, **camera chaos**, **overpromise vs Tesla-FSD branding**, and **shipping a perception stream that robots cannot safely trust**.

---

## Critical Pitfalls

### 1. Treating relative depth as metric meters

**What goes wrong:**  
Relative / affine-invariant monocular models (MiDaS, Depth Anything V2 base relative models, etc.) output **relative inverse depth** or scale-ambiguous depth. Teams colorize the map, see sharp edges, and expose “depth in meters” on the API. Robots then plan stops at 0.8 m that are actually 2.5 m — or crash into objects that looked “far.”

**Why it happens:**  
Demos and papers optimize for visual quality and ranking metrics (δ1, AbsRel after scale alignment). Robotics needs **absolute scale**. Relative models are often used because they are faster, more general, and easier to run. Metric fine-tunes exist (Depth Anything V2 metric indoor/outdoor, Metric3D, ZoeDepth lineage) but are domain-split and still imperfect zero-shot.

**Warning signs:**
- API field named `depth_m` with no scale provenance or confidence
- Depth values change when camera zooms or FOV changes without corresponding geometry
- “Looks correct” in colorized overlay but fails a tape-measure test
- Same scene produces different absolute ranges after restart or model swap
- Free-space thresholds hardcoded in meters on relative outputs

**Prevention:**
- Explicitly type depth in the API: `relative` | `metric_estimated` | `metric_calibrated`
- Never call relative output “meters” in UI or docs
- Prefer metric models when obstacle distance matters; document indoor vs outdoor heads (DA-V2: Hypersim max_depth≈20 m indoor, VKITTI max_depth≈80 m outdoor)
- Offer optional scale calibration (known object size, ground plane + camera height, stereo assist later)
- Ship a **trust score / uncertainty** channel, not just a depth map

**Phase to address:** Perception core / depth model selection (early foundation phase) — before any robot API contract freezes.

**Confidence:** HIGH  
**Sources:** [MiDaS (relative inverse depth)](https://pytorch.org/hub/intelisl_midas_v2/), [Depth Anything V2 metric fine-tunes](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth), [Metric3D FAQ](https://github.com/YvanYin/Metric3D)

---

### 2. Ignoring camera intrinsics (beautiful depth, broken geometry)

**What goes wrong:**  
Depth maps look fine; back-projected point clouds / free-space polygons are stretched, curved, or wrong-sized. Metric3D’s own FAQ: *“Why depth maps look good but pointclouds are distorted? Because the focal length is not properly set.”*

**Why it happens:**  
Makers use random USB webcams with unknown/wrong EXIF, digital zoom, auto-crop, or driver-reported resolutions that differ from the actual active sensor window. Metric models that assume a canonical camera space amplify wrong `fx/fy/cx/cy`.

**Warning signs:**
- Obstacles look closer on image edges than center (or vice versa)
- Ground plane tilts when camera pitch is level
- Changing resolution (720p ↔ 1080p) changes “meters” without re-calibration
- No calibration step in onboarding; intrinsics hard-coded to 518×518 or 640×480 defaults

**Prevention:**
- Require or strongly guide camera calibration (OpenCV checkerboard or Charuco) for any metric/3D path
- Store per-camera profiles: resolution, intrinsics, distortion, mounting height/pitch
- If uncalibrated: degrade gracefully to relative depth + image-space free space, not fake metric 3D
- Document that network cameras often need manual FOV/focal entry
- Re-validate intrinsics whenever crop, binning, or digital zoom changes

**Phase to address:** Camera ingestion + calibration UX (early; blocks trustworthy spatial API).

**Confidence:** HIGH  
**Sources:** [Metric3D Q&A](https://github.com/YvanYin/Metric3D), [OpenCV camera calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html)

---

### 3. Overpromising “Tesla FSD–style” vision-only autonomy

**What goes wrong:**  
Marketing / README / UI copy implies production-grade vision-only driving. Makers expect lane-keeping, cross-traffic prediction, and fail-safe navigation. Reality: single monocular camera + hobby compute cannot match multi-camera, fleet-trained, safety-engineered stacks. Trust collapses; project becomes “cool demo that almost hit my dog.”

**Why it happens:**  
Inspiration language bleeds into product claims. Visual overlays look “smart.” Scope creep into control/planning because perception “should just work.”

**Warning signs:**
- Homepage leads with FSD comparisons without “perception only” caveats
- Issues filed as “robot won’t navigate” when only depth/detections ship
- No written safety boundary: “Sentry AI does not control motors”
- Demo videos hide failure cases (glass, mirrors, night, motion blur)

**Prevention:**
- Position as **perception stream for makers**, not autonomy
- Hard product boundary: depth, detections, free-space/obstacles — control is consumer’s job
- Public known-failure list (glass, thin poles, low light, textureless walls, specular floors)
- Require consumers to keep e-stop / bumper / simple fallback sensors for physical robots
- Never auto-publish “safe to proceed” without explicit consumer policy

**Phase to address:** Product positioning + docs from day one; enforce in API design phase.

**Confidence:** HIGH (product risk); domain evidence is community/pattern-level rather than a single paper.

---

### 4. Demo FPS ≠ control-loop latency

**What goes wrong:**  
Dashboard shows 30 FPS video while the robot receives detections that are 200–400 ms stale. UI stream is optimized for smoothness (latest frame, drop intermediate); robot path is coupled to the same pipeline and blocks on model batching, JSON encoding, or WebSocket backpressure.

**Why it happens:**  
Teams measure model forward-pass time on a warm GPU with preloaded tensors, not capture→preprocess→infer→postprocess→serialize→network→consumer. UI and control share one synchronous path. Open-vocab models and full-res depth run every frame.

**Warning signs:**
- “30 FPS” only in the web UI; API timestamps lag wall clock
- Latency spikes when overlays are enabled
- Queue depth grows under load (processing every frame instead of latest-only)
- Edge device “works” on still images but drops to single-digit FPS on live video

**Prevention:**
- Separate **preview path** (lossy, droppable) from **robot perception path** (timestamped, latest-frame, bounded latency)
- Publish end-to-end latency metrics: capture time, inference time, emit time, age-at-consumer
- Default policy: drop intermediate frames; never build unbounded queues
- Budget models by tier: edge “fast” profile vs desktop “quality” profile
- Design dual-rate pipeline: cheap detector every frame, heavy depth every N ms

**Phase to address:** Architecture + streaming API design (before UI polish).

**Confidence:** HIGH

---

### 5. Desktop-only pipeline that cannot reach Jetson / Pi-class targets

**What goes wrong:**  
v1 is a PyTorch research script on an RTX desktop. Edge port is “later.” By then: CUDA-only ops, 335M–1.3B depth models, Python GIL bottlenecks, no TensorRT/ONNX export path, and model licenses that block commercial makers. Edge becomes a rewrite.

**Why it happens:**  
Desktop GPU is the happy path. Multi-target is stated but not enforced by CI. TensorRT engines are device-specific (must build/validate on target SKU). Pi-class may need NPU/accelerator paths that pure PyTorch never exercises.

**Warning signs:**
- No export format (ONNX/TensorRT/CoreML) in milestone definition
- Only Large/Giant models in demos
- “Works on Jetson” claim without published FPS/power numbers
- Dependencies pin bleeding-edge CUDA that JetPack cannot match

**Prevention:**
- First-class **runtime profiles**: `desktop-gpu`, `jetson`, `cpu-fallback` with explicit model sizes
- Prefer exportable models early; validate TensorRT on real Orin/Xavier hardware (engines are not freely portable across SKUs)
- Keep a Small/Base depth + nano/small detector path that hits a published latency budget on target hardware
- CI smoke tests on at least one non-desktop profile (even CPU with tiny models)
- Track JetPack / CUDA / TensorRT matrix in docs

**Phase to address:** Stack selection + first runnable pipeline; re-validate each phase that adds models.

**Confidence:** HIGH  
**Sources:** [Ultralytics Jetson / TensorRT notes](https://docs.ultralytics.com/guides/nvidia-jetson/), [Ultralytics deployment practices](https://docs.ultralytics.com/guides/model-deployment-practices/)

---

### 6. Free-space / obstacles naively thresholded from monocular depth

**What goes wrong:**  
`depth < 1.5 m ⇒ obstacle` produces flickering blobs, ground-as-obstacle (camera pitch), sky-as-free, and missed thin obstacles. Robot stutter-stops or drives into walls that were “sky-colored” in the depth map.

**Why it happens:**  
Monocular depth is noisy temporally and biased by texture, lighting, and semantics. Without ground-plane reasoning, temporal filter, or morphology, thresholds fight the noise. Relative depth thresholds are especially meaningless across scenes.

**Warning signs:**
- Free-space mask flashes frame-to-frame
- Floor near camera always “occupied”
- Glass doors and black mats invisible
- No hysteresis / temporal smoothing parameters in UI

**Prevention:**
- Derive free-space with camera extrinsics (height, pitch) + ground plane when available
- Temporal smoothing / hysteresis on occupancy; expose controls in developer UI
- Prefer “obstacle likelihood” grids over binary masks for robot consumers
- Document failure classes; allow sensor fusion *on the consumer side* without making LiDAR required
- Validate on motion sequences, not stills

**Phase to address:** Spatial post-processing phase after raw depth works; do not ship free-space in v1 without this.

**Confidence:** HIGH

---

## Performance / Latency Traps

### Running full-resolution depth + open-vocab detection every frame

**What goes wrong:**  
Edge dies; desktop gets warm; UI freezes under multi-model load.

**Prevention:**
- Resolution pyramid: detect at 640-class, depth at fixed model input (e.g. 518), display at stream res
- Schedule heavy models (open-vocab, large depth) on demand or lower rate
- Profile **combined** pipeline, not each model in isolation

**Phase:** Runtime optimization / model routing  
**Confidence:** HIGH

### Measuring the wrong latency

**What goes wrong:**  
Reports “12 ms inference” while capture buffers add 100 ms and WebSocket JSON adds more.

**Prevention:**
- Instrument full pipeline with monotonic timestamps on every frame
- Budget: capture ≤ X, infer ≤ Y, encode ≤ Z, total age ≤ robot control period
- Prefer binary frames (msgpack/protobuf/flatbuffers) for robot stream; JSON for debug only

**Phase:** Streaming API  
**Confidence:** HIGH

### UI path starving the robot path

**What goes wrong:**  
JPEG encode + canvas overlays + browser WebRTC compete with inference for GPU/CPU.

**Prevention:**
- Offload overlay rendering to client when possible; server sends structured detections + optional low-res depth preview
- Cap UI stream FPS independently of perception publish rate
- Never block inference thread on UI clients

**Phase:** Web dashboard architecture  
**Confidence:** HIGH

### Unbounded queues / “process every frame”

**What goes wrong:**  
Latency grows without bound under load; robot acts on ancient state.

**Prevention:**
- Latest-frame-wins mailboxes between stages
- Explicit backpressure; drop with metrics (`frames_dropped`)
- Alert when age-at-emit exceeds threshold

**Phase:** Pipeline architecture  
**Confidence:** HIGH

### Cold start and model load treated as “runtime”

**What goes wrong:**  
First-frame multi-second stall; makers think product is broken.

**Prevention:**
- Warmup inference on startup; progress UI for weight download/load
- Cache compiled engines (TensorRT) on device
- Separate install-time download from run-time start

**Phase:** Packaging / runtime UX  
**Confidence:** MEDIUM–HIGH

### Quantization / export accuracy cliffs

**What goes wrong:**  
FP16/INT8 TensorRT looks fine on COCO demo images, fails on maker’s warehouse lighting; depth edges smear after export.

**Prevention:**
- Validate quantized models on *target domain* clips, not only public benchmarks
- Keep FP16 as default edge path; INT8 only with calibration set from real cameras
- Regression tests: mAP / depth AbsRel / free-space IoU pre- and post-export

**Phase:** Edge export  
**Confidence:** HIGH (deployment literature); exact numbers model-dependent

---

## Camera & Hardware Traps

### “Any USB camera works” without a support matrix

**What goes wrong:**  
MJPEG vs YUYV bandwidth issues, auto-focus hunting, rolling shutter on fast robots, IR-cut flicker, 30 FPS claimed but 8 FPS delivered over USB2 hubs.

**Prevention:**
- Publish a **supported cameras** list + known-bad list
- Prefer fixed-focus, global-shutter when motion is high (document as recommendation)
- Normalize capture via a camera abstraction (V4L2 / OpenCV / GStreamer) with explicit fourcc, FPS, buffer size
- Disable autofocus/autoexposure for reproducible perception when possible (or document the cost)

**Phase:** Camera layer  
**Confidence:** HIGH

### Network / RTSP cameras as first-class without latency honesty

**What goes wrong:**  
IP cameras add 100–500 ms buffering; H.264 GOPs delay keyframes; Wi-Fi drops freeze the world.

**Prevention:**
- Label sources with expected latency class: local USB < RTSP LAN < RTSP Wi-Fi
- Prefer low-latency RTSP settings; document camera firmware knobs
- Timestamp frames at receive time and, if available, RTP/camera time
- Watchdog on stream stall → clear last detections rather than holding stale obstacles forever

**Phase:** Camera ingestion  
**Confidence:** HIGH

### No extrinsics: camera height / pitch unknown

**What goes wrong:**  
Free-space and “distance to floor obstacles” become fiction.

**Prevention:**
- Onboarding: mount height, pitch, and optional roll
- Sensible defaults with big UI warnings when unset
- Optional auto pitch-from-vanishing / ground segmentation later — not required for v1 if manual entry works

**Phase:** Spatial calibration  
**Confidence:** HIGH

### Multi-camera extension points that assume identical models/timebases

**What goes wrong:**  
v1 “extension ready” code hard-codes single camera global state; multi-cam later requires rewrite.

**Prevention:**
- Namespace all state by `camera_id`
- Frame messages carry camera_id + timestamp + intrinsics_id
- Do not fuse multi-cam in v1, but do not use process-global “the frame”

**Phase:** Architecture foundations  
**Confidence:** HIGH

### Thermal / power throttling on edge

**What goes wrong:**  
Jetson works on desk with fan; in robot enclosure FPS collapses mid-run.

**Prevention:**
- Document power modes, cooling requirements, sustained FPS not peak FPS
- Runtime adaptive quality (drop depth rate when thermal throttle detected)

**Phase:** Edge deployment docs + runtime  
**Confidence:** MEDIUM–HIGH

---

## Model & Accuracy Traps

### Indoor metric model outdoors (and reverse)

**What goes wrong:**  
Depth Anything V2 ships **separate** metric weights for indoor (Hypersim, max_depth 20) and outdoor (Virtual KITTI, max_depth 80). Wrong head → systematically wrong distances.

**Prevention:**
- Explicit scene mode in UI/API: `indoor` | `outdoor` | `relative_general`
- Auto-suggest based on user environment; never silent default to outdoor on a tabletop robot
- Consider Metric3D-class models if true zero-shot metric across domains is required — still validate

**Phase:** Depth model integration  
**Confidence:** HIGH  
**Sources:** [DA-V2 metric README](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth)

### Temporal flicker / frame-to-frame depth inconsistency

**What goes wrong:**  
Single-image models have no temporal prior; robot sees vibrating obstacles. (Video Depth Anything and similar address this but cost more.)

**Prevention:**
- Temporal filter on depth and tracks on detections
- Evaluate on video, not only images
- Optional “stable mode” that trades latency for consistency

**Phase:** Post-processing  
**Confidence:** HIGH

### Detector class set mismatch (COCO ≠ maker world)

**What goes wrong:**  
Fixed-class COCO models miss cables, cones, pet gates, custom tools; open-vocab is slower and flaky on short prompts.

**Prevention:**
- Ship fixed-class for reliability + open-vocab as optional query path (matches product intent)
- Document default classes; provide fine-tune / custom weights hook
- For open-vocab: prompt templates, confidence floors, rate limits

**Phase:** Detection features  
**Confidence:** HIGH

### Domain shift: lab demo → garage robot

**What goes wrong:**  
Benchmarks pass; dusty floors, HDR windows, night IR LEDs destroy performance.

**Prevention:**
- Maintain a **maker domain eval set** (diverse amateur videos)
- Night / motion-blur / rolling-shutter stress tests in CI-ish eval scripts
- Expose confidence; fail soft

**Phase:** Evaluation harness (ongoing)  
**Confidence:** HIGH

### Training-data / license landmines

**What goes wrong:**  
Depth-Anything-V2-Small is Apache-2.0; **Base/Large/Giant are CC-BY-NC-4.0** (non-commercial). Makers building products or companies using Sentry AI as dependency hit license walls. YOLO/Ultralytics AGPL history and dual-licensing also surprise commercial users.

**Prevention:**
- Default stack = commercially friendly licenses only
- Document every bundled weight’s license in a `THIRD_PARTY_MODELS.md`
- Optional “research weights” install path clearly marked non-commercial
- Prefer Apache/MIT/BSD model weights for the default maker path

**Phase:** Stack selection (blocker for defaults)  
**Confidence:** HIGH  
**Sources:** [Depth Anything V2 LICENSE section](https://github.com/DepthAnything/Depth-Anything-V2)

### HuggingFace / OpenCV preprocessing mismatches

**What goes wrong:**  
Same weights, different resize/upsampling → different depth (DA-V2 notes OpenCV vs Pillow differences in Transformers pipeline).

**Prevention:**
- One canonical preprocess path in Sentry; lock it in tests
- Golden-image regression for depth and boxes

**Phase:** Model integration  
**Confidence:** HIGH

### Black borders / letterboxing pollution

**What goes wrong:**  
Metric3D warns: black padding at boundaries harms depth. Letterboxed detector inputs shift boxes if undo is wrong.

**Prevention:**
- Crop padding; correct box mapping from letterbox space
- Unit tests for coordinate transforms

**Phase:** Pre/post-processing  
**Confidence:** HIGH

---

## Product / Scope Traps

### Building control / planning “just a little”

**What goes wrong:**  
Scope expands into nav stack; half-baked control becomes liability; perception quality work stalls.

**Prevention:**
- Out of scope remains out of scope: **perception stream only**
- Provide example consumer snippets (ROS2 node, Python client) — not a full navigator
- API designed so many controllers can subscribe without Sentry owning behavior

**Phase:** All phases — enforce at review  
**Confidence:** HIGH

### Chat / VLM / voice before solid depth+detect

**What goes wrong:**  
Demo candy delays the core value: reliable local spatial awareness.

**Prevention:**
- v1 = camera → depth + detect + free-space + web overlays + stream API
- Extension hooks only for voice/VLM

**Phase:** Roadmap ordering  
**Confidence:** HIGH

### Dense SLAM / full mapping in v1

**What goes wrong:**  
Multi-month detour; monocular SLAM failure modes dominate; makers still just wanted “don’t hit the chair.”

**Prevention:**
- Stick to depth + obstacles; mapping later
- If odometry appears, keep it optional and labeled experimental

**Phase:** Scope control  
**Confidence:** HIGH

### Dashboard that cannot drive debugging

**What goes wrong:**  
Pretty video, no way to see latency, model version, intrinsics, or confidence — makers cannot tell why the robot is wrong.

**Prevention:**
- Developer controls: thresholds, model toggles, colormap, freeze-frame, latency HUD
- Export debug bundle (frame + config + outputs) for issue reports

**Phase:** Web UI  
**Confidence:** HIGH

### Plugin architecture too early / too late

**What goes wrong:**  
Too early: abstract soup, no working pipeline. Too late: god-object rewrite for ROS2/multi-cam.

**Prevention:**
- Thin interfaces early: `CameraSource`, `DepthModel`, `Detector`, `Publisher`
- One working concrete path first; plugins second

**Phase:** Architecture foundations  
**Confidence:** MEDIUM–HIGH

### Assuming ROS2 is free

**What goes wrong:**  
ROS2 middleware (RMW), QoS, and security add complexity; makers on pure Python/HTTP bounce off.

**Prevention:**
- REST/WebSocket first-class; ROS2 as optional bridge package
- Don’t block v1 on ROS2

**Phase:** Integration phase after core API  
**Confidence:** HIGH

---

## Security & Safety Notes

### Perception is not a safety system

**What goes wrong:**  
Users treat free-space as a safety interlock. Missed detection → injury/property damage. Open-source liability narratives escalate.

**Prevention:**
- Explicit safety disclaimer: not certified, not for life-critical use
- Recommend independent emergency stop and contact sensing on physical robots
- Avoid “safe/unsafe” language in API; use occupancy/confidence
- Log enough for post-mortems without claiming functional safety (ISO 26262 etc. out of scope)

**Phase:** Docs + API semantics  
**Confidence:** HIGH

### Local network exposure of camera streams

**What goes wrong:**  
Web UI binds `0.0.0.0` with no auth; household camera becomes LAN-visible; later internet-exposed via port forward.

**Prevention:**
- Default bind localhost; opt-in LAN with warning
- Optional auth token for remote access
- No cloud upload by default (privacy constraint)

**Phase:** Web server defaults  
**Confidence:** HIGH

### Model / weight supply chain

**What goes wrong:**  
Auto-download from mutable URLs; compromised weights or ToS surprises.

**Prevention:**
- Pin hashes for downloaded weights
- Document mirror/offline install
- Prefer user-controlled model directory

**Phase:** Packaging  
**Confidence:** MEDIUM–HIGH

### Prompt injection via open-vocabulary / future VLM features

**What goes wrong:**  
Untrusted scene text or UI prompts influence behavior when VLM/voice arrives.

**Prevention:**
- Treat open-vocab queries as untrusted input; sandbox side effects
- No tool execution from model text in v1

**Phase:** When open-vocab / VLM ships  
**Confidence:** MEDIUM

### Stale perception as a hazard

**What goes wrong:**  
Stream stalls; last “all clear” free-space remains true while robot moves.

**Prevention:**
- Messages carry `timestamp` and `ttl` / `max_age`
- Consumers must invalidate stale data; document this contract
- On stream loss: publish explicit `stream_stale` state

**Phase:** API contract  
**Confidence:** HIGH

---

## Checklist for Planning

Use this when writing the roadmap and phase plans.

### Geometry & depth
- [ ] API distinguishes relative vs metric depth; no silent “meters” on relative models
- [ ] Indoor/outdoor/relative model modes are first-class
- [ ] Camera intrinsics + mount extrinsics captured before promising metric free-space
- [ ] Free-space uses temporal smoothing + documented failure modes
- [ ] Tape-measure / known-distance validation scenes in eval set

### Latency & runtime
- [ ] End-to-end latency budget defined for desktop and at least one edge target
- [ ] Latest-frame-wins pipeline; drop metrics exposed
- [ ] UI stream decoupled from robot perception stream
- [ ] Dual model tiers: quality (desktop) vs fast (edge)
- [ ] Export path (ONNX/TensorRT) planned before locking model choices

### Cameras
- [ ] Abstraction for USB / RTSP / file sources with capability probes
- [ ] Supported camera matrix and latency classes documented
- [ ] Autofocus/exposure guidance for makers
- [ ] `camera_id` namespacing from day one

### Models & licensing
- [ ] Default weights are commercially usable licenses
- [ ] `THIRD_PARTY_MODELS.md` with license + citation per weight
- [ ] Fixed-class detector reliable path + optional open-vocab
- [ ] Golden-image preprocess regression tests

### Product & safety
- [ ] Messaging: perception aid, not FSD/autonomy
- [ ] No motor control in scope
- [ ] Safety disclaimer + stale-data contract
- [ ] Localhost-first web UI; privacy by default
- [ ] Known-failure gallery in docs

### Phase mapping (suggested)

| Concern | Address in |
|--------|------------|
| Depth type system, model licenses, camera abstraction | Foundations / stack phase |
| Intrinsics calibration UX | Camera bring-up phase |
| Dual-path streaming + latency budgets | Architecture / API phase |
| Metric depth + free-space post-processing | Spatial perception phase |
| Fixed + open-vocab detection | Detection phase |
| Web overlays + developer controls | Dashboard phase |
| Jetson/Pi profiles, TensorRT export | Edge deployment phase |
| ROS2 bridge, multi-cam, voice | Extensions only after core |

### Highest-cost mistakes if deferred
1. Freezing a “depth in meters” API that is actually relative  
2. Building UI-coupled pipeline that cannot meet robot latency  
3. Defaulting to non-commercial model weights  
4. Shipping free-space without extrinsics/temporal logic  
5. Branding as FSD-class autonomy without safety boundaries  

---

## Sources

| Source | Use | Confidence |
|--------|-----|------------|
| [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) + [metric fine-tunes](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth) | Relative vs metric split; indoor/outdoor heads; licenses | HIGH |
| [Depth Anything V2 paper](https://arxiv.org/abs/2406.09414) | Model family context | HIGH |
| [Metric3D](https://github.com/YvanYin/Metric3D) | Focal length / point cloud distortion; canonical camera | HIGH |
| [MiDaS](https://pytorch.org/hub/intelisl_midas_v2/) | Relative inverse depth definition | HIGH |
| [ZoeDepth](https://github.com/isl-org/ZoeDepth) | Metric+relative combination lineage (archived) | MEDIUM |
| [Ultralytics deployment practices](https://docs.ultralytics.com/guides/model-deployment-practices/) | Quantization / deployment | HIGH |
| [Ultralytics Jetson guide](https://docs.ultralytics.com/guides/nvidia-jetson/) | TensorRT device-specificity, DLA | HIGH |
| [OpenCV camera calibration](https://docs.opencv.org/4.x/dc/dbb/tutorial_py_calibration.html) | Intrinsics workflow | HIGH |
| Sentry AI `PROJECT.md` constraints | Product scope, multi-target, local OSS | HIGH |

---

*Research dimension: pitfalls only. Does not commit stack or feature picks — feeds roadmap risk flags and phase ordering.*
