---
phase: 10-live-tensorrt-fixed-class-yolo
plan: 02
subsystem: docs
tags: [tensorrt, jetson, export-docs, packaging, on-device, keyword-tests]

requires:
  - phase: 10-live-tensorrt-fixed-class-yolo
    provides: "Live TRT factory branch + soft-fallback reason codes + parity suite (10-01)"
provides:
  - "Docs honesty for live TRT conditions matching factory path"
  - "On-device engine lifecycle rules (TRT-02)"
  - "JetPack/system TensorRT packaging; no pip tensorrt pin (TRT-03)"
  - "Keyword/static tests encoding TRT-02/03 honesty"
affects:
  - 11-sticky-fallback
  - 12-edge-docs-ci

tech-stack:
  added: []
  patterns:
    - "Live TRT docs mirror factory: preferred + .engine + system tensorrt → backend_live=tensorrt"
    - "Soft-fallback reason vocabulary in operator docs (trt_artifact_missing|trt_dep_missing|path_rejected)"
    - "No project tensorrt pip extra; JetPack/system only"
    - "Keyword tests couple live + tensorrt + .engine without requiring hardware"

key-files:
  created: []
  modified:
    - docs/export/yolo26-onnx-tensorrt.md
    - docs/export/jetson-packaging.md
    - docs/export/README.md
    - docs/architecture.md
    - docs/configuration.md
    - src/sentry_ai/config/profiles/jetson.yaml
    - tests/test_export_docs.py

key-decisions:
  - "Primary live TRT table in yolo26-onnx-tensorrt.md; JetPack/no-pip in jetson-packaging.md"
  - "jetson.yaml comments only — YAML field values unchanged"
  - "No FPS claims; dual-model measure-on-device with Phase 11 deferred"
  - "Conf caveat: runtime conf via Ultralytics postprocess NMS for default engines"

patterns-established:
  - "Export docs live matrix covers both ORT (Phase 9) and TRT (Phase 10) under conditions"
  - "Absolute TRT-not-live-yet language removed for fixed-class"
  - "test_no_tensorrt_optional_extra remains the packaging hygiene gate"

requirements-completed: [TRT-02, TRT-03]

duration: 2min
completed: 2026-08-10
---

# Phase 10 Plan 02: On-Device TRT Docs + Jetson Packaging Honesty Summary

**Operator docs and keyword tests state live fixed-class TensorRT only when preferred_backend=tensorrt + allowlisted .engine + system/JetPack tensorrt are present; on-device never-copy rules and no project tensorrt pip pin preserved (TRT-02/TRT-03).**

## Performance

- **Duration:** 2 min
- **Started:** 2026-08-10T15:01:02Z
- **Completed:** 2026-08-10T15:02:59Z
- **Tasks:** 2/2
- **Files modified:** 7

## Accomplishments

- Replaced absolute “TRT not live yet / future phase” language with honest live conditions matching 10-01 factory behavior
- Documented soft-fallback reasons `trt_artifact_missing` / `trt_dep_missing` / `path_rejected` across export + product docs
- Strengthened Jetson packaging: JetPack/system TensorRT only, no project pip pin, on-device build, never-copy, no multi-SKU prebuilt engines
- Serve recipe discoverable: export_yolo.py --format engine → SENTRY_DETECTOR_ENGINE / allowlist → sentry serve --profile jetson
- Keyword tests encode live TRT + packaging hygiene; full Phase 10 automated suite green (63 passed) without Jetson/system TRT

## Task Commits

Each task was committed atomically:

1. **Task 1: Docs honesty for live TRT + on-device lifecycle (TRT-02, TRT-03)** - `0a9503f` (docs)
2. **Task 2: Keyword/static tests for TRT-02/03 + phase suite gate** - `6bb2dc1` (test)

**Plan metadata:** `90e5daa` (docs: complete plan)

## Files Created/Modified

