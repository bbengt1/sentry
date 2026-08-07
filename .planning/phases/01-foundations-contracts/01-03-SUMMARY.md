---
phase: 01-foundations-contracts
plan: 03
subsystem: plugins-backends-licenses
tags: [plugin-registry, entry-points, inference-backend, null-backend, third-party-models, smoke-cli, tdd, pytest]

# Dependency graph
requires:
  - phase: 01-foundations-contracts/01-01
    provides: "Installable sentry_ai package, Typer CLI skeleton, pytest/ruff"
  - phase: 01-foundations-contracts/01-02
    provides: "Frame/PerceptionFrame schemas, RuntimeProfile config, MODEL-01 policy constants"
provides:
  - "Hybrid PluginRegistry with register/get/list + entry-point discover"
  - "SyntheticSource / NoopWorker / NullSink builtins"
  - "InferenceBackend Protocol + NullBackend + DeviceInfo stubs"
  - "THIRD_PARTY_MODELS.md with DAV2 Small Apache-2.0 default"
  - "Full sentry smoke validating synthetic PerceptionFrames"
affects: [02-camera-ingest, frame-bus, perception-workers, model-loading]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Hybrid registry: in-tree register_builtins + importlib.metadata entry points"
    - "discover() skip-if-present for idempotent re-declaration of builtins"
    - "runtime_checkable InferenceBackend Protocol; NullBackend without torch"
    - "Smoke: SyntheticSource → PerceptionFrame.model_validate → NullSink"
    - "TDD RED test commits before GREEN feat commits"

key-files:
  created:
    - src/sentry_ai/plugins/__init__.py
    - src/sentry_ai/plugins/protocols.py
    - src/sentry_ai/plugins/registry.py
    - src/sentry_ai/plugins/builtins.py
    - src/sentry_ai/backend/__init__.py
    - src/sentry_ai/backend/protocols.py
    - src/sentry_ai/backend/null.py
    - THIRD_PARTY_MODELS.md
    - tests/test_plugins_registry.py
    - tests/test_backend_protocols.py
    - tests/test_third_party_models_doc.py
  modified:
    - pyproject.toml
    - src/sentry_ai/cli.py
    - src/sentry_ai/policy/models.py
    - src/sentry_ai/policy/__init__.py
    - tests/test_cli_smoke.py
    - README.md

key-decisions:
  - "discover() uses skip-if-present so entry-point re-declarations of builtins do not raise"
  - "register_builtins is also skip-if-present for safe post-discover calls"
  - "NullBackend.name = BackendName.CPU (no dedicated null enum)"
  - "probe_device always returns available=False without touching CUDA"
  - "Smoke asserts allow_cloud is false before validating PerceptionFrames"

patterns-established:
  - "Pattern: entry-point groups sentry_ai.sources|workers|sinks in pyproject.toml"
  - "Pattern: SyntheticSource increments frame_id and builds real Frame via schemas"
  - "Pattern: health prints version, profile, schema_version, plugin lists"
  - "Pattern: THIRD_PARTY_MODELS.md table + policy NON_DEFAULT_LICENSE_TAGS hooks"

requirements-completed: [FOUND-04, FOUND-05, FOUND-06, MODEL-01]

# Metrics
duration: 4min
completed: 2026-08-07
---

# Phase 1 Plan 03: Plugins, Backends & Licenses Summary

**Hybrid plugin registry with synthetic/noop/null builtins, InferenceBackend/NullBackend stubs, THIRD_PARTY_MODELS.md Apache-default licenses, and full `sentry smoke` PerceptionFrame validation.**

## Performance

- **Duration:** ~4 min
- **Started:** 2026-08-07T14:32:48Z
- **Completed:** 2026-08-07T14:36:09Z
- **Tasks:** 3/3 (each with TDD RED → GREEN)
- **Files modified:** 17 created/updated

## Accomplishments

