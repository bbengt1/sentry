# Phase 4 Plan Check — Monocular Depth

**Checked:** 2026-08-07  
**Plans verified:** 04-01, 04-02  
**Status:** PLAN CHECK PASSED  
**Gate type:** Revision Gate (pre-execution)

---

## Verdict

**PLAN CHECK PASSED**

Plans will achieve the Phase 4 goal and all four roadmap requirements (DEPTH-01..04) if executed as written. No blockers. Warnings below are hygiene / map-alignment only and do not prevent execution.

---

## Phase Goal (source of truth)

> Add the spatial awareness primitive with honest monocular depth semantics (relative by default).

**ROADMAP Success Criteria:**

1. Local monocular depth model produces a per-frame depth map  
2. Stream includes depth with explicit `depth_kind` (relative vs metric modes)  
3. Dashboard shows depth colormap overlaid or side-by-side with RGB  
4. Relative depth is never exposed as meters; optional metric mode is clearly labeled  
5. Stage latency for depth is reported in telemetry  

**Requirements:** DEPTH-01, DEPTH-02, DEPTH-03, DEPTH-04  

---

## Coverage Summary

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| DEPTH-01 Monocular depth model runs locally (DAV2 Small OSS) | 04-01 | T1 depth extra + HF cache; T2 preprocess/mapping/store; T3 worker+loop+plugin | Covered |
| DEPTH-02 Depth in perception stream with explicit `depth_kind` | 04-02 | T1 snapshot DepthPayload + completeness.depth | Covered |
| DEPTH-03 Depth colormap on web dashboard | 04-02 | T1 colormap helpers; T2 MJPEG blend_depth | Covered |
| DEPTH-04 Optional metric labeled; never conflated with relative | 04-01 T2 kind_for_mode; 04-02 T1 honesty tests + config; T2 status unit omit; T3 UI “not meters” | Covered |

### Goal-backward (ROADMAP SC → plans)

| # | Success criterion | Delivering tasks | Status |
|---|-------------------|------------------|--------|
| 1 | Local monocular depth → per-frame depth map | 04-01 T3 DepthAnythingWorker + DepthLoop → set_depth; injectable CI + real HF path under `--extra depth` | Covered |
| 2 | Stream includes depth with `depth_kind` | 04-02 T1 GET /api/snapshot DepthPayload.kind + completeness.depth (full `/v1` deferred Phase 5 per CONTEXT) | Covered |
| 3 | Dashboard depth colormap | 04-02 T1 colorize/blend TURBO; T2 server-side MJPEG composite | Covered |
| 4 | Relative never meters; metric clearly labeled | 04-01 mapping kind_for_mode; 04-02 honesty tests, status unit omit, UI “relative (not meters)”, metric_estimated + m | Covered |
| 5 | Depth stage latency in telemetry | 04-01 store last_depth_latency_ms; 04-02 status depth_latency_ms + UI #metric-depth-ms | Covered |

### Explicit checks requested

| Check | Result |
|-------|--------|
| Depth honesty (relative never meters) | **Pass** — kind_for_mode from mode only; DepthPayload validators; no `depth_m`; UI badge “not meters”; `test_depth_kind_honesty` + schema tests |
| Apache Small default | **Pass** — MODE_TO_MODEL allowlists only Small HF ids; never Base/Large/Giant default; THIRD_PARTY + README; T-04-03 |
| Mock CI | **Pass** — injectable model/processor; unit tests never call HF hub; full suite green without depth extra; real DAV2 manual-only |
| DET-parity pattern for store | **Pass** — extend single `PerceptionStore` with `DepthProduct` (not DepthStore); keep-latest + isolated snapshot; dual det+depth coexistence tests |
| No free-space scope creep | **Pass** — free_space=False only on Completeness; free-space UI/derivation explicitly out of scope (Phase 5) |
| Threat models | **Pass** — both plans include STRIDE registers (04-01: T-04-01..05+SC; 04-02: T-04-01..06+SC) |

