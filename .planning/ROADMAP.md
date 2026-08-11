# Roadmap: Sentry AI

## Milestones

- ✅ **v1.0 Camera-only perception MVP** — Phases 1–7 (shipped 2026-08-09)
- ✅ **v0.2 Edge Runtime** — Phases 8–12 (shipped 2026-08-10)
- 🚧 **v0.3 Metric Depth Calibration UX** — Phases 13–18 (in progress)

## Phases

<details>
<summary>✅ v1.0 Camera-only perception MVP (Phases 1–7) — SHIPPED 2026-08-09</summary>

- [x] Phase 1: Foundations & Contracts (3/3 plans) — completed 2026-08-07
- [x] Phase 2: Camera Ingest & Live Preview (3/3 plans) — completed 2026-08-07
- [x] Phase 3: Fixed-Class Detection (2/2 plans) — completed 2026-08-07
- [x] Phase 4: Monocular Depth (2/2 plans) — completed 2026-08-08
- [x] Phase 5: Free-Space & Unified Stream (3/3 plans) — completed 2026-08-08
- [x] Phase 6: Developer Controls & Open-Vocab (2/2 plans) — completed 2026-08-08
- [x] Phase 7: Edge Profiles & Extension Stubs (3/3 plans) — completed 2026-08-08

Full phase detail: [milestones/v1.0-ROADMAP.md](milestones/v1.0-ROADMAP.md)  
Requirements archive: [milestones/v1.0-REQUIREMENTS.md](milestones/v1.0-REQUIREMENTS.md)  
Audit: [milestones/v1.0-MILESTONE-AUDIT.md](milestones/v1.0-MILESTONE-AUDIT.md)

</details>

<details>
<summary>✅ v0.2 Edge Runtime (Phases 8–12) — SHIPPED 2026-08-10</summary>

- [x] Phase 8: Backend Selection & Honesty (2/2 plans) — completed 2026-08-09
- [x] Phase 9: Live ORT Fixed-Class YOLO (2/2 plans) — completed 2026-08-09
- [x] Phase 10: Live TensorRT Fixed-Class YOLO (2/2 plans) — completed 2026-08-10
- [x] Phase 11: Sticky Fallback & Dual-Model Guardrails (2/2 plans) — completed 2026-08-10
- [x] Phase 12: Docs, CI & Packaging Polish (2/2 plans) — completed 2026-08-10

Full phase detail: [milestones/v0.2-ROADMAP.md](milestones/v0.2-ROADMAP.md)  
Requirements archive: [milestones/v0.2-REQUIREMENTS.md](milestones/v0.2-REQUIREMENTS.md)  
Audit: [milestones/v0.2-MILESTONE-AUDIT.md](milestones/v0.2-MILESTONE-AUDIT.md)

</details>

### 🚧 v0.3 Metric Depth Calibration UX (In Progress)

**Milestone Goal:** Makers can turn monocular relative depth into honest metric distances using a Live Preview calibration wizard (known distance / height) — without claiming vehicle-grade accuracy. Persist scale per camera, re-apply on serve, wire free-space meters only when calibrated.

**Constraints:** Zero new pip deps; spine freeze (DetectionLoop / FrameBus / ORT-TRT factory); no FSD claims; synthetic CI tests (no physical room).

- [ ] **Phase 13: Honesty Contracts & CalibrationState** - Promotion rules, validators, draft vs applied state model
- [ ] **Phase 14: Scale Math + DepthLoop Plug-in** - Fit/reject scale; apply post-worker pre-store
- [ ] **Phase 15: Wizard REST + Live Preview UI** - Sample/fit/apply/cancel API + static wizard panel
- [ ] **Phase 16: Free-Space Metric Path** - Meters only when calibrated; smoother reset
- [ ] **Phase 17: Persist & Re-apply on Serve** - Per-camera_id YAML; fingerprint refuse; clear
- [ ] **Phase 18: Docs + Synthetic CI Polish** - Operator guide; honesty docs; hardware-free tests

## Phase Details

