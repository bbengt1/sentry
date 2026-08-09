---
phase: 01-foundations-contracts
verified: 2026-08-07T14:37:54Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 1: Foundations & Contracts Verification Report

**Phase Goal:** Establish the product skeleton and non-negotiable contracts so every later phase shares types, plugins, licenses, and multi-target hooks.

**Verified:** 2026-08-07T14:37:54Z  
**Status:** passed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Developer can install the package and run a health/smoke command against synthetic frames | ✓ VERIFIED | `uv run sentry health` → exit 0, prints `sentry-ai 0.1.0` / `status: ok`; `uv run sentry smoke` → exit 0, `validated 3 synthetic PerceptionFrame(s)`; 66 pytest green; ruff clean |
| 2 | Frame / PerceptionFrame schemas include frame_id, camera_id, timestamps, and depth_kind enum | ✓ VERIFIED | `Frame`: frame_id, camera_id, t_capture, t_ingest (`src/sentry_ai/schemas/frame.py`); `PerceptionFrame`: frame_id, camera_id, t_capture, t_publish + Completeness + DepthPayload (`perception.py`); `DepthKind` = relative \| metric_estimated \| metric_calibrated (`enums.py`); relative+unit=`m` rejected by validator |
| 3 | Plugin registry stubs exist for sources, model workers, and sinks | ✓ VERIFIED | `PluginRegistry` + `register_builtins` + entry-point groups; builtins: `synthetic` source, `noop` worker, `null` sink; health lists all three |
| 4 | THIRD_PARTY_MODELS.md documents default model licenses; defaults exclude NC-only weights | ✓ VERIFIED | DAV2 Small Apache-2.0 marked **Yes** default; CC-BY-NC Base/Large/Giant **No**; AGPL YOLO **No**; policy constants in `policy/models.py` |
| 5 | Config supports runtime profile names (desktop-gpu, jetson, cpu-fallback) | ✓ VERIFIED | YAML under `config/profiles/`; `RuntimeProfile` enum; `load_config` loads all three with `allow_cloud=False` |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `pyproject.toml` | Installable sentry-ai package, scripts, entry points | ✓ VERIFIED | name=`sentry-ai`, script `sentry=sentry_ai.cli:main`, entry-points for sources/workers/sinks; deps: pydantic, pyyaml, typer only |
| `src/sentry_ai/__init__.py` | Package + `__version__` | ✓ VERIFIED | `__version__ = "0.1.0"` |
| `src/sentry_ai/cli.py` | health + smoke CLI | ✓ VERIFIED | Typer app; smoke builds synthetic Frames → PerceptionFrame validate; asserts `allow_cloud` false |
| `src/sentry_ai/__main__.py` | `python -m sentry_ai` | ✓ VERIFIED | Invokes `cli.main` |
| `src/sentry_ai/schemas/frame.py` | Frame model | ✓ VERIFIED | Required identity fields, extra=forbid |
| `src/sentry_ai/schemas/perception.py` | PerceptionFrame, DepthPayload, Completeness | ✓ VERIFIED | No `depth_m`; relative unit forbidden |
| `src/sentry_ai/schemas/enums.py` | DepthKind, RuntimeProfile, BackendName | ✓ VERIFIED | All three enums present |
| `src/sentry_ai/config/load.py` | YAML safe_load + profile merge | ✓ VERIFIED | `yaml.safe_load` only; env overrides |
| `src/sentry_ai/config/profiles/*.yaml` | Three runtime profiles | ✓ VERIFIED | desktop-gpu, jetson, cpu-fallback; all `allow_cloud: false` |
| `src/sentry_ai/plugins/registry.py` | PluginRegistry | ✓ VERIFIED | register/get/list/discover |
| `src/sentry_ai/plugins/builtins.py` | SyntheticSource, NoopWorker, NullSink | ✓ VERIFIED | Substantive stubs, used by smoke |
| `src/sentry_ai/plugins/protocols.py` | CameraSource, ModelWorker, Sink | ✓ VERIFIED | runtime_checkable Protocols |
| `src/sentry_ai/backend/protocols.py` | InferenceBackend, probe_device | ✓ VERIFIED | No torch import |
| `src/sentry_ai/backend/null.py` | NullBackend | ✓ VERIFIED | load/infer/close stubs |
| `src/sentry_ai/policy/models.py` | Local OSS policy constants | ✓ VERIFIED | DEFAULT_ALLOW_CLOUD=False, NON_DEFAULT_LICENSE_TAGS |
| `THIRD_PARTY_MODELS.md` | License table | ✓ VERIFIED | Apache default; AGPL/NC non-default |
| `README.md` | One-command start | ✓ VERIFIED | `uv sync --extra dev` + `uv run sentry smoke` |
| `.github/workflows/ci.yml` | CI smoke | ✓ VERIFIED | uv sync, ruff, pytest, sentry health |
| `tests/*` | Wave 0 + full phase suite | ✓ VERIFIED | 8 test modules, 66 passed |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `pyproject.toml` [project.scripts] | `sentry_ai.cli:main` | console_scripts | ✓ WIRED | `sentry = "sentry_ai.cli:main"` (main wraps Typer app) |
| `src/sentry_ai/__main__.py` | `cli.main` | python -m | ✓ WIRED | Import + call |
| README | `uv run sentry smoke` | documented start | ✓ WIRED | One-command section present |
| entry-points groups | builtins | discovery | ✓ WIRED | `sentry_ai.sources|workers|sinks` → SyntheticSource/NoopWorker/NullSink |
| `cli.smoke` | Frame / PerceptionFrame | synthetic validate | ✓ WIRED | SyntheticSource.read → PerceptionFrame.model_validate → NullSink.emit |
| `DepthPayload` validator | DepthKind.RELATIVE | unit reject | ✓ WIRED | `relative_depth_forbids_unit` via model_validator |
| config load | yaml.safe_load | safe YAML | ✓ WIRED | `load.py` uses safe_load only |
| SentryConfig / YAML | allow_cloud: false | MODEL-01 default | ✓ WIRED | Field default + all three profiles + smoke assert |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `cli.smoke` | `frame` | `SyntheticSource.read()` | Yes — incremental frame_id, real epoch timestamps | ✓ FLOWING |
| `cli.smoke` | `perception` | `PerceptionFrame.model_validate(...)` from frame fields | Yes — validated pydantic model | ✓ FLOWING |
| `cli.health` | plugin lists | `PluginRegistry` after register_builtins + discover | Yes — synthetic/noop/null | ✓ FLOWING |
| Profile load | `SentryConfig` | YAML files under `config/profiles/` | Yes — real YAML parse + pydantic | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite | `uv run pytest -q` | 66 passed in 0.21s | ✓ PASS |
| Lint | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Health CLI | `uv run sentry health` | exit 0; sources/workers/sinks listed | ✓ PASS |
| Smoke CLI | `uv run sentry smoke` | exit 0; 3 PerceptionFrames validated, allow_cloud=False | ✓ PASS |
| Relative depth honesty | Python DepthPayload(relative, unit=m) | ValidationError | ✓ PASS |
| Profiles load | load_config for all three | RuntimeProfile values; allow_cloud all False | ✓ PASS |
| Forbidden deps | pyproject deps scan | no torch/opencv/fastapi/ultralytics/numpy | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
|-------|---------|--------|--------|
| — | — | No probe scripts declared for this phase | SKIPPED (N/A) |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| FOUND-01 | 01-01 | Installable package + one-command start | ✓ SATISFIED | pyproject, CLI, README, CI |
| FOUND-02 | 01-02 | Frame / PerceptionFrame with frame_id, camera_id, timestamps | ✓ SATISFIED | frame.py, perception.py + tests |
| FOUND-03 | 01-02 | Depth typed relative \| metric_*; never meters when relative | ✓ SATISFIED | DepthKind + validator; no depth_m field |
| FOUND-04 | 01-03 | Plugin registry stubs sources/workers/sinks | ✓ SATISFIED | registry + builtins + entry points |
| FOUND-05 | 01-03 | Default commercially friendly OSS; THIRD_PARTY_MODELS.md | ✓ SATISFIED | Doc + policy constants + tests |
| FOUND-06 | 01-02, 01-03 | desktop-gpu / jetson / cpu-fallback profiles (+ backend stubs) | ✓ SATISFIED | YAML profiles + RuntimeProfile + InferenceBackend/NullBackend |
| MODEL-01 | 01-02, 01-03 | Core path local OSS only (no mandatory cloud) | ✓ SATISFIED | allow_cloud default false; smoke refuses true; no cloud deps |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| — | — | No TBD/FIXME/XXX/TODO debt markers in phase source | — | Clean |
| `plugins/builtins.py` | 52 | `NoopWorker.process` returns None | ℹ️ Info | Intentional Phase 1 stub; smoke uses it as pass-through |
| `backend/null.py` | 28 | `NullBackend.infer` returns None | ℹ️ Info | Intentional no-op backend; no torch |
| `backend/protocols.py` | 45–64 | `probe_device` always `available=False` | ℹ️ Info | Documented Phase 1 stub; real probe deferred to edge phases |

No blocker debt markers. Stub returns are intentional contracts, not hollow placeholders pretending to be complete features.

### Human Verification Required

None. All success criteria are programmatically verified (CLI exit codes, schema validation, file contents, tests).

### Gaps Summary

No gaps. All five roadmap success criteria and seven Phase 1 requirements are satisfied by substantive, wired implementations. Forbidden heavy deps (torch/opencv/fastapi) are absent from `pyproject.toml`.

### Dependency Constraint Check

| Constraint | Status | Evidence |
|------------|--------|----------|
| No torch in dependencies | ✓ | pyproject deps: pydantic, pydantic-settings, pyyaml, typer (+ dev pytest/ruff) |
| No opencv in dependencies | ✓ | Clean |
| No fastapi in dependencies | ✓ | Clean |

### Recommendation

**Advance to Phase 2.** Phase 1 goal achieved: installable skeleton, shared schemas, plugin/backend stubs, license policy docs, and multi-target profile names are in place for later phases.

---

_Verified: 2026-08-07T14:37:54Z_  
_Verifier: Claude (gsd-verifier)_

## VERIFICATION PASSED
