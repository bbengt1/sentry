# Phase 9 Plan Check — Live ORT Fixed-Class YOLO

**Checked:** 2026-08-09  
**Plans:** `09-01-PLAN.md`, `09-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** CONTEXT, RESEARCH, PATTERNS, VALIDATION, ROADMAP Phase 9, REQUIREMENTS ORT-01..04  

**Overall verdict:** **PASS_WITH_FLAGS**

---

## Phase goal (from ROADMAP)

> Makers can run fixed-class YOLO live via ONNX Runtime when the profile prefers `onnxruntime` and a valid `.onnx` artifact is present — same Detection wire contract as PyTorch

**Success criteria (must be TRUE):**
1. With `preferred_backend=onnxruntime` and a valid `.onnx` artifact + optional `onnx` extra, fixed-class YOLO runs live (not torch-only under an ORT label)
2. ORT path produces the same `Detection` wire contract (class, conf, bbox_xyxy, source=fixed) as the PyTorch path
3. Optional `onnx` (or equivalent) extra is documented for install; CI does not require GPU ORT
4. Golden/parity tests (mock session or fixture) prove postprocess mapping without Jetson hardware

**Requirements:** ORT-01, ORT-02, ORT-03, ORT-04

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| ORT-01 | Live ORT when preferred + valid `.onnx` (+ dep) | 09-01 | T1 factory live branch + honesty matrix | Covered |
| ORT-02 | Same Detection wire contract as torch | 09-02 | T1 process parity + conf golden | Covered |
| ORT-03 | Optional `onnx` extra documented; CI no GPU ORT | 09-01 | T2 pin + T3 docs honesty | Covered |
| ORT-04 | Golden/parity without Jetson | 09-02 | T1 FakeModel parity; T2 status fixture | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Live ORT only when path + dep OK | factory condition chain: resolve → dep probe → `YoloDetectionWorker(weights=onnx)` | `backend_live=onnxruntime` **only** on that path |
| Soft-fallback honesty (never silent ORT claim) | reasons `ort_artifact_missing` \| `ort_dep_missing` \| `path_rejected` → live=torch | Retires default `ort_loader_not_implemented` |
| Worker weights match live label | Live path uses `weights=str(path)` not `rt.detector_weights` | Unit assert `_weights.endswith(".onnx")` when live=ort |
| Same Detection contract | Reuse `predict` + `results_to_detections`; schema default `source=fixed` | 09-02 parity + existing mapping goldens |
| Runtime conf works on ORT path | Same worker `set_conf` → predict conf kwarg | `test_ort_set_conf_applies_on_next_process` |
| Optional `onnx` extra | `pyproject.toml` pin `onnxruntime>=1.20,<1.29` | Static `test_pyproject_onnx_extra.py` |
| Docs honesty (not export-only) | export/architecture/configuration + cpu-fallback comment | Keyword tests in `test_export_docs.py` |
| No custom ORT decoder | Ultralytics-native only; forbid `InferenceSession` | Out of scope + phase `rg` gate |
| DetectionLoop / bus / store / `/v1` frozen | Explicit freeze; no production edits | Verify checklists in both plans |
| No Jetson / GPU ORT in CI | `model=` inject + monkeypatch resolve/dep | ORT-03/04 suite policy |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- All four phase requirement IDs appear in plan frontmatter:
  - `09-01`: ORT-01, ORT-03
  - `09-02`: ORT-02, ORT-04
- Partition matches ROADMAP plan split (live path + packaging/docs vs parity/golden).
- No phase-mapped REQUIREMENTS.md item orphaned.
- TRT-*, sticky thrash, depth/YOLOE ORT correctly **not** claimed (later/deferred).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done |
|------|-------|-------|--------|--------------------|------|
| 09-01 | 3 | all | all | all pytest | all |
| 09-02 | 2 | all | all | all pytest | all |

`verify.plan-structure` **valid** for both plans; zero structural errors/warnings.  
Actions name concrete modules, reason codes, pin string, freeze constraints, and forbid real `YOLO("*.onnx")` in default CI.

### 3. Dependency Correctness — PASS

```
09-01 (wave 1, depends_on: [])  →  09-02 (wave 2, depends_on: ["09-01"])
```

- Acyclic; wave = max(deps)+1 consistent.
- 09-02 correctly assumes live factory branch + soft reason codes from 09-01.
- No same-wave file conflicts.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| `build_detection_worker` ORT branch → `_try_resolve_artifact` / `resolve_detector_artifact` | 09-01 T1 |
| Live success → `YoloDetectionWorker(weights=str(onnx_path), model=)` | 09-01 T1 |
| Live claim → `_onnxruntime_available` / `find_spec` (no top-level import) | 09-01 T1 |
| `onnx` extra → docs install (`uv sync --extra detect --extra onnx`) | 09-01 T2–T3 |
| `test_ort_parity` → factory live branch (resolve+dep monkeypatch + FakeModel) | 09-02 T1 |
| `YoloDetectionWorker.process` → `results_to_detections` (shared postprocess) | 09-02 T1 |
| Status honesty pass-through live=onnxruntime | 09-02 T2 |

No isolated artifacts; status never recomputes live from preferred.

### 5. Scope Sanity — PASS (flag)

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 09-01 | 3 (target) | **10** (warning threshold) | T3: 5 docs/config + export tests |
| 09-02 | 2 (target) | 2 | T1: new parity module only |

- Task counts within 2–3 target.
- Plan 01 file count sits at the warning line (10) but is coherently split across factory / packaging / docs — no split required for quality.

### 6. Verification Derivation — PASS

must_haves truths are operator-observable (live only on path+dep, soft reasons, Detection fields, conf, no Jetson, spine freeze).  
Artifacts map to truths; key_links specify wiring methods (resolve, weights path, find_spec, FakeModel inject).

### 7. Context Compliance — PASS

| Locked decision | Plan coverage |
|-----------------|---------------|
| Ultralytics-native `YOLO("*.onnx")` via worker weights | 09-01 T1; no custom session |
| Optional `onnx` extra pin `>=1.20,<1.29` | 09-01 T2 |
| No `tensorrt` pip extra | 09-01 T2 asserts + out of scope |
| Factory sole author of `backend_live` | both plans; status pass-through only |
| Spine freeze (DetectionLoop / bus / store / `/v1`) | both plans; verify `rg` / git diff |
| Artifact resolve via existing `resolve_detector_artifact` + `SENTRY_DETECTOR_ONNX` | 09-01 T1 |

Deferred excluded: live TRT, sticky thrash-free modes, onnxruntime-gpu exclusive extra, YOLOE ORT.

Discretion handled: reuse `YoloDetectionWorker`; `find_spec` dep probe; `ort_dep_missing` / `ort_artifact_missing`; FakeModel golden strategy; no thin ORT wrapper class.

### 7b. Scope Reduction — PASS

No invented v1/static shadowing of locked decisions:

- Live ORT is full delivery when preferred + allowlisted `.onnx` + dep available.
- Mock/FakeModel CI path is **ORT-04 locked strategy**, not a reduction of the live factory branch.
- Soft-fallback on missing artifact/dep is CONTEXT honesty lock, not omission of live path.
- Lazy load (no eager corrupt-`.onnx` validation) matches torch and RESEARCH A2 — not a cut of ORT-01.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| ORT live loader selection | API/Backend (factory) | `factory.py` only |
| Artifact resolve | API/Backend (`artifact_paths`) | reuse; no reimplement |
| YOLO onnx load + predict | API/Backend (`YoloDetectionWorker`) | weights path only |
| Detection mapping | API/Backend (`mapping`) | reuse; 09-02 proves |
| Runtime conf | API/Backend (worker) | parity tests |
| `backend_live` honesty | API/Backend (factory sole author) | status pass-through |
| DetectionLoop / bus / store / `/v1` | Frozen | **no edits** |
| Optional `onnx` packaging | Packaging + docs | pyproject + export docs |

No security-sensitive selection or live-label authorship demoted to less-trusted tiers.

### 8. Nyquist Compliance — PASS

`workflow.nyquist_validation: true` in config.json. RESEARCH has `## Validation Architecture`.

