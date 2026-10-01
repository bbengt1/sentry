# Phase 20: Online sample + fit/reject — Research

**Researched:** 2026-10-01
**Domain:** Throttled N-sample window into draft only; reuse v0.3 fit/reject; no meter promotion
**Confidence:** HIGH for plug-in boundaries (code-verified on main `c98a09b`); HIGH for the locked window defaults below
**Research flag:** Partial — resolved here. Do not reopen N / interval during execute unless Brent overrides before 20-01 starts.

## Summary

Phase 19 shipped the session flag, the first-scale refuse, Cancel / Clear / disable-online, and the four-way `online_status` plane. Nothing samples, fits, or commits on that flag. Phase 20 adds a **control-plane sampler** that, only while online is already on, re-reads the maker's **already-consented** image anchors against a **pre-apply raw** depth map, on a throttle, and writes **draft samples** only. When the window is full it calls the existing `fit_scale_median` and may `set_draft_params` only if `ok=True`. It never calls `apply`, `apply_params`, or `apply_map`, never writes YAML, and never assigns `auto_committed` or `rejected`.

The store's depth product is **post-apply** (`DepthLoop` calls `apply_map` before `set_depth`). Sampling that product as if it were raw compounds scale (pitfall #4 / #8) and is the online-specific way a fit can push free-space past the 3 m horizon. The sampler's supported maps are worker output **before** `apply_map`, or an explicit invert of the store map. This phase does not hook `DepthLoop`.

---

## Locked decisions (do not reopen)

