---
phase: 06-developer-controls-open-vocab
plan: 01
subsystem: api
tags: [pipeline, control-plane, enable-gates, free-space, live-preview, telemetry]

# Dependency graph
requires:
  - phase: 05-free-space-unified-stream
    provides: FreeSpaceLoop, PerceptionStore free-space product, status free_space_* fields
  - phase: 04-monocular-depth
    provides: DepthLoop, depth config routes, depth_fps telemetry
  - phase: 03-fixed-class-detection
    provides: DetectionLoop, detection conf PATCH, det_fps telemetry
provides:
  - Thread-safe PipelineState (stage flags + free-space near/mid cuts)
  - GET/PATCH /api/pipeline/config control plane
  - Loop enable gates on Detection/Depth/FreeSpace (pause without teardown)
  - PerceptionStore clear_* for honest completeness on disable
  - Live Preview stage toggles, free-space cut sliders, stage FPS telemetry
affects:
  - 06-02-open-vocab
  - Live Preview operators
  - future stage control consumers

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Enable Event gate inside loop _run (not stop/start threads)"
    - "Unified pipeline config route for multi-stage cold-path knobs"
    - "clear_* product slots on disable for honest completeness"

key-files:
  created:
    - src/sentry_ai/control/__init__.py
    - src/sentry_ai/control/pipeline_state.py
    - src/sentry_ai/api/routes_pipeline.py
    - tests/test_pipeline_config.py
    - tests/test_loop_enable_gates.py
    - tests/test_free_space_runtime_cuts.py
  modified:
    - src/sentry_ai/models/detection/loop.py
    - src/sentry_ai/models/depth/loop.py
    - src/sentry_ai/spatial/loop.py
    - src/sentry_ai/state/perception_store.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - tests/test_api_preview.py
    - tests/test_cli_serve.py

key-decisions:
  - "Enable flags inside loops skip compute; never stop/start threads for UI toggles"
  - "Unified GET/PATCH /api/pipeline/config for stages + free-space cuts; keep det conf + depth mode routes"
  - "clear_* product slots on disable (not empty error products) for honest completeness"
  - "near_cut > mid_cut validated server-side (422); client warns only"

patterns-established:
  - "PipelineState.snapshot/update under Lock; partial kwargs merge with post-merge validation"
  - "loop.set_enabled → Event + store.clear_* once; is_enabled() for introspection"
  - "FreeSpaceLoop.set_cuts(near_cut=, mid_cut=) under lock; passed to compute_free_space each frame"
  - "Live Preview pipelineFromServer guard mirrors confFromServer for stage/cutoff feedback loops"

requirements-completed: [UI-03, UI-04, UI-05]

# Metrics
duration: 6min
completed: 2026-08-08
---

# Phase 6 Plan 01: Developer Controls Summary

**Thread-safe stage enable/disable + free-space near/mid cutoffs via GET/PATCH `/api/pipeline/config`, loop enable gates that skip compute without teardown, and Live Preview stage toggles with stage FPS telemetry.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-08-08T16:17:06Z
- **Completed:** 2026-08-08T16:23:34Z
- **Tasks:** 3/3
- **Files modified:** 18

## Accomplishments

- `PipelineState` control plane with defaults (all stages on; near=0.72, mid=0.45) and near>mid validation
- DetectionLoop / DepthLoop / FreeSpaceLoop honor `set_enabled` — skip process/compute, clear stage product once, keep thread alive
- FreeSpaceLoop runtime near/mid cuts apply on next `compute_free_space` frame without resetting OccupancySmoother
- Live Preview is a full stage/threshold console: checkboxes, free-space sliders, det/depth/fs FPS + latency

## Task Commits

Each task was committed atomically:

1. **Task 1: PipelineState + loop enable gates + free-space runtime cuts + store clear** - `1354011` (feat)
2. **Task 2: GET/PATCH /api/pipeline/config + create_app/cli wiring + status stage flags** - `b50672c` (feat)
3. **Task 3: Live Preview stage toggles, free-space sliders, and stage FPS telemetry** - `f6ed73a` (feat)

**Plan metadata:** docs commit after task commits (see git log)

## Files Created/Modified

- `src/sentry_ai/control/pipeline_state.py` — thread-safe stage flags + free-space cuts
- `src/sentry_ai/api/routes_pipeline.py` — GET/PATCH `/api/pipeline/config` (extra=forbid, 422 on bad cuts)
- `src/sentry_ai/models/detection/loop.py` — `_enabled` Event gate + clear_detections on disable
- `src/sentry_ai/models/depth/loop.py` — `_enabled` Event gate + clear_depth on disable
- `src/sentry_ai/spatial/loop.py` — enable gate + set_cuts/getters + near/mid to compute
- `src/sentry_ai/state/perception_store.py` — clear_detections / clear_depth / clear_free_space
- `src/sentry_ai/api/app.py` / `deps.py` / `cli.py` — inject pipeline_state + loop refs
- `src/sentry_ai/api/routes_preview.py` / `capture/status.py` — stage flags on `/api/status`
- `src/sentry_ai/ui/static/index.html` — stage toggles, cut sliders, stage FPS
- `tests/test_pipeline_config.py` / `test_loop_enable_gates.py` / `test_free_space_runtime_cuts.py` — coverage

## Decisions Made

- Followed locked plan: enable flags inside loops, unified pipeline config route, keep existing det conf + depth mode routes
- Explicit store `clear_*` (not error products) for stage-off honesty (RESEARCH A4)
- No open-vocab scope creep; no React rewrite; no source switcher UI

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Ruff E501/I001 fixed inline before Task 3 commit.

## User Setup Required

None — no new packages or external services.

## Known Stubs

None — stage control and free-space cuts are fully wired; open-vocab intentionally deferred to 06-02.

## Threat Flags

None beyond plan threat model (T-06-01 through T-06-05 mitigated/accepted as specified).

## Verification

```
uv run pytest tests/test_pipeline_config.py tests/test_loop_enable_gates.py \
  tests/test_free_space_runtime_cuts.py tests/test_api_preview.py \
  tests/test_cli_serve.py tests/test_api_detection.py tests/test_api_depth.py -q
# 83 passed
uv run ruff check ...  # All checks passed
```

## Success Criteria

1. UI-03: Three stage toggles disable compute without serve restart — **met**
2. UI-04: Det conf (existing) + free-space near/mid cuts adjustable live — **met**
3. UI-05: Dashboard shows capture + stage FPS/latency telemetry — **met**
4. Control plane GET/PATCH `/api/pipeline/config` is source of truth — **met**
5. No open-vocab / React / source switcher scope creep — **met**

## Next Phase Readiness

- 06-02 can add open-vocab worker/loop/routes/UI on the same enable-gate and pipeline patterns
- CaptureLoop remains always-on; stage disable never tears down serve

## Self-Check: PASSED

- [x] `src/sentry_ai/control/pipeline_state.py` exists
- [x] `src/sentry_ai/api/routes_pipeline.py` exists
- [x] `tests/test_pipeline_config.py` exists
- [x] Commits `1354011`, `b50672c`, `f6ed73a` present in git log
