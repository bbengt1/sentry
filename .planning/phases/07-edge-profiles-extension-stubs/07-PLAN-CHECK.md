# Phase 7 Plan Check — Edge Profiles & Extension Stubs

**Checked:** 2026-08-08  
**Plans:** `07-01-PLAN.md`, `07-02-PLAN.md`, `07-03-PLAN.md`  
**Checker:** gsd-plan-checker (goal-backward, adversarial)  
**Artifacts read:** CONTEXT, RESEARCH, VALIDATION, PATTERNS, ROADMAP Phase 7, REQUIREMENTS EDGE-01..05, prior `06-PLAN-CHECK.md` format  

**Overall verdict:** **PASS_WITH_FLAGS**

---

## Phase goal (from ROADMAP)

> Make multi-target deployment real and leave clean extension points for post-v1 capabilities.

**Success criteria (must be TRUE):**
1. Desktop GPU full pipeline is documented end-to-end as the primary maker path  
2. Runtime profiles select model tiers/backends for desktop, Jetson-class, and CPU/lite  
3. ONNX and/or TensorRT export recipes exist with on-device engine build notes  
4. Headless mode serves perception API without the UI  
5. Stubs/scaffolds exist for ROS2 bridge, multi-cam schema tests, and voice plugin no-op  
6. Safety/privacy disclaimers and non-autonomy positioning are finalized in docs  

**Requirements:** EDGE-01, EDGE-02, EDGE-03, EDGE-04, EDGE-05  

---

## Coverage Summary

| Requirement | Roadmap success | Plans | Tasks | Status |
|-------------|-----------------|-------|-------|--------|
| EDGE-01 | Desktop GPU E2E primary path docs | 07-03 | T2 desktop-gpu.md + README + doc tests | Covered |
| EDGE-02 | Profiles select tiers/backends at serve | 07-01 | T1 ProfileRuntime, T2 serve wiring + probe + banner | Covered |
| EDGE-03 | ONNX/TRT recipes + on-device engine notes | 07-02 | T1 docs/export + Jetson packaging, T2 export_yolo.py | Covered |
| EDGE-04 | Multi-cam tests + ROS2 stub + voice no-op | 07-03 | T1 camera_id multi, Ros2PerceptionBridge, VoiceNullSink | Covered |
| EDGE-05 | Headless API without UI | 07-01 | T3 create_app(serve_ui) + `--no-ui` | Covered |

### Goal-backward truth map

| Must be TRUE | Delivered by | Wiring |
|--------------|--------------|--------|
| Profiles drive detector/OV/depth + device policy | `profile_runtime` + `tier_to_open_vocab_weight` + depth Small allowlist + `device_for_backend` | `cli.serve` constructs workers from `ProfileRuntime` |
| desktop→s, jetson/cpu→n; OV n/s from detector_tier | Profile YAML + helpers + tests | Parametrized profile matrix tests |
| preferred_backend honesty (no silent TRT/ORT live) | `device_for_backend` + banner/log language | tensorrt→cuda-like device; onnxruntime→cpu; live PyTorch stated |
| Serve default stays cpu-fallback | CLI Option default + tests | No CUDA auto-switch |
| Headless: no Live Preview HTML; `/v1` + `/api` live | `serve_ui` + root gate + `--no-ui` | MJPEG kept; GET `/` 404 JSON |
| Headless ≠ auth | Non-localhost warning retained + safety docs | Explicit must_have + T-07-01 |
| Export recipes without Jetson CI | docs/export + scripts/export | Keyword + CLI parse tests only |
| On-device TRT; no prebuilt engines; no cross-SKU copy | jetson-packaging + export docs + content tests | Hard rules in action + negative phrase checks |
| Pi/CPU lite honesty | Export + Jetson docs keywords | No unmeasured dual-model realtime FPS |
| Multi-cam camera_id extension key | Schema multi-id tests | v1 single active source documented |
| ROS2 stub importable, no rclpy | `Ros2PerceptionBridge` NotImplemented | Not auto-registered as sink |
| Voice no-op discoverable | VoiceNullSink + entry point `voice-null` | builtins + pyproject |
| Desktop primary path documented | `docs/desktop-gpu.md` + README | Links extras, profile, `/v1`, headless, AGPL |
| Safety/privacy/non-autonomy finalized | `docs/safety-and-privacy.md` + README | Perception-only, free-space not interlock, localhost |

---

## Dimension Results

### 1. Requirement Coverage — PASS

- All five requirement IDs appear in plan frontmatter:
  - `07-01`: EDGE-02, EDGE-05  
  - `07-02`: EDGE-03  
  - `07-03`: EDGE-04, EDGE-01  
