---
phase: 03-fixed-class-detection
plan: 02
subsystem: detection-api-ui
tags: [opencv-overlay, mjpeg, snapshot, conf-patch, perception-store, live-preview, det-03, det-04]

# Dependency graph
requires:
  - phase: 03-fixed-class-detection
    provides: YoloDetectionWorker, DetectionLoop, PerceptionStore, configure_model_cache, tier_to_weight
  - phase: 02-camera-ingest-live-preview
    provides: create_app, routes_preview MJPEG, CaptureLoop, StatusSnapshot, index.html
provides:
  - draw_detections pure OpenCV overlay helper
  - GET /api/snapshot PerceptionFrame JSON (DET-04)
  - GET/PATCH /api/detection/config runtime conf (DET-03)
  - MJPEG server-side boxes from same PerceptionStore
  - Status det telemetry (count, latency, conf, fps, frame_id)
  - Live Preview conf slider + det metrics
  - sentry serve DetectionLoop lifecycle with graceful degrade
affects:
  - phase-04-depth
  - phase-05-perception-stream
  - phase-06-open-vocab

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Server-side OpenCV draw before MJPEG imencode (Option A)
    - create_app optional perception_store + detection_worker injection
    - Status det fields merged in api_status (capture loop stays clean)
    - Debounced conf PATCH from UI (150ms)
    - 404 empty store product; 503 missing worker/store

key-files:
  created:
    - src/sentry_ai/models/detection/overlay.py
    - src/sentry_ai/api/routes_detection.py
  modified:
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - README.md
    - tests/test_detection_overlay.py
    - tests/test_api_detection.py
    - tests/test_api_preview.py
    - tests/test_cli_serve.py

key-decisions:
  - "Overlay transport Option A: server OpenCV draw before JPEG encode"
  - "GET /api/snapshot 404 when no product yet (not 503)"
  - "Det metrics merged in api_status from store/worker — CaptureLoop not coupled"
  - "serve always injects PerceptionStore; worker/loop only when detect extra importable"

patterns-established:
  - "MJPEG + snapshot + UI metrics all read PerceptionStore only"
  - "Handlers never open cameras or call worker.process / predict"
  - "DetectionConfigUpdate conf Field(ge=0,le=1) extra=forbid"
  - "serve: capture start → det start; finally det stop → capture stop"

requirements-completed: [DET-03, DET-04]

# Metrics
duration: 5min
completed: 2026-08-07
---

# Phase 3 Plan 02: Detection Overlays + API + UI Summary

**Server-side OpenCV overlays on MJPEG, GET /api/snapshot PerceptionFrame parity, runtime conf PATCH, status telemetry, Live Preview controls, and sentry serve DetectionLoop wiring — DET-03/DET-04 closed.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-08-07T19:22:21Z
- **Completed:** 2026-08-07T19:26:46Z
- **Tasks:** 3/3
- **Files modified:** 14

## Accomplishments

- Pure `draw_detections` draws labeled boxes (`{class} {conf:.2f}`) without ultralytics
- `GET /api/snapshot` returns `PerceptionFrame` with `completeness.detections=true` matching store product (empty list valid)
- `PATCH /api/detection/config` updates worker conf without restart; 422 on range/extra; 503 when worker missing
- MJPEG encodes bus frame + store overlay — same truth as snapshot (DET-04)
- `/api/status` exposes `detections_count`, `det_latency_ms`, `det_conf`, `det_fps`, `det_frame_id`
- Live Preview conf slider debounced 150ms; Detections/Det ms metrics; first-run cache note
- `sentry serve` starts DetectionLoop when detect extra available; degrades to capture-only with install hint

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED: Overlay + detection API tests** - `f1b60b2` (test)
2. **Task 1 GREEN: Overlay helper + routes + app injection** - `1e9cdf0` (feat)
3. **Task 2 RED: MJPEG overlay / status / serve tests** - `967cd2c` (test)
4. **Task 2 GREEN: MJPEG overlay + status det + serve DetectionLoop** - `4a3c3f2` (feat)
5. **Task 3: Live Preview conf UI + docs polish** - `940dfe6` (feat)

