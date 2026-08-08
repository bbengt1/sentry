---
phase: 05-free-space-unified-stream
plan: 03
subsystem: api
tags: [fastapi, websocket, free-space, perception-frame, mjpeg, stale, api-05]

# Dependency graph
requires:
  - phase: 05-free-space-unified-stream (05-01)
    provides: FreeSpaceLoop, FreeSpaceProduct, draw_free_space
  - phase: 05-free-space-unified-stream (05-02)
    provides: assemble_perception_frame, FreeSpacePayload wire shape, /api/snapshot alias path
provides:
  - "GET /v1/snapshot + WS /v1/stream JSON PerceptionFrame (~10 Hz keep-latest)"
  - "/api/snapshot alias parity with /v1 via same assembler"
  - "MJPEG free-space overlay (depth → free-space → boxes) from store only"
  - "Status free_space_* + obstacle_count + age/stale for Live Preview"
  - "FreeSpaceLoop always-on in sentry serve lifecycle"
  - "API-05 denylist tests on /v1 snapshot + stream envelopes"
  - "README /v1 contract + perception-only boundary docs"
affects: [phase-6-dashboard-polish, robot-clients, verification]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Versioned /v1 routes alongside /api back-compat aliases"
    - "WebSocket keep-latest ~10 Hz with shutdown_flag interruptible sleep"
    - "MJPEG draw order: blend_depth → draw_free_space → draw_detections"
    - "Serve always starts FreeSpaceLoop (CPU Spatial Post; no ML ImportError gate)"
    - "UI STALE/incomplete badges from /api/status free_space_stale ages"

key-files:
  created:
    - src/sentry_ai/api/routes_v1.py
    - tests/test_api_v1.py
    - tests/test_api_perception_only.py
  modified:
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/routes_detection.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - README.md
    - tests/test_api_preview.py
    - tests/test_cli_serve.py
    - tests/test_assemble_perception_frame.py

key-decisions:
  - "WS /v1/stream uses fixed 0.1s sleep keep-latest; no per-client queue"
  - "FreeSpaceLoop always constructed after store creation (no depth-extra gate)"
  - "Status free_space_age_ms/stale computed in routes_preview from product t_capture + DEFAULT_TTL_MS"
  - "README documents perception-only boundary without banned product phrases"

patterns-established:
  - "routes_v1: REST + WS share assemble_perception_frame only"
  - "serve start order capture→det→depth→free_space; stop reverse"
  - "Language denylist tests on index.html + README for T-05-06"

requirements-completed: [API-01, API-02, API-05, SPACE-03, SPACE-04, UI-02, UI-06]

# Metrics
duration: 4min
completed: 2026-08-08
---

# Phase 5 Plan 03: Free-Space Overlay & Unified /v1 Stream Summary

**Shipped versioned perception API (`GET /v1/snapshot`, `WS /v1/stream` ~10 Hz keep-latest), MJPEG free-space overlay from the same PerceptionStore, FreeSpaceLoop always-on in serve, and STALE/incomplete Live Preview honesty with API-05 denylist coverage.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-08T12:20:56Z
- **Completed:** 2026-08-08T12:25:22Z
- **Tasks:** 3/3
- **Files modified:** 13

## Accomplishments

- Robots can consume merged `PerceptionFrame` via REST + WebSocket at `/v1` with ages/stale/completeness stats
- Live Preview draws free-space from store products (UI-06 parity) and surfaces obstacles/age + STALE badges
- `sentry serve` always runs FreeSpaceLoop (CPU Spatial Post) after depth; no new ML packages
- API-05 motor/safety denylist holds on `/v1` snapshot and stream wire dumps

## Task Commits

Each task was committed atomically:

1. **Task 1: /v1 snapshot + WebSocket stream + app wiring + API-05 tests** - `407c1c8` (feat)
2. **Task 2: MJPEG free-space overlay + status telemetry + FreeSpaceLoop serve lifecycle** - `6a80172` (feat)
3. **Task 3: Live Preview UI footer/STALE + README /v1 docs** - `877ee3b` (feat)

**Plan metadata:** (pending final docs commit)

## Files Created/Modified

