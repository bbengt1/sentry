---
gsd_state_version: 1.0
milestone: v1.0
milestone_name: milestone
status: ready_to_plan
stopped_at: Phase 3 complete (2/2) — ready to discuss Phase 4
last_updated: 2026-08-07T19:31:26.496Z
last_activity: 2026-08-07
progress:
  total_phases: 7
  completed_phases: 3
  total_plans: 8
  completed_plans: 8
  percent: 43
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-07)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** Phase 4 — monocular depth

## Current Position

Phase: 4
Plan: Not started
Status: Ready to plan
Last activity: 2026-08-07

Progress: [███░░░░░░░] 43% (Phase 3 of 7 complete)

## Performance Metrics

**Velocity:**

- Total plans completed: 9
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 3 | - | - |
| 3 | 2 | - | - |

**Recent Trend:**

- Last 5 plans: —
- Trend: —

| Phase 01 P01 | 3min | 3 tasks | 19 files |
| Phase 01 P02 | 4min | 3 tasks | 19 files |
| Phase 01 P03 | 4min | 3 tasks | 17 files |
| Phase 02 P01 | 4min | 3 tasks | 25 files |
| Phase 02 P02 | 4min | 3 tasks | 7 files |
| Phase 02 P03 | 8min | 3 tasks | 16 files |
| Phase 03 P01 | 6min | 3 tasks | 25 files |
| Phase 03 P02 | 5min | 3 tasks | 14 files |

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table. Recent decisions affecting current work:

- Camera-only depth + obstacles for v1 spatial awareness (not full SLAM)
- Single camera first; multi-cam via extension points
- Web dashboard with live overlays + controls (not chat-first)
- Fixed-class + open-vocab detection
- Perception stream only (no robot control)
- Multi-target: desktop GPU + Jetson/Pi-class edge
- Local OSS models only; stack: FastAPI + YOLO26 + DAV2 Small + React
- Standard granularity: 7 phases
- **Phase 1 package naming:** dist `sentry-ai`, import `sentry_ai`, CLI `sentry` (avoid PyPI `sentry` collision)
- Phase 1 thin deps only: pydantic, pyyaml, typer, pytest, ruff — no torch/opencv/fastapi yet
- [Phase 01]: Dist name sentry-ai (not sentry) to avoid PyPI/getsentry collision
- [Phase 01]: Console script points to main() callable for reliable entry
- [Phase 01]: Apache-2.0 for application code; Wave 0 stubs use pytest.mark.skip
- [Phase 01]: DepthPayload in perception.py with shared validator; StrEnum for ruff UP042
- [Phase 01]: Typed Detection/FreeSpacePayload placeholders; profile YAML via Path + hatch force-include
- [Phase 01]: discover() skip-if-present for entry-point re-declarations of builtins
- [Phase 01]: NullBackend.name = BackendName.CPU; probe_device always available=False
- [Phase 01]: Smoke asserts allow_cloud false before validating synthetic PerceptionFrames
- [Phase ?]: ImageFrame runtime dataclass (meta Frame + image_bgr); Frame stays identity-only
- [Phase ?]: SyntheticSource re-exported from plugins.builtins for entry-point stability
- [Phase ?]: UsbSource/FileSource thin subclasses of OpenCVSource with BUFFERSIZE=1
- [Phase 02]: frames_dropped is overwrite-count (publish while slot occupied)
- [Phase 02]: get_latest is non-consuming keep-latest; CaptureLoop owns source lifecycle
- [Phase 02]: Lazy CaptureLoop export avoids bus↔capture circular import
- [Phase 02]: StatusSnapshot.bind defaults None until 02-03 serve
- [Phase 02]: MJPEG multipart StreamingResponse + static HTML for Live Preview (no Vite/React)
- [Phase 02]: create_app injects bus+loop without starting capture (caller owns lifecycle)
- [Phase 02]: RTSP is OpenCV URL best-effort; PyAV deferred with docs/camera-sources.md
- [Phase 02]: sentry serve --host defaults to 127.0.0.1 (MODEL-03)
- [Phase ?]: ultralytics-opencv-headless optional detect extra only
- [Phase 03]: DetectionLoop on FrameBus; InferenceBackend stays stubs; overlays deferred to 03-02
- [Phase 03]: desktop-gpu detector_tier m→s; thread-safe conf read each process()
- [Phase 03]: Overlay transport Option A: server OpenCV draw before JPEG encode
- [Phase 03]: GET /api/snapshot 404 when no product; 503 when store/worker missing
- [Phase 03]: Det metrics merged in api_status; CaptureLoop not coupled to detection

### Pending Todos

None yet.

### Blockers/Concerns

None. Plan check passed with 4 non-blocking warnings (file count per plan, research open-questions labeling, DepthPayload path clarity, depth.kind vs depth_kind naming).

## Deferred Items

| Category | Item | Status | Deferred At |
|----------|------|--------|-------------|
| *(none)* | | | |

## Session Continuity

Last session: 2026-08-07T19:28:04.041Z
Stopped at: Completed 03-02-PLAN.md
Next: Execute 03-02-PLAN.md (overlays, snapshot JSON, runtime conf, serve wiring)
