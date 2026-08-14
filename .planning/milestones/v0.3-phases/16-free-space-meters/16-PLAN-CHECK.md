# Phase 16 Plan Check — Free-Space Metric Path

**Checked:** 2026-08-13  
**Plans:** `16-01-PLAN.md`, `16-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** ROADMAP Phase 16, REQUIREMENTS FS-01..03, RESEARCH, PATTERNS, VALIDATION, both PLAN.md files, current `free_space.py` / loop / assemble / validators  
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + user brief)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> Free-space products use honest meters only when underlying depth is `metric_calibrated` — never ordinal percentile bands relabeled as meters

**Success criteria (must be TRUE):**
1. Free-space products emit `units="m"` only when depth kind is `metric_calibrated`
2. Relative and `metric_estimated` free-space stay ordinal; unit labels never flip while still computing pure ordinal percentile nearness as if meters
3. Free-space smoother/state resets on calibration apply and clear so stale ordinal/metric occupancy does not ghost

**Requirements:** FS-01, FS-02, FS-03

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| FS-01 | `units="m"` only when `metric_calibrated` | 16-01 compute + 16-02 wire | T1 metric branch; T1 assemble/validator/loop | Covered |
| FS-02 | No label-only percentile flip | 16-01 | 4–5 m smoking-gun + no min–max + sliders ignored | Covered |
| FS-03 | Smoother reset on apply/clear | 16-02 | `reset_smoother` + kind-change detect | Covered |
| SC1 units only when calibrated | 16-01 result.units + 16-02 store/assemble | Covered |
| SC2 relative/estimated ordinal | 16-01 keeps percentile path | Covered |
| SC3 smoother reset | 16-02 loop `_last_kind` | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Absolute 1.5/3.0 m cuts | `compute_free_space` calibrated branch | 16-01 T1 |
| No min–max on meters | `_meters_to_nearness` constant horizon; never `depth_to_nearness` | 16-01 T1 |
| Estimated still ordinal | kind switch; existing test kept | 16-01 T1 |
| 4–5 m scene far in metric | FS-02 golden test | 16-01 T1 |
| Loop consume kind | `kind=depth.kind` | 16-02 T1 |
| No re-scale | grep apply_map; consume store map | 16-02 T1 |
| Assemble helper flip | `_units_for_depth_kind` | 16-02 T1 |
| Validator grace ends | calibrated must be `"m"` | 16-02 T1 |
| Smoother reset | `reset_smoother` on kind != `_last_kind` | 16-02 T1 |
| Optional `distance_m` | mean blob meters, calibrated only | 16-02 T1 |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- FS-01/02 in 16-01 (pure) + 16-02 (wire for FS-01).
- FS-03 entirely in 16-02 (needs a running loop + EMA).
- CAL/WIZ/PER/OPS correctly not claimed. Docs polish is Phase 18.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 16-01 | 1 | 2 | yes | pytest | yes | yes | yes |
| 16-02 | 1 | 12 | yes | pytest | yes | yes | yes |

Both plans include threat_model with T-16-* + T-16-SC.

16-02 file count is high but it is **one wiring wave** (loop + store + assemble + schema + optional routes) — same shape as 15-01 REST+inject. Splitting store vs assemble would race the validator grace (assemble `"m"` before validator tighten, or tighten before assemble, both break tests). **Keep as one task.**

### 3. Dependency Correctness — PASS

```
16-01 (wave 1, depends_on: [])  →  16-02 (wave 2, depends_on: ["16-01"])
```

Validator tighten is correctly **after** the metric compute path exists, in the same wave as assemble flip.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| calibrated compute → units=m via meter cuts | 16-01 |
| relative/estimated → ordinal percentile | 16-01 |
| ordinal sliders ignored when calibrated | 16-01 + 16-02 |
| loop → compute(kind=depth.kind) | 16-02 |
| kind change → reset_smoother | 16-02 |
| assemble helper → m | 16-02 |
| validator calibrated must m | 16-02 |
| distance_m mean blob | 16-02 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 16-01 | 1 | 2 | Pure compute + tests; no wire |
| 16-02 | 1 | 12 | Loop/store/assemble/schema; optional routes |

### 6. Verification Derivation — PASS

must_haves truths are product-observable; artifacts and key_links present. Seed pytest command matches VALIDATION.md.

### 7. Context Compliance — PASS (no CONTEXT.md)

All 10 locked research decisions appear in RESEARCH and plan Locked decisions tables. Split: 16-01 honors #1–5, #9–10; 16-02 honors #3, #6–10.

### 7b. Scope Reduction — PASS

YAML (17), wizard REST redesign (15 done), docs polish (18), RANSAC, FSD/motor deferred explicitly — not silent drops of FS-01..03.

Optional belt-and-suspenders is extra, not a substitute for loop kind-detect (required).

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Metric band math | free_space.py | 16-01 |
| Loop consume / reset | loop.py | 16-02 |
| Store units | perception_store.py | 16-02 |
| Wire units | assemble.py | 16-02 |
| Validator | validators.py | 16-02 |
| distance_m | ObstacleCue + extract | 16-02 |
| Depth scale | DepthLoop (Phase 14) | not duplicated |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. All tasks have automated pytest verify commands. Wave 0 gaps mapped to plan tasks (smoking-gun, no min–max, slider ignore, kind reset, validator flip).

### 9. Cross-Plan Data Contracts — PASS

- 16-02 consumes 16-01 `units="m"` on `FreeSpaceResult` when calibrated.
- 16-01 does **not** tighten the wire validator (assemble still ordinal until 16-02).
- `distance_m` omitted in 16-01 so relative `no distance_m` tests stay green; added in 16-02.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

RESEARCH Open Questions marked RESOLVED; locks match plans (absolute cuts + optional distance_m; 1.5/3.0; pinned polarity; kind-detect reset; consume-only).

### 12. Pattern Compliance — PASS

PATTERNS.md covers touch files; plans cite PATTERNS + RESEARCH in read_first.

---

## Phase boundary check

| Forbidden in Phase 16 | Plans |
|----------------------|-------|
| YAML persist I/O | Out of scope |
| Wizard REST redesign | Out of scope |
| DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` | Frozen / grep verify |
| Re-scale in free-space | Locked consume-only |
| RANSAC / FSD / motor | Out of scope |
| Docs polish | Phase 18 |
| New pip deps | Locked zero |
| Label-only assemble flip without metric cuts | 16-01 required first |

**PASS**

---

## Special checks

| Check | Result |
|-------|--------|
| Locked decisions in RESEARCH + plan tables | **PASS** |
| FS-01..03 mapped | **PASS** |
| FS-02 smoking-gun (4–5 m far) | **PASS** |
| Phase 13 calibrated+ordinal grace removed in 16-02 | **PASS** |
| threat_model T-16-* + SC | **PASS** |
| Wave deps 16-01 → 16-02 | **PASS** |
| Consume DepthLoop map; no apply_map | **PASS** |
| Smoother reset without CalibrationState listeners | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 16-01 pure metric compute + honesty | 1 | 1 | 2 | FS-01, FS-02 | Valid |
| 16-02 loop/wire/reset/distance_m | 2 | 1 | 12 | FS-03, FS-01 wire | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0  
**Warnings:** 0  

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 16` starting with 16-01.

## VERIFICATION PASSED
