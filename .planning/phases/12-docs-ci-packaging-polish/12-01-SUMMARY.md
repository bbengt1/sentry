---
phase: 12-docs-ci-packaging-polish
plan: 01
subsystem: docs
tags: [edge-serve, export, onnx, tensorrt, agpl, keyword-tests, documentation]

# Dependency graph
requires:
  - phase: 09-live-onnxruntime-fixed-class-yolo
    provides: Live fixed-class ORT factory + onnx extra + export doc live conditions
  - phase: 10-live-tensorrt-fixed-class-yolo
    provides: Live fixed-class TRT factory + system TensorRT packaging honesty
  - phase: 11-sticky-fallback-dual-model-guardrails
    provides: Sticky soft/strict fallback + dual-model measure-on-device language
provides:
  - Numbered export → place artifact → sentry serve edge hub (docs/edge-serve.md)
  - Split-brain hub honesty (README, desktop-gpu, scripts/export, export index)
  - AGPL lineage for YOLO-derived .onnx/.engine in THIRD_PARTY_MODELS
  - Keyword locks for EDGE-DOC-01 and EDGE-DOC-02
affects: [12-02-ci-packaging, redistributors, maker onboarding]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Keyword-locked documentation honesty via Path.read_text asserts"
    - "Thin e2e hub linking into docs/export/* (desktop-gpu shape)"
    - "AGPL policy documentation for derived artifacts (not legal certification)"

key-files:
  created:
    - docs/edge-serve.md
    - tests/test_edge_serve_docs.py
  modified:
    - README.md
    - docs/desktop-gpu.md
    - docs/export/README.md
    - scripts/export/README.md
    - docs/README.md
    - THIRD_PARTY_MODELS.md
    - CHANGELOG.md
    - tests/test_export_docs.py
    - tests/test_desktop_docs.py
    - tests/test_third_party_models_doc.py

key-decisions:
  - "Ship thin docs/edge-serve.md hub rather than expanding only export/*"
  - "AGPL derived-artifact section uses evaluate-obligations / same commercial caution tone — not compliance certification"
  - "CHANGELOG Unreleased only; do not bump package 0.1.0 → 0.2.0"

patterns-established:
  - "EDGE-DOC keyword suite: forbid stale non-live TRT phrases on hub surfaces; require export→serve discoverability"
  - "Edge hub numbered path: install → export → place → serve --profile → --no-ui → backend_live honesty → soft/strict → measure dual-model"

requirements-completed: [EDGE-DOC-01, EDGE-DOC-02]

# Metrics
duration: 3min
completed: 2026-08-10
---

# Phase 12 Plan 01: Edge Serve Docs + AGPL Lineage Summary

**Numbered export→onnx/engine→`sentry serve --profile` hub with split-brain hub honesty and AGPL lineage for YOLO-derived `.onnx`/`.engine`**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-08-10T21:23:55Z
- **Completed:** 2026-08-10T21:26:09Z
- **Tasks:** 3/3
- **Files modified:** 12

## Accomplishments

- Makers can follow a numbered export → place artifact → `sentry serve --profile` path (with/without UI) from `docs/edge-serve.md`, linked from root README and docs index
- Root README, desktop-gpu, and scripts/export no longer claim TensorRT is export-only or jetson is still-PyTorch-only; live ORT/TRT conditions triad is discoverable
- `THIRD_PARTY_MODELS.md` documents AGPL commercial caution for derived `.onnx` / `.engine` with evaluate-obligations policy tone
- Keyword tests lock EDGE-DOC-01/02 honesty without hardware; no invented dual-model FPS claims

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 RED — keyword tests for edge narrative + AGPL lineage** - `dc777fd` (test)
2. **Task 2: Edge hub + split-brain doc honesty (EDGE-DOC-01)** - `ba7ec6e` (feat)
3. **Task 3: AGPL derived-artifact lineage (EDGE-DOC-02) + suite green** - `f2935ea` (feat)

**Plan metadata:** `84001ba` (docs: complete plan)

_Note: TDD Task 1 was test-only RED; GREEN landed in Tasks 2–3._

## Files Created/Modified

- `docs/edge-serve.md` — Thin numbered export→serve hub (ORT/TRT live triad, soft/strict, dual-model measure-only)
- `tests/test_edge_serve_docs.py` — Hub existence + narrative + README link locks
- `README.md` — Jetson profile honesty, Export live conditions, edge-serve doc table row
- `docs/desktop-gpu.md` — Remove non-live TRT claim; jetson comment + multi-SKU honesty
- `docs/export/README.md` — Retire Phase 7 / 07-03 deferral; link desktop-gpu + edge-serve
- `scripts/export/README.md` — Live fixed-class serve can use exported artifacts when conditions met
- `docs/README.md` — Start-here edge-serve row; v0.2 milestone versioning note
- `THIRD_PARTY_MODELS.md` — Derived ORT/TRT AGPL lineage section
- `CHANGELOG.md` — Unreleased changed notes for hub honesty + lineage
- `tests/test_export_docs.py` — Root/scripts/export index EDGE-DOC-01 asserts
- `tests/test_desktop_docs.py` — No stale non-live TRT claims
- `tests/test_third_party_models_doc.py` — AGPL derived .onnx/.engine lineage lock

## Decisions Made

- Prefer thin `docs/edge-serve.md` hub (desktop-gpu pattern) over README-only expansion so makers get one numbered path without duplicating full export recipes
- AGPL lineage is project policy documentation (“same commercial caution”, “evaluate obligations”, “not legal advice”) — not a compliance certification claim
- Package version stays 0.1.0; Unreleased CHANGELOG only

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- EDGE-DOC-01 and EDGE-DOC-02 complete; ready for plan 12-02 (CI workflow / gitignore / packaging static locks)
- No factory/runtime changes; keyword suite green without Jetson/GPU
- Unrelated untracked 12-02 work (`tests/test_edge_ci_workflow.py`, `tests/test_pyproject_onnx_extra.py` mods) left untouched

## TDD Gate Compliance

1. RED: `dc777fd` — `test(12-01): add failing keyword tests for EDGE-DOC honesty`
2. GREEN: `ba7ec6e` + `f2935ea` — docs/feat commits making the suite pass

## Self-Check: PASSED

- FOUND: `docs/edge-serve.md`
- FOUND: `tests/test_edge_serve_docs.py`
- FOUND: `THIRD_PARTY_MODELS.md` Derived section
- FOUND: `dc777fd`, `ba7ec6e`, `f2935ea`
- Suite: 35 passed (`test_export_docs`, `test_desktop_docs`, `test_third_party_models_doc`, `test_edge_serve_docs`)
- Stale phrases absent from hub surfaces
- Ruff clean on modified test modules

---
*Phase: 12-docs-ci-packaging-polish*
*Completed: 2026-08-10*
