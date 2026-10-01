# Phase 20 Plan Check — Online sample + fit/reject

**Checked:** 2026-10-01
**Plans:** `20-01-PLAN.md`, `20-02-PLAN.md`
**Checker:** plan-check (goal-backward) against main `c98a09b`
**Artifacts read:** ROADMAP Phase 20, REQUIREMENTS ONL-03/ONL-04, v0.4 research SUMMARY/ARCHITECTURE/PITFALLS, 20-RESEARCH/PATTERNS/VALIDATION, both PLAN.md files, Phase 19 locks, `calibration_state.py`, `spatial/calibration.py`, `routes_calibration.py` sample/compute, `models/depth/loop.py` apply-before-store, `code-review-2026-09-25-full-repo.md` CR-007 and CR-018
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + Phase 19)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> An online sampler can collect a throttled N-sample window into draft only and run the same v0.3 fit/reject without promoting meters

**Success criteria (must be TRUE):**
1. Online samples write draft only — WIZ-04 holds; draft never claims `metric_calibrated` / meters
2. Fit/reject is the same v0.3 gates; `ok=False` never becomes applied
3. No per-frame unguarded refit on the DepthLoop hot path — sticky last applied scale; throttle / N-sample window
4. Synthetic unit tests cover draft-only sampling and reject-stays-applied without a physical room

**Requirements:** ONL-03, ONL-04

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| ONL-03 samples | Draft only, kind stays applied | 20-01 window + 20-02 `snapshot.scale` | T1 RED / T2 GREEN | Covered |
| ONL-03 throttle | No per-frame hot-path refit | 20-01 N=8, 1.0 s, frame id; rg DepthLoop | T1/T2 | Covered |
| ONL-04 pass | Same fit, draft params only | 20-02 `draft_staged` | T1/T2 | Covered |
| ONL-04 fail | `ok=False` never applied | 20-02 residual + absurd | T1/T2 | Covered |
| SC4 no room | synthetic pytest, injected `now_s` | both | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Samples are draft | 20-01 `replace_draft_samples` | `note="online"` |
| No fit until the window exists | 20-01 returns `window_short` | 20-02 fits only at `window_n` |
| Passed fit is not meters | 20-02 `set_draft_params` | `snapshot.scale` stays applied |
| Failed fit is not applied | 20-02 `clear_draft_params` | applied scale unchanged |
| No hot-path refit | sampler not imported by DepthLoop | both plans rg |
| Cancel / Clear / disable stay distinct | 20-01 matrix | anchors follow consent, window follows draft |
| Nothing auto-commits | monkeypatch raise | both plans |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- ONL-03 split: collection (20-01) + "a passed fit is still draft" (20-02). Roadmap SC1 is both.
- ONL-04 entirely in 20-02. 20-01 must not import `fit_scale_median`.
- ONL-01/02/05/06/07/08 are not claimed. Phase 19 locks are regression tests, not re-implementation of the flag.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 20-01 | 2 | 4 | yes | pytest sampler+state+persist+fit+api | yes | yes | yes |
| 20-02 | 2 | 3 | yes | pytest sampler+fit+state+persist+api | yes | yes | yes |

RED/GREEN kept. 20-02 Task 1 is RED only because 20-01 stops at `window_short`.

### 3. Dependency Correctness — PASS

```
20-01 (wave 1, depends_on: [])  →  20-02 (wave 2, depends_on: ["20-01"])
```

20-02 consumes `consider`, anchors, and `replace_draft_samples`. It adds `clear_draft_params` and the fit branch. It does not reopen the throttle numbers.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| `apply()` success → anchors, online stays off | 20-01 |
| `consider` → `replace_draft_samples` | 20-01 |
| `map_space=applied` → invert then read | 20-01 |
| `clear_draft` drops window, not anchors | 20-01 |
| `clear_applied` drops anchors | 20-01 |
| full window → `fit_scale_median` | 20-02 |
| `ok=True` → `set_draft_params` only | 20-02 |
| `ok=False` → `clear_draft_params` only | 20-02 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 20-01 | 2 | 4 | State + new sampler + tests. No routes, no fit module |
| 20-02 | 2 | 3 | Fit branch + `clear_draft_params` + tests. `spatial/calibration.py` read-only |

One new module. No new package dependency.

### 6. Verification Derivation — PASS

