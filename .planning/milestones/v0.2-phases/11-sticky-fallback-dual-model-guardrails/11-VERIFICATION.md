---
phase: 11-sticky-fallback-dual-model-guardrails
verified: 2026-08-10T18:15:26Z
status: passed
score: 15/15 must-haves verified
overrides_applied: 0
---

# Phase 11: Sticky Fallback & Dual-Model Guardrails Verification Report

**Phase Goal:** Missing ORT/TRT artifacts or deps never thrash or silently lie; depth and open-vocab stay on existing PyTorch paths this milestone

**Verified:** 2026-08-10T18:15:26Z  
**Status:** passed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

Merged from ROADMAP success criteria + 11-01/11-02 PLAN `must_haves.truths` (deduplicated).

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | When preferred ORT/TRT artifact/dep is missing, behavior is sticky (fail-closed or torch fallback with reason logged once — never thrash every frame) | ✓ VERIFIED | `factory._miss` + `_log_reason_once`; single `build_detection_worker` call in `cli.py:507`; `DetectionLoop` has zero factory references; soft/strict + log-once tests green |
| 2 | Soft vs strict fallback modes are documented; live backend + reason remain visible when they differ from requested | ✓ VERIFIED | Soft/strict tables in `docs/configuration.md`, `docs/architecture.md`, export dual-model docs; status/banner/UI pass-through of `backend_*` + `fallback_to_torch` |
| 3 | Depth and open-vocab continue on existing PyTorch paths (no live ORT/TRT for those stages) | ✓ VERIFIED | `cli.py` constructs `DepthAnythingWorker` / `YoloeOpenVocabWorker` outside factory; `tests/test_edge_rt04_torch_only.py` locks construction + no ORT/TRT claims in depth/yoloe workers |
| 4 | Dual-model guidance exists for TRT YOLO + torch depth; continuous open-vocab + TRT+DAV2 is not first-class | ✓ VERIFIED | `docs/export/yolo26-onnx-tensorrt.md`, `jetson-packaging.md`, `README.md` — measure-on-device + not-first-class language; export keyword tests green |
| 5 | Soft miss (`fallback_to_torch=true`): factory returns torch worker, `backend_live=torch`, stable reason | ✓ VERIFIED | `factory._miss` soft branch; soft matrix tests (jetson/cpu-fallback/dep/path) in `test_detection_factory.py` |
| 6 | Strict miss (`fallback_to_torch=false`): `worker=None`, `backend_live=None`, reason set — never silent torch under ORT/TRT labels | ✓ VERIFIED | `factory._miss` strict branch; strict matrix tests for TRT/ORT artifact/dep/path/unsupported |
| 7 | Strict serve fails closed with `typer.Exit(1)` after printing requested/reason | ✓ VERIFIED | `cli.py:514-523` worker-is-None path; `test_cli_serve` / factory inspect-source asserts Exit wiring |
| 8 | Resolve is sticky: factory once at serve; DetectionLoop never re-resolves | ✓ VERIFIED | One production call site in `cli.py`; `rg build_detection_worker loop.py` empty; sticky unit test |
| 9 | When `backend_reason` set, factory emits exactly one structured log per construct (warning soft / error strict) | ✓ VERIFIED | `_log_reason_once`; caplog tests `test_soft_miss_logs_warning_once` / `test_strict_miss_logs_error_once` |
| 10 | Soft remains global default including jetson; package YAML not flipped to strict | ✓ VERIFIED | `DeviceConfig.fallback_to_torch=True`; profile default tests; no `fallback_to_torch: false` in package profiles |
| 11 | No new pip packages; factory uses `find_spec` only (no module-level onnxruntime/tensorrt imports) | ✓ VERIFIED | Factory source: `importlib.util.find_spec` probes only; no top-level ORT/TRT imports |
| 12 | Operator status/banner/UI show factory-authored `backend_*` and pass-through `fallback_to_torch` (False preserved) | ✓ VERIFIED | StatusSnapshot field; create_app/AppState/routes `is not None` loop; CLI inject + banner; UI footer soft/strict; honesty tests True/False pass-through |
| 13 | Status route never recomputes live from `preferred_backend` | ✓ VERIFIED | `routes_preview.py` pass-through only; honesty tests assert no factory recompute |
| 14 | Export/docs no longer say dual-model guardrails or sticky policy are deferred to Phase 11 | ✓ VERIFIED | Zero matches for `Phase 11 owns` / `deferred to Phase 11` in export dual-model docs; keyword suite asserts retirement |
| 15 | Dual-model: measure-on-device YOLO+DAV2; no published dual-model FPS; continuous OV+TRT+DAV2 not first-class | ✓ VERIFIED | Explicit shipped language in yolo26/jetson-packaging/README; FPS hygiene asserts in export tests |

