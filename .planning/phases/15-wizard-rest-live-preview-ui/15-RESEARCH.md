# Phase 15: Wizard REST + Live Preview UI - Research

**Researched:** 2026-08-13
**Domain:** In-memory calibration wizard REST + static Live Preview panel on top of Phase 14 fit/apply
**Confidence:** HIGH

## Summary

Phase 14 shipped pure fit/reject (`spatial/calibration.py`) and the DepthLoop plug-in (`CalibrationState.apply_map` after `worker.process`, before `set_depth`). CLI already constructs one `CalibrationState` and injects it into `DepthLoop`. **No wizard REST, no `create_app` inject, no Live Preview panel.** [VERIFIED: `cli.py` `calibration_state = CalibrationState()` + `DepthLoop(..., calibration=calibration_state)` only; `create_app` / `AppState` have no `calibration_state` kw; `_draft_samples` exists on `CalibrationState` but has no public add/list API; `index.html` depth badge already labels `metric_calibrated (m)` from `/api/status` `depth_kind` only.]

Phase 15 must deliver:

1. **REST control plane** (WIZ-01/02/04, OPS-01 backend) — freeze/sample/fit/apply/cancel + additive `/api/status`; same `CalibrationState` instance as DepthLoop.
2. **Static wizard panel** (WIZ-03, OPS-01 UI) — extend `ui/static/index.html`; never locally claim `metric_calibrated`.

**Primary recommendation:** Handlers only snapshot store depth and mutate `CalibrationState`. **Cancel = `clear_draft` only.** Explicit **Clear** calls `clear_applied`. Sample **only when inactive**. Fit reuses `fit_scale_median` / `fit_affine_lstsq`; only `ok=True` may `set_draft_params`. Live stream `depth_kind` stays base until `apply()`. Zero new pip deps; no YAML (17); no free-space meters (16).

---

## Locked Decisions (authoritative)

| # | Decision | Value |
|---|----------|-------|
| 1 | Cancel vs Clear | **Cancel = `clear_draft` only** (discard staging). Explicit **Clear** for `clear_applied`. ROADMAP WIZ-02 “Cancel leaves no calibrated state” means cancel-before-apply never promotes; it does **not** wipe an already-applied calibration |
| 2 | Sample while applied | **Forbidden.** Sample only when inactive. Sampling while applied → **409** (`calibration_already_applied`) to avoid double-scale |
| 3 | Sample core | `{point_uv \| bbox_xyxy, known_meters}` → `observed_raw` from store `snapshot_depth()` (or freeze pin). Handlers **never** call `worker.process` or open cameras |
| 4 | Known distance vs height | **Known-distance primary** (`known_meters` is distance along the depth axis). Height→meters helper **optional**, documented weak-FOV pinhole only — not calibrated intrinsics |
| 5 | Fit | Reuse `fit_scale_median` / `fit_affine_lstsq`. Only `ok=True` may `set_draft_params`. Rejected fit → **422**, **no draft** |
| 6 | Preview vs live stream | Preview numbers from draft / `CalibrationFitResult`. Live stream `depth_kind` stays **base** until `apply()` (DepthLoop sole writer) |
| 7 | Same instance | CLI already has one `CalibrationState` for DepthLoop. `create_app(..., calibration_state=)` and `AppState` **must get that same object** |
| 8 | REST (in-memory only, no YAML) | GET snapshot; POST freeze; POST sample; DELETE samples; POST compute; POST apply; POST cancel → `clear_draft`; POST clear → `clear_applied`; GET `/api/status` additive: `calibration_active`, scale, method, sample_count, camera_id |
| 9 | UI | Wizard panel on existing `index.html`; **never locally claim** `metric_calibrated`; badge may use status fields |
| 10 | Constraints | Zero new pip deps (no React); freeze DetectionLoop / FrameBus / ORT-TRT; synthetic ASGI tests + FakeDepthWorker; no YAML persist (17); no free-space meters (16); `extra=forbid` bodies; **503** if `calibration_state` missing |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Rationale |
|------------|--------------|-----------|
| Sample list + draft/apply/cancel | `control/calibration_state.py` | Already owns `_draft_samples`, `set_draft_params`, `clear_draft`, `apply`, `clear_applied` |
| Fit/reject | `spatial/calibration.py` | Phase 14; routes call, never reimplement |
| Optional height→distance | `spatial/calibration.py` thin helper | Documented FOV; pairs API stays core |
| REST | `api/routes_calibration.py` | Analog: `routes_pipeline.py` / `routes_depth.py` — no inference |
| App inject | `api/app.py` + `api/deps.py` + `cli.py` | Same object as DepthLoop |
| Status honesty | `api/routes_preview.py` `/api/status` | Additive fields; never invent kind |
| Wizard chrome | `ui/static/index.html` | Static; poll status; call REST |
| YAML persist | Phase 17 | Out of phase 15 |
| Free-space meters | Phase 16 | Out of phase 15 |

