---
phase: 07-edge-profiles-extension-stubs
plan: 02
subsystem: edge-export
tags: [export, onnx, tensorrt, jetson, yolo26, yoloe, depth-anything, ultralytics, edge]

# Dependency graph
requires:
  - phase: 07-01
    provides: Profile wiring (jetson/desktop-gpu/cpu-fallback), KNOWN_WEIGHTS including yoloe n/s
  - phase: 03-detection
    provides: Ultralytics detect extra + YOLO26 weights allowlist
  - phase: 06-developer-controls-open-vocab
    provides: YOLOE weights in KNOWN_WEIGHTS
provides:
  - docs/export suite (ONNX/TRT recipes + Jetson packaging honesty)
  - scripts/export/export_yolo.py thin CLI (KNOWN_WEIGHTS basename allowlist)
  - Content + CLI tests without Jetson/GPU/real export in CI
affects: [07-03-extension-stubs-docs, edge-deploy, EDGE-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Export is offline docs+scripts; live serve stays PyTorch profiles"
    - "TensorRT engines built on-device; never copy .engine across SKUs"
    - "KNOWN_WEIGHTS basename-only validation rejects path traversal"
    - "Doc honesty tests via pathlib keyword asserts (third_party pattern)"

key-files:
  created:
    - docs/export/README.md
    - docs/export/yolo26-onnx-tensorrt.md
    - docs/export/yoloe-export.md
    - docs/export/depth-anything-v2.md
    - docs/export/jetson-packaging.md
    - scripts/export/export_yolo.py
    - scripts/export/README.md
    - tests/test_export_docs.py
    - tests/test_export_script_cli.py
  modified:
    - README.md
    - pyproject.toml

key-decisions:
  - "EDGE-03 delivered as docs + scripts only — no TRT InferenceBackend"
  - "Import KNOWN_WEIGHTS from sentry_ai.models.cache with frozenset fallback"
  - "YOLOE export documented experimental; PyTorch on-demand OV remains supported"
  - "Depth export is feasibility notes; live path stays HF Small"
  - "pytest mark export registered for opt-in full export (skipped by default)"
  - "No tensorrt/onnx project extras"

patterns-established:
  - "scripts/export/* not imported by sentry_ai runtime package"
  - "validate_weights + parse_args testable without ultralytics"
  - "Export docs copy camera-sources honesty matrix style"

requirements-completed: [EDGE-03]

# Metrics
duration: 3min
completed: 2026-08-08
---

# Phase 7 Plan 02: Export Recipes + Jetson Packaging Summary

**ONNX/TensorRT export recipes and Jetson packaging notes as docs + a safe Ultralytics CLI wrapper — no live TRT runtime, no prebuilt engines, no Jetson in CI**

## Performance

- **Duration:** 3 min
- **Started:** 2026-08-08T17:11:05Z
- **Completed:** 2026-08-08T17:14:15Z
- **Tasks:** 2/2
- **Files modified:** 11

## Accomplishments

- Shipped `docs/export/*` with on-device TensorRT hard rules, no cross-SKU engine copy, Jetson n + DAV2 Small + OV off/on-demand honesty, Pi/CPU lite/best-effort language
- Added `scripts/export/export_yolo.py` with KNOWN_WEIGHTS basename allowlist and path-traversal rejection
- Keyword + CLI tests green without GPU, Jetson, weight download, or real `model.export`
- README links edge export docs (additive only; desktop-gpu/safety left for 07-03)

## Task Commits

Each task was committed atomically (TDD RED → GREEN):

1. **Task 1 RED: Export docs keyword tests** - `27f3ac8` (test)
2. **Task 1 GREEN: Export + Jetson documentation suite** - `61244fe` (docs)
3. **Task 2 RED: Export script CLI tests** - `0e47171` (test)
4. **Task 2 GREEN: export_yolo CLI + scripts README** - `7a92a25` (feat)

**Plan metadata:** `278169e` (docs: complete plan)

## Files Created/Modified

- `docs/export/README.md` — export index, offline vs live PyTorch honesty
- `docs/export/yolo26-onnx-tensorrt.md` — YOLO26 ONNX/engine recipes + on-device rules
- `docs/export/yoloe-export.md` — experimental YOLOE export + PyTorch OV fallback
- `docs/export/depth-anything-v2.md` — HF Small live path + community export notes
- `docs/export/jetson-packaging.md` — JetPack/TRT packaging, measure-on-device matrix
- `scripts/export/export_yolo.py` — argparse CLI, allowlist, Ultralytics export main path
- `scripts/export/README.md` — how to run with `uv run python scripts/export/...`
- `tests/test_export_docs.py` — existence + honesty keyword asserts
- `tests/test_export_script_cli.py` — --help, validate_weights, traversal, no real export
- `README.md` — Export (ONNX / TensorRT) subsection linking docs/export
- `pyproject.toml` — register `export` pytest mark

## Decisions Made

- Followed locked CONTEXT/RESEARCH decisions: docs+scripts only; on-device engines; no prebuilt `.engine`; no `tensorrt` pip extra; YOLOE experimental; depth feasibility-only
- Prefer `from sentry_ai.models.cache import KNOWN_WEIGHTS` with identical frozenset fallback if import fails
- README ownership: additive export section only (07-03 owns desktop-gpu + safety rewrite)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Register pytest `export` mark**
- **Found during:** Task 2 (CLI tests)
- **Issue:** `@pytest.mark.export` emitted `PytestUnknownMarkWarning`
- **Fix:** Added marker to `[tool.pytest.ini_options]` in `pyproject.toml`
- **Files modified:** `pyproject.toml`
- **Verification:** suite runs clean (19 passed, 1 skipped, 0 warnings)
- **Committed in:** `7a92a25` (part of Task 2 feat)

---

**Total deviations:** 1 auto-fixed (Rule 2)
**Impact on plan:** Hygiene only; no scope creep; no new packages.

## Issues Encountered

None

## User Setup Required

None — export is optional maker tooling using existing `detect` extra. TensorRT engines require system JetPack/TRT on the maker’s target device (documented, not product install).

## Known Stubs

None that block EDGE-03. Intentional non-product surfaces:

- No live ONNX Runtime / TensorRT `InferenceBackend` (deferred by design)
- YOLOE export path is experimental; PyTorch OV is the supported edge path
- Depth export is community feasibility notes only
- Opt-in `@pytest.mark.export` full-export test remains skipped by default

## Threat Flags

None beyond plan threat model. Mitigations applied:

| Threat | Mitigation shipped |
|--------|-------------------|
| T-07-10 path traversal on `--weights` | Basename + KNOWN_WEIGHTS allowlist |
| T-07-11 engine portability | Docs + keyword tests (on-device / do not copy) |
| T-07-12 CI real export | Tests never call `model.export` |
| T-07-13 AGPL | Export docs link THIRD_PARTY_MODELS.md |
| T-07-14 depth meters honesty | depth doc preserves relative / metric_estimated |
| T-07-SC package installs | No tensorrt/onnx extras |

## Verification

```text
uv run pytest tests/test_export_docs.py tests/test_export_script_cli.py -q
# 19 passed, 1 skipped
```

- No `.engine` files committed
- `pyproject.toml` has no `tensorrt` extra
- `uv run python scripts/export/export_yolo.py --help` exits 0 and mentions onnx/engine

## Self-Check: PASSED

- All required artifacts present under `docs/export/`, `scripts/export/`, `tests/`
- Commits `27f3ac8`, `61244fe`, `0e47171`, `7a92a25` present on branch

## Next Phase Readiness

- **Ready for 07-03:** yes
- 07-03 owns extension stubs (ROS2/voice/multi-cam) + desktop-gpu + safety/privacy docs
- Do not re-edit export recipes unless 07-03 needs cross-links only
