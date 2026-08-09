---
phase: 02-camera-ingest-live-preview
plan: 03
subsystem: api
tags: [fastapi, mjpeg, uvicorn, opencv, rtsp, typer, live-preview]

requires:
  - phase: 02-camera-ingest-live-preview (02-01)
    provides: ImageFrame, SyntheticSource, OpenCVSource USB/file, SourceError
  - phase: 02-camera-ingest-live-preview (02-02)
    provides: FrameBus, CaptureLoop, StatusSnapshot / build_status
provides:
  - FastAPI create_app with MJPEG + /api/status + static Live Preview
  - sentry serve CLI (default host 127.0.0.1)
  - RTSP OpenCV source plugin + camera-sources docs
affects:
  - phase-03-depth-models
  - phase-05-perception-stream
  - phase-06-dashboard

tech-stack:
  added: [fastapi>=0.141, uvicorn[standard]>=0.52, httpx>=0.28]
  patterns:
    - "create_app injects bus+CaptureLoop; handlers never open cameras"
    - "MJPEG StreamingResponse + asyncio.sleep ~30 FPS UI cap"
    - "Packaged static HTML via hatch force-include"
    - "MODEL-03 localhost default bind with LAN opt-in warning"

key-files:
  created:
    - src/sentry_ai/api/__init__.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/ui/static/index.html
    - docs/camera-sources.md
    - tests/test_api_preview.py
    - tests/test_cli_serve.py
    - tests/test_sources_rtsp.py
  modified:
    - src/sentry_ai/cli.py
    - src/sentry_ai/plugins/registry.py
    - src/sentry_ai/sources/opencv_source.py
    - src/sentry_ai/sources/__init__.py
    - pyproject.toml
    - uv.lock
    - README.md

key-decisions:
  - "MJPEG multipart StreamingResponse + static HTML (no Vite/React)"
  - "create_app does not start CaptureLoop — caller owns lifecycle for TestClient"
  - "RTSP is OpenCV URL best-effort; PyAV deferred with docs"
  - "serve --host defaults to 127.0.0.1 (MODEL-03)"

patterns-established:
  - "API package factory + app.state injection (no process globals)"
  - "UI is pure bus subscriber (get_latest + imencode only)"
  - "CLI serve builds source → FrameBus → CaptureLoop → uvicorn"

requirements-completed: [CAM-04, UI-01, MODEL-03]

duration: 8min
completed: 2026-08-07
---

# Phase 2 Plan 03: FastAPI Live Preview + RTSP Serve Summary

**Localhost FastAPI MJPEG Live Preview with status pill, RTSP OpenCV plugin, and `sentry serve` defaulting to 127.0.0.1**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-08-07T15:54:14Z
- **Completed:** 2026-08-07T16:02:00Z
- **Tasks:** 3/3
- **Files modified:** 16

## Accomplishments

- FastAPI `create_app` serves `/api/status`, `/preview/mjpeg` (multipart JPEG + `asyncio.sleep`), and UI-SPEC Live Preview HTML at `/`
- Packaged static page auto-connects MJPEG, polls status for pill/FPS/drops/bind (no autonomous/motor language)
- `RtspSource` + registry/entry point; `docs/camera-sources.md` documents RTSP limits
- `sentry serve` wires capture thread + uvicorn; default host `127.0.0.1` with LAN opt-in warning
- Full suite green: 115 pytest, ruff clean; no torch/ultralytics/PyAV

## Task Commits

Each task was committed atomically:

1. **Task 1: FastAPI app factory + MJPEG + status routes** - `373692c` (feat)
2. **Task 2: Static Live Preview page + packaging** - `2d2b7bf` (feat)
3. **Task 3: RTSP source + sentry serve + docs** - `141e4a8` (feat)

**Plan metadata:** `6fd6deb` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/api/app.py` — `create_app(bus, capture_loop, bind=...)`
- `src/sentry_ai/api/routes_preview.py` — status JSON, MJPEG generator, GET `/`
- `src/sentry_ai/api/deps.py` — typed `AppState` holder
- `src/sentry_ai/ui/static/index.html` — UI-SPEC Live Preview page
- `src/sentry_ai/cli.py` — `serve` command + source builder
- `src/sentry_ai/sources/opencv_source.py` — `RtspSource`
- `docs/camera-sources.md` — source matrix + RTSP known limits
- `README.md` — one-command preview + localhost/privacy notes
- `tests/test_api_preview.py`, `test_cli_serve.py`, `test_sources_rtsp.py`

## Decisions Made

- MJPEG over WebSocket/WebRTC for zero-build HTML (locked UI-SPEC)
- Capture lifecycle owned by CLI/tests, not `create_app` (deterministic TestClient)
- Infinite MJPEG stream tested via async generator one-shot + route media_type (avoids TestClient hang on open stream)
- httpx kept under `optional-dependencies.dev` (project convention) rather than uv `dependency-groups`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] TestClient hung on infinite MJPEG stream**
- **Found during:** Task 1
- **Issue:** `TestClient.stream("GET", "/preview/mjpeg")` never completed iteration against infinite generator
- **Fix:** Assert multipart via async generator `__anext__` + route media_type without full HTTP stream consume
- **Files modified:** `tests/test_api_preview.py`
- **Verification:** `pytest tests/test_api_preview.py` green
- **Committed in:** `373692c`

**2. [Rule 3 - Blocking] FastAPI rejected union FileResponse|HTMLResponse response model**
- **Found during:** Task 2
- **Issue:** `@router.get("/")` with union return type raised FastAPIError at import
- **Fix:** `response_model=None` on root route
- **Files modified:** `src/sentry_ai/api/routes_preview.py`
- **Verification:** GET `/` returns 200 with Live Preview title
- **Committed in:** `2d2b7bf`

**3. [Rule 2 - Critical] httpx placement under dependency-groups**
- **Found during:** Task 1
- **Issue:** `uv add --dev` placed httpx in `[dependency-groups]` instead of existing `[project.optional-dependencies] dev`
- **Fix:** Moved httpx into `optional-dependencies.dev` to match project install (`uv sync --extra dev`)
- **Files modified:** `pyproject.toml`
- **Verification:** `uv sync --extra dev` + tests import TestClient
- **Committed in:** `373692c`

---

**Total deviations:** 3 auto-fixed (1 Rule 1, 1 Rule 2, 1 Rule 3)
**Impact on plan:** Necessary for correctness and CI determinism; no scope creep

## Issues Encountered

- Starlette deprecation warning: TestClient prefers `httpx2` — non-blocking for Phase 2; continue with httpx 0.28

## User Setup Required

None — synthetic path works offline; USB/RTSP are operator hardware

## Known Stubs

None that block Phase 2 goals. Phase 3+ ML workers remain stubs by design.

## Threat Flags

None beyond plan threat model (localhost unauthenticated preview is intentional MODEL-03).

## Verification

```text
uv run pytest -q  → 115 passed
uv run ruff check src tests  → All checks passed
uv run sentry serve --help  → --host default 127.0.0.1
grep torch/ultralytics/av pyproject  → none
```

## Next Phase Readiness

Phase 2 vertical slice complete: sources → bus → browser. Ready for Phase 3 depth models to consume `FrameBus.get_latest()` without touching cameras.

## Self-Check: PASSED

- FOUND: `src/sentry_ai/api/app.py`
- FOUND: `src/sentry_ai/api/routes_preview.py`
- FOUND: `src/sentry_ai/ui/static/index.html`
- FOUND: `docs/camera-sources.md`
- FOUND commits: `373692c`, `2d2b7bf`, `141e4a8`
