# Requirements: Sentry AI

**Defined:** 2026-08-07  
**Core Value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Foundations & Contracts

- [x] **FOUND-01**: Project ships as an installable Python package with documented one-command local start
- [x] **FOUND-02**: Shared schemas define `Frame` and `PerceptionFrame` with `frame_id`, `camera_id`, and timestamps
- [x] **FOUND-03**: Depth outputs are typed (`relative` | `metric_estimated` | `metric_calibrated`); relative depth is never labeled as meters
- [x] **FOUND-04**: Plugin registry stubs exist for camera sources, model workers, and sinks
- [x] **FOUND-05**: Default models are commercially friendly OSS weights; third-party licenses documented (`THIRD_PARTY_MODELS.md`)
- [x] **FOUND-06**: Device/backend abstraction supports desktop-gpu, jetson, and cpu-fallback profiles (stubs acceptable until edge phase)

### Camera Ingest

- [x] **CAM-01**: System captures from USB UVC cameras via OpenCV (or equivalent)
- [x] **CAM-02**: System captures from file / video sources for local development and CI
- [x] **CAM-03**: System supports synthetic frame source for automated tests
- [x] **CAM-04**: System supports network/IP cameras (RTSP) for external camera development
- [x] **CAM-05**: Frame bus uses keep-latest drop policy with drop/FPS metrics (no unbounded capture queues)
- [x] **CAM-06**: Camera disconnect / reconnect is handled with clear error state in UI and API (no silent freeze)

### Fixed-Class Detection

- [x] **DET-01**: Fixed-class object detector runs locally (YOLO26 or equivalent OSS) on the live camera stream
- [x] **DET-02**: Detections include class, confidence, and bounding box in image coordinates
- [x] **DET-03**: Confidence threshold is adjustable at runtime without restart
- [x] **DET-04**: Detections appear on the web dashboard overlay and in the perception stream (same truth)

### Monocular Depth

- [x] **DEPTH-01**: Monocular depth model runs locally (Depth Anything V2 Small or equivalent OSS)
- [x] **DEPTH-02**: Depth map is available in the perception stream with explicit `depth_kind`
- [x] **DEPTH-03**: Depth colormap is shown on the web dashboard
- [x] **DEPTH-04**: Optional metric mode (if enabled) is explicitly labeled and never conflated with relative depth

### Free-Space / Obstacles

- [x] **SPACE-01**: Free-space / obstacle regions are derived from depth (simple occupancy or near-field bands — not SLAM)
- [x] **SPACE-02**: Obstacle cues are exposed in the perception stream in a machine-readable form
- [x] **SPACE-03**: Free-space / obstacle overlay is shown on the web dashboard
- [x] **SPACE-04**: Stale / incomplete perception is signaled (TTL or completeness flags); no implied “safe to proceed”

### Perception Stream API

- [x] **API-01**: WebSocket stream delivers merged `PerceptionFrame` under a versioned `/v1` contract
- [x] **API-02**: REST snapshot endpoint returns latest `PerceptionFrame`
- [x] **API-03**: Each frame reports completeness for depth, detections, and free-space
- [x] **API-04**: Stream metadata includes FPS / stage latency and drop counts
- [x] **API-05**: API never emits motor commands, velocities, or path plans (perception-only boundary)

### Developer Web Interface

- [x] **UI-01**: Web dashboard shows live camera video in realtime
- [x] **UI-02**: Dashboard overlays detections, depth colormap, and free-space/obstacles
- [x] **UI-03**: Developer can toggle perception stages (detection, depth, free-space) at runtime
- [x] **UI-04**: Developer can adjust thresholds (detection conf, depth/free-space cutoffs) interactively
- [x] **UI-05**: Dashboard shows performance telemetry (FPS, stage latency)
- [x] **UI-06**: UI and robot API consume the same perception state (overlay parity)

### Open-Vocabulary Detection

- [x] **OVD-01**: Open-vocabulary detector (YOLOE or equivalent OSS) accepts text prompts for custom classes
- [x] **OVD-02**: Open-vocab path can run on-demand or at a lower rate than fixed-class detection
- [x] **OVD-03**: Open-vocab results appear on dashboard and in stream when enabled

### Multi-Target & Extensibility

- [x] **EDGE-01**: Documented desktop GPU development path runs the full pipeline
- [x] **EDGE-02**: Runtime profiles exist for desktop, Jetson-class, and CPU/lite fallback
- [x] **EDGE-03**: Export recipes for ONNX and/or TensorRT exist for edge deployment
- [x] **EDGE-04**: Extension stubs exist for multi-camera (`camera_id` schema), ROS2 bridge scaffold, and voice plugin no-op
- [x] **EDGE-05**: Headless mode runs perception API without requiring the web UI

### Local Models & Privacy

- [x] **MODEL-01**: Core inference path uses only local open-source models (no mandatory cloud)
- [x] **MODEL-02**: Models are cacheable for offline use after first download
- [x] **MODEL-03**: Default bind is localhost; remote exposure is opt-in and documented

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Advanced Spatial