---

## Standard Stack

Zero new packages. FastAPI + Pydantic 2 (`extra=forbid`) + existing NumPy fitters + static HTML/JS. Tests: `fastapi.testclient.TestClient` + `PerceptionStore.set_depth` + FakeDepthWorker (handlers must never call `process`).

```bash
uv sync --extra dev
```

---

## Architecture Patterns

```
CLI serve
  CalibrationState()  ──▶ DepthLoop(..., calibration=state)
                      └──▶ create_app(..., calibration_state=state)
                                │
                                ▼
                     routes_calibration  (cold path)
                       snapshot_depth() → observed_raw
                       fit_* → set_draft_params  (ok=True only)
                       apply() / clear_draft() / clear_applied()
                                │
                                ▼
                     DepthLoop hot path (unchanged Phase 14)
                       worker.process → promote → apply_map → set_depth
```

Wizard: idle → sample (inactive only) → compute (draft) → preview numbers → Apply (commit) | Cancel (drop draft) | Clear (drop applied).

Anti-patterns: UI claiming calibrated before `/api/status` says so; Cancel wiping applied; sampling on scaled maps; handlers calling `worker.process`; YAML I/O; free-space unit flip; React; dual `CalibrationState` instances.

---

## Common Pitfalls

1. **Cancel vs Clear confusion** — WIZ-02 wording looks like Cancel always restores uncalibrated. Lock: Cancel never promotes a draft; Clear is the wipe-applied control.
2. **Double-scale** — sampling while applied fits against already-scaled maps. 409 + require Clear first.
3. **Draft claiming meters** — compute must not write PerceptionStore or change `depth_kind` on `/api/status` / `/api/snapshot`.
4. **Split CalibrationState** — CLI injects DepthLoop only today; AppState default None would 503 the wizard or apply to a different object. Same instance required.
5. **Height-as-bbox-pixels** — without FOV, height is not distance. Optional helper documents `d = (H * fy) / h_px` with default HFOV 70°.
6. **Rejected fit staged** — Phase 14 lock: `ok=False` must not `set_draft_params`.
7. **Scope creep** — YAML, free-space meters, DetectionLoop/FrameBus/ORT-TRT, React, scipy.

---

## Code Examples

See `15-PATTERNS.md` for full target APIs. Summary:

- `CalibrationSample` Pydantic (`extra=forbid`): `point_uv` or `bbox_xyxy`, `known_meters`, filled `observed_raw`, `frame_id`
- `CalibrationState.add_draft_sample` / `get_draft_samples` (copy) — `_draft_samples` already exists
- Routes: `_require_calibration_state` → 503; sample reads freeze pin or `snapshot_depth()`
- `fit_scale_median(observed, known)` then `set_draft_params` only if `result.ok`
- POST cancel → `clear_draft()`; POST clear → `clear_applied()`
- `/api/status` adds `calibration_active` (= applied+valid), `calibration_scale`, `calibration_method`, `calibration_sample_count`, `calibration_camera_id`

