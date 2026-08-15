# Architecture: Online Re-calibration into Existing Sentry Spine

**Domain:** Consent-once gated online refine of an already-applied monocular metric scale  
**Project:** Sentry AI  
**Milestone:** **v0.4 Online Re-calibration (CAL-F03)**  
**Researched:** 2026-08-15  
**Overall confidence:** HIGH for plug-in boundaries (code-verified v0.3 spine); MEDIUM for exact N-sample / throttle defaults

## Executive answer

| Question | Answer |
|----------|--------|
| **Online without spine rewrite?** | Yes. Add an **opt-in online flag + draft sampler + gated `apply_params`**. DepthLoop remains the **sole** `apply_map` site. |
| **Invent first scale?** | **No.** First `metric_calibrated` still needs wizard `apply()` or matching persist `try_reapply`. |
| **Default?** | Online **off**. v0.3 behavior until the maker opts in. |
| **Draft = meters?** | **No.** WIZ-04 holds until `apply()` / `apply_params` of a **passed** fit. |
| **Where does auto-commit write?** | `CalibrationState.apply_params` only. Never a second map transform. |
| **YAML on auto-commit?** | **No** by default (session-only). YAML only on explicit save / persist:true / documented opt-in. |
| **DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`?** | **Frozen.** |

**Do not rewrite:** `FrameBus`, `DetectionLoop`, `OpenVocabLoop`, edge ORT/TRT factory, free-space algorithm core, persist fingerprint refuse, perception-only API boundary.

**Extend for v0.4:** `CalibrationState` online flag + online status; throttled draft sampler; gated auto-commit; status/docs; smoother reset on auto-commit (already exists for Apply).

---

## Current spine (code truth)

v0.3 insert point is already live:

```
DepthAnythingWorker.process → raw map + kind/unit
  → CalibrationState.apply_map / promote_kind_unit
  → PerceptionStore.set_depth
  → FreeSpaceLoop (units="m" only when metric_calibrated)
```

`CalibrationState` already has: draft vs applied, `apply()`, `apply_params()`, `clear_draft()`, `clear_applied()`, persist status `none|applied|ignored_mismatch|error`.

**v0.4 insert (control plane, not a second hot-path transform):**

```
online flag (default off)
  → if off: no samples, no auto-commit
  → if on and not applied: draft samples allowed; NEVER apply_params
  → if on and applied: throttle / N-window → same fit/reject (draft)
       → gate: fit ok + residual + fingerprints_match
            → apply_params (session-only)
            → next DepthLoop frame uses new applied params
            → reset OccupancySmoother like Apply
       → else: sticky last applied; status=rejected or online_draft
```

---

## Honesty contracts (do not weaken)

| Layer | v0.3 truth | v0.4 rule |
|-------|------------|-----------|
| `kind_for_mode` | Never returns calibrated | **Frozen** |
| Draft | Never `metric_calibrated` | **Holds** for online samples |
| `ok=False` fit | Never applied | **Holds** |
| Fingerprint mismatch | Refuse persist re-apply | **Also refuse auto-commit** |
| Cancel | `clear_draft` only | **Unchanged** |
| Clear | applied + YAML | **Unchanged**; disable-online ≠ Clear |
| Free-space meters | iff `metric_calibrated` | Auto-commit is just another applied commit |
| Persist YAML | explicit save / persist:true | Auto-commit **session-only** |

---

## Recommended architecture (opinionated)

### Design thesis

Online re-cal is **not** a neural stage and **not** a per-frame DepthLoop refit. It is a **throttled control-plane refine** that may replace applied params the same way persist load already does (`apply_params`).

This mirrors v0.2 “factory at construction, loop frozen” and v0.3 “diversity under a thin post-process owned by DepthLoop.”

### Why `apply_params` (not `apply()`, not a new transform)

| Placement | Verdict | Why |
|-----------|---------|-----|
| **`apply_params` after gated fit** | **Recommended** | Persist re-apply already commits without wizard samples; online is the same class |
| `apply()` from draft | Avoid for auto-commit | Wizard path; online should not require a staged wizard draft machine |
| New `apply_map` in sampler / API / UI | **Forbidden** | Dual truth |
| Inside `DepthAnythingWorker` | Avoid | Couples user calib to model load |
| Per-frame refit in DepthLoop | **Forbidden** | Pitfall #5 lock — oscillating scale |

### Component diagram (v0.4)

```
┌──────────────────────── spine (frozen) ──────────────────────────────┐
│ FrameBus → DetectionLoop / OpenVocabLoop                             │
│ FrameBus → DepthLoop → apply_map → set_depth → FreeSpaceLoop         │
└──────────────────────────────────▲───────────────────────────────────┘
                                   │ applied params only
┌──────────────────────────────────┴───────────────────────────────────┐
│ CalibrationState (EXTENDED)                                          │
│   online: bool = False                                               │
│   online_status: online_off \| online_draft \| auto_committed \| rejected │
│   draft samples / draft params (never promote)                       │
│   apply() / apply_params() / clear_draft() / clear_applied()         │
└──────────────────────────────────▲───────────────────────────────────┘
                                   │
        ┌──────────────────────────┼──────────────────────────┐
        │                          │                          │
        ▼                          ▼                          ▼
 online sampler (NEW)      same fit/reject (REUSE)     persist I/O (UNCHANGED)
 throttle / N-window       ok=False never applied      no implicit YAML write
