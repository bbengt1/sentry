---
phase: 05-free-space-unified-stream
plan: 02
subsystem: api
tags: [free-space, perception-frame, assemble, ttl, stale, completeness, pydantic, fastapi]

# Dependency graph
requires:
  - phase: 05-free-space-unified-stream/01
    provides: FreeSpaceProduct + set_free_space / snapshot_free_space + free_space store metrics
  - phase: 04-monocular-depth
    provides: DepthProduct + multi-product /api/snapshot merge baseline
provides:
  - Expanded FreeSpacePayload + ObstacleCue wire schemas (no masks, no distance_m)
  - assemble_perception_frame single merge path (completeness + TTL/stale + stats)
  - GET /api/snapshot thin assembler client (alias-ready for /v1)
affects:
  - 05-03 (/v1 REST/WS, MJPEG parity, API-05 envelope tests)
  - robot consumers of PerceptionFrame free_space + stale flags

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Single pure assemble_perception_frame for all REST/WS consumers"
    - "completeness = presence + error is None; stale = age_ms > TTL (independent)"
    - "Wire free_space = obstacles + bands + counts; masks/depth_map stay in-process"

key-files:
  created:
    - src/sentry_ai/api/assemble.py
    - tests/test_assemble_perception_frame.py
  modified:
    - src/sentry_ai/schemas/perception.py
    - src/sentry_ai/schemas/__init__.py
    - src/sentry_ai/api/routes_detection.py
    - tests/test_schemas_perception.py
    - tests/test_api_detection.py

key-decisions:
  - "FreeSpacePayload expanded with ObstacleCue list + bands; units default ordinal; no distance_m"
  - "DEFAULT_TTL_MS: detections 500 / depth 750 / free_space 750; TtlConfig overrideable"
  - "Primary identity = max t_capture among present products"
  - "/api/snapshot is thin alias to assembler only — no dual merge"

patterns-established:
  - "Assembler returns None when all products absent; handlers map to 404"
  - "Stale flags live in stats (det_stale/depth_stale/free_space_stale/products_stale)"
  - "API-05 denylist includes safe_to_drive, go_nogo, cmd_vel, twist, path_plan"

requirements-completed: [SPACE-02, SPACE-04, API-03, API-04, API-05]

# Metrics
duration: 4min
completed: 2026-08-08
---

# Phase 5 Plan 02: Free-Space Wire + Unified Assembler Summary

**Expanded FreeSpacePayload with ObstacleCue wire shape, single assemble_perception_frame merge (completeness + TTL/stale ages/stats), and /api/snapshot refactored to that assembler only.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-08T12:12:12Z
- **Completed:** 2026-08-08T12:16:22Z
- **Tasks:** 3/3
- **Files modified:** 7

## Accomplishments

- Expanded `FreeSpacePayload` / `ObstacleCue` with method, depth_kind, units=ordinal, obstacles, bands — no full masks or distance_m on the wire
- Implemented pure `assemble_perception_frame` with completeness (availability) separate from TTL stale flags (freshness); DEFAULT_TTL_MS 500/750/750
- Refactored GET `/api/snapshot` to call assembler only; free_space appears when FreeSpaceProduct present; 404 only when all three products absent
- API-05 denylist extended (safe_to_drive, go_nogo, cmd_vel, twist); full suite 295 passed + ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Expand FreeSpacePayload + ObstacleCue schemas**
   - `05477eb` test(05-02): add failing tests for FreeSpacePayload + ObstacleCue
   - `5c995b3` feat(05-02): expand FreeSpacePayload and ObstacleCue wire schemas
2. **Task 2: assemble_perception_frame + TTL/stale/completeness/stats**
   - `20ce566` test(05-02): add failing tests for assemble_perception_frame
   - `816d8b8` feat(05-02): implement assemble_perception_frame with TTL/stale
3. **Task 3: Refactor GET /api/snapshot to assembler**
   - `e91b651` feat(05-02): refactor /api/snapshot to assemble_perception_frame

**Plan metadata:** (pending final docs commit)

_Note: Tasks 1–2 used TDD RED→GREEN commits; Task 3 combined tests + refactor in one feat commit._

## Files Created/Modified

- `src/sentry_ai/schemas/perception.py` — ObstacleCue + expanded FreeSpacePayload (extra=forbid)
- `src/sentry_ai/schemas/__init__.py` — export ObstacleCue
- `src/sentry_ai/api/assemble.py` — assemble_perception_frame, TtlConfig, DEFAULT_TTL_MS
- `src/sentry_ai/api/routes_detection.py` — thin /api/snapshot → assembler
- `tests/test_schemas_perception.py` — SPACE-02 / API-05 schema coverage
- `tests/test_assemble_perception_frame.py` — merge, stale, stats, no masks
- `tests/test_api_detection.py` — free_space on snapshot, assembler-only source check

## Decisions Made

- Wire free-space is obstacle list + bands + counts only (user-locked; masks stay in-process)
- Completeness = product present and error is None; stale is age vs TTL in stats only
- Primary frame identity is max t_capture among present products (including free_space)
- `/api/snapshot` kept as working alias via assembler; `/v1` deferred to 05-03
- units always `"ordinal"` for free-space payload (including metric_estimated depth kinds)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- **05-03 ready:** attach GET `/v1/snapshot` + WS `/v1/stream` to `assemble_perception_frame` only
- FreeSpacePayload wire shape and TTL/stale stats are stable for UI footer / STALE badge
- MJPEG overlay continues to read FreeSpaceProduct masks in-process (unchanged by this plan)
- No dual merge remains in routes_detection — parity foundation for UI-06

## TDD Gate Compliance

- Task 1: RED `05477eb` → GREEN `5c995b3` ✅
- Task 2: RED `20ce566` → GREEN `816d8b8` ✅
- Task 3: combined feat commit with tests (refactor-focused) — no separate RED commit

## Verification

```text
uv run pytest tests/test_schemas_perception.py tests/test_assemble_perception_frame.py tests/test_api_detection.py -q
# + full suite: 295 passed
uv run ruff check src/sentry_ai/schemas src/sentry_ai/api/assemble.py src/sentry_ai/api/routes_detection.py
# All checks passed!
```

## Self-Check: PASSED

- All key files present (schemas, assemble.py, routes_detection, three test modules, SUMMARY)
- All task commits present: 05477eb, 5c995b3, 20ce566, 816d8b8, e91b651
- No intentional stubs blocking plan goals
- `/api/snapshot` uses assemble_perception_frame only

---
*Phase: 05-free-space-unified-stream*
*Completed: 2026-08-08*
