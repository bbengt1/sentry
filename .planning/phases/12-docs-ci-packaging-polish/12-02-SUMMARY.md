---
phase: 12-docs-ci-packaging-polish
plan: 02
subsystem: testing
tags: [ci, github-actions, gitignore, packaging, edge-ci, tensorrt, onnx, pytest, hatch]

# Dependency graph
requires:
  - phase: 09-live-onnx-fixed-class-yolo
    provides: onnx extra pin + packaging static tests
  - phase: 10-live-tensorrt-fixed-class-yolo
    provides: TRT factory matrix + parity mocks
  - phase: 11-sticky-fallback-dual-model-guardrails
    provides: soft/strict sticky factory + EDGE-RT-04 torch-only suite
provides:
  - EDGE-CI-02 static lock on .github/workflows/ci.yml (ubuntu-latest, uv sync --extra dev only)
  - gitignore hygiene for *.engine / *.onnx / *.pt export artifacts
  - hatch force-include assert (no model engines in wheel)
  - EDGE-CI-01 living matrix gate documented + verified green without Jetson
affects: [ci, packaging, contributor-onboarding, v0.2-closeout]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Static Path.read_text locks for CI workflow (no PyYAML dependency)"
    - "tomllib force-include hygiene for hatch wheel packaging"
    - "EDGE-CI-01 matrix owned by factory/honesty/parity suites; EDGE-CI-02 owns workflow keywords"

key-files:
  created:
    - tests/test_edge_ci_workflow.py
  modified:
    - tests/test_pyproject_onnx_extra.py
    - .gitignore

key-decisions:
  - "Leave ci.yml byte-identical — already Jetson/GPU-free; lock with tests only"
  - "EDGE-CI-01 is verify-only — no factory rewrite; document matrix ownership in test docstring"
  - "gitignore *.engine/*.onnx next to *.pt; zero tracked engines confirmed"

patterns-established:
  - "CI static lock: assert ubuntu-latest + uv sync --extra dev; forbid self-hosted/jetson/tensorrt/cuda/gpu and ML extras"
  - "Packaging hygiene: optional-deps has no tensorrt; force-include excludes .engine/.onnx/.pt"
  - "Artifact gitignore + companion static test prevents casual engine commits"

requirements-completed: [EDGE-CI-01, EDGE-CI-02]

# Metrics
duration: 1min
completed: 2026-08-10
---

# Phase 12 Plan 02: CI & Packaging Polish Summary

**Static EDGE-CI-02 locks on Jetson-free GHA + gitignore/wheel hygiene, with EDGE-CI-01 selection matrix verified green without hardware**

## Performance

- **Duration:** 1 min
- **Started:** 2026-08-10T21:24:02Z
- **Completed:** 2026-08-10T21:25:22Z
- **Tasks:** 3
- **Files modified:** 3 (ci.yml unchanged)

## Accomplishments

- Added `tests/test_edge_ci_workflow.py` locking default GHA to `ubuntu-latest` + `uv sync --extra dev` only (no Jetson/self-hosted/tensorrt/cuda/gpu/ML extras)
- Extended packaging tests: no `tensorrt` optional extra; hatch force-include ships profiles + UI static only (never `.engine`/`.onnx`/`.pt`)
- Gitignored local export artifacts (`*.engine`, `*.onnx` alongside `*.pt`); zero tracked engines confirmed
- Verified EDGE-CI-01 factory/honesty/artifact/parity/EDGE-RT-04 matrix green (85 tests) without Jetson; factory untouched

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 RED — CI workflow + packaging static locks** - `1da2923` (test)
2. **Task 2: gitignore artifacts + confirm CI content lock** - `9a8e479` (feat)
3. **Task 3: EDGE-CI-01 selection/fallback matrix gate** - `45392dd` (docs)

**Plan metadata:** (pending final docs commit)

_Note: TDD RED (Task 1) failed only on missing gitignore lines; GREEN (Task 2) closed the gap. Task 3 was verify-only plus ruff-clean docstring for living matrix ownership._

## Files Created/Modified

- `tests/test_edge_ci_workflow.py` — EDGE-CI-02 static workflow + gitignore locks; EDGE-CI-01 matrix ownership docstring
- `tests/test_pyproject_onnx_extra.py` — force-include hygiene assert (no engines/onnx/pt in wheel)
- `.gitignore` — `*.engine` and `*.onnx` ignored with comment on local export artifacts
- `.github/workflows/ci.yml` — verified compliant; left byte-identical (no edit)

## Decisions Made

- **ci.yml lock-only:** Workflow already matched the contract; editing would risk parallel-plan churn — tests encode the policy instead
- **No factory rewrite:** EDGE-CI-01 coverage lives in existing suites; 12-02 only gates and documents ownership
- **No new packages / no YAML parser:** Plain `Path.read_text` + `tomllib` only

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Ruff E501 on EDGE-CI-01 matrix table in docstring**
- **Found during:** Task 3 (matrix gate / ruff check)
- **Issue:** Wide markdown table in module docstring exceeded 88-char line length; CI runs `ruff check src tests`
- **Fix:** Reformatted living matrix as compact bullet list under 88 chars
- **Files modified:** `tests/test_edge_ci_workflow.py`
- **Verification:** `uv run ruff check src tests` clean; matrix suite still 85 passed
- **Committed in:** `45392dd` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/style for CI lint)
**Impact on plan:** Necessary for ruff-clean CI; no scope creep.

## Issues Encountered

None beyond the docstring line-length fix above.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- EDGE-CI-01 and EDGE-CI-02 requirements satisfied for Phase 12 closeout
- Parallel plan 12-01 still owns product docs / AGPL lineage (no file overlap)
- Default GHA remains contributor-friendly without GPU runners

## Self-Check: PASSED

- FOUND: `tests/test_edge_ci_workflow.py`
- FOUND: `tests/test_pyproject_onnx_extra.py`
- FOUND: `.gitignore` (`*.pt`, `*.engine`, `*.onnx`)
- FOUND: commits `1da2923`, `9a8e479`, `45392dd`
- VERIFIED: 85 matrix/packaging tests green; ruff clean; factory untouched; ci.yml unchanged

---
*Phase: 12-docs-ci-packaging-polish*
*Completed: 2026-08-10*
