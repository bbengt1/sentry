# Phase 8 Plan Check — Backend Selection & Honesty

**Checked:** 2026-08-09  
**Plans:** `08-01-PLAN.md`, `08-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** CONTEXT, RESEARCH, PATTERNS, VALIDATION, ROADMAP Phase 8, REQUIREMENTS BACK-01/02/04 + EDGE-RT-01..03  

**Overall verdict:** **PASS**

**Re-check:** 2026-08-09 — `08-VALIDATION.md` authored from RESEARCH Validation Architecture (Nyquist gate closed).

---

## Phase goal (from ROADMAP)

> Operators and robots see honest backend identity; serve constructs the fixed-class detector via a factory driven by `preferred_backend`, with safe artifact path resolution — torch path still works end-to-end

**Success criteria (must be TRUE):**
1. `sentry serve` constructs the fixed-class detection worker through a factory from `profile_runtime` (not hard-coded torch-only construction)
2. `preferred_backend` selects among torch / onnxruntime / tensorrt **loader branches** (torch fully live; ORT/TRT may stub — selection is real wiring)
3. Status / serve banner expose both `backend_requested` and `backend_live` (never claim ORT/TRT when torch is running)
4. Artifact paths for `.onnx` / `.engine` resolve from config/env/cache with a safe allowlist (no path traversal)
5. DetectionLoop / FrameBus / PerceptionStore / `/v1` remain the perception spine unchanged; desktop-gpu stays torch-default

**Requirements:** BACK-01, BACK-02, BACK-04, EDGE-RT-01, EDGE-RT-02, EDGE-RT-03

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| BACK-01 | preferred_backend selects loader branch | 08-01 | T2 factory branches + soft stubs | Covered |
| BACK-02 | status/banner requested vs live | 08-02 | T1 StatusSnapshot+/api/status; T2 banner+footer | Covered |
| BACK-04 | allowlisted .onnx/.engine paths | 08-01 | T1 `resolve_detector_artifact` + traversal tests | Covered |
| EDGE-RT-01 | spine frozen | 08-01 T3 + 08-02 (no loop/bus/store/v1 edits) | Covered |
| EDGE-RT-02 | serve via factory from profile_runtime | 08-01 | T3 wire `build_detection_worker(rt)` | Covered |
| EDGE-RT-03 | desktop-gpu torch; jetson/cpu select honestly | 08-01 T2 matrix; 08-02 banner/status | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Factory owns fixed-class construction | `build_detection_worker` + `WorkerBuild` | `cli.serve` replaces inline `YoloDetectionWorker(...)` |
| preferred_backend selects real branches | if/elif torch \| onnxruntime \| tensorrt in factory | Torch live `.pt`; ORT/TRT soft-stub branches exist |
| Never claim live ORT/TRT under torch | `backend_live=torch` + reason codes; tests assert never ort/trt live | Factory sole author; status/UI pass-through only |
| Torch desktop-gpu still works E2E | torch branch → `YoloDetectionWorker` + DetectionLoop unchanged | `model=` injection for unit tests (no weight download) |
| Artifact paths safe | `resolve_detector_artifact` stem/suffix + root allowlist | env/cache/CWD; reject `..` / out-of-root |
| Status + banner honesty | StatusSnapshot + app.state + `/api/status` + CLI banner | 08-01 stashes locals → 08-02 injects |
| Live Preview UI hint | footer `metric-backend` from `/api/status` | Display only; no client write of identity |
| DetectionLoop frozen | Explicit freeze checklist; no edits to loop/bus/store/v1 | Duck-typed `worker.process` only |
| No Jetson / no new packages | pure pathlib + torch soft stubs; pytest only | No onnxruntime/tensorrt top-level imports |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- All six phase requirement IDs appear in plan frontmatter:
  - `08-01`: BACK-01, BACK-04, EDGE-RT-01, EDGE-RT-02, EDGE-RT-03
  - `08-02`: BACK-02, EDGE-RT-01, EDGE-RT-03
- Partition matches ROADMAP plan split (factory+paths vs status/banner honesty).
- No phase-mapped REQUIREMENTS.md item orphaned.
- BACK-03 / EDGE-RT-04 / ORT-* / TRT-* correctly **not** claimed (later phases).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done |
|------|-------|-------|--------|--------------------|------|
| 08-01 | 3 | all | all | all pytest | all |
| 08-02 | 2 | all | all | all pytest | all |

`verify.plan-structure` **valid** for both plans; zero structural errors/warnings.  
Actions name concrete modules, reason codes (`ort_loader_not_implemented`, `trt_loader_not_implemented`, `unsupported_backend`, `path_rejected`), env vars, and freeze constraints.

### 3. Dependency Correctness — PASS

```
08-01 (wave 1, depends_on: [])  →  08-02 (wave 2, depends_on: ["08-01"])
```

- Acyclic; wave = max(deps)+1 consistent.
- Shared `cli.py` only sequential (08-01 factory locals → 08-02 create_app/banner).
- No forward dependency from 08-01 into status/UI work.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| `cli.serve` → `build_detection_worker(rt)` | 08-01 T3 |
| factory → `YoloDetectionWorker` (torch + soft stubs) | 08-01 T2 |
| factory → `resolve_detector_artifact` (pre-check only) | 08-01 T1–T2 |
| `DetectionLoop(bus, worker, store)` unchanged | 08-01 T3 |
| WorkerBuild locals → `create_app(backend_*)` | 08-02 T2 (consumes 08-01 stash) |
| `api_status` → `app.state.backend_*` merge | 08-02 T1 |
| banner → `backend_requested` / `backend_live` / reason | 08-02 T2 |
| Live Preview footer → `/api/status` | 08-02 T2 |

No isolated artifacts; status/UI never invent live labels.

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 08-01 | 3 (target) | 7 | T2: factory + tests (~3 files) |
| 08-02 | 2 (target) | 9 | T1: status/app/routes + honesty tests |

- Within 2–3 tasks/plan and well under file thresholds.
- Clean split: construction/selection (01) then honesty surface (02).

### 6. Verification Derivation — PASS

must_haves truths are operator/robot-observable (factory used, live≠false ORT/TRT, banner/status pair, path reject, spine frozen).  
Artifacts map to truths; key_links specify wiring methods.

### 7. Context Compliance — PASS

| Locked decision | Plan coverage |
|-----------------|---------------|
| Factory at serve; DetectionLoop frozen | 08-01 T2–T3; freeze checklist |
| Torch `.pt` desktop-gpu default | 08-01 T2 desktop-gpu matrix |
| Phase 8 wires selection only (no live ORT/TRT) | Soft stubs; out-of-scope live sessions |
| No silent `backend_live=tensorrt` when torch | Explicit never-emit + tests |
| Artifact allowlist; no path traversal | 08-01 T1 |
| No prebuilt engines in wheel | CONTEXT + threat model; no engine ship tasks |

Deferred excluded: live ORT/TRT, sticky thrash-free modes, Jetson matrix depth, dual-model VRAM, depth/OV backends.

Discretion handled: `factory.py` + `artifact_paths.py`; soft stub (not raise); env names `SENTRY_DETECTOR_*`; Live Preview footer line.

### 7b. Scope Reduction — PASS

Soft-stub language is **not** silent reduction of a full-delivery decision:

- CONTEXT / ROADMAP explicitly allow ORT/TRT stubs until Phases 9–10.
- Plans still deliver **real branch wiring** + honest labels (BACK-01 + BACK-02).
- “Even if `.onnx` exists — no live ORT” is a phase boundary lock, not invented v1/v2 shadowing of a live-ORT decision.

No “placeholder / static for now / will wire later” that drops a locked deliverable.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Backend selection | API/Backend (serve construct) | factory + cli.serve |
| Artifact allowlist | API/Backend (config) | `artifact_paths.py` |
| backend identity authorship | API/Backend | WorkerBuild → app.state |
| Live Preview display | Browser (secondary) | index.html footer only |
| DetectionLoop scheduling | Frozen API/Backend | **no edits** |

No security-sensitive path policy or live-label authorship demoted to browser.

### 8. Nyquist Compliance — PASS

`workflow.nyquist_validation: true` in config.json. RESEARCH has `## Validation Architecture`.