- `src/sentry_ai/api/routes_v1.py` — GET `/v1/snapshot` + WS `/v1/stream` via assembler
- `src/sentry_ai/api/app.py` — include `v1_router`
- `src/sentry_ai/api/routes_detection.py` — `/api/snapshot` documented as `/v1` alias
- `src/sentry_ai/api/routes_preview.py` — free-space draw order + status free_space_* fields
- `src/sentry_ai/capture/status.py` — optional free-space StatusSnapshot fields
- `src/sentry_ai/cli.py` — FreeSpaceLoop start/stop lifecycle + banner
- `src/sentry_ai/ui/static/index.html` — free-space footer metrics + STALE/incomplete badges
- `README.md` — `/v1` contract, ordinal free-space, perception-only boundary
- `tests/test_api_v1.py` — snapshot/stream/alias parity coverage
- `tests/test_api_perception_only.py` — API-05 denylist on wire envelopes
- `tests/test_api_preview.py` — draw order, status free-space, language denylist
- `tests/test_cli_serve.py` — FreeSpaceLoop lifecycle source asserts
- `tests/test_assemble_perception_frame.py` — ruff E501 wrap (blocking green)

## Decisions Made

- Keep-latest WS at fixed ~10 Hz with interruptible sleep honoring `shutdown_flag` (same spirit as MJPEG)
- FreeSpaceLoop always-on regardless of depth extra; idles until depth product appears
- Status ages/stale derived in preview routes using `DEFAULT_TTL_MS["free_space"]` so UI can badge without calling assembler
- README avoids banned “safe to drive” phrases while still documenting the perception-only boundary

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Ruff F401 unused `time` import in new test_api_v1.py**
- **Found during:** Task 3 verification
- **Issue:** Left over from draft seed helpers
- **Fix:** Removed unused import
- **Files modified:** `tests/test_api_v1.py`
- **Committed in:** `877ee3b`

**2. [Rule 3 - Blocking] Pre-existing ruff E501 in assemble tests blocked green gate**
- **Found during:** Task 3 verification (`uv run ruff check src tests`)
- **Issue:** Long forbidden_substrings tuple line from 05-02
- **Fix:** Wrapped tuple to multi-line
- **Files modified:** `tests/test_assemble_perception_frame.py`
- **Committed in:** `877ee3b`

**3. [Rule 1 - Bug] README language denylist self-conflict**
- **Found during:** Task 3
- **Issue:** README documented API-05 by listing the banned phrase “safe to drive”, which failed the denylist test
- **Fix:** Rephrased boundary section to “autonomy-clearance fields” without banned product copy
- **Files modified:** `README.md`
- **Committed in:** `877ee3b`

---

**Total deviations:** 3 auto-fixed (1× Rule 1, 2× Rule 3)
**Impact on plan:** No scope creep; verification gate and honesty language kept green.

## Issues Encountered

None beyond the denylist wording clash noted above.

## User Setup Required

None — no new packages or secrets. Free-space needs depth product (optional `uv sync --extra depth`) but FreeSpaceLoop starts without it.

## Known Stubs

None — `/v1` routes assemble real store products; UI polls live `/api/status`; FreeSpaceLoop is fully wired.

## Threat Flags

None beyond plan register. Mitigations applied:

| Threat | Mitigation delivered |
|--------|----------------------|
| T-05-01 units honesty | Assembler ordinal units; README ordinal docs |
| T-05-02 stale after stall | ages + free_space_stale on status; UI STALE badge |
| T-05-03 motor elevation | extra=forbid + test_api_perception_only denylist |
| T-05-05 WS backpressure | keep-latest; fixed 0.1s sleep; no queue |
| T-05-06 safe-to-drive UI | HTML/README string denylist tests |

## Verification Results

```text
uv run pytest tests/test_api_v1.py tests/test_api_perception_only.py \
  tests/test_api_preview.py tests/test_cli_serve.py \
  tests/test_assemble_perception_frame.py tests/test_free_space*.py -q
# 70 passed

uv run ruff check src tests
# All checks passed

uv run pytest -q
# 311 passed
```

## Phase 5 Success Criteria

| Criterion | Status |
|-----------|--------|
| Free-space on dashboard (MJPEG + footer) | Met |
| WS `/v1/stream` PerceptionFrame | Met |
| REST snapshot merged (`/v1` + `/api` alias) | Met |
| Stale/incomplete visible | Met |
| UI = API store | Met (single PerceptionStore) |
| Stream metadata FPS/latency/drops | Met (assembler stats + status free_space_fps) |

## Next Phase Readiness

Phase 5 complete from execution perspective. Ready for `/gsd:verify-work` and Phase 6 planning (dashboard polish / multi-stage controls if scoped).

## Self-Check: PASSED

- Created files exist (routes_v1, tests, SUMMARY)
- Commits found: 407c1c8, 6a80172, 877ee3b
- Full suite 311 passed; ruff clean
