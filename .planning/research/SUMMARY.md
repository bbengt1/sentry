# Project Research Summary

**Project:** Sentry AI — v0.4 Online Re-calibration (CAL-F03)  
**Domain:** Consent-once gated online refinement of an already-applied monocular metric scale  
**Researched:** 2026-08-15  
**Confidence:** HIGH

## Executive Summary

Sentry AI v0.4 is a **honesty-preserving online refine milestone**, not a new depth model and not a silent first-scale inventor. v0.3 already ships wizard Apply, persist `try_reapply`, DepthLoop `apply_map`, and `metric_calibrated` + meters only when applied+valid. This milestone **pulls CAL-F03 in** as **consent-once gated auto-commit**: after a maker has consented to metric scale (wizard Apply or matching persist re-apply), an **opt-in** (default off) online path can refine that scale without another Apply click — **without ever labeling draft, rejected, or fingerprint-mismatched depth as meters**.

**Recommended approach:** Add **zero new pip dependencies**. Reuse the shipped NumPy fit/reject, `CalibrationState` draft vs applied, `apply_params`, DepthLoop sole `apply_map`, fingerprint refuse, and free-space smoother reset. Online samples stay **draft only**. Auto-commit is allowed only when **online on AND already applied AND fit ok AND residual gate AND fingerprints_match**. Persist default: auto-commit is **session-only**. DetectionLoop, FrameBus, ORT/TRT factory, and `kind_for_mode` stay frozen.

**Key risks (kept as locks):** (1) **Silent unit lies** — draft / rejected / mismatch labeled as meters; (2) **Oscillating / free-space breakage** — per-frame scale thrash or label-only meters; (3) **Persistence mismatch** — auto-commit writing YAML or re-applying the wrong camera; (5) **Per-frame unguarded refit** — sticky scale required; throttle / N-sample window. Never claim vehicle-grade accuracy.

## Key Findings

### Recommended Stack

Full detail: [STACK.md](./STACK.md)

**Add zero third-party packages.** Online re-cal is product logic on the shipped FastAPI / Pydantic 2 / NumPy / OpenCV / PyYAML / static Live Preview / `CalibrationState` stack. No scipy, React, SLAM, Open3D, or new depth network.

**Core technologies:**
- **NumPy** — reuse v0.3 scale/shift fit + reject gates
- **`CalibrationState`** — draft vs applied; `apply()` / `apply_params()` / `apply_map()` / `clear_draft` / `clear_applied`
- **Pydantic 2** — existing `CalibrationParams` + additive online status (`extra=forbid`)
- **PyYAML persist** — unchanged path; auto-commit does **not** write YAML by default
- **FastAPI + static Live Preview** — opt-in toggle + status; no npm frontend
- **DepthLoop** — remains the sole `apply_map` site

**Critical constraint:** Do not add a `calibration` or `online` extra. Depth still needs existing `--extra depth`.

### Expected Features

Full detail: [FEATURES.md](./FEATURES.md)

**Must have (table stakes):**
- Online mode **opt-in, default off**
- First `metric_calibrated` still **Apply** or matching persist **`try_reapply`**
- Online sampler writes **draft only** (WIZ-04 holds)
- Reuse the same fit/reject; `ok=False` never becomes applied
- Gated auto-commit via **`apply_params`**
- Cancel = draft only; Clear = applied + YAML; **disable-online ≠ Clear**
- DepthLoop sole `apply_map`; smoother reset on auto-commit; persist refuse unchanged
- Status: `online_off` / `online_draft` / `auto_committed` / `rejected` distinct from `depth.kind` and persist status
- Docs + synthetic CI

**Should have (competitive):**
- Throttle / N-sample window readout
- Residual of last online fit vs last auto-commit
- Live Preview toggle that cannot invent first scale
- Headless REST enable after a consented applied scale

