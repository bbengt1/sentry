# Phase 3 Plan Check — Fixed-Class Detection

**Checked:** 2026-08-07  
**Plans verified:** 03-01, 03-02  
**Status:** PLAN CHECK PASSED  
**Gate type:** Revision Gate (pre-execution)

---

## Verdict

**PLAN CHECK PASSED**

Plans will achieve the Phase 3 goal and all five roadmap requirements (DET-01..04, MODEL-02) if executed as written. No blockers. Warnings below are hygiene / map-alignment only and do not prevent execution.

---

## Phase Goal (source of truth)

> Deliver the first robot-usable AI signal — local fixed-class detection on the live stream with UI/API parity.

**ROADMAP Success Criteria:**

1. Local OSS fixed-class detector runs on live frames without cloud  
2. Boxes + labels + confidences appear on the dashboard overlay  
3. Same detections are available on a stream/snapshot endpoint  
4. Confidence threshold changes at runtime without process restart  
5. Models cache locally for offline re-runs after first download  

**Requirements:** DET-01, DET-02, DET-03, DET-04, MODEL-02  

---

## Coverage Summary

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| DET-01 Fixed-class local YOLO on live stream | 03-01 | T3 worker+loop; 03-02 T2 serve lifecycle | Covered |
| DET-02 class / conf / bbox_xyxy | 03-01 | T2 mapping + T3 process path | Covered |
| DET-03 runtime conf without restart | 03-01 T3 set_conf foundation; 03-02 T1 PATCH + T3 UI | Covered |
| DET-04 UI + stream same truth | 03-02 | T1 snapshot/overlay; T2 MJPEG from store; T3 metrics | Covered |
| MODEL-02 offline cache after first download | 03-01 | T1 cache helper + AGPL/cache docs; 03-02 serve uses configure_model_cache | Covered |

### Goal-backward (ROADMAP SC → plans)

| # | Success criterion | Delivering tasks | Status |
|---|-------------------|------------------|--------|
| 1 | Local OSS detector on live frames, no cloud | 03-01 T3 YoloDetectionWorker+DetectionLoop; 03-02 T2 serve start; mock CI + real path with `--extra detect` | Covered |
| 2 | Boxes + labels + conf on dashboard | 03-02 T1 draw_detections; T2 MJPEG overlay; T3 Live Preview | Covered |
| 3 | Same detections on stream/snapshot | 03-02 T1 GET /api/snapshot; T2 MJPEG from same PerceptionStore | Covered (snapshot path; full /v1 deferred Phase 5 per CONTEXT) |
| 4 | Conf threshold at runtime | 03-01 T3 set_conf; 03-02 T1 PATCH /api/detection/config; T3 debounced UI | Covered |
| 5 | Models cache offline after first download | 03-01 T1 configure_model_cache + THIRD_PARTY_MODELS/README; manual offline after cache per VALIDATION | Covered |

### Explicit checks requested

| Check | Result |
|-------|--------|
| No depth / open-vocab scope | **Pass** — both plans list as out of scope; no YOLOE/DAV2/free-space implementation tasks |
| Threat models | **Pass** — both plans include STRIDE registers T-03-01..05 + SC |
| Mock CI strategy | **Pass** — injectable FakeModel/FakeWorker; never download weights in default CI; VALIDATION manual-only for real YOLO |
| DET-04 parity | **Pass** — single PerceptionStore; snapshot + MJPEG + status all read store; tests assert snapshot list == store |
| Localhost (MODEL-03 continuity) | **Pass** — 03-02 preserves 127.0.0.1 default, allow_cloud gate, LAN warn |
| AGPL docs | **Pass** — 03-01 T1 updates THIRD_PARTY_MODELS + README; extends test_third_party_models_doc |

---

## Plan Summary

| Plan | Wave | depends_on | Tasks | Requirements | Threat model | Structure |
|------|------|------------|-------|--------------|--------------|-----------|
| 03-01 | 1 | [] | 3 | DET-01, DET-02, MODEL-02 | Present (T-03-01..05, SC) | Valid |
| 03-02 | 2 | ["03-01"] | 3 | DET-03, DET-04 | Present | Valid |

Dependency graph: acyclic, wave-consistent (`1 → 2`). No forward refs. Cross-plan contract: PerceptionStore / YoloDetectionWorker / DetectionLoop / configure_model_cache / tier_to_weight (01 → 02).

`gsd-sdk query verify.plan-structure` → both plans `valid: true`, zero errors.

---

## Dimension Results

### 1. Requirement Coverage — PASS

All five Phase 3 requirement IDs appear in plan `requirements` frontmatter and map to concrete tasks. No roadmap requirement orphaned. Deferred (depth, free-space, open-vocab, full `/v1`, TensorRT, stage matrix) correctly excluded.

### 2. Goal-Backward — PASS

All five ROADMAP success criteria have implementing tasks and `must_haves.truths`. Vertical slice complete:

