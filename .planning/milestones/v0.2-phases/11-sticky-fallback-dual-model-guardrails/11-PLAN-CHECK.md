# Phase 11 Plan Check — Sticky Fallback & Dual-Model Guardrails

**Checked:** 2026-08-10  
**Plans:** `11-01-PLAN.md`, `11-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** RESEARCH, PATTERNS, VALIDATION, ROADMAP Phase 11, REQUIREMENTS BACK-03 + EDGE-RT-04  
**CONTEXT.md:** none (discuss-phase not run; locked decisions from RESEARCH `user_constraints` + STATE/ROADMAP)

**Overall verdict:** **PASS** (hygiene flags only — no plan rewrite required)

---

## Phase goal (from ROADMAP)

> Missing ORT/TRT artifacts or deps never thrash or silently lie; depth and open-vocab stay on existing PyTorch paths this milestone

**Success criteria (must be TRUE):**
1. When preferred ORT/TRT artifact or dependency is missing, behavior is documented and sticky (fail-closed or explicit torch fallback with reason logged once — never thrash every frame)
2. Soft vs strict fallback modes are documented; live backend + reason remain visible when they differ from requested
3. Depth and open-vocab continue on existing PyTorch paths (no live ORT/TRT for those stages this milestone)
4. Dual-model guidance exists for TRT YOLO + torch depth (no continuous open-vocab + TRT+DAV2 as a first-class claim)

**Requirements:** BACK-03, EDGE-RT-04

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| BACK-03 | Sticky soft/strict fallback; reason logged once; no thrash | 11-01 (+ 11-02 operator surface) | 01 T1–T3 config/factory/serve/docs; 02 T1 status | Covered |
| EDGE-RT-04 | Depth/OV stay PyTorch; dual-model honesty | 11-02 | T2 torch-only lock tests + dual-model docs | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Soft miss → torch worker + reason (default) | factory `_miss` when `fallback_to_torch=True` | existing reason codes unchanged |
| Strict miss → no silent torch under ORT/TRT | `worker=None`, `backend_live=None`, reason set | serve `typer.Exit(1)` |
| Sticky resolve (no per-frame re-probe) | single serve factory call; loop has no factory | sticky inspect test + docs |
| Reason logged once | factory `logger.warning` / `logger.error` when reason set | caplog unit tests |
| Soft default global (incl. jetson) | `DeviceConfig.fallback_to_torch=True`; no jetson YAML flip | env `SENTRY_FALLBACK_TO_TORCH` always-wins |
| Soft vs strict documented | configuration.md + architecture.md (01); export dual-model (02) | keyword tests |
| Operator visibility requested/live/reason + mode | status pass-through `fallback_to_torch`; banner; UI reason when live null/differs | create_app → AppState → routes → footer |
| Depth torch/HF only | serve `DepthAnythingWorker` not via factory | `test_edge_rt04_torch_only.py` |
| OV YOLOE `.pt` only | serve `YoloeOpenVocabWorker(weights=…)` | same + yoloe source inspect |
| Dual-model measure-on-device YOLO+DAV2; non-claim continuous OV+TRT+DAV2 | export docs + keywords; retire Phase 11 deferral | `test_export_docs.py` |
| No Jetson / real engines in CI | monkeypatch + source inspect only | VALIDATION hardware policy |
| Spine freeze | DetectionLoop / bus / store / `/v1` untouched | explicit out-of-scope both plans |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- Roadmap requirement IDs appear in plan frontmatter:
  - `11-01`: BACK-03
  - `11-02`: EDGE-RT-04, BACK-03 (operator surface / status mode)
- Partition matches ROADMAP plan split (sticky soft/strict policy vs dual-model scope lock + status).
- No phase-mapped REQUIREMENTS.md item orphaned.
- EDGE-DOC-* / EDGE-CI-* correctly left to Phase 12; live ORT/TRT depth/OV deferred.

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done | read_first | acceptance_criteria |
|------|-------|-------|--------|--------------------|------|------------|---------------------|
| 11-01 | 3 | all | all | all pytest | all | all | all |
| 11-02 | 2 | all | all | all pytest | all | all | all |

`verify.plan-structure` **valid** for both plans; zero structural errors/warnings.  
Actions name concrete modules, reason codes, Exit(1) contract, freeze constraints, env name, and doc keyword surfaces. No shallow “align with” actions (task actions ~200–335 words, numbered steps).

Both plans include `<threat_model>` with STRIDE register (T-11-01..06 + SC on 01; T-11-07..11 + SC on 02).

### 3. Dependency Correctness — PASS

```
11-01 (wave 1, depends_on: [])  →  11-02 (wave 2, depends_on: ["11-01"])
```

- Acyclic; wave = max(deps)+1 consistent (mirrors Phase 9/10).
- Shared `cli.py`: sequential only — 01 owns Exit(1) / factory-once; 02 owns create_app `fallback_to_torch` inject + banner mode. 01 explicitly defers status field wiring to 02.
- No same-wave file conflicts.

### 4. Key Links Planned — PASS

| Link | Plan |
|------|------|
| `load_config` → `DeviceConfig.fallback_to_torch` via `SENTRY_FALLBACK_TO_TORCH` | 11-01 T1 |
| `profile_runtime` → `ProfileRuntime.fallback_to_torch` | 11-01 T1 |
| `build_detection_worker` → `rt.fallback_to_torch` soft/strict `_miss` | 11-01 T2 |
| factory miss → structured soft-fallback / strict-fail log once | 11-01 T2 |
| `cli.serve` → factory once; `worker is None` → `typer.Exit(1)` | 11-01 T3 |
| `cli.serve` → `create_app(fallback_to_torch=…)` pass-through | 11-02 T1 |
| `/api/status` → `app.state.fallback_to_torch` (`is not None` for False) | 11-02 T1 |
| depth/OV construction → separate workers (not factory) | 11-02 T2 |
| export dual-model docs → measure-on-device + continuous-OV non-claim | 11-02 T2 |

No isolated artifacts; status never recomputes live from preferred.

### 5. Scope Sanity — PASS (borderline warning on 11-02 files)

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 11-01 | 3 (target) | 8 (within 5–8) | T2 factory policy + matrix |
| 11-02 | 2 (target) | 12 (warning threshold 10) | T1 status chain 7 files |

- Task counts within 2–3 target (no 4+ warning / 5+ blocker).
- 11-02 file count is elevated because status pass-through must touch the full honesty chain (status/app/deps/routes/cli/UI) plus EDGE-RT-04 docs/tests — coherent, not crammed complex domain rewrite.
- Coherent split: BACK-03 policy (01) vs EDGE-RT-04 lock + operator surface (02).

### 6. Verification Derivation — PASS

must_haves truths are operator-observable (soft vs strict outcomes, Exit(1), sticky, depth/OV torch, dual-model measure-on-device, no continuous OV+TRT+DAV2, no silent ORT/TRT claim).  
Artifacts map to truths; key_links specify wiring methods (env parse, rt field, `_miss`, Exit, create_app pass-through, keyword patterns).

### 7. Context Compliance — PASS (via RESEARCH locks; no CONTEXT.md)

| Locked decision (RESEARCH / STATE) | Plan coverage |
|------------------------------------|---------------|
| Soft default globally (incl. jetson); strict opt-in | 11-01 T1–T3; jetson YAML values unchanged |
| Strict available | factory miss + serve Exit(1) |
| Sticky resolve; factory sole author of live | 11-01 sticky proof; 11-02 pass-through only |
| Depth/OV stay PyTorch | 11-02 EDGE-RT-04 tests + docs |
| No continuous OV+TRT+DAV2 first-class | 11-02 dual-model non-claim |
| No FPS claims; measure-on-device only | 11-02 docs + keywords |
| No new packages / find_spec only | 11-01 package lock |
| Spine freeze | both plans out-of-scope |

Deferred excluded: live ORT/TRT depth/YOLOE, VRAM governor / dual-model scheduler, Pi dual-model FPS, Phase 12 EDGE-DOC/CI polish, prebuilt multi-SKU engines, runtime reconfigure.

Discretion locked by plans: soft global default; `SENTRY_FALLBACK_TO_TORCH` always-wins; Exit(1) on strict; `fallback_to_torch` status bool field; residual corrupt-engine thrash docs-only.

### 7b. Scope Reduction — PASS

No invented v1/static shadowing of locked decisions:

- Soft/strict is full policy delivery (not “static labels”).
- Residual live-load thrash “document only” is RESEARCH A4 discretion, not a reduction of BACK-03 sticky factory resolve.
- EDGE-RT-04 is lock-by-test (code already torch) — correct for “continue on existing paths,” not omission.
- Dual-model guidance is full SC4 wording (measure-on-device + non-claim), not placeholder deferral.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Backend resolve | API/Backend (factory at serve) | `factory.py` |
| Soft/strict policy | API/Backend (factory + config) | models/load/profile_runtime + factory |
| Reason emission once | API/Backend (factory log) | factory logger |
| Status honesty pass-through | API/Backend (`/api/status`) | status/app/deps/routes |
| Depth / OV inference | API/Backend (existing workers) | serve construction lock only |
| Dual-model VRAM guidance | Docs | export docs + keywords |
| DetectionLoop / bus / store / `/v1` | Frozen | **no edits** |

No security-sensitive selection demoted to browser/UI (UI only renders pass-through fields).

### 8. Nyquist Compliance — PASS

`workflow.nyquist_validation: true` in config.json. RESEARCH has `## Validation Architecture`.  
**Check 8e:** `11-VALIDATION.md` **present**.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 config + ProfileRuntime plumb | 11-01 | 1 | `uv run pytest tests/test_detection_factory.py -q --tb=short` | ✅ |
| T2 factory soft/strict + log + sticky | 11-01 | 1 | `uv run pytest tests/test_detection_factory.py -q --tb=short` | ✅ |
| T3 serve Exit(1) + sticky docs | 11-01 | 1 | `uv run pytest tests/test_detection_factory.py tests/test_cli_serve.py -q --tb=short` | ✅ |
| T1 status/banner/UI fallback_to_torch | 11-02 | 2 | `uv run pytest tests/test_backend_honesty_status.py -q --tb=short` | ✅ |
| T2 EDGE-RT-04 + dual-model docs | 11-02 | 2 | `uv run pytest tests/test_edge_rt04_torch_only.py tests/test_export_docs.py tests/test_backend_honesty_status.py tests/test_detection_factory.py -q --tb=short` | ✅ |