**Check 8e:** `09-VALIDATION.md` **present**.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 live factory + honesty matrix | 09-01 | 1 | `uv run pytest tests/test_detection_factory.py tests/test_artifact_paths.py -q` | ✅ |
| T2 onnx extra pin | 09-01 | 1 | `uv run pytest tests/test_pyproject_onnx_extra.py -q` | ✅ |
| T3 docs honesty | 09-01 | 1 | `uv run pytest tests/test_export_docs.py tests/test_pyproject_onnx_extra.py tests/test_detection_factory.py -q` | ✅ |
| T1 ORT process/conf parity | 09-02 | 2 | `uv run pytest tests/test_ort_parity.py tests/test_detection_mapping.py tests/test_detection_worker.py -q` | ✅ |
| T2 status honesty + phase gate | 09-02 | 2 | `uv run pytest tests/test_ort_parity.py tests/test_detection_factory.py tests/test_backend_honesty_status.py tests/test_detection_mapping.py tests/test_export_docs.py tests/test_pyproject_onnx_extra.py -q` | ✅ |

- Every task has `<automated>` verify; no watch-mode; no Jetson/E2E required.
- Wave 0 gaps from VALIDATION are implemented as TDD tasks inside plans (not a separate Wave 0 plan) — acceptable and complete.
- Sampling: Wave 1 3/3 automated; Wave 2 2/2 automated → ✅