### Phase 13: Honesty Contracts & CalibrationState
**Goal**: Depth honesty contracts and an in-process CalibrationState make `metric_calibrated` + meters reachable only when applied and valid — relative depth can never claim meters
**Depends on**: Phase 12 (v0.2 shipped; depth kind triad already exists)
**Requirements**: CAL-04, CAL-05
**Success Criteria** (what must be TRUE):
  1. Relative (and uncalibrated) depth products reject or never emit `unit="m"` on store / snapshot / `/v1` contracts (validators + tests)
  2. `CalibrationState` distinguishes draft vs applied; draft/staging alone does not report as calibrated
  3. Promotion policy is explicit: only applied + valid calibration yields the pair `depth_kind=metric_calibrated` and `unit="m"` together
  4. Calibration params include fingerprint fields (camera_id, resolution/size, depth mode/model) designed for later persist safety
**Plans**: TBD

### Phase 14: Scale Math + DepthLoop Plug-in
**Goal**: Makers (and tests) can fit a global monocular scale from ground-truth samples and have that scale transform depth maps on the single DepthLoop truth path
**Depends on**: Phase 13
**Requirements**: CAL-01, CAL-02, CAL-03
**Success Criteria** (what must be TRUE):
  1. A pure fit (numpy, no new deps) recovers scale from known-distance samples (known height supported when geometry is defined)
  2. Invalid fits are rejected (too few samples, residual too high, inconsistent signs) and never become applied scale
  3. When calibration is applied, DepthLoop transforms the depth map after the worker and before `PerceptionStore.set_depth` (store depth is scaled; free-space/UI/API inherit it)
  4. Synthetic unit tests prove fit / reject / apply without a physical room
**Plans**: TBD
**Research flag**: Needs `/gsd:plan-phase --research` (pure scale vs affine; residual gates; metric_estimated double-scale)

### Phase 15: Wizard REST + Live Preview UI
**Goal**: Makers can run a Live Preview calibration wizard that stages samples, previews a fit, and Apply/Cancel without inventing meters mid-draft
**Depends on**: Phase 14
**Requirements**: WIZ-01, WIZ-02, WIZ-03, WIZ-04, OPS-01
**Success Criteria** (what must be TRUE):
  1. Maker can open a Live Preview calibration wizard, collect samples, and stage a fit before commit
  2. Maker can Apply (commits calibrated state) or Cancel (leaves no calibrated state or meter claims)
  3. Wizard shows sample count, residual/status, and calibrated vs relative labeling clearly
  4. Draft/staging never claims `metric_calibrated` on the live perception stream until Apply
  5. Status / banner / Live Preview show whether calibration is active and base honesty (relative vs calibrated)
**Plans**: TBD
**UI hint**: yes

### Phase 16: Free-Space Metric Path
**Goal**: Free-space products use honest meters only when underlying depth is `metric_calibrated` — never ordinal percentile bands relabeled as meters
**Depends on**: Phase 14 (scaled depth maps exist); Phase 15 recommended for end-to-end UX feedback
**Requirements**: FS-01, FS-02, FS-03
**Success Criteria** (what must be TRUE):
  1. Free-space products emit `units="m"` only when depth kind is `metric_calibrated`
  2. Relative and `metric_estimated` free-space stay ordinal; unit labels never flip while still computing pure ordinal percentile nearness as if meters
  3. Free-space smoother/state resets on calibration apply and clear so stale ordinal/metric occupancy does not ghost
**Plans**: TBD
**Research flag**: Needs research (absolute meter band cuts vs keep ordinal nearness + separate distance fields)

### Phase 17: Persist & Re-apply on Serve
**Goal**: Valid calibration survives restarts for the matching camera/fingerprint; mismatches refuse auto-apply and stay honestly relative
**Depends on**: Phase 14 (apply path proven in-memory); Phase 15 (wizard can trigger persist)
**Requirements**: PER-01, PER-02, PER-03, PER-04
**Success Criteria** (what must be TRUE):
  1. Maker can save calibration keyed by `camera_id` (plus fingerprint fields needed for safety)
  2. On `sentry serve`, valid saved calibration re-applies for a matching camera/fingerprint without re-running the wizard
  3. Mismatched fingerprint (resolution, model/mode, camera_id) refuses auto-apply and keeps honest relative depth with a visible reason
  4. Maker can clear/invalidate stored calibration and return to uncalibrated relative depth
**Plans**: TBD

### Phase 18: Docs + Synthetic CI Polish
**Goal**: Operators have a guided non-FSD calibration flow in docs; CI covers fit/apply/honesty/persist with synthetic data only
**Depends on**: Phases 13–17 (wire behavior exists)
**Requirements**: OPS-02, OPS-03
**Success Criteria** (what must be TRUE):
  1. Operator docs describe the calibration wizard, persistence path, and honesty rules without vehicle-grade / FSD claims
  2. `perception-frame` / safety docs reflect free-space meters only when calibrated (no doc drift to “always ordinal”)
  3. Automated tests cover fit / apply / honesty / persist with synthetic frames (no physical room required in CI)
