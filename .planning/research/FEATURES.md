# Feature Landscape: v0.3 Metric Depth Calibration UX

**Domain:** Monocular depth scale calibration UX for maker robotics (camera-only)  
**Milestone:** Sentry AI v0.3 Metric Depth Calibration UX  
**Researched:** 2026-08-11  
**Confidence:** HIGH for Sentry contracts + maker UX table stakes; MEDIUM for academic auto-scale methods (out of core path)

## Scope Lock (do not expand)

| In scope | Out of scope this milestone |
|----------|----------------------------|
| Live Preview **calibration wizard** (known heights / floor markers) | Full camera **intrinsic** suite (chessboard photogrammetry as primary) |
| Fit scale (and optional shift) from user ground truth | Stereo / multi-view depth |
| Persist + re-apply per-camera (or per-profile) at `sentry serve` | Live ORT/TRT for depth models |
| Honest `depth_kind` / units: relative default; meters only when calibrated | ROS2 metric TF package |
| Free-space near-field distances use metric when calibrated | Language/CLIP auto-scale as product path |
| Docs + CI-safe tests (synthetic frames; no real room) | Vehicle-grade / FSD accuracy claims |

**Shipped baseline (v1.0 + v0.2):** Relative DAV2 Small depth + optional `metric_indoor` / `metric_outdoor` heads labeled **`metric_estimated`**; free-space near-field bands with **ordinal** units; Live Preview depth badge honesty; wire forbids relative + `unit: "m"`; `DepthKind.METRIC_CALIBRATED` enum exists but has no calibration path yet; free-space still forces ordinal even for estimated metric (`assemble.py`).

---

## How Metric Calibration Works (ecosystem reality)

Monocular relative depth is **scale-ambiguous** (classically affine in inverse-depth: scale + shift). Products that feel honest do **not** invent meters from relative maps. They either:

1. **Ship domain metric heads** (DAV2 Hypersim indoor / VKITTI outdoor) → approximate meters, domain-sensitive → Sentry already maps these to `metric_estimated`.  
2. **Anchor with user ground truth** (known object size, tape distance, floor marker) → fit a global scale (and optionally shift) on the current depth map → label **`metric_calibrated`**.  
3. **Sensor fusion** (LiDAR/stereo/ARKit) — **out of product thesis** for Sentry.

### Canonical maker procedure (what good UX encodes)

```
1. Depth already running (relative or metric_estimated)
2. User starts wizard in Live Preview
3. Choose method: known height | known distance | floor marker
4. Place object / tape in view; freeze or use live frame
5. Mark region(s) in image (box / two points / line on floor)
6. Enter known physical value in meters (or cm with clear unit)
7. System samples depth at mark(s), solves scale (and optional shift)
8. Preview: depth badge flips to metric_calibrated (m); optional sample readout
9. Apply (persist) or Cancel (revert)
10. On next serve: load cal for this camera_id / profile automatically
```

**Math makers expect under the hood (not in the UI):**  
For a known distance \(d_{\mathrm{true}}\) at a pixel with relative depth \(z_{\mathrm{rel}}\):

- Simple scale (metric head already roughly metric): \(d = s \cdot z\) with \(s = d_{\mathrm{true}} / z_{\mathrm{rel}}\).  
- Affine in inverse depth (relative / disparity-like maps): \(d = 1 / (\alpha z_{\mathrm{inv}} + \beta)\).  
- Multi-point: least-squares over 2–N anchors; show residual / confidence.

**Opinionated Sentry choice:** Prefer **user-anchored scale (optional shift)** on the **current depth product**, promote kind to `metric_calibrated`, persist params — **not** a new network fine-tune and **not** language priors. Wizard complexity stays Med; reliability and honesty stay high.

**Confidence:** HIGH for scale-ambiguity + user-anchor pattern (MiDaS/DAV2 literature + Sentry contracts); MEDIUM for exact affine-vs-scale default (phase research should pick one formula and test on synthetic maps).

---

## Expected Maker Behaviors

What hobbyist / student / small-team roboticists actually do when given monocular depth:

