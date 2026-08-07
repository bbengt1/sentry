# Phase 2 Plan Check — Camera Ingest & Live Preview

**Checked:** 2026-08-07  
**Plans verified:** 02-01, 02-02, 02-03  
**Status:** PLAN CHECK PASSED  
**Gate type:** Revision Gate (pre-execution)

---

## Verdict

**PLAN CHECK PASSED**

Plans will achieve the Phase 2 goal and all eight roadmap requirements if executed as written. No blockers. Warnings below are hygiene / map-alignment only and do not prevent execution.

---

## Phase Goal (source of truth)

> Prove “any camera works” with a realtime capture loop, keep-latest frame bus, and browser preview — no models yet.

**ROADMAP Success Criteria:**

1. USB camera and file/video source produce live frames with stable `frame_id`s  
2. Synthetic source powers automated tests without hardware  
3. RTSP/network camera source works or is documented with known limits  
4. Frame bus drops oldest under load and reports drop metrics (no unbounded queue growth)  
5. Browser shows live preview; camera unplug surfaces a clear error and recovery path  
6. Default server bind is localhost  

**Requirements:** CAM-01, CAM-02, CAM-03, CAM-04, CAM-05, CAM-06, UI-01, MODEL-03  

---

## Coverage Summary

| Requirement | Plans | Tasks | Status |
|-------------|-------|-------|--------|
| CAM-01 USB UVC | 02-01 | T3 (OpenCVSource + mock) | Covered |
| CAM-02 File/video | 02-01 | T3 (file fixture + loop) | Covered |
| CAM-03 Synthetic | 02-01 | T2 (patterned BGR ImageFrame) | Covered |
| CAM-04 RTSP | 02-03 | T3 (plugin + mock + docs limits) | Covered |
| CAM-05 Keep-latest bus | 02-02 | T1 (FrameBus + metrics) | Covered |
| CAM-06 Disconnect/reconnect | 02-02 T2 + 02-03 T1/T2 (status API + UI pill) | Covered |
| UI-01 Live preview | 02-03 | T1 MJPEG + T2 static HTML | Covered |
| MODEL-03 Localhost bind | 02-03 | T3 (`--host` default 127.0.0.1) | Covered |

### Goal-backward (ROADMAP SC → plans)

| # | Success criterion | Delivering tasks | Status |
|---|-------------------|------------------|--------|
| 1 | USB + file live frames / stable frame_id | 02-01 T3 | Covered (USB mock + file fixture; hardware manual) |
| 2 | Synthetic powers CI | 02-01 T2 | Covered |
| 3 | RTSP works or documented limits | 02-03 T3 + docs/camera-sources.md | Covered |
| 4 | Bus drop + metrics, no unbounded queue | 02-02 T1 | Covered |
| 5 | Browser preview + unplug error/recovery | 02-02 T2 + 02-03 T1–T2; manual USB | Covered |
| 6 | Default bind localhost | 02-03 T3 + tests/test_cli_serve.py | Covered |

---

## Plan Summary

| Plan | Wave | depends_on | Tasks | Requirements | Threat model | Structure |
|------|------|------------|-------|--------------|--------------|-----------|
| 02-01 | 1 | [] | 3 | CAM-01..03 | Present (T-2-01..04, SC) | Valid |
| 02-02 | 2 | [02-01] | 3 | CAM-05, CAM-06 | Present | Valid |
| 02-03 | 3 | [02-01, 02-02] | 3 | CAM-04, UI-01, MODEL-03 | Present | Valid |

Dependency graph: acyclic, wave-consistent (`1 → 2 → 3`). No forward refs.

---

## Dimension Results

### 1. Requirement Coverage — PASS

All eight Phase 2 requirement IDs appear in plan `requirements` frontmatter and map to concrete tasks. No roadmap requirement orphaned. Deferred requirements (DET-*, UI-02+, full `/v1`) correctly excluded.

### 2. Goal-Backward — PASS

All six ROADMAP success criteria have implementing tasks and `must_haves.truths`. Vertical slice complete: sources → bus → capture thread → FastAPI MJPEG/static → `sentry serve`.

