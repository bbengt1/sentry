# Phase 2: Camera Ingest & Live Preview - Context

**Gathered:** 2026-08-07  
**Status:** Ready for planning  
**Source:** Project init decisions + ROADMAP Phase 2 + Phase 1 shipped contracts (no separate discuss-phase)

<domain>
## Phase Boundary

Prove “any camera works”: realtime capture from commodity sources into a keep-latest Frame Bus, plus a browser live preview — **no ML models** yet.

**In scope:**
- USB UVC camera capture (OpenCV or equivalent)
- File / video sources for local dev and CI
- Synthetic frame source for automated tests
- RTSP / network camera source (or documented known limits)
- Frame Bus with keep-latest drop policy, drop/FPS metrics
- Camera disconnect/reconnect with clear error state (no silent freeze)
- FastAPI shell + MJPEG and/or WebSocket preview
- Minimal web page showing live camera video (UI-01)
- Default bind **localhost** only (MODEL-03); remote exposure opt-in and documented
- Extend Phase 1 plugin sources with real implementations
- Carry image payload on Frame path (Phase 1 Frame was identity-only)

**Out of scope for this phase:**
- Object detection, depth, free-space (Phases 3–5)
- Detection overlays, thresholds, stage toggles (Phases 5–6)
- Full developer dashboard polish (Phase 6)
- WebRTC (later if needed)
- Multi-camera fusion
- Perception stream `/v1` robot API completeness (Phase 5) — preview API only is fine
- torch / ultralytics / model weights

</domain>

<decisions>
## Implementation Decisions

### From project + research (locked)
- Sources write to **Frame Bus only**; workers never open cameras
- **Keep-latest** drop policy; never unbounded capture queues
- **UI is a subscriber**, not on the inference hot path
- Single camera first; `camera_id` already on Frame
- Localhost default bind
- OpenCV headless first; PyAV/GStreamer when RTSP needs it
- MJPEG/WS JPEG preview first; WebRTC later if lag hurts
- Phase 1 package: `sentry-ai` / `sentry_ai`, CLI `sentry`

### From Phase 1 shipped code (must respect)
- `CameraSource` protocol: `open()`, `read() -> Frame`, `close()`, `name`
- `Frame` has `frame_id`, `camera_id`, `t_capture`, optional `t_ingest`, `width`/`height`
- Plugin registry + entry points for sources
- Built-in `synthetic` source exists as stub — upgrade or replace with real synthetic that can feed bus

### Claude's Discretion
- Whether Frame gains `image_jpeg: bytes` / numpy buffer vs separate `FrameBuffer` type
- Threading model: capture thread + async FastAPI vs all asyncio
- Static HTML vs minimal Vite for preview page (research recommended MJPEG/WS first — lean HTML is OK for Phase 2)
- Exact reconnect backoff policy
- Whether `sentry serve` / `sentry preview` is the CLI entry for the server

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase 1 shipped contracts
- `src/sentry_ai/schemas/frame.py` — Frame identity
- `src/sentry_ai/plugins/protocols.py` — CameraSource Protocol
- `src/sentry_ai/plugins/registry.py` — registry + entry points
- `src/sentry_ai/plugins/builtins.py` — synthetic/noop/null stubs
- `src/sentry_ai/cli.py` — CLI entry
- `src/sentry_ai/config/` — profiles + load

### Planning
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md` — CAM-01..06, UI-01, MODEL-03
- `.planning/ROADMAP.md` — Phase 2 success criteria
- `.planning/phases/01-foundations-contracts/01-SUMMARY.md` or plan SUMMARYs
- `.planning/research/SUMMARY.md` — Phase 2 spine
- `.planning/research/ARCHITECTURE.md` — Frame Bus rules
- `.planning/research/STACK.md` — OpenCV, FastAPI, capture notes
- `.planning/research/PITFALLS.md` — latency, queues, bind, camera chaos

</canonical_refs>

<specifics>
## Specific Ideas

- Roadmap plans: 02-01 sources+reconnect, 02-02 frame bus, 02-03 FastAPI+preview+RTSP
- Success: plug USB or use file/synthetic → browser shows live video on localhost
- Metrics: drop counts, capture FPS visible somehow (API or preview page)

</specifics>

<deferred>
## Deferred Ideas

- Detection / depth / free-space → Phases 3–5
- Interactive controls / open-vocab → Phase 6
- Full `/v1` perception stream → Phase 5
- WebRTC → post-v1 if needed
- Edge packaging → Phase 7

</deferred>

---
*Phase: 02-camera-ingest-live-preview*  
*Context gathered: 2026-08-07*