| Behavior | Implication for product |
|----------|-------------------------|
| “How far is that obstacle in meters?” is the first metric ask | Free-space + depth must surface meters only after calibration |
| Will put a **door frame, chair, person, or tape measure** in frame once | Wizard must accept known **height** and known **distance** paths |
| Expects calibration to **stick across restarts** for the same camera mount | Persist per `camera_id` (and/or profile); re-apply at serve |
| Recalibrates after **remount / different room / lens change** | Clear “Clear calibration” + re-run wizard; never silent stale cal |
| Trusts UI badges more than docs | Live Preview, snapshot, `/v1` must **never** disagree on kind/units |
| Accepts “approximate hobby accuracy” if labeled | Copy: calibrated ≈ not vehicle-grade; show residual if multi-point |
| Prefers **wizard over CLI math** for first success | Primary path is Live Preview; headless file/API is secondary |
| Uses synthetic/file sources in CI and laptop bring-up | All cal logic must run on synthetic depth without a real room |
| Headless robot deploy still needs metric | Load persisted cal without UI; status reports calibrated vs not |
| Will mis-enter units (cm vs m) | Explicit unit control; sanity bounds (e.g. reject 200 m “chair height”) |
| May calibrate on `metric_estimated` or `relative` | Both supported; resulting kind is always `metric_calibrated` when user anchors |

---

## Table Stakes

Features makers expect once Sentry claims “metric calibration UX.” Missing any of these makes the milestone feel incomplete or dishonest.

| Feature | Why Expected | Complexity | Notes / Sentry dependency |
|---------|--------------|------------|---------------------------|
| **Live Preview calibration wizard** | Primary maker surface already exists; CLI-only cal fails the product thesis | Med | Extend `ui/static/index.html` + new `/api/calibration/*` routes; reuse MJPEG + status poll pattern |
| **Known object height path** | Universal maker ground truth (door ~2.0 m, person, box) | Med | User draws vertical extent or bbox; enter height_m; sample depth along object |
| **Known distance / floor marker path** | Tape measure to wall / floor mark is the other common anchor | Med | Click point or short segment; enter distance_m; sample depth at mark |
| **Apply / Cancel with visual feedback** | Calibration is a mutation; reversible preview is table stakes | Low–Med | Staging params until Apply; Cancel restores prior product labeling |
| **Promote to `metric_calibrated` + `unit: "m"`** | Enum already exists; honesty contract requires distinct kind | Med | Wire `DepthPayload.kind`; depth worker or post-process scale layer; validators already forbid relative+m |
| **Never label relative as meters** | Shipped v1 honesty; calibration must not regress | Low | Keep badge copy + Pydantic validators; tests for kind/unit matrix |
| **Free-space uses metric when calibrated** | Obstacle “nearness” without meters is half a product | Med–High | Today free-space is always ordinal (`free_space.py`, `assemble._units_for_depth_kind`); need meter bands or `distance_m` **only** when kind is calibrated |
| **Persist calibration** | Restart without re-wizard is expected | Med | JSON/YAML under config dir keyed by `camera_id` (+ optional profile); schema versioned |
| **Re-apply on `sentry serve`** | Headless robots cannot open Live Preview every boot | Med | Load at depth/free-space construction; status shows loaded cal fingerprint |
| **Clear / invalidate calibration** | Remount / wrong room must be recoverable | Low | Explicit clear API + UI; drop kind back to relative or metric_estimated |
| **UI ↔ snapshot ↔ `/v1` single truth** | Dual truth is a trust killer | Low–Med | Same store product after apply; no client-side-only meter labels |
| **Status / badge honesty** | Operators need “relative / estimated / calibrated” at a glance | Low | Extend existing depth badge in `index.html` + `/api/status` |
| **Sanity checks on user input** | Bad entries create silent wrong meters (worse than ordinal) | Low–Med | Bounds, polarity checks, optional multi-point residual threshold |
| **CI-safe tests without physical room** | Milestone requires automated tests | Med | Synthetic depth maps with planted scale; inject cal params; no camera |
| **Operator docs for the flow** | Makers fail open-ended math; need screenshots + failure modes | Low–Med | New `docs/` calibration guide; link from edge/serve hub |

### Table-stakes quality bar (non-negotiable)

