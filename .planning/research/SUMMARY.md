# Project Research Summary

**Project:** Sentry AI — v0.3 Metric Depth Calibration UX  
**Domain:** Monocular depth scale calibration (known height / marker → honest metric scale)  
**Researched:** 2026-08-11  
**Confidence:** HIGH

## Executive Summary

Sentry AI v0.3 is a **maker calibration UX milestone**, not a new depth model or SLAM product. Monocular DAV2 depth is scale-ambiguous; experts recover meters by **anchoring user ground truth** (tape distance, known object height, optional floor marker) and fitting a global affine scale — then labeling the product `metric_calibrated` only when that ground truth is applied. Domain metric heads stay `metric_estimated`; relative stays relative with `unit=null`. Free-space remains ordinal until a real calibrated depth product exists.

**Recommended approach:** Add **zero new pip dependencies**. Implement pure-numpy scale/shift fit + thread-safe `CalibrationState`, apply **post-`DepthAnythingWorker.process` / pre-`PerceptionStore.set_depth` inside DepthLoop**, expose wizard REST + static Live Preview panel, persist per-`camera_id` YAML under the existing cache root, and promote free-space to meters only when kind is `metric_calibrated`. DetectionLoop, FrameBus, ORT/TRT factory, and perception-only API boundary stay frozen.

**Key risks:** (1) **Silent unit lies** — labeling relative maps as meters without kind promotion; (2) **Free-space breakage** — flipping `units="m"` while still running per-frame ordinal percentile bands; (3) **Persistence hazards** — re-applying scale for the wrong camera/resolution/model. Mitigate by honesty-first contracts, metric free-space only after scaled maps exist, and fingerprint-gated auto-load. Never claim vehicle-grade accuracy.

## Key Findings

### Recommended Stack

Full detail: [STACK.md](./STACK.md)

**Add zero third-party packages.** Calibration is product logic on the shipped FastAPI / Pydantic 2 / NumPy / OpenCV / PyYAML / static Live Preview stack. No scipy, React, SLAM, Open3D, platformdirs, or new depth network.

**Core technologies:**
- **NumPy** (≥2.0) — scale-only median or scale+shift `lstsq`; map apply — sufficient for monocular affine recovery
- **Pydantic 2** — calibration record + API bodies (`extra=forbid`) — matches all wire models
- **PyYAML** — per-`camera_id` persist files — same family as profiles; no DB
- **FastAPI + static `index.html`** — wizard REST + Live Preview panel — no npm frontend
- **OpenCV headless** — optional ArUco assist / freeze JPEG — already core; no april-tag pip
- **Existing DAV2 + `DepthKind`** — relative / metric_estimated source maps; calibration is post-process only

**Critical constraint:** Do not add a `calibration` extra. Depth still needs existing `--extra depth`.

### Expected Features

Full detail: [FEATURES.md](./FEATURES.md)

**Must have (table stakes):**
- Live Preview **calibration wizard** (known distance primary + known height)
- **Apply / Cancel** with visual feedback (staging before commit)
- Promote to **`metric_calibrated` + `unit: "m"`** only when applied and valid
- **Never** label relative as meters (FOUND-03 / validators)
- **Free-space uses meters when calibrated**; ordinal otherwise
- **Persist + re-apply** per `camera_id` at `sentry serve` (headless path)
- **Clear / invalidate** calibration (remount recovery)
- UI ↔ snapshot ↔ `/v1` **single truth**
- **CI-safe synthetic tests** + operator docs

**Should have (competitive):**
- Guided multi-step wizard (not a raw scale slider)
- Residual / confidence readout for multi-point fits
- Staging preview numbers before Apply
- Status fingerprint (`calibration_active`, method, scale, age)
- Works on both relative and metric_estimated bases

**Defer (v2+ / later milestone):**
- Full chessboard intrinsic suite as primary path
- ArUco/AprilTag as *required* marker
- Language/CLIP auto-scale
- Continuous online re-cal without consent
- Stereo / SLAM / ROS2 metric TF
- Obstacle `distance_m` on every cue if schema churn is high (prefer band/unit flip first)
- Live ORT/TRT for depth models

