# Phase 21 Plan Check — Gated auto-commit + DepthLoop/status

**Checked:** 2026-10-08
**Plans:** `21-01-PLAN.md`, `21-02-PLAN.md`
**Checker:** plan-check (goal-backward) against main `8ba5b34`
**Artifacts read:** ROADMAP Phase 21, REQUIREMENTS ONL-05/ONL-07 (+ new ONL-09), STATE Phase 19/20 locks, 20-02-SUMMARY, 21-RESEARCH/PATTERNS/VALIDATION, both PLAN.md files, `online_sampler.py`, `calibration_state.py`, `calibration_persist.py`, `calibration_store.py` (`fingerprints_match`), `models/depth/loop.py`, `spatial/free_space.py`, `spatial/loop.py`, `routes_calibration.py` (`/apply` smoother reset), `routes_preview.py` (status), `cli.py` serve wiring, `code-review-2026-09-25-full-repo.md` CR-007
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + Brent 2026-10-08 CR-007 decision)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> A passed online fit can auto-commit via `apply_params` only when all gates hold; DepthLoop remains the sole map apply site; free-space smoother resets; status distinguishes auto-commit from reject

**Success criteria (must be TRUE):**
1. Auto-commit calls `apply_params` only when online on AND already applied AND fit ok AND residual gate AND `fingerprints_match`
2. Failed gates leave the last sticky applied scale unchanged; `ok=False` / mismatch never become applied
3. DepthLoop remains the sole `apply_map` site
4. Free-space smoother resets on auto-commit like wizard Apply
5. Persist fingerprint refuse is unchanged
6. Status distinguishes `online_draft` / `auto_committed` / `rejected` from `depth.kind` and persist status
7. (new) Auto-commit refuses a candidate that puts the raw map's median at or past 3 m; wizard Apply unchanged

**Requirements:** ONL-05, ONL-07, ONL-09

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| ONL-05 conjuncts | SC1, SC2 | 21-01 gate matrix; 21-02 live fingerprint | T1 RED / T2 GREEN | Covered |
| ONL-07 sole apply_map | SC3 | 21-02 sole-site scan | T1/T2 | Covered |
| ONL-07 smoother | SC4 | 21-02 reset spy | T1/T2 | Covered |
| ONL-07 persist refuse | SC5 | 21-02 mismatch test; no persist edits | T1/T2 | Covered |
| Status | SC6 | 21-01 writes; 21-02 `/api/status` | T1/T2 | Covered |
| ONL-09 horizon | SC7 | 21-01 boundary + scale 1000 + wizard unchanged | T1/T2 | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Only gated commits go live | 21-01 `_commit_gate` | `apply_params(expect_applied=)` |
| Horizon cannot be emptied by auto-commit | 21-01 `horizon_median_m` | `DEFAULT_METRIC_MID_CUT_M` import |
| Refuse keeps consented scale | 21-01 | applied `is` unchanged; draft cleared |
| Clear/disable beat a commit | 21-01 | lock-held identity + online check |
| Live frames reach gates | 21-02 `_consider_online` | raw map + live fingerprint |
| One transform site | 21-02 | unchanged `apply_map` line |
| EMA reset | 21-02 `_attach_online_sampler` | `reset_smoother` callback |

---

## Dimension Results

### 1. Requirement Coverage — PASS
ONL-05 split: decision logic (21-01) + live inputs (21-02). ONL-07 in 21-02. ONL-09 in 21-01. ONL-08 (docs/CI/persist policy) stays Phase 22; Phase 21 only writes the status values it defines.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 21-01 | 2 | 4 | yes | pytest sampler+auto-commit+state+persist+fit+api | yes | yes | yes |
| 21-02 | 2 | 3 | yes | ruff + full pytest + health | yes | yes | yes |

### 3. Dependency Correctness — PASS

```
21-01 (wave 1, depends_on: [])  →  21-02 (wave 2, depends_on: ["21-01"])
```

21-02 consumes `auto_commit`, `on_auto_commit`, and `live_fingerprint` from 21-01 and does not edit control/.