**Score:** 15/15 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/sentry_ai/config/models.py` | `DeviceConfig.fallback_to_torch` default True | ✓ VERIFIED | Line 18; extra=forbid retained |
| `src/sentry_ai/config/load.py` | `SENTRY_FALLBACK_TO_TORCH` env always-wins | ✓ VERIFIED | Lines 119–129 mirror allow_cloud pattern |
| `src/sentry_ai/config/profile_runtime.py` | `ProfileRuntime.fallback_to_torch` plumbed | ✓ VERIFIED | Field + `profile_runtime()` composition |
| `src/sentry_ai/models/detection/factory.py` | Soft/strict `_miss` + once-log | ✓ VERIFIED | `_miss`, `_log_reason_once`, optional worker/live |
| `src/sentry_ai/cli.py` | Strict Exit(1); inject fallback; depth/OV separate | ✓ VERIFIED | Exit path, create_app kwarg, DepthAnythingWorker + YoloeOpenVocabWorker |
| `src/sentry_ai/capture/status.py` | `fallback_to_torch: bool \| None` | ✓ VERIFIED | Line 79 |
| `src/sentry_ai/api/app.py` | create_app + app.state + AppState mirror | ✓ VERIFIED | Kwarg + state + deps |
| `src/sentry_ai/api/deps.py` | `AppState.fallback_to_torch` | ✓ VERIFIED | Field present |
| `src/sentry_ai/api/routes_preview.py` | Pass-through includes False | ✓ VERIFIED | `is not None` field loop |
| `src/sentry_ai/ui/static/index.html` | Footer reason + soft/strict hint | ✓ VERIFIED | Lines 449–476 |
| `tests/test_detection_factory.py` | Soft/strict/sticky/log/config matrix | ✓ VERIFIED | Substantive suite; all green |
| `tests/test_backend_honesty_status.py` | True/False pass-through; current reason codes | ✓ VERIFIED | No `ort_loader_not_implemented` |
| `tests/test_edge_rt04_torch_only.py` | EDGE-RT-04 construction proofs | ✓ VERIFIED | 5 static tests; green |
| `tests/test_export_docs.py` | Dual-model + sticky keyword honesty | ✓ VERIFIED | Green with export docs |
| `docs/configuration.md` | Soft/strict + env + sticky | ✓ VERIFIED | BACK-03 section + env table |
| `docs/architecture.md` | Fallback chain honesty | ✓ VERIFIED | Sticky soft/strict section |
| `docs/export/yolo26-onnx-tensorrt.md` | Shipped dual-model guardrails | ✓ VERIFIED | Measure-on-device; Phase 11 deferral gone |
| `docs/export/jetson-packaging.md` | Dual-model honesty + sticky | ✓ VERIFIED | Same contract |
| `docs/export/README.md` | Dual-model pointer | ✓ VERIFIED | Hard-rule list item |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `load_config` | `DeviceConfig.fallback_to_torch` | `SENTRY_FALLBACK_TO_TORCH` env always-wins | ✓ WIRED | Env set → parse; else setdefault True |
| `profile_runtime` | `ProfileRuntime.fallback_to_torch` | `cfg.device.fallback_to_torch` | ✓ WIRED | Composition field |
| `build_detection_worker` | `rt.fallback_to_torch` | `_miss` soft torch vs strict None | ✓ WIRED | All ORT/TRT/unsupported miss paths |
| `cli.serve` | `build_detection_worker` once | `worker is None` → `typer.Exit(1)` | ✓ WIRED | Single call site + Exit |
| Factory miss path | `logging.getLogger(__name__)` | soft-fallback / strict-fail | ✓ WIRED | Once-log helper |
| `cli.serve` | `create_app(fallback_to_torch=…)` | pass-through only | ✓ WIRED | `getattr(rt, "fallback_to_torch", True)` |
| `routes_preview /api/status` | `app.state.fallback_to_torch` | field tuple if value is not None | ✓ WIRED | False preserved |
| `cli.serve` depth | `DepthAnythingWorker` | separate from factory | ✓ WIRED | Dedicated construct block |
| `cli.serve` OV | `YoloeOpenVocabWorker(weights=rt.open_vocab_weights)` | `.pt` path only | ✓ WIRED | Default OpenVocabLoop mode off |
| Export dual-model docs | measure-on-device + non-claim continuous OV | keyword tests | ✓ WIRED | export_docs suite |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| Factory `WorkerBuild` | `backend_live` / `backend_reason` / `worker` | Artifact resolve + dep probe + `rt.fallback_to_torch` | Yes — live path or soft/strict miss with real reason codes | ✓ FLOWING |
| `/api/status` | `fallback_to_torch`, `backend_*` | `app.state` set by CLI from factory/rt | Yes — pass-through of construct-time values (False not dropped) | ✓ FLOWING |
| UI footer | req/live/reason/fb | `/api/status` poll | Yes — renders status fields only; no invented live ORT/TRT | ✓ FLOWING |
| Depth path | `depth_worker` | `DepthAnythingWorker(model_id=rt.depth_model_id)` | Torch/HF path (not factory backends) | ✓ FLOWING |
| OV path | `ov_worker` | `YoloeOpenVocabWorker(weights=rt.open_vocab_weights)` | YOLOE `.pt` weights from profile | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| DeviceConfig soft default | `DeviceConfig().fallback_to_torch is True` | True | ✓ PASS |
| StatusSnapshot field | `'fallback_to_torch' in StatusSnapshot.model_fields` | True | ✓ PASS |
| Strict miss shape | `WorkerBuild(worker=None, backend_live=None, …)` | Shape accepted | ✓ PASS |
| Phase 11 pytest suite | `uv run pytest tests/test_detection_factory.py tests/test_cli_serve.py tests/test_backend_honesty_status.py tests/test_edge_rt04_torch_only.py tests/test_export_docs.py -q` | **97 passed** | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| N/A | — | Phase does not declare probe scripts | SKIPPED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| BACK-03 | 11-01, 11-02 | Documented sticky fail/fallback when preferred ORT/TRT missing | ✓ SATISFIED | Soft/strict factory + Exit(1) + once-log + docs + status surface |
| EDGE-RT-04 | 11-02 | Depth and open-vocab stay PyTorch this milestone | ✓ SATISFIED | Separate constructors + edge_rt04 static lock + dual-model non-claim docs |

No orphaned Phase 11 requirements in REQUIREMENTS.md.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No TBD/FIXME/XXX/TODO in phase-touched files | — | Clean |
| — | — | No Phase 11 deferral lies in export dual-model docs | — | Clean |
| — | — | No `ort_loader_not_implemented` residual in honesty tests | — | Clean |
| — | — | No module-level onnxruntime/tensorrt factory imports | — | Clean |

### Human Verification Required

None. All roadmap success criteria and plan must-haves are programmatically verified (unit/static tests + source wiring). Live Jetson dual-model VRAM/latency measurement is intentionally out of scope (docs: measure-on-device; Phase 12 CI/docs polish).

### Gaps Summary

No gaps. Phase goal achieved:

1. **BACK-03** — Sticky process-level resolve; soft default torch+reason; strict fail-closed opt-in; reason logged once; operator-visible via status/banner/UI.
2. **EDGE-RT-04** — Depth/OV remain torch/HF and YOLOE `.pt` paths; not routed through detection factory; dual-model docs ship measure-on-device YOLO+DAV2 and non-claim continuous OV+TRT+DAV2; Phase 11 deferral language retired.

---

_Verified: 2026-08-10T18:15:26Z_  
_Verifier: Claude (gsd-verifier)_
