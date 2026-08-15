# Feature Landscape: v0.4 Online Re-calibration

**Domain:** Consent-once gated online refinement of an already-applied monocular metric scale  
**Milestone:** Sentry AI v0.4 Online Re-calibration (CAL-F03)  
**Researched:** 2026-08-15  
**Confidence:** HIGH for Sentry contracts + honesty locks; MEDIUM for exact N-sample / throttle defaults (plan-phase)

## Scope Lock (do not expand)

| In scope | Out of scope this milestone |
|----------|----------------------------|
| Opt-in online refine **after** first consented scale | Inventing the first `metric_calibrated` without Apply / persist `try_reapply` |
| Draft-only online sampler + same fit/reject | Per-frame unguarded refit / oscillating scale |
| Gated auto-commit via `apply_params` | Auto-writing YAML on every auto-commit |
| Status `online_off` / `online_draft` / `auto_committed` / `rejected` | Chessboard / ArUco-required kit / stereo |
| Session-only persist default; docs + synthetic CI | ROS2 metric TF, multi-cam fusion, ORT/TRT depth |
| Disable-online without Clear | Language/CLIP auto-scale; FSD / vehicle-grade claims |

**Shipped baseline (v1.0 + v0.2 + v0.3):** Wizard Apply / Cancel / Clear; `CalibrationState.apply` + `apply_params` + `apply_map`; DepthLoop sole apply site; `metric_calibrated` + `unit="m"` only when applied+valid; free-space meters iff calibrated; YAML persist with fingerprint refuse; WIZ-04 draft never claims meters.

**Flip from v0.3 research:** v0.3 treated “continuous online re-cal without explicit Apply” as an **anti-feature** (CAL-F03). v0.4 **pulls CAL-F03 in** as **consent-once gated auto-commit** — not unguarded online, not silent first scale.

---

## How Online Re-cal Works (product reality)

Monocular scale is sticky after consent. Makers who already applied (or matching persist re-applied) a scale may want it to **nudge** as the scene/mount drifts — without clicking Apply every time, and without the stack inventing meters from a draft or a rejected fit.

```
1. Depth running; online default OFF (v0.3 behavior)
2. Maker consents once: wizard Apply  OR  matching persist try_reapply
   → first metric_calibrated exists
3. Maker opts in to online (UI/REST); status=online_draft while sampling
4. Sampler collects N samples on a throttle (not every frame)
5. Same v0.3 fit/reject runs on the window (draft only)
6. If online on AND already applied AND fit ok AND residual AND fingerprints_match
   → apply_params (session-only) → DepthLoop apply_map → smoother reset
   → status=auto_committed
7. Else keep last sticky applied scale; status=rejected or stay online_draft
8. Disable online ≠ Clear (applied + YAML remain)
9. Cancel still clears draft only; Clear still clears applied + YAML
```

**Opinionated Sentry choice:** Consent-once + gated `apply_params`. Do **not** silently promote the first scale. Do **not** refit on every DepthLoop frame.

---

## Expected Maker Behaviors

| Behavior | Implication for product |
|----------|-------------------------|
| Wants meters after one tape/wizard run | First scale still Apply / persist re-apply |
| Leaves the robot running after consent | Opt-in online can refine without another click |
| Turns online off to freeze scale | Disable-online must not Clear applied or YAML |
| Cancels a bad online window | Cancel = draft only; last applied stays |
| Remounts / swaps camera | Fingerprint refuse still blocks auto-commit and persist re-apply |
| Trusts badges more than docs | `online_*` status ≠ `depth.kind` ≠ persist status |
| Restarts serve | Auto-commit is session-only unless they explicitly saved |
| Uses synthetic/CI | All gates testable without a room |

---

## Table Stakes

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Online opt-in, default off** | Unguarded online was the v0.3 anti-feature | Low | Flag on `CalibrationState` / REST; boot off |
| **First calibrated still Apply or persist `try_reapply`** | Online must not invent the first scale | Low–Med | Gate auto-commit on `is_applied()` |
| **Online sampler draft only** | WIZ-04 holds | Med | Samples → draft; never `apply_map` from draft |
| **Reuse fit/reject** | Same honesty as wizard | Low | `ok=False` never applied |
| **Gated auto-commit via `apply_params`** | One commit API already exists | Med | All five conjuncts required |
| **Cancel / Clear unchanged** | Operators already learned v0.3 | Low | disable-online ≠ Clear |
| **DepthLoop sole `apply_map`** | Single truth | Low | No second scale site |
| **Smoother reset on auto-commit** | Same as Apply (FS-03) | Low | Reset like wizard Apply |
| **Persist refuse unchanged** | Wrong camera is a permanent lie | Low | fingerprints_match required |
| **Session-only auto-commit** | YAML is a restart lie if implicit | Med | save / persist:true / documented opt-in only |
| **Status four-way** | Distinguish online from kind/persist | Low–Med | `online_off` / `online_draft` / `auto_committed` / `rejected` |
| **Docs + synthetic CI** | No room / Jetson / CUDA | Med | Extend honesty matrix |

