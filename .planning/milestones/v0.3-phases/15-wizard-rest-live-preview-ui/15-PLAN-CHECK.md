# Phase 15 Plan Check — Wizard REST + Live Preview UI

**Checked:** 2026-08-13  
**Plans:** `15-01-PLAN.md`, `15-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** ROADMAP Phase 15, REQUIREMENTS WIZ-01..04 OPS-01, RESEARCH, PATTERNS, VALIDATION, both PLAN.md files  
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + user brief)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> Makers can run a Live Preview calibration wizard that stages samples, previews a fit, and Apply/Cancel without inventing meters mid-draft

**Success criteria (must be TRUE):**
1. Maker can open a Live Preview calibration wizard, collect samples, and stage a fit before commit
2. Maker can Apply (commits calibrated state) or Cancel (leaves no calibrated state or meter claims)
3. Wizard shows sample count, residual/status, and calibrated vs relative labeling clearly
4. Draft/staging never claims metric_calibrated on the live perception stream until Apply
5. Status / banner / Live Preview show whether calibration is active and base honesty (relative vs calibrated)

**Requirements:** WIZ-01, WIZ-02, WIZ-03, WIZ-04, OPS-01

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| WIZ-01 | Sample + stage fit | 15-01 | T1 inject + T2 sample/compute | Covered |
| WIZ-02 | Apply / Cancel | 15-01 T2 + 15-02 labels | Cancel=clear_draft; Clear=clear_applied | Covered (interpreted) |
| WIZ-03 | Count / residual / labels | 15-02 | T1 panel | Covered |
| WIZ-04 | Draft never live metric_calibrated | 15-01 T2 | snapshot kind stays relative | Covered |
| OPS-01 | Status + Live Preview active vs relative | 15-01 status + 15-02 badge | Covered |
| SC1 wizard collect/stage | 15-01 REST + 15-02 panel | Covered |
| SC2 Apply or Cancel | Apply commits; Cancel-before-apply never promotes | Covered |
| SC3 feedback | 15-02 count/residual/labels | Covered |
| SC4 draft not live kind | 15-01 tests | Covered |
| SC5 status/banner | calibration_active fields | Covered |

### WIZ-02 interpretation (locked)

ROADMAP: "Cancel leaves no calibrated state or meter claims" means **cancel-before-apply never promotes**. It does **not** wipe an already-applied calibration. Explicit **Clear** calls `clear_applied`. Both plans honor this; 15-01 tests cancel-after-apply leaves applied.

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Same CalibrationState | cli + create_app | 15-01 T1 |
| Sample observed_raw from store | routes_calibration | 15-01 T2 |
| 409 if sample while applied | routes | 15-01 T2 |
| Fit reuse; ok-gated draft | fit_* then set_draft_params | 15-01 T2 |
| Cancel = clear_draft | POST cancel | 15-01 T2 |
| Clear = clear_applied | POST clear | 15-01 T2 |
| Status additive fields | routes_preview | 15-01 T2 |
| Wizard chrome | index.html | 15-02 T1 |
| No local kind claim | JS + tests | 15-02 T1 |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- WIZ-01/02/04 + OPS-01 backend in 15-01; WIZ-03 + OPS-01 UI in 15-02.
- PER/FS correctly not claimed. CAL-* already Phase 13/14.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 15-01 | 2 | 12 | yes | pytest | yes | yes | yes |
| 15-02 | 1 | 2 | yes | pytest | yes | yes | yes |

Both plans include threat_model with T-15-* + T-15-SC.

### 3. Dependency Correctness — PASS

```
15-01 (wave 1, depends_on: [])  →  15-02 (wave 2, depends_on: ["15-01"])
```

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| CLI same object → DepthLoop + create_app | 15-01 T1 |
| sample → snapshot_depth + add_draft_sample | 15-01 T2 |
| compute → fit_* → set_draft_params if ok | 15-01 T2 |
| cancel → clear_draft | 15-01 T2 |
| clear → clear_applied | 15-01 T2 |
| status → calibration_active | 15-01 T2 |
| wizard fetch → /api/depth/calibration | 15-02 T1 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 15-01 | 2 | 12 | REST + inject; no HTML chrome |
| 15-02 | 1 | 2 | Static panel only |

### 6. Verification Derivation — PASS

must_haves truths are product-observable; artifacts and key_links present.

### 7. Context Compliance — PASS (no CONTEXT.md)

All 10 locked research decisions appear in RESEARCH and plan Locked decisions tables.

### 7b. Scope Reduction — PASS

YAML persist (17) and free-space meters (16) deferred explicitly — not silent drops of WIZ/OPS.

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Sample list | calibration_state.py | 15-01 T1 |
| REST | routes_calibration.py | 15-01 T2 |
| App inject | app.py / deps.py / cli.py | 15-01 T1 |
| Status | routes_preview.py | 15-01 T2 |
| Wizard UI | index.html | 15-02 |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. All tasks have automated pytest verify commands. Wave 0 gaps mapped to plan tasks.

### 9. Cross-Plan Data Contracts — PASS

- 15-02 consumes 15-01 paths (sample/compute/apply/cancel/clear) and status field names.
- Cancel vs Clear semantics shared.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

RESEARCH Open Questions marked RESOLVED; locks match plans.

### 12. Pattern Compliance — PASS

PATTERNS.md covers touch files; plans cite PATTERNS + RESEARCH in read_first.

---

## Phase boundary check

| Forbidden in Phase 15 | Plans |
|----------------------|-------|
| YAML persist I/O | Out of scope |
| Free-space meter algorithm | Out of scope |
| DetectionLoop / FrameBus / ORT-TRT | Frozen / grep verify |
| New pip deps / new frontend stack | Locked zero |
| Local UI claim of calibrated kind | 15-02 forbids |

**PASS**

---

## Special checks

| Check | Result |
|-------|--------|
| Locked decisions in RESEARCH + plan tables | **PASS** |
| WIZ-01..04 + OPS-01 mapped | **PASS** |
| Cancel != Clear | **PASS** |
| threat_model T-15-* + SC | **PASS** |
| Wave deps 15-01 → 15-02 | **PASS** |
| Same CalibrationState instance | **PASS** |
| FakeDepthWorker / never process | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 15-01 REST + inject + status | 1 | 2 | 12 | WIZ-01, WIZ-02, WIZ-04, OPS-01 | Valid |
| 15-02 static wizard | 2 | 1 | 2 | WIZ-03, OPS-01 | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0  
**Warnings:** 0  

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 15` starting with 15-01.

## VERIFICATION PASSED
