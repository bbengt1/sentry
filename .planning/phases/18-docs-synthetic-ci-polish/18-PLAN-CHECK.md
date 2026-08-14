# Phase 18 Plan Check — Docs + Synthetic CI Polish

**Checked:** 2026-08-14
**Plans:** `18-01-PLAN.md`, `18-02-PLAN.md`
**Checker:** gsd-plan-checker (goal-backward, adversarial)
**Artifacts read:** ROADMAP Phase 18, REQUIREMENTS OPS-02/OPS-03, RESEARCH (Skip flag), PATTERNS, VALIDATION, both PLAN.md files, Phase 12 12-01/12-02 analogs, stale hubs on main, `ci.yml`, existing v0.3 test inventory
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + user brief)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> Operators have a guided non-FSD calibration flow in docs; CI covers fit/apply/honesty/persist with synthetic data only

**Success criteria (must be TRUE):**
1. Operator docs describe the calibration wizard, persistence path, and honesty rules without vehicle-grade / FSD claims
2. `perception-frame` / safety docs reflect free-space meters only when calibrated (no doc drift to “always ordinal”)
3. Automated tests cover fit / apply / honesty / persist with synthetic frames (no physical room required in CI)

**Requirements:** OPS-02, OPS-03

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| OPS-02 | Operator hub + honesty, no FSD | 18-01 hub + keywords | T1 RED tests / T2 GREEN docs | Covered |
| OPS-02 SC2 | No always-ordinal drift | 18-01 perception-frame/safety/README | T2 refresh + keyword forbid | Covered |
| OPS-03 | Synthetic fit/apply/honesty/persist | 18-02 inventory + existing 13–17 suites | T1 matrix + CI lock | Covered |
| SC3 no room | CI stays `--extra dev` | 18-02 + existing `test_edge_ci_workflow.py` | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| `docs/calibration.md` hub | 18-01 T2 | numbered wizard + STACK path |
| Keyword lock | `test_calibration_docs.py` | 18-01 T1 RED → T2 GREEN |
| Stale always-ordinal gone | hub refresh | 18-01 T2 |
| STACK persist path (not ~/.config) | hub + keyword | 18-01 |
| Honesty triad / Cancel≠Clear / persist status | hub tables | 18-01 |
| Fit/apply/honesty/persist tested | existing suites | 18-02 inventory |
| No room/Jetson/CUDA/`--extra depth` | `ci.yml` + EDGE-CI-02 | 18-02 |
| No product creep | files_modified docs+tests | both plans |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- OPS-02 entirely in 18-01 (docs + keyword TDD). CAL/WIZ/FS/PER correctly not re-claimed.
- OPS-03 entirely in 18-02 (inventory + CI lock). Does not re-implement Phase 13–17 product tests.
- complete-milestone / REQUIREMENTS checkbox sweep explicitly later — not a silent drop of OPS-02/03.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 18-01 | 2 | 13 | yes | pytest keyword | yes | yes | yes |
| 18-02 | 1 | 2 | yes | pytest inventory + CI | yes | yes | yes |

Both plans include threat_model with T-18-* + T-18-SC.

18-01 split RED/GREEN matches Phase 12-01 (docs TDD). Combining into one task would hide the RED gate. **Keep two tasks.**

18-02 is one verify-only wave (same shape as 12-02 Task 3). Splitting “write matrix” vs “run suites” would leave OPS-03 incomplete. **Keep as one task.**

### 3. Dependency Correctness — PASS

```
18-01 (wave 1, depends_on: [])  →  18-02 (wave 2, depends_on: ["18-01"])
```

18-02 inventories `tests/test_calibration_docs.py` from 18-01. CI lock does not depend on prose, but the phase gate is “full suite including new keywords.”

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| README / docs/README → calibration.md | 18-01 |
| Hub → STACK persist path | 18-01 |
| Keywords → hub surfaces | 18-01 |
| Matrix → existing 13–17 modules | 18-02 |
| EDGE-CI-02 → ci.yml no `--extra depth` | 18-02 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 18-01 | 2 | 13 | Docs + 2 test modules; no src/ |
| 18-02 | 1 | 2 | Tests only; ci.yml verify-only |

### 6. Verification Derivation — PASS

must_haves truths are product-observable (hub phrases, CI YAML, file existence). Seed pytest matches VALIDATION.md.

### 7. Context Compliance — PASS (no CONTEXT.md)

All 10 locked decisions appear in RESEARCH and plan Locked decisions tables. Split: 18-01 honors #1–7, #9; 18-02 honors #8–10.

### 7b. Scope Reduction — PASS

Product features, spine edits, version bump, complete-milestone, `~/.config` JSON, room/Jetson CI deferred explicitly — not silent drops of OPS-02/03.

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Operator hub | `docs/calibration.md` | 18-01 |
| Wire/safety honesty copy | existing hubs | 18-01 |
| Keyword lock | `tests/test_calibration_docs.py` | 18-01 |
| v0.3 matrix | `tests/test_v03_honesty_matrix.py` | 18-02 |
| CI hardware lock | `test_edge_ci_workflow.py` + ci.yml | 18-02 |
| Fit/apply/persist behavior | Phases 13–17 (already shipped) | 18-02 verify-only |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. All tasks have automated pytest verify. Wave 0 gaps mapped (missing hub, stale phrases, missing matrix module).

### 9. Cross-Plan Data Contracts — PASS

- 18-02 consumes 18-01 `test_calibration_docs.py` in V03_INVENTORY.
- 18-01 does not edit ci.yml.
- 18-02 does not reopen hub prose unless a test proves drift.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

Research flag Skip honored (short RESEARCH: stale table, locks, inventory, split, must-not-ship). No open questions.

### 12. Pattern Compliance — PASS

PATTERNS.md covers hub + keyword + matrix; plans cite PATTERNS + RESEARCH + Phase 12 analogs in read_first.

---

## Phase boundary check

| Forbidden in Phase 18 | Plans |
|----------------------|-------|
| src/sentry_ai product edits | Out of scope |
| DetectionLoop / FrameBus / ORT / kind_for_mode | Frozen |
| New pip deps | Locked zero |
| pyproject 0.1.0 bump | Explicit |
| ~/.config JSON persist docs | Overruled; STACK YAML |
| CI `--extra depth` / Jetson / CUDA / room | Forbidden |
| FSD / vehicle-grade / precise meters as claims | Keyword forbid |
| complete-milestone | Later step |
| Re-implementing fit/persist product tests | Inventory only |

**PASS**

---

## Special checks

| Check | Result |
|-------|--------|
| Locked decisions in RESEARCH + plan tables | **PASS** |
| OPS-02/03 mapped | **PASS** |
| STACK path not ARCHITECTURE ~/.config JSON | **PASS** |
| Cancel draft-only; Clear deletes | **PASS** (docs) |
| Persist status ≠ depth.kind | **PASS** (docs) |
| Phase 12 TDD analog for docs | **PASS** |
| threat_model T-18-* + SC | **PASS** |
| Wave deps 18-01 → 18-02 | **PASS** |
| No product-feature creep | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 18-01 docs hub + keyword TDD | 1 | 2 | 13 | OPS-02 | Valid |
| 18-02 CI inventory lock | 2 | 1 | 2 | OPS-03 | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0
**Warnings:** 0

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 18` starting with 18-01. After both plans merge, v0.3 requirements are closable; complete-milestone is a later step.

## VERIFICATION PASSED