- Matches ROADMAP plan split exactly.  
- No phase-mapped REQUIREMENTS.md EDGE item is orphaned.  
- Success criterion 6 (safety/privacy) is owned by 07-03 with dedicated doc + keyword tests (cross-cutting, not a separate EDGE ID).

### 2. Task Completeness — PASS

| Plan | Tasks | Files | Action | Verify (automated) | Done |
|------|-------|-------|--------|--------------------|------|
| 07-01 | 3 | all | all | all pytest | all |
| 07-02 | 2 | all | all | all pytest | all |
| 07-03 | 2 | all | all | all pytest | all |

`verify.plan-structure` **valid** for all three plans; zero structural errors/warnings.  
Actions name concrete types, device policy table cases, doc hard rules, NotImplemented shapes, and CI constraints (no weight download / no real export / no Jetson).

### 3. Dependency Correctness — PASS

```
07-01 (wave 1, depends_on: [])
    ├─→ 07-02 (wave 2, depends_on: [07-01])
    └─→ 07-03 (wave 2, depends_on: [07-01])
```

- Acyclic; wave = max(deps)+1 consistent.  
- 07-02 ∥ 07-03 after 07-01 is correct (export docs vs stubs/docs).  
- Soft note in 07-02: may land same milestone as profile wiring language; does not hard-import unfinished helpers into export scripts beyond KNOWN_WEIGHTS.  
- No forward artifact dependency from 07-01 into unbuilt export/ROS2 code.

### 4. Key Links Planned — PASS

Critical wiring is task-level, not artifact-only:

| Link | Plan |
|------|------|
| `cli.serve` → `profile_runtime(cfg)` → YOLO/YOLOE/Depth workers | 07-01 T2 |
| preferred_backend tensorrt/onnxruntime → device policy + honesty log | 07-01 T1–T2 |
| `--no-ui` → `create_app(serve_ui=False)` → root gate | 07-01 T3 |
| `export_yolo.py` → Ultralytics `export` + KNOWN_WEIGHTS allowlist | 07-02 T2 |
| Export/Jetson docs → on-device engine / no cross-SKU copy | 07-02 T1 |
| VoiceNullSink → register_builtins + EP `voice-null` | 07-03 T1 |
| Ros2PerceptionBridge → NotImplemented + README | 07-03 T1 |
| README → desktop-gpu + export + safety | 07-02 T1, 07-03 T2 |

### 5. Scope Sanity — PASS with warnings

| Plan | Tasks | Frontmatter files | Heaviest task |
|------|-------|-------------------|---------------|
| 07-01 | 3 (target) | 18 | T1: 11 files (helpers + multi-test) |
| 07-02 | 2 (target) | 10 | T1: 7 docs/tests |
| 07-03 | 2 (target) | 15 | T1: 10 stubs/tests |

- Task counts within 2–3 target.  
- **Warning:** 07-01 at 18 `files_modified` (above 15 guideline); mitigated by clean TDD splits (helpers → serve wire → headless).  
- **Warning:** 07-03 at 15 files (borderline); T1 is dense (multi-cam + ROS2 + voice + registry).

### 6. Verification Derivation — PASS

must_haves truths are operator-observable (profiles select weights/devices, headless serves API, export recipes honest, stubs import, desktop path documented). Artifacts and key_links map to those truths. No “library installed” style truths. Honesty constraints (TRT live path, prebuilt engines, Pi FPS, free-space not interlock) are first-class truths + tests.

### 7. Context Compliance — PASS

| Locked decision | Honored? |
|-----------------|----------|
| Profiles drive detector_tier / depth_tier / preferred_backend at serve | Yes — ProfileRuntime + serve wiring |
| Export = recipes + scripts; no Jetson in CI | Yes — 07-02 docs/scripts only |
| Headless = API without static UI (`--no-ui`) | Yes — RESEARCH discretion lock |
| Stubs only for ROS2 / multi-cam / voice | Yes — NotImplemented + schema tests + no-op sink |
| Perception-only + privacy + non-autonomy finalized | Yes — safety-and-privacy.md |
| Local OSS; allow_cloud false | Yes — profile matrix + safety docs |
| No React rewrite | Yes — not in scope; headless gates HTML only |

**Discretion locked in plans (valid):** keep serve default `cpu-fallback`; light probe; `--no-ui` not `sentry api`; importable ROS2 bridge; OV off default + n-tier weights on jetson/cpu; no tensorrt pip extra.

**Deferred excluded:** full ROS2 package, multi-cam fusion UX, real voice ASR/TTS, prebuilt TRT engines, OpenVINO first-class runtime, authenticated remote API, metric free-space — all out-of-scope or explicitly forbidden.