- **Contract stability:** `relative` never has `unit: "m"`; meters only with `metric_estimated` or `metric_calibrated`.  
- **No dual truth:** Live Preview labels == `/v1/snapshot` depth/free-space kinds and units for the same product snapshot.  
- **Calibrated ≠ vehicle-grade:** UI and docs say approximate / hobby monocular.  
- **Perception-only:** No `safe_to_drive` / distance-based interlocks from calibration.  
- **Synthetic-first tests:** Unit + API tests do not require a real scene.

---

## Differentiators

Features that turn “another scale-factor CLI flag” into a product-shaped maker calibration experience on Sentry’s existing stack.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Guided wizard, not raw scale slider** | Makers succeed without understanding inverse-depth affine math | Med | Multi-step panel on Live Preview; method picker + mark + enter value + preview |
| **Two first-class anchor methods (height + distance)** | Covers indoor robot benches and hallway tape tests | Med | Prefer both in MVP; third method (ArUco) can wait |
| **Per-`camera_id` persistence with re-apply** | Multi-cam hooks already in schema; single active cam still benefits | Med | File path or profile field; fingerprint in status |
| **Immediate free-space meterization when calibrated** | Depth cal that does not move free-space feels unfinished | Med–High | Extend `FreeSpacePayload.units` to `"m"`; optional obstacle `distance_m` only under calibrated kind |
| **Staging preview before Apply** | See sample distance / band change before committing | Med | Soft-apply on overlay; hard-apply writes store + disk |
| **Residual / confidence readout (multi-point)** | Builds trust; flags bad marks | Med | If N≥2 anchors, show fit residual; warn if high |
| **Works on relative *and* metric_estimated bases** | Makers may start from either mode | Low–Med | Cal params relative to current depth product; document which base was used |
| **Headless re-apply without UI** | Robot deploy path parity with Live Preview | Med | Serve loads cal file; `/api/status` reports calibration state |
| **Honest triad of kinds in all surfaces** | Differentiates from tools that print “depth (m)” on MiDaS | Low | Badge + docs + wire already partially there; complete free-space path |
| **Synthetic demo path in docs** | First success without arranging furniture | Low | Scripted synthetic source + planted geometry for tutorial |

### Differentiator priority for v0.3 story

1. Live Preview wizard with known height **and** known distance  
2. Apply → `metric_calibrated` + meters on depth products  
3. Free-space near-field uses meters when calibrated (ordinal otherwise)  
4. Persist + re-apply per camera/profile at serve  
5. Staging preview + clear cal + residual if multi-point  
6. Docs + synthetic CI  

---

## Anti-Features

Features to **explicitly not build** in v0.3 (or ever as core without a new milestone).

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Claim vehicle-grade / FSD metric accuracy** | Monocular + hobby anchors cannot support it; product liability | Explicit approximate language; residual display |
| **Chessboard intrinsic calibration as primary path** | Deferred in PROJECT.md; high UX cost; not needed for global scale | Optional later; scale anchors first |
| **Stereo / multi-view / SLAM scale recovery** | Different product; multi-cam fusion still extension-only | Single-camera user anchors |
| **Language / CLIP auto-scale as default** | Research-grade, caption-noisy, hard to test honestly (RSA-style) | Human-entered known size only |
| **Silent promotion of `metric_estimated` → `metric_calibrated`** | Estimated heads are domain-biased, not user-calibrated | Only user apply sets calibrated |
| **Labeling relative depth with `m` or `distance_m`** | Violates FOUND-03 / validators / trust | Keep forbid; free-space stays ordinal until calibrated |
| **Safety interlocks (`safe_to_drive`, stop if obstacle < 1 m)** | Perception-only boundary | Consumers own control |
| **Online continuous auto-recalibration without consent** | Scale drift confuses robots; hard to debug | Explicit wizard re-run; optional later “recheck” button |
| **Requiring LiDAR / RealSense for calibration** | Breaks camera-only thesis | Tape / known object only |
| **Fine-tuning DAV2 weights in the wizard** | Hours of GPU, non-maker UX, CI nightmare | Global scale/shift on frozen model |
| **Bulk `depth_map` meters on WebSocket** | Bandwidth; not needed for robot near-field | Metadata + free-space cues; binary later if needed |
| **ArUco / AprilTag as *required* marker** | Extra print step blocks first success | Optional later; height/distance first |
| **Per-frame independent scale (no persistence)** | Feels broken after restart | Persist params |
| **Global single cal shared blindly across all cameras** | Wrong scale on second USB cam | Key by `camera_id` |
| **Hiding uncalibrated state** | “Looks metric” is the failure mode of the whole domain | Loud relative / estimated badges |
| **Changing free-space method name for marketing** | `near_field_bands` is honest | Keep method; change units only when calibrated |

