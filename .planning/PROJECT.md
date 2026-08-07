# Sentry AI

## What This Is

Sentry AI is an open-source, camera-only perception stack for maker robotics — vision-based spatial awareness and object recognition without LiDAR or radar. Think Tesla FSD-style perception, scoped for hobbyist and maker robots that use off-the-shelf USB or network cameras. It runs local open-source models, exposes a realtime web developer interface with live overlays and controls, and ships a perception stream (depth, detections, free space / obstacles) that robots can consume via API.

## Core Value

Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

- [ ] Camera-only spatial awareness (monocular depth estimation + free space / occupied regions)
- [ ] Support for off-the-shelf cameras (USB, network/IP, and local/dev camera sources)
- [ ] Local development workflow using local or external cameras
- [ ] Realtime web interface showing live perception output (video + overlays)
- [ ] Interactive developer controls (thresholds, model toggles, inspection) between developer and AI models
- [ ] Local open-source AI models only (no required cloud inference)
- [ ] Fixed-class object detection plus optional open-vocabulary queries
- [ ] Perception stream API for robots (depth map, detections, free-space/obstacles) — control remains consumer’s job
- [ ] Single-camera pipeline first, with extension points for multi-camera later
- [ ] Multi-target runtime: desktop GPU for development + edge (Jetson / Pi-class) as first-class deployment
- [ ] Extensible architecture for future capabilities (voice I/O, multi-camera, navigation cues, etc.)

### Out of Scope

- LiDAR / radar / ultrasonic as required sensors — product is camera-only by design
- Full robot control / motion planning stack — Sentry AI outputs perception; robot control is the consumer’s responsibility
- Dense SLAM / full 3D map building in v1 — depth + obstacles only; mapping can come later
- Multi-camera fusion in v1 — single camera first; multi-camera is an extension point
- Cloud-only or proprietary model dependency — local OSS models are required
- Voice feedback / voice input in v1 — deferred as extensibility hooks, not core delivery
- Commercial robot fleet management / cloud fleet dashboards — maker / local focus

## Context

**Problem:** Maker robotics often depends on expensive or hard-to-integrate depth sensors (LiDAR, structured light). Vision-only stacks exist in research and industry (e.g. automotive FSD), but there is no approachable, open-source, camera-only perception product tailored for makers with:

1. Off-the-shelf camera support  
2. Local OSS models  
3. A realtime interactive developer UI  
4. A clean perception API for robots  

**Users:** Maker / hobbyist roboticists, students, and small teams building robots who want spatial awareness from cameras they already have.

**Inspiration:** Tesla FSD-style vision-only perception — adapted for open hardware, local inference, and maker workflows rather than production vehicles.

**v1 spatial model:** Monocular (or optional stereo later) depth estimation, free space vs occupied / obstacle regions, fixed-class object detection + open-vocabulary queries, single camera.

**v1 interface:** Web dashboard — live video, perception overlays, model/threshold controls. Chat/scene Q&A and voice are future extensions.

**v1 outputs:** Perception stream (depth map, bounding boxes / masks, free-space / obstacle signals) over REST and/or WebSocket (and optionally ROS2 later if research supports it as non-blocking).

**Hardware:** Desktop GPU for primary development; edge deployment (NVIDIA Jetson, Raspberry Pi-class with accelerators where feasible) as a first-class goal, not an afterthought.

## Constraints

- **Sensors**: Cameras only for spatial awareness — no LiDAR/radar requirement
- **Models**: Local open-source models required; cloud optional only as non-default extension
- **Cameras**: Must support common off-the-shelf sources (USB UVC, RTSP/network, file/synthetic for tests)
- **Runtime**: Multi-target — develop on desktop GPU; deploy path to edge devices
- **Interface**: Web-based realtime dashboard for developers
- **Architecture**: Plugin / extension-friendly for voice, multi-camera, ROS2, etc.
- **License**: Open source product suitable for maker community use and contribution
- **Privacy**: Prefer on-device processing; no mandatory data upload

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Camera-only perception (no LiDAR/radar) | Core product thesis; maker accessibility | — Pending |
| Spatial v1 = depth + obstacles, not full SLAM | Ship useful navigation signal without mapping complexity | — Pending |
| Single camera first | Reduces v1 complexity; multi-cam as extension | — Pending |
| Web dashboard for developer UI | Universal, easy local dev, realtime overlays | — Pending |
| Live overlays + controls (not chat-first) | Developer tooling first; NL Q&A later | — Pending |
| Fixed-class + open-vocab detection | Standard reliability + flexible queries | — Pending |
| Perception stream only (no robot control) | Clean boundary; works with any robot stack | — Pending |
| Multi-target: desktop + edge | Dev ergonomics without abandoning deployment | — Pending |
| Local OSS models only for core path | Open source, offline-capable, no vendor lock-in | — Pending |
| Extensible plugin architecture | Voice, multi-cam, ROS2 without rewrite | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd:complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-08-07 after initialization*
