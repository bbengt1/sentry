---
phase: 05-free-space-unified-stream
verified: 2026-08-08T12:30:21Z
status: passed
score: 6/6 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 5: Free-Space & Unified Stream Verification Report

**Phase Goal:** Deliver the core product thesis — free-space/obstacles from depth plus a unified, versioned perception stream robots can consume.
**Verified:** 2026-08-08T12:30:21Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | Free-space / obstacle regions are derived from depth and shown on the dashboard | ✓ VERIFIED | `compute_free_space` near-field bands on depth maps (`spatial/free_space.py`); `FreeSpaceLoop` polls `snapshot_depth` → `set_free_space`; MJPEG draws via `draw_free_space` after depth blend (`routes_preview.py` L190–211); UI footer shows free-space / obstacles / age (`index.html`) |
| 2 | WebSocket `/v1/stream` delivers merged `PerceptionFrame` with completeness flags | ✓ VERIFIED | `routes_v1.v1_stream` accepts WS, calls `assemble_perception_frame`, `send_json(frame.model_dump())` at `STREAM_PERIOD_S=0.1`; completeness set in assembler; `test_v1_stream_yields_json_perception_frame` |
| 3 | REST snapshot returns the latest merged frame | ✓ VERIFIED | `GET /v1/snapshot` + alias `GET /api/snapshot` both call only `assemble_perception_frame(store)` and return `model_dump()`; 404 when all products absent; alias parity test |
| 4 | Stale or incomplete data is visible; no “safe to proceed” claims | ✓ VERIFIED | Assembler sets `*_age_ms`, `*_stale`, `products_stale` independent of completeness; UI STALE/incomplete badges; schema `extra=forbid`; denylist tests for `safe_to_drive`/`go_nogo`/motor fields; no such fields in source models |
| 5 | UI overlays match API content (single perception state store) | ✓ VERIFIED | Single `PerceptionStore`; FreeSpaceLoop sole Spatial Post producer; MJPEG/status/API all `snapshot_*` only; single assembler for REST/WS; no free-space recompute in handlers |
| 6 | Stream metadata includes FPS, stage latency, and drops | ✓ VERIFIED | Assembler merges `det/depth/free_space` latency + ages + `*_fps` + `*_frames_dropped` from `metrics_snapshot`; free-space metrics on store; status endpoint exposes free_space latency/fps/age |

