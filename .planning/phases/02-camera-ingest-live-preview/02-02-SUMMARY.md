---
phase: 02-camera-ingest-live-preview
plan: 02
subsystem: capture
tags: [FrameBus, CaptureLoop, keep-latest, reconnect, BusMetrics, StatusSnapshot, threading]

requires:
  - phase: 02-01
    provides: "ImageFrame, SourceStatus, SourceError/SourceDisconnected, SyntheticSource, make_image_frame"
provides:
  - "FrameBus depth-1 keep-latest mailbox with BusMetrics (CAM-05)"
  - "CaptureLoop daemon thread with exponential reconnect backoff (CAM-06)"
  - "StatusSnapshot wire DTO + CaptureLoop.build_status for 02-03 API"
affects:
  - 02-03-preview-api-rtsp
  - phase-3-perception-workers

tech-stack:
  added: []
  patterns:
    - "Depth-1 FrameBus with threading.Lock; overwrite-count drops"
    - "Capture owns source lifecycle; FastAPI only subscribes via bus/status"
    - "Exponential reconnect backoff 0.25→5.0 ×2"
    - "Lazy CaptureLoop package export avoids bus↔capture circular import"
    - "StatusSnapshot Pydantic extra=forbid for wire status"

key-files:
  created:
    - src/sentry_ai/bus/__init__.py
    - src/sentry_ai/bus/frame_bus.py
    - src/sentry_ai/capture/loop.py
  modified:
    - src/sentry_ai/capture/__init__.py
    - src/sentry_ai/capture/status.py
    - tests/test_frame_bus.py
    - tests/test_capture_loop_reconnect.py

key-decisions:
  - "frames_dropped is overwrite-count (publish while slot occupied), not claim-based"
  - "get_latest is non-consuming keep-latest (not queue pop)"
  - "Lazy __getattr__ export of CaptureLoop breaks bus↔capture import cycle"
  - "ERROR until first successful open; RECONNECTING after first success on open/read failure"
  - "StatusSnapshot.bind defaults None until 02-03 serve sets it"

patterns-established:
  - "FrameBus: single-slot mailbox + Lock + 1s monotonic FPS window"
  - "CaptureLoop: daemon thread, interruptible backoff sleep, status_detail for UI"
  - "build_status combines loop + bus + latest meta without FastAPI"

requirements-completed: [CAM-05, CAM-06]

duration: 4min
completed: 2026-08-07
---

# Phase 2 Plan 02: FrameBus & CaptureLoop Summary

**Depth-1 keep-latest FrameBus with drop/FPS metrics plus daemon CaptureLoop reconnect spine so FastAPI only subscribes (CAM-05/CAM-06)**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-07T15:44:20Z
- **Completed:** 2026-08-07T15:48:38Z
- **Tasks:** 3/3
- **Files modified:** 7

## Accomplishments

- Implemented `FrameBus` + `BusMetrics`: depth-1 mailbox, overwrite-count drops, 1-second `capture_fps` window, isolated `metrics_snapshot`
- Implemented `CaptureLoop` daemon thread owning source open/read/close, publishing only to the bus, exponential reconnect backoff with visible `SourceStatus` + `status_detail`
- Added `StatusSnapshot` (Pydantic, `extra="forbid"`) and `CaptureLoop.build_status()` for 02-03 `/api/status` without HTTP wiring here
- CAM-05/CAM-06 unit coverage green; full suite 96 passed; ruff clean; no `queue.Queue` backlog

## Task Commits

Each task was committed atomically:

1. **Task 1: FrameBus keep-latest + BusMetrics (CAM-05)** - `80243a1` (test RED) → `8366a7b` (feat GREEN)
2. **Task 2: CaptureLoop thread + reconnect (CAM-06)** - `2c3b5f6` (test RED) → `3ef3e98` (feat GREEN)
3. **Task 3: StatusSnapshot + build_status** - `678c311` (feat)

**Plan metadata:** `08e31b9` (docs: complete plan)

_Note: TDD tasks produced RED then GREEN commits._

## Files Created/Modified

- `src/sentry_ai/bus/frame_bus.py` — Thread-safe keep-latest mailbox + BusMetrics
- `src/sentry_ai/bus/__init__.py` — Re-exports FrameBus, BusMetrics
- `src/sentry_ai/capture/loop.py` — CaptureLoop with reconnect policy + build_status
- `src/sentry_ai/capture/status.py` — SourceStatus + StatusSnapshot wire model
- `src/sentry_ai/capture/__init__.py` — Lazy CaptureLoop export; StatusSnapshot export
- `tests/test_frame_bus.py` — CAM-05 coverage (depth-1, drops, snapshot isolation, concurrent smoke)
- `tests/test_capture_loop_reconnect.py` — CAM-06 happy/reconnect/open-fail + build_status

## Decisions Made

- **Overwrite-count drops:** every publish while the slot is occupied increments `frames_dropped` (matches “never process backlog”)
- **Non-consuming get_latest:** subscribers peek; bus does not pop on read
- **Status policy:** ERROR before first successful open; RECONNECTING after; STREAMING on successful publish
- **bind deferred:** StatusSnapshot.bind is optional until CLI serve (02-03)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import bus ↔ capture**
- **Found during:** Task 2 GREEN
- **Issue:** `capture/__init__` imported `CaptureLoop` which imports `FrameBus`, while `frame_bus` imports `ImageFrame` via the capture package — partial init ImportError
- **Fix:** Lazy `CaptureLoop` export via `__getattr__` in `capture/__init__.py`
- **Files modified:** `src/sentry_ai/capture/__init__.py`
- **Commit:** `3ef3e98`

**2. [Rule 1 - Bug] Test import of `tests.conftest` failed**
- **Found during:** Task 1 GREEN
- **Issue:** `from tests.conftest import make_image_frame` raised ModuleNotFoundError (tests is not a package)
- **Fix:** Use `image_frame_factory` pytest fixture from conftest
- **Files modified:** `tests/test_frame_bus.py`
- **Commit:** `8366a7b`

## Threat Flags

None — no new network endpoints, auth paths, or trust-boundary surfaces beyond plan threat model (process-local bus + future status wire DTO).

## Known Stubs

None — FrameBus and CaptureLoop are fully implemented; 02-03 FastAPI/MJPEG remain out of scope.

## Verification

- [x] `pytest tests/test_frame_bus.py -q` green (CAM-05)
- [x] `pytest tests/test_capture_loop_reconnect.py -q` green (CAM-06)
- [x] No unbounded frame queue in bus or loop
- [x] CaptureLoop stop/join clean under pytest
- [x] Status snapshot includes fps + drops + status enum
- [x] Full suite green (96 passed); ruff clean

## Self-Check: PASSED

- All key files present
- Commits `80243a1`, `8366a7b`, `2c3b5f6`, `3ef3e98`, `678c311` present on main