### Architecture Approach

Full detail: [ARCHITECTURE.md](./ARCHITECTURE.md)

Treat calibration as a **runtime affine transform on monocular depth**, not a neural stage and not a FreeSpaceLoop rewrite. **Single insert point:** after `DepthAnythingWorker.process`, before `PerceptionStore.set_depth`. Free-space, MJPEG, assemble, and `/v1` all inherit the calibrated map + kind — no dual truth.

**Major components:**
1. **Pure fit helpers** (`spatial/calibration` or `models/depth/calibration`) — samples → scale/shift → validate/reject
2. **`CalibrationState`** — thread-safe draft vs applied; `apply_map()`; camera_id match
3. **DepthLoop hook** — sole writer of scaled depth + kind promotion
4. **`routes_calibration`** — freeze/sample/fit/apply/cancel/persist; no inference, no cameras
5. **Persist I/O** — versioned YAML per camera_id; soft-fail corrupt; fingerprint refuse
6. **Live Preview wizard** — extend `ui/static/index.html`; draft never claims meters
7. **Free-space + assemble honesty** — `units="m"` only for `METRIC_CALIBRATED`; reset smoother on apply/clear

**Frozen:** FrameBus, DetectionLoop, OpenVocabLoop, DepthAnythingWorker infer core, `kind_for_mode` (never returns calibrated), ORT/TRT factory, perception-only boundary.

**Hot path:**
```
DepthAnythingWorker.process → raw map + kind/unit
  → CalibrationState.apply_if_active → scale*map+shift; kind=metric_calibrated; unit="m"
  → PerceptionStore.set_depth
  → FreeSpaceLoop (inherits kind; metric units only when calibrated)
```

### Critical Pitfalls

Full detail: [PITFALLS.md](./PITFALLS.md)

1. **Silent unit lies** — `unit="m"` or free-space meters while map is still relative / wrong model loaded. **Avoid:** promote kind+unit together from mode + calib state only; validators on every surface; mode switch must reload/invalidate weights.
2. **Free-space breakage** — flip `units="m"` while percentile nearness cuts still run. **Avoid:** gate meters on a real metric path (absolute thresholds and/or separate `distance_m`); never overload `nearness_*` 0..1 as meters; reset `OccupancySmoother` on apply/clear.
3. **Persistence hazards** — wrong camera/resolution/model auto-applies stale scale. **Avoid:** key by camera_id + capture fingerprint + image size + depth mode/model; refuse mismatch; atomic write; soft inactive on corrupt.
4. **Scale math lies** — bbox height alone without geometry; pure scale on affine maps; double-scale on metric heads. **Avoid:** prefer known-distance samples; one documented formula; residual reject; store base mode; sample only when inactive.
5. **Wizard UX thrash** — partial apply, Cancel lies, UI meters before `/v1`. **Avoid:** draft → preview → atomic commit state machine; UI never invents calibrated; sticky scale after commit.

## Implications for Roadmap

Phases continue from v0.2 (phases 8–12). Suggested **v0.3 phases 13–18**.

### Phase 13: Honesty Contracts & CalibrationState Model
**Rationale:** Same lesson as v0.2 backend_live honesty — without kind/unit/calib state, every later feature invents lies. Schema and promotion rules must exist before math or UI.  
**Delivers:** `CalibrationParams` / sample models; promotion gate (`metric_calibrated` only when applied+valid); status field shapes; validators/tests for relative-forbids-m matrix; fingerprint fields designed (even if I/O later).  
**Addresses:** Never label relative as meters; kind triad honesty; contract stability.  
**Avoids:** Pitfall #1 silent unit lies; #8 double-scale schema confusion.  
**Research flag:** Standard — enum/validators already exist; extend carefully.

