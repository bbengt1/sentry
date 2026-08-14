# Phase 14 Plan Check — Scale Math + DepthLoop Plug-in

**Checked:** 2026-08-12  
**Plans:** `14-01-PLAN.md`, `14-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** ROADMAP Phase 14, REQUIREMENTS CAL-01/02/03, RESEARCH, PATTERNS, VALIDATION, both PLAN.md files  
**CONTEXT.md:** none (locked decisions taken from ROADMAP + RESEARCH + user brief)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> Makers (and tests) can fit a global monocular scale from ground-truth samples and have that scale transform depth maps on the single DepthLoop truth path

**Success criteria (must be TRUE):**
1. A pure fit (numpy, no new deps) recovers scale from known-distance samples (known height supported when geometry is defined)
2. Invalid fits are rejected (too few samples, residual too high, inconsistent signs) and never become applied scale
3. When calibration is applied, DepthLoop transforms the depth map after the worker and before `PerceptionStore.set_depth`
4. Synthetic unit tests prove fit / reject / apply without a physical room

**Requirements:** CAL-01, CAL-02, CAL-03

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| CAL-01 | Pure fit recovers scale | 14-01 | T1 median + affine | Covered |
| CAL-02 | Reject invalid fits | 14-01 | T1 gates (samples/scale/residual/non-positive) | Covered |
| CAL-03 | DepthLoop transform before store | 14-02 | T1 apply_map; T2 loop+CLI+FakeDepthWorker | Covered |
| SC1 pure fit | spatial/calibration.py | 14-01 | Covered |
| SC2 reject | fit-time ok=False | 14-01 | Covered |
| SC3 DepthLoop hook | promote+apply_map | 14-02 | Covered |
| SC4 synthetic | test_calibration_fit + test_depth_loop | 14-01/02 | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Median scale from D/d | fit_scale_median | spatial/calibration.py |
| Affine optional N>=2 | fit_affine_lstsq | same |
| Non-positive obs rejected | _valid_pairs | fit-time |
| Absurd scale rejected | MIN/MAX_SCALE gate | fit-time before draft |
| High residual rejected | residual_rms_gate | fit-time before draft |
| apply_map float32 CoW | CalibrationState.apply_map | lock + new array |
| Store gets scaled+promoted | DepthLoop success path | promote then apply then set_depth |
| CLI wires state | cli.serve | CalibrationState() inject |
| No wizard/YAML/FS meters | out-of-scope both plans | phase boundary |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- CAL-01/02 in 14-01; CAL-03 in 14-02; no orphaned Phase 14 reqs.
- CAL-04/05 already complete in Phase 13; WIZ/FS/PER correctly not claimed.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 14-01 | 1 | 3 | yes | pytest | yes | yes | yes (10 items) |
| 14-02 | 2 | 5 | yes | pytest | yes | yes | yes (9 + 7 items) |

Both plans include `<threat_model>` with T-14-01..05 + T-14-SC.

### 3. Dependency Correctness — PASS

```
14-01 (wave 1, depends_on: [])  →  14-02 (wave 2, depends_on: ["14-01"])
```

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| fitters → CalibrationFitResult | 14-01 |
| reject gates → no draft | 14-01 |
| apply_map → scale/offset | 14-02 T1 |
| DepthLoop → promote + apply_map → set_depth | 14-02 T2 |
| cli → DepthLoop(calibration=) | 14-02 T2 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 14-01 | 1 | 3 | Pure math only |
| 14-02 | 2 | 5 | State apply + loop + CLI |

### 6. Verification Derivation — PASS

must_haves truths are product-observable; artifacts and key_links present.

### 7. Context Compliance — PASS (no CONTEXT.md)

All 9 locked research decisions appear in RESEARCH and both plans' Locked decisions tables.

### 7b. Scope Reduction — PASS

Wizard/YAML/free-space meters deferred explicitly per RESEARCH — not silent drops of CAL-01/02/03.

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Pure fit/reject | spatial/calibration.py | 14-01 |
| apply_map | control/calibration_state.py | 14-02 |
| DepthLoop hook | models/depth/loop.py | 14-02 |
| CLI inject | cli.py | 14-02 |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. All tasks have automated pytest verify commands. Wave 0 gaps mapped to plan tasks.

### 9. Cross-Plan Data Contracts — PASS

- Apply formula documented in 14-01, implemented in 14-02 apply_map.
- FitResult fields align with CalibrationParams scale/offset/residual_rms/sample_count/method.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

RESEARCH Open Questions marked (RESOLVED); locks match plans.

### 12. Pattern Compliance — PASS

PATTERNS.md covers all touch files; plans cite PATTERNS + RESEARCH in read_first.

---

## Phase boundary check

| Forbidden in Phase 14 | Plans |
|----------------------|-------|
| Wizard REST / index.html | Out of scope |
| YAML persist I/O | Out of scope |
| Free-space meter algorithm | Out of scope |
| DetectionLoop / FrameBus / ORT-TRT | Frozen / grep verify |
| New pip deps | Locked zero |

**PASS**

---

## Special checks

| Check | Result |
|-------|--------|
| Locked decisions in RESEARCH + plan tables | **PASS** |
| CAL-01/02/03 mapped | **PASS** |
| threat_model T-14-01..05 + SC | **PASS** |
| Wave deps 14-01 → 14-02 | **PASS** |
| FakeDepthWorker for CAL-03 | **PASS** |
| Copy-on-write + lock in apply_map | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 14-01 Pure fit/reject | 1 | 1 | 3 | CAL-01, CAL-02 | Valid |
| 14-02 apply_map + DepthLoop + CLI | 2 | 2 | 5 | CAL-03 | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0  
**Warnings:** 0  

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 14` starting with 14-01.

## VERIFICATION PASSED
