# Domain Pitfalls: Metric Depth Calibration UX

**Domain:** Adding monocular **metric scale** (known heights / markers) to an existing **relative-depth** perception stack  
**Project:** Sentry AI — milestone **v0.3 Metric Depth Calibration UX**  
**Researched:** 2026-08-11  
**Overall confidence:** HIGH for honesty / free-space / persistence risks (verified against Sentry code + contracts); MEDIUM for exact scale-estimation geometry formulas (depends on chosen wizard method)

**Product thesis (non-negotiable):** camera-only maker perception — **not FSD**. Calibration yields **honest approximate meters**, never vehicle-grade clearance.

**Existing honesty baseline (must not regress):**
- `DepthKind`: `relative` | `metric_estimated` | `metric_calibrated` ([`enums.py`](../../src/sentry_ai/schemas/enums.py))
- Relative **forbids** `unit` / meters ([`validators.py`](../../src/sentry_ai/schemas/validators.py), FOUND-03)
- Free-space v1 is **ordinal** near-field bands; no `distance_m` ([`free_space.py`](../../src/sentry_ai/spatial/free_space.py), [`perception-frame.md`](../../docs/perception-frame.md))
- Wire free-space units hard-coded ordinal even for `metric_calibrated` today ([`assemble.py`](../../src/sentry_ai/api/assemble.py) `_units_for_depth_kind`)

---

## Critical Pitfalls

### 1. Silent unit lies (relative labeled as meters)

**What goes wrong:**  
UI footer, `/v1` snapshot, colormap legend, or free-space payload says `"m"` / “meters” while the underlying map is still **relative** (or affine-normalized ordinal). Robots treat nearness as stopping distance. Support tickets look like “depth is wrong by 3×” when the real bug is **unit fiction**.

**Why it happens:**
- Temptation to “just multiply by a scale and set unit=m” without promoting `depth_kind`
- Confusing **`metric_estimated`** (DAV2 metric heads, domain-split, still uncalibrated) with **`metric_calibrated`** (user ground-truth scale)
- Latent mode-switch hazard already in code: `kind_for_mode()` sets kind/unit from **config string**, but `DepthAnythingWorker._ensure_model()` **returns the already-loaded model** after `set_depth_mode` only updates `model_id` — relative weights can keep running under a metric label ([`worker.py`](../../src/sentry_ai/models/depth/worker.py) `set_depth_mode` + `_ensure_model` early return)
- Colormap / status copy that hardcodes “m” when `depth_kind` is relative

**Consequences:**
- Unsafe control-loop assumptions (hobby monocular ≠ clearance)
- Trust collapse; FOUND-03 regression
- Impossible field debugging (“meters disagree with tape measure”)

**Prevention:**
- **Single promotion rule:** `unit="m"` **only** when `kind ∈ {metric_estimated, metric_calibrated}`; relative always `unit=null`
- Validators: keep `relative_depth_forbids_unit`; add tests that reject relative+`m` on **every** surface (DepthPayload, free-space `units`, UI status, docs examples)
- Never derive kind from “array looks like meters” heuristics — kind comes from **mode + calibration state** only (already the mapping.py philosophy)
- Mode switch must **invalidate or reload** weights when `model_id` changes; status reports **loaded** model id, not just requested mode
- Live Preview badge text: `relative` / `metric_estimated` / `metric_calibrated` — never bare “meters” without kind
- Product copy: calibrated ≠ accurate; show residual / method / timestamp

**Detection:**
- Snapshot `depth.kind=relative` with `unit="m"` (should fail schema)
- Status shows metric while depth worker still holds relative HF id
- Free-space `units="m"` while obstacles only have 0..1 nearness and no metric band path

**Phase ownership:** **Phase 1 — Honesty contracts & scale state model** (first phase; blocks every other plan).  
**Warning signs in PR review:** any PR that sets `unit="m"` without updating `kind`; any mode toggle that does not clear/reload model.

**Confidence:** HIGH  
**Sources:** [`validators.py`](../../src/sentry_ai/schemas/validators.py), [`mapping.py`](../../src/sentry_ai/models/depth/mapping.py), [`worker.py`](../../src/sentry_ai/models/depth/worker.py), [`docs/perception-frame.md`](../../docs/perception-frame.md), FOUND-03

---

### 2. Free-space breakage (ordinal bands dressed as meters)

