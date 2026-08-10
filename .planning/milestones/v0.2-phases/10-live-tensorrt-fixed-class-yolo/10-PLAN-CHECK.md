# Phase 10 Plan Check — Live TensorRT Fixed-Class YOLO

**Checked:** 2026-08-10  
**Plans:** `10-01-PLAN.md`, `10-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** RESEARCH, PATTERNS, VALIDATION, ROADMAP Phase 10, REQUIREMENTS TRT-01..04  
**CONTEXT.md:** none (discuss-phase not run; locked decisions from RESEARCH `user_constraints` + STATE/ROADMAP)

**Overall verdict:** **PASS** (hygiene flags only — no plan rewrite required)

---

## Phase goal (from ROADMAP)

> Jetson-class and NVIDIA desktop can run fixed-class YOLO live via TensorRT from an on-device `.engine` — no multi-SKU engines in the wheel, no pip `tensorrt` app dependency

**Success criteria (must be TRUE):**
1. With `preferred_backend=tensorrt` and a valid on-device `.engine`, fixed-class YOLO runs live via system/JetPack TensorRT
2. Docs require **on-device** engine build; project does not ship multi-SKU prebuilt engines in the wheel/repo
3. Jetson-class packaging notes cover JetPack/system TensorRT (no generic `tensorrt` pip pin as required app dep)
4. TRT path maps results into the same `Detection` contract; conf remains adjustable at runtime when supported

**Requirements:** TRT-01, TRT-02, TRT-03, TRT-04

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| TRT-01 | Live TRT when preferred + valid `.engine` + system TRT | 10-01 | T1 factory live branch + honesty matrix | Covered |
| TRT-02 | On-device build; no multi-SKU engines in wheel/repo | 10-02 | T1 docs lifecycle; T2 keyword tests | Covered |
| TRT-03 | JetPack/system TRT; no project pip pin | 10-02 | T1 jetson-packaging; T2 no-tensorrt extra | Covered |
| TRT-04 | Same Detection contract; conf when supported | 10-01 | T2 parity + conf goldens; T3 status live triple | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Live TRT only when path + dep OK | factory condition chain: resolve → dep probe → `YoloDetectionWorker(weights=engine)` | `backend_live=tensorrt` **only** on that path |
| Soft-fallback honesty (never silent TRT claim) | reasons `trt_artifact_missing` \| `trt_dep_missing` \| `path_rejected` → live=torch | Retires default `trt_loader_not_implemented` |
| Worker weights match live label | Live path uses `weights=str(path)` not `rt.detector_weights` | Unit assert `_weights.endswith(".engine")` when live=trt |
| Same Detection contract | Reuse `predict` + `results_to_detections`; schema default `source=fixed` | 10-01 T2 parity + mapping goldens |
| Runtime conf works on TRT path (when supported) | Same worker `set_conf` → predict conf kwarg; docs conf caveat | `test_trt_set_conf_applies_on_next_process` + 10-02 docs |
| No `tensorrt` pip extra | pyproject hygiene + static test | `test_no_tensorrt_optional_extra` stays green |
| On-device / never-copy / no multi-SKU engines | export + jetson packaging docs + keywords | TRT-02 keyword asserts |
| JetPack/system TRT packaging | `jetson-packaging.md` + keywords | TRT-03 |
| Status honesty for live TRT | pass-through live=tensorrt triple | 10-01 T3 |
| DetectionLoop / bus / store / `/v1` frozen | Explicit freeze; no production edits | Verify checklists in both plans |
| No Jetson / system TRT / real `.engine` in CI | `model=` inject + monkeypatch resolve/dep | RESEARCH / VALIDATION hardware policy |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- All four phase requirement IDs appear in plan frontmatter:
  - `10-01`: TRT-01, TRT-04
  - `10-02`: TRT-02, TRT-03
- Partition matches ROADMAP plan split (live Ultralytics-native TRT path vs on-device lifecycle + Jetson packaging).
- No phase-mapped REQUIREMENTS.md item orphaned.
- BACK-03 sticky thrash, dual-model first-class, depth/YOLOE TRT correctly **not** claimed (Phase 11 / deferred).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------------------|------|------------|---------------------|
| 10-01 | 3 | all | all | all pytest | all | all | all |
| 10-02 | 2 | all | all | all pytest | all | all | all |

`verify.plan-structure` **valid** for both plans; zero structural errors/warnings.  
Actions name concrete modules, reason codes, freeze constraints, forbid real `YOLO("*.engine")` / `check_tensorrt()` / top-level `import tensorrt`, and doc keyword surfaces. No shallow “align with” actions.

Both plans include `<threat_model>` with STRIDE register.

### 3. Dependency Correctness — PASS

```
10-01 (wave 1, depends_on: [])  →  10-02 (wave 2, depends_on: ["10-01"])
```

- Acyclic; wave = max(deps)+1 consistent (mirrors Phase 9 `09-01` → `09-02`).
- 10-02 correctly assumes live factory branch + reason codes from 10-01; docs must match factory behavior.
- No same-wave file conflicts (disjoint `files_modified`).

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| `build_detection_worker` TRT branch → `_try_resolve_artifact` / `resolve_detector_artifact` | 10-01 T1 |
| Live success → `YoloDetectionWorker(weights=str(engine_path), model=)` | 10-01 T1 |
| Live claim → `_tensorrt_available` / `find_spec` (no top-level import) | 10-01 T1 |
| `test_trt_parity` → factory live branch (resolve+dep monkeypatch + FakeModel) | 10-01 T2 |
| `YoloDetectionWorker.process` → `results_to_detections` (shared postprocess) | 10-01 T2 |
| Status honesty pass-through live=tensorrt | 10-01 T3 |
| Docs live TRT conditions → factory path (10-01) | 10-02 T1 |
| Docs on-device rules → `export_yolo.py --format engine` | 10-02 T1 |
| `test_no_tensorrt_optional_extra` → pyproject optional-dependencies | 10-02 T2 |

No isolated artifacts; status never recomputes live from preferred.

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 10-01 | 3 (target) | 4 | T1: factory + factory matrix |
| 10-02 | 2 (target) | 8 (within 5–8 target) | T1: 6 docs/config surfaces |

- Task counts within 2–3 target (no 4+ warning / 5+ blocker).
- File counts under warning threshold (10).
- Coherent split: code+parity vs docs+keywords (no pip packaging plan needed — TRT-03 is system-only).

### 6. Verification Derivation — PASS

must_haves truths are operator-observable (live only on path+dep, soft reasons, Detection fields, conf, on-device rules, no pip pin, no Jetson, spine freeze).  
Artifacts map to truths; key_links specify wiring methods (resolve, weights path, find_spec, FakeModel inject, keyword patterns).

### 7. Context Compliance — PASS (via RESEARCH locks; no CONTEXT.md)

| Locked decision (RESEARCH / STATE) | Plan coverage |
|------------------------------------|---------------|
| Ultralytics-native `YOLO("*.engine")` via worker weights | 10-01 T1; no custom Runtime/bindings/NMS |
| No `tensorrt` pip extra / system JetPack only | 10-01 no extra; 10-02 docs + static test |
| No multi-SKU prebuilt engines in wheel/repo | 10-02 TRT-02 docs + keywords |
| On-device engine build required | 10-02 lifecycle recipe |
| Soft torch fallback + reason codes | 10-01 T1 matrix |
| Factory sole author of `backend_live` | both plans; status pass-through only |
| Spine freeze (DetectionLoop / bus / store / `/v1`) | both plans; verify `rg` / freeze lists |
| Reuse `YoloDetectionWorker` (no TRT wrapper class) | 10-01 locked decisions |
| Dep probe `find_spec` only; never `check_tensorrt()` | 10-01 T1 acceptance + threat T-10-04 |
| Mock-only default CI | both plans; VALIDATION hardware policy |

Deferred excluded: sticky thrash (Phase 11), dual-model first-class (Phase 11), depth/YOLOE TRT, custom TRT decoder, prebuilt Releases engines, EDGE-DOC/CI polish (Phase 12).

Discretion handled: no factory CUDA probe; new `test_trt_parity.py`; no required real-engine integration test; JetPack matrix “verify on device”; live path not hard-coded to profile name `jetson`.

### 7b. Scope Reduction — PASS

No invented v1/static shadowing of locked decisions:

- Live TRT is full delivery when preferred + allowlisted `.engine` + system tensorrt available.
- Mock/FakeModel CI path is **locked EDGE-CI / RESEARCH strategy**, not a reduction of the live factory branch (real engine load is manual-only UAT — same class as Phase 9 ORT).
- Soft-fallback on missing artifact/dep is honesty lock, not omission of live path.
- Conf “when supported” matches TRT-04 wording + baked-NMS caveat (docs in 10-02).

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| TRT live loader selection | API/Backend (factory) | `factory.py` only |
| Artifact resolve | API/Backend (`artifact_paths`) | reuse; no reimplement |
| YOLO engine load + predict | API/Backend (`YoloDetectionWorker`) | weights path only |
| Detection mapping | API/Backend (`mapping`) | reuse; 10-01 T2 proves |
| Runtime conf | API/Backend (worker) | parity tests |
| `backend_live` honesty | API/Backend (factory sole author) | status pass-through |
| DetectionLoop / bus / store / `/v1` | Frozen | **no edits** |
| On-device engine build | Operator / docs | 10-02 |
| System / JetPack TensorRT | OS packaging + docs | 10-02 (no app pin) |

No security-sensitive selection or live-label authorship demoted to less-trusted tiers.

### 8. Nyquist Compliance — PASS

`workflow.nyquist_validation: true` in config.json. RESEARCH has `## Validation Architecture`.  
**Check 8e:** `10-VALIDATION.md` **present**.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 live factory + honesty matrix | 10-01 | 1 | `uv run pytest tests/test_detection_factory.py tests/test_artifact_paths.py -q` | ✅ |
| T2 TRT process/conf parity | 10-01 | 1 | `uv run pytest tests/test_trt_parity.py tests/test_detection_mapping.py tests/test_detection_worker.py -q` | ✅ |
| T3 status honesty + phase-01 gate | 10-01 | 1 | `uv run pytest tests/test_trt_parity.py tests/test_detection_factory.py tests/test_backend_honesty_status.py tests/test_detection_mapping.py -q` | ✅ |
| T1 docs honesty live TRT + lifecycle | 10-02 | 2 | `uv run pytest tests/test_export_docs.py tests/test_pyproject_onnx_extra.py -q` | ✅ |
| T2 keyword/static + phase suite gate | 10-02 | 2 | `uv run pytest tests/test_detection_factory.py tests/test_trt_parity.py tests/test_backend_honesty_status.py tests/test_export_docs.py tests/test_pyproject_onnx_extra.py tests/test_artifact_paths.py -q` | ✅ |