### 4. Key Links Planned — PASS
`gates → apply_params(expect_applied)`, `candidate → horizon`, `refuse → mark_online_rejected`, `commit → on_auto_commit → reset_smoother`, `DepthLoop → consider(raw, live)`, `online_status → /api/status`.

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 21-01 | 2 | 4 | control plane only; `spatial/calibration.py` read-only |
| 21-02 | 2 | 3 | DepthLoop hook + serve wiring; routes read-only |

No new module, route, snapshot field, YAML key, or dependency.

### 6. Verification Derivation — PASS
Truths are observable on `CalibrationState`, `OnlineSampleResult`, the stored depth product, the smoother spy, and `/api/status`. Clocks injected.

### 7. Context Compliance — PASS
Brent 2026-10-08: horizon refuse for auto-commit only, keep last consented calibration, wizard unchanged — RESEARCH lock #4/#5, 21-01 tables and tests. Carried locks: no gate edits, no `fit_affine_lstsq`, restart out of scope, version 0.1.0, Phase 19 honesty, CR-001..005.

### 7b. Scope Reduction — PASS
Deferred and stated: YAML/persist policy and docs (Phase 22), wizard/YAML half of CR-007, deadband, relative horizon rule (open questions).

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Gates + horizon | `OnlineSampler` control plane | 21-01 |
| Atomic commit + status | `CalibrationState` under its lock | 21-01 |
| Live inputs | `DepthLoop` (existing pre-apply point) | 21-02 |
| Smoother reset | `FreeSpaceLoop.reset_smoother` via callback | 21-02 |
| `apply_map` | DepthLoop only | unchanged |

### 8. Nyquist Compliance — PASS
VALIDATION.md exists; every task has an automated pytest command; Wave 0 gaps listed; no hardware.

### 9. Cross-Plan Data Contracts — PASS
Reason tokens listed once in RESEARCH (`committed`, `fit_rejected`, `gate_*`, `fingerprint_*`, `offset_not_zero`, `horizon_refused`, `horizon_unknown`, `commit_stale`). `OnlineSampleResult` gains no fields. `auto_commit=False` keeps the Phase 20 contract.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS
CR-007 horizon question closed by Brent 2026-10-08; rule defined and justified. Two non-blocking open questions recorded.

### 12. Pattern Compliance — PASS
PATTERNS.md names the guarded commit, horizon helper, gate order, DepthLoop insertion, serve seam, and test list. Analogs: `/apply` + smoother reset, `refuse_if_mismatch`.

---

## Phase boundary check

| Forbidden in Phase 21 | Plans |
|----------------------|-------|
| Horizon gate on wizard / `try_reapply` | 21-01 wizard scale-1000 test |
| Edits to fit gates / `fit_affine_lstsq` | diff-empty + rg acceptance |
| Second `apply_map` | 21-02 sole-site test |
| YAML write / new key / anchors persisted | tmp_path bytes; no store edits |
| New route / snapshot field / dep / version bump | files_modified; T-21-SC |
| `refuse_if_mismatch` / `fingerprints_match` edits | diff-empty acceptance |
| Restart support | out of scope in both plans |

**PASS**

---

## Review findings

| ID | In these plans? |
|----|-----------------|
| CR-007 in-range scale / offset on the online path | Yes — ONL-09 horizon refuse; scale-only + `offset_not_zero`; live-HxW fingerprint |
| CR-007 wizard / YAML / `manual_scale` / boot `width=None` | No — wizard is the override (Brent) |
| CR-009 / CR-015 atomicity | Online path only (`expect_applied`) |
| CR-018 status honesty | Yes — status written only by commit/refuse paths |
| CR-001–005 | No — on main (PRs #23, #22); untouched |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 21-01 gated auto-commit + horizon refuse | 1 | 2 | 4 | ONL-05, ONL-09 | Valid |
| 21-02 DepthLoop hook + smoother + status | 2 | 2 | 3 | ONL-07, ONL-05 | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0
**Warnings:** 0

**Open questions for Brent (non-blocking, from RESEARCH):**
1. Large scenes: strict-absolute horizon refuses every candidate when the true scene median is at least 3 m. Keep strict, or allow a relative rule?
2. Deadband: commit (and smoother reset) every passing window, or skip when the new scale is within ~1% of applied?

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 21` starting with 21-01. If Brent answers either open question before 21-01 starts, fold it into 21-01 Task 1 tests. Do not implement Phase 21 in the planning PR.

## VERIFICATION PASSED
