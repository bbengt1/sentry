---
phase: 11-sticky-fallback-dual-model-guardrails
plan: 01
subsystem: detection-factory
tags: [fallback, strict, soft, sticky, ORT, TRT, BACK-03, factory, config]

# Dependency graph
requires:
  - phase: 10-live-tensorrt-fixed-class-yolo
    provides: live TRT factory path + soft-fall reason matrix + WorkerBuild honesty
  - phase: 09-live-onnxruntime-fixed-class-yolo
    provides: live ORT factory path + soft-fall reason codes
provides:
  - DeviceConfig.fallback_to_torch default True + SENTRY_FALLBACK_TO_TORCH env always-wins
  - ProfileRuntime.fallback_to_torch plumbed into factory
  - Factory soft miss (torch+reason) vs strict miss (worker None, live None)
  - Once-per-construct structured soft-fallback WARNING / strict-fail ERROR log
  - Serve typer.Exit(1) fail-closed on strict miss
  - Docs for sticky soft-default and strict opt-in
affects:
  - 11-02 dual-model guardrails status surface (fallback_to_torch field on status/preview)
  - Phase 12 edge docs polish

# Tech tracking
tech-stack:
  added: []
  patterns:
    - soft-default fallback_to_torch with env always-wins (mirror SENTRY_ALLOW_CLOUD)
    - factory _miss helper for soft torch vs strict None worker
    - once-per-construct reason log at factory (not DetectionLoop)

key-files:
  created: []
  modified:
    - src/sentry_ai/config/models.py
    - src/sentry_ai/config/load.py
    - src/sentry_ai/config/profile_runtime.py
    - src/sentry_ai/models/detection/factory.py
    - src/sentry_ai/cli.py
    - tests/test_detection_factory.py
    - tests/test_cli_serve.py
    - docs/configuration.md
    - docs/architecture.md

key-decisions:
  - "Soft fallback_to_torch=True remains global default including jetson YAML values"
  - "Strict miss shape: worker=None, backend_live=None, reason set (never torch under preferred ORT/TRT)"
  - "SENTRY_FALLBACK_TO_TORCH env always-wins when set (mirrors SENTRY_ALLOW_CLOUD)"
  - "Strict serve UX: typer.Exit(code=1) after loud stderr; DetectionLoop not constructed"
  - "Reason log once in factory (warning soft / error strict); sticky process-level resolve"

patterns-established:
  - "Config surface: DeviceConfig field + load_config env always-wins + ProfileRuntime plumb"
  - "Factory _miss(fallback_to_torch) centralizes soft/strict miss returns"
  - "Serve single factory call; worker is None → Exit(1) before DetectionLoop"

requirements-completed: [BACK-03]

# Metrics
duration: 3min
completed: 2026-08-10
---

# Phase 11 Plan 01: Sticky Fallback Soft/Strict Summary

**Soft-default `fallback_to_torch` + strict fail-closed factory miss, sticky once-log, and serve Exit(1) for BACK-03**

## Performance

- **Duration:** 3 min
- **Started:** 2026-08-10T18:04:02Z
- **Completed:** 2026-08-10T18:07:04Z
- **Tasks:** 3
- **Files modified:** 9

## Accomplishments

- Plumbed `fallback_to_torch` through DeviceConfig → load_config env → ProfileRuntime (default soft True globally)
- Factory soft miss still returns torch worker + reason; strict miss returns `worker=None` / `backend_live=None` with same reason codes
- Once-per-construct structured log (WARNING soft / ERROR strict) when `backend_reason` is set
- Serve fails closed with `typer.Exit(1)` on strict miss; sticky single factory call site preserved
- Docs cover soft vs strict table, `SENTRY_FALLBACK_TO_TORCH`, sticky resolve, residual load-risk note

## Task Commits

Each task was committed atomically:

1. **Task 1: Plumb fallback_to_torch config + ProfileRuntime** - `e4e1f53` (feat)
2. **Task 2 RED: Failing soft/strict/log/sticky tests** - `9aaa21e` (test)
3. **Task 2 GREEN: Factory soft/strict miss policy + once-log** - `07e7b4d` (feat)
4. **Task 3: Serve strict fail-closed + sticky/soft-strict docs** - `7464c20` (feat)

**Plan metadata:** `docs(11-01): complete sticky soft/strict fallback plan`

_Note: TDD Task 2 used RED → GREEN commits_

## Files Created/Modified

- `src/sentry_ai/config/models.py` - `DeviceConfig.fallback_to_torch: bool = True`
- `src/sentry_ai/config/load.py` - `SENTRY_FALLBACK_TO_TORCH` env always-wins override
- `src/sentry_ai/config/profile_runtime.py` - `ProfileRuntime.fallback_to_torch` field + plumb
- `src/sentry_ai/models/detection/factory.py` - `_miss` soft/strict + once-log; optional worker/live
- `src/sentry_ai/cli.py` - strict `worker is None` → stderr + `typer.Exit(1)`; banner `fallback_to_torch`
- `tests/test_detection_factory.py` - config + strict matrix + log-once + sticky proofs
- `tests/test_cli_serve.py` - inspect-source Exit + single factory call wiring
- `docs/configuration.md` - soft/strict table, env, sticky contract
- `docs/architecture.md` - fallback chain honesty + residual risk

## Decisions Made

- Soft remains global default (including jetson package profiles — field values unchanged)
- Strict miss never claims `backend_live=torch` under preferred ORT/TRT
- Env name `SENTRY_FALLBACK_TO_TORCH` with always-wins semantics (mirror allow_cloud)
- Serve Exit(1) rather than detection-disabled-while-process-up for strict
- Residual corrupt-engine thrash documented only (no DetectionLoop rewrite)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- BACK-03 sticky soft/strict policy complete; ready for **11-02** (EDGE-RT-04 dual-model torch scope lock + status surface for `fallback_to_torch`)
- Spine freeze intact (DetectionLoop/FrameBus/store/`/v1` untouched)
- No Jetson/real engines required in CI — unit matrix green (61 tests factory+cli_serve)

## Verification

```text
uv run pytest tests/test_detection_factory.py tests/test_cli_serve.py -q
# 61 passed
```

## Self-Check: PASSED

- [x] key files exist (models/load/profile_runtime/factory/cli/docs/tests)
- [x] commits e4e1f53, 9aaa21e, 07e7b4d, 7464c20 present
- [x] acceptance criteria greps pass (fallback_to_torch, SENTRY_FALLBACK_TO_TORCH, soft-fallback/strict-fail, typer.Exit, sticky docs)
- [x] jetson profiles remain soft-default (no `fallback_to_torch: false` in package profiles)
- [x] no stubs that block plan goal

---
*Phase: 11-sticky-fallback-dual-model-guardrails*
*Completed: 2026-08-10*