**Score:** 6/6 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/sentry_ai/spatial/free_space.py` | Near-field free-space algorithm | ✓ VERIFIED | 306 lines; `compute_free_space`, `FreeSpaceResult`, ordinal units, no `distance_m` |
| `src/sentry_ai/spatial/smoothing.py` | Morphology + EMA smoother | ✓ VERIFIED | 101 lines; open 3×3, close 5×5, EMA α=0.35, re-threshold 0.5 |
| `src/sentry_ai/spatial/overlay.py` | `draw_free_space` pure draw | ✓ VERIFIED | 107 lines; free/occupied tint + obstacle boxes; copy-out |
| `src/sentry_ai/spatial/loop.py` | `FreeSpaceLoop` daemon | ✓ VERIFIED | 163 lines; polls depth, skip same `frame_id`, publish product, drop accounting |
| `src/sentry_ai/state/perception_store.py` | FreeSpaceProduct triple store | ✓ VERIFIED | `set_free_space` / `snapshot_free_space` / free_space metrics under same lock |
| `src/sentry_ai/schemas/perception.py` | FreeSpacePayload + ObstacleCue | ✓ VERIFIED | Expanded wire shape; `extra=forbid`; no motor/`distance_m` |
| `src/sentry_ai/api/assemble.py` | Single merge path | ✓ VERIFIED | 234 lines; det+depth+free_space; completeness + TTL/stale + stats |
| `src/sentry_ai/api/routes_v1.py` | `/v1/snapshot` + `/v1/stream` | ✓ VERIFIED | 93 lines; assembler-only handlers; ~10 Hz keep-latest WS |
| `src/sentry_ai/api/routes_preview.py` | MJPEG free-space + status | ✓ VERIFIED | Draw order depth→free-space→boxes; free_space status fields |
| `src/sentry_ai/api/routes_detection.py` | `/api/snapshot` alias | ✓ VERIFIED | Thin assembler alias; no dual merge |
| `src/sentry_ai/api/app.py` | Mount v1 router | ✓ VERIFIED | `include_router(v1_router)` |
| `src/sentry_ai/cli.py` | FreeSpaceLoop lifecycle | ✓ VERIFIED | Always-on when store exists; start after depth; stop reverse |
| `src/sentry_ai/ui/static/index.html` | Footer + STALE badges | ✓ VERIFIED | free-space/obstacles/age metrics; STALE/incomplete; no safe-to-drive copy |
| `src/sentry_ai/capture/status.py` | Status free_space fields | ✓ VERIFIED | Optional free_space_* + obstacle_count fields |
| `README.md` | `/v1` contract docs | ✓ VERIFIED | Snapshot/stream/stale consumer notes + wire shape |
| Phase 5 tests | SPACE/API coverage | ✓ VERIFIED | free_space_*, assemble, api_v1, perception_only, preview, cli_serve |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `spatial/loop.py` | `PerceptionStore.snapshot_depth` | FreeSpaceLoop poll | ✓ WIRED | L87–95 skip missing/same frame |
| `spatial/loop.py` | `set_free_space` | publish product | ✓ WIRED | L112–140 after `compute_free_space` |
| `spatial/loop.py` | `compute_free_space` + `OccupancySmoother` | Spatial Post sole owner | ✓ WIRED | L55, L104–108 |
| `api/assemble.py` | triple `snapshot*` | merge read | ✓ WIRED | L93–95 |
| `api/assemble.py` | `FreeSpacePayload` | obstacles+bands wire | ✓ WIRED | L203–217; no masks |
| `routes_v1.py` | `assemble_perception_frame` | snapshot + stream | ✓ WIRED | L49, L87 |
| `routes_detection.py` | `assemble_perception_frame` | `/api/snapshot` | ✓ WIRED | L66 |
| `routes_preview.py` | `draw_free_space` + `snapshot_free_space` | MJPEG + status | ✓ WIRED | L118–128, L201–208 |
| `cli.py` | `FreeSpaceLoop` | serve start/stop | ✓ WIRED | L382–420 start; L430 stop first |
| `index.html` | `/api/status` free_space fields | footer poll | ✓ WIRED | obstacle_count / free_space_* / STALE |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| FreeSpaceLoop | FreeSpaceProduct | DepthProduct.depth_map → compute_free_space | Yes (synthetic + live depth) | ✓ FLOWING |
| assemble_perception_frame | PerceptionFrame | store snapshot×3 + metrics | Yes (products or None→404) | ✓ FLOWING |
| routes_v1 snapshot/stream | JSON body | assembler model_dump | Yes | ✓ FLOWING |
| MJPEG overlay | free/occupied masks | store free_space product | Yes (in-process masks) | ✓ FLOWING |
| UI footer | obstacle_count, ages, stale | `/api/status` from store | Yes | ✓ FLOWING |

**Single assembler contract:** Only `src/sentry_ai/api/assemble.py` implements merge. Call sites: `routes_v1` (GET + WS) and `routes_detection` (`/api/snapshot`). No dual merge logic.

**Honesty constraints:**
- Free-space path: `method="near_field_bands"`, `units="ordinal"`; no `distance_m` on result/product/wire ObstacleCue
- No motor/velocity/path_plan/safe_to_drive/go_nogo fields on schemas or API dumps (tests + `extra=forbid`)

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full test suite | `uv run pytest -q` | 311 passed | ✓ PASS |
| Ruff | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Health | `uv run sentry health` | status: ok | ✓ PASS |
| Smoke | `uv run sentry smoke` | smoke ok (3 frames) | ✓ PASS |
| Synthetic free-space | `compute_free_space` near blob | 1 obstacle, ordinal, no distance_m | ✓ PASS |
| Phase 5 API tests | pytest api_v1 + assemble + perception_only | 20 collected / all pass | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No phase-declared or conventional probes | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| SPACE-01 | 05-01 | Free-space/obstacles from depth | ✓ SATISFIED | `compute_free_space` + FreeSpaceLoop + tests |
| SPACE-02 | 05-01/02 | Machine-readable obstacle cues | ✓ SATISFIED | ObstacleCue list + bands on FreeSpacePayload |
| SPACE-03 | 05-03 | Overlay on dashboard | ✓ SATISFIED | draw_free_space in MJPEG + footer |
| SPACE-04 | 05-02/03 | Stale/incomplete; no safe-to-proceed | ✓ SATISFIED | TTL stats + STALE UI + denylist |
| API-01 | 05-03 | WS `/v1/stream` PerceptionFrame | ✓ SATISFIED | routes_v1 websocket |
| API-02 | 05-03 | REST snapshot PerceptionFrame | ✓ SATISFIED | `/v1/snapshot` + `/api/snapshot` |
| API-03 | 05-02 | Completeness flags | ✓ SATISFIED | Completeness det/depth/free_space |
| API-04 | 05-02 | FPS / latency / drops metadata | ✓ SATISFIED | stats from metrics_snapshot |
| API-05 | 05-02/03 | Perception-only (no motor) | ✓ SATISFIED | schema forbid + dump denylist tests |
| UI-02 | 05-03 | Overlays include free-space | ✓ SATISFIED | depth→free-space→boxes order |
| UI-06 | 05-03 | UI/API same store | ✓ SATISFIED | single store + single assembler |

No orphaned Phase 5 requirements. UI-03/04/05 correctly mapped to Phase 6 (not this phase).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/XXX in phase-touched source | — | — |
| — | — | No safe-to-drive / go_nogo API fields | — | — |
| `assemble.py` | 214–216 | FreeSpacePayload width/height/roi always `None` | ℹ️ Info | Optional wire fields unused; obstacles+bands still complete SPACE-02 |

Debt-marker gate: clean. “not available” strings are HTTP 503 details, not stubs.

### Human Verification Required

None required for goal achievement. Overlay correctness, assembler parity, stream contract, and stale honesty are covered by automated tests and code wiring. Live visual tuning is optional polish, not a phase blocker.

### Gaps Summary

No gaps. All six roadmap success criteria are observable in code with Level 1–4 evidence. Phase 5 product thesis (Spatial Post free-space + unified `/v1` PerceptionFrame stream + UI/API parity + stale honesty + perception-only boundary) is achieved.

---

_Verified: 2026-08-08T12:30:21Z_
_Verifier: Claude (gsd-verifier)_