Truths are observable on `CalibrationState` and `OnlineSampleResult`. Clocks are injected. VALIDATION.md lists the same behaviors.

### 7. Context Compliance — PASS (no CONTEXT.md)

Locks from the user brief and Phase 19 are in RESEARCH and both plan tables: draft ≠ meters; Cancel / Clear / disable distinct; no auto-commit; N and interval locked; pre-apply raw; same fit gates; no `auto_committed` / `rejected`.

### 7b. Scope Reduction — PASS

Auto-commit, DepthLoop hook, smoother reset, fingerprint commit gate, YAML policy, UI, and a new horizon gate are deferred in RESEARCH and in each plan's out-of-scope list. They are Phase 21/22 or the open CR-007 question, not silent drops of ONL-03/04.

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Consent anchors | `CalibrationState` under the existing lock | 20-01 |
| Throttle + window | `OnlineSampler` control plane | 20-01 |
| Fit | call `fit_scale_median` | 20-02 |
| Staging | existing `set_draft_params` | 20-02 |
| `apply_map` / DepthLoop | frozen | out of scope |
| Status enum writes | Phase 21 | forbidden |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. Every task has an automated pytest command. Wave 0 gaps are the missing sampler, the missing anchors, and the missing fit branch. No hardware.

### 9. Cross-Plan Data Contracts — PASS

- Reason `window_short` is the 20-01 → 20-02 handoff. 20-02 replaces it only when the window is full and a fit ran.
- `OnlineSampleResult.reason` tokens are listed once in RESEARCH.
- Draft samples stay `CalibrationSample` so Cancel (`clear_draft`) already drops them.
- Applied fingerprint copied onto draft params; no new snapshot fields.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

Partial flag closed: N=8, interval 1.0 s, strictly increasing `frame_id`. Geometry is last-consent anchors, not a new measurement. Open questions are recorded and do not block the two plans: headless anchors across restart (confirm before execute), horizon gate (before Phase 21 only).

### 12. Pattern Compliance — PASS

PATTERNS.md names the state methods, the sampler class, the fit call, and the test list. Plans cite it. Analog is wizard compute's "stage only when ok", not a second apply site.

---

## Phase boundary check

| Forbidden in Phase 20 | Plans |
|----------------------|-------|
| `apply` / `apply_params` / `apply_map` from the sampler | T-20-01 / T-20-08 |
| Assigning `auto_committed` / `rejected` | rg forbid in 20-02 |
| DepthLoop edits | rg `online_sampler` in `loop.py` |
| New HTTP route | files_modified |
| YAML key / anchors persisted | tmp_path bytes; no store edits |
| Fit-gate constant edits | `spatial/calibration.py` not in files_modified |
| New pip deps / version bump | T-20-SC |
| Live Preview / FSD copy | out of scope |

**PASS**

---

## Review findings

| ID | In these plans? |
|----|-----------------|
| CR-007 one-point / double-scale | Yes, as N=8, pre-apply read, absurd scale does not stage, in-range scale stays draft |
| CR-007 YAML / `manual_scale` / boot `width=None` / wizard clamp | No. Left open before Phase 21 |
| CR-018 status honesty | Yes, as "do not assign the enum; online-off writes nothing". The route itself is already on main |
| CR-001–003, CR-004–005 | No. PRs #23 and #22 |
| CR-006, CR-008–CR-017 | No. Outside this phase |

---

## Special checks

| Check | Result |
|-------|--------|
| Locked N / interval in RESEARCH + plan tables | **PASS** |
| ONL-03/04 mapped | **PASS** |
| Phase 19 Cancel / Clear / disable restated and tested | **PASS** |
| Pre-apply raw vs store map | **PASS** |
| `ok=False` cannot become applied | **PASS** |
| threat_model T-20-* + SC | **PASS** |
| Wave deps 20-01 → 20-02 | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 20-01 throttled draft window + anchors | 1 | 2 | 4 | ONL-03 | Valid |
| 20-02 fit/reject stays draft | 2 | 2 | 3 | ONL-04, ONL-03 | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0
**Warnings:** 0

The `not_applied` branch is defensive. The public unapplied path is `online_off` because `set_online(True)` already refuses. That is documented in 20-01, not an open task.

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 20` starting with 20-01, after Brent confirms the anchor question in 20-RESEARCH if he has not already. Do not start Phase 21 until both plans merge. Do not implement Phase 20 in the planning PR.

## VERIFICATION PASSED
