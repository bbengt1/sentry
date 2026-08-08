# Phase 6 Plan Check — Developer Controls & Open-Vocab

**Checked:** 2026-08-08  
**Plans:** `06-01-PLAN.md`, `06-02-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** CONTEXT, RESEARCH, VALIDATION, UI-SPEC, PATTERNS, ROADMAP Phase 6, REQUIREMENTS UI-03..05 / OVD-01..03  

---

## Phase goal (from ROADMAP)

> Make the developer console fully interactive and add open-vocabulary detection as the flexible query path.

**Success criteria (must be TRUE):**
1. Developer can enable/disable detection, depth, and free-space stages live  
2. Thresholds (conf, depth/free-space cutoffs) adjust interactively from the UI  
3. Performance telemetry is visible in the dashboard  
4. Open-vocab prompts produce detections for custom classes via local OSS model  
5. Open-vocab can run on-demand or lower-rate without blocking the fixed-class path  

**Requirements:** UI-03, UI-04, UI-05, OVD-01, OVD-02, OVD-03  

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| UI-03 | Stage enable/disable live | 06-01 | T1 enable gates, T2 PATCH pipeline, T3 checkboxes | Covered |
| UI-04 | Conf + free-space near/mid cutoffs live | 06-01 | T1 FreeSpaceLoop cuts, T2 pipeline PATCH, T3 sliders; existing det conf kept | Covered |
| UI-05 | Capture + stage FPS/latency on dashboard | 06-01 | T2 status flags/metrics, T3 footer telemetry | Covered |
| OVD-01 | Text prompts → local YOLOE detections | 06-02 | T1 worker + schema, T2 API, T3 prompt UX | Covered |
| OVD-02 | On-demand / lower-rate; fixed-class unblocked | 06-02 | T2 OpenVocabLoop modes + independence tests | Covered |
| OVD-03 | OV on dashboard + `/v1` when enabled | 06-02 | T2 assemble/overlay/MJPEG/status, T3 UI | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Stages toggle without restart; disabled = skip compute | PipelineState + loop `set_enabled` + Event gate (not stop/start) | PATCH `/api/pipeline/config` → loops; store `clear_*` once |
| Free-space near/mid adjust live | FreeSpaceLoop cut knobs + pipeline PATCH | UI sliders → pipeline config → next `compute_free_space` |
| Det conf adjustable | Existing `/api/detection/config` (kept) | Existing conf slider unchanged |
| Stage FPS/latency visible | `/api/status` + store metrics + footer | Status poll already has capture FPS; plan adds stage fps fields in UI |
| OV text prompts via YOLOE | `YoloeOpenVocabWorker` + set_classes dirty flag | `/api/open-vocab/*` cold path only |
| OV off / on_demand / continuous every_n=3 | `OpenVocabLoop` separate thread | Default off; POST run arms one-shot |
| Fixed-class not blocked | Separate product slot; never `set_detections` from OV | Assemble merges fixed then OV |
| OV on MJPEG + stream | assemble + overlay color + preview | `source=open_vocab` + magenta boxes |
| AGPL disclosed | THIRD_PARTY_MODELS + UI/README note | Doc tests |
| No React rewrite | Extend static `index.html` only | Explicit in both plans |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- All six requirement IDs appear in plan frontmatter (`06-01`: UI-03/04/05; `06-02`: OVD-01/02/03).
- No phase-mapped REQUIREMENTS.md item is orphaned.
- UI-04 “depth/free-space cutoffs” correctly interpreted per RESEARCH/CONTEXT as free-space near/mid cuts (depth-derived bands); depth_mode remains via existing PATCH `/api/depth/config` (not a missing cutoff control).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done |
|------|-------|-------|--------|--------------------|------|
| 06-01 | 3 | all | all | all pytest | all |
| 06-02 | 3 | all | all | all pytest | all |

`verify.plan-structure` valid for both plans; zero structural errors. Actions name concrete types, methods, validation rules, and test fakes.

### 3. Dependency Correctness — PASS

```
06-01 (wave 1, depends_on: [])  →  06-02 (wave 2, depends_on: [06-01])
```

- Acyclic; wave assignment consistent.
- Shared files (`index.html`, store, app, cli, preview, status) only touch in sequence via depends_on.
- No forward reference to unbuilt OV artifacts from 06-01 (explicit out-of-scope).

### 4. Key Links Planned — PASS

Critical wiring is task-level, not artifact-only:

| Link | Plan |
|------|------|
| PATCH pipeline → `set_enabled` + free-space cuts | 06-01 T2 |
| Loop enable gate → skip `process` / clear product | 06-01 T1 |
| index.html → pipeline/config + status | 06-01 T3 |
| OpenVocabLoop → `set_open_vocab` only | 06-02 T2 |
| assemble → fixed then OV + source tags | 06-02 T2 |
| overlay / MJPEG → `Detection.source` color | 06-02 T2 |
| index.html → `/api/open-vocab/*` | 06-02 T3 |
| serve → inject PipelineState / OV loop lifecycle | 06-01 T2, 06-02 T2 |

### 5. Scope Sanity — PASS with warnings

| Plan | Tasks | Frontmatter files | Heaviest task files |
|------|-------|-------------------|---------------------|
| 06-01 | 3 (target) | 18 | T2: 9 |
| 06-02 | 3 (target) | 26 | T2: 15 |

- Task counts are within target (2–3).
- File counts exceed the 15+ guideline (warning, not fail): many are thin wiring + new test modules under TDD; actions are highly specified, which mitigates context risk.
- **Warning:** 06-02 Task 2 packs loop + API + assemble + overlay + app/deps/cli + five test files — largest single-task surface in the phase.

### 6. Verification Derivation — PASS

must_haves truths are user/operator-observable (toggle stages, adjust cuts, see FPS, OV prompts, non-blocking fixed path, AGPL). Artifacts and key_links map to those truths. No “library installed” style truths.

### 7. Context Compliance — PASS

| Locked decision | Honored? |
|-----------------|----------|
| Developer-first overlays + controls | Yes |
| Fixed-class primary; OV secondary | Yes — default off, every_n=3, separate loop |
| UI/API share PerceptionStore | Yes — fourth product + assemble |
| Local OSS; AGPL documented | Yes — YOLOE + THIRD_PARTY + UI note |
| Disabled = skip compute, not hide-only | Yes — enable gates + clear_* |
| No React rewrite | Yes — static index.html only |
| Source switcher not in Phase 6 UI | Yes — deferred / CLI-only |

Deferred (edge packaging, voice/VLM, always-on OV default) excluded. Discretion areas chosen and locked in plans (unified `/api/pipeline/config`, detect extra, OpenVocabProduct + `source`, free-space cuts wired).

### 7b. Scope Reduction — PASS

No silent v1/hardcoded/stub reductions of locked decisions. “Boxes only / ignore masks for v1” matches RESEARCH discretion, not a CONTEXT lock. HTML “placeholder” is UX copy, not deferred implementation.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

- Control + inference + merge on API/Backend  
- Browser only RPC (checkboxes, sliders, prompt)  
- Overlays server-drawn (MJPEG)  
- Capture always-on; stage toggles must not stop CaptureLoop  

No auth/security capability demoted to browser.

### 8. Nyquist Compliance — PASS

VALIDATION.md present. `workflow.nyquist_validation` enabled.

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 enable gates + cuts | 06-01 | 1 | `pytest tests/test_loop_enable_gates.py tests/test_free_space_runtime_cuts.py` | ✅ |
| T2 pipeline API + wiring | 06-01 | 1 | `pytest tests/test_pipeline_config.py` + related | ✅ |
| T3 Live Preview controls | 06-01 | 1 | `pytest tests/test_api_preview.py` + related | ✅ |
| T1 YOLOE worker + AGPL | 06-02 | 2 | `pytest tests/test_yoloe_worker.py` + cache/doc | ✅ |
| T2 OV loop/API/assemble | 06-02 | 2 | `pytest tests/test_open_vocab_loop.py` + api/assemble/overlay | ✅ |
| T3 OV UX | 06-02 | 2 | `pytest tests/test_api_open_vocab.py` + preview | ✅ |

- No `<automated>MISSING</automated>`; Wave 0 test files are created inside TDD tasks (same paths as RESEARCH Wave 0 gaps).
- Sampling: each wave has 3/3 tasks with automated verify → ✅  
- Mock rule explicit: FakeModel / no YOLOE weight download in CI → ✅  

**Note:** VALIDATION.md frontmatter still `nyquist_compliant: false` / `wave_0_complete: false` (pre-execution draft). Content is sufficient for planning; metadata should be refreshed after tests land.

### 9. Cross-Plan Data Contracts — PASS

- 06-01 introduces `clear_*` and PipelineState; 06-02 extends with `clear_open_vocab` / OpenVocabProduct without dual-writing `set_detections`.
- Assemble merge contract: fixed first, then OV; completeness OR of both products — single consumer, no conflicting sanitizers.
- Shared UI file edited in wave order only.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root.

### 11. Research Resolution — PASS (with formality warning)

RESEARCH `## Open Questions` has six items with explicit recommendations (weight 26s, clear-on-disable, `source` field, every_n=3, CLI-only source switcher, independent stage flags). Plans lock all six. Section is not titled `## Open Questions (RESOLVED)` — formality only.

### 12. Pattern Compliance — PASS

PATTERNS.md maps new files to analogs (`routes_detection`, `yolo_worker`, `DetectionLoop`, etc.). Both plans cite PATTERNS + RESEARCH patterns in `read_first` and actions (extra=forbid, injectable model, enable Event, conf debounce).

---

## Special checks (user-requested)

| Check | Result |
|-------|--------|
| Stage flags **not** teardown | **PASS** — `set_enabled` / Event; explicit ban on stop()/start() for UI toggles; T-06-02 / T-6-02 |
| OV not blocking fixed-class | **PASS** — separate loop + OpenVocabProduct; independence tests; dual-writer threat mitigated |
| Mock tests (no weight download CI) | **PASS** — FakeModel; handler must not call process; lazy load on worker thread |
| AGPL | **PASS** — THIRD_PARTY_MODELS active row + UI/README first-run note + doc tests |
| No React rewrite required | **PASS** — static HTML only; CONTEXT/UI-SPEC honored |
| Threat models | **PASS** — both plans include STRIDE registers; VALIDATION lists T-6-01..05; prompt caps, no motor fields, localhost default |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 06-01 Control plane + interactive UI | 1 | 3 | 18 | UI-03, UI-04, UI-05 | Valid |
| 06-02 Open-vocab + stream/UI | 2 | 3 | 26 | OVD-01, OVD-02, OVD-03 | Valid |

---

## Issues

### Blockers

None.

### Warnings (should fix; execution may proceed)

```yaml
issues:
  - plan: "06-02"
    dimension: scope_sanity
    severity: warning
    description: "Plan 06-02 lists 26 files_modified; Task 2 alone touches 15 files (loop, API, assemble, overlay, app/deps/cli, multiple tests). Quality risk if executor context saturates."
    task: 2
    fix_hint: "Optional split: 06-02a worker+loop+API tests; 06-02b assemble+overlay+serve+UI — or keep single plan but execute Task 2 as two commits with intermediate pytest."

  - plan: "06-01"
    dimension: scope_sanity
    severity: warning
    description: "Plan 06-01 lists 18 files_modified (above 15 guideline) though only 3 well-scoped tasks."
    fix_hint: "Acceptable if executor follows TDD task boundaries; no mandatory split."

  - plan: null
    dimension: nyquist_compliance
    severity: warning
    description: "06-VALIDATION.md Wave 0 checklist names tests/test_loop_enable_flags.py but plans/RESEARCH use tests/test_loop_enable_gates.py; VALIDATION omits test_free_space_runtime_cuts.py and test_detection_overlay.py present in plans."
    fix_hint: "Sync VALIDATION.md Wave 0 list and filenames to plan/RESEARCH test paths before execute-phase."

  - plan: null
    dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations and are locked in plans, but section is not marked (RESOLVED)."
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity."
```

### Info

- Depth_mode UI control is optional (API already exists); not required by UI-SPEC layout — no gap.
- Capture FPS already rendered; 06-01 correctly extends stage FPS/latency visibility for UI-05.

---

## Recommendation

**0 blockers.** Plans will achieve Phase 6 goal and all mapped requirements if executed as written. Optional polish: align VALIDATION.md test names; consider splitting 06-02 Task 2 only if executor hits context pressure.

Proceed with `/gsd:execute-phase 6`.

---

## PLAN CHECK PASSED
