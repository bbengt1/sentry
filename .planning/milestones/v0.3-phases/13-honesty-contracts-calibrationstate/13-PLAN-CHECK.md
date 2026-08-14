# Phase 13 Plan Check — Honesty Contracts & CalibrationState

**Checked:** 2026-08-11 (re-verify after acceptance_criteria revision)  
**Plans:** `13-01-PLAN.md`, `13-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** ROADMAP Phase 13, REQUIREMENTS CAL-04/CAL-05, RESEARCH, PATTERNS, VALIDATION, both PLAN.md files, prior 13-PLAN-CHECK  
**CONTEXT.md:** none (locked decisions taken from ROADMAP + RESEARCH)

**Overall verdict:** **PASS** — prior blocker (missing `<acceptance_criteria>`) resolved on all 4 tasks

---

## Phase goal (from ROADMAP)

> Depth honesty contracts and an in-process CalibrationState make `metric_calibrated` + meters reachable only when applied and valid — relative depth can never claim meters

**Success criteria (must be TRUE):**
1. Relative (and uncalibrated) depth products reject or never emit `unit="m"` on store / snapshot / `/v1` contracts (validators + tests)
2. `CalibrationState` distinguishes draft vs applied; draft/staging alone does not report as calibrated
3. Promotion policy is explicit: only applied + valid calibration yields the pair `depth_kind=metric_calibrated` and `unit="m"` together
4. Calibration params include fingerprint fields (camera_id, resolution/size, depth mode/model) designed for later persist safety

**Requirements:** CAL-04, CAL-05

---

## Prior issues disposition

| Prior issue | Severity | Disposition |
|-------------|----------|-------------|
| All 4 tasks missing `<acceptance_criteria>` | blocker ×4 | **FIXED** — each task now has criteria (12/8/7/11 items) derived from `<behavior>` |
| RESEARCH Open Questions not marked (RESOLVED) | warning | **RETAINED** — formality only; plans lock all 5 answers |
| VALIDATION `wave_0_complete: false` | info | **RETAINED** — expected pre-execution |

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| CAL-04 | Applied+valid → pair; fingerprint; promote gate | 13-01, 13-02 | 01-T1 promote + calibrated-requires-m; 02-T1 fingerprint; 02-T2 promote wrapper | Covered |
| CAL-05 | Relative/uncalibrated never claim meters on store/snapshot/v1 | 13-01, 13-02 | 01-T1 wire matrix; 01-T2 store gate; 02-T2 draft never promotes | Covered |
| SC1 store/snapshot/v1 honesty | validators + tests | 13-01 | Wire + store + regression | Covered |
| SC2 draft vs applied | CalibrationState | 13-02 | T2 state machine | Covered |
| SC3 promote only applied+valid | pure + wrapper | 13-01 T1, 13-02 T2 | Covered |
| SC4 fingerprint fields | params schema | 13-02 T1 | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Relative forbids unit on wire | `assert_depth_kind_unit` + DepthPayload validator | model_validator → shared assert |
| Calibrated requires unit=`"m"` | same assert + depth_kind tests | CAL-04 pair on wire/store |
| Free-space meters only when calibrated | `assert_free_space_units` + FreeSpacePayload validator | forbid relative/estimated + `units="m"` |
| Store rejects dishonest pairs | `set_depth` → `assert_depth_kind_unit` before product write | no partial write |
| Mode never calibrated | test guard only; mapping.py production unchanged | `kind_for_mode` never METRIC_CALIBRATED |
| Draft ≠ applied / never promotes | CalibrationState draft vs applied fields | promote uses applied+valid only |
| Applied+valid → pair | pure `promote_kind_unit` + state wrapper | 13-01 ships pure; 13-02 wraps |
| Fingerprint for later persist | CalibrationFingerprint on params | camera_id, size, mode, model_id, schema_version |
| No fit / DepthLoop / wizard / YAML | explicit out-of-scope + threat model | Phase 14–17 handoff docstring only |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- CAL-04 and CAL-05 appear in both plans' `requirements` frontmatter.
- Partition matches ROADMAP plan split (honesty contracts → CalibrationState).
- No phase-mapped REQUIREMENTS.md item orphaned.
- CAL-01/02/03, WIZ-*, FS-*, persist correctly **not** claimed (later phases).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------------------|------|------------|---------------------|
| 13-01 | 2 | all | all | all pytest | all | all | **all present** (T1: 12 items, T2: 8 items) |
| 13-02 | 2 | all | all | all pytest | all | all | **all present** (T1: 7 items, T2: 11 items) |

`verify.plan-structure` returns **valid** for both plans.  

Criteria are lifted from each task's `<behavior>` (1:1 item match) — measurable honesty/state outcomes that the automated pytest verify commands exercise. Project plan-phase contract (`read_first` + `acceptance_criteria`) satisfied on all 4 tasks.

Both plans include `<threat_model>` with STRIDE registers (T-13-01..05 + SC on 01; T-13-06..10 + SC on 02).

### 3. Dependency Correctness — PASS

```
13-01 (wave 1, depends_on: [])  →  13-02 (wave 2, depends_on: ["13-01"])
```

- Acyclic; wave consistent with deps.
- Shared contract: pure `promote_kind_unit` from 01 consumed by 02 wrapper — no forward dep from 01 into CalibrationState.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| DepthPayload → `assert_depth_kind_unit` | 13-01 T1 |
| FreeSpacePayload → `assert_free_space_units` | 13-01 T1 |
| PerceptionStore.set_depth → `assert_depth_kind_unit` | 13-01 T2 |
| pure `promote_kind_unit` → CalibrationState wrapper | 13-01 → 13-02 |
| CalibrationState.promote → validators.promote | 13-02 T2 |
| apply → `is_valid_calibration_params` | 13-02 T2 |
| CalibrationParams.fingerprint → CalibrationFingerprint | 13-02 T1 |

No isolated artifacts; promotion path fully wired across plans.

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 13-01 | 2 (target) | 7 | T1: validators + perception + 2 test modules |
| 13-02 | 2 (target) | 5 | T2: CalibrationState + exports + full state tests |

Within 2–3 tasks/plan and under file thresholds. Clean split: contracts (01) then state machine (02).

### 6. Verification Derivation — PASS

must_haves truths are product-observable (wire reject, store reject, draft never calibrated, promote pair, fingerprint present).  
Artifacts map to truths; key_links specify wiring methods.

### 7. Context Compliance — PASS (no CONTEXT.md)

Locked decisions sourced from ROADMAP + RESEARCH and honored in both plans:

| Locked decision | Plan coverage |
|-----------------|---------------|
| Kind↔unit full matrix | 13-01 T1 |
| Free-space m only when calibrated; calibrated+ordinal allowed | 13-01 T1 |
| Store gate at set_depth | 13-01 T2 |
| kind_for_mode never calibrated | 13-01 T2 (test-only) |
| promote pure API | 13-01 T1 |
| CalibrationState draft vs applied + fingerprint | 13-02 |
| Zero new pip deps | both |
| No DepthLoop / wizard / free-space algorithm / YAML | both out-of-scope |

### 7b. Scope Reduction — PASS

No invented v1/v2, “static for now,” or “wire later” that drops a locked Phase 13 deliverable.  
Residual RMS / apply_map / AppState injection deferred **explicitly** to later phases per RESEARCH — not silent reduction of CAL-04/05.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Kind/unit validators | API/Backend (schemas) | validators.py + perception.py |
| Store honesty gate | Database/Storage (PerceptionStore) | set_depth assert |
| Promotion policy | API/Backend (policy helpers) | pure promote + state wrap |
| CalibrationState draft/applied | API/Backend (control plane) | control/calibration_state.py |
| Fingerprint fields | API/Backend (params schema) | schemas/calibration.py |
| DepthLoop apply / wizard / free-space meters / YAML | out of phase | correctly excluded |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists (`13-VALIDATION.md`). Nyquist enabled in config.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 validators + wire | 13-01 | 1 | `uv run pytest tests/test_calibration_validators.py tests/test_schemas_depth_kind.py tests/test_schemas_perception.py -q` | ✅ |
| T2 store + mapping guard | 13-01 | 1 | multi-file honesty suite pytest | ✅ |
| T1 calibration models | 13-02 | 2 | `uv run pytest tests/test_calibration_state.py -q` | ✅ |
| T2 CalibrationState machine | 13-02 | 2 | state + honesty regression pytest | ✅ |

Sampling: Wave 1: 2/2 verified → ✅; Wave 2: 2/2 verified → ✅  
Wave 0: tests created via TDD tasks (no `<automated>MISSING</automated>`); VALIDATION maps gaps to plan tasks → ✅  
No watch mode; unit/smoke latency acceptable.

Overall Dim 8: ✅ PASS

### 9. Cross-Plan Data Contracts — PASS

- `promote_kind_unit(base_kind, base_unit, *, applied, valid) -> tuple` defined in 13-01, wrapped in 13-02 with matching signature.
- No sanitizing transform that strips fields another plan needs.
- Calibration models live only in 13-02; honesty asserts only in 13-01 with store consumer in same plan.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

Constraints from PROJECT/ROADMAP (zero new deps, spine freeze, no FSD) honored.

### 11. Research Resolution — PASS (with warning)

RESEARCH `## Open Questions` has five items; plans lock all five:

1. metric_estimated + unit=None reject → **yes** (13-01 locked decision A2)  
2. Residual/scale clamps → **Phase 14 structural-only** (13-02)  
3. apply_map stub in Phase 13 → **omit** (13-02 discretion)  
4. calibrated + free-space ordinal allowed → **yes** (13-01)  
5. Persist path format → **out of phase** (Phase 17)

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phase 9–12). Not a blocker: answers are locked in plan decisions.

### 12. Pattern Compliance — PASS

PATTERNS.md File Classification covers all planned touch files.  
Plans cite PATTERNS + RESEARCH in every task `read_first`.  
Shared patterns (extra=forbid, PipelineState lock twin, pure ValueError asserts, model_validator mode=after) appear in actions.

---

## Phase boundary check

| Forbidden in Phase 13 | Plans |
|----------------------|-------|
| Fit / scale math (CAL-01/02) | Not tasked |
| DepthLoop hook / apply_map impl | Explicitly omit; handoff docstring only |
| Wizard REST / index.html | Out of scope both plans |
| Persist YAML I/O | Out of scope both plans |
| Free-space algorithm / meter path | Schema units only; no algorithm edits |

**PASS** — phase boundary held.

---

## Special checks

| Check | Result |
|-------|--------|
| CAL-04 + CAL-05 each in plan `requirements` | **PASS** — both plans claim both |
| Every task has `read_first` + `acceptance_criteria` | **PASS** — all 4 tasks |
| `threat_model` present | **PASS** — both plans |
| Nyquist Dimension 8 / validation map | **PASS** — VALIDATION present; all tasks automated |
| Waves and dependencies correct | **PASS** — 01 wave1; 02 wave2 depends 13-01 |
| must_haves present | **PASS** — truths/artifacts/key_links both plans |
| No fit / DepthLoop / wizard / persist | **PASS** — boundary explicit |
| Zero new packages | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 13-01 Honesty validators + store gate | 1 | 2 | 7 | CAL-04, CAL-05 | Valid |
| 13-02 CalibrationState + fingerprint | 2 | 2 | 5 | CAL-04, CAL-05 | Valid |

---

## Structured Issues

```yaml
issues:
  - dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    plan: null
    fix_hint: "Optional hygiene: rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED."

  - dimension: nyquist_compliance
    severity: info
    description: "13-VALIDATION.md has wave_0_complete: false (pre-execution draft). Plans implement Wave 0 tests as TDD tasks; nyquist_compliant already true."
    plan: null
    fix_hint: "After execution lands Wave 0 checkboxes, set wave_0_complete: true."
```

**Blockers:** 0  
**Warnings:** 1 (hygiene)  
**Info:** 1  

---

## Recommendation

**Plans will achieve the phase goal.** All four success criteria, CAL-04/05, phase boundary, Nyquist, threats, key links, and mandatory task gates (`read_first` + `acceptance_criteria`) are covered.

Execute: `/gsd:execute-phase 13`

Optional non-blocking hygiene: mark RESEARCH Open Questions (RESOLVED).

## VERIFICATION PASSED
