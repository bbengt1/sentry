---
phase: 07-edge-profiles-extension-stubs
plan: 03
subsystem: edge-extensions-docs
tags: [ros2, voice-null, camera_id, desktop-gpu, safety, privacy, non-autonomy, plugins, stubs]

# Dependency graph
requires:
  - phase: 07-01
    provides: Runtime profiles (desktop-gpu/jetson/cpu-fallback) + headless --no-ui
  - phase: 07-02
    provides: Export docs + README Export section (preserved)
  - phase: 01-foundations-contracts
    provides: Frame/PerceptionFrame camera_id, NullSink, plugin registry
provides:
  - Multi-cam camera_id schema/store identity tests (no fusion)
  - Importable Ros2PerceptionBridge NotImplemented stub (no rclpy)
  - VoiceNullSink voice-null entry point + register_builtins
  - docs/desktop-gpu.md primary maker path (EDGE-01)
  - docs/safety-and-privacy.md non-autonomy + privacy (release docs)
affects: [phase-7-verify, v1-ship, integrators]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Extension stubs importable without heavy deps; ROS2 not auto-registered"
    - "VoiceNullSink twin of NullSink via sinks entry point voice-null"
    - "Doc honesty tests via pathlib keyword asserts (third_party pattern)"
    - "v1 single active source; camera_id is multi-cam extension key only"

key-files:
  created:
    - src/sentry_ai/extensions/__init__.py
    - src/sentry_ai/extensions/ros2/__init__.py
    - src/sentry_ai/extensions/ros2/bridge.py
    - src/sentry_ai/extensions/ros2/README.md
    - docs/desktop-gpu.md
    - docs/safety-and-privacy.md
    - tests/test_camera_id_multi.py
    - tests/test_extensions_stubs.py
    - tests/test_desktop_docs.py
    - tests/test_safety_docs.py
  modified:
    - src/sentry_ai/plugins/builtins.py
    - src/sentry_ai/plugins/registry.py
    - pyproject.toml
    - README.md
    - tests/test_plugins_registry.py

key-decisions:
  - "Ros2PerceptionBridge importable without auto-register as sink (health stays clean)"
  - "VoiceNullSink name/entry-point voice-null; no ASR/TTS"
  - "Multi-cam = schema identity tests only; store remains single-slot keep-latest"
  - "Desktop GPU documented as primary maker path; serve default remains cpu-fallback"
  - "Safety doc consolidates perception-only, free-space not interlock, localhost default"

patterns-established:
  - "extensions/ package for post-v1 scaffolds without core heavy deps"
  - "NotImplemented bridge with README-pointing error message"
  - "Additive README sections (Primary path / Safety / Extension stubs) preserve Export"

requirements-completed: [EDGE-04, EDGE-01]

# Metrics
duration: 4min
completed: 2026-08-08
---

# Phase 7 Plan 03: Extension Stubs + Release Docs Summary

**Multi-cam camera_id identity tests, importable ROS2 NotImplemented bridge (no rclpy), VoiceNullSink no-op, plus desktop GPU primary-path and safety/privacy release docs**

## Performance

- **Duration:** 4 min
- **Started:** 2026-08-08T17:16:31Z
- **Completed:** 2026-08-08T17:20:01Z
- **Tasks:** 2/2
- **Files modified:** 15

## Accomplishments

- EDGE-04: multi-cam `camera_id` schema/store identity tests; v1 single-active-source documented
- EDGE-04: `Ros2PerceptionBridge` importable stub (`start`/`emit` → NotImplementedError; no rclpy; not auto-registered)
- EDGE-04: `VoiceNullSink` (`voice-null`) registered in builtins + entry points; discover idempotent
- EDGE-01: `docs/desktop-gpu.md` primary maker E2E path (extras, profile, USB, cache, `/v1`, headless)
- Safety/privacy finalized in `docs/safety-and-privacy.md` + README links (perception-only, free-space not interlock, localhost)

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED:** `ace4bdf` — `test(07-03): add failing tests for multi-cam ids and extension stubs`
2. **Task 1 GREEN:** `a7d3ec0` — `feat(07-03): ROS2 bridge stub, VoiceNullSink, multi-cam identity hooks`
3. **Task 2 RED:** `cba5e3e` — `test(07-03): add failing desktop GPU and safety doc content tests`
4. **Task 2 GREEN:** `e70c025` — `docs(07-03): desktop GPU primary path and safety/privacy release docs`

**Plan metadata:** (final docs commit after state update)

## Files Created/Modified

- `src/sentry_ai/extensions/ros2/bridge.py` — `Ros2PerceptionBridge` NotImplemented stub
- `src/sentry_ai/extensions/ros2/README.md` — integrator mapping notes + deferred scope
- `src/sentry_ai/plugins/builtins.py` — `VoiceNullSink` no-op
- `src/sentry_ai/plugins/registry.py` — register `voice-null` in builtins
- `pyproject.toml` — `voice-null` sinks entry point
- `docs/desktop-gpu.md` — primary maker path
- `docs/safety-and-privacy.md` — non-autonomy + privacy
- `README.md` — primary path, profiles, headless, safety, extension stubs (Export section preserved)
- `tests/test_camera_id_multi.py`, `tests/test_extensions_stubs.py`, `tests/test_desktop_docs.py`, `tests/test_safety_docs.py`, `tests/test_plugins_registry.py`

## Decisions Made

- Followed plan locks: stubs only; no production ROS2/voice/multi-cam fusion
- ROS2 stays out of default sink registry so `sentry health` remains clean
- README edits additive — Export section from 07-02 kept intact

## Deviations from Plan

None - plan executed exactly as written.

## TDD Gate Compliance

- RED commits: `ace4bdf`, `cba5e3e`
- GREEN commits: `a7d3ec0`, `e70c025`
- Gates satisfied for both tasks

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| `Ros2PerceptionBridge.start/emit` | `extensions/ros2/bridge.py` | Intentional EDGE-04 NotImplemented |
| `VoiceNullSink` | `plugins/builtins.py` | Intentional no-op voice extension point |
| Multi-cam fusion | N/A | Deferred; only identity tests ship |

These stubs **do not** block plan goals (EDGE-04 requires stubs, not products).

## Threat Flags

None new beyond plan `<threat_model>` mitigations (T-07-20..25 applied: no cmd_vel, no-op voice, no rclpy, free-space not interlock, localhost warnings).

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 7 all three plans complete (profiles, export, stubs/docs)
- Ready for phase verification: `uv run pytest -q` (433 passed, 1 skipped) + ruff
- ROADMAP success criteria 1, 5, 6 satisfied alongside 07-01/07-02

## Self-Check: PASSED

- `src/sentry_ai/extensions/ros2/bridge.py` FOUND
- `docs/desktop-gpu.md` FOUND
- `docs/safety-and-privacy.md` FOUND
- Commits `ace4bdf`, `a7d3ec0`, `cba5e3e`, `e70c025` FOUND in git log
- Verification: plan-targeted pytest green; full suite 433 passed, 1 skipped

---
*Phase: 07-edge-profiles-extension-stubs*
*Completed: 2026-08-08*