| # | Lock | Value |
|---|------|-------|
| 1 | Home | `OnlineSampler` is a helper that mutates `CalibrationState` through its methods. Not a second source of truth. Not `OnlineRecalState`. |
| 2 | When it runs | `consider` no-ops unless `is_online()` and `is_applied()`. Online-off and unapplied write nothing. |
| 3 | What it measures | Session **consent anchors** captured from wizard draft samples inside successful `apply()` only: `point_uv` or `bbox_xyxy` plus `known_meters`. No CLIP, no detection tracking, no new GT. |
| 4 | Persist of anchors | **Session only.** YAML still strips `samples`. `try_reapply` / `apply_params` do not invent anchors. No anchors → `no_anchors`, no fit. |
| 5 | Clear vs Cancel vs disable | `clear_applied` drops anchors (consent gone). `clear_draft` (Cancel) drops the online window (it lives in draft) and does **not** drop anchors, applied, or the online flag. `set_online(False)` drops none of applied, YAML, anchors, or existing draft. |
| 6 | Draft home | Online window replaces `_draft_samples` (same list Cancel already clears). No second sample list. `note="online"`. |
| 7 | Window | **`ONLINE_WINDOW_N = 8`** accepted frames before a fit. One frame = one read of every anchor. |
| 8 | Throttle | **`ONLINE_MIN_INTERVAL_S = 1.0`** between accepts. Caller passes `now_s` (tests must not sleep). `time.monotonic` is the Phase 21 caller's clock. |
| 9 | Frame gate | Accept only a **strictly increasing** `frame_id`. Same or older id does not count, even if the clock advanced. |
| 10 | Map space | Default `map_space="raw"` (worker map before `apply_map`). `map_space="applied"` inverts with the current applied scale/offset: `raw = (map - offset) / scale`, then reads anchors. |
| 11 | Fit | `fit_scale_median` only (offset 0). Same absurd-scale and residual gates. Affine and `manual_scale` stay wizard/persist paths. |
| 12 | `ok=False` | Do not `set_draft_params`. `clear_draft_params` only (samples stay). Applied scale unchanged. `online_status` stays `online_draft`. |
| 13 | `ok=True` | `set_draft_params` only. Applied scale, `snapshot.scale`, kind/unit, online flag, and `online_status` unchanged. Draft fingerprint copied from the **applied** params. |
| 14 | Status plane | Phase 20 never assigns `auto_committed` or `rejected`. Three planes stay separate. |
| 15 | Hot path | No `consider` inside `DepthLoop._run`. No `apply_map` edit. No new HTTP route. |
| 16 | Honesty from Phase 19 | `set_online(True)` unapplied still raises `online_requires_applied`. `apply` / `apply_params` still do not turn online on. Nothing in this phase auto-commits. |
| 17 | Out of phase | Five-conjunct auto-commit, smoother reset, `fingerprints_match` as a commit gate, YAML policy, Live Preview, docs hub, new deps, DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`. |

### Why these window numbers

DepthLoop keep-latest is on the order of the camera rate. A 1.0 s gap is at least several frames at maker rates and is injectable in tests. Eight accepted frames is enough for a median ratio to move off a single pair, so the online path is not the wizard's one-point zero-residual accept. Eight timestamps `0, 1, …, 7` finish a window with no sleep and no camera. Constructors may take a smaller `window_n` only in tests that are not the default-lock test; the default on `OnlineSampler()` is 8 and 1.0.

---

## Current APIs (code-verified on main)

| Surface | Today | Phase 20 touch |
|---------|-------|----------------|
| `CalibrationState.apply` | Commits draft params; clears draft samples; does not enable online | On **success only**, replace `_consent_anchors` from those draft samples, then clear draft |
| `apply_params` | Commits params; clears draft; does not enable online | **Do not** change anchors |
| `clear_applied` | Wipes applied, forces online off | Also clears anchors |
| `clear_draft` | Drops draft params + samples; online unchanged | Unchanged (this is how Cancel drops the window) |
| `add_draft_sample` | Append | Keep. Sampler uses a new `replace_draft_samples` so the window stays bounded |
| `set_draft_params` | Stages params; does not apply | Called only from the sampler when fit `ok=True` |
| `POST /sample` | **409** when already applied | Sampler must not use this route. Online is only legal after apply |
| `POST /compute` | Fits current draft; 422 and no `set_draft_params` when `ok=False` | Sampler calls `fit_scale_median` itself; same staging rule |
| `fit_scale_median` | `MIN_SCALE=1e-4`, `MAX_SCALE=1e4`, residual `max(0.15 * median(D), 0.05)` | **Reuse. Do not edit gates** |
| `DepthLoop._run` | `refuse_if_mismatch` → `promote_kind_unit` → `apply_map` → `set_depth` | **Frozen.** Store map is post-apply |
| `CalibrationSnapshot.scale` | Applied scale only | Stays applied. A staged draft must not show up as `snapshot.scale` |
| YAML | `_BANNED_YAML_KEYS` includes `samples` | No new key |

`apply_map` formula remains `scale * map + offset` (float32 copy). Invert is the algebraic inverse, used only when `map_space="applied"`.

---

## Plan split

| Plan | Wave | Req | Delivers |
|------|------|-----|----------|
| **20-01** | 1 | ONL-03 | Anchors on successful `apply`; throttled window into draft only; no fit; honesty matrix (Cancel / Clear / disable) |
| **20-02** | 2 (`depends_on: 20-01`) | ONL-04 | Full window → `fit_scale_median`; `ok=True` stages draft params only; `ok=False` does not; applied scale sticky |

---

## Sampler contract

```text
consider(depth_map, *, frame_id, now_s, map_space="raw") -> OnlineSampleResult

checks, in order, writing nothing on failure:
  missing frame_id
  not online            -> online_off
  not applied           -> not_applied
  no consent anchors    -> no_anchors
  frame_id <= last accepted -> frame_not_advanced
  now_s - last_accept < 1.0 -> throttled
  map_space applied and scale not finite/>0 -> bad_applied_scale
  any anchor not finite and >0 on the raw map -> empty_roi

on accept:
  replace draft samples with the last min(accepted, 8) frames
  if accepted < 8: reason window_short, no fit
  if accepted >= 8: fit_scale_median
      ok=False -> clear_draft_params, reason fit_rejected
      ok=True  -> set_draft_params, reason draft_staged
  never apply / apply_params / apply_map / YAML / status enum write
