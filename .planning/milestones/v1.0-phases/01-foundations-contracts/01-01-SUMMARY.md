---
phase: 01-foundations-contracts
plan: 01
subsystem: packaging
tags: [uv, hatchling, typer, pytest, ruff, sentry-ai, python3.11]

# Dependency graph
requires: []
provides:
  - "Installable sentry-ai package (import sentry_ai)"
  - "Typer CLI entry `sentry` with health/smoke skeleton"
  - "Wave 0 pytest paths for plans 01-02 and 01-03"
  - "CI workflow (ruff + pytest on Python 3.11)"
  - "README one-command local start"
affects: [01-02, 01-03, foundations-contracts]

# Tech tracking
tech-stack:
  added:
    - pydantic>=2.13,<3
    - pydantic-settings>=2.15,<3
    - pyyaml>=6.0.3
    - typer>=0.27
    - pytest>=8 (dev)
    - ruff>=0.8 (dev)
    - hatchling>=1.26 (build)
  patterns:
    - "src-layout package under src/sentry_ai/"
    - "console script sentry → sentry_ai.cli:main"
    - "Wave 0 skip-marked tests for later plans"
    - "uv lock + editable install (no pythonpath hacks)"

key-files:
  created:
    - pyproject.toml
    - .python-version
    - LICENSE
    - README.md
    - uv.lock
    - .gitignore
    - src/sentry_ai/__init__.py
    - src/sentry_ai/__main__.py
    - src/sentry_ai/cli.py
    - tests/conftest.py
    - tests/test_cli_smoke.py
    - tests/test_schemas_frame.py
    - tests/test_schemas_depth_kind.py
    - tests/test_schemas_perception.py
    - tests/test_config_profiles.py
    - tests/test_plugins_registry.py
    - tests/test_backend_protocols.py
    - tests/test_third_party_models_doc.py
    - .github/workflows/ci.yml
  modified: []

key-decisions:
  - "Dist name sentry-ai (not sentry) to avoid PyPI/getsentry collision"
  - "Console script points to main() callable for reliable entry"
  - "Apache-2.0 for application code"
  - "Wave 0 stubs use pytest.mark.skip so suite stays green"

patterns-established:
  - "Pattern: src layout + hatchling + uv sync --extra dev"
  - "Pattern: Typer app with health/smoke; full smoke validation deferred to 01-03"
  - "Pattern: skip-marked Wave 0 tests document intended coverage path"

requirements-completed: [FOUND-01]

# Metrics
duration: 3min
completed: 2026-08-07
---

# Phase 1 Plan 01: Package Scaffold Summary

**Installable `sentry-ai` package with Typer CLI health/smoke skeleton, Wave 0 pytest stubs, and CI — FOUND-01 foundation for all later plans.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-08-07T11:08:27Z
- **Completed:** 2026-08-07T11:11:14Z
- **Tasks:** 3/3
- **Files modified:** 19 created

## Accomplishments

- Installable distribution `sentry-ai` imports as `sentry_ai` (`__version__ = "0.1.0"`)
- CLI entry points work: `uv run sentry health|smoke` and `python -m sentry_ai health`
- README documents one-command start and disambiguates from getsentry
- Wave 0 test paths exist; CLI tests pass; later-plan stubs skip cleanly
- CI workflow runs ruff + pytest on Python 3.11 without ML/camera deps

## Task Commits

Each task was committed atomically:

1. **Task 1: Package scaffold and tooling config** - `fc239e6` (feat)
2. **Task 2: CLI skeleton, README, and Wave 0 test stubs** - `23032a9` (feat)
3. **Task 3: CI workflow for ruff + pytest on Python 3.11** - `3f900b1` (ci)

**Plan metadata:** `d362490` (docs: complete plan)

## Files Created/Modified

- `pyproject.toml` — hatchling package metadata, deps, scripts, ruff/pytest config
- `.python-version` — pins Python 3.11
- `LICENSE` — Apache-2.0 application license
- `README.md` — one-command start + naming disambiguation
- `uv.lock` — locked dependency graph
- `.gitignore` — Python/uv/IDE ignores (keeps `.venv` out of git)
- `src/sentry_ai/__init__.py` — package version export
- `src/sentry_ai/__main__.py` — `python -m sentry_ai` entry
- `src/sentry_ai/cli.py` — Typer health/smoke skeleton
- `tests/conftest.py` — fixture placeholder for synthetic frames (01-02)
- `tests/test_cli_smoke.py` — real FOUND-01 CLI tests
- `tests/test_schemas_*.py`, `tests/test_config_profiles.py` — skip until 01-02
- `tests/test_plugins_registry.py`, `tests/test_backend_protocols.py`, `tests/test_third_party_models_doc.py` — skip until 01-03
- `.github/workflows/ci.yml` — uv + ruff + pytest + health on 3.11

