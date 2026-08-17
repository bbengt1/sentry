# Phase 19 Plan Check — Online consent & honesty state

**Checked:** 2026-08-15
**Plans:** `19-01-PLAN.md`, `19-02-PLAN.md`
**Checker:** executor plan-check (goal-backward, adversarial)
**Artifacts read:** ROADMAP Phase 19, REQUIREMENTS ONL-01/ONL-02/ONL-06, v0.4 research SUMMARY/FEATURES/ARCHITECTURE/STACK/PITFALLS, 19-RESEARCH/PATTERNS/VALIDATION, both PLAN.md files, Phase 17/18 XML analogs, `calibration_state.py`, `calibration_persist.py`, `routes_calibration.py`, `/api/status` calibration block, `CalibrationSnapshot`
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + user brief)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> Online mode exists as an opt-in default-off flag with honest status, and cannot invent the first metric scale; Cancel/Clear stay v0.3; disable-online is not Clear

**Success criteria (must be TRUE):**
1. Online re-calibration is opt-in and default off (serve / state boot with online disabled)
2. First `metric_calibrated` still requires wizard Apply or matching persist `try_reapply` — enabling online while unapplied does not auto-commit a scale
3. Cancel still clears draft only; Clear still clears applied + YAML
4. Disable-online does not clear applied params or delete the YAML file
5. Status can represent `online_off` (and is distinct from `depth.kind` and persist status)

**Requirements:** ONL-01, ONL-02, ONL-06

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| ONL-01 flag | Default off | 19-01 `set_online` / snapshot.online | T1 RED / T2 GREEN | Covered |
| ONL-01 status | `online_off` distinct plane | 19-02 snapshot + GET + `/api/status` | T1 RED / T2 GREEN | Covered |
| ONL-02 | First scale still Apply / `try_reapply` | 19-01 refuse-unapplied + try_reapply stays off | T1/T2 | Covered |
| ONL-06 Cancel | draft only | 19-02 state + REST | T1/T2 | Covered |
| ONL-06 Clear | applied + YAML; online forced off | 19-02 persist + REST | T1/T2 | Covered |
| ONL-06 disable ≠ Clear | flag only | 19-02 YAML-exists after disable | T1/T2 | Covered |
| SC5 no room | synthetic pytest | both plans | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Boot online-off | 19-01 `CalibrationState()` | `_online_enabled=False` |
| Enable unapplied refused | 19-01 `online_requires_applied` | 19-02 REST 409 |
| First scale Apply / try_reapply | 19-01 tests | apply/apply_params unchanged |
| Cancel = draft | 19-02 | `clear_draft` untouched |
| Clear = applied + YAML | 19-02 | `clear_persisted`; online reset in `clear_applied` |
| Disable ≠ Clear | 19-02 | `set_online(False)` no `delete_params` |
| `online_off` distinct | 19-02 | third plane on snapshot + status |
| No sampler / auto-commit / `apply_map` | both Out of scope | files_modified |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- ONL-01 split: flag (19-01) + status plane (19-02). Not a silent drop — ROADMAP SC5 is explicitly 19-02.
- ONL-02 entirely in 19-01 (state + persist). 19-02 re-asserts via 409.
- ONL-06 entirely in 19-02. 19-01 already resets online on `clear_applied` as a precursor (documented).
- ONL-03/04/05/07/08 correctly not claimed (Phases 20–22).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 19-01 | 2 | 4 | yes | pytest state+persist | yes | yes | yes |
| 19-02 | 2 | 7 | yes | pytest state+persist+API | yes | yes | yes |

Both plans include threat_model with T-19-* + T-19-SC.

RED/GREEN split matches Phase 18-01 / honesty-critical Phase 13. Combining would hide the RED gate. **Keep two tasks per plan.**

### 3. Dependency Correctness — PASS

```
19-01 (wave 1, depends_on: [])  →  19-02 (wave 2, depends_on: ["19-01"])
```