### 3. Task Completeness — PASS

`gsd-sdk query verify.plan-structure` → all three plans `valid: true`, zero errors. Every task has:

- `<files>`
- `<read_first>`
- `<action>` (concrete steps)
- `<verify>` with `<automated>`
- `<acceptance_criteria>` + `<done>`

TDD tasks also include `<behavior>`.

### 4. Concrete Actions — PASS

Actions specify types, fields, backoff constants, API paths, CLI flags, package pins, and anti-patterns (no torch/PyAV/WebRTC, no numpy on Pydantic `Frame`, no capture in request handlers). Not vague “implement auth”-style tasks.

### 5. Dependencies & Waves — PASS

| Plan | Wave | depends_on | Consistent? |
|------|------|------------|-------------|
| 02-01 | 1 | [] | Yes |
| 02-02 | 2 | ["02-01"] | Yes |
| 02-03 | 3 | ["02-01","02-02"] | Yes |

Cross-plan contracts: `ImageFrame` (01→02→03), `FrameBus`/`CaptureLoop`/`build_status` (02→03), Wave 0 skip stubs (01→02/03 fill-in). Compatible.

### 6. Scope Sanity — PASS (with warnings)

| Plan | Tasks | files_modified count | Notes |
|------|-------|----------------------|-------|
| 02-01 | 3 (target) | ~24 | Inflated by Wave 0 skip stubs + fixtures; implementation core is smaller |
| 02-02 | 3 | 8 | Within target |
| 02-03 | 3 | ~16 | RTSP + serve + docs + API surface; dense but coherent |

No plan exceeds 5 tasks. No ML/detection/depth/WebRTC scope creep. Forbidden packages explicitly excluded.

### 7. Context Compliance — PASS

| Locked decision | Honored? |
|-----------------|----------|
| Sources → Frame Bus only | Yes (02-02 loop publishes; FastAPI only `get_latest`) |
| Keep-latest, no unbounded queues | Yes (depth-1 mailbox, anti-queue rules) |
| UI subscriber only | Yes (MJPEG/status poll) |
| Localhost default bind | Yes (MODEL-03) |
| OpenCV headless first; PyAV deferred | Yes |
| MJPEG first; WebRTC later | Yes |
| Phase 1 package/CLI names | Yes |

**Discretion used appropriately:** `ImageFrame` dataclass (not numpy on Frame); capture daemon thread + async FastAPI; static HTML; backoff 0.25→5.0×2; CLI `sentry serve`.

**Deferred ideas excluded:** detection/depth/free-space, WebRTC, full `/v1`, Vite/React dashboard, edge packaging.

**No scope reduction** of locked decisions (no “v1 static labels” style downgrades). RTSP “OpenCV best-effort + documented limits” matches CAM-04 and research acceptance bar.

### 7b. Scope Reduction — PASS

No silent simplification of D-decisions. CAM-04 honesty path is requirement-aligned, not reduction.

### 7c. Architectural Tier Compliance — PASS

Matches RESEARCH Architectural Responsibility Map:

| Capability | Expected tier | Plan placement |
|------------|---------------|----------------|
| Capture I/O | Backend capture thread | 02-01 sources + 02-02 CaptureLoop |
| FrameBus | Backend | 02-02 |
| MJPEG encode | API async | 02-03 routes |
| Live HTML | Static / browser | 02-03 index.html |
| Bind policy | API / CLI | 02-03 serve |

No security-sensitive logic placed in browser tier.

### 8. Nyquist Compliance — PASS

| Check | Result |
|-------|--------|
| 8e VALIDATION.md exists | Yes (`02-VALIDATION.md`) |
| 8a Automated verify on every task | Yes (`uv run pytest` / ruff / imports) |
| 8b Feedback latency | OK (~30–60s budget; no `--watch`) |
| 8c Sampling continuity | 3/3 tasks per wave have automated verify |
| 8d Wave 0 completeness | 02-01 T1 creates skip stubs for later plans’ test files |

