# Domain Pitfalls: Online Re-calibration

**Domain:** Adding **consent-once gated online refine** on top of an already-honest monocular metric scale  
**Project:** Sentry AI — milestone **v0.4 Online Re-calibration (CAL-F03)**  
**Researched:** 2026-08-15  
**Overall confidence:** HIGH for honesty / persist / unguarded-refit locks (verified against v0.3 code + contracts)

**Product thesis (non-negotiable):** camera-only maker perception — **not FSD**. Online refine yields **honest approximate meters**, never vehicle-grade clearance.

**v0.3 honesty baseline (must not regress):**
- `metric_calibrated` + `unit="m"` only when applied+valid
- Draft never claims meters (WIZ-04)
- Free-space `units="m"` iff calibrated (absolute cuts, not label-only)
- Persist fingerprint refuse; Cancel = draft; Clear = applied + YAML

**Numbered locks below are inherited from v0.3 research. Do not delete them.** v0.3 deferred unguarded online re-cal *because* of #1, #2, #3, and #5. v0.4 ships the gated form and **keeps these as locks**.

---

## Critical Pitfalls

### 1. LOCK — Silent unit lies (relative / draft / rejected labeled as meters)

**What goes wrong:**  
UI, `/v1`, or free-space says meters while the map is still relative, **draft**, **rejected**, or **fingerprint-mismatched**. Online mode makes this worse if a sampler “looks calibrated enough” and the stack promotes kind without `apply()` / `apply_params` of a passed fit.

**Why it happens:**
- Temptation to treat online samples as already-metric
- Collapsing `online_status` into `depth.kind`
- Inventing the **first** scale from online (no prior Apply / `try_reapply`)
- `ok=False` fit still writing applied params

**Consequences:** Unsafe control-loop assumptions; FOUND-03 / WIZ-04 regression; impossible field debugging.

**Prevention (v0.4 lock):**
- First `metric_calibrated` still needs explicit Apply or matching persist `try_reapply`
- Online sampler is **draft only**
- `ok=False` never becomes applied
- `unit="m"` only with applied+valid kind promotion (existing helper)
- Status `online_draft` / `rejected` must not paint meters

**Detection:** Snapshot `depth.kind=relative` with `unit="m"`; online_draft with `metric_calibrated` invented this session without Apply/`try_reapply`; rejected fit changes kind.

**Phase ownership:** **Phase 19** (consent/honesty) + **Phase 21** (auto-commit gate).  
**Confidence:** HIGH

---

### 2. LOCK — Free-space breakage / oscillating scale

**What goes wrong:**  
Auto-commit flips free-space labels or scale every few frames. Smoother ghosts pre-commit occupancy. Operators see “meters” jump. Robots oscillate near-field bands.