---

## Plan Summary

| Plan | Wave | depends_on | Tasks | Requirements | Threat model | Structure |
|------|------|------------|-------|--------------|--------------|-----------|
| 04-01 | 1 | [] | 3 | DEPTH-01 | Present (T-04-01..05, SC) | Valid |
| 04-02 | 2 | ["04-01"] | 3 | DEPTH-02, DEPTH-03, DEPTH-04 | Present (T-04-01..06, SC) | Valid |

Dependency graph: acyclic, wave-consistent (`1 → 2`). No forward refs. Cross-plan contract: `DepthProduct` / `set_depth` / `snapshot_depth` / `DepthAnythingWorker` / `DepthLoop` / `configure_model_cache` HF_HOME / MODE_TO_MODEL (01 → 02).

`gsd-sdk query verify.plan-structure` → both plans `valid: true`, zero errors.

---

## Dimension Results

### 1. Requirement Coverage — PASS

All four Phase 4 requirement IDs appear in plan `requirements` frontmatter and map to concrete tasks. No roadmap requirement orphaned. Deferred (free-space, full `/v1` WS, open-vocab, TensorRT, stereo, full metric calibration) correctly excluded.

### 2. Goal-Backward — PASS

All five ROADMAP success criteria have implementing tasks and `must_haves.truths`. Vertical slice complete:

```
FrameBus → DepthLoop → DepthAnythingWorker → PerceptionStore (DepthProduct)
                ↓                    ↓
         MJPEG blend_depth    GET /api/snapshot DepthPayload
         status depth_*       PATCH /api/depth/config + UI labels
         sentry serve lifecycle + optional depth extra
```

### 3. Task Completeness — PASS

Every task has:

- `<files>`
- `<read_first>`
- `<action>` (concrete steps: HF model ids, kind/unit mapping, store fields, route contracts, UI element ids)
- `<verify>` with `<automated>`
- `<acceptance_criteria>` + `<done>`

TDD tasks include `<behavior>`. Actions are specific (not “implement depth”).

### 4. Dependencies & Waves — PASS

| Plan | Wave | depends_on | Consistent? |
|------|------|------------|-------------|
| 04-01 | 1 | [] | Yes |
| 04-02 | 2 | ["04-01"] | Yes |

Wave 0 skip stubs for 04-02 colormap/api_depth created in 04-01 T1. No same-wave file conflicts (sequential waves; README/THIRD_PARTY dual-touch is wave-ordered).

### 5. Key Links Planned — PASS

| Link | Plan | Task wiring |
|------|------|-------------|
| DepthLoop → FrameBus.get_latest | 04-01 | T3 `_run` keep-latest |
| DepthLoop → PerceptionStore.set_depth | 04-01 | T3 after process |
| Worker → kind_for_mode / MODE_TO_MODEL | 04-01 | T3 process path |
| Worker → configure_model_cache / HF_HOME | 04-01 | T1 cache + T3 real load |
| pyproject → depth extra + worker entry | 04-01 | T1 + T3 registry |
| MJPEG → snapshot_depth + blend_depth | 04-02 | T2 |
| snapshot → DepthPayload + Completeness.depth | 04-02 | T1 |
| PATCH → worker.set_depth_mode | 04-02 | T1 |
| UI → /api/status depth_kind / depth_latency_ms | 04-02 | T3 |
| serve → DepthLoop start/stop | 04-02 | T3 |

Artifacts are not isolated — store is the single-truth hub (DET-parity).

### 6. Scope Sanity — PASS (with warnings)

| Plan | Tasks | files_modified | Notes |
|------|-------|----------------|-------|
| 04-01 | 3 (target) | 22 | Inflated by Wave 0 skip stubs + package inits + docs (same pattern as Phase 3-01 with 25) |
| 04-02 | 3 (target) | 17 | Colormap + routes + status + serve + UI — dense but coherent twin of 03-02 |