- **SPACE-V2-01**: Metric depth with guided intrinsics/extrinsics calibration UX
- **SPACE-V2-02**: Temporal occupancy history / lightweight local map
- **SPACE-V2-03**: Optional stereo or depth-camera source adapters (RealSense/OAK as *sources*, not requirements)

### Platform

- **PLAT-V2-01**: First-class multi-camera fusion
- **PLAT-V2-02**: Production ROS2 bridge package with standard message types
- **PLAT-V2-03**: Sustained Pi-class “lite” profile with published FPS budgets
- **PLAT-V2-04**: WebRTC low-latency preview path

### Interaction

- **INT-V2-01**: Scene Q&A / VLM chat about the live view
- **INT-V2-02**: Voice input and voice feedback plugins
- **INT-V2-03**: High-level navigation cues (“stop”, “clear left”) as optional sink

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Required LiDAR / radar / ultrasonic | Contradicts camera-only product thesis |
| Full SLAM / dense 3D mapping in v1 | Delays useful depth+obstacles; separate product surface |
| Robot control / motion planning | Consumers own control; safety/e-stop outside Sentry |
| Mandatory cloud inference | Privacy, offline workshops, vendor lock-in |
| Hardware-locked depth camera requirement | Would become another OAK/ZED wrapper |
| Fleet / multi-robot cloud SaaS | Not maker-local core |
| Training / labeling platform | External tools; not v1 scope |
| FSD / autonomous vehicle claims | Liability and overpromise; monocular hobby ≠ vehicle-grade |
| Always-on cloud camera upload | Privacy landmine |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FOUND-01 | Phase 1 | Complete |
| FOUND-02 | Phase 1 | Complete |
| FOUND-03 | Phase 1 | Complete |
| FOUND-04 | Phase 1 | Complete |
| FOUND-05 | Phase 1 | Complete |
| FOUND-06 | Phase 1 | Complete |
| CAM-01 | Phase 2 | Complete |
| CAM-02 | Phase 2 | Complete |
| CAM-03 | Phase 2 | Complete |
| CAM-04 | Phase 2 | Complete |
| CAM-05 | Phase 2 | Complete |
| CAM-06 | Phase 2 | Complete |
| UI-01 | Phase 2 | Complete |
| DET-01 | Phase 3 | Complete |
| DET-02 | Phase 3 | Complete |
| DET-03 | Phase 3 | Complete |
| DET-04 | Phase 3 | Complete |
| DEPTH-01 | Phase 4 | Complete |
| DEPTH-02 | Phase 4 | Complete |
| DEPTH-03 | Phase 4 | Complete |
| DEPTH-04 | Phase 4 | Complete |
| SPACE-01 | Phase 5 | Complete |
| SPACE-02 | Phase 5 | Complete |
| SPACE-03 | Phase 5 | Complete |
| SPACE-04 | Phase 5 | Complete |
| API-01 | Phase 5 | Complete |
| API-02 | Phase 5 | Complete |
| API-03 | Phase 5 | Complete |
| API-04 | Phase 5 | Complete |
| API-05 | Phase 5 | Complete |
| UI-02 | Phase 5 | Complete |
| UI-03 | Phase 6 | Complete |
| UI-04 | Phase 6 | Complete |
| UI-05 | Phase 6 | Complete |
| UI-06 | Phase 5 | Complete |
| OVD-01 | Phase 6 | Complete |
| OVD-02 | Phase 6 | Complete |
| OVD-03 | Phase 6 | Complete |
| EDGE-01 | Phase 7 | Complete |
| EDGE-02 | Phase 7 | Complete |
| EDGE-03 | Phase 7 | Complete |
| EDGE-04 | Phase 7 | Complete |
| EDGE-05 | Phase 7 | Complete |
| MODEL-01 | Phase 1 | Complete |
| MODEL-02 | Phase 3 | Complete |
| MODEL-03 | Phase 2 | Complete |

**Coverage:**
- v1 requirements: 42 total
- Mapped to phases: 42
- Unmapped: 0

## Definition of Done (v1 Milestone)

v1 is release-ready when:

1. A maker can plug in a USB camera, start Sentry with one command, and see live video + detections + depth + free-space overlays in the browser.
2. A robot client can subscribe to `/v1` WebSocket (or REST snapshot) and receive timestamped `PerceptionFrame` messages with depth, detections, and free-space.
3. All inference runs locally with OSS models; no cloud required after model cache.
4. Depth semantics are honest (`depth_kind`); free-space is not marketed as a safety interlock.
5. Desktop GPU path is documented; edge profiles and export recipes exist with honest performance expectations.
6. Extension points exist (stubs) for multi-cam, ROS2, and voice without blocking v1.

---
*Requirements defined: 2026-08-07*  
*Last updated: 2026-08-07 after research synthesis*
