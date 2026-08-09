---
phase: 02-camera-ingest-live-preview
verified: 2026-08-07T16:06:01Z
status: human_needed
score: 6/6 must-haves verified
overrides_applied: 0
gaps: []
human_verification:
  - test: "Run `uv run sentry serve --source synthetic` and open http://127.0.0.1:8000/"
    expected: "Green streaming pill, moving green bar MJPEG, FPS/drops/bind metrics update"
    why_human: "Browser visual appearance and realtime MJPEG smoothness cannot be fully asserted via TestClient"
  - test: "If a USB camera is available: `uv run sentry serve --source usb --device 0`, then unplug cable"
    expected: "Status pill goes reconnecting/error with banner; page does not hard-freeze; replug returns to streaming"
    why_human: "Real UVC disconnect requires physical hardware not present in CI"
  - test: "Optional lab RTSP: `uv run sentry serve --source rtsp --url rtsp://…`"
    expected: "Frames appear or reconnect status; latency matches docs (100–500ms class)"
    why_human: "Live network camera not available in automated environment; CAM-04 allows documented limits"
---

# Phase 2: Camera Ingest & Live Preview Verification Report

**Phase Goal:** Prove “any camera works” with a realtime capture loop, keep-latest frame bus, and browser preview — no models yet.  
**Verified:** 2026-08-07T16:06:01Z  
**Status:** human_needed  
**Re-verification:** No — initial verification  

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | USB camera and file/video source produce live frames with stable `frame_id`s | ✓ VERIFIED | `UsbSource`/`FileSource` via `OpenCVSource`: monotonic `_next_frame_id`, `CAP_PROP_BUFFERSIZE=1`, real file fixture reads ids 0,1,2…; USB mocked `VideoCapture(0)` + buffersize in `tests/test_sources_opencv.py`; file real clip in `tests/test_sources_file.py` (115 suite green) |
| 2 | Synthetic source powers automated tests without hardware | ✓ VERIFIED | `SyntheticSource` patterned BGR HxWx3 uint8, fps=0 default; used by smoke CLI, CaptureLoop tests, API tests; `uv run sentry smoke` OK |
| 3 | RTSP/network camera source works or is documented with known limits | ✓ VERIFIED | `RtspSource` + registry/entry-point `rtsp`; mock open/read tests; `docs/camera-sources.md` documents latency, freezes, FFmpeg variance, credentials, deferred PyAV/GStreamer |
| 4 | Frame bus drops oldest under load and reports drop metrics (no unbounded queue) | ✓ VERIFIED | Depth-1 `_latest` slot; overwrite increments `frames_dropped`; no `queue.Queue`; metrics expose published/dropped/fps/last_publish_t; 50 publishes → 49 drops, latest frame_id=49 |
| 5 | Browser shows live preview; camera unplug surfaces clear error/recovery path | ✓ VERIFIED | GET `/` HTML auto-connects `/preview/mjpeg`; status poll shows reconnecting/error banner; CaptureLoop sets RECONNECTING + backoff + re-open; API `/api/status` exposes status/status_detail; tests for MJPEG JPEG parts + disconnect recovery |
| 6 | Default server bind is localhost | ✓ VERIFIED | `serve --host` default `127.0.0.1`; LAN warning for non-localhost; `create_app` default bind `127.0.0.1:8000`; help + tests assert default |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/sentry_ai/capture/image_frame.py` | ImageFrame meta+BGR | ✓ VERIFIED | 29 lines, slots dataclass, frame_id/camera_id props |
| `src/sentry_ai/capture/status.py` | SourceStatus + StatusSnapshot | ✓ VERIFIED | StrEnum + Pydantic extra=forbid wire DTO |
| `src/sentry_ai/sources/synthetic.py` | CAM-03 synthetic | ✓ VERIFIED | 67 lines, real patterned frames |
| `src/sentry_ai/sources/opencv_source.py` | USB/file/RTSP OpenCV | ✓ VERIFIED | 160 lines; Usb/File/Rtsp subclasses; BUFFERSIZE=1 |
| `src/sentry_ai/sources/errors.py` | SourceError hierarchy | ✓ VERIFIED | SourceError + SourceDisconnected |
| `src/sentry_ai/bus/frame_bus.py` | Keep-latest + metrics | ✓ VERIFIED | 74 lines; Lock; overwrite drops |
| `src/sentry_ai/capture/loop.py` | CaptureLoop reconnect | ✓ VERIFIED | 222 lines; daemon thread; backoff 0.25→5.0×2 |
| `src/sentry_ai/api/app.py` | create_app factory | ✓ VERIFIED | Injects bus+loop; no capture start |
| `src/sentry_ai/api/routes_preview.py` | MJPEG + status + `/` | ✓ VERIFIED | bus-only handlers; asyncio.sleep ~30 FPS |
| `src/sentry_ai/ui/static/index.html` | Live Preview UI | ✓ VERIFIED | 215 lines; pill, banner, metrics, MJPEG img |
| `src/sentry_ai/cli.py` | health/smoke/serve | ✓ VERIFIED | serve wires source→bus→loop→uvicorn |
| `docs/camera-sources.md` | RTSP limits + matrix | ✓ VERIFIED | 69 lines; honest limits table |
| `tests/test_*` (phase) | CAM/UI/MODEL coverage | ✓ VERIFIED | sources, bus, loop, api, serve, rtsp |

gsd-sdk `verify.artifacts`: 02-01 9/9, 02-02 4/4 passed.

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `protocols.CameraSource` | `ImageFrame` | `read() -> ImageFrame` | ✓ WIRED | `plugins/protocols.py:22` |
| `synthetic.py` | `schemas.frame.Frame` | `Frame(...)` meta | ✓ WIRED | constructs Frame with frame_id |
| `builtins.py` | `SyntheticSource` | re-export | ✓ WIRED | import from sources.synthetic |
| `registry.register_builtins` | usb/file/rtsp | skip-if-present | ✓ WIRED | registers all four sources |
| `cli.smoke` | ImageFrame.meta | PerceptionFrame fields | ✓ WIRED | meta.frame_id/camera_id/t_capture |
| `capture/loop.py` | `FrameBus.publish` | capture thread | ✓ WIRED | `self._bus.publish(frame)` |
| `capture/loop.py` | source.read/open/close | thread-owned lifecycle | ✓ WIRED | only in `_run` |
| `frame_bus.py` | `threading.Lock` | serialize mailbox | ✓ WIRED | publish/get_latest/metrics |
| `routes_preview` | `bus.get_latest` + imencode | MJPEG | ✓ WIRED | no VideoCapture in routes |
| `index.html` | `/preview/mjpeg` | img src | ✓ WIRED | auto-connect |
| `index.html` | `/api/status` | poll 500ms | ✓ WIRED | fetch + setInterval |
| `cli.serve` | uvicorn + CaptureLoop | start/stop | ✓ WIRED | loop.start → uvicorn.run → finally stop |

Note: gsd-sdk `verify.key-links` reported false negatives (regex escaping / path labels). Manual code inspection confirms all links WIRED.

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| MJPEG generator | `item = bus.get_latest()` | CaptureLoop → FrameBus.publish | Synthetic/OpenCV ImageFrame BGR | ✓ FLOWING |
| `/api/status` | `loop.build_status()` | loop status + bus metrics + latest meta | Real enums/metrics | ✓ FLOWING |
| index.html metrics | fetch `/api/status` | StatusSnapshot JSON | Dynamic status/fps/drops | ✓ FLOWING |
| FrameBus slot | `_latest` | source.read ImageFrame | Real ndarray + Frame meta | ✓ FLOWING |

No hollow/static empty paths on the preview pipeline. Handlers never open cameras.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full unit suite | `uv run pytest -q` | 115 passed, 1 Starlette deprecation warning | ✓ PASS |
| Lint | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Health plugins | `uv run sentry health` | sources: file, rtsp, synthetic, usb; status: ok | ✓ PASS |
| Smoke synthetic | `uv run sentry smoke` | validated 3 synthetic PerceptionFrame(s) | ✓ PASS |
| Serve defaults | `uv run sentry serve --help` | `[default: 127.0.0.1]` | ✓ PASS |
| Runtime bus+API | uv run python create_app TestClient | streaming + Live Preview HTML | ✓ PASS |
| No ML required deps | pyproject dependencies | no torch/ultralytics | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| (none declared) | — | Phase has no `scripts/*/tests/probe-*.sh` | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| CAM-01 | 02-01 | USB UVC via OpenCV | ✓ SATISFIED | UsbSource + mock VideoCapture(index)+BUFFERSIZE=1 |
| CAM-02 | 02-01 | File/video sources | ✓ SATISFIED | FileSource + real mp4 fixture tests + loop_file |
| CAM-03 | 02-01 | Synthetic for tests | ✓ SATISFIED | SyntheticSource + smoke + suite |
| CAM-04 | 02-03 | RTSP/network | ✓ SATISFIED | RtspSource + docs known limits + mock tests |
| CAM-05 | 02-02 | Keep-latest + drop/FPS metrics | ✓ SATISFIED | FrameBus depth-1 overwrite-count |
| CAM-06 | 02-02 | Disconnect/reconnect clear state | ✓ SATISFIED | CaptureLoop RECONNECTING/ERROR + UI banner + API |
| UI-01 | 02-03 | Live camera video | ✓ SATISFIED | MJPEG + static Live Preview + TestClient |
| MODEL-03 | 02-03 | Default localhost bind | ✓ SATISFIED | serve host default + LAN opt-in warning + docs |

No orphaned Phase 2 requirements.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/XXX/TODO in phase source | — | Clean |
| — | — | No queue.Queue backlog | — | CAM-05 intact |
| — | — | No torch/ultralytics required deps | — | “no models” intact |
| `README.md` | ~44 | Example path `tests/fixtures/sample_clip.mp4` | ℹ️ Info | Fixture dir only has `.gitkeep`; file source still works with any path; tests write temp clips |

### Human Verification Required

### 1. Synthetic browser Live Preview

**Test:** `uv run sentry serve --source synthetic` → open `http://127.0.0.1:8000/`  
**Expected:** Streaming pill (green), moving green bar, FPS/drops/bind update  
**Why human:** Visual smoothness / browser rendering not fully covered by ASGI TestClient  

### 2. USB unplug recovery (hardware)

**Test:** `uv run sentry serve --source usb --device 0`, unplug camera  
**Expected:** reconnecting/error banner + status_detail; no permanent silent freeze; recovery on replug  
**Why human:** Physical UVC not available in CI (adapter path is mock-tested)  

### 3. Optional RTSP lab

**Test:** `uv run sentry serve --source rtsp --url "rtsp://…"`  
**Expected:** Frames or reconnect path; latency within documented class  
**Why human:** Live IP camera not in CI; CAM-04 allows documented best-effort  

### Gaps Summary

**No blocking gaps.** All six roadmap success criteria are implemented, wired, and covered by automated tests or honest documentation (RTSP). Residual work is optional human UAT for real browser feel and physical USB/RTSP hardware — already checklisted in `docs/camera-sources.md`.

Phase goal achieved in code: any registered source → CaptureLoop → keep-latest FrameBus → localhost FastAPI Live Preview, without models.

---

_Verified: 2026-08-07T16:06:01Z_  
_Verifier: Claude (gsd-verifier)_