---

## Feature Dependencies (on shipped depth / free-space / UI)

```
FrameBus + DepthLoop + DepthAnythingWorker (v1)
    → depth product (map in-process, kind, unit)
        → Live Preview colormap + depth_kind badge (v1)
        → Free-space near_field_bands (v1, ordinal only)
        → PerceptionFrame /v1 (v1)

NEW v0.3 layer (conceptually):
  CalibrationService / scale applicator
    depends on: live depth product (relative OR metric_estimated)
    produces: scale (+ optional shift) params + kind=metric_calibrated
    feeds: depth post-process OR worker config
    feeds: free-space meter path when calibrated
    feeds: persist file → serve re-apply
    feeds: Live Preview wizard + status

Does NOT depend on: ORT/TRT backends, open-vocab, ROS2, multi-cam fusion
Must NOT break: relative honesty, perception-only boundary, keep-latest loops
```

| Existing component | Dependency type | v0.3 impact |
|--------------------|-----------------|-------------|
| `DepthKind` enum | **Reuse** | `METRIC_CALIBRATED` becomes live path |
| `DepthPayload` + validators | **Reuse / extend** | unit `"m"` only with estimated/calibrated |
| `kind_for_mode` / depth_mode API | **Keep** | estimated modes remain; cal is orthogonal |
| Depth colormap MJPEG | **Reuse** | Colormap may stay relative-normalized; **labels** change |
| Free-space `near_field_bands` | **Extend** | Meter bands / optional `distance_m` when calibrated |
| `assemble_perception_frame` | **Extend** | `_units_for_depth_kind` currently always ordinal — must change for calibrated |
| Live Preview `index.html` | **Extend** | Wizard panel + badge states |
| `/api/depth/config` | **Adjacent** | Do not overload; prefer `/api/calibration/*` |
| Profiles / `camera_id` | **Keying** | Persist map keyed by camera (+ optional profile) |
| Headless `--no-ui` | **Support** | Load cal without wizard; no HTML dependency |
| Synthetic / file sources | **Test harness** | CI plants known geometry |

### Suggested wire deltas (feature-level, not full schema design)

| Surface | Uncalibrated (today) | After successful Apply |
|---------|----------------------|------------------------|
| `depth.kind` | `relative` or `metric_estimated` | `metric_calibrated` |
| `depth.unit` | `null` or `"m"` (estimated) | `"m"` |
| `free_space.units` | `"ordinal"` | `"m"` (only if calibrated) |
| `free_space.depth_kind` | matches depth | `metric_calibrated` |
| Obstacle fields | `nearness_*` only | Keep nearness; **optional** additive `distance_m` if schema allows later — or meterized band cuts only in v0.3 |
| Status | depth_kind badge | + `calibration: applied \| none` + age/fingerprint |

**Opinion:** Prefer **minimal schema growth** in v0.3: flip kinds/units and meterize free-space band cuts when calibrated; defer additive `distance_m` on every obstacle if it expands validators too much — but **some** robot-facing meter signal is table stakes.

---

## Complexity Notes

| Work item | Complexity | Why |
|-----------|------------|-----|
| Scale fit (1-point known distance) | Low | Closed-form; pure numpy |
| Height path (vertical extent + pinhole height) | Med | Needs careful sampling (median of object strip); optional weak intrinsics assumption |
| Affine inverse-depth fit (multi-point) | Med | Standard least-squares; edge cases on bad masks |
| Wizard UI in static Live Preview | Med | Multi-step state machine in existing HTML/JS; no React rewrite |
| Persist + load + fingerprint | Low–Med | File I/O + schema version; serve wiring |
| Free-space metric bands | Med–High | Band cuts today are ordinal nearness thresholds; metric needs distance thresholds or scaled nearness — easy to get wrong |
| Honesty matrix tests | Med | Combinatorial: relative / estimated / calibrated × UI / snapshot / free-space |
| Headless re-apply | Low | Load path without UI |
| Docs + synthetic tutorial | Low–Med | Content work; high leverage |

