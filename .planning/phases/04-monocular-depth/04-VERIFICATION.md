---
phase: 04-monocular-depth
verified: 2026-08-08T10:25:13Z
status: human_needed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
human_verification:
  - test: "Install depth extra and run live preview (synthetic or USB)"
    expected: "MJPEG shows TURBO depth colormap blended on RGB; footer Depth shows 'relative (not meters)' and Depth ms updates; /api/snapshot has depth.kind=relative and unit=null"
    why_human: "Real DAV2 HF weight download and visual colormap quality cannot be asserted in CI (mock/injectable model path by design)"
  - test: "After first depth weight download, disconnect network and re-run serve"
    expected: "Depth still works from SENTRY_MODEL_CACHE/hf (or ~/.cache/sentry-ai/hf) without re-download"
    why_human: "Offline re-run after real HF download is an operator path; unit tests only verify HF_HOME cache policy"
  - test: "Optional: PATCH /api/depth/config to metric_indoor after serve started relative"
    expected: "Status/UI label becomes metric_estimated (m); if model does not reload, depth values may still be relative — confirm whether restart with metric mode is required for true metric weights"
    why_human: "Runtime set_depth_mode updates model_id/kind/unit but does not clear a already-loaded model; real-weight behavior needs operator confirmation"
---

# Phase 4: Monocular Depth Verification Report

**Phase Goal:** Add the spatial awareness primitive with honest monocular depth semantics (relative by default).  
**Verified:** 2026-08-08T10:25:13Z  
**Status:** human_needed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | Local monocular depth model produces a per-frame depth map | ✓ VERIFIED | `DepthAnythingWorker.process` returns HxW float32 `depth_map` at original resolution; `DepthLoop` reads `FrameBus.get_latest()`, skips same `frame_id`, writes `PerceptionStore.set_depth`; no `VideoCapture` in depth package; injectable fake model/processor for CI |
| 2 | Stream includes depth with explicit `depth_kind` (relative vs metric modes) | ✓ VERIFIED | `GET /api/snapshot` builds `DepthPayload(kind=..., unit=...)` + `completeness.depth`; relative → unit null; metric_indoor/outdoor → `metric_estimated` + `m` via `kind_for_mode`; never serializes full `depth_map` |
| 3 | Dashboard shows depth colormap overlaid or side-by-side with RGB | ✓ VERIFIED | Server-side `colorize_depth` / `blend_depth` (OpenCV `COLORMAP_TURBO`, alpha 0.45) in `_mjpeg_generator` before `draw_detections` / `imencode`; Live Preview uses same `/preview/mjpeg` stream |
| 4 | Relative depth is never exposed as meters; optional metric mode is clearly labeled | ✓ VERIFIED | Schema validator `relative_depth_forbids_unit`; no `depth_m` field; UI maps relative → `"relative (not meters)"`, metric + unit m → `"metric_estimated (m)"`; status omits `depth_unit` when null; honesty tests pass |
| 5 | Stage latency for depth is reported in telemetry | ✓ VERIFIED | `DepthLoop` measures `latency_ms` via `perf_counter`; store `last_depth_latency_ms` / product.latency_ms; `/api/status` exposes `depth_latency_ms`, `depth_fps`, `depth_kind`, `depth_frame_id`; snapshot `stats.depth_latency_ms`; UI `#metric-depth-ms` |

**Score:** 5/5 truths verified

### Plan-Level Truths (supporting)

