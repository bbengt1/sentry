# Phase 5 Plan Check — Free-Space & Unified Stream

**Checked:** 2026-08-08  
**Plans verified:** 05-01, 05-02, 05-03  
**Status:** PLAN CHECK PASSED  
**Gate type:** Revision Gate (pre-execution)

---

## Verdict

**PLAN CHECK PASSED**

Plans will achieve the Phase 5 goal and all eleven roadmap requirements (SPACE-01..04, API-01..05, UI-02, UI-06) if executed as written. No blockers. Warnings below are hygiene / soft-wiring language only and do not prevent execution.

---

## Phase Goal (source of truth)

> Deliver the core product thesis — free-space/obstacles from depth plus a unified, versioned perception stream robots can consume.

**ROADMAP Success Criteria:**

1. Free-space / obstacle regions are derived from depth and shown on the dashboard  
2. WebSocket `/v1/stream` delivers merged `PerceptionFrame` with completeness flags  
3. REST snapshot returns the latest merged frame  
4. Stale or incomplete data is visible to consumers (TTL / completeness); no “safe to proceed” claims  
5. UI overlays match API content (single perception state store)  
6. Stream metadata includes FPS, stage latency, and drops  

**Requirements:** SPACE-01, SPACE-02, SPACE-03, SPACE-04, API-01, API-02, API-03, API-04, API-05, UI-02, UI-06  

---

## Coverage Summary

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| SPACE-01 Free-space from depth (not SLAM) | 05-01 | T1 near-field bands + smoothing; T2 FreeSpaceLoop | Covered |
| SPACE-02 Machine-readable obstacle cues on stream | 05-01 T2 product fields; 05-02 T1–T3 wire payload + snapshot | Covered |
| SPACE-03 Free-space overlay on dashboard | 05-01 T3 `draw_free_space`; 05-03 T2 MJPEG wire | Covered |
| SPACE-04 Stale/incomplete; no “safe to proceed” | 05-02 T2 TTL/stale; 05-03 T1 denylist + T3 STALE UI | Covered |
| API-01 WS `/v1/stream` merged PerceptionFrame | 05-03 | T1 WebSocket ~10 Hz keep-latest | Covered |
| API-02 REST snapshot latest frame | 05-02 T3 `/api/snapshot`; 05-03 T1 `/v1/snapshot` + alias parity | Covered |
| API-03 Completeness det/depth/free_space | 05-02 | T2 assembler completeness | Covered |
| API-04 FPS / stage latency / drops | 05-02 T2 stats; 05-03 stream inherits via assembler | Covered |
| API-05 Perception-only (no motor/velocity/path) | 05-02 T1 schema denylist; 05-03 T1 envelope tests | Covered |
| UI-02 Overlay det + depth + free-space | 05-03 | T2 draw order depth→free→boxes; T3 footer | Covered |
| UI-06 UI + robot API same store | 05-02 single assembler; 05-03 store-only MJPEG + `/v1` | Covered |

### Goal-backward (ROADMAP SC → plans)

| # | Success criterion | Delivering tasks | Status |
|---|-------------------|------------------|--------|
| 1 | Free-space from depth on dashboard | 05-01 algorithm+loop+draw helper; 05-03 MJPEG + serve FreeSpaceLoop | Covered |
| 2 | WS `/v1/stream` + completeness | 05-02 assembler; 05-03 T1 WS send_json of PerceptionFrame | Covered |
| 3 | REST latest merged frame | 05-02 `/api/snapshot` → assembler; 05-03 `GET /v1/snapshot` alias parity | Covered |
| 4 | Stale/incomplete visible; no safe-to-proceed | 05-02 ages/TTL/stale ≠ completeness; 05-03 STALE badge + denylist + README | Covered |
| 5 | UI overlays match API (single store) | FreeSpaceProduct in PerceptionStore; MJPEG `snapshot_free_space`; API assemble same store | Covered |
| 6 | Stream metadata FPS/latency/drops | 05-02 stats from store metrics + ages; WS dumps full frame | Covered |

### Explicit checks requested

| Check | Result |
|-------|--------|
| Free-space honesty (no fake meters) | **Pass** — `units="ordinal"`, `method="near_field_bands"`, never `distance_m` on relative path; even `metric_estimated` stays ordinal without calibration; honesty tests in 05-01/05-02 |
| No motor fields (API-05) | **Pass** — `extra=forbid` + expanded FORBIDDEN denylist (safe_to_drive, go_nogo, cmd_vel, twist, path_plan); schema + `/v1` dump tests |
| Single store parity (UI-06) | **Pass** — one PerceptionStore triple product; single `assemble_perception_frame`; MJPEG reads store only (no handler-side free-space math) |
| Stale TTL | **Pass** — DEFAULT_TTL_MS det 500 / depth 750 / free_space 750; ages + `*_stale` + `products_stale` independent of completeness |
| No SLAM creep | **Pass** — near-field bands only; NOT ground-plane / BEV / SLAM / Nav2; deferred metric meters / stage matrix / open-vocab excluded |
| Threat models | **Pass** — all three plans include STRIDE registers (T-05-01..05/06 + SC) covering ordinal honesty, stale spoofing, motor elevation, mask disclosure, WS DoS, safe-to-drive UI misuse |