| Task | Plan | Wave | Automated Command (abbrev) | Status |
|------|------|------|----------------------------|--------|
| T1 | 02-01 | 1 | uv sync + import smoke + pytest schemas + ruff | ✅ |
| T2 | 02-01 | 1 | pytest synthetic/registry/smoke/schemas + sentry smoke + ruff | ✅ |
| T3 | 02-01 | 1 | pytest opencv/file/synthetic/registry/smoke + health + ruff | ✅ |
| T1 | 02-02 | 2 | pytest test_frame_bus + ruff | ✅ |
| T2 | 02-02 | 2 | pytest bus+loop+synthetic + ruff | ✅ |
| T3 | 02-02 | 2 | pytest bus+loop + full suite + ruff | ✅ |
| T1 | 02-03 | 3 | uv sync + pytest api_preview + ruff | ✅ |
| T2 | 02-03 | 3 | pytest api_preview + file/grep UI-SPEC strings + ruff | ✅ |
| T3 | 02-03 | 3 | pytest rtsp/cli/api/bus/loop + serve --help + full suite + ruff | ✅ |

Sampling: each wave 3/3 verified → ✅  
Wave 0 stubs: present in 02-01 → ✅  
Overall Dimension 8: ✅ PASS  

`nyquist_validation` enabled in `.planning/config.json`.

### 9. Cross-Plan Data Contracts — PASS

Shared entities:

- `ImageFrame` (meta `Frame` + `image_bgr`) — produced 01, published 02, JPEG-encoded 03; no conflicting sanitize/strip.
- `SourceStatus` / `StatusSnapshot` — defined 01/02, JSON in 03; fields align with RESEARCH status API shape.
- Drop metric = overwrite-count locked in 02-02 and exposed via 03 `/api/status`.

### 10. CLAUDE.md Compliance — SKIPPED

No project-root `CLAUDE.md`. Plans follow Phase 1 conventions (uv, ruff, pytest, `sentry_ai`, perception-only language) documented in RESEARCH.

### 11. Research Resolution — PASS (hygiene note)

`## Open Questions` lists six items, each with an explicit **Recommendation**. Plans lock those defaults (overwrite-count drops, source-owned `frame_id`, RTSP mock+docs, keep-last stale frame, CLI source flags, port 8000). No unresolved research blocking execution.

**Hygiene:** section heading is not titled `## Open Questions (RESOLVED)` and items lack inline `RESOLVED:` markers — see Warning W3.

### 12. Pattern Compliance — PASS

Plans `read_first` include `02-PATTERNS.md` and `02-RESEARCH.md`. New files without codebase analogs (FrameBus, FastAPI, MJPEG, index.html) reference RESEARCH Patterns 2–5. Shared concerns (no numpy on Frame, registry skip-if-present, lifecycle open/read/close) repeated in actions.

---

## Special Checks (user-requested)

| Check | Result |
|-------|--------|
| ImageFrame pattern (not numpy on Pydantic Frame) | **PASS** — 02-01 creates `@dataclass ImageFrame`; Frame stays identity-only; tests keep schema green |
| Localhost default bind | **PASS** — 02-03 serve `--host` default `127.0.0.1`; help + README warn on `0.0.0.0`; test asserts default |
| UI-SPEC compliance for preview page | **PASS** — 02-03 T2: title, status pill text+color, footer Source/FPS/Drops/Bind, auto-connect MJPEG, plain-language errors, no motor language |
| Threat models present | **PASS** — all three PLANs have STRIDE tables mapping T-2-01..04 + supply-chain |
| No ML/detection/depth/WebRTC as required | **PASS** — explicitly out of scope in objectives and forbidden lists |
| Wave order 02-01 → 02-02 → 02-03 | **PASS** |

---

## Warnings (non-blocking)

