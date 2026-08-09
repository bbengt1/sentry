---
phase: 08-backend-selection-honesty
verified: 2026-08-09T19:47:11Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
gaps: []
deferred: []
human_verification: []
---

# Phase 8: Backend Selection & Honesty — Verification Report

**Phase Goal:** Operators and robots see honest backend identity; serve constructs the fixed-class detector via a factory driven by `preferred_backend`, with safe artifact path resolution — torch path still works end-to-end  
**Verified:** 2026-08-09T19:47:11Z  
**Status:** passed  
**Re-verification:** No — initial verification  

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `sentry serve` constructs the fixed-class detection worker through a factory from `profile_runtime` (not hard-coded torch-only construction) | ✓ VERIFIED | `cli.py` serve: `build = build_detection_worker(rt, conf=0.25)` → `worker = build.worker` → `DetectionLoop(bus, worker, store)`. No direct `YoloDetectionWorker(` in `cli.py`. Source inspect tests in `test_cli_serve.py`. |
| 2 | `preferred_backend` selects among torch / onnxruntime / tensorrt **loader branches** (torch live; ORT/TRT may stub) | ✓ VERIFIED | `factory.py` `build_detection_worker`: distinct branches for torch/cpu, onnxruntime, tensorrt, unknown. Torch → live torch; ORT → `backend_live=torch` + `ort_loader_not_implemented` (or `path_rejected`); TRT → same with `trt_loader_not_implemented`. Artifact pre-check via `resolve_detector_artifact`. Profile matrix tests green. |
| 3 | Status / serve banner expose both `backend_requested` and `backend_live` (never claim ORT/TRT when torch running) | ✓ VERIFIED | Banner: `typer.echo` of `backend_requested` / `backend_live` / `backend_reason` from WorkerBuild. `create_app(..., backend_*)` → `app.state` → `/api/status` getattr merge (never recomputes live). Live Preview footer `metric-backend`: `req → live` (+ reason when differ). Honesty tests assert `backend_live not in ("tensorrt","onnxruntime")`. |
| 4 | Artifact paths for `.onnx` / `.engine` resolve from config/env/cache with safe allowlist (no path traversal) | ✓ VERIFIED | `artifact_paths.py`: stem/suffix allowlists; roots = weights_dir / artifact_root / cwd; explicit/env outside roots raise `path_rejected`; cache/CWD miss returns None. Tests cover traversal, absolute outside roots, wrong suffix, unknown stem. Spot-check: `/etc/passwd` rejected. |
| 5 | DetectionLoop / FrameBus / PerceptionStore / `/v1` unchanged; desktop-gpu stays torch-default | ✓ VERIFIED | No `backend_` / `preferred_backend` refs in loop, bus, store, routes_v1. DetectionLoop still duck-types `worker.process`. `desktop-gpu.yaml`: `preferred_backend: torch`. Factory desktop-gpu build: requested=torch, live=torch, reason=None. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/sentry_ai/config/artifact_paths.py` | resolve_detector_artifact + allowlists | ✓ VERIFIED | 203 lines; pure pathlib/os; no ORT/TRT imports |
| `src/sentry_ai/models/detection/factory.py` | WorkerBuild + build_detection_worker | ✓ VERIFIED | 158 lines; soft-stub honesty; no top-level ort/trt imports |
| `src/sentry_ai/cli.py` | serve uses factory; banner + create_app injection | ✓ VERIFIED | build_detection_worker; backend_* locals → create_app + banner |
| `src/sentry_ai/capture/status.py` | optional backend_* on StatusSnapshot | ✓ VERIFIED | `backend_requested/live/reason: str \| None = None` |
| `src/sentry_ai/api/app.py` | create_app kwargs → app.state | ✓ VERIFIED | kwargs + AppState + app.state assignment |
| `src/sentry_ai/api/routes_preview.py` | /api/status merges backend_* | ✓ VERIFIED | pass-through getattr; never recompute live |
| `src/sentry_ai/ui/static/index.html` | footer Backend metric | ✓ VERIFIED | `#metric-backend` + pollStatus pair/reason |
| `tests/test_artifact_paths.py` | BACK-04 coverage | ✓ VERIFIED | traversal, allowlist, suffix, stem |
| `tests/test_detection_factory.py` | BACK-01 / EDGE-RT-03 | ✓ VERIFIED | profile matrix + honesty invariants |
| `tests/test_backend_honesty_status.py` | BACK-02 status/API | ✓ VERIFIED | TRT/ORT soft-stub + null injection |
| `tests/test_cli_serve.py` | factory + banner wiring | ✓ VERIFIED | source-inspect contracts |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `cli.py` serve | `build_detection_worker(rt)` | factory construction | ✓ WIRED | replaces hard-coded YoloDetectionWorker |
| `build_detection_worker` | `YoloDetectionWorker` | torch live + soft ORT/TRT stub | ✓ WIRED | always constructs torch worker Phase 8 |
| `build_detection_worker` | `resolve_detector_artifact` | ORT/TRT pre-check | ✓ WIRED | env + cache roots; path_rejected soft-stub |
| `DetectionLoop` | `worker.process` | duck-type unchanged | ✓ WIRED | no backend switch in loop |
| `cli.serve` WorkerBuild | `create_app(backend_*)` | app.state injection | ✓ WIRED | kwargs + AppState |
| `routes_preview.api_status` | `app.state.backend_*` | getattr merge | ✓ WIRED | after model_dump |
| `ui/static/index.html` pollStatus | `/api/status` | metric-backend | ✓ WIRED | `req → live` (+ reason) |
| `cli` banner | WorkerBuild fields | typer.echo | ✓ WIRED | requested/live/reason on stderr when set |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `build_detection_worker` | backend_requested/live/reason | ProfileRuntime.preferred_backend | Yes — profile YAML → normalize_backend → branch | ✓ FLOWING |
| serve banner | backend_* locals | WorkerBuild | Yes — factory-authored | ✓ FLOWING |
| `/api/status` | backend_* keys | app.state from create_app kwargs | Yes — pass-through; null when not injected | ✓ FLOWING |
| Live Preview footer | metric-backend text | pollStatus JSON | Yes — from /api/status fields | ✓ FLOWING |
| `resolve_detector_artifact` | Path \| None | env/weights_dir/cwd under allowlist | Yes — real pathlib resolve or None | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Phase 8 test suite | `uv run pytest tests/test_detection_factory.py tests/test_artifact_paths.py tests/test_backend_honesty_status.py tests/test_cli_serve.py tests/test_detection_loop.py -q` | **58 passed**, 1 warning | ✓ PASS |
| Profile honesty matrix | `build_detection_worker` for desktop-gpu / jetson / cpu-fallback | torch/torch; tensorrt→torch+trt_…; onnxruntime→torch+ort_… | ✓ PASS |
| Path traversal reject | `resolve_detector_artifact(explicit=/etc/passwd, …)` | ValueError `path_rejected: … outside allowlist` | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| — | — | No phase-declared probes | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| BACK-01 | 08-01 | preferred_backend selects loader branch | ✓ SATISFIED | factory branches + profile tests |
| BACK-02 | 08-02 | status/banner expose requested + live | ✓ SATISFIED | status schema, /api/status, banner, UI |
| BACK-04 | 08-01 | safe artifact path allowlist | ✓ SATISFIED | artifact_paths + tests |
| EDGE-RT-01 | 08-01/02 | DetectionLoop/FrameBus/store/`/v1` spine | ✓ SATISFIED | no backend refs in spine modules |
| EDGE-RT-02 | 08-01 | serve constructs via factory from profile_runtime | ✓ SATISFIED | cli + factory |
| EDGE-RT-03 | 08-01/02 | desktop-gpu torch default; jetson/cpu honest | ✓ SATISFIED | profiles + soft-stub reasons |

**Orphaned requirements for Phase 8:** none (BACK-03 / EDGE-RT-04 map to Phase 11).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX debt markers in phase-touched code | — | — |
| — | — | No placeholder/stub returns on honesty path | — | — |

**Note (intentional, not a gap):** ORT/TRT loader branches soft-stub to torch with reason codes. This is the Phase 8 lock (live ORT/TRT deferred to Phases 9–10). Honesty invariants prevent false live claims.

### Confirmation Bias / Inversion Notes

1. **Could status invent live ORT/TRT?** No — route only getattr-merges app.state; factory never sets `backend_live` to onnxruntime/tensorrt.
2. **Is "loader branch" just a log string?** No — distinct code paths, reason codes, artifact resolve pre-check; selection is real wiring even while loaders soft-stub.
3. **Hard-coded empty backend fields?** Defaults are None for backward compat; serve injects real factory values when detect extra is present.

### Human Verification Required

None. Automated tests and code wiring cover all success criteria. Live Preview footer visual polish is optional operator eyeball, not a goal blocker.

### Gaps Summary

No gaps. Phase goal achieved.

---

_Verified: 2026-08-09T19:47:11Z_  
_Verifier: Claude (gsd-verifier)_
