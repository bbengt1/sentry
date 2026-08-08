---
phase: 06-developer-controls-open-vocab
verified: 2026-08-08T16:39:02Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
re_verification: false
---

# Phase 6: Developer Controls & Open-Vocab Verification Report

**Phase Goal:** Make the developer console fully interactive and add open-vocabulary detection as the flexible query path.
**Verified:** 2026-08-08T16:39:02Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Developer can enable/disable detection, depth, and free-space stages live | ✓ VERIFIED | `PipelineState` + `PATCH /api/pipeline/config` pushes `set_enabled` into Detection/Depth/FreeSpace loops; UI stage checkboxes call `patchPipeline`; loops gate `_run` on `_enabled` Event (no `stop()`/`start()`); disable clears stage product once (`clear_detections`/`clear_depth`/`clear_free_space`). Tests: `tests/test_pipeline_config.py`, `tests/test_loop_enable_gates.py`. Spot-check: PATCH disable det → 200. |
| 2 | Thresholds (conf, free-space cutoffs) adjust interactively from the UI | ✓ VERIFIED | Conf: existing `PATCH /api/detection/config` + conf slider debounce 150ms in `index.html`. Free-space: near/mid sliders → `PATCH /api/pipeline/config` with `near_cut`/`mid_cut`; `FreeSpaceLoop.set_cuts` applies next frame. Invalid `near_cut <= mid_cut` → 422 (spot-check + tests). Depth mode remains via `PATCH /api/depth/config` (prior phase). |
| 3 | Performance telemetry is visible in the dashboard | ✓ VERIFIED | Footer shows Cap/Det/Depth/FS/OV FPS + stage latencies; `applyStatus` reads `det_fps`, `depth_fps`, `free_space_fps`, `ov_fps`, `*_latency_ms` from `/api/status`. `StatusSnapshot` includes stage flags, cuts, and OV fields. Store `metrics_snapshot` exposes `ov_fps`. |
| 4 | Open-vocab prompts produce detections for custom classes via local OSS model | ✓ VERIFIED | `YoloeOpenVocabWorker.set_prompt_classes` + dirty `set_classes` + `predict`; tags `source="open_vocab"`. Default weights `yoloe-26s-seg.pt` (Ultralytics YOLOE, AGPL, documented). API: `GET/PATCH /api/open-vocab/config`, `POST /api/open-vocab/run`. UI prompt + Run. Assemble merges OV into wire detections. Overlay magenta + `ov:` prefix. |
| 5 | Open-vocab can run on-demand or lower-rate without blocking the fixed-class path | ✓ VERIFIED | Separate `OpenVocabLoop` thread (modes `off`/`on_demand`/`continuous`, `every_n=3` default continuous). Writes **only** `set_open_vocab` — never `set_detections`. `test_fixed_detection_loop_independent` asserts both loops process concurrently with separate store slots. Default mode `off`. |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `src/sentry_ai/control/pipeline_state.py` | Thread-safe stage flags + free-space cutoffs | ✓ VERIFIED | 107 lines; lock + snapshot/update; validates cuts and bools |
| `src/sentry_ai/api/routes_pipeline.py` | GET/PATCH `/api/pipeline/config` | ✓ VERIFIED | Side-effects `set_enabled` / `set_cuts`; 422 on ValueError |
| `src/sentry_ai/models/detection/loop.py` | `set_enabled` enable gate | ✓ VERIFIED | Event gate at top of `_run`; clear on disable |
| `src/sentry_ai/models/depth/loop.py` | `set_enabled` enable gate | ✓ VERIFIED | Same pattern as detection |
| `src/sentry_ai/spatial/loop.py` | `set_enabled` + near/mid cut runtime knobs | ✓ VERIFIED | `set_cuts`/`set_near_cut`/`set_mid_cut`; cuts read under lock per frame |
| `src/sentry_ai/models/detection/yoloe_worker.py` | Injectable YOLOE worker | ✓ VERIFIED | 187 lines; `model=` inject; FakeModel in tests |
| `src/sentry_ai/models/detection/open_vocab_loop.py` | Modes off/on_demand/continuous | ✓ VERIFIED | 242 lines; sole OV writer |
| `src/sentry_ai/api/routes_open_vocab.py` | config + run API | ✓ VERIFIED | 210 lines; arm on_demand without process on request path |
| `src/sentry_ai/state/perception_store.py` | OpenVocabProduct + clear/set/snapshot | ✓ VERIFIED | Separate slot; `ov_fps` metrics |
| `src/sentry_ai/api/assemble.py` | Merge fixed then OV with source tags | ✓ VERIFIED | completeness if either present |
| `src/sentry_ai/schemas/perception.py` | `Detection.source` fixed\|open_vocab | ✓ VERIFIED | default `"fixed"` |
| `src/sentry_ai/ui/static/index.html` | Stage toggles, cuts, OV UX, telemetry | ✓ VERIFIED | 849 lines; wired to pipeline + open-vocab APIs |
| `src/sentry_ai/cli.py` | serve injects control plane + OV | ✓ VERIFIED | PipelineState, loops, start/stop order |
| `THIRD_PARTY_MODELS.md` | YOLOE AGPL Phase 6 active | ✓ VERIFIED | `yoloe-26s-seg.pt` default; edge n documented |
| Phase 6 tests (pipeline, gates, cuts, yoloe, OV loop, API, assemble) | Coverage without weight download | ✓ VERIFIED | FakeModel / FakeOvWorker inject; no YOLOE download in CI |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `routes_pipeline.py` | `PipelineState` + loop `set_enabled` / cuts | PATCH side effects | ✓ WIRED | Lines 82–108 push flags and `set_cuts` |
| Detection/Depth/FreeSpace loops | `worker.process` / `compute_free_space` | `_enabled` Event gate | ✓ WIRED | All three skip compute when disabled; clear product once |
| `index.html` | `/api/pipeline/config` + `/api/status` | checkbox/slider PATCH + poll | ✓ WIRED | `patchPipeline`, stage toggles, cut sliders, telemetry in `applyStatus` |
| `cli.py` | `create_app` control plane | serve injects refs | ✓ WIRED | `pipeline_state`, loops, OV worker/loop |
| `OpenVocabLoop` | `PerceptionStore.set_open_vocab` | only OV writer | ✓ WIRED | No `.set_detections(` in source |
| `YoloeOpenVocabWorker` | YOLOE `set_classes` + `predict` | dirty flag | ✓ WIRED | set_classes only when `_classes_dirty` |
| `assemble_perception_frame` | `snapshot` + `snapshot_open_vocab` | fixed first then OV | ✓ WIRED | merge + source re-assert |
| `draw_detections` / MJPEG | `Detection.source` | magenta vs cyan | ✓ WIRED | overlay + preview extends dets from OV product |
| `index.html` | `/api/open-vocab/*` | Run + continuous + prompt | ✓ WIRED | POST run, PATCH mode continuous/off |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| Stage toggles UI | `detection_enabled` etc. | PATCH → PipelineState → loop Event | Yes (bool flags; loops skip/clear) | ✓ FLOWING |
| Free-space cut sliders | `near_cut`/`mid_cut` | PATCH → FreeSpaceLoop → `compute_free_space` | Yes (runtime floats) | ✓ FLOWING |
| Conf slider | `conf` | PATCH `/api/detection/config` → worker | Yes | ✓ FLOWING |
| Dashboard FPS/latency | `det_fps`, stage ms, `ov_fps` | `/api/status` ← store metrics + products | Yes (metrics from real process path) | ✓ FLOWING |
| OV prompt/Run | prompt classes → OV product → assemble/MJPEG | POST arm → OpenVocabLoop → set_open_vocab | Yes (worker process; tests with FakeOvWorker) | ✓ FLOWING |
| Wire detections | `merged_detections` | fixed product + OV product | Yes (merge path; dual store slots) | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Full unit suite | `uv run pytest -q` | 365 passed in 5.64s | ✓ PASS |
| Lint | `uv run ruff check src tests` | All checks passed | ✓ PASS |
| Health | `uv run sentry health` | status: ok | ✓ PASS |
| Smoke | `uv run sentry smoke` | smoke ok: 3 synthetic frames | ✓ PASS |
| Pipeline GET/PATCH + 422 | TestClient PATCH near≤mid | GET 200 defaults; invalid cuts 422; disable det 200 | ✓ PASS |
| Stage flags ≠ thread teardown | code review + `test_loop_enable_gates` | `set_enabled` only; routes never call stop/start | ✓ PASS |
| Separate OpenVocabProduct | `test_open_vocab_loop` dual-write asserts | OV never writes detections slot | ✓ PASS |
| Mock tests no weight download | `test_yoloe_worker` FakeModel | `model=` inject; no network | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No phase-declared or conventional `scripts/*/tests/probe-*.sh` for Phase 6 | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| UI-03 | 06-01 | Toggle detection/depth/free-space at runtime | ✓ SATISFIED | PipelineState + routes + enable gates + UI toggles + tests |
| UI-04 | 06-01 | Adjust conf and free-space cutoffs interactively | ✓ SATISFIED | detection conf API + pipeline cuts + UI sliders + 422 validation |
| UI-05 | 06-01 | Dashboard performance telemetry (FPS, stage latency) | ✓ SATISFIED | status fields + footer metrics including OV |
| OVD-01 | 06-02 | Open-vocab YOLOE accepts text prompts | ✓ SATISFIED | YoloeOpenVocabWorker + set_prompt_classes + API + docs |
| OVD-02 | 06-02 | On-demand or lower-rate without blocking fixed-class | ✓ SATISFIED | OpenVocabLoop modes; independent DetectionLoop test |
| OVD-03 | 06-02 | OV results on dashboard and stream when enabled | ✓ SATISFIED | assemble merge, MJPEG overlay, status ov_*, UI controls |

No orphaned Phase 6 requirements in REQUIREMENTS.md beyond the six claimed above.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO` debt markers in phase-touched sources | — | Clean |

Additional anti-stub checks:
- Loops do **not** use `stop()`/`start()` for UI toggles (enable Events only).
- OpenVocabLoop has **no** `.set_detections(` call (only docstring mention of never dual-writing).
- YOLOE worker returns `[]` without classes; process path real when classes set.
- Handlers document and tests assert they never call `worker.process` on the request path.

### Human Verification Required

None required for automated goal closure. Optional live browser check (not blocking):

1. Start `uv run sentry serve`, open Live Preview, toggle stages and confirm overlays drop/return without process restart.
2. Move conf and near/mid cut sliders; confirm response and free-space band change.
3. Enter open-vocab prompt, Run once; confirm magenta `ov:` boxes (after first YOLOE weight download if missing).

### Gaps Summary

No gaps. All five roadmap success criteria are implemented, wired, and covered by tests. Stage control uses in-loop enable flags (not thread teardown). Open-vocab is a separate product path with independent scheduling.

---

_Verified: 2026-08-08T16:39:02Z_
_Verifier: Claude (gsd-verifier)_