```yaml
issues:
  - dimension: scope_sanity
    severity: WARNING
    plan: "02-01"
    finding: >
      files_modified lists ~24 paths (above 15 soft threshold). Count is inflated by
      intentional Wave 0 skip stubs (test_frame_bus, test_api_preview, test_cli_serve,
      test_sources_rtsp, etc.) plus small package __init__ files. Real implementation
      surface is manageable within 3 tasks.
    affected_field: frontmatter.files_modified
    suggested_fix: >
      Optional: note in plan objective that Wave 0 stubs inflate file count; no split
      required. Executor should create stubs as thin pytest.mark.skip modules.

  - dimension: scope_sanity
    severity: WARNING
    plan: "02-03"
    finding: >
      Task 3 bundles CAM-04 RTSP plugin, sentry serve CLI, docs/camera-sources.md,
      and README (~9 files). Coherent vertical slice but dense for one task.
    affected_field: tasks.Task3
    suggested_fix: >
      Acceptable as-is (single “ship the serve path” task). Split only if execution
      quality degrades mid-task.

  - dimension: research_resolution
    severity: WARNING
    plan: null
    finding: >
      02-RESEARCH.md ## Open Questions is not retitled (RESOLVED) and items use
      Recommendation rather than RESOLVED markers, even though plans lock all defaults.
    affected_field: 02-RESEARCH.md##Open Questions
    suggested_fix: >
      Optional hygiene: retitle to ## Open Questions (RESOLVED) and prefix each
      recommendation with RESOLVED. Not required before execute-phase.

  - dimension: nyquist_compliance
    severity: WARNING
    plan: null
    finding: >
      02-VALIDATION.md Per-Task Verification Map still attributes CAM-01..04 to plan
      02-01 and omits CAM-04 from 02-03 row (UI-01, MODEL-03 only). Plans correctly
      place CAM-04 in 02-03.
    affected_field: 02-VALIDATION.md##Per-Task Verification Map
    suggested_fix: >
      Update VALIDATION map rows to match plan requirements frontmatter
      (02-01: CAM-01..03; 02-02: CAM-05/06; 02-03: CAM-04, UI-01, MODEL-03).
```

---

## Blockers

None.

---

## Structured Issues

```yaml
issues:
  - dimension: scope_sanity
    severity: WARNING
    plan: "02-01"
    finding: "High files_modified count (~24) driven by Wave 0 skip stubs"
    affected_field: frontmatter.files_modified
    suggested_fix: "No split required; document Wave 0 inflation if desired"

  - dimension: scope_sanity
    severity: WARNING
    plan: "02-03"
    finding: "Task 3 density (RTSP + serve + docs + README)"
    affected_field: tasks.Task3
    suggested_fix: "Keep bundled unless execution struggles"

  - dimension: research_resolution
    severity: WARNING
    plan: null
    finding: "Open Questions lack formal RESOLVED markers (content resolved in plans)"
    affected_field: 02-RESEARCH.md
    suggested_fix: "Mark section Open Questions (RESOLVED)"

  - dimension: nyquist_compliance
    severity: WARNING
    plan: null
    finding: "VALIDATION.md map mis-assigns CAM-04 to 02-01"
    affected_field: 02-VALIDATION.md
    suggested_fix: "Align map with plan requirements fields"
```

---

## Recommendation

**0 blockers.** Proceed to execution:

```text
/gsd:execute-phase 2
```

Optional pre-exec hygiene (non-blocking): fix VALIDATION map CAM-04 row; mark RESEARCH open questions resolved.

---

## Checklist

- [x] Phase goal extracted from ROADMAP.md  
- [x] All PLAN.md files loaded and structure-validated  
- [x] must_haves parsed (truths, artifacts, key_links)  
- [x] Requirement coverage CAM-01..06, UI-01, MODEL-03  
- [x] Task completeness (files, action, verify, done, read_first)  
- [x] Dependency graph acyclic and wave-consistent  
- [x] Key links planned (bus publish, MJPEG encode, HTML→stream, CLI→bind)  
- [x] Scope within budget (warnings only)  
- [x] Context compliance + no deferred-scope creep  
- [x] Architectural tier compliance  
- [x] Cross-plan data contracts  
- [x] Threat models on all plans  
- [x] Nyquist / VALIDATION alignment  
- [x] ImageFrame pattern + localhost bind + UI-SPEC  
- [x] Overall status: **passed**

---

*Plan check agent — Phase 2 Camera Ingest & Live Preview*  
*Do not modify PLAN.md — check only*