**Check 8e:** `08-VALIDATION.md` **present** (authored 2026-08-09 from RESEARCH Validation Architecture).

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 artifact paths | 08-01 | 1 | `uv run pytest tests/test_artifact_paths.py -q` | ✅ |
| T2 factory soft stubs | 08-01 | 1 | `uv run pytest tests/test_detection_factory.py … -q` | ✅ |
| T3 serve factory wire | 08-01 | 1 | `uv run pytest tests/test_cli_serve.py … -q` | ✅ |
| T1 status/api honesty | 08-02 | 2 | `uv run pytest tests/test_backend_honesty_status.py … -q` | ✅ |
| T2 banner + footer | 08-02 | 2 | `uv run pytest tests/test_cli_serve.py tests/test_backend_honesty_status.py … -q` | ✅ |

- Every task has automated verify; Wave 0 tests named; no Jetson/E2E required.

### 9. Cross-Plan Data Contracts — PASS

- 08-01 authors `WorkerBuild{backend_requested, backend_live, backend_reason}`; 08-02 displays only (pass-through).
- Soft-stub policy shared: ORT/TRT → live=torch + fixed reason codes.
- Artifact resolve records existence but **does not** flip `backend_live` (no contract conflict with future live loaders).
- No strip/sanitize vs re-parse conflict.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root.

