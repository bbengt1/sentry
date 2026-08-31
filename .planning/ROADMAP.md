# Roadmap: Sentry AI

## Milestones

- ✅ **v1.0 Camera-only perception MVP** — Phases 1–7 (shipped 2026-08-09)
- ✅ **v0.2 Edge Runtime** — Phases 8–12 (shipped 2026-08-10)
- ✅ **v0.3 Metric Depth Calibration UX** — Phases 13–18 (shipped 2026-08-14)
- 🚧 **v0.4 Online Re-calibration** — Phases 19–22 (in progress)

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

<details>
<summary>✅ v0.3 Metric Depth Calibration UX (Phases 13–18) — SHIPPED 2026-08-14</summary>

- [x] Phase 13: Honesty Contracts & CalibrationState (2/2 plans) — completed 2026-08-11
- [x] Phase 14: Scale Math + DepthLoop Plug-in (2/2 plans) — completed 2026-08-13
- [x] Phase 15: Wizard REST + Live Preview UI (2/2 plans) — completed 2026-08-13
- [x] Phase 16: Free-Space Metric Path (2/2 plans) — completed 2026-08-13
- [x] Phase 17: Persist & Re-apply on Serve (2/2 plans) — completed 2026-08-14
- [x] Phase 18: Docs + Synthetic CI Polish (2/2 plans) — completed 2026-08-14

Full phase detail: [milestones/v0.3-ROADMAP.md](milestones/v0.3-ROADMAP.md)  
Requirements archive: [milestones/v0.3-REQUIREMENTS.md](milestones/v0.3-REQUIREMENTS.md)  
Audit: [milestones/v0.3-MILESTONE-AUDIT.md](milestones/v0.3-MILESTONE-AUDIT.md)

</details>

### 🚧 v0.4 Online Re-calibration (In Progress)

**Milestone Goal:** After a maker has consented to metric scale (wizard Apply or matching persist re-apply), Sentry can continuously refine that scale online without another Apply click — without ever labeling draft, rejected, or fingerprint-mismatched depth as meters.

**Constraints:** Online default off; first `metric_calibrated` still Apply or persist `try_reapply`; draft ≠ meters (WIZ-04); same fit/reject (`ok=False` never applied); auto-commit only if online on AND already applied AND fit ok AND residual gate AND `fingerprints_match` via `apply_params`; DepthLoop sole `apply_map`; smoother reset on auto-commit; sticky scale (throttle / N-sample, no per-frame unguarded refit); Cancel = draft only; Clear = applied + YAML; disable-online ≠ Clear; auto-commit session-only (YAML only on explicit save / persist:true / documented opt-in); status `online_off` / `online_draft` / `auto_committed` / `rejected` separate from `depth.kind` and persist; zero new deps; freeze DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; synthetic CI; no FSD.

- [x] **Phase 19: Online consent & honesty state** - Opt-in default off; first scale still Apply / persist re-apply; Cancel/Clear/disable-online semantics — **complete (19-01, 19-02)**
- [ ] **Phase 20: Online sample + fit/reject** - Throttled draft-only sampler; reuse v0.3 fit/reject
- [ ] **Phase 21: Gated auto-commit + DepthLoop/status** - Five-conjunct `apply_params`; sole `apply_map`; smoother reset; online status
- [ ] **Phase 22: Persist policy + docs/CI** - Session-only auto-commit; operator docs; synthetic honesty matrix

## Phase Details

### Phase 19: Online consent & honesty state
**Goal**: Online mode exists as an opt-in default-off flag with honest status, and cannot invent the first metric scale; Cancel/Clear stay v0.3; disable-online is not Clear
**Depends on**: Phase 18 (v0.3 shipped; draft vs applied, Apply / `try_reapply`, Cancel/Clear already exist)
**Requirements**: ONL-01, ONL-02, ONL-06
**Success Criteria** (what must be TRUE):
  1. Online re-calibration is opt-in and default off (serve / state boot with online disabled)
  2. First `metric_calibrated` still requires wizard Apply or matching persist `try_reapply` — enabling online while unapplied does not auto-commit a scale
  3. Cancel still clears draft only; Clear still clears applied + YAML
  4. Disable-online does not clear applied params or delete the YAML file
  5. Status can represent `online_off` (and is distinct from `depth.kind` and persist status)
**Plans**: [19-01](phases/19-online-consent-honesty-state/19-01-PLAN.md), [19-02](phases/19-online-consent-honesty-state/19-02-PLAN.md) — complete

### Phase 20: Online sample + fit/reject
**Goal**: An online sampler can collect a throttled N-sample window into draft only and run the same v0.3 fit/reject without promoting meters
**Depends on**: Phase 19
**Requirements**: ONL-03, ONL-04
**Success Criteria** (what must be TRUE):
  1. Online samples write draft only — WIZ-04 holds; draft never claims `metric_calibrated` / meters
  2. Fit/reject is the same v0.3 gates; `ok=False` never becomes applied
  3. No per-frame unguarded refit on the DepthLoop hot path — sticky last applied scale; throttle / N-sample window
  4. Synthetic unit tests cover draft-only sampling and reject-stays-applied without a physical room
**Plans**: TBD
**Research flag**: Partial — lock N-sample / throttle defaults at plan-phase