No plan exceeds 4–5 tasks. No free-space / open-vocab / TensorRT / stereo creep. Optional-extra isolates torch/transformers.

### 7. must_haves / Verification Derivation — PASS

Truths are user-observable (mock worker returns depth_map + kind; snapshot completeness; relative never meters; TURBO on MJPEG; serve degrade). Artifacts map to truths with exports. Key links specify wiring method.

### 8. Context Compliance — PASS

| Locked decision | Honored? |
|-----------------|----------|
| DAV2 Small Apache-2.0 default; never NC Base/Large | Yes — MODE_TO_MODEL Small only + docs + T-04-03 |
| Relative by default; metric only when enabled with correct kind+unit | Yes — depth_mode default relative; metric → METRIC_ESTIMATED + m |
| No `depth_m` on relative paths; existing DepthPayload | Yes — map into existing schemas; honesty tests assert no depth_m |
| Workers never open cameras; FrameBus → store | Yes — DepthLoop twin; architecture asserts no VideoCapture |
| UI and API one depth product truth | Yes — single PerceptionStore for MJPEG/snapshot/status |
| Local OSS only; cache after first download | Yes — HF_HOME under SENTRY_MODEL_CACHE; offline after cache |

**Claude's Discretion** exercised and locked in plans: HF transformers path (not native/timm); full float in-process + metadata-only wire; server-side TURBO alpha-blend 0.45; optional-extra `depth`; metric indoor/outdoor via `depth_mode` + GET/PATCH config.

**Deferred ideas excluded:** free-space Spatial Post, full `/v1` WS, open-vocab, TensorRT, stereo, full metric calibration UX.

**Scope reduction:** None detected. Optional UI depth_mode select is “nice-to-have” while DEPTH-04 still closes via PATCH config + status/UI labels when metric product present — matches RESEARCH recommendation (serve-time/config enough; PATCH if low cost). Wave 0 test stubs are Nyquist scaffolding, not reduced product scope. Snapshot vs full `/v1` is explicit Phase 5 deferral in CONTEXT.

### 7b. Scope Reduction Detection — PASS

No “v1 static”, “hardcoded labels instead of calculated”, “future enhancement” substitutions for locked decisions. Metric mode is real (MODE_TO_MODEL metric heads + METRIC_ESTIMATED), not a fake label on relative maps. Relative honesty is enforced end-to-end (mapping → store → wire → status → UI).

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| DAV2 load + inference | Backend depth thread | DepthAnythingWorker + DepthLoop |
| Preprocess / kind mapping | Backend worker pure helpers | preprocess.py + mapping.py |
| Full float depth map | Backend store (in-process) | DepthProduct.depth_map |
| Depth metadata JSON | API handlers (no re-infer) | routes_detection snapshot |
| Colormap composite | Backend MJPEG encode | colormap.py + routes_preview |
| Depth latency telemetry | Backend metrics → browser poll | store metrics + status + index.html |
| Metric mode config | Worker state + optional browser | set_depth_mode + PATCH + optional UI |
| HF model cache | Backend + filesystem | configure_model_cache HF_HOME |
| Capture ownership | Unchanged CaptureLoop | Workers never VideoCapture |

No security-sensitive capability assigned to a less-trusted tier. Handlers never run inference.

### 8. Nyquist Compliance — PASS

VALIDATION.md present. `workflow.nyquist_validation: true`.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 Wave 0 + depth extra + HF cache + docs | 04-01 | 1 | `pytest test_model_cache + third_party_doc + ruff + rg depth extra` | ✅ |
| T2 preprocess + mapping + store | 04-01 | 1 | `pytest test_depth_preprocess + mapping + perception_store + ruff` | ✅ |
| T3 worker + loop + plugin | 04-01 | 1 | focused depth/store/registry pytest + full suite + ruff | ✅ |
| T1 colormap + snapshot + depth routes | 04-02 | 2 | `pytest colormap + api_depth + kind_honesty + api_detection + schemas + ruff` | ✅ |
| T2 MJPEG blend + status | 04-02 | 2 | `pytest preview + api_depth + colormap + ruff` | ✅ |
| T3 serve + UI + docs | 04-02 | 2 | focused pytest + full suite + ruff | ✅ |