19-02 consumes `set_online` / `snapshot.online` from 19-01. REST 409 maps the 19-01 error token. Status enum cannot land before the flag exists.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| `set_online(True)` → `is_applied()` refuse | 19-01 |
| `try_reapply` match → online stays False | 19-01 |
| POST `/online` → `set_online` / 409 | 19-02 |
| GET calibration → snapshot online fields | 19-02 |
| `/api/status` → additive online fields | 19-02 |
| `clear_applied` → `online_off` | 19-01 precursor + 19-02 |
| `set_online(False)` → YAML remains | 19-02 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 19-01 | 2 | 4 | State + schema + tests; no routes |
| 19-02 | 2 | 7 | Status + REST + `/api/status`; no sampler |

### 6. Verification Derivation — PASS

must_haves truths are product-observable (boot flag, 409, YAML exists after disable, status tokens). Seed pytest matches VALIDATION.md.

### 7. Context Compliance — PASS (no CONTEXT.md)

All user-brief locks appear in RESEARCH + plan tables: default off; first scale Apply/`try_reapply`; draft ≠ meters; Cancel/Clear/disable; four-way status; no sampler/auto-commit/`apply_map`; zero new deps; session flag (no YAML); `CalibrationState` not a new class.

### 7b. Scope Reduction — PASS

Sampler, auto-commit, persist policy, DepthLoop, UI toggle, CLI/env, FSD, complete-milestone deferred explicitly — not silent drops of ONL-01/02/06.

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Session flag + first-scale lock | `CalibrationState` | 19-01 |
| Snapshot `online` | `CalibrationSnapshot` | 19-01 |
| Four-way `online_status` | `CalibrationSnapshot` | 19-02 |
| Cancel/Clear semantics | existing routes + `clear_applied` | 19-02 |
| Thin toggle | `POST /api/depth/calibration/online` | 19-02 |
| Status plane on `/api/status` | `routes_preview.py` additives | 19-02 |
| Sampler / auto-commit / `apply_map` | Phases 20–21 | Out of scope |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. All tasks have automated pytest verify. Wave 0 gaps mapped (missing flag, missing status, missing disable≠Clear tests).

### 9. Cross-Plan Data Contracts — PASS

- 19-02 requires 19-01 `set_online` + `snapshot.online`.
- 19-01 does not add REST or `online_status` on the snapshot.
- 19-02 does not reopen first-scale math or `apply_map`.
- Error token `online_requires_applied` is the 19-01 ↔ 19-02 contract.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

Research flag Standard honored. Open questions closed in 19-RESEARCH: home=`CalibrationState`; enable-unapplied=refuse; flag=session-only; REST thin POST in 19-02; UI deferred.

### 12. Pattern Compliance — PASS

PATTERNS.md covers flag, snapshot, Cancel/Clear/disable matrix, REST, `/api/status`; plans cite PATTERNS + RESEARCH + Phase 17 persist-status analog.

---

## Phase boundary check

| Forbidden in Phase 19 | Plans |
|----------------------|-------|
| Sampler / N-window / throttle | Out of scope (20) |
| Auto-commit / five-conjunct `apply_params` | Out of scope (21) |
| DepthLoop `apply_map` edits | Frozen |
| DetectionLoop / FrameBus / ORT / `kind_for_mode` | Frozen |
| YAML persist of online flag | Session only |
| Live Preview toggle | Out of scope (22) |
| New pip deps / pyproject bump | Locked zero |
| FSD / vehicle-grade claims | No docs hub this phase |
| Setting `auto_committed` / `rejected` | Enum only; rg forbid |

**PASS**

---

## Special checks

| Check | Result |
|-------|--------|
| Locked decisions in RESEARCH + plan tables | **PASS** |
| ONL-01/02/06 mapped | **PASS** |
| Consent-once / default-off | **PASS** |
| Cancel draft-only; Clear deletes; disable ≠ Clear | **PASS** |
| Status ≠ depth.kind ≠ persist | **PASS** |
| Phase 17 persist-status analog for additives | **PASS** |
| threat_model T-19-* + SC | **PASS** |
| Wave deps 19-01 → 19-02 | **PASS** |
| No product-feature creep into 20–22 | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 19-01 opt-in flag + first-scale lock | 1 | 2 | 4 | ONL-01 (flag), ONL-02 | Valid |
| 19-02 Cancel/Clear/disable + status plane | 2 | 2 | 7 | ONL-06, ONL-01 (status) | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0
**Warnings:** 0

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 19` starting with 19-01. Do not start Phase 20 until both plans merge.

## VERIFICATION PASSED