### Phase 14: Scale Math + DepthLoop Plug-in
**Rationale:** Math before chrome. Wizard without pure fit stamps `metric_calibrated` on garbage. Apply must land on the depth product so free-space and UI share one truth.  
**Delivers:** numpy scale-only (MVP) + optional scale+shift fit; reject rules; `CalibrationState.apply_map`; DepthLoop post-process hook; synthetic unit tests (no room); mode-aware apply (relative vs metric_estimated).  
**Addresses:** Ground-truth scale fit; promote kind on applied product.  
**Uses:** NumPy only; no new deps.  
**Avoids:** Pitfall #4 scale math; #9 thread races (single apply site).  
**Research flag:** **Needs research** — affine-in-inverse vs pure scale for relative DAV2 polarity; residual thresholds.

### Phase 15: Calibration REST API + Live Preview Wizard
**Rationale:** Maker-primary path is Live Preview; API first (or same phase) so UI is not inventing endpoints. Draft/commit prevents mid-wizard meter claims.  
**Delivers:** `/api/depth/calibration/*` (freeze, sample, fit, apply, cancel, status); static wizard (known distance + known height); staging preview; Apply/Cancel; honesty copy (not FSD); status badge for `metric_calibrated`.  
**Addresses:** Wizard; apply/cancel; known height + distance paths; UI single truth with store.  
**Avoids:** Pitfall #5 UX thrash; #6 overclaim copy; #10 colormap-only feedback (show numeric sample).  
**Research flag:** Height path geometry (weak FOV) — **needs research** or document distance-primary. Wizard UX patterns are standard.

### Phase 16: Free-Space Metric Path
**Rationale:** Free-space meters **depend** on honestly calibrated depth maps. Do not ship free-space `units="m"` in the same PR as wizard chrome alone.  
**Delivers:** `assemble._units_for_depth_kind` returns `"m"` only for `METRIC_CALIBRATED`; ordinal for relative **and** metric_estimated; metric band thresholds and/or optional additive `distance_m`; smoother reset on apply/clear; golden tests.  
**Addresses:** Free-space metric when calibrated; never relative-as-meters.  
**Avoids:** Pitfall #2 free-space breakage.  
**Research flag:** **Needs research** — absolute meter band cuts vs keep ordinal nearness + separate distance fields; threshold defaults for makers.

### Phase 17: Persist & Re-apply on Serve
**Rationale:** Wrong persistence is a **permanent** silent lie. Only save what in-memory apply already got right; headless robots need load without wizard.  
**Delivers:** YAML under `$SENTRY_MODEL_CACHE/calibration/{camera_id}.yaml` (or resolved equivalent); atomic write; load at serve with fingerprint check; auto-apply when valid; clear/delete; banner + status (`applied | none | ignored_mismatch | error`); headless path.  
**Addresses:** Persist + re-apply; clear calibration; headless deploy.  
**Avoids:** Pitfall #3 persistence hazards.  
**Research flag:** Low — file I/O standard; resolve cache vs config path (see Gaps).

### Phase 18: Docs + Synthetic CI Polish
**Rationale:** Operator success needs a guided flow; docs must not still say “free-space always ordinal” after metric path ships.  
**Delivers:** Operator calibration guide; update `perception-frame.md` + safety copy; synthetic E2E honesty matrix; residual hardware-free CI green.  
**Addresses:** Docs; CI-safe tests; non-FSD language.  
**Avoids:** Pitfall #6 overclaim; #12 CI needs real room; doc drift.  
**Research flag:** Skip — content + test expansion.

### Phase Ordering Rationale

```
13 Honesty/state ──► 14 Scale apply (DepthLoop) ──► 15 Wizard + API
                              │
                              ▼
                       16 Free-space metric
                              │
                              ▼
                       17 Persist/re-apply ──► 18 Docs/CI
```

