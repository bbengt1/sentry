---
phase: 18-docs-synthetic-ci-polish
plan: 02
subsystem: tests
tags: [calibration, ci, honesty, ops-03]

requires:
  - phase: 18-01
    provides: docs/calibration.md + test_calibration_docs.py keyword lock
provides:
  - tests/test_v03_honesty_matrix.py inventory + ci.yml lock
  - test_edge_ci_workflow.py OPS-03 comment (existing EDGE-CI-02 tests unchanged)
affects:
  - complete-milestone (later; v0.3 reqs now closable)

tech-stack:
  added: []
  patterns:
    - Phase 12 Path.read_text CI lock (EDGE-CI-02 analog)
    - Living inventory tuple + is_file() (no product re-implementation)

key-files:
  created:
    - tests/test_v03_honesty_matrix.py
    - .planning/phases/18-docs-synthetic-ci-polish/18-02-SUMMARY.md
  modified:
    - tests/test_edge_ci_workflow.py
    - .planning/STATE.md
    - .planning/ROADMAP.md

key-decisions:
  - "Inventory is path-existence + ci.yml static lock; no CalibrationState re-tests"
  - "ci.yml left byte-identical (ubuntu-latest + uv sync --extra dev)"
  - "REQUIREMENTS checkboxes left for complete-milestone (Lock #10)"

patterns-established:
  - "OPS-03 living V03_INVENTORY so deleting a Phase 13–17 suite fails CI"

requirements-completed: [OPS-03]

duration: 25min
completed: 2026-08-14
---

# Phase 18 Plan 02: Honesty Matrix + Synthetic CI Lock

**OPS-03: fit / apply / honesty / persist stay proven by existing Phase 13–17 synthetic suites. Thin inventory lock + EDGE-CI-02 reuse. Default GHA never requires a room, Jetson, CUDA, or `--extra depth`. Zero product runtime changes.**

## Performance

- **Duration:** ~25 min
- **Started:** 2026-08-14T12:22:00Z
- **Completed:** 2026-08-14T12:50:00Z
- **Tasks:** 1/1
- **Files modified:** 5 (+ this summary)

## Accomplishments

- `tests/test_v03_honesty_matrix.py`: docstring table + `V03_INVENTORY` (14 Phase 13–17 / 18-01 suites) + file-existence lock + `ci.yml` `--extra depth` forbid
- `tests/test_edge_ci_workflow.py`: docstring + one-line comment that v0.3 OPS-03 reuses EDGE-CI-02; three existing tests unchanged
- `.github/workflows/ci.yml` unchanged: `ubuntu-latest` + `uv sync --extra dev` + ruff + pytest + `sentry health`
- STATE: Phase 18 complete; next is complete-milestone (no more product phases)
- ROADMAP: Phase 18 + 18-01/18-02 plans marked complete; REQUIREMENTS left open (Lock #10)
- No `src/sentry_ai` edits; pyproject stays 0.1.0; zero new deps

## Task Commits

MCP push commits on `feat/18-02-honesty-matrix-ci`.

## Files Created/Modified

- `tests/test_v03_honesty_matrix.py` — OPS-03 living inventory + CI lock
- `tests/test_edge_ci_workflow.py` — OPS-03 reuse comment only
- `.planning/STATE.md` — Phase 18 complete; next complete-milestone
- `.planning/ROADMAP.md` — Phase 18 plans checked; milestone close later
- `.planning/phases/18-docs-synthetic-ci-polish/18-02-SUMMARY.md` — this file

## Decisions Made

- Follow PLAN Target APIs (14 inventory paths); RESEARCH extras (`test_schemas_depth_kind.py`, `test_api_calibration_smoother.py`) stay covered by default `pytest -q` but are not in the lock tuple
- Do not close REQUIREMENTS.md checkboxes (complete-milestone is a later step)
- No `pytest --collect-only` helper — `is_file()` is the required lock

## Deviations from Plan

- ROADMAP Phase 18 checkboxes marked complete (planning hygiene). REQUIREMENTS.md untouched per Lock #10
- Did not add a new `test_ci_no_extra_depth_or_room` (existing EDGE-CI-02 already forbids `--extra depth`)

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- Phase 18 complete (OPS-02 + OPS-03)
- v0.3 product phases 13–18 implemented; no more product phases
- Next: `/gsd:complete-milestone` (close REQUIREMENTS checkboxes; not this PR)

## Verification

```text
uv run pytest tests/test_v03_honesty_matrix.py tests/test_edge_ci_workflow.py \
  tests/test_calibration_fit.py tests/test_calibration_store.py \
  tests/test_calibration_persist.py tests/test_calibration_validators.py \
  tests/test_free_space_bands.py tests/test_calibration_docs.py \
  tests/test_safety_docs.py -q --tb=short
```

Box: matrix + EDGE-CI-02 lock tests green against stub tree (inventory files + ci.yml). Full inventoried suites + ruff via GitHub CI (no clone).

## Self-Check: PASSED

- Key files present
- Target APIs match plan (`V03_INVENTORY`, existence + ci.yml lock)
- No DetectionLoop / FrameBus / ORT-TRT / kind_for_mode / src edits
- No pyproject version bump
- ci.yml byte-identical

---
*Phase: 18-docs-synthetic-ci-polish*
*Completed: 2026-08-14*
