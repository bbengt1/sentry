---
phase: 04-monocular-depth
plan: 01
subsystem: depth
tags: [depth-anything-v2, transformers, huggingface, perception-store, frame-bus, monocular-depth]

# Dependency graph
requires:
  - phase: 03-fixed-class-detection
    provides: DetectionLoop / YoloDetectionWorker / PerceptionStore / configure_model_cache patterns
  - phase: 02-camera-ingest
    provides: FrameBus + ImageFrame keep-latest bus
  - phase: 01-foundation
    provides: DepthKind / DepthPayload / ModelWorker protocol / plugin registry
provides:
  - optional-extra depth (torch/transformers/hf-hub/pillow)
  - DepthAnythingWorker with injectable model/processor (CI-safe)
  - DepthLoop FrameBus subscriber twin of DetectionLoop
  - PerceptionStore DepthProduct + set_depth/snapshot_depth + depth metrics
  - pure preprocess (BGR→RGB, depth_stats) and MODE_TO_MODEL / kind_for_mode
  - HF_HOME under SENTRY_MODEL_CACHE/hf
affects: [04-02 monocular-depth API/UI, phase-05 free-space]

# Tech tracking
tech-stack:
  added: [torch, transformers, huggingface-hub, pillow]
  patterns:
    - injectable ModelWorker + dedicated FrameBus loop (mirror detect)
    - dual product PerceptionStore (det + depth keep-latest)
    - kind/unit honesty from configured mode only
    - optional-extra for heavy ML deps

key-files:
  created:
    - src/sentry_ai/models/depth/__init__.py
    - src/sentry_ai/models/depth/preprocess.py
    - src/sentry_ai/models/depth/mapping.py
    - src/sentry_ai/models/depth/worker.py
    - src/sentry_ai/models/depth/loop.py
    - tests/test_depth_preprocess.py
    - tests/test_depth_mapping.py
    - tests/test_depth_worker.py
    - tests/test_depth_loop.py
    - tests/test_depth_colormap.py
    - tests/test_api_depth.py
  modified:
    - pyproject.toml
    - uv.lock
    - src/sentry_ai/models/cache.py
    - src/sentry_ai/state/perception_store.py
    - src/sentry_ai/plugins/registry.py
    - THIRD_PARTY_MODELS.md
    - README.md
    - tests/test_model_cache.py
    - tests/test_perception_store.py
    - tests/test_plugins_registry.py
    - tests/test_third_party_models_doc.py
    - .gitignore

key-decisions:
  - "HF Transformers DAV2 Small default (Apache-2.0); never Base/Large NC"
  - "Extend one PerceptionStore with DepthProduct rather than separate DepthStore"
  - "kind_for_mode from configured depth_mode only — no float-range heuristics"
  - "Full HxW float depth_map in-process; wire JSON deferred to 04-02"
  - "optional-extra depth; unit tests inject fakes and never hit HF hub"

patterns-established:
  - "DepthLoop structural twin of DetectionLoop (bus → process → set_depth, error-alive)"
  - "DepthAnythingWorker inject model+processor for CI; configure_model_cache before from_pretrained"
  - "MODE_TO_MODEL Small-only allowlist for relative/metric_indoor/metric_outdoor"

requirements-completed: [DEPTH-01]

# Metrics
duration: 12min
completed: 2026-08-08
---

# Phase 4 Plan 01: Monocular Depth Core Summary

**Injectable DepthAnythingWorker + DepthLoop publish keep-latest DepthProduct into PerceptionStore with honest DepthKind/unit; HF cache under SENTRY_MODEL_CACHE; CI never downloads weights.**

## Performance

- **Duration:** ~12 min
- **Started:** 2026-08-08T10:07:52Z
- **Completed:** 2026-08-08T10:20:00Z
- **Tasks:** 3/3
- **Files modified:** 22

## Accomplishments

- Optional `depth` extra + entry point `depth-anything-v2-small`; HF_HOME sibling of YOLO weights under Sentry cache
- Pure preprocess/mapping contracts with golden tests locking BGR→RGB and mode honesty (relative forbids meters)
- `DepthAnythingWorker` + `DepthLoop` process FrameBus frames into store without cameras; dual det+depth products coexist
- Plugin registry registers depth worker when importable; 04-02 colormap/API tests skip cleanly

## Task Commits

Each task was committed atomically:

1. **Task 1: Wave 0 depth extra, package skeleton, HF cache, docs, test stubs** - `23fdcba` (feat)
2. **Task 2: Preprocess + mapping contracts + PerceptionStore DepthProduct** - `1748513` (feat)
3. **Task 3: DepthAnythingWorker + DepthLoop + plugin registration** - `fbba1e8` (feat)

**Plan metadata:** `1faa222` (docs: complete plan)

## Files Created/Modified

- `src/sentry_ai/models/depth/worker.py` — DepthAnythingWorker + DepthResult; injectable HF path
- `src/sentry_ai/models/depth/loop.py` — DepthLoop keep-latest bus subscriber
- `src/sentry_ai/models/depth/preprocess.py` — bgr_to_rgb_uint8, depth_stats
- `src/sentry_ai/models/depth/mapping.py` — MODE_TO_MODEL, kind_for_mode
- `src/sentry_ai/state/perception_store.py` — DepthProduct + depth metrics dual half
- `src/sentry_ai/models/cache.py` — HF_HOME / HUGGINGFACE_HUB_CACHE under cache root
- `src/sentry_ai/plugins/registry.py` — depth-anything-v2-small builtin registration
- `pyproject.toml` / `uv.lock` — optional-extra depth
- `THIRD_PARTY_MODELS.md` / `README.md` — Phase 4 Apache Small default + install docs
- Tests for preprocess, mapping, worker, loop, store, cache, registry; 04-02 skip stubs

## Decisions Made

- Followed plan locks: HF Transformers Small default, extend PerceptionStore, injectable fakes, relative default honesty
- Thin-copied `resolve_device` into depth worker (YOLO twin; shared util deferred)
- `depth_map` may share array reference on snapshot_depth (documented immutability after set)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] YOLO_CONFIG_DIR test isolation under setdefault**
- **Found during:** Task 3 verification
- **Issue:** `test_configure_model_cache_uses_arg` failed when prior tests left `YOLO_CONFIG_DIR` set; `os.environ.setdefault` would not overwrite, so YOLO path assert was false under tmp_path
- **Fix:** delenv `YOLO_CONFIG_DIR` in cache tests that assert path under tmp_path
- **Files modified:** `tests/test_model_cache.py`
- **Verification:** full suite green
- **Committed in:** `fbba1e8` (part of Task 3)

---

**Total deviations:** 1 auto-fixed (Rule 1)
**Impact on plan:** Necessary test isolation; no scope creep. 04-02 surface intentionally deferred.

## Issues Encountered

None blocking. Full suite: 203 passed, 4 skipped (04-02 stubs), ruff clean without depth weights.

## User Setup Required

None for unit path. Real depth inference requires:

```bash
uv sync --extra dev --extra depth
# first run downloads HF weights into SENTRY_MODEL_CACHE/hf (or ~/.cache/sentry-ai/hf)
```

Serve/API wiring is 04-02.

## Known Stubs

| Stub | File | Reason |
|------|------|--------|
| colormap tests | `tests/test_depth_colormap.py` | Deferred to 04-02 (pytest.mark.skip) |
| API depth tests | `tests/test_api_depth.py` | Deferred to 04-02 (pytest.mark.skip) |

No production stubs that block DEPTH-01 pipeline goals.

## Threat Flags

None beyond plan threat model. Mitigations applied:

- T-04-01: kind_for_mode from mode only; schema rejects relative+unit
- T-04-02: MODE_TO_MODEL Small allowlist; HF_HOME under SENTRY_MODEL_CACHE
- T-04-03: never Base/Large default
- T-04-04: dedicated DepthLoop; never infer in capture/handlers
- T-04-SC: optional-extra only; no timm native path

## Next Phase Readiness

04-02 can attach:

- snapshot/status DepthPayload metadata + stats
- colormap MJPEG composite
- `sentry serve` DepthLoop start + depth_worker DI
- runtime depth_mode config foundation (`set_depth_mode` already on worker)

## Self-Check: PASSED

- [x] `src/sentry_ai/models/depth/worker.py` exists
- [x] `src/sentry_ai/models/depth/loop.py` exists
- [x] `src/sentry_ai/models/depth/preprocess.py` exists
- [x] `src/sentry_ai/models/depth/mapping.py` exists
- [x] Commits `23fdcba`, `1748513`, `fbba1e8` present
- [x] Full pytest green without real HF weights
