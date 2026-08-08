---
phase: 04-monocular-depth
plan: 02
subsystem: depth-api-ui
tags: [depth-colormap, mjpeg, snapshot, status, depth-kind, honesty, serve-lifecycle]

# Dependency graph
requires:
  - phase: 04-monocular-depth
    provides: DepthAnythingWorker / DepthLoop / DepthProduct / PerceptionStore snapshot_depth
  - phase: 03-fixed-class-detection
    provides: snapshot API / MJPEG overlay / serve detection block / StatusSnapshot det fields
  - phase: 02-camera-ingest
    provides: create_app / Live Preview / FrameBus
provides:
  - colorize_depth + blend_depth (OpenCV COLORMAP_TURBO)
  - GET /api/snapshot DepthPayload + multi-product completeness
  - GET/PATCH /api/depth/config depth_mode
  - MJPEG server-side depth blend from PerceptionStore
  - StatusSnapshot depth_* telemetry fields
  - Live Preview depth kind badge + latency
  - sentry serve DepthLoop lifecycle with optional-extra degrade
affects: [phase-05 free-space, phase-06 stage matrix]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - server-side OpenCV TURBO alpha-blend before JPEG encode (parity with detection overlay)
    - snapshot 404 only when neither det nor depth product exists
    - DepthPayload metadata/stats only — never full depth_map on wire
    - relative never unit m; metric_estimated + m when metric modes enabled
    - serve optional-extra twin (depth mirrors detect ImportError degrade)

key-files:
  created:
    - src/sentry_ai/models/depth/colormap.py
    - src/sentry_ai/api/routes_depth.py
    - tests/test_depth_kind_honesty.py
  modified:
    - src/sentry_ai/api/routes_detection.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - README.md
    - tests/test_depth_colormap.py
    - tests/test_api_depth.py
    - tests/test_api_preview.py
    - tests/test_cli_serve.py

key-decisions:
  - "Overlay transport: server-side COLORMAP_TURBO alpha 0.45 before MJPEG encode"
  - "Snapshot never serializes depth_map; metadata + min/max/mean/latency only"
  - "404 only when neither detection nor depth product exists"
  - "Relative UI label: relative (not meters); metric shows kind + m when unit is m"
  - "serve depth_mode defaults to relative; PATCH /api/depth/config for runtime toggle"

patterns-established:
  - "blend_depth then draw_detections order on MJPEG single-store truth"
  - "routes_depth mirrors routes_detection conf config (Literal enum + extra=forbid)"
  - "Status depth fields merged in api_status only — CaptureLoop stays depth-unaware"

requirements-completed: [DEPTH-02, DEPTH-03, DEPTH-04]

# Metrics
duration: 6min
completed: 2026-08-08
---

# Phase 4 Plan 02: Depth API/UI/Serve Wiring Summary

**Snapshot DepthPayload + completeness, server-side TURBO MJPEG blend, honest relative/metric labels, depth latency telemetry, and DepthLoop wired into sentry serve.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-08-08T10:16:29Z
- **Completed:** 2026-08-08T10:22:42Z
- **Tasks:** 3/3
- **Files modified:** 16

## Accomplishments

- Pure OpenCV `colorize_depth` / `blend_depth` (COLORMAP_TURBO, alpha 0.45) with shape/copy/resize tests
- `GET /api/snapshot` multi-product: depth-only or det-only → 200; neither → 404; never full maps on wire
- `GET/PATCH /api/depth/config` with Literal `depth_mode` enum; 503 without worker; 422 on invalid/extra
- MJPEG blends store depth then draws detections; status exposes `depth_kind` / `depth_latency_ms` / fps / error
- Live Preview footer shows `relative (not meters)` + depth ms; serve starts DepthLoop with degrade hint
- Full suite green: 227 passed; ruff clean; honesty tests lock no `depth_m` field and relative unit null

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: failing colormap/snapshot/honesty tests** - `5d131c9` (test)
2. **Task 1 GREEN: colormap + snapshot DepthPayload + depth config** - `41f8898` (feat)
3. **Task 2 RED: MJPEG depth blend + status telemetry tests** - `06ca1b4` (test)
4. **Task 2 GREEN: routes_preview blend + StatusSnapshot depth fields** - `f053db4` (feat)
5. **Task 3: serve DepthLoop + UI labels + README** - `2fa4d57` (feat)

**Plan metadata:** (pending final docs commit)

_Note: TDD tasks used separate RED/GREEN commits for Tasks 1–2._

## Files Created/Modified

