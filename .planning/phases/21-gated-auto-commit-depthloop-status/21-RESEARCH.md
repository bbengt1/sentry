# Phase 21: Gated auto-commit + DepthLoop/status — Research

**Researched:** 2026-10-08
**Domain:** Promote a passed online fit to applied via `apply_params` only when every gate holds; DepthLoop hook; smoother reset; `auto_committed` / `rejected` status
**Confidence:** HIGH for plug-in boundaries (code-verified on main `8ba5b34`); HIGH for the locked horizon rule below
**Research flag:** Resolved here. CR-007 horizon refuse decided by Brent 2026-10-08 (LOCKED). Do not reopen during execute.

## Summary

Phase 20 shipped `OnlineSampler`: a throttled 8-frame window over consent anchors that runs `fit_scale_median` and only ever stages draft params. Phase 21 lets that passed fit go live, without another Apply click, but only through `CalibrationState.apply_params` and only when **all** of these hold at the moment of commit:

1. online is on
2. a consented scale is already applied
3. the fit is `ok` (same v0.3 absurd-scale gate)
4. the residual gate passed (same v0.3 residual, enforced inside `fit_scale_median`)
5. `fingerprints_match(applied.fingerprint, live)` for the frame that closed the window
6. **horizon refuse (new, ONL-09):** the candidate does not push the raw map to or past the 3 m free-space horizon (rule below)

Any failure keeps the last consented calibration applied, clears staged draft params, and sets `online_status="rejected"`. A pass calls `apply_params`, sets `online_status="auto_committed"`, clears the window, and resets the free-space smoother like wizard Apply. `DepthLoop` gets one optional hook that passes the **pre-apply raw** map, the live fingerprint, and a monotonic clock to the sampler before the unchanged `promote_kind_unit` → `apply_map` lines. `DepthLoop` stays the only `apply_map` call site. Auto-commit writes no YAML.

The wizard (`/sample` → `/compute` → `/apply`) and persist `try_reapply` are **unchanged** and do not get the horizon gate. Manual wizard Apply stays the maker's override.

---

## Locked decisions (do not reopen)

