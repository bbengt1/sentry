---
phase: 02-camera-ingest-live-preview
plan: 01
subsystem: capture
tags: [opencv, numpy, ImageFrame, CameraSource, synthetic, usb, file]

requires:
  - phase: 01-foundations-contracts
    provides: "Frame identity schema, CameraSource protocol, plugin registry, CLI smoke"
provides:
  - "Runtime ImageFrame (meta Frame + BGR ndarray)"
  - "SourceStatus enum and SourceError/SourceDisconnected hierarchy"
  - "Real SyntheticSource with patterned BGR (CAM-03)"
  - "OpenCVSource USB + file adapters (CAM-01, CAM-02)"
  - "Plugin registry + entry points for synthetic/usb/file"
  - "Wave 0 skip stubs for FrameBus, capture loop, RTSP, serve/API"
affects:
  - 02-02-frame-bus-capture-loop
  - 02-03-preview-api-rtsp

tech-stack:
  added: [opencv-python-headless, numpy]
  patterns:
    - "ImageFrame runtime dataclass separate from Pydantic Frame"
    - "CameraSource.read() -> ImageFrame"
    - "OpenCV multi-source adapter with thin UsbSource/FileSource plugins"
    - "SourceDisconnected for reconnect foundation"

key-files:
  created:
    - src/sentry_ai/capture/image_frame.py
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/sources/errors.py
    - src/sentry_ai/sources/synthetic.py
    - src/sentry_ai/sources/opencv_source.py
    - tests/test_sources_synthetic.py
    - tests/test_sources_file.py
    - tests/test_sources_opencv.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/sentry_ai/plugins/protocols.py
    - src/sentry_ai/plugins/builtins.py
    - src/sentry_ai/plugins/registry.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/config/models.py
    - tests/conftest.py
    - tests/test_plugins_registry.py

key-decisions:
  - "ImageFrame is a slots dataclass (meta + image_bgr); Frame stays identity-only"
  - "SyntheticSource lives in sources/ and is re-exported from plugins.builtins for entry-point stability"
  - "UsbSource/FileSource thin subclasses of OpenCVSource with fixed name attrs"
  - "Default synthetic fps=0.0 so unit tests never sleep"
  - "Empty file path rejected with ValueError before VideoCapture (T-2-01)"

patterns-established:
  - "Runtime pixels never on Pydantic Frame"
  - "Source adapters own monotonic frame_id and epoch timestamps"
  - "register_builtins skip-if-present for usb/file alongside synthetic"
  - "Wave 0 skip-marked test modules for later plans"

requirements-completed: [CAM-01, CAM-02, CAM-03]

duration: 4min
completed: 2026-08-07
---

# Phase 2 Plan 01: Camera Source Adapters Summary

**Runtime ImageFrame + OpenCV/synthetic sources delivering CAM-01/02/03 at the adapter layer without numpy on Pydantic Frame**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-07T15:37:16Z
- **Completed:** 2026-08-07T15:41:08Z
- **Tasks:** 3/3
- **Files modified:** 25

## Accomplishments

- Introduced `ImageFrame` (Frame meta + HxWx3 uint8 BGR) and evolved `CameraSource.read() -> ImageFrame`
- Shipped real `SyntheticSource` with deterministic green-bar pattern; migrated CLI smoke and registry tests
- Implemented `OpenCVSource` / `UsbSource` / `FileSource` with BUFFERSIZE=1, loop-on-EOF, and `SourceDisconnected`
- Registered usb/file in builtins + entry points; `sentry health` lists `file, synthetic, usb`
- Wave 0 skip stubs for bus/loop/RTSP/API/serve; `make_image_frame` fixture for later plans

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 deps, ImageFrame, status/errors, protocol, stubs** - `f509386` (feat)
2. **Task 2: Real SyntheticSource (CAM-03) + migrate consumers** - `99e2103` (test RED) → `ddb92f1` (feat GREEN)
3. **Task 3: OpenCVSource USB + file (CAM-01/02) + registry** - `7b9943b` (test RED) → `f7e7e15` (feat GREEN)

**Plan metadata:** `824450a` (docs: complete plan)

_Note: TDD tasks produced RED then GREEN commits._

## Files Created/Modified

- `src/sentry_ai/capture/image_frame.py` — runtime ImageFrame dataclass
- `src/sentry_ai/capture/status.py` — SourceStatus StrEnum
- `src/sentry_ai/sources/errors.py` — SourceError / SourceDisconnected
- `src/sentry_ai/sources/synthetic.py` — CAM-03 patterned BGR source
- `src/sentry_ai/sources/opencv_source.py` — OpenCVSource + UsbSource + FileSource
- `src/sentry_ai/plugins/protocols.py` — CameraSource.read → ImageFrame
- `src/sentry_ai/plugins/builtins.py` — re-export SyntheticSource; NoopWorker accepts ImageFrame
- `src/sentry_ai/plugins/registry.py` — register usb/file skip-if-present
- `src/sentry_ai/cli.py` — smoke uses image.meta
- `src/sentry_ai/config/models.py` — SourceConfig device/path/url/camera_id
- `pyproject.toml` / `uv.lock` — opencv-python-headless, numpy; usb/file entry points
- `tests/conftest.py` — make_image_frame helper
- `tests/test_sources_*.py` — CAM-01/02/03 coverage + Wave 0 skip stubs

## Decisions Made

- Kept Phase 1 entry point `sentry_ai.plugins.builtins:SyntheticSource` stable via re-export
- Thin `UsbSource`/`FileSource` subclasses rather than factory callables so registry stores real classes with `name` attrs
- File loop defaults True; USB loop defaults False
- No fastapi/torch installed (deferred per plan)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. TDD RED phases correctly failed on missing modules; GREEN implementations passed full suite.

## User Setup Required

None — no external services; USB hardware not required (mocked).

## Known Stubs

Wave 0 skip-only modules (intentional; filled in later plans):

| File | Reason |
|------|--------|
| `tests/test_sources_rtsp.py` | plan 02-03 |
| `tests/test_frame_bus.py` | plan 02-02 |
| `tests/test_capture_loop_reconnect.py` | plan 02-02 |
| `tests/test_api_preview.py` | plan 02-03 |
| `tests/test_cli_serve.py` | plan 02-03 |

No production stubs block CAM-01/02/03 source-adapter goals.

## TDD Gate Compliance

- Task 2: RED `99e2103` → GREEN `ddb92f1`
- Task 3: RED `7b9943b` → GREEN `f7e7e15`

## Verification

```
uv run pytest -q  → 78 passed
uv run sentry health → sources: file, synthetic, usb
uv run ruff check src tests → All checks passed
No fastapi/torch in dependencies
```

## Self-Check: PASSED

- All must-have artifacts present
- All task commits present on main
- Phase 1 consumers (smoke, registry, Frame schema) green after protocol evolution