**Plans**: TBD

## Progress

| Phase | Milestone | Plans | Status | Completed |
|-------|-----------|-------|--------|-----------|
| 1–7 | v1.0 | 18/18 | Complete | 2026-08-09 |
| 8. Backend Selection & Honesty | v0.2 | 2/2 | Complete | 2026-08-09 |
| 9. Live ORT Fixed-Class YOLO | v0.2 | 2/2 | Complete | 2026-08-09 |
| 10. Live TensorRT Fixed-Class YOLO | v0.2 | 2/2 | Complete | 2026-08-10 |
| 11. Sticky Fallback & Dual-Model Guardrails | v0.2 | 2/2 | Complete | 2026-08-10 |
| 12. Docs, CI & Packaging Polish | v0.2 | 2/2 | Complete | 2026-08-10 |
| 13. Honesty Contracts & CalibrationState | v0.3 | 0/? | Not started | - |
| 14. Scale Math + DepthLoop Plug-in | v0.3 | 0/? | Not started | - |
| 15. Wizard REST + Live Preview UI | v0.3 | 0/? | Not started | - |
| 16. Free-Space Metric Path | v0.3 | 0/? | Not started | - |
| 17. Persist & Re-apply on Serve | v0.3 | 0/? | Not started | - |
| 18. Docs + Synthetic CI Polish | v0.3 | 0/? | Not started | - |

**Coverage:** v0.3 19/19 requirements mapped ✓

## Architecture Spine (reference)

```
Camera Sources → Frame Bus → Model Workers (depth || detection || open-vocab)
                      │              │
                      │              ▼
                      │       Spatial Post (free-space / obstacles)
                      │              │
                      ▼              ▼
               Perception State Store
                      │
          ┌───────────┴───────────┐
          ▼                       ▼
   Web Dev UI              Perception Stream API
   (overlays+controls)     (WS/REST → robots)
```

**v0.2 plug-in point:** `build_detection_worker(profile_runtime)` at serve construction — torch / ORT / TRT loaders for fixed-class YOLO. DetectionLoop, FrameBus, PerceptionStore, `/v1` frozen.

**v0.3 plug-in point:** `CalibrationState.apply_map` **after** `DepthAnythingWorker.process` and **before** `PerceptionStore.set_depth` inside DepthLoop. Free-space, MJPEG, assemble, and `/v1` inherit calibrated map + kind. DetectionLoop / FrameBus / ORT-TRT factory remain frozen.

```
DepthAnythingWorker.process → raw map + kind/unit
  → CalibrationState.apply_if_active → scale*map (+shift); kind=metric_calibrated; unit="m"
  → PerceptionStore.set_depth
  → FreeSpaceLoop (units="m" only when metric_calibrated)
```

## Stack Snapshot

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file/RTSP); synthetic for tests; Continuity uniqueID on macOS |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE; live ORT/TRT for fixed-class |
| Depth | Depth Anything V2 Small (Apache-2.0 default) — PyTorch/HF |
| Calibration | Pure NumPy scale/shift fit + CalibrationState (zero new deps) |
| Free-space | NumPy/OpenCV postprocess; meters only when `metric_calibrated` |
| Frontend | Static Live Preview (MJPEG + controls + calibration wizard) |
| Edge | Live ORT + live TRT for fixed-class YOLO; soft/strict fallback; Jetson-free CI |
| Persist | Per-`camera_id` YAML under cache/config root; fingerprint-gated auto-load |

## Phase Ordering Rationale (v0.3)

```
13 Honesty/state ──► 14 Scale apply (DepthLoop) ──► 15 Wizard + API
                              │
                              ▼
                       16 Free-space metric
                              │
                              ▼
                       17 Persist/re-apply ──► 18 Docs/CI
```

1. **Honesty first** — kind/unit/calib state before any product mutation  
2. **Math before chrome** — pure fit + DepthLoop apply before wizard labels  
3. **Depth apply before free-space meters** — free-space must consume real scaled maps  
4. **Persist late among features** — only persist a proven apply path  
5. **Docs finalize after wire behavior exists**