### 9. Cross-Plan Data Contracts — PASS

- 09-01 authors live ORT `WorkerBuild` + reason vocabulary; 09-02 consumes the same helpers (`_try_resolve_artifact`, `_onnxruntime_available`) and asserts `backend_live=="onnxruntime"` before process checks.
- Soft-stub reasons stable across plans: `ort_artifact_missing` / `ort_dep_missing` / `path_rejected`.
- Shared postprocess (`results_to_detections`) not duplicated or re-transformed.
- No strip/sanitize vs re-parse conflict.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root. Plans follow Phase 8 conventions (TDD, factory sole author, spine freeze).

### 11. Research Resolution — PASS (formality flag)

RESEARCH `## Open Questions` has three items with recommendations; plans lock all three:

1. Eager vs lazy ORT load → stay lazy (09-01 out of scope: no eager corrupt validation)  
2. `model=` injection requires path+dep for live claim → 09-01 T1 + 09-02 monkeypatch resolve  
3. cpu-fallback comment still export-only → 09-01 T3 updates profile YAML comment  

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phase 8).

### 12. Pattern Compliance — PASS

PATTERNS.md File Classification covers factory, yolo_worker, mapping, pyproject extras, export docs, factory tests, parity goldens, export keyword tests.  
Plans cite PATTERNS + RESEARCH in `read_first`; recommended live-branch shape matches 09-01 T1 action.  
Shared patterns (factory sole author, Ultralytics-native, `model=` inject, spine freeze, reason codes, artifact allowlist) appear in plan actions.

New `tests/test_pyproject_onnx_extra.py` is a thin static pin test (Wave 0 optional in RESEARCH) — no analog gap that blocks execution.

---

## Special checks (user-requested strict)

| Check | Result |
|-------|--------|
| Live ORT **only** when artifact + dep; honesty | **PASS** — condition chain order locked; never claim live ORT under `.pt` weights; soft reasons for missing artifact/dep/path_rejected |
| No custom ORT decoder smuggled as required | **PASS** — Ultralytics-native only; InferenceSession/hand decoder out of scope; phase verification `rg` forbids custom session |
| DetectionLoop frozen | **PASS** — no edits to `loop.py` / FrameBus / PerceptionStore / `routes_v1`; both plans freeze + verify |
| No Jetson in CI | **PASS** — FakeModel inject; mock resolve/dep; no GPU ORT extra; no real `YOLO("*.onnx")` default suite |
| VALIDATION.md present | **PASS** — `09-VALIDATION.md` present with ORT-01..04 dimension map + reason-code contract |
| Deferred not smuggled | **PASS** — live TRT stays soft-stub; sticky thrash Phase 11; no YOLOE ORT; no tensorrt extra |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Content status |
|------|------|-------|-------|--------------|----------------|
| 09-01 Live factory ORT + onnx extra + docs | 1 | 3 | 10 | ORT-01, ORT-03 | Valid |
| 09-02 Detection parity / golden (mocks) | 2 | 2 | 2 | ORT-02, ORT-04 | Valid |

---

## Issues

### Blockers (must fix)

```yaml
issues: []
```

### Warnings (should fix; non-blocking)

```yaml
issues:
  - plan: null
    dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity (optional hygiene)."

  - plan: "09-01"
    dimension: scope_sanity
    severity: warning
    description: "Plan 09-01 lists 10 files_modified (warning threshold). Task split is coherent (factory / packaging / docs) so no mandatory replan."
    fix_hint: "Optional: if executor context pressure appears, split docs task into a 09-03 — not required before execute."

  - plan: null
    dimension: verification_derivation
    severity: info
    description: "09-VALIDATION.md frontmatter still has nyquist_compliant: false and wave_0_complete: false (pre-execution draft). Plans implement Wave 0 tests as TDD tasks."
    fix_hint: "After execute/verify, flip VALIDATION flags when ORT-01..04 rows are green."
```

---

## Recommendation

**PASS_WITH_FLAGS** — no blockers. Plans will achieve Phase 9 goal and ORT-01..04 if executed as written.

**Strict invariants held:**
- Live ORT only on artifact + dep success with `.onnx` worker weights
- Soft-fallback honesty (never silent ORT claim)
- No custom ORT decoder required or smuggled
- DetectionLoop / bus / store / `/v1` frozen
- CI free of Jetson / GPU ORT / real onnx load
- `09-VALIDATION.md` present and mapped

**Orchestrator action:** Present to user as **ready to execute** (`/gsd:execute-phase 9`). Optional hygiene: mark RESEARCH Open Questions resolved; no plan rewrite required.

---

## PLAN CHECK PASS_WITH_FLAGS
