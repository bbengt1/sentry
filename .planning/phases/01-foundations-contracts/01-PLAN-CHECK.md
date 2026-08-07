# Phase 1 Plan Check — Foundations & Contracts

**Checked:** 2026-08-07  
**Phase:** 01-foundations-contracts  
**Plans verified:** 3 (`01-01`, `01-02`, `01-03`)  
**Status:** PASSED (0 blockers; warnings only)

---

## Goal (from ROADMAP)

Establish the product skeleton and non-negotiable contracts so every later phase shares types, plugins, licenses, and multi-target hooks.

**Requirements:** FOUND-01, FOUND-02, FOUND-03, FOUND-04, FOUND-05, FOUND-06, MODEL-01

**Success criteria:**
1. Install + health/smoke against synthetic frames
2. Frame / PerceptionFrame with frame_id, camera_id, timestamps, depth_kind enum
3. Plugin registry stubs (sources / workers / sinks)
4. THIRD_PARTY_MODELS.md with commercially friendly defaults (NC excluded)
5. Runtime profiles: desktop-gpu | jetson | cpu-fallback

---

## Dimension Results

| # | Dimension | Result | Notes |
|---|-----------|--------|-------|
| 1 | Requirement coverage | ✅ PASS | All FOUND-01..06 + MODEL-01 in plan frontmatter |
| 2 | Goal-backward / must_haves | ✅ PASS | ROADMAP success criteria map to plan truths + tasks |
| 3 | Task completeness | ✅ PASS | All 9 tasks have files, read_first, action, verify/automated, acceptance_criteria, done |
| 4 | Concrete actions | ✅ PASS | Field names, enum values, entry points, deps pinned; no vague "align" without targets |
| 5 | Dependencies & waves | ✅ PASS | `01-01 → 01-02 → 01-03`; acyclic; waves 1/2/3 consistent |
| 6 | Scope | ✅ PASS | No camera capture, torch, FastAPI, full UI; deferred items excluded |
| 7 | Threat models | ✅ PASS | Each plan has STRIDE register (T-1-01..05 + SC) |
| 8 | Nyquist / validation | ✅ PASS | VALIDATION.md present; all tasks automated; Wave 0 stubs in 01-01 |
| 9 | Naming locks | ✅ PASS | `sentry-ai` / `sentry_ai` / CLI `sentry` locked in 01-01 |
| 10 | Depth honesty | ✅ PASS | DepthKind three values; no `depth_m`; relative rejects unit meters |
| 7c | Architectural tier | ✅ PASS | Contracts/CLI/plugins in API/Backend tier per RESEARCH map |
| 9x | Cross-plan data contracts | ✅ PASS | Frame/PerceptionFrame/config produced in 01-02, consumed in 01-03 |
| 10x | CLAUDE.md compliance | ⏭ SKIP | No project `./CLAUDE.md` |
| 11 | Research resolution | ⚠️ WARNING | Open Questions not marked RESOLVED (recommendations adopted in plans) |
| 12 | Pattern compliance | ⏭ SKIP | No PATTERNS.md for this phase |
| 7b | Scope reduction | ✅ PASS | "Stubs" language matches FOUND-04/06 ("stubs acceptable"); no silent D-XX reduction |
| — | Context compliance | ✅ PASS | Locked decisions implemented; deferred ideas not in plans |

---

## Requirement Coverage

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| FOUND-01 | 01-01 | T1 package, T2 CLI/README/Wave0, T3 CI | Covered |
| FOUND-02 | 01-02 | T1 Frame, T2 PerceptionFrame | Covered |
| FOUND-03 | 01-02 | T1 DepthKind + DepthPayload validators | Covered |
| FOUND-04 | 01-03 | T1 PluginRegistry + builtins + entry points | Covered |
| FOUND-05 | 01-03 | T3 THIRD_PARTY_MODELS.md + policy polish | Covered |
| FOUND-06 | 01-02, 01-03 | 01-02 T3 profiles; 01-03 T2 backend protocols | Covered (split intentional) |
| MODEL-01 | 01-02, 01-03 | 01-02 T3 allow_cloud false; 01-03 T3 docs/smoke assert | Covered |

---

## Goal-Backward (ROADMAP Success Criteria)