**Why it happens:**
- Per-frame refit (also pitfall #5)
- Auto-commit without smoother reset (FS-03 was for Apply/Clear only)
- Label-only unit flip without a new applied map

**Prevention (v0.4 lock):**
- Sticky applied scale; throttle / N-sample window
- Reset `OccupancySmoother` on auto-commit **like Apply**
- Free-space meters still iff `metric_calibrated` on a real scaled map
- Rejected fits leave last applied map untouched

**Detection:** Band fractions thrash while online; `units="m"` with unchanged map after a rejected fit; smoother ghost after auto-commit.

**Phase ownership:** **Phase 20** (window) + **Phase 21** (smoother reset).  
**Confidence:** HIGH

---

### 3. LOCK — Persistence mismatch (wrong camera, implicit YAML, silent re-apply)

**What goes wrong:**  
Auto-commit writes YAML every time; a later serve reloads a scale fit for another mount/resolution/model. Or disable-online is implemented as Clear and the file disappears. Or mismatch still auto-commits because “online is on.”

**Why it happens:**
- Treating auto-commit like persist:true Apply
- Reusing persist `applied` as online success
- Skipping `fingerprints_match` on the auto-commit gate

**Prevention (v0.4 lock):**
- Auto-commit is **session-only** by default
- YAML only on explicit save / persist:true / documented opt-in
- `fingerprints_match` is a required auto-commit conjunct
- Persist refuse unchanged
- Disable-online ≠ Clear (no file delete)

**Detection:** Serve logs calibration applied after camera/resolution/model change with no new wizard; YAML mtime changes on every auto-commit; Clear-shaped disable.

**Phase ownership:** **Phase 21** (gate includes fingerprints) + **Phase 22** (persist policy).  
**Confidence:** HIGH

---

### 4. Scale math lies (wrong target, double-scale, bbox misuse)

**What goes wrong:**  
Online window samples the **already-scaled** map and fits again (double-scale). Or it invents geometry the wizard never consented to.

**Prevention:** Sample **pre-apply raw** (or equivalent documented space); reuse v0.3 fit/reject; do not add CLIP/language scale. Residual reject stays closed.

**Phase ownership:** **Phase 20**.  
**Confidence:** HIGH for double-scale risk; MEDIUM for exact window recipe.

---

### 5. LOCK — Per-frame unguarded refit (wizard UX thrash / sticky-scale breach)

**What goes wrong:**  
Online “helpfully” refits every DepthLoop frame. Scale oscillates. Cancel does not restore draft-only. Disable-online clears applied. Preview shows meters while `/v1` does not (or reverse).

**Why it happens:**
- Fit on the hot path
- No N-sample / throttle window
- Auto-commit without the five conjuncts
- Disable implemented as `clear_applied`

**Prevention (v0.4 lock):**
- **No per-frame unguarded refit** — sticky scale after commit
- Throttle / N-sample window on the control plane
- Cancel = draft only; Clear = applied + YAML; disable-online ≠ Clear
- Auto-commit only: online on AND already applied AND fit ok AND residual AND fingerprints_match
- UI never locally claims `auto_committed` or meters

**Detection:** Scale changes every frame while online; Cancel wipes applied; disable deletes YAML; footer kind ≠ `/v1` kind.

**Phase ownership:** **Phase 19** (Cancel/Clear/disable) + **Phase 20** (no hot-path fit) + **Phase 21** (gate).  
**Confidence:** HIGH

---

### 6. Accuracy / FSD overclaim (product thesis breach)

**What goes wrong:**  
Docs or UI imply “online re-cal = always-accurate meters / autonomous-ready.”

**Prevention:** Keep safety copy; “approximate hobby monocular”; no `safe_to_drive`; residual/status visible; no FSD language.

**Phase ownership:** **Phase 22** docs + UI copy in 19/21.  
**Confidence:** HIGH

---

## Moderate Pitfalls

### 7. Enabling online before first consent

**What goes wrong:** Toggle on with no applied scale silently becomes first meters.

**Prevention:** Enable while unapplied → 409 or no-op; stay `online_off`; never `apply_params`.

**Phase ownership:** Phase 19.

### 8. Double-scaling and kind confusion

**What goes wrong:** Online samples calibrated maps and multiplies scale again.

**Prevention:** Sample raw / pre-apply space; store `depth_mode` + `model_id`; tests for relative→calibrated and estimated→calibrated refine.

**Phase ownership:** Phase 20.

### 9. Thread / product races on auto-commit

**What goes wrong:** Sampler writes applied while DepthLoop reads half-updated params.

**Prevention:** Existing `CalibrationState` lock; `apply_params` is already atomic; `apply_map` copies params then computes outside the lock (shipped).

**Phase ownership:** Phase 21.

### 10. Collapsing three status planes

**What goes wrong:** One badge for kind + persist + online.

**Prevention:** `online_*` additive and separate from `depth.kind` and persist `none|applied|ignored_mismatch|error`.

**Phase ownership:** Phase 19 + 21 + 22.

### 11. Intrinsics / stereo / ArUco scope creep

**Prevention:** CAL-F01/F02/F04 stay future. v0.4 = gated refine of the v0.3 affine.

### 12. CI requires a real room

**Prevention:** Synthetic gate matrix; no room / Jetson / CUDA / `--extra depth` required in default GHA.

---

## Phase ownership map (v0.4)

| Phase | Name | Prevents (pitfall #) | Delivers |
|-------|------|----------------------|----------|
| **19** | **Online consent & honesty state** | #1 first-scale lie; #5 Cancel/Clear/disable; #7 enable-before-consent | Flag default off; status enum; first scale still Apply/`try_reapply` |
| **20** | **Online sample + fit/reject** | #4/#8 double-scale; #5 unguarded refit | Draft-only sampler; reuse fit/reject; throttle / N-window |
| **21** | **Gated auto-commit + DepthLoop/status** | #1/#2/#3/#5/#9 | Five-conjunct `apply_params`; smoother reset; status |
| **22** | **Persist policy + docs/CI** | #3 implicit YAML; #6 FSD; #12 room CI | Session-only persist; docs; synthetic matrix |

```
19 Consent/honesty ──▶ 20 Sample + fit ──▶ 21 Gated auto-commit ──▶ 22 Persist/docs/CI
```

---

## Anti-patterns checklist (PR review)

- [ ] First `metric_calibrated` invented by online (no Apply / `try_reapply`)
- [ ] Draft / rejected / mismatch labeled as meters
- [ ] `ok=False` becomes applied
- [ ] Per-frame unguarded refit on DepthLoop
- [ ] Auto-commit writes YAML by default
- [ ] Auto-commit without `fingerprints_match`
- [ ] Disable-online = Clear (wipes applied or YAML)
- [ ] Cancel clears applied
- [ ] Second `apply_map` site
- [ ] Online status collapsed into `depth.kind` or persist status
- [ ] FSD / vehicle-grade / “precise meters” copy
- [ ] Tests that require a physical room
- [ ] New pip deps / React / SLAM / ORT-TRT depth

---

## Question → pitfall → phase

| Question | Answer | Prevent in |
|----------|--------|------------|
| Can online invent the first scale? | No | **19** |
| Silent meters from draft/reject/mismatch? | Highest severity — lock #1 | **19 + 21** |
| Oscillating scale / free-space thrash? | Lock #2 + #5 | **20 + 21** |
| Implicit YAML / wrong-camera persist? | Lock #3 | **21 + 22** |
| Per-frame unguarded refit? | Lock #5 | **20 + 21** |

---

## Sources

| Source | Confidence | Use |
|--------|------------|-----|
| PROJECT.md v0.4 locked decisions | HIGH | Gate conjuncts |
| v0.3 PITFALLS #1/#2/#3/#5 | HIGH | **Locks — do not delete** |
| `control/calibration_state.py` | HIGH | apply / apply_params / apply_map |
| `spatial/calibration.py` | HIGH | fit/reject |
| `config/calibration_store.py` | HIGH | fingerprint refuse |
| `docs/calibration.md` + safety-and-privacy.md | HIGH | Non-FSD copy |

---
*PITFALLS for v0.4 Online Re-calibration. #1 silent meters, #2 oscillating/free-space, #3 persist mismatch, and #5 per-frame unguarded refit remain locks. Supersedes the v0.3 “defer online re-cal” focus of this file for roadmap input; v0.3 honesty contracts remain in force.*