### Phase 21: Gated auto-commit + DepthLoop/status
**Goal**: A passed online fit can auto-commit via `apply_params` only when all gates hold; DepthLoop remains the sole map apply site; free-space smoother resets; status distinguishes auto-commit from reject
**Depends on**: Phase 20
**Requirements**: ONL-05, ONL-07
**Success Criteria** (what must be TRUE):
  1. Auto-commit calls `apply_params` only when online on AND already applied AND fit ok AND residual gate AND `fingerprints_match`
  2. Failed gates leave the last sticky applied scale unchanged; `ok=False` / mismatch never become applied
  3. DepthLoop remains the sole `apply_map` site (no second transform in sampler / API / UI)
  4. Free-space smoother resets on auto-commit like wizard Apply
  5. Persist fingerprint refuse is unchanged (mismatch cannot auto-commit)
  6. Status distinguishes `online_draft` / `auto_committed` / `rejected` from `depth.kind` and persist status
**Plans**: TBD

### Phase 22: Persist policy + docs/CI
**Goal**: Auto-commit stays session-only unless the maker explicitly persists; operators have non-FSD docs; CI covers the online gate matrix with synthetic data only
**Depends on**: Phase 21
**Requirements**: ONL-08
**Success Criteria** (what must be TRUE):
  1. Auto-commit does not write YAML by default (session-only); YAML only on explicit save / persist:true / documented opt-in
  2. Operator docs describe online opt-in, first-scale consent, Cancel/Clear/disable-online, and honesty rules without vehicle-grade / FSD claims
  3. Status docs keep `online_*` separate from `depth.kind` and persist `none|applied|ignored_mismatch|error`
  4. Automated tests cover the online gate matrix (off / not-applied / reject / mismatch / success) with synthetic frames (no physical room; default GHA stays Jetson-free)
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
| 13–18 | v0.3 | 12/12 | Complete | 2026-08-14 |
| 19. Online consent & honesty state | v0.4 | 2/2 | Complete | 2026-08-30 |
| 20. Online sample + fit/reject | v0.4 | 0/? | Not started | - |
| 21. Gated auto-commit + DepthLoop/status | v0.4 | 0/? | Not started | - |
| 22. Persist policy + docs/CI | v0.4 | 0/? | Not started | - |

**Coverage:** v0.4 8/8 requirements mapped ✓

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
          ┌───────────┬───────────┐
          ▼                       ▼
   Web Dev UI              Perception Stream API
   (overlays+controls)     (WS/REST → robots)
```

**v0.2 plug-in point:** `build_detection_worker(profile_runtime)` at serve construction — torch / ORT / TRT loaders for fixed-class YOLO. DetectionLoop, FrameBus, PerceptionStore, `/v1` frozen.

**v0.3 plug-in point:** `CalibrationState.apply_map` **after** `DepthAnythingWorker.process` and **before** `PerceptionStore.set_depth` inside DepthLoop. Free-space, MJPEG, assemble, and `/v1` inherit calibrated map + kind. DetectionLoop / FrameBus / ORT-TRT factory remain frozen.

**v0.4 plug-in point:** Throttled online sampler + gated `apply_params` on the **control plane** (not a second `apply_map`). DepthLoop remains the sole map apply site. Auto-commit session-only by default.

```
DepthAnythingWorker.process → raw map + kind/unit
  → CalibrationState.apply_if_active → scale*map (+shift); kind=metric_calibrated; unit="m"
  → PerceptionStore.set_depth
  → FreeSpaceLoop (units="m" only when metric_calibrated)

Online (default off): draft samples → same fit/reject → apply_params only if
  online on AND already applied AND fit ok AND residual AND fingerprints_match
```

## Stack Snapshot

| Layer | Choice |
|-------|--------|
| Backend | Python 3.11 + FastAPI + Pydantic 2 |
| Capture | OpenCV (USB/file/RTSP); synthetic for tests; Continuity uniqueID on macOS |
| Detection | YOLO26 (Ultralytics); open-vocab YOLOE; live ORT/TRT for fixed-class |
| Depth | Depth Anything V2 Small (Apache-2.0 default) — PyTorch/HF |
| Calibration | Pure NumPy scale/shift fit + CalibrationState (zero new deps) |
| Online re-cal | Opt-in flag + draft sampler + gated `apply_params` (session-only) |
| Free-space | NumPy/OpenCV postprocess; meters only when `metric_calibrated` |
| Frontend | Static Live Preview (MJPEG + controls + calibration wizard + online toggle) |
| Edge | Live ORT + live TRT for fixed-class YOLO; soft/strict fallback; Jetson-free CI |
| Persist | Per-`camera_id` YAML under cache/config root; fingerprint-gated auto-load; auto-commit does not write YAML by default |

## Phase Ordering Rationale (v0.4)

```
19 Consent/honesty ──▶ 20 Sample + fit/reject ──▶ 21 Gated auto-commit
                                                         │
                                                         ▼
                                                  22 Persist policy + docs/CI
```

1. **Consent first** — online-off default and first-scale lock before any sampler
2. **Draft before commit** — samples never promote meters
3. **Auto-commit after proven fit** — reuse reject gates + `apply_params`
4. **Persist last** — session-only YAML policy after the in-memory gate is honest