Height helper (optional):

```
fy = (width_px / 2) / tan(radians(hfov_deg) / 2)   # default hfov_deg=70
distance_m = (known_height_m * fy) / bbox_height_px
```

Reason / HTTP: `calibration_already_applied` 409; `insufficient_valid_samples` / `absurd_scale` / `residual_rms_too_high` / `affine_requires_n_ge_2` 422; missing state 503; extra body fields 422.

---

## Open Questions (RESOLVED)

1. Cancel wipe applied? → **No.** Cancel = `clear_draft`. Clear = `clear_applied`.
2. Sample while applied HTTP? → **409** (conflict), not silent resample.
3. Height path? → Optional FOV helper; primary is `known_meters` distance.
4. Freeze? → Optional in-memory pin of last `snapshot_depth()`; samples prefer pin; no disk.
5. Dual state objects? → **Forbidden.** One instance to DepthLoop + `create_app`.
6. Persist on apply? → **No** (Phase 17).
7. Affine vs median in wizard? → Default median; compute body may request `affine` when N≥2.

---

## Validation Architecture

| Req ID | Behavior | File |
|--------|----------|------|
| WIZ-01 | Sample + stage fit before commit | `tests/test_api_calibration.py` |
| WIZ-02 | Apply commits; Cancel drops draft only; Clear drops applied | `tests/test_api_calibration.py` |
| WIZ-03 | Wizard shows count / residual / relative vs calibrated | `index.html` + `tests/test_api_preview.py` |
| WIZ-04 | Draft never claims `metric_calibrated` on snapshot/status kind | `tests/test_api_calibration.py` |
| OPS-01 | Status + Live Preview show active vs relative | `routes_preview.py` + `index.html` |

Quick: `uv run pytest tests/test_api_calibration.py tests/test_api_preview.py tests/test_cli_calibration_inject.py tests/test_calibration_state.py tests/test_calibration_fit.py tests/test_depth_loop.py -q`

---

## Security Domain

| Threat | Mitigation |
|--------|------------|
| UI invents calibrated meters | Badge/kind only from `/api/status`; draft never writes store |
| Cancel silently clears applied | Cancel = `clear_draft` only; explicit Clear |
| Double-scale samples | 409 when applied |
| Absurd / high-residual draft | Fit-time `ok=False` → 422, no `set_draft_params` |
| Handler inference / cameras | Never `worker.process` / VideoCapture |
| Extra/motor fields | `extra=forbid` |
| New deps supply chain | Zero new packages (T-15-SC) |

---

## Phase Requirements

| ID | Research Support |
|----|------------------|
| WIZ-01 | Sample + compute draft REST |
| WIZ-02 | Apply / Cancel (`clear_draft`) / Clear (`clear_applied`) |
| WIZ-03 | Static panel: count, residual, labels |
| WIZ-04 | Draft does not promote live kind |
| OPS-01 | `/api/status` additive + badge/panel |

### Must ship
1. `create_app` / `AppState` / CLI same `CalibrationState` instance
2. `routes_calibration.py` freeze/sample/compute/apply/cancel/clear
3. Additive `/api/status` calibration fields
4. `CalibrationSample` + draft-sample APIs on `CalibrationState`
5. Static wizard on `index.html`
6. Synthetic ASGI + FakeDepthWorker tests

### Must not ship
YAML persist; free-space `units="m"` algorithm; DetectionLoop/FrameBus/ORT-TRT edits; React/npm; scipy; handler-side `worker.process`; locally invented `metric_calibrated`.

---

## RESEARCH COMPLETE

**Phase:** 15 - Wizard REST + Live Preview UI
**Confidence:** HIGH

Key findings: Cancel ≠ Clear; sample only when inactive; same CalibrationState for loop + app; fit reuse with ok-gated draft; UI never claims calibrated locally; in-memory REST only.

Ready for planning.