**Highest risk feature:** free-space meterization without lying — ordinal nearness polarity + ROI heuristics were designed without meters. Phase research should lock: *convert depth map to meters first, then re-derive nearness from metric depth*, rather than “multiply ordinal by a constant.”

---

## MVP Recommendation

**Prioritize (must ship for milestone claim):**

1. **Known distance** wizard path (tape / floor mark) — simplest correct scale  
2. **Known height** wizard path (door / person / box) — maker-expected second path  
3. **Apply / Cancel** + Live Preview badge → `metric_calibrated (m)`  
4. **Persist + re-apply** per `camera_id` at serve  
5. **Free-space honesty:** meters when calibrated; ordinal when not; never relative-as-meters  
6. **Clear calibration** + status fingerprint  
7. **CI synthetic tests** + operator docs  

**Defer (nice / next milestone):**

| Feature | Reason |
|---------|--------|
| Multi-point residual UI polish | Ship 1-point first; residual is differentiator #2 |
| ArUco automatic detection | Extra dependency; print friction |
| Chessboard intrinsics | Explicit out of scope |
| Language auto-scale | Research, not maker-trustworthy |
| Obstacle `distance_m` on every cue | Prefer band/unit flip first if schema churn is high |
| Continuous online re-cal | Consent + drift issues |
| Metric free-space cut sliders in meters in UI | Can keep ordinal cut sliders until calibrated path is solid |

---

## Phase Ordering Hints (for roadmap)

1. **Contracts & applicator** — scale/shift model, kind promotion, validators, synthetic unit tests  
2. **Persist / load / serve re-apply** — file schema, status fingerprint, headless path  
3. **Live Preview wizard** — mark + enter + staging preview + apply/cancel  
4. **Free-space metric path** — only after depth product is honestly calibrated  
5. **Docs + integration tests** — synthetic E2E; operator guide  

**Ordering rationale:** Free-space meters **depend** on calibrated depth product; wizard **depends** on applicator; persist can parallelize with wizard once contract is fixed. Do not build UI labels before store/API kind flips — dual truth is the domain’s worst pitfall.

**Research flags:**

| Topic | Flag |
|-------|------|
| Affine-in-inverse vs pure scale for relative DAV2 | **Needs phase research** (map polarity + formula) |
| Free-space band semantics in meters | **Needs phase research** (threshold design) |
| Height path geometry (intrinsics assumptions) | **Needs phase research** (or document weak-pinhole) |
| Persist path (file vs profile field) | Standard; low research |
| Wizard step UX | Standard maker patterns; low research |

---

## Sources

| Source | Use | Confidence |
|--------|-----|------------|
| Sentry `PROJECT.md` v0.3 goals | Scope lock | HIGH |
| `docs/perception-frame.md`, `schemas/enums.py`, `schemas/perception.py` | Kind/unit/free-space contracts | HIGH |
| `models/depth/mapping.py`, `api/routes_depth.py` | Existing relative vs metric_estimated modes | HIGH |
| `spatial/free_space.py`, `api/assemble.py` | Ordinal free-space; calibrated path not wired | HIGH |
| Depth Anything V2 metric_depth README + Context7 | Metric heads = domain estimated meters, not user-cal | HIGH |
| HF monocular depth guide (relative vs absolute; scale/shift) | Domain fundamentals | HIGH |
| arXiv:2601.01457 (language-as-prior scale recovery) | Academic auto-cal; **anti-feature for core** | MEDIUM (research only) |
| Phase 4 UI-SPEC / research (depth honesty badges) | UI patterns to extend | HIGH |

---

*Research for v0.3 Metric Depth Calibration UX — features only. Supersedes v0.2 Edge Runtime FEATURES.md as the active research feature landscape for roadmap input.*