---

## Plan Summary

| Plan | Wave | depends_on | Tasks | files_modified | Requirements | Threat model | Structure |
|------|------|------------|-------|----------------|--------------|--------------|-----------|
| 05-01 | 1 | [] | 3 | 11 | SPACE-01, SPACE-02 | Present (T-05-01..05, SC) | Valid |
| 05-02 | 2 | ["05-01"] | 3 | 7 | SPACE-02, SPACE-04, API-03..05 | Present | Valid |
| 05-03 | 3 | ["05-01","05-02"] | 3 | 12 | API-01, API-02, API-05, SPACE-03, SPACE-04, UI-02, UI-06 | Present | Valid |

Dependency graph: acyclic, wave-consistent (`1 → 2 → 3`). No forward refs.  
Cross-plan contract: `FreeSpaceProduct` / `set_free_space` / `snapshot_free_space` / `FreeSpaceLoop` / `draw_free_space` (01) → `assemble_perception_frame` / expanded `FreeSpacePayload` (02) → `/v1` REST+WS + MJPEG + serve lifecycle (03).

File dual-touch: `routes_detection.py` in 05-02 then 05-03 (wave-ordered; safe).

`gsd-sdk query verify.plan-structure` → all three plans `valid: true`, zero errors.

---

## Dimension Results

### 1. Requirement Coverage — PASS

All eleven Phase 5 requirement IDs appear in plan `requirements` frontmatter and map to concrete tasks. No roadmap requirement orphaned. Deferred (UI-03/04 stage matrix, open-vocab Phase 6, edge TensorRT Phase 7, metric-calibrated free-space meters) correctly excluded.

### 2. Goal-Backward — PASS

All six ROADMAP success criteria have implementing tasks and `must_haves.truths`. Vertical slice complete:

```
DepthProduct.depth_map
        ↓
FreeSpaceLoop (Spatial Post: bands + morphology/EMA)
        ↓
PerceptionStore.FreeSpaceProduct (in-process masks + obstacles)
        ↓
assemble_perception_frame ──→ GET /v1/snapshot + WS /v1/stream
        │                     GET /api/snapshot (alias)
        ↓
MJPEG: blend_depth → draw_free_space → draw_detections
UI footer/STALE from /api/status free_space_* (same store)
```

### 3. Task Completeness — PASS

Every task has `<files>`, `<action>`, `<verify>` with `<automated>`, and `<done>`. TDD tasks include `<behavior>`. Actions are specific (function names, field lists, draw order, TTL numbers, start/stop order) — not “implement free-space.”

05-03 Task 3 is non-TDD `auto` (UI/docs); still has files/action/verify/done.

### 4. Dependencies & Waves — PASS

| Plan | Wave | depends_on | Consistent? |
|------|------|------------|-------------|
| 05-01 | 1 | [] | Yes |
| 05-02 | 2 | ["05-01"] | Yes |
| 05-03 | 3 | ["05-01","05-02"] | Yes |

No same-wave file conflicts. Sequential dual-touch of `routes_detection.py` is correct.

### 5. Key Links Planned — PASS

| Link | Plan | Task wiring |
|------|------|-------------|
| FreeSpaceLoop → `snapshot_depth` | 05-01 | T2 poll keep-latest |
| FreeSpaceLoop → `set_free_space` | 05-01 | T2 after compute |
| free_space → morphology/CC obstacles | 05-01 | T1 |
| FreeSpaceLoop → OccupancySmoother | 05-01 | T2 |
| assemble → triple snapshot | 05-02 | T2 |
| assemble → FreeSpacePayload (no masks) | 05-02 | T2 |
| `/api/snapshot` → assemble | 05-02 | T3 |
| `/v1/*` → assemble | 05-03 | T1 |
| MJPEG → `draw_free_space` + store | 05-03 | T2 |
| serve → FreeSpaceLoop start/stop | 05-03 | T2 |
| UI footer → status free_space fields | 05-03 | T3 |

Artifacts are not isolated — store + single assembler are the hubs.

### 6. Scope Sanity — PASS (with warnings)

| Plan | Tasks | files_modified | Notes |
|------|-------|----------------|-------|
| 05-01 | 3 (target) | 11 | Slightly above 5–8 file target; coherent Spatial Post package + store half |
| 05-02 | 3 (target) | 7 | Within target |
| 05-03 | 3 (target) | 12 | REST/WS + overlay + serve + UI + docs — dense but coherent twin of Phase 3–4 wave 2 |