| Source | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 04-01 | Worker returns depth map + kind/unit without camera; fake model in CI | ✓ VERIFIED | `tests/test_depth_worker.py` FakeModel/FakeProcessor; 227 full suite green |
| 04-01 | Default DAV2 Small relative; never NC Base/Large | ✓ VERIFIED | `MODE_TO_MODEL` Small-only allowlist; health lists `depth-anything-v2-small` |
| 04-01 | Relative → RELATIVE/unit=None; metric modes → METRIC_ESTIMATED/`m` from mode only | ✓ VERIFIED | `kind_for_mode`; worker uses mode not float heuristics |
| 04-01 | DepthLoop bus-only; set_depth; no VideoCapture | ✓ VERIFIED | `loop.py` + tests; grep clean |
| 04-01 | Single PerceptionStore DepthProduct keep-latest; full float in-process | ✓ VERIFIED | `DepthProduct.depth_map` in store; wire is metadata only |
| 04-01 | HF_HOME under SENTRY_MODEL_CACHE/hf | ✓ VERIFIED | `configure_model_cache` creates `hf/` sibling of `weights/` |
| 04-01 | optional-extra `depth`; unit tests never download HF | ✓ VERIFIED | `pyproject.toml` `[depth]` extra; inject path; tests assert no hub |
| 04-02 | Snapshot DepthPayload + completeness; no full arrays | ✓ VERIFIED | Spot-check + `test_api_depth.py` / `test_depth_kind_honesty.py` |
| 04-02 | MJPEG blend from same store; handlers never infer | ✓ VERIFIED | `routes_preview` blend only; FakeDepthWorker `process` asserts if called |
| 04-02 | serve starts DepthLoop when depth extra available; degrades otherwise | ✓ VERIFIED | `cli.py` try/import + start/stop order; `test_cli_serve.py` |

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/sentry_ai/models/depth/worker.py` | DepthAnythingWorker | ✓ VERIFIED | 267 lines; inject + real HF path; kind_for_mode |
| `src/sentry_ai/models/depth/loop.py` | DepthLoop bus subscriber | ✓ VERIFIED | 138 lines; set_depth + latency + drops |
| `src/sentry_ai/models/depth/preprocess.py` | BGR→RGB + depth_stats | ✓ VERIFIED | Pure helpers; golden tests |
| `src/sentry_ai/models/depth/mapping.py` | MODE_TO_MODEL + kind_for_mode | ✓ VERIFIED | Small-only; relative/metric modes |
| `src/sentry_ai/models/depth/colormap.py` | colorize + blend TURBO | ✓ VERIFIED | 73 lines; alpha 0.45 default |
| `src/sentry_ai/state/perception_store.py` | DepthProduct dual store | ✓ VERIFIED | set/snapshot_depth + depth metrics |
| `src/sentry_ai/models/cache.py` | HF_HOME under cache | ✓ VERIFIED | `hf/` + HUGGINGFACE_HUB_CACHE |
| `src/sentry_ai/api/routes_depth.py` | GET/PATCH depth_mode | ✓ VERIFIED | Literal enum; 503 without worker |
| `src/sentry_ai/api/routes_preview.py` | MJPEG blend + status depth_* | ✓ VERIFIED | snapshot_depth + blend_depth |
| `src/sentry_ai/api/routes_detection.py` | Snapshot merges depth | ✓ VERIFIED | DepthPayload metadata only |
| `src/sentry_ai/capture/status.py` | depth_* StatusSnapshot fields | ✓ VERIFIED | Optional fields with defaults |
| `src/sentry_ai/cli.py` | DepthLoop lifecycle | ✓ VERIFIED | Parallel to DetectionLoop |
| `src/sentry_ai/ui/static/index.html` | Depth kind + latency UI | ✓ VERIFIED | Honesty copy + poll |
| Depth unit/API tests | Mock CI coverage | ✓ VERIFIED | worker/loop/mapping/colormap/api/honesty |

gsd-sdk `verify.artifacts`: 04-01 10/10, 04-02 10/10.

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `depth/loop.py` | `FrameBus.get_latest` | `_run` keep-latest | ✓ WIRED | Pattern + tests |
| `depth/loop.py` | `PerceptionStore.set_depth` | publish after process | ✓ WIRED | Success + exception paths |
| `depth/worker.py` | `kind_for_mode` / `MODE_TO_MODEL` | mode → kind/unit | ✓ WIRED | |
| `depth/worker.py` | `configure_model_cache` | before `from_pretrained` | ✓ WIRED | Real load path only |
| `pyproject.toml` | `DepthAnythingWorker` | extra + entry point | ✓ WIRED | `depth-anything-v2-small` |
| `routes_preview.py` | `snapshot_depth` / `blend_depth` | MJPEG encode path | ✓ WIRED | Before draw_detections |
| `routes_detection.py` | `DepthPayload` + completeness | GET /api/snapshot | ✓ WIRED | |
| `routes_depth.py` | `depth_worker` depth_mode | GET/PATCH /api/depth/config | ✓ WIRED | |
| `index.html` | `/api/status` depth fields | `applyStatus` poll | ✓ WIRED | |
| `cli.py` serve | `DepthLoop.start/stop` | lifecycle | ✓ WIRED | gsd path quirk said missing; source confirms at lines 287–346 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| DepthLoop → store | `DepthProduct.depth_map` | `worker.process(frame)` from `ImageFrame.image_bgr` | Yes (fake in CI; HF on real path) | ✓ FLOWING |
| Snapshot API | `depth` DepthPayload | `store.snapshot_depth()` metadata only | Yes when product good | ✓ FLOWING |
| MJPEG preview | blended pixels | `store.snapshot_depth().depth_map` → `blend_depth` | Yes when map present | ✓ FLOWING |
| Status / UI | `depth_kind`, `depth_latency_ms` | same store product + metrics | Yes | ✓ FLOWING |
| Single store | one `PerceptionStore` in serve | CLI constructs once; injects into app + both loops | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full unit suite | `uv run pytest -q` | 227 passed | ✓ PASS |
| Lint | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Health | `uv run sentry health` | status ok; workers include depth-anything-v2-small | ✓ PASS |
| Smoke | `uv run sentry smoke` | smoke ok (3 synthetic PerceptionFrames) | ✓ PASS |
| Snapshot honesty | TestClient relative seed | kind=relative, unit=null, no depth_map, depth_latency_ms in stats | ✓ PASS |
| Status telemetry | TestClient relative seed | depth_kind=relative, depth_latency_ms=12.5, no depth_unit | ✓ PASS |
| Mapping exports | `kind_for_mode` / MODE_TO_MODEL | relative none; metric m; Small-only | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No phase-declared or conventional `scripts/*/tests/probe-*.sh` | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| DEPTH-01 | 04-01 | Local monocular depth (DAV2 Small OSS) | ✓ SATISFIED | Worker + loop + store + optional extra + mock CI |
| DEPTH-02 | 04-02 | Depth on stream with explicit depth_kind | ✓ SATISFIED | Snapshot DepthPayload + completeness.depth |
| DEPTH-03 | 04-02 | Depth colormap on dashboard | ✓ SATISFIED | Server-side TURBO blend on MJPEG Live Preview |
| DEPTH-04 | 04-02 | Metric labeled; never conflated with relative | ✓ SATISFIED | Schema + mapping + UI honesty + tests |

No orphaned Phase 4 requirements (REQUIREMENTS.md maps DEPTH-01..04 only to Phase 4).

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| `src/sentry_ai/models/depth/worker.py` | `set_depth_mode` | Updates `_model_id` but does not clear loaded `_model`/`_processor` | ⚠️ Warning | Runtime PATCH from relative→metric after first load keeps relative weights while labeling metric_estimated+m; constructor-time metric mode still loads correct id. Honesty of *labels* holds; true metric inference after live switch may need process restart |
| `src/sentry_ai/ui/static/index.html` | ~316 | `return null` | ℹ️ Info | 503 conf PATCH branch — not a stub |

No TBD/FIXME/XXX debt markers in phase-modified depth/API/store/cli/UI paths.

### Human Verification Required

### 1. Live depth with real weights

**Test:** `uv sync --extra depth` (optionally with detect), `sentry serve --source synthetic`, open `http://127.0.0.1:8000/`  
**Expected:** TURBO colormap blend on preview; Depth footer `relative (not meters)`; Depth ms updates; `GET /api/snapshot` has `depth.kind=relative`, `unit: null`  
**Why human:** Real HF download + visual quality outside CI mock path

### 2. Offline cache after first download

**Test:** Run once with network, then offline with same `SENTRY_MODEL_CACHE`  
**Expected:** Depth continues from `.../hf` without re-download  
**Why human:** Operator offline path; tests only check env path policy

### 3. Optional metric mode runtime switch

**Test:** With serve running, `PATCH /api/depth/config` `{"depth_mode":"metric_indoor"}`  
**Expected:** Labels show metric_estimated (m). Confirm whether depth values/model actually switch or whether restart is required  
**Why human:** Code path updates mode/kind without unloading loaded HF model

### Gaps Summary

No BLOCKER gaps against roadmap success criteria. All five truths are implemented, wired, and covered by automated tests with mock-friendly CI.

**Non-blocking note:** Runtime `set_depth_mode` after a successful real load does not reload HF weights. Default serve path stays relative (honest). Full metric *weights* at runtime may require process restart with metric mode at construction — flag for human check / optional follow-up, not a phase-stopper.

---

_Verified: 2026-08-08T10:25:13Z_  
_Verifier: Claude (gsd-verifier)_