- Every task has `<automated>` verify; no `MISSING`; no watch-mode; no Jetson/real engines required.
- Wave 0 gaps from VALIDATION are implemented as TDD tasks inside plans (not a separate Wave 0 plan) — acceptable (Phase 9/10 precedent).
- Sampling: Wave 1 3/3 automated; Wave 2 2/2 automated → ✅
- Feedback latency: unit/static pytest — ✅ (no E2E suite as primary gate)

### 9. Cross-Plan Data Contracts — PASS

- 11-01 authors `fallback_to_torch` + strict miss shape (`worker=None`, `backend_live=None`); 11-02 pass-through preserves False and null live + reason.
- Reason vocabulary stable across both plans (no rename).
- Status never invents live ORT/TRT; factory remains sole author.
- No strip/sanitize vs re-parse conflict on shared entities.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root. Plans follow Phase 8–10 conventions (TDD, factory sole author, spine freeze, mock-first CI, no new packages).

### 11. Research Resolution — PASS (formality flag)

RESEARCH `## Open Questions` has four items with recommendations; plans lock all four:

1. Strict default on jetson → **No** — soft global; jetson YAML unchanged (11-01)  
2. Strict semantics exit vs detection-off → **`typer.Exit(1)`** (11-01 T3)  
3. Expose fallback mode on status → **`fallback_to_torch` bool field** (11-02 T1)  
4. Harden live-load sticky pause → **document residual only** (11-01 architecture residual note)

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phase 9/10).