No plan exceeds 4–5 tasks. No SLAM / Nav2 / BEV-default / motor / second dense net / stage-toggle matrix creep. No new ML packages.

### 7. must_haves / Verification Derivation — PASS

Truths are user/consumer-observable (ordinal free-space, WS stream, alias parity, STALE, no motor fields, overlay order). Artifacts map to truths with exports. Key links specify wiring method (`snapshot_free_space`, `assemble_perception_frame`, `draw_free_space`).

### 8. Context Compliance — PASS

| Locked decision / discretion | Honored? |
|------------------------------|----------|
| NumPy/OpenCV Spatial Post only (no second net) | Yes — pure `spatial/` package |
| Spatial Post sole free-space owner | Yes — FreeSpaceLoop separate from DepthLoop |
| Image-space / ordinal occupancy (not fake meters) | Yes — units/method honesty locked |
| Perception stream only | Yes — API-05 denylist + docs |
| UI overlays from same store robots read | Yes — UI-06 wiring |
| Localhost default bind preserved | Yes — threat model + no bind change tasks |
| Discretion: algorithm near-field bands | Yes — research-locked default |
| Discretion: separate FreeSpaceLoop | Yes |
| Discretion: wire = obstacles+bands (not full masks) | Yes |
| Discretion: JSON WS | Yes |
| Discretion: `/api/snapshot` alias | Yes |
| Deferred: stage toggles / open-vocab / edge / metric meters | Excluded |

**Scope reduction:** No silent “v1 static labels” style reduction of locked decisions. “v1” language is limited to research-locked choices (ordinal even for `metric_estimated`; obstacle list not full masks) that match CONTEXT discretion + deferred metric calibration.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Free-space derivation / smoothing | API/Backend Spatial Post | `spatial/*` + FreeSpaceLoop |
| Merged frame assembly / TTL | API/Backend | `api/assemble.py` |
| WS/REST `/v1` | API/Backend | `routes_v1.py` |
| MJPEG free-space draw | API/Backend | `routes_preview.py` |
| Footer metrics / STALE display | Browser | `index.html` polls `/api/status` |
| API-05 boundary | API schema + tests | schemas + test_api_perception_only |

No security-sensitive free-space math or auth elevation in browser tier.

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. `workflow.nyquist_validation: true`.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 bands+smoothing | 05-01 | 1 | `pytest tests/test_free_space_bands.py tests/test_free_space_smoothing.py` | ✅ |
| T2 store+loop | 05-01 | 1 | `pytest tests/test_perception_store.py tests/test_free_space_loop.py` | ✅ |
| T3 overlay | 05-01 | 1 | full 05-01 free-space suite | ✅ |
| T1 schemas | 05-02 | 2 | `pytest tests/test_schemas_perception.py` | ✅ |
| T2 assemble | 05-02 | 2 | assemble + schemas | ✅ |
| T3 snapshot alias | 05-02 | 2 | api_detection + assemble + schemas | ✅ |
| T1 /v1 + API-05 | 05-03 | 3 | test_api_v1 + perception_only + detection | ✅ |
| T2 MJPEG+serve | 05-03 | 3 | test_api_preview + test_cli_serve | ✅ |
| T3 UI+README | 05-03 | 3 | phase regression suite | ✅ |

- **8a Automated verify:** all tasks have `<automated>` (no MISSING)  
- **8b Latency:** unit/API pytest only (not full E2E suite / no `--watch`)  
- **8c Sampling:** each wave 3/3 tasks verified  
- **8d Wave 0:** TDD tasks create tests in-plan (RED→GREEN); no broken MISSING links  

**Note:** VALIDATION.md / RESEARCH Validation Architecture still list alternate test names (`test_free_space.py`, `test_spatial_loop.py`, `test_assemble_frame.py`, `test_v1_snapshot.py`). Plans use a consistent final set (`test_free_space_bands.py`, `test_free_space_loop.py`, `test_assemble_perception_frame.py`, `test_api_v1.py`). Hygiene only — not a plan blocker.

### 9. Cross-Plan Data Contracts — PASS

| Shared entity | Producer | Consumer | Compatible? |
|---------------|----------|----------|-------------|
| FreeSpaceProduct (masks + obstacles) | 05-01 | 05-02 assemble, 05-03 MJPEG | Yes — masks stay in-process; wire strips masks |
| FreeSpacePayload wire shape | 05-02 schemas | 05-03 `/v1` dump | Yes — same assembler |
| `assemble_perception_frame` | 05-02 | 05-03 REST+WS | Yes — single merge path |
| `draw_free_space` | 05-01 | 05-03 preview | Yes — pure helper |