- `docs/export/yolo26-onnx-tensorrt.md` — Live TRT table row, soft-fallback reasons, env placement, conf caveat, deferred list honesty
- `docs/export/jetson-packaging.md` — Live TRT when conditions met; JetPack/system TRT; no pip pin; dual-model measure-on-device
- `docs/export/README.md` — Live ORT + live TRT matrix; removed absolute non-live language
- `docs/architecture.md` — Profiles vs live inference includes live TRT conditions
- `docs/configuration.md` — preferred tensorrt live conditions + SENTRY_DETECTOR_ENGINE / ARTIFACT_ROOT env
- `src/sentry_ai/config/profiles/jetson.yaml` — Header comments only (live TRT when .engine + system tensorrt)
- `tests/test_export_docs.py` — Live TRT conditions + system packaging / no pip extra keyword asserts

## Decisions Made

- Doc surface split per plan discretion: primary live table in yolo26; packaging in jetson-packaging; short honesty in architecture/configuration
- jetson.yaml field values untouched (`preferred_backend: tensorrt` remains)
- pyproject.toml not modified; `test_no_tensorrt_optional_extra` remains the static gate
- No invented FPS; dual-model first-class deferred to Phase 11

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None for CI/dev. On-device makers need JetPack/system TensorRT (`python -c "import tensorrt"`) and an on-device-built `.engine` — documented in export docs, not a project pip install.

## Known Stubs

None. Docs describe real factory conditions from 10-01; soft-fallback when artifact/dep missing is intentional honesty.

## Threat Flags

None new. Mitigations applied for plan threat model:
- T-10-09: keyword tests require live conditions + soft-fallback honesty
- T-10-10: `test_no_tensorrt_optional_extra` stays green; no pyproject tensorrt key
- T-10-11: on-device / never-copy / no prebuilt language retained + keyword-asserted
- T-10-12: no FPS claims; measure-on-device dual-model note
- T-10-13: only allowlisted env paths documented (`SENTRY_DETECTOR_ENGINE`, `SENTRY_ARTIFACT_ROOT`)
- T-10-SC: no package installs; docs forbid project pip pin

## Verification

```text
uv run pytest tests/test_export_docs.py tests/test_pyproject_onnx_extra.py \
  tests/test_detection_factory.py tests/test_trt_parity.py \
  tests/test_backend_honesty_status.py tests/test_artifact_paths.py -q
# 63 passed

uv run ruff check tests/test_export_docs.py
# All checks passed

rg -n 'TRT not live yet|live TensorRT is not claimed until a future' docs/
# empty

# no tensorrt optional-extra; no *.engine committed; spine freeze intact
# factory still has backend_live="tensorrt" live path from 10-01
```

## Success Criteria Mapping

| Criterion | Status |
|-----------|--------|
| On-device build + no multi-SKU prebuilt engines (TRT-02) | Met |
| JetPack/system TRT + no project pip pin (TRT-03) | Met |
| Live TRT conditions match 10-01 + soft-fallback reasons | Met |
| Keyword/static tests encode honesty; no-tensorrt extra green | Met |
| Export → place engine → serve recipe discoverable | Met |
| Phase 10 automated suite green without Jetson | Met |

## Next Phase Readiness

- Phase 10 complete for automated dimensions (factory + docs)
- Sticky thrash-free fallback remains Phase 11
- Full edge-serve narrative polish + AGPL lineage refresh remain Phase 12

## Self-Check: PASSED

- FOUND: `docs/export/yolo26-onnx-tensorrt.md`
- FOUND: `docs/export/jetson-packaging.md`
- FOUND: `docs/export/README.md`
- FOUND: `docs/architecture.md`
- FOUND: `docs/configuration.md`
- FOUND: `src/sentry_ai/config/profiles/jetson.yaml`
- FOUND: `tests/test_export_docs.py`
- FOUND: commits `0a9503f`, `6bb2dc1`, `90e5daa`
