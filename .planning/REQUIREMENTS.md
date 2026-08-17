# Requirements: Sentry AI

**Defined:** 2026-08-15  
**Milestone:** v0.4 Online Re-calibration  
**Core value:** Reliable camera-only depth + obstacle awareness and object recognition that makers can run locally and plug into their robots — without proprietary sensors or cloud AI.

## v0.4 Requirements

Requirements for this milestone. Each maps to roadmap phases (19+).

### Online consent & honesty

- [ ] **ONL-01**: Online re-calibration is opt-in and **default off** (v0.3 Apply-only behavior until the maker enables online)
- [x] **ONL-02**: First `metric_calibrated` still requires explicit wizard Apply or matching persist `try_reapply` — online must not invent the first scale
- [ ] **ONL-06**: Cancel still clears draft only; Clear still clears applied + YAML; disable-online is not Clear (applied scale and YAML remain)

### Online sample + fit

- [ ] **ONL-03**: Online sampler writes **draft only** — WIZ-04 holds until `apply()` / `apply_params` of a passed fit (draft never claims meters)
- [ ] **ONL-04**: Online refine reuses the same v0.3 fit/reject gates; `ok=False` never becomes applied

### Gated auto-commit

- [ ] **ONL-05**: Auto-commit uses `apply_params` only when online is on AND already applied AND fit ok AND residual gate AND `fingerprints_match`
- [ ] **ONL-07**: DepthLoop remains the sole `apply_map` site; free-space smoother resets on auto-commit like Apply; persist fingerprint refuse is unchanged

### Operator surfaces

- [ ] **ONL-08**: Status distinguishes `online_off` / `online_draft` / `auto_committed` / `rejected` from `depth.kind` and persist status; operator docs and synthetic CI cover the online gates (no physical room; auto-commit is session-only unless explicit save / persist:true / documented opt-in)

## Future Requirements

Deferred beyond v0.4. Tracked but not in current roadmap.

### Calibration advanced

- **CAL-F01**: Full chessboard / photogrammetry intrinsic suite as primary path
- **CAL-F02**: Required ArUco/AprilTag marker kit workflow
- **CAL-F03**: Continuous online re-calibration without explicit Apply — **pulled into v0.4** as consent-once gated auto-commit (ONL-01..08). First scale still requires Apply / persist `try_reapply`.
- **CAL-F04**: Stereo or multi-view metric depth

### Platform

- **PLAT-F01**: Production ROS2 metric TF / frame package
- **PLAT-F02**: Multi-camera fusion with shared metric world frame
- **PLAT-F03**: Live ORT/TRT for depth models

## Out of Scope

| Feature | Reason |
|---------|--------|
| Vehicle-grade / FSD metric accuracy claims | Product thesis: maker monocular ≠ AV |
| Inventing the first scale from online samples | Consent lock: Apply or matching persist `try_reapply` first |
| Per-frame unguarded refit / oscillating scale | Sticky scale; throttle / N-sample window |
| Implicit YAML write on every auto-commit | Session-only default; persist mismatch lock |
| LiDAR-required calibration | Camera-only stack |
| New heavy deps (SLAM, Open3D, scipy, React) | Research: zero new packages; extend existing stack |
| Changing ORT/TRT fixed-class detection factory | Closed in v0.2; not this milestone |
| Motor control / safety interlocks from depth | Perception-only API boundary |
| Language/CLIP automatic scale without user GT | Honesty and anti-feature risk |
| Chessboard / required ArUco kit / stereo / ROS2 TF / multi-cam fusion / ORT-TRT depth | CAL-F01/F02/F04, PLAT-F01–F03 |

## Traceability

Which phases cover which requirements. Filled during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| ONL-01 | Phase 19 | Pending |
| ONL-02 | Phase 19 | Complete (19-01) |
| ONL-03 | Phase 20 | Pending |
| ONL-04 | Phase 20 | Pending |
| ONL-05 | Phase 21 | Pending |
| ONL-06 | Phase 19 | Pending |
| ONL-07 | Phase 21 | Pending |
| ONL-08 | Phase 22 | Pending |

**Coverage:**
- v0.4 requirements: 8 total
- Mapped to phases: 8/8 ✓
- Unmapped: 0

| Phase | Requirements | Count |
|-------|--------------|-------|
| 19 Online consent & honesty state | ONL-01, ONL-02, ONL-06 | 3 |
| 20 Online sample + fit/reject | ONL-03, ONL-04 | 2 |
| 21 Gated auto-commit + DepthLoop/status | ONL-05, ONL-07 | 2 |
| 22 Persist policy + docs/CI | ONL-08 | 1 |

---
*Requirements defined: 2026-08-15*  
*Last updated: 2026-08-17 after 19-01 (ONL-02 complete; ONL-01 flag half shipped)*