### 7b. Scope Reduction — PASS

No silent v1/hardcoded/stub reductions of locked decisions.  
- “Device policy honesty for preferred_backend=tensorrt/onnxruntime” is the **full** CONTEXT/RESEARCH decision, not a shadow of a live TRT backend.  
- “Export docs+scripts only” and “extension stubs only” match locked deliverable shape.  
- “Depth export = feasibility notes” matches RESEARCH hard rule #5.  
- Product “v1 single active source” language is intentional, not planner invented scope cut.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Profile → weights / device policy | API / Backend | `profile_runtime` + `cli.serve` |
| Device probe | API / Backend | `backend/protocols.py` |
| Headless UI gate | Frontend Server (FastAPI route) | `routes_preview` + `create_app` |
| Export ONNX/TRT | Docs/scripts offline | `docs/export`, `scripts/export` |
| ROS2 / voice / multi-cam hooks | Plugins / extensions stubs | extensions + builtins |
| Safety/privacy copy | Docs | safety-and-privacy.md |

No security-sensitive capability demoted to browser. No TRT runtime smuggled into core extras.

### 8. Nyquist Compliance — PASS

VALIDATION.md present. Nyquist enabled (absent key = enabled; section present in RESEARCH).

| Task | Plan | Wave | Automated Command | Status |
|------|------|------|-------------------|--------|
| T1 ProfileRuntime helpers | 07-01 | 1 | `pytest tests/test_profile_application.py tests/test_model_cache.py tests/test_depth_mapping.py tests/test_config_profiles.py` | ✅ |
| T2 serve wire + probe + banner | 07-01 | 1 | `pytest tests/test_profile_application.py tests/test_cli_serve.py tests/test_backend_protocols.py …` | ✅ |
| T3 headless | 07-01 | 1 | `pytest tests/test_headless_serve.py tests/test_cli_serve.py tests/test_api_preview.py …` | ✅ |
| T1 export docs | 07-02 | 2 | `pytest tests/test_export_docs.py` | ✅ |
| T2 export script CLI | 07-02 | 2 | `pytest tests/test_export_docs.py tests/test_export_script_cli.py` | ✅ |
| T1 stubs multi-id/ROS2/voice | 07-03 | 2 | `pytest tests/test_camera_id_multi.py tests/test_extensions_stubs.py tests/test_plugins_registry.py …` | ✅ |
| T2 desktop + safety docs | 07-03 | 2 | `pytest tests/test_desktop_docs.py tests/test_safety_docs.py …` | ✅ |

- No `<automated>MISSING</automated>`; Wave 0 test files created inside TDD tasks (same paths as VALIDATION/RESEARCH).  
- Sampling: Wave 1 3/3; Wave 2 4/4 with automated verify → ✅  
- CI rules explicit: no real `model.export`, no weight download, no Jetson, no rclpy → ✅  

**Note:** VALIDATION.md frontmatter still `nyquist_compliant: false` / `wave_0_complete: false` (pre-execution draft). Content sufficient for planning; refresh metadata after tests land.

### 9. Cross-Plan Data Contracts — PASS

- 07-01 owns live profile/device semantics; 07-02 documents offline export and references profile names without dual-implementing device policy.  
- 07-02 KNOWN_WEIGHTS allowlist aligned with 07-01 cache (import preferred; hardcoded fallback only if awkward).  
- 07-03 docs describe `--profile desktop-gpu` / `--no-ui` as shipped by 07-01 (depends_on enforces order).  
- Parallel README edits (07-02 export section vs 07-03 desktop/safety) explicitly coordinated with distinct headings — residual merge risk only (warning below).  
- No strip/sanitize vs re-parse conflict on shared entities.

### 10. CLAUDE.md Compliance — SKIPPED

No `./CLAUDE.md` in project root.

### 11. Research Resolution — PASS (formality warning)

RESEARCH `## Open Questions` has three items with explicit recommendations; plans lock all three:

1. YOLOE export experimental + PyTorch OV fallback → 07-02  
2. Measure Jetson on device; no priority scheduler → 07-02 packaging  
3. No CUDA auto-default profile → 07-01 keep cpu-fallback  

Section is **not** titled `## Open Questions (RESOLVED)` — formality only (same class as Phase 6).

### 12. Pattern Compliance — PASS with minor note

PATTERNS.md maps profiles YAML, cache tiers, CLI flags, create_app headless, NullSink/voice, export docs honesty, multi-cam schema tests. Plans cite PATTERNS + RESEARCH in `read_first` and actions.

**Note:** New module `profile_runtime.py` is not a separate File Classification row (covered via RESEARCH sketch + Pattern 1 / shared profile→serve wiring). Acceptable; not a blocker.