**What goes wrong:**  
Calibration flips free-space `units` to `"m"` (or adds `distance_m`) while Spatial Post still runs **per-frame min–max nearness + percentile cuts** (`near_cut=0.72`, `mid_cut=0.45`). Obstacles “look metric” but band membership is still **scene-relative**. EMA smoother (`OccupancySmoother`) carries pre-calibration occupancy into post-calibration frames. Polarity `auto` can flip after scale if the map polarity or value range changes.

**Why it happens:**
- v1 free-space was deliberately ordinal for relative **and** `metric_estimated` ([`test_metric_estimated_still_ordinal_units`](../../tests/test_free_space_bands.py))
- `assemble._units_for_depth_kind` always returns `"ordinal"` — easy to “fix” by returning `"m"` without a metric algorithm path
- `depth_to_nearness` normalizes **each frame** to [0,1]; absolute meters are destroyed before banding
- Near/mid cuts are unitless; they are not “1.5 m / 3 m”

**Consequences:**
- Robot thinks “near band = under 1 m” when it means “top 28% nearest pixels in this FOV”
- Calibration appears to “work” in UI (label change) while obstacle geometry is unchanged
- Apply/cancel calibration leaves smoother ghost obstacles or empty free-space for several frames

**Prevention:**
- **Two free-space modes, explicit:**

  | Depth state | Free-space units | Band logic |
  |-------------|------------------|------------|
  | `relative` | `ordinal` | Keep percentile nearness + cuts (v1) |
  | `metric_estimated` (uncalibrated) | `ordinal` (default) or clearly labeled estimated | Do **not** invent meter bands without policy |
  | `metric_calibrated` | `"m"` only if metric path runs | Absolute depth thresholds in meters (e.g. near &lt; N m) on **scaled map**, not 0..1 cuts |

- Gate `units="m"` on free-space behind **metric band implementation**, not kind alone
- On calibration apply / clear / mode change: **reset `OccupancySmoother`** and force free-space recompute (clear product once if needed — mirror `set_enabled(False)` honesty)
- Keep `nearness_*` ordinal fields; if meters are exposed, add **separate** fields (e.g. `distance_mean_m`) — never overload nearness 0..1 as meters
- Golden tests: same relative map + scale factor → metric free-space bands move with absolute thresholds; uncalibrated path never emits `units="m"`

**Detection:**
- Free-space `units="m"` but `method=near_field_bands` with only fractional cuts and no metric threshold config
- Obstacle `nearness_mean` &gt; 1.0 or “distance” identical to pre-calibration nearness
- Band fractions identical before/after scale apply (label-only change)

**Phase ownership:** **Phase 4 — Free-space metric path** (after depth scale actually applied to maps; **not** in the same PR as the wizard chrome).  
**Depends on:** Phase 1 honesty + Phase 2 scale application to depth product.

**Confidence:** HIGH  
**Sources:** [`free_space.py`](../../src/sentry_ai/spatial/free_space.py), [`spatial/loop.py`](../../src/sentry_ai/spatial/loop.py), [`assemble.py`](../../src/sentry_ai/api/assemble.py), Phase 5 research (ordinal by design)

---

### 3. Persistence hazards (wrong camera, stale scale, silent re-apply)

**What goes wrong:**  
Calibration is saved globally or under profile name only. Operator swaps USB camera / RTSP URL / resolution / lens; serve reloads last scale and labels `metric_calibrated`. Scale was fit for another FOV/height/mount. Or file is corrupt / half-written and serve either crashes or silently runs uncalibrated while UI still shows “calibrated.”

**Why it happens:**
- v1 is single active source but `camera_id` is already the multi-cam extension key — easy to ignore in v0.3
- Profile YAML is a **deployment** unit, not a physical camera fingerprint
- Resolution / crop / Continuity uniqueID changes without changing `camera_id` string
- Race: wizard writes file while serve reads; no schema version / checksum
- Re-apply on serve before depth worker ready → status lies about calibrated while first frames are relative

**Consequences:**
- Persistent silent unit lie across restarts (worst class of honesty bug)
- “It worked yesterday” after camera re-mount
- Multi-machine copy of calib JSON (like TRT engines) looks portable and is not

**Prevention:**
- **Key calibration by physical identity**, not only profile:

  | Key component | Why |
  |---------------|-----|
  | `camera_id` | Source identity on PerceptionFrame |
  | Capture fingerprint | backend + device path / uniqueID / RTSP host path |
  | Image size (W×H) | Scale from bbox height is resolution-sensitive |
  | Depth mode / model id | Relative vs metric head changes value domain |
  | Schema version | Forward-compatible load |