### Table-stakes quality bar (non-negotiable)

- Draft, rejected, and fingerprint-mismatched depth **never** claim `metric_calibrated` / meters.
- First scale is **never** invented by online mode.
- Auto-commit does **not** write YAML by default.
- No per-frame unguarded refit.
- Calibrated ≠ vehicle-grade. Perception-only. Synthetic-first tests.

---

## Differentiators

| Feature | Value Proposition | Complexity |
|---------|-------------------|------------|
| **Consent-once, then hands-off refine** | Makers get drift correction without Apply spam | Med |
| **Sticky scale + throttle window** | Robots see stable meters, not oscillating scale | Med |
| **Three-plane status honesty** | online / kind / persist never collapse into one badge | Low |
| **Disable without destroy** | Freeze scale without wiping YAML | Low |
| **Headless opt-in after persist re-apply** | Robots can enable online after a matching file load | Low–Med |

---

## Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Silent first scale from online samples** | Invents meters without consent | Require Apply or matching `try_reapply` first |
| **Online default on** | Surprises headless robots | Default off |
| **Draft / rejected labeled as meters** | FOUND-03 / WIZ-04 regression | WIZ-04 holds |
| **Per-frame unguarded refit** | Oscillating scale; pitfall #5 lock | Throttle / N-sample; sticky applied |
| **Auto-commit writes YAML by default** | Persist mismatch across restarts | Session-only; explicit save |
| **Disable-online = Clear** | Destroys consented scale | Flag only |
| **Second `apply_map` site** | Dual truth | DepthLoop only |
| **Language/CLIP auto-scale** | Ungrounded | Human-consented geometry only |
| **Chessboard / ArUco-required / stereo** | CAL-F01/F02/F04 | Deferred |
| **FSD / vehicle-grade claims** | Product thesis | Approximate hobby monocular |
| **New pip deps / React / SLAM** | Scope | Zero new deps |

The v0.3 anti-feature “continuous online auto-recalibration **without consent**” remains forbidden. What ships is the **consented, gated** form.

---

## Feature Dependencies

```
v0.3 CalibrationState (draft vs applied, apply / apply_params / apply_map)
    → online flag (default off)
    → online sampler (draft only, throttled)
    → same fit/reject
    → gated apply_params
    → DepthLoop apply_map (unchanged site)
    → FreeSpaceLoop smoother reset (same as Apply)
    → persist refuse unchanged; YAML not implicit

Does NOT depend on: ORT/TRT backends, open-vocab, ROS2, multi-cam fusion
Must NOT break: WIZ-04, relative honesty, Cancel/Clear, fingerprint refuse
```

---

## MVP Recommendation

**Prioritize (must ship):**

1. Online flag default off + status four-way  
2. First scale still Apply / persist `try_reapply`  
3. Draft-only sampler + reused fit/reject  
4. Gated `apply_params` auto-commit + DepthLoop / smoother  
5. Cancel/Clear/disable-online semantics  
6. Session-only persist + docs + synthetic CI  

**Defer:** chessboard, required ArUco, stereo, ROS2 TF, multi-cam fusion, ORT/TRT depth, CLIP auto-scale, per-frame refit.

---

## Phase Ordering Hints (for roadmap)

1. **Consent & honesty state** — flag, first-scale lock, Cancel/Clear/disable  
2. **Sample + fit/reject** — draft only, throttle / N-window  
3. **Gated auto-commit** — `apply_params` + DepthLoop + smoother + status  
4. **Persist policy + docs/CI** — session-only YAML; honesty matrix  

**Research flags:** Phase 20 window/throttle defaults need plan-phase lock. Other phases are standard extensions of shipped code.

---

## Sources

| Source | Use | Confidence |
|--------|-----|------------|
| PROJECT.md v0.4 goals + locked decisions | Scope lock | HIGH |
| `control/calibration_state.py` | apply / apply_params / apply_map | HIGH |
| `spatial/calibration.py` | fit/reject reuse | HIGH |
| `config/calibration_store.py` | persist refuse | HIGH |
| v0.3 FEATURES anti-feature “online without consent” | Flip to gated form | HIGH |
| v0.3 PITFALLS #1/#2/#3/#5 | Locks, not deletions | HIGH |

---
*Research for v0.4 Online Re-calibration — features only. Supersedes the v0.3 “defer online re-cal” landscape as the active feature file for roadmap input.*
