# Phase 12 Plan Check — Docs, CI & Packaging Polish

**Checked:** 2026-08-10  
**Plans:** `12-01-PLAN.md`, `12-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** RESEARCH, PATTERNS, VALIDATION, ROADMAP Phase 12, REQUIREMENTS EDGE-DOC-01/02 + EDGE-CI-01/02  
**CONTEXT.md:** none (discuss-phase not run; locks from RESEARCH + ROADMAP)

**Overall verdict:** **PASS** (hygiene flags only — no plan rewrite required)

---

## Phase goal (from ROADMAP)

> Makers can follow export → engine/onnx → `sentry serve` on desktop/Jetson without fake FPS claims; contributors merge safely without Jetson hardware

**Success criteria (must be TRUE):**
1. Jetson/desktop edge serve docs cover export → engine/onnx → `sentry serve --profile …` (with or without UI)
2. AGPL Ultralytics remains documented for ORT/TRT artifacts derived from YOLO weights (`THIRD_PARTY_MODELS` lineage)
3. Unit tests cover backend selection, missing-artifact honesty, and factory wiring without NVIDIA Jetson in CI
4. Default GitHub Actions does not require Jetson or TensorRT GPU

**Requirements:** EDGE-DOC-01, EDGE-DOC-02, EDGE-CI-01, EDGE-CI-02

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| EDGE-DOC-01 | Export → onnx/engine → `sentry serve --profile …` (± UI) narrative | 12-01 | T1 keyword RED; T2 hub + split-brain fix | Covered |
| EDGE-DOC-02 | AGPL lineage for YOLO-derived `.onnx`/`.engine` | 12-01 | T1 keyword RED; T3 THIRD_PARTY lineage | Covered |
| EDGE-CI-01 | Selection / missing-artifact honesty / factory wiring without Jetson | 12-02 | T3 consolidated matrix gate (verify-only) | Covered |
| EDGE-CI-02 | Default GHA no Jetson / TensorRT GPU | 12-02 | T1 static lock RED; T2 gitignore + confirm ci.yml | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Numbered export → artifact → serve path discoverable | `docs/edge-serve.md` hub + root README link | T2 numbered steps 1–8; keyword lock in `test_edge_serve_docs.py` |
| Path works with and without UI | hub steps for `--no-ui` / headless + with-UI serve | keyword require `--no-ui` or headless |
| Split-brain hubs no longer claim non-live TRT | Fix README, desktop-gpu, scripts/export README, export index | forbid phrases keyword-tested |
| Live ORT/TRT conditions triad discoverable | README Export rewrite + edge hub links into `docs/export/*` | conditions table from export docs |
| No invented dual-model FPS | measure-on-device language; forbid “30 fps dual-model” | hub + export keyword tests |
| AGPL covers derived ORT/TRT artifacts | THIRD_PARTY “Derived ORT / TRT artifacts” section | `test_doc_agpl_lineage_for_derived_onnx_engine` |
| Backend selection matrix without Jetson | Existing factory suite (mock matrix) | 12-02 T3 verification command |
| Missing-artifact honesty soft+strict | Existing factory + honesty tests | same matrix gate |
| Factory wiring sticky | Existing sticky/serve call-site coverage | documented in test_edge_ci_workflow docstring |
| Default GHA Jetson/GPU-free | Static lock on `ci.yml` | `test_edge_ci_workflow.py` |
| Packaging hygiene | no tensorrt extra; force-include clean; `*.engine`/`*.onnx` gitignore | pyproject + gitignore tests |
| No runtime scope creep | Explicit out-of-scope both plans | factory/DetectionLoop/FrameBus/`/v1` frozen |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- All four phase requirement IDs appear in plan frontmatter:
  - `12-01`: EDGE-DOC-01, EDGE-DOC-02
  - `12-02`: EDGE-CI-01, EDGE-CI-02
- Partition matches ROADMAP plan split (docs/AGPL lineage vs CI/packaging matrix).
- No phase-mapped REQUIREMENTS.md item orphaned.
- Success criteria 1–4 each map to concrete tasks with measurable done criteria.
- Deferred correctly excluded: live ORT/TRT depth/OV, Jetson self-hosted GHA, factory rewrite, FPS tables, tensorrt pip extra, version bump 0.1.0→0.2.0.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------------------|------|------------|---------------------|
| 12-01 | 3 | all | all | all pytest | all | all | all |
| 12-02 | 3 | all | all | all pytest | all | all | all |

`verify.plan-structure` **valid** for both plans; zero structural errors/warnings.  
Actions are concrete and non-shallow: numbered doc surfaces, exact forbid/require phrases, TDD RED→GREEN sequence, living matrix table, packaging assert shapes from PATTERNS.  
Both plans include `<threat_model>` with STRIDE register (T-12-01..05 + SC on 01; T-12-06..10 + SC on 02).

### 3. Dependency Correctness — PASS

```
12-01 (wave 1, depends_on: [])  ‖  12-02 (wave 1, depends_on: [])
```

- Acyclic; both wave 1 with empty depends_on → parallel OK.
- **Zero file overlap** between plans (docs/AGPL vs CI/packaging tests/config) — concurrent execution safe.
- Research lock: “Parallelism — Zero file overlap with 12-01 — may run same wave” honored.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| README → `docs/edge-serve.md` (docs table + Export section) | 12-01 T2 |
| `edge-serve.md` → export recipes + `sentry serve --profile` numbered path | 12-01 T2 |
| THIRD_PARTY → derived `.onnx`/`.engine` AGPL caution | 12-01 T3 |
| Keyword tests → hub surfaces (forbid stale / require discoverability) | 12-01 T1 |
| `test_edge_ci_workflow.py` → `.github/workflows/ci.yml` static asserts | 12-02 T1 |
| `test_pyproject_onnx_extra.py` → hatch force-include + no tensorrt extra | 12-02 T1 |
| EDGE-CI-01 gate → factory/honesty/artifact/parity suites | 12-02 T3 |
| `.gitignore` → `*.engine`/`*.onnx` + static test | 12-02 T2 |

No isolated artifacts; docs discoverability and CI locks are wired end-to-end.

### 5. Scope Sanity — PASS (borderline warning on 12-01 files)

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 12-01 | 3 (target) | 12 (warning threshold 10) | T2 multi-hub honesty rewrite |
| 12-02 | 3 (target) | 4 (within target) | T1 static locks + T3 matrix gate |

- Task counts within 2–3 target (no 4+ warning / 5+ blocker).
- 12-01 file count elevated because split-brain fix must touch all hub surfaces (README, desktop-gpu, export index, scripts/export, docs index, edge hub, CHANGELOG) plus four test modules — coherent docs domain, not crammed runtime work.
- Coherent split: DOC-01/02 (01) vs CI-01/02 + packaging (02).

### 6. Verification Derivation — PASS

must_haves truths are maker/contributor-observable:
- Followable numbered export→serve path
- Stale non-live TRT language gone from hubs
- AGPL lineage for derived artifacts
- GHA stays ubuntu-latest + dev-only
- Selection/honesty matrix proven without Jetson

Artifacts map to truths; key_links specify Path.read_text / tomllib / pytest suite methods.

### 7. Context Compliance — PASS (via RESEARCH locks; no CONTEXT.md)

| Locked decision (RESEARCH) | Plan coverage |
|----------------------------|---------------|
| Fix split-brain root/desktop/scripts hubs | 12-01 T2 |
| Prefer thin `docs/edge-serve.md` hub | 12-01 T2 creates hub |
| AGPL derived lineage policy (not legal cert) | 12-01 T3 |
| No fake dual-model FPS | 12-01 keywords + hub step 8 |
| No new packages / no factory rewrite | both plans out-of-scope |
| CHANGELOG Unreleased only; no version bump | 12-01 T2/T3 |
| EDGE-CI-01 verify-only existing matrix | 12-02 T3 |
| EDGE-CI-02 static lock + packaging hygiene | 12-02 T1–T2 |
| Parallel plans OK (no file overlap) | both wave 1 |

Deferred excluded: Jetson self-hosted GHA, real engine loads in CI, DetectionLoop redesign, FPS benchmarks, tensorrt pip extra, live ORT/TRT depth/OV.

### 7b. Scope Reduction — PASS

No invented v1/static shadowing of requirements:

- EDGE-DOC-01 is full numbered e2e path (not “link only / static for now”).
- EDGE-DOC-02 is full derived-artifact lineage section (not weight-row only).
- EDGE-CI-01 verify-only is correct — research confirms matrix already green; requirement is “unit tests cover,” not “rewrite factory.”
- EDGE-CI-02 locks existing compliant workflow with static tests (full requirement).
- Packaging gitignore + force-include are complete hygiene, not placeholders.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| End-to-end edge serve narrative | Docs | `docs/edge-serve.md` + hub fixes |
| AGPL / THIRD_PARTY lineage | Docs + keyword tests | THIRD_PARTY + `test_third_party_models_doc.py` |
| Backend selection / honesty | Unit tests (pytest) | factory/honesty matrix gate (verify) |
| GHA without Jetson/TRT GPU | CI workflow + static tests | `test_edge_ci_workflow.py` |
| Packaging hygiene | pyproject / hatch + tests | force-include + no tensorrt extra |
| Live ORT/TRT inference | API/Backend (already shipped) | **out of scope** — docs match factory |

No security-sensitive capability demoted to a less-trusted tier.

### 8. Nyquist Compliance — PASS

`workflow.nyquist_validation: true` in config.json. RESEARCH has `## Validation Architecture`.  
**Check 8e:** `12-VALIDATION.md` **present**.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 Wave 0 RED keyword tests | 12-01 | 1 | `uv run pytest tests/test_export_docs.py tests/test_desktop_docs.py tests/test_third_party_models_doc.py tests/test_edge_serve_docs.py -q --tb=line` | ✅ |
| T2 Edge hub + split-brain honesty | 12-01 | 1 | `uv run pytest tests/test_export_docs.py tests/test_desktop_docs.py tests/test_edge_serve_docs.py -q --tb=short` | ✅ |
| T3 AGPL lineage + suite green | 12-01 | 1 | `uv run pytest tests/test_third_party_models_doc.py tests/test_export_docs.py tests/test_desktop_docs.py tests/test_edge_serve_docs.py -q --tb=short` | ✅ |
| T1 Wave 0 RED CI/packaging locks | 12-02 | 1 | `uv run pytest tests/test_edge_ci_workflow.py tests/test_pyproject_onnx_extra.py -q --tb=short` | ✅ |
| T2 gitignore + CI content lock | 12-02 | 1 | `uv run pytest tests/test_edge_ci_workflow.py tests/test_pyproject_onnx_extra.py -q --tb=short` | ✅ |
| T3 EDGE-CI-01 matrix gate | 12-02 | 1 | `uv run pytest tests/test_detection_factory.py tests/test_backend_honesty_status.py tests/test_artifact_paths.py tests/test_ort_parity.py tests/test_trt_parity.py tests/test_edge_rt04_torch_only.py tests/test_edge_ci_workflow.py tests/test_pyproject_onnx_extra.py -q --tb=short` | ✅ |

- Every task has `<automated>` verify; no `MISSING`; no watch-mode; no Jetson/real engines required.
- Wave 0 gaps from VALIDATION are implemented as TDD Task 1 inside each plan (Phase 9–11 precedent) — acceptable.
- Sampling: Wave 1 (both plans) 6/6 automated → ✅
- Feedback latency: unit/static pytest — ✅ (no E2E suite as primary gate)

### 9. Cross-Plan Data Contracts — PASS

- No shared mutable data pipeline between 12-01 (docs/keywords) and 12-02 (CI/packaging static).
- Disjoint file sets; no strip/sanitize vs re-parse conflict.
- Both plans freeze factory reason codes and runtime — no contract drift risk.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root. Plans follow Phase 8–11 conventions (TDD keyword/static tests, spine freeze, mock-first CI, no new packages, no tensorrt pip extra).

### 11. Research Resolution — PASS (formality flag)

RESEARCH `## Open Questions` has three items with recommendations; plans lock all three:

1. Dedicated `docs/edge-serve.md` vs expand-only → **thin hub created** (12-01 T2)  
2. CHANGELOG Unreleased / version bump → **Unreleased notes; no 0.1.0→0.2.0 bump** (12-01 T2/T3)  
3. Manual Jetson checklist ownership → **on-device validation checklist in edge hub** (12-01 T2)

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phase 9–11).

### 12. Pattern Compliance — PASS

PATTERNS.md File Classification covers all planned touch files (README, desktop-gpu, edge-serve, export README, scripts/export README, docs README, THIRD_PARTY, CHANGELOG, four doc test modules, test_edge_ci_workflow, pyproject packaging tests, gitignore, ci.yml).  
Plans cite PATTERNS + RESEARCH + VALIDATION in `read_first`; forbid/require phrases and module shapes match PATTERNS 1:1.  
Shared patterns (keyword honesty, numbered e2e hub, live ORT/TRT triad, AGPL policy tone, static CI/packaging gates, TDD RED→GREEN, no runtime creep) appear in plan actions.

---

## Special checks (user-requested strict)

| Check | Result |
|-------|--------|
| EDGE-DOC-01/02 + EDGE-CI-01/02 each in some plan `requirements` | **PASS** — 01: DOC; 02: CI |
| Every task has `read_first` + `acceptance_criteria` | **PASS** — all 6 tasks |
| `threat_model` present | **PASS** — both plans |
| Nyquist Dimension 8 / validation map | **PASS** — VALIDATION present; all tasks automated |
| Waves (parallel OK) | **PASS** — both wave 1, empty depends_on, zero file overlap |
| must_haves present | **PASS** — truths/artifacts/key_links both plans |
| No shallow actions | **PASS** — concrete numbered steps, exact phrases, TDD sequence |
| Export→serve ± UI narrative | **PASS** — hub steps include `--profile` and `--no-ui`/headless |
| AGPL derived `.onnx`/`.engine` | **PASS** — THIRD_PARTY section + keyword test |
| CI matrix without Jetson | **PASS** — factory/honesty/parity gate verify-only |
| GHA no Jetson/TRT GPU locked | **PASS** — static workflow tests |
| No dual-model FPS invention | **PASS** — measure-on-device + keyword forbid |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Content status |
|------|------|-------|-------|--------------|----------------|
| 12-01 Edge serve docs + AGPL lineage | 1 | 3 | 12 | EDGE-DOC-01, EDGE-DOC-02 | Valid |
| 12-02 CI + packaging locks | 1 | 3 | 4 | EDGE-CI-01, EDGE-CI-02 | Valid |

---

## Structured Issues

```yaml
issues:
  - dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    plan: null
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity (optional hygiene)."

  - dimension: scope_sanity
    severity: warning
    description: "Plan 12-01 lists 12 files_modified (warning threshold 10) because split-brain honesty must touch all hub surfaces + keyword test modules."
    plan: "12-01"
    metrics:
      tasks: 3
      files: 12
    fix_hint: "Acceptable for multi-hub docs honesty; do not split mid-narrative. No rewrite required."

  - dimension: nyquist_compliance
    severity: info
    description: "12-VALIDATION.md frontmatter still has nyquist_compliant: false and wave_0_complete: false (pre-execution draft). Plans implement Wave 0 tests as TDD Task 1."
    plan: null
    fix_hint: "After execution starts / Wave 0 checkboxes land, set nyquist_compliant: true and wave_0_complete: true."

  - dimension: verification_derivation
    severity: info
    description: "12-VALIDATION.md quick-run / per-task map is coarser than plan-level automated commands (does not list test_edge_serve_docs.py or full EDGE-CI-01 suite explicitly in every row)."
    plan: null
    fix_hint: "Optional: refresh VALIDATION per-task map to match plan verify blocks after Wave 0 lands."
```

**Blockers:** 0  
**Warnings:** 2  
**Info:** 2  

---

## Recommendation

Plans will achieve the Phase 12 goal. EDGE-DOC-01/02 and EDGE-CI-01/02 have concrete tasks, wiring, automated verifies without Jetson, threat models, and no scope reduction of roadmap requirements. Parallel wave-1 execution is safe (disjoint files). No plan rewrite required.

**Orchestrator action:** Present to user as **ready to execute** (`/gsd:execute-phase 12`). Optional hygiene: mark RESEARCH Open Questions resolved; flip VALIDATION nyquist flags when appropriate.