**Plan metadata:** (docs commit after this SUMMARY)

## Files Created/Modified

- `src/sentry_ai/models/detection/overlay.py` — pure OpenCV draw helper
- `src/sentry_ai/api/routes_detection.py` — snapshot + conf GET/PATCH
- `src/sentry_ai/api/app.py` / `deps.py` — optional store/worker injection
- `src/sentry_ai/api/routes_preview.py` — MJPEG overlay + status det merge
- `src/sentry_ai/capture/status.py` — optional det fields on StatusSnapshot
- `src/sentry_ai/cli.py` — serve DetectionLoop lifecycle
- `src/sentry_ai/ui/static/index.html` — conf control + det metrics
- `README.md` — detection API table, cache, serve examples
- `tests/test_detection_overlay.py`, `test_api_detection.py`, `test_api_preview.py`, `test_cli_serve.py`

## Decisions Made

- Empty store → **404** `"no detection product yet"` (prefer over 503; store present but no product)
- Missing store/worker → **503**
- Det telemetry merged in `api_status` rather than CaptureLoop knowing about detection
- Conf debounce 150ms (within 100–200ms UI-SPEC band)
- Temporal skew between RGB frame_id and det frame_id accepted (status/snapshot carry det_frame_id)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Architecture test matched docstring "YOLO"**
- **Found during:** Task 1 GREEN
- **Issue:** `test_routes_detection_has_no_videocapture` asserted `"YOLO" not in source`; module docstring said "YOLO inference"
- **Fix:** Reworded docstring to "model inference"
- **Files modified:** `src/sentry_ai/api/routes_detection.py`
- **Committed in:** `1e9cdf0`

**2. [Rule 1 - Bug] Ruff E501 on new API tests**
- **Found during:** Task 3 verify (full suite ruff)
- **Issue:** Four lines > 88 chars in `test_api_detection.py`
- **Fix:** Wrapped kwargs / split assert locals
- **Files modified:** `tests/test_api_detection.py`
- **Committed in:** `940dfe6`

---

**Total deviations:** 2 auto-fixed (Rule 1 × 2)
**Impact on plan:** Cosmetic/test hygiene only; no architectural change.

## Issues Encountered

None beyond the two auto-fixes above. Full suite: **165 passed**, ruff clean.

## User Setup Required

None for core/CI path. For real YOLO boxes on Live Preview:

```bash
uv sync --extra dev --extra detect
uv run sentry serve --source synthetic
# open http://127.0.0.1:8000/
```

First run may download weights into `SENTRY_MODEL_CACHE` or `~/.cache/sentry-ai/weights` (offline thereafter). AGPL: see `THIRD_PARTY_MODELS.md`.

## Known Stubs

None that block Phase 3 goals. Real YOLO weight download remains manual/offline-demo only (by design — CI uses mocks).

## Threat Flags

None new beyond plan register. Mitigations applied:
- conf PATCH bounded + extra=forbid (T-03-02)
- store-only overlay/snapshot parity (T-03-03)
- UI debounce (T-03-04)
- localhost default preserved (MODEL-03)

## Verification

```text
uv run pytest -q   # 165 passed
uv run ruff check src tests  # All checks passed
```

- Snapshot detections match store product content
- PATCH conf → worker.get_conf matches; GET reflects
- No VideoCapture / predict in detection or preview route handlers
- serve source-inspect confirms PerceptionStore + DetectionLoop + degrade path

## Manual check (not CI gate)

Real YOLO on synthetic/USB after weight download: boxes on MJPEG, conf slider updates overlays without restart, snapshot parity — document for operators; CI does not download weights.

## Next Phase Ready

Phase 3 success criteria met with mocks; DET-01..04 + MODEL-02 end-to-end. Ready for Phase 4 (depth) / roadmap next phase.

## Self-Check: PASSED

- overlay.py, routes_detection.py, routes_preview.py, index.html present
- Commits f1b60b2, 1e9cdf0, 967cd2c, 4a3c3f2, 940dfe6 present
- 165 pytest passed; ruff clean
- DET-03, DET-04 marked complete; ROADMAP Phase 3 Complete