```
FrameBus → DetectionLoop → YoloDetectionWorker → PerceptionStore
                ↓                    ↓
         MJPEG overlay      GET /api/snapshot
         status metrics     PATCH conf + UI slider
         sentry serve lifecycle + optional detect extra
```

### 3. Task Completeness — PASS

Every task has:

- `<files>`
- `<read_first>`
- `<action>` (concrete steps: types, paths, conf defaults, package pins)
- `<verify>` with `<automated>`
- `<acceptance_criteria>` + `<done>`

TDD tasks include `<behavior>`. Actions are specific (not “implement detection”).

### 4. Dependencies & Waves — PASS

| Plan | Wave | depends_on | Consistent? |
|------|------|------------|-------------|
| 03-01 | 1 | [] | Yes |
| 03-02 | 2 | ["03-01"] | Yes |

Wave 0 stubs created in 03-01 T1 (`test_detection_overlay`, `test_api_detection` skip until 03-02). No same-wave file conflicts.

### 5. Key Links Planned — PASS

| Link | Plan | Task wiring |
|------|------|-------------|
| DetectionLoop → FrameBus.get_latest | 03-01 | T3 `_run` keep-latest |
| DetectionLoop → PerceptionStore.set_detections | 03-01 | T3 after process |
| Worker → results_to_detections | 03-01 | T3 process path |
| cache → ultralytics weights_dir | 03-01 | T1 + T3 load path |
| pyproject → yolo-fixed entry point | 03-01 | T3 |
| MJPEG → store + draw_detections | 03-02 | T2 |
| snapshot → PerceptionFrame from store | 03-02 | T1 |
| PATCH → worker.set_conf | 03-02 | T1 |
| UI → /api/detection/config | 03-02 | T3 |
| serve → DetectionLoop start/stop | 03-02 | T2 |

Artifacts are not isolated — store is the DET-04 single-truth hub.

### 6. Scope Sanity — PASS (with warnings)

| Plan | Tasks | files_modified | Notes |
|------|-------|----------------|-------|
| 03-01 | 3 (target) | 25 | Inflated by Wave 0 skip stubs + package inits + docs; core impl is cache/mapping/store/worker/loop |
| 03-02 | 3 (target) | 14 | Overlay + routes + status + serve + UI — dense but coherent |

No plan exceeds 4–5 tasks. No depth/open-vocab/supervision/TensorRT creep. Optional-extra isolates torch.

### 7. must_haves / Verification Derivation — PASS

Truths are user-observable (mock worker returns detections; snapshot completeness; conf without restart; boxes on MJPEG; AGPL/cache docs). Artifacts map to truths with exports. Key links specify wiring method.

### 8. Context Compliance — PASS

| Locked decision | Honored? |
|-----------------|----------|
| YOLO26 via Ultralytics (n edge / s desktop) | Yes — weights map + desktop-gpu `m`→`s` |
| Local OSS; no cloud after cache | Yes — MODEL-02 cache + no cloud path |
| UI and API one truth | Yes — PerceptionStore only |
| Workers never open cameras | Yes — bus-only; architecture asserts |
| Ultralytics AGPL documented | Yes — THIRD_PARTY_MODELS + README + tests |
| Perception-only (no motor fields) | Yes — forbidden copy in UI tests |

**Claude's Discretion** exercised and locked in plans: DetectionLoop thread; Option A server-side OpenCV overlay; `/api/snapshot`; yolo26n default; no `supervision`.

**Deferred ideas excluded:** depth, free-space, open-vocab, full control plane, edge TRT.

**Scope reduction:** None detected. “InferenceBackend remains stubs” matches CONTEXT/RESEARCH (do not wrap Ultralytics in `infer(tensor)`). Wave 0 test stubs are Nyquist scaffolding filled in later tasks, not reduced product scope. Snapshot vs full `/v1` is explicit Phase 5 deferral in CONTEXT.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| YOLO inference | Backend detection thread | YoloDetectionWorker + DetectionLoop |
| Runtime conf | Worker state + browser slider | set_conf + PATCH + index.html |
| Overlay draw | Backend MJPEG encode | overlay.py + routes_preview |
| Snapshot JSON | API handlers (no re-infer) | routes_detection from store |
| Model cache | Backend + filesystem | models/cache.py |
| Live Preview controls | Static HTML | index.html |

No security-sensitive capability assigned to a less-trusted tier.

### 8. Nyquist Compliance — PASS

VALIDATION.md present. `workflow.nyquist_validation: true`.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 Wave 0 + cache + AGPL | 03-01 | 1 | `uv lock && uv sync --extra dev && pytest test_model_cache + third_party_doc + ruff + import smoke` | ✅ |
| T2 mapping + store | 03-01 | 1 | `pytest test_detection_mapping + test_perception_store + ruff` | ✅ |
| T3 worker + loop + plugin | 03-01 | 1 | focused pytest modules + full suite + ruff | ✅ |
| T1 overlay + routes + app | 03-02 | 2 | `pytest test_detection_overlay + test_api_detection + ruff` | ✅ |
| T2 MJPEG + status + serve | 03-02 | 2 | `pytest preview + api_detection + cli_serve + cli_smoke + ruff` | ✅ |
| T3 UI + docs polish | 03-02 | 2 | full `pytest -q` + ruff | ✅ |