```

---

## New vs modified vs frozen

### NEW (small)

| Component | Responsibility |
|-----------|----------------|
| Online flag + status | Default off; four-way status separate from `depth.kind` and persist |
| Online sampler | Throttled / N-sample window into **draft only** |
| Auto-commit gate | Five conjuncts → `apply_params` or reject |
| REST/UI toggle | Enable/disable online; cannot invent first scale |
| Synthetic tests | Gate matrix: off / not-applied / reject / mismatch / success |

### MODIFIED (careful)

| Component | Change | Do not |
|-----------|--------|--------|
| `CalibrationState` | online flag + status; auto-commit helper | Change `apply_map` formula |
| Calibration REST / status | Toggle + `online_*` fields | Overload persist status |
| FreeSpaceLoop | Reset smoother on auto-commit (same hook as Apply) | New band algorithm |
| Live Preview | Toggle + status copy | Rebuild wizard; React |
| `docs/calibration.md` | Online section; session-only persist | FSD language |

### FROZEN

FrameBus, DetectionLoop, ORT/TRT factory, `kind_for_mode`, persist fingerprint refuse, Cancel/Clear semantics, DepthLoop as sole `apply_map` site.

---

## Auto-commit gate (lock)

Auto-commit **only if all** hold:

1. Online mode **on**
2. Calibration **already applied** (wizard Apply or matching persist `try_reapply`)
3. Fit **ok** (same v0.3 reject gates)
4. Residual gate passes
5. `fingerprints_match`

On failure: keep last sticky applied scale; set `online_status=rejected` or stay `online_draft`; **never** change `depth.kind` from a failed fit.

Disable-online: set flag off + `online_off`; do **not** `clear_applied` or delete YAML.

---

## Data flow

### A. Serve start

```
cli.serve → CalibrationState(online=False)
  → try_reapply if file matches (v0.3)  # this MAY create first applied
  → online remains off unless operator enables
```

Matching persist re-apply **is** first-scale consent. Online still defaults off.

### B. Hot path (unchanged ownership)

```
worker.process → apply_map(applied params or passthrough) → set_depth
```

No fit, no sample, no YAML I/O in DepthLoop.

### C. Online cold path

```
if not online: return
collect sample into draft (throttled)
if window ready:
    fit/reject (draft params only)
    if gate: apply_params; reset smoother; status=auto_committed
    else: status=rejected; applied unchanged
```

### D. Persist

Auto-commit does **not** write YAML. Explicit save / persist:true / documented opt-in only. Fingerprint refuse unchanged.

---

## Status planes (do not collapse)

| Plane | Values | Meaning |
|-------|--------|---------|
| `depth.kind` | relative / metric_estimated / metric_calibrated | Product honesty |
| persist | none / applied / ignored_mismatch / error | File load/save |
| online | online_off / online_draft / auto_committed / rejected | v0.4 control |

A frame can be `metric_calibrated` + persist `applied` + `online_off`. A rejected online fit must not flip kind back to relative.

---

## API surface (additive)

Keep existing wizard routes. Add:

| Method | Path (suggested) | Behavior |
|--------|------------------|----------|
| `GET` | `/api/depth/calibration` | Include `online` + `online_status` |
| `POST` | `/api/depth/calibration/online` | `{enabled: bool}` — enable refused if not already applied (or enable-but-idle without auto-commit) |

**Opinion:** Enabling online while unapplied is allowed only as a no-op / 409 — it must **not** auto-commit a first scale. Prefer 409 + stay `online_off` until first consent exists.

Handlers never call `worker.process`, never write PerceptionStore, never `apply_map`.

---

## Patterns to follow

1. **Loop stable, control-plane swappable** — same as v0.2/v0.3.  
2. **Draft vs applied** — online samples are draft.  
3. **Sticky after commit** — no per-frame re-estimate.  
4. **Single store truth** — UI / `/v1` / free-space read store after DepthLoop.  
5. **CI without a room** — synthetic gate matrix.

---

## Anti-patterns

| Anti-pattern | Instead |
|--------------|---------|
| Auto-commit first scale | Require Apply / `try_reapply` |
| Fit inside DepthLoop | Throttled control plane |
| YAML on every auto-commit | Session-only |
| Disable-online deletes YAML | Flag only |
| Collapse online status into `depth.kind` | Three planes |
| New apply site in UI/API | DepthLoop only |

---

## Suggested build order

1. **Phase 19** — online flag default off; first-scale lock; Cancel/Clear/disable semantics; status enum  
2. **Phase 20** — sampler + reused fit/reject (draft only)  
3. **Phase 21** — gated `apply_params` + smoother reset + status  
4. **Phase 22** — persist policy + docs + synthetic CI  

---

## Confidence assessment

| Area | Level | Notes |
|------|-------|-------|
| DepthLoop remains sole apply site | **HIGH** | Code-verified |
| `apply_params` reuse | **HIGH** | Persist path already commits without wizard |
| First-scale lock | **HIGH** | Product lock |
| Window/throttle numbers | **MEDIUM** | Plan-phase |

---

## Sources

| Source | Informs | Confidence |
|--------|---------|------------|
| `control/calibration_state.py` | apply / apply_params / apply_map | HIGH |
| `spatial/calibration.py` | fit/reject | HIGH |
| `config/calibration_store.py` | fingerprint refuse | HIGH |
| `models/depth/loop.py` | sole apply site | HIGH |
| PROJECT.md v0.4 locks | Gate conjuncts | HIGH |

---
*Architecture research for Sentry AI v0.4 Online Re-calibration. Consent-once gated auto-commit via `apply_params`; DepthLoop remains the sole `apply_map` site; online default off; no implicit YAML.*