- Every task has `<automated>` verify; no `MISSING`; no watch-mode; no Jetson/system TensorRT/real `.engine` required.
- Wave 0 gaps from VALIDATION are implemented as TDD tasks inside plans (not a separate Wave 0 plan) — acceptable and complete (Phase 9 precedent).
- Sampling: Wave 1 3/3 automated; Wave 2 2/2 automated → ✅
- Feedback latency: quick set estimated ~30–90s — **WARNING** (borderline >30s); still unit/static pytest, not E2E.

### 9. Cross-Plan Data Contracts — PASS

- 10-01 authors live TRT `WorkerBuild` + reason vocabulary; 10-02 documents the same codes and live conditions.
- Soft-stub reasons stable: `trt_artifact_missing` / `trt_dep_missing` / `path_rejected`.
- Shared postprocess (`results_to_detections`) not duplicated or re-transformed.
- No strip/sanitize vs re-parse conflict on shared entities.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root. Plans follow Phase 8/9 conventions (TDD, factory sole author, spine freeze, mock-first CI).

### 11. Research Resolution — PASS (formality flag)

RESEARCH `## Open Questions` has five items with recommendations; plans lock all five:

1. CUDA probe at factory → **No** (10-01 discretion; `find_spec` only)  
2. Parity module location → new `tests/test_trt_parity.py` (10-01 T2)  
3. Opt-in real engine test → omit from default suite (10-01 T2)  
4. JetPack matrix depth → “verify on device”; no invented pins/FPS (10-02)  
5. Desktop preferred=tensorrt override → live path not hard-coded to `jetson` profile (10-01 T1)

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phase 9).

