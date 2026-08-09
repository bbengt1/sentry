---
phase: 06-developer-controls-open-vocab
plan: 02
subsystem: perception, api, ui
tags: [yoloe, open-vocab, detection, assemble, mjpeg, agpl, ultralytics]

requires:
  - phase: 06-01
    provides: PipelineState, enable gates, create_app injection, Live Preview controls, clear_* store methods
  - phase: 03
    provides: YoloDetectionWorker / DetectionLoop / PerceptionStore / draw_detections patterns
provides:
  - YoloeOpenVocabWorker with injectable model and dirty-flag set_classes
  - OpenVocabLoop modes off/on_demand/continuous (every_n=3 default)
  - OpenVocabProduct separate store slot (never dual-write set_detections)
  - Detection.source fixed|open_vocab + assemble merge with dual-color overlay
  - GET/PATCH /api/open-vocab/config + POST /api/open-vocab/run
  - Live Preview open-vocab prompt UX + AGPL docs
affects: [phase-07, edge-export, commercial-forks]

tech-stack:
  added: []  # YOLOE via existing detect extra (ultralytics) — no new package
  patterns:
    - "Separate OpenVocabProduct mailbox; assemble merges fixed then OV"
    - "Dirty-flag set_classes once per prompt change"
    - "POST /run arms loop only — never process on request thread"
    - "Magenta OV boxes vs cyan fixed; source tag on wire"

key-files:
  created:
    - src/sentry_ai/models/detection/yoloe_worker.py
    - src/sentry_ai/models/detection/open_vocab_loop.py
    - src/sentry_ai/api/routes_open_vocab.py
    - tests/test_yoloe_worker.py
    - tests/test_open_vocab_loop.py
    - tests/test_api_open_vocab.py
    - tests/test_assemble_open_vocab.py
  modified:
    - src/sentry_ai/schemas/perception.py
    - src/sentry_ai/state/perception_store.py
    - src/sentry_ai/models/cache.py
    - src/sentry_ai/api/assemble.py
    - src/sentry_ai/models/detection/overlay.py
    - src/sentry_ai/api/app.py
    - src/sentry_ai/api/deps.py
    - src/sentry_ai/api/routes_preview.py
    - src/sentry_ai/capture/status.py
    - src/sentry_ai/cli.py
    - src/sentry_ai/ui/static/index.html
    - THIRD_PARTY_MODELS.md
    - README.md

key-decisions:
  - "OpenVocabProduct fourth store slot — never dual-write set_detections"
  - "Default OV mode off; continuous every_n=3 opt-in only"
  - "Detection.source additive default fixed — existing fixed path unchanged"
  - "YOLOE via existing detect extra; yoloe-26s-seg.pt default; mock in CI"

patterns-established:
  - "Open-vocab twin of fixed YOLO worker/loop writing separate product"
  - "Cold-path open-vocab config: arm/mode/prompt only; inference on daemon thread"
  - "Dual-color draw_detections branch on Detection.source"

requirements-completed: [OVD-01, OVD-02, OVD-03]

duration: 8min
completed: 2026-08-08
---

# Phase 6 Plan 02: Open-Vocab Detection Summary

**Open-vocabulary YOLOE path with separate store product, assemble merge + source tags, dual-color overlays, and Live Preview prompt UX — default off, never blocking fixed-class.**

## Performance

- **Duration:** 8 min
- **Started:** 2026-08-08T16:27:01Z
- **Completed:** 2026-08-08T16:34:48Z
- **Tasks:** 3/3
- **Files modified:** 24

## Accomplishments

- **OVD-01:** `YoloeOpenVocabWorker` accepts text prompts via `set_prompt_classes`, dirty-flag `set_classes`, tags `source=open_vocab`; injectable FakeModel — no weight downloads in CI
- **OVD-02:** `OpenVocabLoop` modes off / on_demand / continuous every_n=3; fixed DetectionLoop independent; default off
- **OVD-03:** Assembler merges fixed then OV; MJPEG dual-color; `/v1` wire carries source tags; Live Preview Run + continuous controls

## Task Commits

Each task was committed atomically:

1. **Task 1: Detection.source + YOLOE worker + OpenVocabProduct store + cache/AGPL docs** - `1320ee7` (feat)
2. **Task 2: OpenVocabLoop + open-vocab API + assemble merge + overlay + serve wiring** - `9aaaa0c` (feat)
3. **Task 3: Live Preview open-vocab prompt UX + telemetry + docs note** - `f16a565` (feat)

**Plan metadata:** `e3e9ace` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/models/detection/yoloe_worker.py` — YOLOE open-vocab worker (injectable model)
- `src/sentry_ai/models/detection/open_vocab_loop.py` — mode scheduler writing set_open_vocab only
- `src/sentry_ai/api/routes_open_vocab.py` — config + run arm API (≤32 classes, ≤64 chars)
- `src/sentry_ai/schemas/perception.py` — Detection.source Literal
- `src/sentry_ai/state/perception_store.py` — OpenVocabProduct + ov_* metrics
- `src/sentry_ai/api/assemble.py` — fixed-first merge + ov stats/TTL
- `src/sentry_ai/models/detection/overlay.py` — magenta OV boxes + ov: prefix
- `src/sentry_ai/api/app.py` / `deps.py` / `routes_preview.py` / `cli.py` — wiring + status/MJPEG
- `src/sentry_ai/ui/static/index.html` — prompt + Run + continuous + ov telemetry
- `THIRD_PARTY_MODELS.md` / `README.md` — Phase 6 AGPL YOLOE active docs
- Tests: yoloe_worker, open_vocab_loop, api_open_vocab, assemble_open_vocab, overlay, cli_serve, preview

## Decisions Made

- Followed locked RESEARCH decisions: YOLOE via detect extra, OpenVocabProduct, default off, every_n=3, magenta overlay, AGPL docs
- Prompt caps enforced at API layer (T-06-10); worker strips empties only
- POST /run sets on_demand + arms — never calls process on request thread (T-06-16)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None. Full suite `uv run pytest -q` → 365 passed; ruff clean on modified sources.

## User Setup Required

None. Optional: `uv sync --extra detect` for real YOLOE weights on first open-vocab Run.

## Known Stubs

None. Open-vocab path is fully wired; default mode off is intentional (not a stub).

## Threat Flags

None new beyond plan `<threat_model>` mitigations (T-06-10…T-06-16 applied).

## Verification

```text
uv run pytest tests/test_yoloe_worker.py tests/test_open_vocab_loop.py \
  tests/test_api_open_vocab.py tests/test_assemble_open_vocab.py \
  tests/test_detection_overlay.py tests/test_model_cache.py \
  tests/test_third_party_models_doc.py tests/test_api_preview.py \
  tests/test_cli_serve.py -q
# + full suite: 365 passed
```

## Success Criteria Mapping

| Criterion | Status |
|-----------|--------|
| OVD-01 text prompts → open_vocab detections | Met |
| OVD-02 on_demand/continuous without blocking fixed | Met |
| OVD-03 OV on MJPEG + /v1 when enabled | Met |
| AGPL documented; tests never download weights | Met |
| Phase 6 success criteria 4–5 (open-vocab) | Met |

## Self-Check: PASSED

- [x] `src/sentry_ai/models/detection/yoloe_worker.py` exists
- [x] `src/sentry_ai/models/detection/open_vocab_loop.py` exists
- [x] `src/sentry_ai/api/routes_open_vocab.py` exists
- [x] Commits `1320ee7`, `9aaaa0c`, `f16a565` on main
- [x] Full pytest green (365)