| Success criterion | Delivered by | must_haves / tasks |
|-------------------|--------------|--------------------|
| 1. Install + health/smoke synthetic | 01-01 install/CLI; 01-03 full smoke | truths + cli.smoke key_link |
| 2. Frame/PerceptionFrame + depth_kind | 01-02 T1–T2 | DepthKind enum + identity fields + nested DepthPayload.kind |
| 3. Plugin registry stubs | 01-03 T1 | synthetic/noop/null + entry-point groups |
| 4. THIRD_PARTY_MODELS.md | 01-03 T3 | Apache default Small; AGPL/NC non-default |
| 5. Runtime profiles | 01-02 T3 | RuntimeProfile + three YAML profiles |

---

## Plan Summary

| Plan | Wave | depends_on | Tasks | files_modified | Requirements | Threat model | Status |
|------|------|------------|-------|----------------|--------------|--------------|--------|
| 01-01 | 1 | [] | 3 | 18 | FOUND-01 | yes | Valid (file-count warning) |
| 01-02 | 2 | [01-01] | 3 | 18 | FOUND-02,03,06, MODEL-01 | yes | Valid (file-count warning) |
| 01-03 | 3 | [01-01, 01-02] | 3 | 15 | FOUND-04,05,06, MODEL-01 | yes | Valid (file-count warning) |

### Task structure (all plans)

| Task | Plan | read_first | action | verify/automated | acceptance_criteria | done |
|------|------|------------|--------|------------------|---------------------|------|
| T1 Package scaffold | 01-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| T2 CLI + Wave 0 stubs | 01-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| T3 CI workflow | 01-01 | ✅ | ✅ | ✅ | ✅ | ✅ |
| T1 Frame + DepthKind | 01-02 | ✅ | ✅ + behavior | ✅ | ✅ | ✅ |
| T2 PerceptionFrame | 01-02 | ✅ | ✅ + behavior | ✅ | ✅ | ✅ |
| T3 Config + MODEL-01 | 01-02 | ✅ | ✅ + behavior | ✅ | ✅ | ✅ |
| T1 Plugins | 01-03 | ✅ | ✅ + behavior | ✅ | ✅ | ✅ |
| T2 Backend stubs | 01-03 | ✅ | ✅ + behavior | ✅ | ✅ | ✅ |
| T3 Licenses + smoke | 01-03 | ✅ | ✅ + behavior | ✅ | ✅ | ✅ |

---

## Dimension 8: Nyquist Compliance

VALIDATION.md: **present** (`01-VALIDATION.md`)

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 | 01-01 | 1 | `uv sync` + import sentry_ai + name grep | ✅ |
| T2 | 01-01 | 1 | `sentry health/smoke` + `pytest -q` | ✅ |
| T3 | 01-01 | 1 | ci.yml + ruff + pytest + health | ✅ |
| T1 | 01-02 | 2 | `pytest tests/test_schemas_frame.py tests/test_schemas_depth_kind.py` | ✅ |
| T2 | 01-02 | 2 | schema suite pytest | ✅ |
| T3 | 01-02 | 2 | config + schema suite + ruff | ✅ |
| T1 | 01-03 | 3 | `pytest tests/test_plugins_registry.py` | ✅ |
| T2 | 01-03 | 3 | backend pytest + import smoke | ✅ |
| T3 | 01-03 | 3 | full pytest + ruff + smoke + health | ✅ |

- Sampling: every wave has automated verify on all tasks → ✅  
- Wave 0: test paths created as skip stubs in 01-01 T2 → ✅ planned  
- Watch mode: none → ✅  
- Latency: unit/smoke only, no ML → ✅ under 30s target  
- Overall: ✅ PASS

---

## Naming & Depth Locks

| Lock | Plan enforcement |
|------|------------------|
| Dist `sentry-ai` | 01-01 T1 pyproject name + grep verify |
| Import `sentry_ai` | 01-01 src layout + import assert |
| CLI `sentry` | 01-01 scripts entry + health/smoke |
| DepthKind three values | 01-02 T1 exact enum strings |
| No `depth_m` | 01-02 behavior + acceptance + tests |
| Relative never meters | model_validator rejects unit on relative |
| Profiles three names | RuntimeProfile + YAML files + tests |
| No Phase 1 torch/opencv/fastapi | explicit forbid + verify greps |

---

## Context Compliance

**Locked decisions:** All mapped to tasks (product identity, depth honesty, multi-profile, plugins, camera_id, local OSS, commercially friendly defaults, stack direction).

**Claude's discretion:** Used appropriately (src layout, pytest, typer CLI, YAML profiles, hatchling, Apache-2.0 product license recommendation).

**Deferred (excluded):** Camera ingest, frame bus, FastAPI UI, YOLO/DAV2 inference, free-space stream, ROS2/TensorRT execution — only mentioned as out-of-scope.