- On fingerprint mismatch: **refuse** auto-apply → fall back to relative honesty + loud status reason (`calib_mismatch:resolution`, etc.)
- Atomic write (temp + rename); validate with Pydantic before applying
- Status/telemetry: `calibration.state` = `none | applied | ignored_mismatch | error` separate from `depth.kind`
- Clear/cancel writes explicit “no calib” state (delete or tombstone) — do not leave orphan files that reappear on restart
- Never ship a default “1.0 m scale” in the wheel

**Detection:**
- Serve logs “calibration applied” after camera_id or resolution change with no new wizard run
- Two hosts share one calib file path via NFS/USB
- UI shows calibrated; `/v1` depth kind is relative (split brain)

**Phase ownership:** **Phase 5 — Persist & re-apply** (after apply path works in-memory). Design the **key schema** in Phase 1 so wizard + serve do not invent divergent formats.  
**Warning signs:** “save to profile YAML only”; no invalidation tests.

**Confidence:** HIGH (pattern matches multi-cam hooks + edge artifact fingerprint lessons from v0.2)

---

### 4. Scale math lies (affine depth, wrong target, bbox height misuse)

**What goes wrong:**  
Wizard takes “object is 1.7 m tall,” measures bbox height in pixels, computes a single scale `s`, multiplies the whole map. Reality: monocular relative depth is often **affine-invariant** (scale **and** shift), not pure scale; known **height** needs a geometric model (camera height / pitch / focal length or a known depth sample), not raw `H_real / h_px` alone. Partial occlusion, non-vertical objects, and detection jitter produce 20–50% scale error that is then labeled `metric_calibrated`.

**Why it happens:**
- Blog-post “scale factor” oversimplification
- Using YOLO bbox height as metric height without upright assumption or foot-point depth
- Calibrating on **disparity-like** relative maps with a formula meant for metric-head meters
- Single-click calibration with no multi-sample median / outlier reject
- Mixing **metric_estimated** head outputs (already meters, domain-clipped at max_depth 20/80 m per DAV2 metric heads) with a second “relative scale” pipeline

**Consequences:**
- Systematic bias (always 1.4× too far) trusted as calibrated truth
- Outdoor/indoor domain mismatch amplified
- Makers believe wizard “finished” = accurate

**Prevention:**
- Document the **exact** scale model in code + docs (one formula, one module):
  - Prefer: sample depth at a known **metric reference** (tape distance to marker **or** known-size target with stated FOV/intrinsics assumptions) → fit `d_m ≈ s * f(d_raw)` (and optional shift if model requires)
  - Known object height: require upright object + ground contact point + explicit camera-height or focal assumption; surface assumptions in UI
- Fit on **≥N samples** or temporal median; reject if residual &gt; threshold; stay relative if reject
- Separate pipelines:
  - **Relative + user scale** → `metric_calibrated` (with method=`user_scale`)
  - **Metric head** → `metric_estimated` unless user scale also applied (then calibrated-on-estimated, still not FSD)
- Never claim sub-5% accuracy; UI: “approximate meters for makers”
- Synthetic unit tests with known maps (no room required): pure functions for fit/apply/reject

**Detection:**
- Scale factor changes wildly frame-to-frame during wizard
- Calibrated distance to a second known marker fails residual check
- Applying scale to metric_estimated head doubles units (m·s product)

**Phase ownership:** **Phase 2 — Calibration math core (pure, CI-safe)** before any wizard UI.  
**Confidence:** MEDIUM–HIGH for risk class; MEDIUM for exact formula choice (product decision in planning).