### 12. Pattern Compliance — PASS

PATTERNS.md File Classification covers all planned touch files (factory, DeviceConfig, load, profile_runtime, cli, status/app/deps/routes, UI footer, configuration/architecture, export dual-model docs, factory/honesty/export tests, new `test_edge_rt04_torch_only.py`).  
Plans cite PATTERNS + RESEARCH + VALIDATION in `read_first`; `_miss` helper and env mirror match PATTERNS 1:1.  
Shared patterns (sticky one-shot, soft/strict, factory sole author, reason once, status pass-through, EDGE-RT-04 torch lock, spine freeze) appear in plan actions.

---

## Special checks (user-requested strict)

| Check | Result |
|-------|--------|
| BACK-03 + EDGE-RT-04 each in some plan `requirements` | **PASS** — 01: BACK-03; 02: EDGE-RT-04 + BACK-03 |
| Every task has `read_first` + `acceptance_criteria` | **PASS** — all 5 tasks |
| `threat_model` present | **PASS** — both plans |
| Nyquist Dimension 8 / validation map | **PASS** — VALIDATION present; all tasks automated |
| Waves and dependencies correct | **PASS** — 01 wave1; 02 wave2 depends 11-01 |
| must_haves present | **PASS** — truths/artifacts/key_links both plans |
| No shallow actions | **PASS** — concrete numbered steps |
| Soft default + strict opt-in + Exit(1) | **PASS** — locked + tasked |
| Sticky (no loop re-resolve) | **PASS** — inspect + single serve call site |
| Depth/OV not factory-routed | **PASS** — 11-02 T2 |
| Dual-model SC4 + retire Phase 11 deferral | **PASS** — 11-02 T2 |
| No Jetson dependency in CI tasks | **PASS** — mocks/inspect only |
| DetectionLoop frozen | **PASS** — no production loop edits |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Content status |
|------|------|-------|-------|--------------|----------------|
| 11-01 Sticky resolve + soft/strict policy | 1 | 3 | 8 | BACK-03 | Valid |
| 11-02 Dual-model lock + operator status | 2 | 2 | 12 | EDGE-RT-04, BACK-03 | Valid |

