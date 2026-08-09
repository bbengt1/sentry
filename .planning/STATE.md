---
gsd_state_version: 1.0
milestone: v0.2
milestone_name: Edge Runtime
status: planning
last_updated: "2026-08-09T14:13:44.763Z"
last_activity: 2026-08-09
progress:
  total_phases: 0
  completed_phases: 0
  total_plans: 0
  completed_plans: 0
  percent: 0
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-07)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.  
**Current focus:** Awaiting next milestone (`/gsd:new-milestone`)

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-08-09 — Milestone v0.2 started

## Performance Metrics

**Velocity:**

- Total plans completed: 17
- Average duration: —
- Total execution time: 0 hours

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 1 | 3 | - | - |
| 2 | 3 | - | - |
| 3 | 2 | - | - |
| 4 | 2 | - | - |
| 5 | 3 | - | - |
| 6 | 2 | - | - |
| 7 | 2/3 | - | - |

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
| Phase 04 P01 | 6min | 3 tasks | 23 files |
| Phase 04 P02 | 6min | 3 tasks | 16 files |
| Phase 05 P01 | 5min | 3 tasks | 11 files |
| Phase 05 P01 | 5min | 3 tasks | 11 files |
| Phase 05 P02 | 4min | 3 tasks | 7 files |
| Phase 05 P03 | 4min | 3 tasks | 13 files |
| Phase 06 P01 | 6min | 3 tasks | 18 files |
| Phase 06 P02 | 8min | 3 tasks | 24 files |
| Phase 07 P01 | 6min | 3 tasks | 18 files |
| Phase 07 P02 | 3min | 2 tasks | 11 files |
| Phase 07 P03 | 4min | 2 tasks | 15 files |

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
- [Phase 04]: HF Transformers DAV2 Small default (Apache-2.0); never Base/Large NC
- [Phase 04]: Extend one PerceptionStore with DepthProduct rather than separate DepthStore
- [Phase 04]: kind_for_mode from configured depth_mode only — no float-range heuristics
- [Phase 04]: Overlay transport: server-side COLORMAP_TURBO alpha 0.45 before MJPEG encode
- [Phase 04]: Snapshot never serializes depth_map; metadata + min/max/mean/latency only
- [Phase 04]: 404 only when neither detection nor depth product exists
- [Phase 04]: Relative UI label: relative (not meters); metric shows kind + m when unit is m
- [Phase 04]: serve depth_mode defaults to relative; PATCH /api/depth/config for runtime toggle
- [Phase ?]: units always ordinal for v1 free-space even when depth_kind is metric_estimated
- [Phase ?]: OccupancySmoother state owned by FreeSpaceLoop, not PerceptionStore
- [Phase ?]: FreeSpaceLoop polls snapshot_depth only (no FrameBus/ModelWorker)
- [Phase 05]: FreeSpacePayload expanded with ObstacleCue list + bands; units default ordinal; no distance_m
- [Phase 05]: DEFAULT_TTL_MS: detections 500 / depth 750 / free_space 750; TtlConfig overrideable
- [Phase 05]: Primary identity = max t_capture among present products
- [Phase 05]: /api/snapshot is thin alias to assembler only — no dual merge
- [Phase 05]: WS /v1/stream fixed 0.1s keep-latest; no per-client queue
- [Phase 05]: FreeSpaceLoop always-on in serve (CPU Spatial Post; no ML ImportError gate)
- [Phase 05]: Status free_space ages/stale from product t_capture + DEFAULT_TTL_MS for UI badges
- [Phase 06]: Enable flags inside loops skip compute; never stop/start threads for UI toggles — Locked plan decision (UI-03)
- [Phase 06]: Unified GET/PATCH /api/pipeline/config for stages + free-space cuts; keep det conf + depth mode routes — Locked plan decision (UI-04)
- [Phase 06]: clear_* product slots on disable for honest completeness — RESEARCH A4 disable semantics
- [Phase 06]: OpenVocabProduct fourth store slot — never dual-write set_detections
- [Phase 06]: Default OV mode off; continuous every_n=3 opt-in only
- [Phase 06]: Detection.source additive default fixed — existing fixed path unchanged
- [Phase 06]: YOLOE via existing detect extra; yoloe-26s-seg.pt default; mock in CI
- [Phase 07]: Serve default remains cpu-fallback; no CUDA auto-switch to desktop-gpu
- [Phase 07]: preferred_backend tensorrt/onnxruntime is device policy + honesty logs only (live PyTorch)
- [Phase 07]: Headless via create_app(serve_ui=False) + sentry serve --no-ui (not separate api cmd)
- [Phase 07]: Open-vocab weights derive from detector_tier; depth_tier Small-only allowlist
- [Phase 07]: probe_device light non-raising CUDA check; never hard-fails serve
- [Phase 07]: EDGE-03 docs+scripts only; on-device TRT; no prebuilt engines; no tensorrt extra
- [Phase 07]: YOLOE export experimental; PyTorch on-demand OV remains supported edge path
- [Phase 07]: export_yolo validates KNOWN_WEIGHTS basenames only (path traversal rejected)
- [Phase 07]: Ros2PerceptionBridge importable without auto-register as sink (health stays clean)
- [Phase 07]: VoiceNullSink name/entry-point voice-null; no ASR/TTS
- [Phase 07]: Multi-cam = schema identity tests only; store remains single-slot keep-latest
- [Phase 07]: Desktop GPU documented as primary maker path; serve default remains cpu-fallback
- [Phase 07]: Safety doc consolidates perception-only, free-space not interlock, localhost default

### Pending Todos

None yet.

### Blockers/Concerns

Phase 7 verification: **passed** (6/6 success criteria; EDGE-01..05). Report: `.planning/phases/07-edge-profiles-extension-stubs/07-VERIFICATION.md`.

Phase 7 plan-check: **PASS_WITH_FLAGS** (non-blocking). Flags: 07-01 file count, README merge across 07-02/07-03, VALIDATION.md incomplete Wave 0 list, RESEARCH open-questions not marked RESOLVED.

## Deferred Items

Items acknowledged and deferred at milestone close on 2026-08-09:

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02 human_needed UAT (browser MJPEG, physical USB, optional RTSP) | acknowledged |
| verification_gap | Phase 03 human_needed UAT (real YOLO visual + offline cache) | acknowledged |
| verification_gap | Phase 04 human_needed UAT (real DAV2 visual + offline cache; live depth mode reload) | acknowledged |
| integration | Free-space product after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | Most VALIDATION.md still nyquist_compliant false | docs debt |

See also: `milestones/v1.0-MILESTONE-AUDIT.md` tech_debt section.

## Session Continuity

Last session: 2026-08-09
Stopped at: Milestone v1.0 complete-milestone finished (archive + tag)
Next: `/gsd:new-milestone` when ready for v1.1 / v2.0

## Operator Next Steps

- Start the next milestone with `/gsd:new-milestone`
- Optional: push tag `v1.0` to origin when remote is ready