Sampling: Wave 1: 3/3 verified → ✅; Wave 2: 3/3 verified → ✅  
Wave 0: stubs planned in 04-01 T1 for colormap/api_depth; core depth tests filled in 04-01 T2–T3; remaining honesty tests in 04-02 T1 → ✅  
No `--watchAll`. Mock DAV2; no HF weight download in default CI → ✅  
Overall: ✅ PASS

**Note:** VALIDATION.md Wave 0 lists `tests/test_depth_overlay.py` while RESEARCH/plans use `tests/test_depth_colormap.py` — drift only (see warnings).

### 9. Cross-Plan Data Contracts — PASS

Shared entity `DepthProduct` / depth_map + kind/unit:

- 04-01 produces via `set_depth` (keep-latest under lock; stats from depth_stats)
- 04-02 consumes via `snapshot_depth()` for JSON metadata, MJPEG blend, status fields
- Wire path never serializes full HxW float (metadata + stats only) — no strip conflict with in-process colormap consumer
- Completeness: `depth = product exists and error is None`; 404 only when neither det nor depth product exists
- Dual frame_id policy: top-level prefers latest `t_capture`; `det_frame_id` / `depth_frame_id` in stats (implements RESEARCH Q2)

### 10. CLAUDE.md Compliance — SKIPPED

No project-root `CLAUDE.md` / `AGENTS.md`. Plans follow Phase 1–3 conventions documented in RESEARCH/PATTERNS (src layout, ruff, pytest, uv, optional-deps not dependency-groups, handlers never open cameras, optional-extra degrade).

### 11. Research Resolution — PASS (with warning)

RESEARCH `## Open Questions` has recommendations for all five items. Plans implement each:

| Q | Recommendation | Plan implementation |
|---|----------------|---------------------|
| Metric Small license | Relative default; document verify for metric | 04-01 docs + relative default; metric optional with THIRD_PARTY note |
| Snapshot frame_id multi-product | Latest t_capture + dual ids in stats | 04-02 T1 snapshot assembly |
| Depth config API | Optional GET/PATCH if low cost | 04-02 T1 routes_depth |
| Golden numerical tests | Lock preprocess/mapping/colormap not bit-exact DAV2 | 04-01 T2 + 04-02 T1 |
| torch in depth extra | List torch explicitly | 04-01 T1 optional-dependencies.depth |

**Warning:** Section is not titled `## Open Questions (RESOLVED)` and lacks inline `RESOLVED:` markers — hygiene only; does not block execution.

### 12. Pattern Compliance — PASS

Plans reference `04-PATTERNS.md` and analogs in every `<read_first>` (DetectionLoop, YoloDetectionWorker, perception_store, overlay→colormap, routes_preview, create_app, cli serve block). Shared patterns (FrameBus→store, injectable fakes, keep-latest, optional-extra degrade, depth honesty, HF cache) appear in actions. HF inference body correctly falls back to RESEARCH Pattern 3 (No Analog Found).

---

## Threat Model Coverage

| Threat | Plan mitigation | Status |
|--------|-----------------|--------|
| T-04-01 Relative sold as meters / kind spoofing | kind_for_mode from mode only; schema validators; UI “not meters”; test_depth_kind_honesty | Covered both |
| T-04-02 Tampering (cache paths / config) | HF_HOME under SENTRY_MODEL_CACHE; MODE_TO_MODEL allowlist; Literal depth_mode + extra=forbid | Covered both |
| T-04-03 NC weights as default | Apache Small only default; never Base/Large | Covered 04-01 |
| T-04-04 Capture stall / DoS | DepthLoop keep-latest thread; no infer in handlers/MJPEG | Covered both |
| T-04-05 Dual truth UI≠API / array disclosure | Single PerceptionStore; metadata-only wire; size sanity tests | Covered both |
| T-04-06 LAN exposure | Localhost default preserved (MODEL-03) | Covered 04-02 |
| T-04-SC Supply chain | optional-extra only; no native timm; RESEARCH legitimacy | Covered 04-01 |

