---
phase: 05-free-space-unified-stream
plan: 01
subsystem: spatial
tags: [free-space, occupancy, morphology, ema, perception-store, opencv, numpy]

# Dependency graph
requires:
  - phase: 04-monocular-depth
    provides: DepthProduct with in-process depth_map, PerceptionStore dual half, DepthLoop lifecycle twin
provides:
  - Near-field percentile band free-space pure algorithm (SPACE-01)
  - Morphology + EMA OccupancySmoother
  - FreeSpaceProduct triple-product store half
  - FreeSpaceLoop Spatial Post daemon
  - draw_free_space pure overlay helper (SPACE-03 foundation)
affects: [05-02 wire payloads / assemble, 05-03 MJPEG + UI stream]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - near-field percentile bands (image-space ordinal occupancy)
    - FreeSpaceLoop polls snapshot_depth only (no FrameBus)
    - in-process free/occupied masks; obstacles+bands machine-readable

key-files:
  created:
    - src/sentry_ai/spatial/__init__.py
    - src/sentry_ai/spatial/free_space.py
    - src/sentry_ai/spatial/smoothing.py
    - src/sentry_ai/spatial/loop.py
    - src/sentry_ai/spatial/overlay.py
    - tests/test_free_space_bands.py
    - tests/test_free_space_smoothing.py
    - tests/test_free_space_loop.py
    - tests/test_free_space_overlay.py
  modified:
    - src/sentry_ai/state/perception_store.py
    - tests/test_perception_store.py

key-decisions:
  - "units always ordinal for v1 free-space even when depth_kind is metric_estimated"
  - "OccupancySmoother state owned by FreeSpaceLoop, not PerceptionStore"
  - "compute_free_space accepts optional smoother for temporal path; morphology alone when pure"

patterns-established:
  - "Spatial Post package: pure free_space + loop-owned smoothing + store product"
  - "FreeSpaceLoop structural twin of DepthLoop with depth-product poll instead of FrameBus"
  - "draw_free_space copy-in/copy-out tint pattern mirrors blend_depth / draw_detections"

requirements-completed: [SPACE-01, SPACE-02]

# Metrics
duration: 12min
completed: 2026-08-08
---

# Phase 5 Plan 01: Free-Space Spatial Post Core Summary

**Near-field percentile-band free-space from synthetic monocular depth with morphology+EMA smoothing, FreeSpaceProduct on PerceptionStore, FreeSpaceLoop daemon, and pure draw_free_space overlay helper — CI-safe without DAV2/HF.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-08T12:05:48Z
- **Completed:** 2026-08-08T12:18:00Z
- **Tasks:** 3/3
- **Files modified:** 11

## Accomplishments

- Pure `compute_free_space` produces ordinal near-field occupancy, ROI-limited free mask, obstacle cues via connected components, and band fractions without inventing meters
- Temporal `OccupancySmoother` (open 3×3, close 5×5, EMA α=0.35) kills single-pixel salt and stabilizes static blobs
- `FreeSpaceLoop` is sole Spatial Post owner: polls `snapshot_depth()`, skips same/missing depth, writes `FreeSpaceProduct` keep-latest with drop metrics
- `draw_free_space` tints free (cool green) / occupied (amber-red) and optional bboxes with no safety language

## Task Commits

Each task was committed atomically:

1. **Task 1: Near-field free-space algorithm + temporal smoothing (pure)** - `2da7f47` (feat)
2. **Task 2: FreeSpaceProduct store half + FreeSpaceLoop** - `391bfca` (feat)
3. **Task 3: draw_free_space pure overlay helper** - `b960bfc` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified

- `src/sentry_ai/spatial/__init__.py` - Lazy package exports for Spatial Post
- `src/sentry_ai/spatial/free_space.py` - `compute_free_space`, `FreeSpaceResult`, `ObstacleCue`, polarity + ROI bands
- `src/sentry_ai/spatial/smoothing.py` - `morphology_clean`, `smooth_occupancy`, `OccupancySmoother`
- `src/sentry_ai/spatial/loop.py` - `FreeSpaceLoop` daemon Spatial Post owner
- `src/sentry_ai/spatial/overlay.py` - `draw_free_space` pure OpenCV helper
- `src/sentry_ai/state/perception_store.py` - `FreeSpaceProduct`, set/snapshot/metrics free-space half
- `tests/test_free_space_bands.py` - SPACE-01 pure algorithm coverage
- `tests/test_free_space_smoothing.py` - Morphology + EMA coverage
- `tests/test_free_space_loop.py` - FreeSpaceLoop synthetic DepthProduct coverage
- `tests/test_free_space_overlay.py` - Overlay copy/tint/boundary coverage
- `tests/test_perception_store.py` - Free-space store isolation + triple coexistence

## Decisions Made

- **Ordinal honesty locked:** `units="ordinal"` always for v1 free-space (including `metric_estimated` depth); no `distance_m` field on results or obstacle cues
- **Smoother ownership:** EMA float state lives on `FreeSpaceLoop._smoother`, never on the store
- **Loop isolation:** FreeSpaceLoop only needs `PerceptionStore` — no FrameBus, no ModelWorker, no ML imports
- **Wire masks deferred:** Full free/occupied masks stay in-process; obstacles + bands are machine-readable for 05-02

## Deviations from Plan

None - plan executed exactly as written.

Minor API detail: `smooth_occupancy` returns the binary mask (public one-shot API); stateful multi-frame path uses `OccupancySmoother` / internal `_smooth_with_state`. Matches plan intent without changing behavior contracts.

## Issues Encountered

None.

## User Setup Required

None — no new packages, no external services. Free-space path is NumPy/OpenCV only (already core deps).

## Known Stubs

None — algorithm, store, loop, and overlay are fully wired for synthetic depth. MJPEG/API wiring intentionally deferred to 05-02/05-03.

## Threat Flags

None beyond plan register. Mitigations applied:

| Threat | Mitigation shipped |
|--------|-------------------|
| T-05-01 units honesty | `units=ordinal`, no `distance_m`, tests lock |
| T-05-03 loop exceptions | try/except writes error product; thread stays alive |
| T-05-04 mask disclosure | masks in-process only; no serialization this plan |
| T-05-05 DoS | keep-latest same-frame skip; 5 ms Event.wait |

## Verification Results

```
uv run pytest tests/test_free_space_bands.py tests/test_free_space_smoothing.py \
  tests/test_free_space_overlay.py tests/test_free_space_loop.py \
  tests/test_perception_store.py -q
→ 50 passed

uv run ruff check src/sentry_ai/spatial src/sentry_ai/state/perception_store.py \
  tests/test_free_space*.py tests/test_perception_store.py
→ All checks passed
```

## Success Criteria

1. ✅ Synthetic depth → FreeSpaceProduct with obstacles + masks without ML weights
2. ✅ FreeSpaceLoop is sole Spatial Post owner (separate thread; not DepthLoop)
3. ✅ Temporal smoothing reduces single-frame speckles (morphology/EMA tests)
4. ✅ Ordinal honesty: no distance_m / meter claims from relative depth free-space
5. ✅ Existing detection + depth store tests remain green

## Next Phase Ready

- **05-02:** Wire FreeSpacePayload / assemble_perception_frame / obstacle list on REST
- **05-03:** MJPEG `draw_free_space` wiring + UI footer free-space metrics

## Self-Check: PASSED

- All 11 key source/test files present
- Commits `2da7f47`, `391bfca`, `b960bfc` present in git log
- SUMMARY written at `.planning/phases/05-free-space-unified-stream/05-01-SUMMARY.md`