---

## Structured Issues

```yaml
issues:
  - dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    plan: null
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity (optional hygiene)."

  - dimension: scope_sanity
    severity: warning
    description: "Plan 11-02 lists 12 files_modified (warning threshold 10) due to full status honesty chain + docs/tests."
    plan: "11-02"
    metrics:
      tasks: 2
      files: 12
    fix_hint: "Acceptable given pass-through must touch status/app/deps/routes/cli/UI together; do not split mid-chain. No rewrite required."

  - dimension: nyquist_compliance
    severity: info
    description: "11-VALIDATION.md frontmatter still has nyquist_compliant: false and wave_0_complete: false (pre-execution draft). Plans implement Wave 0 tests as TDD tasks."
    plan: null
    fix_hint: "After execution starts / Wave 0 checkboxes land, set nyquist_compliant: true and wave_0_complete: true."

  - dimension: verification_derivation
    severity: info
    description: "VALIDATION.md threat ref maps EDGE-RT-04 to T-11-02, but T-11-02 in 11-01 threat_model is config-tampering; EDGE-RT-04 dual-model threats are T-11-07..11 in 11-02."
    plan: null
    fix_hint: "Optional: realign VALIDATION threat refs to 11-02 IDs for audit clarity."
```

**Blockers:** 0  
**Warnings:** 2  
**Info:** 2  

---

## Recommendation

Plans will achieve the Phase 11 goal. BACK-03 and EDGE-RT-04 have concrete tasks, wiring, automated verifies without Jetson, threat models, and no scope reduction of locked decisions. No plan rewrite required.

**Orchestrator action:** Present to user as **ready to execute** (`/gsd:execute-phase 11`). Optional hygiene: mark RESEARCH Open Questions resolved; flip VALIDATION nyquist flags when appropriate.