**Defer (later milestone):**
- Full chessboard intrinsic suite (CAL-F01)
- Required ArUco/AprilTag kit (CAL-F02)
- Stereo / multi-view (CAL-F04)
- ROS2 metric TF / multi-cam fusion / ORT-TRT depth (PLAT-F01–F03)
- Language/CLIP auto-scale
- Unguarded continuous refit without consent

### Architecture Approach

Full detail: [ARCHITECTURE.md](./ARCHITECTURE.md)

Treat online re-cal as a **cold-path sampler + gated `apply_params`**, not a second apply site and not a per-frame worker mutate.

```
[online off]  → no samples, no auto-commit (v0.3 behavior)
[online on, not yet applied] → samples may draft; NEVER auto-commit first scale
[online on, already applied] → N-sample / throttle window → same fit/reject
    → if ok + residual + fingerprints_match → apply_params (session-only)
    → DepthLoop apply_map (sole site) → smoother reset like Apply
    → else stay on last sticky applied scale; status=rejected or online_draft
```

**Frozen:** FrameBus, DetectionLoop, OpenVocabLoop, DepthAnythingWorker infer core, `kind_for_mode`, ORT/TRT factory, perception-only boundary, persist fingerprint refuse.

### Critical Pitfalls

Full detail: [PITFALLS.md](./PITFALLS.md)

1. **LOCK — Silent unit lies** — draft / rejected / fingerprint-mismatch never claim meters.
2. **LOCK — Free-space / oscillating scale** — do not flip free-space units without a real applied map; reset smoother on auto-commit; do not let scale thrash.
3. **LOCK — Persistence mismatch** — auto-commit is session-only; YAML only on explicit save / persist:true / documented opt-in; refuse still holds.
5. **LOCK — Per-frame unguarded refit** — sticky scale; throttle / N-sample window; no hot-path refit inside DepthLoop.

Do **not** delete these locks. They are why v0.3 deferred unguarded online re-cal and why v0.4 is gated.

## Implications for Roadmap

Phases continue from v0.3 (phases 13–18). Suggested **v0.4 phases 19–22**.

### Phase 19: Online consent & honesty state
**Rationale:** Same lesson as v0.2 backend_live and v0.3 draft vs applied — without an explicit online-off default and a “first scale still needs consent” gate, later sampling invents meters.
**Delivers:** Online mode flag default off; status enum `online_off | online_draft | auto_committed | rejected`; first-calibrated still Apply / `try_reapply`; Cancel/Clear unchanged; disable-online ≠ Clear.
**Addresses:** ONL-01, ONL-02, ONL-06.
**Avoids:** Pitfall #1 silent first scale; #5 disable-as-Clear.
**Research flag:** Standard — extend `CalibrationState` / status; no new math.

### Phase 20: Online sample + fit/reject
**Rationale:** Math before auto-commit. Sampling that writes applied state is a silent lie.
**Delivers:** Throttled / N-sample online collector into **draft only**; reuse v0.3 fit/reject; `ok=False` stays draft/rejected.
**Addresses:** ONL-03, ONL-04.
**Avoids:** Pitfall #5 per-frame unguarded refit; #1 draft-as-meters.
**Research flag:** Partial — lock window size / throttle defaults in plan-phase.

### Phase 21: Gated auto-commit + DepthLoop/status
**Rationale:** Auto-commit is the only new mutation. It must reuse `apply_params` and the existing DepthLoop `apply_map` so free-space/UI/`/v1` stay single-truth.
**Delivers:** Gate (online on AND already applied AND fit ok AND residual AND fingerprints_match) → `apply_params`; smoother reset; status `auto_committed` vs `rejected`.
**Addresses:** ONL-05, ONL-07.
**Avoids:** Pitfall #1/#2/#3; dual apply sites.
**Research flag:** Standard — reuse shipped apply path.