| # | Lock | Value |
|---|------|-------|
| 1 | Commit path | `apply_params` only, with a new keyword-only `expect_applied=` guard (see #8). Never `apply()`, never `apply_map` outside `DepthLoop`. |
| 2 | Conjuncts | online on AND applied AND fit ok AND residual gate AND `fingerprints_match` AND horizon pass. Order and reason tokens in the contract below. |
| 3 | Fit and gates | `fit_scale_median(..., method="known_distance")` unchanged. **No edit** to `MIN_SCALE`, `MAX_SCALE`, `_RESIDUAL_FRAC`, `_RESIDUAL_FLOOR_M`, or `spatial/calibration.py`. No `fit_affine_lstsq`. |
| 4 | Horizon refuse (Brent 2026-10-08) | Online auto-commit refuses a scale that passes the v0.3 gates but would push the raw map past `DEFAULT_METRIC_MID_CUT_M` (3.0 m) once applied. Rule in "Horizon rule". Wizard Apply and `try_reapply` do **not** get this gate. |
| 5 | Refuse outcome | Last consented (applied) params stay. `clear_draft_params()` so a refused scale is not left staged for a stray wizard Apply click. Window samples stay (sliding). `online_status="rejected"` only if online is still on. |
| 6 | Pass outcome | `apply_params(candidate, expect_applied=applied)`; status `auto_committed` set under the same state lock; sampler clears its window; `on_auto_commit()` callback (wired to `FreeSpaceLoop.reset_smoother`). |
| 7 | Opt-in in code | `OnlineSampler(state, *, auto_commit=False, on_auto_commit=None)`. Default `False` keeps the Phase 20 draft-only contract and its tests byte-for-byte. `serve` wiring passes `auto_commit=True`. The maker's consent is still the session online flag (Phase 19). |
| 8 | Atomic commit | `apply_params(params, *, expect_applied=None)`. With `expect_applied` set, under the state lock: require online on AND `self._applied_params is expect_applied`, else `ValueError("auto_commit_stale")`; on success also set `_online_status="auto_committed"`. With the default `None`, behavior is unchanged for wizard/persist callers. A Clear or disable that races the commit wins. |
| 9 | Reject status write | New `mark_online_rejected() -> bool`: under the lock, sets `rejected` only if online is on. Never resurrects status after Clear / disable. |
| 10 | Status meaning | `online_status` is the **last online decision**: `online_draft` until the first full-window decision after enable; then `auto_committed` or `rejected` until the next decision, disable (`online_off`), or Clear (`online_off`). Cancel (`clear_draft`) and wizard `apply()` do not change it (Phase 19 lock). |
| 11 | DepthLoop hook | Optional `online_sampler` (ctor kwarg + `set_online_sampler`). Called only when `calibration` and `depth_map` are present, **after** `refuse_if_mismatch` and **before** the unchanged `promote_kind_unit` / `apply_map`. Raw map is the worker output (pre-apply). `now_s=time.monotonic()`. Exceptions are caught and logged; the frame proceeds with the last applied scale. |
| 12 | Smoother reset | Auto-commit resets the free-space EMA through the same `FreeSpaceLoop.reset_smoother` that `/apply` uses. Reject does not reset. |
| 13 | YAML policy | Auto-commit is session-only: no `persist_applied`, no YAML write/delete, `persist_status` unchanged. Explicit `/save` or `/apply` `persist:true` remain the only writers (Phase 22 documents this). |
| 14 | Persist refuse | `refuse_if_mismatch` and `try_reapply` unchanged. A live mismatch clears applied before the sampler runs, so it cannot auto-commit. |
| 15 | Offset variant | Online candidates are scale-only (`offset == 0.0`, `method == "known_distance"`). The gate refuses anything else (`offset_not_zero`) and commits the sampler's own fit object, never `_draft_params` (a wizard `/compute` could have staged affine params from the online window). The horizon formula still includes `offset`. |
| 16 | Scope locks carried | Restart support out of scope (anchors session-only; STATE 2026-10-05). Version `0.1.0`. No new route, YAML key, snapshot field, or dependency. Phase 19 honesty and CR-001..005 fixes untouched. DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` frozen. |

---

## Horizon rule (ONL-09)

**Definition.** Let `raw` be the pre-apply raw depth map of the frame that completed the window (the map `consider` accepted, after the Phase 20 `map_space="applied"` inversion if used). Let `V = raw[isfinite(raw) & (raw > 0)]`. For a candidate with `scale` and `offset`:

```text
d_med = candidate.scale * median(V) + candidate.offset
refuse "horizon_unknown" if V is empty
refuse "horizon_refused" if d_med >= DEFAULT_METRIC_MID_CUT_M   (3.0 m, imported from spatial/free_space.py)
otherwise pass
```

Because `scale > 0`, `d_med` equals the median of the candidate-applied map over the same pixels. The rule is "the median of the depths at or beyond 3 m", so at least half of the valid pixels land in the far band and the near/mid bands are emptied for at least half the image.

**Why this rule:**

- **Anchors cannot be the input.** A passed fit already makes `scale * observed ≈ known_meters` at the anchors (median ratio, residual gate). An anchor-based check would just test whether the maker's tape points are beyond 3 m and would never catch a drifting raw scale. The scene map is what free-space consumes.
- **Matches the free-space horizon exactly.** `_meters_to_nearness` maps `d >= 3.0` to nearness `0`. Using `>=` and the same constant (imported, not copied) keeps one source of truth.
- **Matches CR-007's own test.** The review asks that a fit "whose implied scale would put a mid-range raw value beyond the far cut must not" go live. The median is that mid-range raw value.
- **Testable and cheap.** It is a scalar on an array the sampler already holds. It runs at most once per full-window accept (at most 1 Hz at the default throttle). It needs no ROI, no smoother state, and no PerceptionStore read.
- **Honesty-consistent.** It can only refuse. A refuse keeps the consented scale, never changes `depth.kind`, and never touches YAML.

**Fixture note:** the Phase 20 "consistent" fixture (raw 2.0, scale 2.0) gives `d_med = 4.0 m` and would be **refused**. Phase 21 success fixtures must keep `scale * median(raw) < 3.0` (for example, raw 1.0, known 2.0, scale 2.0, giving 2.0 m).

**Known cost:** in a scene whose true median depth is at least 3 m (a large hall, or a camera looking down a corridor), every online candidate is refused. Status reads `rejected`, the consented scale stays, and wizard Apply still works. This is conservative by design. See open question 1.

**Scale-down direction** (`d_med` shrinks) is not refused. It adds near/mid obstacles, which is the safe-side error, and it is still bounded by `MIN_SCALE` and the residual gate.

---

## Current APIs (code-verified on main `8ba5b34`)

| Surface | Today | Phase 21 touch |
|---------|-------|----------------|
| `OnlineSampler.consider` | Full window → `draft_staged` / `fit_rejected`; never commits | Add `live_fingerprint=None` kwarg; when `auto_commit=True`, gates + commit/refuse |
| `OnlineSampler.__init__` | `window_n`, `min_interval_s` | Add `auto_commit=False`, `on_auto_commit=None` |
| `CalibrationState.apply_params` | Structural validity; commit; clear draft; no online/anchor change | Add keyword-only `expect_applied=None` atomic guard (#8). Default path unchanged |
| `CalibrationState.set_online_status` | Any of four tokens | Unchanged. Sampler uses `mark_online_rejected` and the guarded commit instead |
| `refuse_if_mismatch` | Clears applied + `ignored_mismatch` | Unchanged |
| `fingerprints_match` | camera_id; depth_mode/model_id if saved non-None; HxW if both non-None | Reused as conjunct 5 |
| `DepthLoop._run` | `refuse_if_mismatch` → `promote_kind_unit` → `apply_map` → `set_depth` | Insert `consider(raw, live_fingerprint=live)` after refuse, before promote |
| `FreeSpaceLoop.reset_smoother` | Called by `/apply` and `/clear` routes | Also via `on_auto_commit` |
| `GET /api/status` | `calibration_online_status` already present | No new field. Now shows `auto_committed` / `rejected` |
| `serve` (`cli.py`) | `DepthLoop` built before `FreeSpaceLoop` | After `FreeSpaceLoop` exists, attach `OnlineSampler(state, auto_commit=True, on_auto_commit=free_space_loop.reset_smoother)` |

---

## Plan split

| Plan | Wave | Req | Delivers |
|------|------|-----|----------|
| **21-01** | 1 | ONL-05, ONL-09 | Gated auto-commit on the control plane: conjuncts, horizon refuse, offset lock, atomic `apply_params(expect_applied=)`, `mark_online_rejected`, status writes, window clear, `on_auto_commit`. No DepthLoop edit |
| **21-02** | 2 (`depends_on: 21-01`) | ONL-07 | DepthLoop hook (raw map + live fingerprint + monotonic), sole `apply_map`, smoother reset wiring in `serve`, persist refuse unchanged, status on `/api/status`, YAML untouched |

---

## Auto-commit contract (when `auto_commit=True`)

```text
consider(depth_map, *, frame_id, now_s, map_space="raw", live_fingerprint=None)

pre-accept checks: unchanged from Phase 20 (missing_frame_id ... empty_roi)
accept + window_short: unchanged
full window -> fit_scale_median (unchanged)
  ok=False                         -> clear_draft_params; mark_online_rejected; reason fit_rejected, fit_ok False
  ok=True, then gates in order (first failure wins; all failures -> clear_draft_params + mark_online_rejected, fit_ok True):
    online off                     -> gate_online_off
    no applied params              -> gate_not_applied
    residual_rms missing/non-finite-> gate_residual
    live_fingerprint is None       -> fingerprint_unavailable
    fingerprints_match false       -> fingerprint_mismatch
    offset != 0 or method != known_distance -> offset_not_zero
    V empty                        -> horizon_unknown
    d_med >= 3.0 m                 -> horizon_refused
  all pass -> apply_params(candidate, expect_applied=applied)
      ValueError                   -> mark_online_rejected; reason commit_stale
      success                      -> status auto_committed (inside the lock); clear window;
                                      on_auto_commit() (exceptions logged, commit stands);
                                      reason committed, fit_ok True
never: apply(), apply_map, persist helpers, YAML, set_online
```

With `auto_commit=False` the Phase 20 contract is unchanged (`draft_staged`, `online_draft`).

---

## Code-review disposition (2026-09-25)

| Finding | Phase 21 |
|---------|----------|
| **CR-007** online half | **Folded as ONL-09.** In-range scale that pushes the median past 3 m is refused for auto-commit; offset variant locked out (scale-only plus `offset_not_zero`); fingerprint gate uses the live frame's HxW, not the boot `width=None` |
| **CR-007** wizard/YAML half | **Not folded.** `is_valid_calibration_params`, `manual_scale` from disk, `try_reapply` gates, boot null width, and the one-point wizard accept stay as-is. Brent: manual wizard Apply is the override and must not change |
| **CR-009 / CR-015** (Clear vs apply atomicity) | Online path only: `expect_applied` guard means a racing Clear/disable wins. The wizard/route atomicity fix is not in this phase |
| **CR-018** status honesty | Status is now written only by the sampler's commit/refuse paths, separate from `depth.kind` and persist |
| CR-001..003, CR-004..005 | Already on main (PRs #23, #22). No route added, no depth-honesty code touched |

---

## Considered and rejected

| Idea | Why not |
|------|---------|
| Horizon check on anchor predictions | A passed fit already matches anchors to `known_meters`; it tests tape distance, not the scene |
| "All pixels ≥ 3 m" | Too weak: a few near pixels let a scale that blanks most of the image through |
| Free-space ROI-only median | ROI fraction is runtime-configurable on `FreeSpaceLoop`; it couples the sampler to spatial config for little gain |
| Relative rule (refuse only if applied median < 3 m and candidate ≥ 3 m) | Lets an already-far scene go to arbitrary scale (applied 3.5 m → candidate 1000×). Kept as open question 1, not the default |
| Gate wizard Apply too | Brent: wizard stays the override and is unchanged |
| Tighten `MAX_SCALE` | Changes the wizard and ONL-04's "same gates" |
| Commit `_draft_params` from state | A wizard `/compute` can overwrite it with affine params from the online window; commit the sampler's own fit |
| Fit / commit in a separate thread | Fit is a median over at most 8×anchors values at ≤1 Hz; one extra thread adds lifecycle risk for nothing |
| Write YAML on auto-commit | Session-only lock; Phase 22 policy |
| New `rejected_reason` snapshot field | No new snapshot fields; reason is in `OnlineSampleResult` and the log |

---

## Must not ship (this phase)

- Horizon gate on wizard `/apply`, `/compute`, or `try_reapply`
- Edits to `spatial/calibration.py` gates, `fit_affine_lstsq` use, or `is_valid_calibration_params`
- A second `apply_map` call site (sampler, API, UI)
- YAML write/delete from auto-commit; new YAML key; anchor persistence; restart support
- New route, snapshot field, dependency, or `pyproject` version bump
- Changes to `refuse_if_mismatch`, `fingerprints_match`, Cancel/Clear/disable semantics
- FSD / vehicle-grade copy (Phase 22 docs)

---

## Open questions (Brent)

1. **Large scenes (before 21-01 execute, non-blocking):** the locked absolute rule refuses every online candidate when the scene's median depth really is at least 3 m, even if the consented scale already puts it there. The plan ships strict-absolute. If you want "refuse only when the candidate crosses 3 m and the applied scale did not, or moves the median by more than X×", say so before 21-01 starts.
2. **Deadband (non-blocking):** every full-window pass commits, even when the new scale equals the applied one. With the default N=8 / 1.0 s that can reset the free-space smoother about every 8 s. The plan ships no deadband. Optional: skip the commit when `|new/applied − 1| < 1%`.

---

## RESEARCH COMPLETE

**Phase:** 21 — Gated auto-commit + DepthLoop/status
**Confidence:** HIGH

Key findings: commit through `apply_params(expect_applied=)` only; six conjuncts including the locked horizon refuse (`scale * median(raw) + offset >= 3.0 m` → refuse); the offset variant is locked out on the online path; DepthLoop passes the raw map and live fingerprint before the unchanged `apply_map`; smoother reset via callback; status is the last online decision; no YAML.

Ready for planning.