**Sources:** DAV2 metric heads use domain max_depth (indoor 20 m / outdoor 80 m) — [Depth Anything V2 metric_depth README](https://github.com/DepthAnything/Depth-Anything-V2/tree/main/metric_depth); OpenCV calibration docs stress known pattern size for **metric** object points but full intrinsics are **out of v0.3 primary path** (PROJECT.md deferred)

---

### 5. Wizard UX thrash (partial apply, cancel lies, mid-stream mutation)

**What goes wrong:**  
User starts wizard, clicks points, Apply fails halfway (depth scaled, free-space still ordinal, UI badge calibrated). Cancel does not restore previous state. Preview shows meters while `/v1` still relative (or reverse). Per-frame re-fit while walking around makes scale oscillate; robots see jumping distances.

**Why it happens:**
- Multi-product store (depth + free-space + status + MJPEG) updated non-atomically
- Apply mutates live worker without a transactional “pending → commit” model
- Status poll (500 ms) and MJPEG path race
- “Helpful” continuous recalibration without sticky commit

**Consequences:**
- Split-brain honesty across UI / snapshot / stream
- Operator cannot trust Cancel
- Support: “I cancelled but still in meters”

**Prevention:**
- **Calibration session state machine:**

  ```
  idle → drafting (pending samples, no product change)
      → preview (optional ephemeral overlay only)
      → committed (atomic: scale + kind + free-space mode + status)
      → cleared
  ```

- Commit is one backend API that updates scale holder + invalidates free-space smoother + sets kind policy; UI never “locally” claims calibrated
- Cancel discards draft only; committed state untouched unless Clear
- Sticky scale after commit (mirror v0.2 sticky backend): no per-frame re-estimate unless user re-runs wizard
- Integration tests: apply → snapshot kind/unit/free-space units consistent; cancel draft → no kind change; clear → relative honesty restored

**Detection:**
- Footer kind ≠ `/v1` depth.kind for &gt;1 status poll
- Cancel leaves `metric_calibrated` on disk
- Scale changes without wizard interaction

**Phase ownership:** **Phase 3 — Live Preview wizard + apply/cancel API** (after pure math + in-memory apply exist).  
**Confidence:** HIGH (same class as v0.2 sticky fallback / honesty)

---

### 6. Accuracy / FSD overclaim (product thesis breach)

**What goes wrong:**  
README, wizard success screen, or release notes imply “metric depth = autonomous navigation ready.” Makers wire free-space meters into unsupervised drive. A single good indoor calibration is marketed as general.

**Why it happens:**
- Calibration UI feels “professional”
- Metric heads + scale sound like stereo/LiDAR
- Competitive pressure vs depth-camera products

**Consequences:**
- Safety incident risk (project explicitly forbids FSD claims)
- Scope creep into full photogrammetry / SLAM

**Prevention:**
- Keep safety copy: free-space **not** an interlock ([`safety-and-privacy.md`](../../docs/safety-and-privacy.md))
- Wizard success: “Approximate metric scale applied — monocular, not vehicle-grade”
- No `safe_to_drive` / go-nogo fields (API-05 unchanged)
- Docs: error sources (domain, lighting, mount change, single-scale limits)
- Residual / method metadata on status, not just a green check

**Detection:**
- Marketing language “precise meters,” “autonomous,” “FSD-lite”
- Wizard omits uncertainty

**Phase ownership:** **Docs + UI copy continuous**; gate in Phase 3 wizard strings and Phase 6 docs polish.  
**Confidence:** HIGH  
**Sources:** PROJECT.md out-of-scope FSD; safety-and-privacy.md

---

## Moderate Pitfalls

### 7. Metric head domain mismatch (indoor head outdoors)

**What goes wrong:**  
User enables `metric_outdoor` outdoors or `metric_indoor` in a warehouse aisle &gt;20 m; max_depth clipping + domain shift makes “meters” systematically wrong even before user calibration.

**Prevention:**  
Wizard and docs state domain; calibration residual fails closed to relative; do not auto-pick outdoor from GPS.

**Phase ownership:** Phase 1 policy + Phase 2 residual gates.

**Confidence:** HIGH (DAV2 metric indoor max_depth=20, outdoor=80 — upstream metric README)

---

### 8. Double-scaling and kind confusion

**What goes wrong:**  
Load metric_estimated head (already meters), then apply relative-style scale again → double scale. Or promote to `metric_calibrated` without recording base mode.

**Prevention:**  
Store `base_depth_mode` + `scale` + `method` in calib record; apply function is pure and mode-aware; tests for relative→calibrated and estimated→calibrated paths.

**Phase ownership:** Phase 1 state model + Phase 2 apply function.

---

### 9. Thread / product races on apply

**What goes wrong:**  
DepthLoop writes unscaled map while apply thread sets kind calibrated; FreeSpaceLoop consumes mixed frames.

**Prevention:**  
Single scale holder with lock read by depth publish path **or** scale applied only in one place (DepthLoop post-process) with generation counter; free-space reads kind from same DepthProduct.

**Phase ownership:** Phase 2 runtime apply wiring.

---

### 10. UI colormap hides metric meaning

**What goes wrong:**  
Per-frame min–max TURBO colormap still used after calibration — far wall always “hot,” so operators think scale did nothing; they crank scale until colors “look right,” destroying metric.

**Prevention:**  
Optional fixed metric colormap range when calibrated (e.g. 0–5 m) with legend; default may stay relative-normalized for visibility but **must not** be the only feedback — show numeric sample depth under cursor / marker.

**Phase ownership:** Phase 3 wizard visual feedback.

---

### 11. Intrinsics scope creep

**What goes wrong:**  
Milestone expands into full chessboard photogrammetry, stereo, multi-view — delays ship; half-finished intrinsics path ships as calibrated meters.

**Prevention:**  
PROJECT.md already defers full intrinsic suite as primary path. v0.3 = **scale UX** on monocular maps; optional rough FOV default documented as assumption, not OpenCV `calibrateCamera` product.

**Phase ownership:** Scope control at roadmap cut; reject in Phase 2 if plan grows calib3d-primary.

---

### 12. CI requires a real room

**What goes wrong:**  
Calibration tests need physical markers → GHA red or zero coverage; regressions in honesty only found on maker desks.

**Prevention:**  
Pure functions + synthetic depth maps + scripted “known height” geometry in tests (PROJECT.md: no real room). Hardware UAT checklist separate (mirror v0.2 ORT/TRT).

**Phase ownership:** Phase 2 tests from day one; Phase 6 docs checklist.

---

## Minor Pitfalls

| Pitfall | Prevention | Phase |
|---------|------------|-------|
| Footer shows only “Depth: relative” without calib state | Status: kind + calib method/age | 3, 5 |
| Persisting scale as free float without units of scale | Schema: `scale`, `shift?`, `depth_space` enum | 1 |
| Wizard uses detection class “person” height prior without user confirm | Require typed height; priors are defaults only | 3 |
| Clearing depth stage leaves free-space metric labels | Stage off clears free-space (already) + reset calib display | 4 |
| Docs still say “v1 free-space always ordinal” after metric path ships | Update perception-frame.md + safety doc in same milestone | 6 |
| `metric_calibrated` in enum but never reachable in tests | Contract tests promote path end-to-end | 1–4 |
| RTSP reconnection new `camera_id` semantics | Document id stability; mismatch → re-calib | 5 |

---

## Phase ownership map (recommended v0.3 cut)

Suggested phases so each critical pitfall is **prevented before** it can ship:

| Phase | Name | Prevents (pitfall #) | Delivers |
|-------|------|----------------------|----------|
| **1** | **Honesty contracts & calib state model** | #1 silent unit lies; #8 double-scale schema; fingerprint fields for #3 | `CalibrationState` schema; promotion rules; validators; status fields; mode-switch reload policy |
| **2** | **Scale math + in-process apply** | #4 scale math; #9 races; #7 residual reject | Pure fit/apply; Depth product scaled maps; CI synthetic tests |
| **3** | **Live Preview wizard apply/cancel** | #5 UX thrash; #6 copy; #10 feedback | Wizard UI; draft/commit; numeric feedback; non-FSD strings |
| **4** | **Free-space metric path** | #2 free-space breakage | Metric bands when calibrated; ordinal otherwise; smoother reset |
| **5** | **Persist & re-apply on serve** | #3 persistence hazards | Atomic file/profile store; fingerprint invalidation; serve load honesty |
| **6** | **Docs + CI polish** | #6, #12, doc drift | Operator calibration guide; hardware-free suites green; perception-frame updates |

**Ordering rationale:**
1. **Honesty first** — same lesson as v0.2 backend_live; without kind/unit/calib state, every later feature invents lies  
2. **Math before chrome** — wizard without pure fit is a UI that stamps `metric_calibrated` on garbage  
3. **Depth apply before free-space meters** — free-space must consume real scaled maps  
4. **Persist last among features** — wrong persistence is a permanent silent lie; only save what apply already got right  
5. **Docs continuous** but finalize after wire behavior exists  

```
Honesty/state ──► Scale apply ──► Wizard UX
                      │
                      ▼
                 Free-space metric
                      │
                      ▼
                 Persist/re-apply ──► Docs/CI
```

---

## Anti-patterns checklist (PR review)

- [ ] `unit="m"` or free-space `units="m"` while `depth_kind=relative`  
- [ ] Free-space `units="m"` without absolute metric band thresholds  
- [ ] Overloading `nearness_mean` (0..1) as meters / adding fake `distance_m` without kind gate  
- [ ] `set_depth_mode` / calib apply that changes labels without reloading or invalidating model/scale  
- [ ] Global calib file with no `camera_id` + resolution + model fingerprint  
- [ ] Auto-apply on fingerprint mismatch  
- [ ] Per-frame scale re-estimation after commit  
- [ ] Cancel that does not restore draft-only state  
- [ ] Wizard success implying navigation-safe / FSD  
- [ ] Tests that require physical room for default CI  
- [ ] Full chessboard intrinsics as blocker for v0.3 scale UX  
- [ ] Leaving `assemble._units_for_depth_kind` always-ordinal after claiming metric free-space shipped  

---

## What this milestone must not “fix” via shortcuts

| Shortcut | Why it is a pitfall amplifier |
|----------|-------------------------------|
| “Just set unit=m on relative maps” | Silent unit lie (#1) — product-breaking |
| Flip free-space units without metric bands | Free-space lie (#2) |
| Save scale in profile only, ignore camera | Persistence hazard (#3) |
| One bbox click, no residual check | Scale math lie (#4) + overclaim (#6) |
| Ship wizard before pure apply tests | UX thrash + untested honesty (#5) |
| Full OpenCV calib3d as v0.3 gate | Scope creep (#11); delays honest scale |
| Claim stereo/LiDAR parity | FSD thesis breach (#6) |

---

## Question → pitfall → phase (direct answers)

| Question | Answer | Prevent in |
|----------|--------|------------|
| Common mistakes adding monocular metric calib UX? | Unit lies; free-space ordinal→“m” label-only; stale/wrong-camera persist; bad scale math; wizard non-atomic apply; FSD overclaim | Phases 1–6 as table above |
| Silent unit lies? | Yes — highest severity; also latent in mode-switch without model reload | **Phase 1** (+ reload policy in Phase 2 wiring) |
| Free-space breakage? | Yes — percentile nearness ≠ meters; smoother ghosting | **Phase 4** (depends on Phase 2 maps) |
| Persistence hazards? | Yes — wrong camera/resolution/model re-apply is permanent lie | **Phase 5** (key design in Phase 1) |
| Which phase prevents each? | See phase ownership map | — |

---

## Sources

| Source | Confidence | Use |
|--------|------------|-----|
| [PROJECT.md](../PROJECT.md) v0.3 goals / out-of-scope | HIGH | Milestone scope, no FSD, no full intrinsics primary |
| [docs/perception-frame.md](../../docs/perception-frame.md) | HIGH | kind/unit wire honesty |
| [src/sentry_ai/schemas/validators.py](../../src/sentry_ai/schemas/validators.py) | HIGH | relative forbids meters |
| [src/sentry_ai/models/depth/worker.py](../../src/sentry_ai/models/depth/worker.py) | HIGH | mode vs loaded-model hazard |
| [src/sentry_ai/models/depth/mapping.py](../../src/sentry_ai/models/depth/mapping.py) | HIGH | kind from mode only |
| [src/sentry_ai/spatial/free_space.py](../../src/sentry_ai/spatial/free_space.py) | HIGH | ordinal nearness bands |
| [src/sentry_ai/api/assemble.py](../../src/sentry_ai/api/assemble.py) | HIGH | free-space units always ordinal today |
| [tests/test_free_space_bands.py](../../tests/test_free_space_bands.py) | HIGH | metric_estimated still ordinal |
| [tests/test_depth_kind_honesty.py](../../tests/test_depth_kind_honesty.py) | HIGH | relative unit null contract |
| [docs/safety-and-privacy.md](../../docs/safety-and-privacy.md) | HIGH | free-space not interlock; not FSD |
| [docs/export/depth-anything-v2.md](../../docs/export/depth-anything-v2.md) | HIGH | relative vs metric_estimated honesty |
| DAV2 metric_depth README (Hypersim 20 m / VKITTI 80 m) | HIGH | domain + max_depth limits |
| OpenCV camera calibration tutorial | MEDIUM | known size → metric object points; full calib deferred |
| v0.2 PITFALLS (sticky honesty / no silent lies) | HIGH | process pattern transfer |

---

*PITFALLS for v0.3 Metric Depth Calibration UX — monocular scale on Sentry’s relative-depth + ordinal free-space stack. Supersedes the v0.2 Edge Runtime focus of this file for roadmap input; ORT/TRT pitfalls remain historically valid for edge work but are not the focus of this milestone.*