### Phase 22: Persist policy + docs/CI
**Rationale:** Wrong persistence is a permanent silent lie. Auto-commit must not become a YAML writer by default.
**Delivers:** Session-only auto-commit; YAML only on explicit save / persist:true / documented opt-in; operator docs; synthetic CI; persist refuse unchanged.
**Addresses:** ONL-08.
**Avoids:** Pitfall #3 persist mismatch; #6 FSD overclaim; #12 CI needs a room.
**Research flag:** Skip — policy + docs + tests.

### Phase Ordering Rationale

```
19 Consent/honesty ──▶ 20 Sample + fit/reject ──▶ 21 Gated auto-commit
                                                         │
                                                         ▼
                                                  22 Persist policy + docs/CI
```

- **Consent first** — online-off default and first-scale lock before any sampler
- **Draft before commit** — samples never promote
- **Auto-commit after proven fit** — reuse reject gates
- **Persist last** — only document/opt-in YAML after in-memory gate is honest

### Research Flags

| Phase | Flag | Why |
|-------|------|-----|
| **20** | Partial | N-sample window / throttle defaults; reuse fit as-is |
| **19, 21, 22** | Standard | State flag, `apply_params`, YAML policy, docs/CI |

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | **HIGH** | Code-verified zero new deps; `apply_params` / `apply_map` already shipped |
| Features | **HIGH** | CAL-F03 pulled in as gated auto-commit; anti-feature was *unguarded* online |
| Architecture | **HIGH** | DepthLoop remains sole apply site; online is control-plane |
| Pitfalls | **HIGH** | #1/#2/#3/#5 kept as locks from v0.3 research |

**Overall confidence:** **HIGH**

### Gaps to Address

- **Window / throttle defaults:** Phase 20 plan locks N and min interval; synthetic tests first.
- **What the online sampler measures:** Prefer the same known-distance / last-consent geometry already in draft samples — do not invent CLIP/language scale.
- **Status vs persist vs kind:** Three planes stay separate (`online_*`, persist `none|applied|ignored_mismatch|error`, `depth.kind`).
- **Whether Live Preview needs a new panel:** Toggle + status is enough; do not rebuild the wizard.

## Sources

### Primary (HIGH confidence)
- In-repo: `control/calibration_state.py` (`apply`, `apply_params`, `apply_map`, `clear_draft`, `clear_applied`); `spatial/calibration.py` fit/reject; `config/calibration_store.py`; DepthLoop hook; `docs/calibration.md`
- Research files: [STACK.md](./STACK.md), [FEATURES.md](./FEATURES.md), [ARCHITECTURE.md](./ARCHITECTURE.md), [PITFALLS.md](./PITFALLS.md)
- v0.3 archive: `milestones/v0.3-REQUIREMENTS.md` (CAL-F03 deferred → this milestone)

### Secondary (MEDIUM confidence)
- v0.3 PITFALLS #1/#2/#3/#5 — still the honesty locks
- DAV2 scale/shift fundamentals — online refine is the same affine, not a new model

## Opinionated defaults (roadmap lock)

1. **Zero new dependencies**
2. **First `metric_calibrated` still needs Apply or matching persist `try_reapply`** — online must not invent the first scale
3. **Online mode default off**
4. **Draft ≠ meters** (WIZ-04 holds until `apply()` / `apply_params` of a passed fit)
5. **Same fit-time reject gates; `ok=False` never becomes applied**
6. **Auto-commit only if:** online on AND already applied AND fit ok AND residual gate AND fingerprints_match — use `apply_params`; DepthLoop sole `apply_map`; reset free-space smoother on auto-commit like Apply
7. **No per-frame unguarded refit** — sticky scale; throttle / N-sample window
8. **Cancel = draft only; Clear = applied + YAML; disable-online ≠ Clear**
9. **Auto-commit is session-only** — YAML only on explicit save / persist:true / documented opt-in
10. **Status distinguishes** `online_off` / `online_draft` / `auto_committed` / `rejected` from `depth.kind` and persist status
11. **Freeze** DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; synthetic CI; no FSD

---
*Research completed: 2026-08-15*  
*Ready for roadmap: yes*
