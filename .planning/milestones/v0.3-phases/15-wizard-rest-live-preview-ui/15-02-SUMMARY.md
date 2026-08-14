---
phase: 15-wizard-rest-live-preview-ui
plan: 02
subsystem: ui
tags: [calibration, wizard-ui, wiz-03, ops-01]

requires:
  - phase: 15-01
    provides: wizard REST freeze/sample/compute/apply/cancel/clear + /api/status calibration_*
provides:
  - static #calibration-wizard on existing index.html
  - footer #metric-calibration from status calibration fields
  - HTML contract tests for wizard ids, routes, honesty denylist
affects:
  - 16 free-space meters (UI still does not flip free-space units)
  - 17 YAML persist (no persist chrome this phase)

tech-stack:
  added: []
  patterns:
    - static Live Preview control-row + 500ms status poll
    - fetch JSON to /api/depth/calibration/*
    - depth badge from status depth_kind only
    - Cancel = clear_draft; Clear = clear_applied

key-files:
  created:
    - .planning/phases/15-wizard-rest-live-preview-ui/15-02-SUMMARY.md
  modified:
    - src/sentry_ai/ui/static/index.html
    - tests/test_api_preview.py
    - .planning/STATE.md

key-decisions:
  - "Click #preview maps to naturalWidth/Height with object-fit contain offsets"
  - "Draft fit numbers render in #calib-draft labeled draft (not live)"
  - "409 sample-while-applied prompts Clear applied first; does not auto-clear"
  - "Optional height field is approximate FOV helper, not primary known-meters path"

patterns-established:
  - "Wizard chrome analog of OV control-row: static HTML/JS, 503/409 non-fatal"

requirements-completed: [WIZ-03, OPS-01]

duration: 35min
completed: 2026-08-13
---

# Phase 15 Plan 02: Live Preview Calibration Wizard UI Summary

**WIZ-03 + OPS-01 UI: static wizard panel on existing index.html. Sample / Compute / Apply / Cancel / Clear call 15-01 REST. Live badge never locally claims metric_calibrated.**

## Performance

- **Duration:** ~35 min
- **Started:** 2026-08-13T13:10:00Z
- **Completed:** 2026-08-13T13:45:00Z
- **Tasks:** 1/1
- **Files modified:** 4

## Accomplishments

- `#calibration-wizard` control-row after open-vocab: method selector, known meters, optional height (FOV helper), Sample / Compute / Apply / Cancel / Clear
- Click `#preview` maps CSS box → `naturalWidth` / `naturalHeight` `point_uv` (object-fit contain)
- `#calib-count` / `#calib-draft` (labeled draft, not live) / `#calib-msg`; residual/scale from compute JSON only
- Footer `#metric-calibration` from `/api/status` `calibration_active` / sample_count / scale / method
- Depth badge still driven only by `data.depth_kind` (relative not meters; estimated/calibrated + unit m)
- 409 sample-while-applied: prompt to Clear applied first (no auto-clear); 503 non-fatal like OV
- Honesty copy: hobby monocular, not vehicle-grade; Cancel drops draft only; Clear drops applied
- HTML contract tests in `tests/test_api_preview.py` (GET `/` ids + inspect-source denylist)
- Zero new pip deps; no React; no YAML persist chrome; no free-space meter unit flip; DetectionLoop / FrameBus / ORT-TRT frozen

## Task Commits

MCP push commits on `feat/15-02-calibration-wizard-ui`.

## Files Created/Modified

- `src/sentry_ai/ui/static/index.html` — wizard panel + status wiring
- `tests/test_api_preview.py` — HTML contract + honesty denylist
- `.planning/STATE.md` — 15-02 done; Phase 15 complete; next Phase 16
- `.planning/phases/15-wizard-rest-live-preview-ui/15-02-SUMMARY.md` — this file

## Decisions Made

- Click-to-sample uses object-fit contain letterbox offsets so UV is natural image pixels, not CSS box pixels
- Height input is labeled approximate FOV helper and is not sent on the click `point_uv` sample path (primary is known meters)
- Compute/draft never writes `#metric-depth-kind`; apply/cancel/clear then `pollStatus()`

## Deviations from Plan

- None material. Freeze button omitted (optional REST; plan said persist omit; freeze not in 15-02 must-haves). Height field present as FOV helper only.

## Issues Encountered

None blocking.

## User Setup Required

None

## Next Phase Readiness

- Phase 15 complete (15-01 REST + 15-02 UI)
- Next is Phase 16 free-space meters per ROADMAP (research: absolute cuts vs distance_m fields)
- Phase 17 persist still out of scope (no YAML chrome)

## Verification

```text
uv run pytest tests/test_api_preview.py tests/test_api_calibration.py -q
```

## Self-Check: PASSED

- Key files present
- Wizard ids and `/api/depth/calibration` routes in GET `/` HTML
- Depth badge still status `depth_kind` only
- Cancel vs Clear copy correct
- No edits to DetectionLoop, FrameBus, ORT-TRT factory, free_space algorithm, REST semantics, or YAML I/O

---
*Phase: 15-wizard-rest-live-preview-ui*
*Completed: 2026-08-13*