### 11. Research Resolution — PASS (formality warning)

RESEARCH `## Open Questions` has three items with recommendations; plans lock all three:

1. Soft stub + reason (not construct-time hard-fail) → 08-01 T2  
2. Optional StatusSnapshot fields; fill via app.state merge; no CaptureLoop backends → 08-02 T1  
3. Env+cache+CWD only (no required YAML detector_onnx/engine fields) → 08-01 T1 (A4)

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phases 1–7).

### 12. Pattern Compliance — PASS

PATTERNS.md File Classification covers factory, artifact_paths, cli serve, StatusSnapshot, routes_preview, create_app, tests.  
Plans cite PATTERNS + RESEARCH in `read_first`; shared patterns (factory plug-in, honesty, path allowlist, spine freeze) appear in both plan actions.

---

## Special checks (user-requested strict)

| Check | Result |
|-------|--------|
| Live ORT/TRT **not** smuggled into Phase 8 | **PASS** — soft stubs only; out-of-scope live sessions/engines; no onnx/tensorrt packages; artifact presence does not flip live |
| Honesty: never claim live TRT/ORT when torch | **PASS** — `backend_live=torch` + reason codes; unit asserts never live=ort/trt; status/UI pass-through only; banner structured fields replace export-target-only prose |
| DetectionLoop frozen | **PASS** — no edits to loop.py / FrameBus / PerceptionStore / routes_v1; serve keeps `DetectionLoop(bus, worker, store)` |
| Tests without Jetson | **PASS** — all verifies are pytest unit/inspect/TestClient; `model=` fakes; no weight download; no GPU ORT/TRT runtime required |
| Threat models present | **PASS** — both plans have STRIDE (T-08-01..05, T-08-10..14) |
| Deferred not smuggled | **PASS** — live ORT/TRT, sticky thrash, depth/OV backends, InferenceBackend Ort/Trt classes excluded |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Content status |
|------|------|-------|-------|--------------|----------------|
| 08-01 Factory + artifacts + serve wire | 1 | 3 | 7 | BACK-01, BACK-04, EDGE-RT-01..03 | Valid |
| 08-02 Status/banner/UI honesty | 2 | 2 | 9 | BACK-02, EDGE-RT-01, EDGE-RT-03 | Valid |

---

## Issues

### Blockers (must fix)

```yaml
issues:
  - plan: null
    dimension: nyquist_compliance
    severity: blocker
    description: "08-VALIDATION.md not found. Nyquist gate 8e requires a phase VALIDATION.md when workflow.nyquist_validation is enabled and RESEARCH has Validation Architecture. Prior v1.0 phases all shipped *-VALIDATION.md."
    fix_hint: "Author .planning/phases/08-backend-selection-honesty/08-VALIDATION.md from 08-RESEARCH.md ## Validation Architecture (and plan automated verifies). Include: test framework table; BACK-01/02/04 + EDGE-RT-01..03 → test map; Wave 0 checklist (test_artifact_paths.py, test_detection_factory.py, test_backend_honesty_status.py, update test_cli_serve.py); threats T-08-01..05 / T-08-10..14; sampling rules; no Jetson/no live ORT-TRT CI constraints. Plans themselves need not be rewritten if VALIDATION mirrors them."
```

### Warnings (should fix; non-blocking once VALIDATION lands)

```yaml
  - plan: null
    dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity."

  - plan: "08-02"
    dimension: key_links_planned
    severity: info
    description: "StatusSnapshot gains backend_* fields while api_status also merges from app.state — dual surface is intentional (schema honesty + CaptureLoop-free fill) but executor must not recompute live labels in the route."
    fix_hint: "Keep route as pass-through getattr only (already specified); do not set backend_live from preferred_backend strings."
```

---

## Recommendation

**PASS** — `08-VALIDATION.md` present; all dimensions green (non-blocking FLAGS only).

**Plan content ready for execute:** both PLANs achieve the Phase 8 goal, all mapped requirements, and honesty/spine/CI constraints. No live ORT/TRT smuggling; no false live TRT claims; DetectionLoop frozen; tests unit-only without Jetson.

**Orchestrator action:** Present to user as **ready to execute** (`/gsd:execute-phase 8`).

---

## PLAN CHECK PASS