### 12. Pattern Compliance — PASS

PATTERNS.md File Classification covers factory, yolo_worker, mapping, jetson.yaml, export docs, architecture/configuration, factory tests, parity goldens, honesty status, export keywords, no-tensorrt extra.  
Plans cite PATTERNS + RESEARCH + VALIDATION in `read_first`; recommended live-TRT branch shape matches 10-01 T1 action 1:1 with ORT template.  
Shared patterns (factory sole author, Ultralytics-native, `model=` inject, spine freeze, reason codes, artifact allowlist, no pip tensorrt, mock-only CI) appear in plan actions.

New `tests/test_trt_parity.py` analog is exact: `tests/test_ort_parity.py`.

---

## Special checks (user-requested strict)

| Check | Result |
|-------|--------|
| TRT-01..04 each in some plan `requirements` | **PASS** — 01: TRT-01/04; 02: TRT-02/03 |
| Every task has `read_first` + `acceptance_criteria` | **PASS** — all 5 tasks |
| `threat_model` present | **PASS** — both plans (T-10-01..13 + SC) |
| Nyquist Dimension 8 / validation map | **PASS** — VALIDATION present; all tasks automated |
| No real Jetson dependency in CI tasks | **PASS** — mocks only; manual UAT table separate |
| No shallow “align with” actions | **PASS** — numbered concrete steps |
| Waves and dependencies correct | **PASS** — 01 wave1; 02 wave2 depends 10-01 |
| must_haves present | **PASS** — truths/artifacts/key_links both plans |
| Live TRT **only** when artifact + dep; honesty | **PASS** — condition chain order locked; never claim live TRT under `.pt` weights |
| No custom TRT decoder smuggled | **PASS** — Ultralytics-native only; Runtime/bindings out of scope |
| DetectionLoop frozen | **PASS** — no edits to loop/bus/store/v1 |
| No tensorrt pip extra | **PASS** — TRT-03 + static test + threat T-10-SC |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Content status |
|------|------|-------|-------|--------------|----------------|
| 10-01 Live Ultralytics-native TRT + parity + honesty | 1 | 3 | 4 | TRT-01, TRT-04 | Valid |
| 10-02 On-device lifecycle + Jetson packaging docs | 2 | 2 | 8 | TRT-02, TRT-03 | Valid |

---

## Structured Issues

```yaml
issues:
  - dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    plan: null
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity (optional hygiene)."

  - dimension: nyquist_compliance
    severity: warning
    description: "Quick validation set estimated ~30–90s (VALIDATION.md); exceeds 30s feedback-latency preference."
    plan: null
    fix_hint: "Acceptable for this suite size; prefer focused -k filters during task iteration if latency bites."

  - dimension: nyquist_compliance
    severity: info
    description: "10-VALIDATION.md frontmatter still has nyquist_compliant: false and wave_0_complete: false (pre-execution draft). Plans implement Wave 0 tests as TDD tasks."
    plan: null
    fix_hint: "After successful plan-check / execution start, set nyquist_compliant: true and wave_0_complete: true when Wave 0 checkboxes land."
```

**Blockers:** 0  
**Warnings:** 2  
**Info:** 1  

---

## Recommendation

Plans will achieve the Phase 10 goal. All TRT-01..04 requirements have concrete tasks, wiring, automated verifies without Jetson, and threat models. No plan rewrite required.

**Orchestrator action:** Present to user as **ready to execute** (`/gsd:execute-phase 10`). Optional hygiene: mark RESEARCH Open Questions resolved; flip VALIDATION nyquist flags when appropriate.