- `PluginRegistry` registers sources/workers/sinks; duplicate names raise `ValueError`
- Builtins: `SyntheticSource` yields schema-valid `Frame`s; `NoopWorker` / `NullSink` stubs
- Entry-point groups `sentry_ai.sources|workers|sinks` declared; `discover()` skip-if-present
- `InferenceBackend` Protocol + `NullBackend` (no torch) + `DeviceInfo` / `probe_device` stubs
- `THIRD_PARTY_MODELS.md`: DAV2 Small Apache-2.0 default; AGPL/CC-BY-NC non-default
- `uv run sentry smoke` validates N synthetic `PerceptionFrame`s with `allow_cloud=false`
- `uv run sentry health` lists version, profile, schema_version, plugins
- Full suite: **66 passed**, ruff clean; no torch/opencv/fastapi deps

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED: Plugin registry tests** - `113ee2f` (test)
2. **Task 1 GREEN: Plugin registry, builtins, entry points** - `50157b8` (feat)
3. **Task 2 RED: Backend protocol tests** - `e401e2c` (test)
4. **Task 2 GREEN: InferenceBackend + NullBackend** - `bbdde1b` (feat)
5. **Task 3 RED: Licenses doc + full smoke tests** - `4de4b2a` (test)
6. **Task 3 GREEN: THIRD_PARTY_MODELS, policy, smoke CLI** - `c3e7dec` (feat)

**Plan metadata:** _(pending final docs commit)_

## Files Created/Modified

- `src/sentry_ai/plugins/protocols.py` — CameraSource, ModelWorker, Sink Protocols
- `src/sentry_ai/plugins/registry.py` — PluginRegistry + register_builtins + discover
- `src/sentry_ai/plugins/builtins.py` — SyntheticSource, NoopWorker, NullSink
- `src/sentry_ai/backend/protocols.py` — InferenceBackend, DeviceInfo, probe_device
- `src/sentry_ai/backend/null.py` — NullBackend with infer_calls counter
- `pyproject.toml` — entry-point groups for sources/workers/sinks
- `THIRD_PARTY_MODELS.md` — model weight license table + MODEL-01 policy
- `src/sentry_ai/policy/models.py` — NON_DEFAULT_LICENSE_TAGS
- `src/sentry_ai/cli.py` — full health (plugins) + smoke (PerceptionFrame validate)
- `README.md` — smoke docs + THIRD_PARTY_MODELS link
- `tests/test_plugins_registry.py`, `tests/test_backend_protocols.py`,
  `tests/test_third_party_models_doc.py`, `tests/test_cli_smoke.py` — full green coverage

## Decisions Made

- **Skip-if-present on discover:** Prefer silent skip over ValueError when entry points re-declare builtins (documented in registry module docstring)
- **NullBackend uses BackendName.CPU:** Avoids inventing a null enum value for Phase 1 stubs
- **Smoke fails if allow_cloud true:** Enforces local OSS path even if a profile is misconfigured
- **No ML deps:** Still pydantic/typer/pyyaml only for runtime

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Removed unused pytest import in backend tests**
- **Found during:** Task 2 GREEN (ruff check)
- **Issue:** `import pytest` unused after writing pure unit tests without fixtures
- **Fix:** Dropped unused import
- **Files modified:** `tests/test_backend_protocols.py`
- **Verification:** ruff clean; 6 backend tests pass
- **Committed in:** `bbdde1b`

---

**Total deviations:** 1 auto-fixed (1 bug/lint)
**Impact on plan:** Cosmetic lint fix only. Plan executed as written.

## Issues Encountered

None — TDD RED/GREEN cycles passed cleanly; entry points available after `uv sync`.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plugin hooks ready for real USB/file/RTSP sources (Phase 2)
- InferenceBackend ready for torch/onnx/tensorrt adapters (Phases 3–4)
- License policy documented so model downloads can enforce defaults
- Smoke path establishes the one-command local start for all future phases
- **Phase 1 complete:** FOUND-01..06 and MODEL-01 satisfied across 01-01..01-03

## Verification

```text
uv run pytest -q          → 66 passed
uv run ruff check src tests → All checks passed
uv run sentry smoke       → smoke ok: validated 3 synthetic PerceptionFrame(s)
uv run sentry health      → version, plugins synthetic/noop/null, schema_version: 1
```

## Self-Check: PASSED

- All key artifacts present (plugins/, backend/, THIRD_PARTY_MODELS.md, cli.py)
- All task commits found in git log
- No intentional stubs blocking plan goals

---
*Phase: 01-foundations-contracts*
*Completed: 2026-08-07*