VALIDATION threats T-4-01..05 map to the same mitigations (ID naming differs slightly).

---

## Mock CI Strategy (verified)

- Injectable `model=` + `processor=` / FakeDepthWorker — no transformers/torch required for unit tests  
- Pure preprocess/mapping/colormap — no torch for golden paths  
- `configure_model_cache` HF_HOME tests use tmp_path — never network  
- Real DAV2 + first-download/offline → VALIDATION **Manual**  
- Full suite remains green without depth extra  
- serve degrades cleanly without `--extra depth` (`uv sync --extra depth` hint)

---

## Depth Honesty Audit (DEPTH-04 + FOUND-03)

| Layer | Relative path | Metric path |
|-------|---------------|-------------|
| mapping.py | RELATIVE, unit=None | METRIC_ESTIMATED, unit="m" |
| worker process | kind_for_mode(mode) only — no float heuristics | same |
| DepthPayload wire | unit null; no depth_m key | kind metric_estimated + unit m |
| /api/status | omit/null depth_unit | depth_unit only when non-null |
| Live Preview UI | “relative (not meters)” / “Relative depth (not meters)” | kind + “m” only when unit is m |
| Tests | test_depth_mapping + test_depth_kind_honesty + test_schemas_depth_kind | metric_indoor/outdoor cases |

No path labels relative depth as meters.

---

## Warnings (non-blocking)

```yaml
issues:
  - dimension: scope_sanity
    severity: warning
    plan: "04-01"
    description: "files_modified lists 22 paths — above 15 nominal threshold, inflated by Wave 0 skip stubs, package __init__, and docs (same pattern as Phase 3-01 with 25)"
    fix_hint: "No split required; executor should treat Wave 0 stubs as thin. Core impl is cache/preprocess/mapping/store/worker/loop"

  - dimension: scope_sanity
    severity: warning
    plan: "04-02"
    description: "files_modified lists 17 paths — dense API/UI wave twin of Phase 3-02"
    fix_hint: "No split required; three tasks already separate colormap/API, MJPEG/status, and serve/UI"

  - dimension: research_resolution
    severity: warning
    plan: null
    description: "04-RESEARCH.md Open Questions have recommendations implemented by plans but section is not marked (RESOLVED)"
    fix_hint: "Retitle to '## Open Questions (RESOLVED)' and prefix each item with RESOLVED: for research hygiene"

  - dimension: verification_derivation
    severity: warning
    plan: null
    description: "04-VALIDATION.md Wave 0 lists tests/test_depth_overlay.py but RESEARCH/plans use tests/test_depth_colormap.py; also VALIDATION omits explicit Wave 0 stub for test_depth_kind_honesty (created as real tests in 04-02 T1)"
    fix_hint: "Align VALIDATION Wave 0 filenames with plans (colormap + kind_honesty) before or during execute"

  - dimension: verification_derivation
    severity: info
    plan: "04-01"
    task: 3
    description: "Task 3 verify runs full pytest suite — may exceed 30s on cold machines"
    fix_hint: "Acceptable as plan-end gate; keep module-focused pytest first (already present)"

  - dimension: task_completeness
    severity: info
    plan: "04-01"
    task: 3
    description: "set_depth_mode/get_depth_mode marked optional in 04-01; 04-02 T1 will add if missing — soft handoff is documented"
    fix_hint: "Prefer implementing thread-safe set/get in 04-01 T3 so 04-02 PATCH is pure wiring"
```

---

## Recommendation

0 blockers. Plans are ready for execution.

Run `/gsd:execute-phase 4` (or execute 04-01 then 04-02) to proceed.

---

## PLAN CHECK PASSED
