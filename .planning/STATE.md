---
gsd_state_version: 1.0
milestone: v0.3
milestone_name: Metric Depth Calibration UX
status: executing
stopped_at: 17-01 YAML store + fingerprint refuse done; next execute 17-02
last_updated: "2026-08-14T08:35:00.000Z"
last_activity: 2026-08-14
progress:
  total_phases: 6
  completed_phases: 4
  total_plans: 10
  completed_plans: 9
  percent: 75
---

# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-08-11)

**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots - without proprietary sensors or cloud AI.  
**Current focus:** Phase 17-01 complete (YAML store + fingerprint refuse). Next execute 17-02 serve re-apply + REST save/clear + status.

## Current Position

Phase: 17 (Persist & Re-apply on Serve) - 17-01 executed  
Plan: 1 of 2 (17-01 done; next 17-02)  
Status: Phase 16 complete on `main`. 17-01 on `feat/17-01-calibration-store`  
Last activity: 2026-08-14

Progress: [############] 75% of v0.3 executed plans (13-16 complete; 17-01 done; next 17-02)

## Performance Metrics

**Velocity:**

- Total plans completed (v0.3): 9 (Phase 13 + Phase 14 + Phase 15 + Phase 16 + 17-01)
- v1.0 + v0.2 history: 28 plans shipped prior milestones

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| Phase 13 P01 | 3min | 2 tasks | 7 files |
| Phase 13 P02 | 2min | 2 tasks | 5 files |
| Phase 14 P01 | 8min | 1 task | 5 files |
| Phase 14 P02 | 25min | 2 tasks | 7 files |
| Phase 15 P01 | 40min | 2 tasks | 16 files |
| Phase 15 P02 | 35min | 1 task | 4 files |
| Phase 16 P01 | 25min | 1 task | 3 files |
| Phase 16 P02 | 20min | 1 task | 17 files |
| Phase 17 P01 | 25min | 1 task | 8 files |

*Updated after each plan completion*

## Accumulated Context

### Decisions

See PROJECT.md Key Decisions (v0.2 factory / ORT / TRT / soft-strict / torch-only depth-OV).

v0.3 roadmap locks (from research):

- Zero new pip dependencies (numpy fit only)
- Post-process scale in DepthLoop (not worker, not free-space, not UI)
- Primary GT = known distance; height feeds same fitter with documented assumptions
- metric_calibrated + unit="m" only when applied and valid
- Free-space meters only after real metric path (not label-only)
- Persist per camera_id with fingerprint refuse
- Static wizard + REST - no new frontend stack, no FSD claims
- [Phase 13]: relative_depth_forbids_unit delegates to assert_depth_kind_unit for single matrix
- [Phase 13]: FreeSpacePayload allows metric_calibrated + ordinal until Phase 16
- [Phase 13]: kind_for_mode production mapping left unchanged; never-calibrated is test-only
- [Phase 13]: Clear draft on successful apply (wizard Apply semantics)
- [Phase 13]: get_applied_params() exposed for Phase 14 consumers
- [Phase 13]: CalibrationSnapshot includes scale/method/fingerprint when applied
- [Phase 13]: manual_scale skips sample_count floor; other methods require >= 1
- [Phase 14]: Fit default = scale-only median of D_i/d_i
- [Phase 14]: Optional affine lstsq when N>=2; store scale+offset
- [Phase 14]: Apply map' = scale*map + offset (not inverse-depth)
- [Phase 14]: No polarity flip; reject non-positive observations
- [Phase 14]: residual_rms reject if > max(0.15*median(D), 0.05); absurd scale outside (1e-4, 1e4); fit-time reject before draft
- [Phase 14]: Same apply for relative and metric_estimated; fingerprint depth_mode+model_id; no undo of metric prior
- [Phase 14]: Core fitter = (observed_raw, known_meters) pairs; height helper optional/minimal
- [Phase 14]: Module spatial/calibration.py; state apply_map in control/calibration_state.py
- [Phase 14]: Zero new deps; freeze DetectionLoop/FrameBus/ORT-TRT; synthetic tests; no wizard/YAML/free-space meters; CoW float32; lock in apply_map
- [Phase 14-01]: CalibrationFitResult lives in spatial/calibration.py (not schemas); lazy spatial exports
- [Phase 14-02]: apply_map CoW float32 under lock; DepthLoop sole apply site; CLI injects CalibrationState; error paths do not invent calibrated meters
- [Phase 15]: Cancel = clear_draft only; explicit Clear = clear_applied
- [Phase 15]: Sample only when inactive (409 if applied)
- [Phase 15]: Same CalibrationState instance for DepthLoop and create_app
- [Phase 15]: REST in-memory only (no YAML); extra=forbid; 503 if state missing
- [Phase 15]: UI never locally claims metric_calibrated; preview numbers from draft until Apply
- [Phase 15-01]: CalibrationSample + public draft sample APIs; freeze pin on app.state
- [Phase 15-01]: CLI hoists CalibrationState for DepthLoop AND create_app
- [Phase 15-01]: REST in-memory freeze/sample/compute/apply/cancel/clear; status additive
- [Phase 15-02]: Static #calibration-wizard on index.html; click-to-sample via naturalWidth/Height
- [Phase 15-02]: Footer #metric-calibration from status calibration_active/scale/method/sample_count
- [Phase 15-02]: Draft numbers labeled draft (not live); badge still status depth_kind only
- [Phase 16]: Calibrated units="m" iff absolute meter cuts (1.5 m / 3.0 m) on scaled depth; never label-only 0.72/0.45 flip
- [Phase 16]: Relative + metric_estimated stay ordinal (percentile + auto polarity)
- [Phase 16]: nearness_* remain 0..1; optional distance_m on cues only when calibrated (mean blob depth)
- [Phase 16]: Pin higher_is_farther on calibrated path; never min-max normalize meters
- [Phase 16]: OccupancySmoother.reset on kind apply/clear; FreeSpaceLoop.reset_smoother; loop detects kind change (no CalibrationState listeners)
- [Phase 16]: assemble METRIC_CALIBRATED -> "m"; else "ordinal"; calibrated must emit "m" (Phase 13 grace ends)
- [Phase 16]: Consume DepthLoop scaled map + kind - never re-scale
- [Phase 16]: Split 16-01 pure compute honesty / 16-02 loop+wire+reset+distance_m
- [Phase 16-01]: compute_free_space metric branch shipped; wire still allows calibrated+ordinal until 16-02 assemble flip
- [Phase 16-02]: FreeSpaceLoop consumes kind+map, never re-scales; store units; assemble helper flip; validator calibrated must be "m"
- [Phase 16-02]: reset_smoother on kind != _last_kind; belt-and-suspenders POST apply/clear (not cancel)
- [Phase 16-02]: ObstacleCue.distance_m optional additive (mean finite blob depth) when calibrated
- [Phase 16]: Complete on main (16-01 + 16-02 merged 2026-08-13)
- [Phase 17]: Path $SENTRY_MODEL_CACHE / default_cache_root() / calibration/{safe_id}.yaml; YAML; no platformdirs
- [Phase 17]: Optional SENTRY_CALIBRATION_DIR + --calibration-file; yaml.safe_load only; Pydantic CalibrationParams; atomic temp+rename; no depth maps
- [Phase 17]: Key by sanitized camera_id stem (reject ..); not profile YAML
- [Phase 17]: Hard-refuse camera_id, depth_mode, model_id; width/height when both sides non-None; no uniqueID/RTSP fields this phase
- [Phase 17]: Serve may match camera_id+mode+model when live sizes still None; later W×H mismatch refuse/clear
- [Phase 17]: Auto-apply only when file present AND fingerprints_match; corrupt/missing soft inactive
- [Phase 17]: apply_params for load (no fake wizard samples); persist via POST save and optional persist:true on apply
- [Phase 17]: Clear deletes the file; Cancel stays draft-only
- [Phase 17]: Additive persist status none|applied|ignored_mismatch|error, separate from depth.kind; serve banner
- [Phase 17]: DepthLoop sole map apply site; I/O in config/calibration_store.py; try_reapply in control/calibration_persist.py
- [Phase 17]: Split 17-01 store+fingerprint+apply_params / 17-02 serve+REST+status+late size
- [Phase 17-01]: YAML store + fingerprints_match + apply_params + try_reapply shipped (PER-01, PER-03)
- [Phase 17-01]: No CLI/REST/DepthLoop/wizard HTML wire (17-02)

### Pending Todos

- Execute Phase 17-02 serve re-apply + REST save/clear + status (PER-02, PER-04)
- Then Phase 18 docs + synthetic CI polish

### Blockers/Concerns

- Persist path locked: `$SENTRY_MODEL_CACHE/calibration/*.yaml` (STACK) — not ARCHITECTURE `~/.config` JSON / platformdirs

## Deferred Items

From v1.0 / v0.2 close (carried forward; non-blocking for v0.3):

| Category | Item | Status |
|----------|------|--------|
| verification_gap | Phase 02-04 human_needed UAT | acknowledged |
| integration | Free-space after depth disable; /v1 bus metrics; YOLOE registry | deferred polish |
| nyquist | Most VALIDATION.md still nyquist_compliant false | docs debt |
| hardware | ORT/TRT E2E remains operator checklist | v0.2 residual |

See also: `milestones/v1.0-MILESTONE-AUDIT.md`, `milestones/v0.2-MILESTONE-AUDIT.md`.

## Session Continuity

Last session: 2026-08-14T08:35:00.000Z
Stopped at: 17-01 YAML store + fingerprint refuse executed
Resume file: None
Next: Execute Phase 17-02 serve re-apply + REST save/clear + status per ROADMAP
