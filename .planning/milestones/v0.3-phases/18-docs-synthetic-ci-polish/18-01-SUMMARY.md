---
phase: 18-docs-synthetic-ci-polish
plan: 01
subsystem: docs
tags: [calibration, docs, honesty, ops-02]

requires:
  - phase: 17
    provides: wizard REST + STACK YAML persist + free-space meters when calibrated
provides:
  - docs/calibration.md operator hub
  - stale-hub honesty refresh (no always-ordinal)
  - tests/test_calibration_docs.py keyword lock
affects:
  - Phase 18-02 honesty matrix / CI lock

tech-stack:
  added: []
  patterns:
    - Phase 12 Path.read_text keyword tests (TDD)
    - Thin numbered hub + outbound links (edge-serve analog)
    - CHANGELOG Unreleased only; package stays 0.1.0

key-files:
  created:
    - docs/calibration.md
    - tests/test_calibration_docs.py
    - .planning/phases/18-docs-synthetic-ci-polish/18-01-SUMMARY.md
  modified:
    - tests/test_safety_docs.py
    - docs/perception-frame.md
    - docs/safety-and-privacy.md
    - README.md
    - docs/README.md
    - docs/api-reference.md
    - docs/cli.md
    - docs/configuration.md
    - docs/architecture.md
    - docs/desktop-gpu.md
    - docs/development.md
    - CHANGELOG.md
    - .planning/STATE.md

key-decisions:
  - "Document REST compute as the Fit action; persist via persist:true or POST save"
  - "STACK YAML path only; do not mention ~/.config in the hub"
  - "Forbid always-ordinal after stripping markdown emphasis so v1 always **ordinal** matches"
  - "Light development.md honesty pointer (user-listed hub; not in keyword HUB_PATHS)"

patterns-established:
  - "OPS-02 keyword module + shared hub-path tuple"
  - "Cancel = draft-only; Clear deletes YAML — documented, not redesigned"

requirements-completed: [OPS-02]

duration: 35min
completed: 2026-08-14
---

# Phase 18 Plan 01: Operator Calibration Guide + Honesty Copy

**OPS-02: operators get a numbered non-FSD calibration hub; hub surfaces stop claiming free-space is always ordinal. Keyword tests lock the honesty triad, STACK persist path, Cancel/Clear, and persist status. Zero product runtime changes.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-14T11:54:00Z
- **Completed:** 2026-08-14T12:25:00Z
- **Tasks:** 2/2
- **Files modified:** 16 (+ this summary)

## Accomplishments

- TDD: `tests/test_calibration_docs.py` require/forbid lists; safety page extended
- `docs/calibration.md` numbered path: serve → wizard (known distance) → sample / fit / Apply or Cancel → persist → fingerprint re-apply → Clear deletes YAML
- Honesty triad + free-space meters iff `metric_calibrated` + 1.5/3.0 m cuts
- Persist: `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml`, `SENTRY_CALIBRATION_DIR`, `--calibration-file`
- Stale hubs refreshed; CHANGELOG Unreleased notes v0.3 docs; `[0.1.0]` untouched
- No `src/sentry_ai` edits; pyproject stays 0.1.0

## Task Commits

MCP push commits on `feat/18-01-calibration-docs`.

## Files Created/Modified

- `tests/test_calibration_docs.py` — OPS-02 keyword lock
- `tests/test_safety_docs.py` — always-ordinal forbid + calibration link
- `docs/calibration.md` — operator hub
- `docs/perception-frame.md` — FS meters when calibrated; optional `distance_m`
- `docs/safety-and-privacy.md` — ordinal unless calibrated; link hub
- `README.md` / `docs/README.md` — discoverability + triad sentence
- `docs/api-reference.md` / `docs/cli.md` / `docs/configuration.md` — REST / flag / env
- `docs/architecture.md` / `docs/desktop-gpu.md` / `docs/development.md` — plug-in + stages
- `CHANGELOG.md` — Unreleased Added/Changed
- `.planning/STATE.md` — 18-01 done; next 18-02

## Decisions Made

- Fit in copy maps to REST `POST .../compute` (shipped name)
- Hub omits `~/.config` entirely (keyword lock)
- `docs/development.md` light refresh (user list; not in HUB_PATHS)

## Deviations from Plan

- Also refreshed `docs/development.md` (user-listed; not in plan `files_modified`)
- Keyword `_plain()` strips `*`/`\`` so markdown-bold “always **ordinal**” is caught
- Added `no distance_m` to stale-phrase forbid (user brief)

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- 18-01 OPS-02 complete
- 18-02: `tests/test_v03_honesty_matrix.py` + confirm `ci.yml` lock; no product code

## Verification

```text
uv run pytest tests/test_calibration_docs.py tests/test_safety_docs.py \
  tests/test_desktop_docs.py tests/test_edge_serve_docs.py \
  tests/test_export_docs.py -q --tb=short
```

Box: calibration + safety + desktop keyword tests green; ruff 88 on new/extended tests.

## Self-Check: PASSED

- Key files present
- Target APIs match plan (hub + keyword functions)
- No DetectionLoop / FrameBus / ORT-TRT / kind_for_mode / src edits
- No pyproject version bump
- No 18-02 honesty matrix / ci.yml changes

---
*Phase: 18-docs-synthetic-ci-polish*
*Completed: 2026-08-14*
