# Phase 6: Developer Controls & Open-Vocab - Context

**Gathered:** 2026-08-08  
**Status:** Ready for planning  
**Source:** ROADMAP + research + Phase 1–5 shipped contracts (YOLO mode)

<domain>
## Phase Boundary

Make the Live Preview a **full interactive developer console** and add **open-vocabulary detection** (promptable classes) that does not block fixed-class detection.

**In scope:**
- Runtime enable/disable of detection, depth, free-space stages (UI-03)
- Interactive thresholds: det conf, free-space near/mid cutoffs (and related knobs) (UI-04)
- Dashboard performance telemetry: FPS + stage latency (UI-05) — expand visibility
- Open-vocab detector (YOLOE or equivalent OSS) text prompts (OVD-01)
- On-demand or lower-rate open-vocab without blocking fixed-class path (OVD-02)
- Open-vocab results on dashboard + perception stream when enabled (OVD-03)
- Control plane API for stage flags + thresholds (cold path, not hot path)
- Keep localhost default; perception-only boundary

**Out of scope:**
- Edge TensorRT packaging (Phase 7)
- Multi-cam fusion, ROS2 production, voice I/O, scene chat/VLM
- Robot control / navigation cues
- Full React/Vite rewrite (extend static Live Preview is fine)
- Always-on heavy open-vocab as default on edge

</domain>

<decisions>
## Implementation Decisions

### Locked from product / research
- Developer-first overlays + controls (not chat-first)
- Fixed-class remains primary continuous path; open-vocab secondary (on-demand / lower rate)
- UI and API share PerceptionStore truth
- Local OSS only (Ultralytics AGPL documented)
- Stages disabled = skip worker / Spatial Post work, not just hide overlay

### From Phase 1–5 shipped
- PATCH `/api/detection/config` conf already exists
- PATCH `/api/depth/config` depth_mode exists
- DetectionLoop, DepthLoop, FreeSpaceLoop + serve lifecycle
- Live Preview conf slider + status polling
- `/v1/snapshot` + `/v1/stream` assembler
- MJPEG overlay pipeline

### Claude's Discretion
- Control plane shape: `/api/pipeline/config` vs per-stage routes
- Open-vocab via YOLOE in same `detect` extra vs separate extra
- How open-vocab merges into Detection list (separate field vs tagged class_name prefix)
- Source switch in UI (synthetic/usb) vs CLI-only for v1 Phase 6
- Free-space cutoff knobs wired into FreeSpaceLoop config

</decisions>

<canonical_refs>
## Canonical References

- `src/sentry_ai/ui/static/index.html` — Live Preview + conf slider
- `src/sentry_ai/api/routes_detection.py`, `routes_depth.py`, `routes_preview.py`, `routes_v1.py`
- `src/sentry_ai/cli.py` — serve lifecycle
- `src/sentry_ai/models/detection/yolo_worker.py`, `loop.py`
- `src/sentry_ai/models/depth/`, `spatial/loop.py`
- `src/sentry_ai/state/perception_store.py`
- `.planning/research/SUMMARY.md` Phase 6, STACK.md YOLOE
- Phase 5 SUMMARYs

</canonical_refs>

<specifics>
## Specific Ideas

Roadmap plans (2):
1. 06-01 Control plane + full interactive UI (toggles, thresholds, telemetry)
2. 06-02 Open-vocab worker (YOLOE) + prompt UX + stream/UI integration

Success: toggle stages live; adjust conf/cutoffs; see FPS/latency; prompt “red cup” style classes; fixed-class still runs.

</specifics>

<deferred>
## Deferred Ideas

- Edge profiles / headless packaging → Phase 7  
- Voice / VLM chat → v2  
- Full multi-source switcher UX if not cheap → optional  

</deferred>

---
*Phase: 06-developer-controls-open-vocab*