---

## Warnings (non-blocking)

### 1. [scope_sanity] High files_modified counts (15–18 per plan)

- **Plans:** 01-01, 01-02, 01-03  
- **Finding:** Each plan lists ≥15 files (threshold table marks 15+ as blocker territory).  
- **Why not a blocker:** Task counts are healthy (3 each). Inflation is structural: Wave 0 skip stubs (01-01), multi-module schema/config package (01-02), and plugin/backend/doc fan-out (01-03). ROADMAP + RESEARCH prescribe exactly three plans; further split would fragment contracts without reducing context risk (pure Python, no ML).  
- **Suggested fix (optional):** None required for execution. If future revision, extract Wave 0-only plan only if executor struggles with 01-01 Task 2 file list.

### 2. [research_resolution] RESEARCH.md Open Questions not marked RESOLVED

- **File:** `01-RESEARCH.md` `## Open Questions`  
- **Finding:** Five open questions lack inline `RESOLVED` markers / `(RESOLVED)` section suffix.  
- **Mitigation already in plans:** SPDX Apache-2.0 (01-01), epoch float timestamps (01-02), CLI `sentry` (01-01), thin Detection/FreeSpacePayload (01-02), GitHub Actions CI (01-01).  
- **Suggested fix:** Mark section `## Open Questions (RESOLVED)` with one-line resolution each (hygiene; not required before execute).

### 3. [task_completeness] DepthPayload file placement slightly ambiguous in 01-02 Task 1

- **Plan:** 01-02 Task 1  
- **Finding:** Action allows DepthPayload in `perception.py` or `validators.py`, but Task 1 `<files>` lists `validators.py` not `perception.py` (Task 2 owns perception).  
- **Risk:** Executor might create perception.py early or leave validators.py empty.  
- **Suggested fix (optional):** Pin Task 1 to `validators.py` (or `frame.py` sibling) only; Task 2 imports single definition.

### 4. [verification_derivation] Wire field name `kind` vs ROADMAP wording `depth_kind`

- **Plan:** 01-02  
- **Finding:** ROADMAP/ARCHITECTURE prose often says `depth_kind`; plans/RESEARCH Pattern 2 use nested `DepthPayload.kind: DepthKind`. Enum values and honesty rules match locked CONTEXT.  
- **Suggested fix (optional):** Document in schema docstring that wire path is `depth.kind` (DepthKind), equivalent to product language `depth_kind`. Not a contract gap for Phase 1.

---

## Issues

```yaml
# No BLOCKERs. Warnings for planner awareness only:
- dimension: scope_sanity
  severity: WARNING
  finding: "Plans list 15–18 files each (threshold 15+). Counts inflated by Wave 0 stubs and multi-module contracts layout; task counts remain 3 and ROADMAP requires 3 plans."
  affected_field: "files_modified"
  suggested_fix: "No split required for execution. Optionally document that Wave 0 stub files are intentionally cheap in 01-01 Task 2."

- dimension: research_resolution
  severity: WARNING
  finding: "01-RESEARCH.md ## Open Questions lacks (RESOLVED) markers though plans adopt all five recommendations."
  affected_field: "01-RESEARCH.md ## Open Questions"
  suggested_fix: "Mark section '## Open Questions (RESOLVED)' with Apache-2.0, epoch timestamps, CLI sentry, thin nested models, GHA CI."

- dimension: task_completeness
  severity: WARNING
  finding: "01-02 Task 1 allows DepthPayload in perception.py or validators.py but files list only validators.py (perception is Task 2)."
  affected_field: "01-02 Task 1 <action> / <files>"
  suggested_fix: "Pin DepthPayload to validators.py (or frame-adjacent) in Task 1; Task 2 imports single definition."

- dimension: verification_derivation
  severity: WARNING
  finding: "ROADMAP success criterion says depth_kind; plans implement DepthPayload.kind: DepthKind (nested). Honesty rules satisfied."
  affected_field: "01-02 schemas DepthPayload.kind"
  suggested_fix: "Optional docstring: wire field is depth.kind (DepthKind enum); product language depth_kind."
```

---

## Recommendation

**Proceed to execution.** Plans will achieve Phase 1 goal: installable `sentry-ai`/`sentry_ai` package, honest depth contracts, multi-profile config with local-only defaults, plugin/backend stubs, license docs, and synthetic `sentry smoke`.

Warnings are hygiene/clarity only — no revision loop required before `/gsd:execute-phase 1`.

---

## PLAN CHECK PASSED