```

`OnlineSampleResult` is an in-process dataclass, not a REST model. No new snapshot fields.

Anchor read matches the wizard point / bbox median (finite and `> 0` only) but raises no `HTTPException`. A frame counts only when **every** anchor reads. Fixed image coordinates: if the consented patch leaves the finite region, the frame is dropped and the last applied scale stays.

---

## Code-review disposition (2026-09-25)

Source: `code-review-2026-09-25-full-repo.md` (PR #21), re-read against main after PRs #20, #22, and #23.

### Folded into this phase (locks and risks, not new ONL ids)

| Finding | What Phase 20 takes |
|---------|---------------------|
| **CR-007** (partial) | Online must not be a one-point zero-residual accept (`N=8`). Samples are pre-apply raw or an explicit invert, so the sampler cannot compound `scale * (scale * raw + offset)`. `absurd_scale` / residual failure never stages draft params and never applies. A scale **inside** `(1e-4, 1e4)` may still `set_draft_params` (same v0.3 gates, ONL-04) but `snapshot.scale` and applied params stay on the consented scale. That in-range hole is a **Phase 21 risk**, not a Phase 20 apply path. |
| **CR-018** (partial) | The missing POST itself landed in 19-02. Phase 20 still must not treat the flag as a meter switch: online-off samples nothing; this phase never sets `auto_committed` or `rejected`; `online_status` is not `depth.kind` and not persist. |

### Not folded

| Finding | Why it is not Phase 20 |
|---------|------------------------|
| **CR-007 remainder** | `is_valid_calibration_params` still allows any finite `scale > 0` and any finite offset; `manual_scale` skips the sample-count check; `try_reapply` does not re-run fit gates; boot fingerprint `width=None` can match a saved width. Those are persist/wizard holes. Changing them rewrites v0.3 load policy. Do not hide them inside the sampler. |
| **CR-001, CR-002, CR-003** | Non-finite depth, stale free-space, and `depth_mode` honesty — PR #23, already on main. |
| **CR-004, CR-005** | Host / Origin / content-type — PR #22. Phase 20 adds no route, so it does not reopen that surface. |
| **CR-006, CR-008–CR-017** | RTSP userinfo, weight digests, Clear/Apply atomicity, ordinal sliders, drop counter, stale MJPEG, URL scheme, Swift helper, OpenAPI. Not the draft sampler. |

---

## Considered and rejected

| Idea | Why not |
|------|---------|
| Sample `PerceptionStore` by default | Store map is post-apply. Default raw; invert is opt-in |
| New `POST /api/depth/calibration/online/sample` | Injects `known_meters` without a new consent story; CR-004 class of problem. In-process `consider` only |
| Fit inside `DepthLoop._run` | Pitfall #5. Phase 21 may call `consider` off the hot path later |
| Separate `_online_samples` list | Cancel would not drop the window unless we special-case it. Draft list already has that meaning |
| Set `online_status=rejected` on `ok=False` | Phase 21 owns that transition (roadmap SC for 21) |
| `fit_affine_lstsq` online | Offset is the CR-007 "push every pixel past 3 m" knob. Scale-only median reuses the primary gate |
| Persist anchors to YAML | Phase 22 policy. This phase must not add a YAML key |
| Tighten `MIN_SCALE` / `MAX_SCALE` | ONL-04 says the same gates. A horizon gate is a product change to the wizard too |
| Enable-while-unapplied idle sampling | Phase 19 lock #3 already refuses. Do not reopen |
| Language / CLIP / detector-tracked GT | Anti-feature. DetectionLoop stays frozen |

---

## Must not ship (this phase)

- `apply` / `apply_params` / `apply_map` from the sampler
- Assignment of `auto_committed` or `rejected`
- DepthLoop edits, smoother reset, `fingerprints_match` commit gate
- YAML write or delete, including an anchors key
- New pip deps; `pyproject` version bump; FastAPI route; `index.html`
- Edits to `fit_scale_median` / `fit_affine_lstsq` thresholds
- FSD / vehicle-grade copy

---

## Open questions (Brent)

1. **Before 20-01 execution:** Anchors exist only after a wizard `apply()` in this process. A matching `try_reapply` restores scale and leaves the sampler idle (`no_anchors`). Phase 20 will not invent tape points and will not store them in YAML. Confirm that headless refine across restart is out of this phase. If it is in, stop and re-plan — that is a persist-schema change, not a sampler tweak.
2. **Before Phase 21, not before Phase 20:** CR-007's in-range scale (just under `1e4`, or a large finite offset on the wizard/YAML path) can still empty metric free-space once something **applies** it. Phase 20 only stages draft. Should auto-commit grow a horizon/offset refuse that the wizard gates do not have? This plan does not add that refuse.

---

## RESEARCH COMPLETE

**Phase:** 20 — Online sample + fit/reject
**Confidence:** HIGH

Key findings: draft window on consented anchors; N=8 and 1.0 s; pre-apply raw; same `fit_scale_median`; `ok=False` never applied; Cancel / Clear / disable stay distinct; no auto-commit.

Ready for planning.