## Decisions Made

- Used `sentry = "sentry_ai.cli:main"` (callable `main()` wrapping Typer app) rather than bare `app` object for reliable console-script invocation
- Added standard `.gitignore` so `.venv` and caches are not tracked (not listed in plan files but required for clean repo)
- Deferred `readme` field until README existed (Task 2), then wired `readme = "README.md"` in pyproject

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added `.gitignore` for Python/uv artifacts**
- **Found during:** Task 1 (Package scaffold)
- **Issue:** Fresh repo had no ignore rules; `.venv`, caches, and egg-info would pollute git status after `uv sync`
- **Fix:** Added standard Python/uv `.gitignore`
- **Files modified:** `.gitignore`
- **Verification:** `.venv` not listed as untracked after sync
- **Committed in:** `fc239e6` (Task 1)

**2. [Rule 2 - Missing Critical] Console script entry uses `main` callable**
- **Found during:** Task 1–2 (CLI entry)
- **Issue:** Plan allowed either `app` or `main`; hatch/console scripts are most reliable with a callable
- **Fix:** Implemented `main()` that invokes the Typer app; script = `sentry_ai.cli:main`
- **Files modified:** `pyproject.toml`, `src/sentry_ai/cli.py`
- **Verification:** `uv run sentry health` and `python -m sentry_ai health` exit 0
- **Committed in:** `fc239e6` / `23032a9`

---

**Total deviations:** 2 auto-fixed (Rule 2 missing critical)
**Impact on plan:** Minor scaffold hygiene; no scope creep into 01-02/01-03

## Issues Encountered

None

## Verification Results

```text
uv sync --extra dev                          # OK
import sentry_ai; assert __version__         # 0.1.0
uv run sentry health                         # exit 0, prints 0.1.0 + cpu-fallback + ok
uv run sentry smoke                          # exit 0, skeleton message
uv run python -m sentry_ai health            # exit 0
uv run pytest -q                             # 3 passed, 7 skipped
uv run ruff check src tests                  # All checks passed
name = "sentry-ai" in pyproject.toml         # OK
no torch/opencv/fastapi/numpy in deps        # OK
README has uv run sentry smoke + getsentry   # OK
.github/workflows/ci.yml present             # OK
```

## Requirement Coverage

| Requirement | Status | Evidence |
|-------------|--------|----------|
| FOUND-01 | Satisfied (scaffold) | Installable package, CLI entry, README one-command path, CI smoke, Wave 0 tests present |

Note: FOUND-01 is fully closed for **scaffold**; later plans deepen schemas/plugins but the installable one-command path is done here.

## Known Stubs

Intentional Phase 1 skeleton stubs (do not block FOUND-01):

| File | Stub | Resolved by |
|------|------|-------------|
| `src/sentry_ai/cli.py` `smoke` | Prints skeleton message; no Frame validation | 01-03 |
| `tests/test_schemas_*.py` | `pytest.mark.skip` | 01-02 |
| `tests/test_config_profiles.py` | `pytest.mark.skip` | 01-02 |
| `tests/test_plugins_registry.py` | `pytest.mark.skip` | 01-03 |
| `tests/test_backend_protocols.py` | `pytest.mark.skip` | 01-03 |
| `tests/test_third_party_models_doc.py` | `pytest.mark.skip` | 01-03 |
| `tests/conftest.py` | No synthetic Frame fixture yet | 01-02 |

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Ready for **01-02**: schemas (`Frame`, `DepthKind`, `PerceptionFrame`) + config profiles
- Ready for **01-03**: plugin registry, backend protocols, `THIRD_PARTY_MODELS.md`, full smoke validation
- Do not add torch/opencv/fastapi/numpy until the phase that needs them

## Self-Check: PASSED

- All created files exist (package, CLI, tests, CI, SUMMARY)
- Commits present: `fc239e6`, `23032a9`, `3f900b1`
- Verification suite green (import, health, smoke, pytest 3p/7s, ruff)

---
*Phase: 01-foundations-contracts*
*Completed: 2026-08-07*