---

## Special checks (user-requested)

| Check | Result |
|-------|--------|
| EDGE-01..05 all in frontmatter | **PASS** — complete partition across three plans |
| Headless honesty (API without HTML; not auth) | **PASS** — serve_ui gate + non-localhost warning + safety doc “headless ≠ auth” |
| Profile honesty (no silent TRT live / no CUDA auto-switch) | **PASS** — device_for_backend + banner + default cpu-fallback |
| No Jetson required for tests | **PASS** — all automated verifies are unit/content/CLI-parse |
| Anti-pattern: overclaim TRT live | **PASS** — explicit forbid + T-07-02 / T-7-03 |
| Anti-pattern: prebuilt engines | **PASS** — docs + verification “no .engine committed” |
| Anti-pattern: full ROS2 product | **PASS** — NotImplemented stub; no rclpy; out of scope |
| Threat models | **PASS** — each plan has STRIDE register; VALIDATION T-7-01..07 aligned |
| Deferred not smuggled | **PASS** — fusion, ASR/TTS, prebuilt engines, remote auth excluded |

---

## Plan Summary

| Plan | Wave | Tasks | Files | Requirements | Status |
|------|------|-------|-------|--------------|--------|
| 07-01 Runtime profiles + headless | 1 | 3 | 18 | EDGE-02, EDGE-05 | Valid |
| 07-02 Export recipes + Jetson notes | 2 | 2 | 10 | EDGE-03 | Valid |
| 07-03 Stubs + desktop/safety docs | 2 | 2 | 15 | EDGE-04, EDGE-01 | Valid |

---

## Issues

### Blockers

None.

### Warnings (should fix; execution may proceed)

```yaml
issues:
  - plan: "07-01"
    dimension: scope_sanity
    severity: warning
    description: "Plan 07-01 lists 18 files_modified (above 15 guideline) though only 3 well-scoped TDD tasks."
    fix_hint: "Acceptable if executor follows task boundaries (helpers → serve → headless) with intermediate pytest; no mandatory split."

  - plan: "07-03"
    dimension: scope_sanity
    severity: warning
    description: "Plan 07-03 Task 1 packs multi-cam tests + ROS2 package + VoiceNullSink + pyproject EP + registry tests (~10 files)."
    task: 1
    fix_hint: "Optional mid-task checkpoint: land camera_id tests first, then ROS2+voice; keep single plan."

  - plan: null
    dimension: key_links_planned
    severity: warning
    description: "Wave 2 parallel plans both edit README.md (07-02 export link section; 07-03 desktop/safety/profiles). Plans coordinate headings but merge conflict risk remains."
    fix_hint: "Executor: apply additive distinct headings; if conflict, rebase 07-03 README after 07-02 or vice versa before SUMMARY."

  - plan: null
    dimension: nyquist_compliance
    severity: warning
    description: "07-VALIDATION.md Wave 0 checklist omits tests/test_safety_docs.py (present in 07-03) and still has nyquist_compliant: false / wave_0_complete: false pre-execution metadata."
    fix_hint: "Add test_safety_docs.py to Wave 0 list; flip metadata after execute when suite green."

  - plan: null
    dimension: research_resolution
    severity: warning
    description: "RESEARCH.md Open Questions have recommendations locked in plans, but section is not marked (RESOLVED)."
    fix_hint: "Rename to '## Open Questions (RESOLVED)' and prefix each answer with RESOLVED for audit clarity."

  - plan: "07-01"
    dimension: pattern_compliance
    severity: info
    description: "profile_runtime.py is central to EDGE-02 but not listed as its own PATTERNS.md File Classification row."
    fix_hint: "Optional PATTERNS touch-up; plans already cite RESEARCH ProfileRuntime sketch — not required before execute."
```

### Info

- 07-02 hard-depends on 07-01 even though export is mostly independent — conservative and fine for profile-name honesty in docs.  
- Optional `SENTRY_NO_UI` is nice-to-have only; flag is sufficient for EDGE-05.  
- Depth Base/Large rejection is correctly treated as NC/license honesty, not a new depth product.

---

## Recommendation

**0 blockers.** Plans will achieve Phase 7 goal and all EDGE-01..05 requirements if executed as written, with honest multi-target/profile/headless/export semantics and no deferred-product scope creep.

Optional polish before or during execute (non-blocking): sync VALIDATION Wave 0 + mark RESEARCH Open Questions resolved; coordinate README merges between 07-02 and 07-03.

**Orchestrator action:** Do **not** re-plan. Present plans to user as **ready to execute**. Proceed with `/gsd:execute-phase 7` when approved.

---

## PLAN CHECK PASSED (WITH FLAGS)
