# Phase 17 Plan Check — Persist & Re-apply on Serve

**Checked:** 2026-08-13  
**Plans:** `17-01-PLAN.md`, `17-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** ROADMAP Phase 17, REQUIREMENTS PER-01..04, RESEARCH, PATTERNS, VALIDATION, both PLAN.md files, current `calibration_state.py` / `cli.py` serve / `routes_calibration.py` / `cache.py` / `load.py`  
**CONTEXT.md:** none (locked decisions from ROADMAP + RESEARCH + user brief)

**Overall verdict:** **PASS**

---

## Phase goal (from ROADMAP)

> Valid calibration survives restarts for the matching camera/fingerprint; mismatches refuse auto-apply and stay honestly relative

**Success criteria (must be TRUE):**
1. Maker can save calibration keyed by `camera_id` (plus fingerprint fields needed for safety)
2. On `sentry serve`, valid saved calibration re-applies for a matching camera/fingerprint without re-running the wizard
3. Mismatched fingerprint (resolution, model/mode, camera_id) refuses auto-apply and keeps honest relative depth with a visible reason
4. Maker can clear/invalidate stored calibration and return to uncalibrated relative depth

**Requirements:** PER-01, PER-02, PER-03, PER-04

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| PER-01 | Save keyed by camera_id + fingerprint | 17-01 store save | T1 save_params / path / sanitize | Covered |
| PER-03 | Mismatch refuses auto-apply | 17-01 match + try_reapply | T1 fingerprints_match + mismatch inactive | Covered |
| PER-02 | Serve re-apply without wizard | 17-02 CLI + 17-01 try_reapply | T1 try_reapply + CLI inspect | Covered |
| PER-04 | Clear stored cal | 17-02 REST clear_persisted | T1 clear deletes; cancel does not | Covered |
| SC1 save | 17-01 YAML | Covered |
| SC2 serve re-apply | 17-01 helper + 17-02 wire | Covered |
| SC3 mismatch visible | persist_status ignored_mismatch | Covered |
| SC4 clear | unlink + late size refuse | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| YAML under cache/calibration/{stem}.yaml | `calibration_store` | 17-01 T1 |
| No platformdirs / not profile YAML | path resolve | 17-01 T1 |
| Atomic write; safe_load; no maps | save/load | 17-01 T1 |
| apply_params (no fake samples) | CalibrationState | 17-01 T1 |
| fingerprints_match hard-refuse | store pure fn | 17-01 T1 |
| try_reapply match → applied | calibration_persist | 17-01 T1 |
| Serve calls try_reapply | cli.serve | 17-02 T1 |
| --calibration-file | cli option | 17-02 T1 |
| POST save + persist:true | routes | 17-02 T1 |
| Clear deletes file | clear_persisted | 17-02 T1 |
| Cancel draft-only | unchanged cancel | 17-02 T1 |
| Status persist enum | /api/status | 17-02 T1 |
| Late W×H refuse | DepthLoop before apply_map | 17-02 T1 |
| Sole scale site | no apply_map in CLI/routes | 17-02 grep |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- PER-01/03 in 17-01 (pure store + match + try_reapply).
- PER-02/04 in 17-02 (serve + REST + late size). PER-02's apply_params path is implemented in 17-01 so 17-02 does not invent a second load API.
- CAL/WIZ/FS/OPS correctly not claimed. Docs polish is Phase 18.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------|------|------------|---------------------|
| 17-01 | 1 | 7 | yes | pytest | yes | yes | yes |
| 17-02 | 1 | 10 | yes | pytest | yes | yes | yes |

Both plans include threat_model with T-17-* + T-17-SC.

17-02 file count is one wiring wave (CLI + app + routes + status + DepthLoop) — same shape as 15-01 / 16-02. Splitting REST vs serve would leave Clear-without-serve or serve-without-status incomplete for PER-02/04. **Keep as one task.**

### 3. Dependency Correctness — PASS

```
17-01 (wave 1, depends_on: [])  →  17-02 (wave 2, depends_on: ["17-01"])
```

REST/CLI consume `try_reapply` / `persist_applied` / `clear_persisted` / `refuse_if_mismatch` from 17-01.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| save → YAML stem | 17-01 |
| load → CalibrationParams via safe_load | 17-01 |
| match → refuse reason | 17-01 |
| try_reapply match → apply_params | 17-01 |
| serve → try_reapply | 17-02 |
| save / persist:true → persist_applied | 17-02 |
| clear → unlink | 17-02 |
| cancel → no unlink | 17-02 |
| DepthLoop → refuse_if_mismatch then apply_map | 17-02 |

### 5. Scope Sanity — PASS

| Plan | Tasks | Frontmatter files | Notes |
|------|-------|-------------------|-------|
| 17-01 | 1 | 7 | Pure I/O + persist helper + apply_params; no CLI/REST |
| 17-02 | 1 | 10 | Serve/REST/status/late size |

### 6. Verification Derivation — PASS

must_haves truths are product-observable; artifacts and key_links present. Seed pytest command matches VALIDATION.md.

### 7. Context Compliance — PASS (no CONTEXT.md)

All 13 locked research decisions appear in RESEARCH and plan Locked decisions tables. Split: 17-01 honors #1-8, #13; 17-02 honors #2, #6-7, #9-13.

### 7b. Scope Reduction — PASS

Capture uniqueID / RTSP fields, profile YAML, platformdirs, wizard HTML, docs (18), FSD/motor deferred explicitly — not silent drops of PER-01..04.

`refuse_if_mismatch` is implemented in 17-01 and **wired** in 17-02 (required for lock #6).

### 7c. Architectural Tier Compliance — PASS

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| YAML I/O / path / match | config/calibration_store.py | 17-01 |
| try_reapply / persist_applied | control/calibration_persist.py | 17-01 |
| apply_params | calibration_state.py | 17-01 |
| Serve load / banner | cli.py | 17-02 |
| REST save/clear | routes_calibration.py | 17-02 |
| Status persist | routes_preview.py | 17-02 |
| Late size | DepthLoop before apply_map | 17-02 |
| Map scale | DepthLoop apply_map (Phase 14) | not duplicated |

### 8. Nyquist Compliance — PASS

VALIDATION.md exists. All tasks have automated pytest verify commands. Wave 0 gaps mapped to plan tasks (round-trip, sanitize, match matrix, try_reapply honesty, save/persist:true, clear-deletes, cancel-leaves-file, late W×H, status field).

### 9. Cross-Plan Data Contracts — PASS

- 17-02 consumes 17-01 `try_reapply` / `ReapplyResult.status` literals.
- 17-01 does **not** edit CLI/REST (existing API tests stay green).
- `CalibrationSnapshot.persist_status` added in 17-01 with default `none` so 17-02 status copy is additive.

### 10. CLAUDE.md Compliance — SKIPPED (no repo-root CLAUDE.md)

### 11. Research Resolution — PASS

RESEARCH Open Questions marked RESOLVED; locks match plans (STACK path; auto-apply on match; explicit persist; Clear deletes; apply_params; no uniqueID this phase).

### 12. Pattern Compliance — PASS

PATTERNS.md covers touch files; plans cite PATTERNS + RESEARCH in read_first.

---

## Phase boundary check

| Forbidden in Phase 17 | Plans |
|----------------------|-------|
| platformdirs / ~/.config JSON | Overruled; STACK YAML path |
| Profile YAML merge | Out of scope |
| Capture uniqueID / RTSP fields | Out of scope |
| yaml.load | safe_load only |
| Depth maps on disk | Explicit omit |
| Fake wizard samples on load | apply_params |
| Auto-save on every apply | persist:true optional |
| Cancel deletes file | Explicit test |
| Second apply_map | grep |
| DetectionLoop / FrameBus / ORT / kind_for_mode | Frozen |
| Wizard HTML redesign | Out of scope |
| Docs polish | Phase 18 |
| New pip deps | Locked zero |
| FSD / motor | Out of scope |

**PASS**

---

## Special checks

| Check | Result |
|-------|--------|
| Locked decisions in RESEARCH + plan tables | **PASS** |
| PER-01..04 mapped | **PASS** |
| STACK path not ARCHITECTURE ~/.config JSON | **PASS** |
| apply_params (no fake samples) | **PASS** |
| Clear deletes; Cancel does not | **PASS** |
| Late W×H refuse after serve-time None | **PASS** |
| threat_model T-17-* + SC | **PASS** |
| Wave deps 17-01 → 17-02 | **PASS** |
| DepthLoop sole scale site | **PASS** |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 17-01 YAML store + fingerprint + apply_params | 1 | 1 | 7 | PER-01, PER-03 | Valid |
| 17-02 serve/REST/status/late size | 2 | 1 | 10 | PER-02, PER-04 | Valid |

---

## Structured Issues

```yaml
issues: []
```

**Blockers:** 0  
**Warnings:** 0  

---

## Recommendation

**Plans will achieve the phase goal.** Execute: `/gsd:execute-phase 17` starting with 17-01.

## VERIFICATION PASSED