Sampling: Wave 1: 3/3 verified → ✅; Wave 2: 3/3 verified → ✅  
Wave 0: stubs planned in 03-01 T1 for all VALIDATION test modules → ✅  
No `--watchAll`. Mock YOLO; no weight download in default CI → ✅  
Overall: ✅ PASS

### 9. Cross-Plan Data Contracts — PASS

Shared entity `DetectionProduct` / `list[Detection]`:

- 03-01 produces via `set_detections` (copy under lock)
- 03-02 consumes via `snapshot()` for JSON, MJPEG draw, status fields
- No strip/sanitize between producers and consumers
- Completeness semantics aligned: empty list + `detections=True` when product exists

### 10. CLAUDE.md Compliance — SKIPPED

No project-root `CLAUDE.md` / `AGENTS.md`. Plans follow Phase 1–2 conventions documented in RESEARCH (src layout, ruff, pytest, uv, optional-deps not dependency-groups, handlers never open cameras).

### 11. Research Resolution — PASS (with warning)

RESEARCH `## Open Questions` has recommendations (optional-extra, n/s defaults, status+snapshot, warmup, MPS auto). Plans implement all five recommendations. Residual Ultralytics network after `sync=False` remains an assumption (A5), not a phase blocker.

**Warning:** Section is not titled `## Open Questions (RESOLVED)` and lacks inline `RESOLVED:` markers — hygiene only; does not block execution.

### 12. Pattern Compliance — PASS

Plans reference `03-PATTERNS.md` and analogs in every `<read_first>` (CaptureLoop, FrameBus, NoopWorker, routes_preview, create_app, StatusSnapshot). Shared patterns (thread-safe conf, no VideoCapture in workers, inject via create_app) appear in actions. `cache.py` correctly falls back to RESEARCH Pattern 3 (no in-repo analog).

---

## Threat Model Coverage

| Threat | Plan mitigation | Status |
|--------|-----------------|--------|
| T-03-01 Malicious/arbitrary weights | Allowlist yolo26n/s/m.pt; cache root; no URL weights | Covered 03-01 |
| T-03-02 Unauthenticated conf on LAN | Localhost default; Pydantic conf [0,1] extra=forbid; LAN warn | Covered 03-02 |
| T-03-03 Dual detection truth | Single PerceptionStore; parity tests | Covered both |
| T-03-04 Capture stall / DoS | DetectionLoop keep-latest; no infer in handlers; UI debounce | Covered both |
| T-03-05 AGPL / disclosure | THIRD_PARTY_MODELS + README + first-run note | Covered 03-01/02 |
| T-03-SC Supply chain | optional-extra only; no supervision; RESEARCH legitimacy | Covered |

---

## Mock CI Strategy (verified)

- Injectable `model=` / FakeDetectionWorker — no Ultralytics import required for unit tests  
- Pure duck-typed `results_to_detections` — no torch for DET-02  
- `configure_model_cache` path tests use tmp_path + env monkeypatch — never network  
- Real YOLO + first-download/offline → VALIDATION **Manual-Only**  
- Smoke path remains green without torch (`test_cli_smoke`)  
- serve degrades cleanly without `--extra detect`

---

## Warnings (non-blocking)

```yaml
issues:
  - dimension: scope_sanity
    severity: warning
    plan: "03-01"
    description: "files_modified lists 25 paths — above 15 nominal threshold, inflated by Wave 0 skip stubs, package __init__s, and docs (same pattern as Phase 2-01)"
    fix_hint: "No split required; executor should treat Wave 0 stubs as thin. Optional: drop 03-02-only stub files from mental load after T1"

  - dimension: scope_sanity
    severity: warning
    plan: "03-02"
    task: 2
    description: "files_modified and Task 2 <files> include capture/loop.py, but recommended approach merges det metrics in routes_preview.api_status without coupling CaptureLoop"
    fix_hint: "Pick one: remove capture/loop.py from files list if unused, or explicitly document build_status optional kwargs if modified"

  - dimension: research_resolution
    severity: warning
    plan: null
    description: "03-RESEARCH.md Open Questions have recommendations implemented by plans but section is not marked (RESOLVED)"
    fix_hint: "Retitle to '## Open Questions (RESOLVED)' and prefix each item with RESOLVED: for Nyquist/research hygiene"

  - dimension: verification_derivation
    severity: info
    plan: "03-01"
    task: 3
    description: "Task 3 verify runs full pytest suite — may exceed 30s on cold machines"
    fix_hint: "Acceptable as plan-end gate; keep module-focused pytest first (already present)"
```

---

## Recommendation

0 blockers. Plans are ready for execution.

Run `/gsd:execute-phase 3` (or execute 03-01 then 03-02) to proceed.

---

## PLAN CHECK PASSED