- `src/sentry_ai/models/depth/colormap.py` — TURBO colorize + alpha blend helpers
- `src/sentry_ai/api/routes_depth.py` — GET/PATCH `/api/depth/config`
- `src/sentry_ai/api/routes_detection.py` — multi-product snapshot with DepthPayload
- `src/sentry_ai/api/routes_preview.py` — status depth_* + MJPEG blend_depth before boxes
- `src/sentry_ai/api/app.py` / `deps.py` — optional `depth_worker` injection
- `src/sentry_ai/capture/status.py` — StatusSnapshot depth telemetry fields
- `src/sentry_ai/cli.py` — DepthLoop lifecycle + degrade message
- `src/sentry_ai/ui/static/index.html` — depth kind badge + depth latency
- `README.md` — depth install, API table, honesty rules
- `tests/test_depth_colormap.py`, `test_api_depth.py`, `test_depth_kind_honesty.py` — DEPTH-02/03/04
- `tests/test_api_preview.py`, `test_cli_serve.py` — MJPEG/status/serve coverage

## Decisions Made

- Server-side TURBO blend (not client decode) for Option A parity with detection overlays
- Snapshot identity prefers latest `t_capture` product; dual frame ids always in stats
- Relative UI copy: **"relative (not meters)"**; metric shows kind + `(m)` only when `depth_unit === "m"`
- Optional depth_mode select in UI omitted (low-cost PATCH API still available for runtime toggle)
- THIRD_PARTY_MODELS Phase 4 active DAV2 Small row already accurate — no edit required

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Honesty tests used substring match on `depth_m`**
- **Found during:** Task 1 (GREEN verification)
- **Issue:** `assert "depth_m" not in json.dumps(data)` failed because `depth_min` / `depth_mean` contain the substring `depth_m`
- **Fix:** Key-level checks on `data` / `depth` / `stats` dicts + `DepthPayload.model_fields`; removed naive JSON string search
- **Files modified:** `tests/test_depth_kind_honesty.py`, `tests/test_api_depth.py`
- **Verification:** honesty + snapshot tests pass
- **Committed in:** `41f8898` (Task 1 GREEN)

**2. [Rule 1 - Bug] Colormap source assert hit docstring word "transformers"**
- **Found during:** Task 1
- **Issue:** docstring said "no transformers" which tripped `assert "transformers" not in source`
- **Fix:** reword docstring; assert on real import forms (`from transformers` / `import torch`)
- **Files modified:** `src/sentry_ai/models/depth/colormap.py`, `tests/test_depth_colormap.py`
- **Verification:** colormap tests pass
- **Committed in:** `41f8898`

---

**Total deviations:** 2 auto-fixed (Rule 1 × 2)
**Impact on plan:** Test correctness only; no architectural scope change.

## Issues Encountered

None beyond the honesty/substring false positives above.

## User Setup Required

None for CI/unit path. Optional manual (not a CI gate):

```bash
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --source synthetic
# Open http://127.0.0.1:8000/ — expect TURBO blend + Depth: relative (not meters) + Depth ms
```

First depth run downloads HF Small weights into `SENTRY_MODEL_CACHE/hf` (or `~/.cache/sentry-ai/hf`).

## Known Stubs

None. Depth map stays in-process by design (not a stub); wire path intentionally metadata-only.

## Threat Flags

None new beyond plan threat model. Mitigations applied:

| Threat | Mitigation delivered |
|--------|----------------------|
| T-04-01 | DepthPayload validators + UI "not meters" + honesty tests |
| T-04-02 | Literal depth_mode + extra=forbid + 503 without worker |
| T-04-03 | No depth_map / depth_m on snapshot; size sanity tests |
| T-04-04 | No inference in handlers; empty depth skips blend |
| T-04-05 | Single PerceptionStore for MJPEG, snapshot, status |

## Verification

```text
uv run pytest -q  → 227 passed
uv run ruff check src tests  → All checks passed
```

Phase 4 success criteria (mocked path):

1. Snapshot/stream includes depth with explicit kind (DEPTH-02) ✓
2. MJPEG encodes TURBO blend when product present (DEPTH-03) ✓
3. Relative never meters; metric labeled metric_estimated + m (DEPTH-04) ✓
4. Depth latency in status/UI ✓
5. serve wires DepthLoop with optional-extra degrade ✓

## Next Phase Ready

Phase 4 monocular depth complete. Next roadmap phase: free-space / obstacle signals (Phase 5) consuming in-process depth maps without re-running depth inference in handlers.

## Self-Check: PASSED

- All key artifacts present (colormap, routes_depth, snapshot, preview, status, cli, UI, tests, README)
- Commits present: `5d131c9`, `41f8898`, `06ca1b4`, `f053db4`, `2fa4d57`
- Full suite 227 passed; ruff clean
- No yolo26n.pt committed