- **Honesty first** — kind/unit/calib state before any product mutation  
- **Math before chrome** — pure fit + DepthLoop apply before wizard labels  
- **Depth apply before free-space meters** — free-space must consume real scaled maps  
- **Wizard before or with free-space UI feedback**, but free-space *algorithm* honesty is its own phase  
- **Persist late among features** — only persist proven apply path  
- **Docs finalize after wire behavior exists**

### Research Flags

| Phase | Flag | Why |
|-------|------|-----|
| **14** | **Needs `/gsd:plan-phase --research`** | Scale formula (pure scale vs affine); residual gates; metric_estimated double-scale |
| **15** | Partial research | Known-height without full intrinsics — distance-primary recommended; FOV assumption documented |
| **16** | **Needs research** | Free-space meter band semantics (absolute cuts vs distance_m fields) |
| **13, 17, 18** | Standard patterns | Validators, YAML I/O, static HTML, docs — skip deep research |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Code-verified no new deps; all primitives in core + depth extra |
| Features | **HIGH** | Table stakes map cleanly to PROJECT.md v0.3 goals + shipped contracts |
| Architecture | **HIGH** | DepthLoop plug-in verified against writer ownership; free-space consumer clear |
| Pitfalls | **HIGH** | Unit lies / free-space / persist verified against assemble, free_space, validators |

**Overall confidence:** **HIGH**

### Gaps to Address

- **Persist path convention:** STACK prefers `$SENTRY_MODEL_CACHE/calibration/*.yaml` (cache root); ARCHITECTURE prefers `~/.config/sentry-ai/calibration/*.json`. **Opinion for roadmap:** follow STACK — existing `default_cache_root()`, YAML, no platformdirs — resolve in Phase 17 plan.
- **Free-space meter semantics:** ARCHITECTURE leans “flip units + optional distance_m, keep nearness ordinal”; PITFALLS requires absolute metric thresholds before claiming `units="m"`. **Lock in Phase 16 research** — do not ship label-only meters.
- **Known-height geometry:** Without intrinsics, height path is approximate. **MVP:** known-distance primary; height converts to distance sample under documented FOV assumption or produces residual-checked samples.
- **Exact residual / scale clamps:** Phase-tuned bounds; synthetic tests first.
- **Whether ObstacleCue gains `distance_m` in v0.3:** Prefer minimal schema growth (units + bands) unless robot signal needs the field — decide in Phase 16.

## Sources

### Primary (HIGH confidence)
- In-repo: `PROJECT.md` v0.3 goals; `schemas/enums.py` (`DepthKind`); `validators.py`; `models/depth/mapping.py`, `worker.py`, `loop.py`; `spatial/free_space.py`, `loop.py`; `api/assemble.py`; `routes_depth.py`; `ui/static/index.html`; `docs/perception-frame.md`, `safety-and-privacy.md`
- Research files: [STACK.md](./STACK.md), [FEATURES.md](./FEATURES.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [PITFALLS.md](./PITFALLS.md)
- Phase 4/5 historical depth honesty research under `.planning/milestones/`

### Secondary (MEDIUM confidence)
- OpenCV ArUco main-module docs — optional marker assist without new packages
- DAV2 metric_depth README — indoor 20 m / outdoor 80 m domain limits; estimated ≠ calibrated
- HF monocular depth scale/shift fundamentals

### Tertiary (LOW confidence)
- Language-prior auto-scale papers — **anti-feature** for core path; citation only

---

## Opinionated defaults (roadmap lock)

1. **Zero new dependencies**  
2. **Post-process scale/shift in DepthLoop** — never retrain or bake into HF weights  
3. **Primary GT = known distance**; height/marker feed the same fitter  
4. **`metric_calibrated` + `unit="m"` only when applied and valid**; cancel restores prior honesty  
5. **Free-space meters only after metric path exists** — never ordinal cuts relabeled as m  
6. **Persist per camera_id with fingerprint refuse** — auto-load on serve when valid  
7. **Static wizard + REST** — no React, no SLAM, no full intrinsics primary, no FSD claims  

---
*Research completed: 2026-08-11*  
*Ready for roadmap: yes*