No conflicting strip/parse on same stream without preservation: full masks preserved on product; wire uses obstacle list only by design.

### 10. CLAUDE.md Compliance — SKIPPED

No project-local `./CLAUDE.md` or `.agents/skills/` in repo. Plans follow GSD + `.planning` contracts and PATTERNS.md analogs.

### 11. Research Resolution — PASS (recommendations locked)

RESEARCH `## Open Questions` lacks formal `(RESOLVED)` suffix, but each design question has an explicit **Recommendation** that plans implement:

| Question | Locked into plans |
|----------|-------------------|
| Nearness polarity | `auto` + explicit polarities + synthetic tests (05-01) |
| `/api/snapshot` forever? | Alias to same assembler (05-02/05-03) |
| Mask on REST? | Omit; obstacles+bands only (05-02) |
| metric_estimated free-space | Stay `units=ordinal` without calibration (05-01) |
| Same-frame merge | Latest-per-product; free_space parent = depth frame_id (05-01/05-02) |

Residual bottom-of-file open items (live polarity tuning, stream Hz after first robot client) are operational, not design blockers.

### 12. Pattern Compliance — PASS

Plans `read_first` and actions reference 05-PATTERNS.md analogs (DepthLoop twin, draw_detections twin, dual→triple store, assemble extract from `api_snapshot`, cli DepthLoop lifecycle). Shared patterns (keep-latest, ordinal honesty, perception-only, no handler inference) appear across plans. `deps.py` correctly left alone (loops owned by CLI; store is single truth).

---

## Warnings (non-blocking)

```yaml
issues:
  - dimension: scope_sanity
    severity: warning
    plan: "05-01"
    description: "11 files_modified (target 5–8; warning ≥10). Coherent Spatial Post package — acceptable, watch context during execute."
    fix_hint: "No split required unless executor context pressure appears; keep TDD slices as written."

  - dimension: scope_sanity
    severity: warning
    plan: "05-03"
    description: "12 files_modified across routes, status, cli, UI, README, and four test modules."
    fix_hint: "Acceptable Phase-close plan; if context tightens mid-execute, finish T1 then T2/T3 as separate commits."

  - dimension: nyquist_compliance
    severity: warning
    plan: null
    description: "VALIDATION.md and RESEARCH Validation Architecture list test filenames that diverge from plan-owned names (e.g. test_free_space.py vs test_free_space_bands.py; test_assemble_frame.py vs test_assemble_perception_frame.py)."
    fix_hint: "Sync VALIDATION.md Wave 0 checklist to plan filenames during execute or a docs-only follow-up; plans themselves are internally consistent."

  - dimension: key_links_planned
    severity: warning
    plan: "05-03"
    task: 2
    description: "Status free_space_age_ms / free_space_stale phrased as 'optionally… if cheap' while Task 3 STALE badge depends on stale flags or ages from status."
    fix_hint: "Executor should treat free_space_age_ms (from product t_capture) as required for UI STALE path; free_space_stale boolean optional if ages + known TTL suffice. Do not ship footer without an age or stale signal."

  - dimension: task_completeness
    severity: warning
    plan: "05-01"
    task: 1
    description: "Morphology ownership slightly dual-specified: compute_free_space 'when called without external smoother' vs loop-owned OccupancySmoother (morphology+EMA)."
    fix_hint: "Implement prefer path: compute_free_space emits raw occupancy; only OccupancySmoother applies open/close+EMA to avoid double morphology."
```

---

## Free-Space Honesty Audit (explicit)

| Risk | Plan control | Status |
|------|--------------|--------|
| Relative depth labeled as meters | `units="ordinal"`; forbid `distance_m`; tests | Locked |
| Fake metric free-space from monocular | method=`near_field_bands`; no ground-plane meters | Locked |
| metric_estimated silently becomes meters | still ordinal without calibration metadata | Locked |
| Safe-to-drive / go-nogo language | schema denylist + UI-SPEC ban + string tests | Locked |
| Dual UI-only free-space path | MJPEG from store product only; no `compute_free_space` in routes | Locked |
| Stale “all clear” after stall | ages + TTL stale flags; completeness ≠ freshness | Locked |
| Motor/cmd_vel on stream | extra=forbid + dump key denylist on `/v1` | Locked |
| SLAM / costmap / Nav2 | Explicit out of scope in CONTEXT + plans | Locked |

---

## Recommendation

0 blockers. Plans are ready for execution.

Run `/gsd:execute-phase 5` (or execute 05-01 → 05-02 → 05-03 in wave order). During 05-03 Task 2, firm up `free_space_age_ms` on `/api/status` so Task 3 STALE badge is not optional in practice.

---

## PLAN CHECK PASSED
