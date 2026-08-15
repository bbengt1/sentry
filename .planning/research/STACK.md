# Stack Research — v0.4 Online Re-calibration

**Domain:** Consent-once gated online refine of an already-applied monocular metric scale  
**Project:** Sentry AI — milestone **v0.4 Online Re-calibration (CAL-F03)**  
**Researched:** 2026-08-15  
**Scope:** Stack **additions/changes only** for opt-in online sampling, reused fit/reject, gated `apply_params` auto-commit, session-only persist, honesty status.  
**Out of scope for this file:** YOLO/ORT/TRT/edge factory (v0.2); wizard first-scale math (v0.3 shipped); stereo/SLAM; chessboard-primary; ArUco-required kit.  
**Overall confidence:** **HIGH** for “no new third-party packages” (code-verified reuse).

---

## Decision (one-liner)

**Add zero new pip dependencies.** Implement online re-cal as in-repo control-plane logic on the shipped NumPy fit, `CalibrationState.apply_params`, DepthLoop `apply_map`, PyYAML persist (read/refuse only on auto-commit), FastAPI REST, and static Live Preview toggle.

---

## Recommended Stack

### Core (unchanged — already ship)

| Technology | Version (project pin) | Purpose | Why |
|------------|----------------------|---------|-----|
| Python | **≥3.11** | Runtime | [VERIFIED] `pyproject.toml` |
| FastAPI | **≥0.141,<1** | Online toggle + status | Existing `/api/depth/calibration/*` |
| Pydantic 2 | **≥2.13,<3** | Additive online fields (`extra=forbid`) | Matches wire models |
| PyYAML | **≥6.0.3** | Persist files | Auto-commit does **not** write by default |
| NumPy | **≥2.0,<2.5** | Reuse scale/shift fit + reject | No new fitter |
| OpenCV headless | **≥4.10,<6** | Unchanged capture / overlays | No new marker stack |
| Static Live Preview | `ui/static/index.html` | Online toggle + status | No React |
| `CalibrationState` | in-repo | draft/applied/apply_params/apply_map | v0.3 shipped |

### What to build (in-repo modules, not packages)

| Module | Responsibility | Stack used |
|--------|----------------|------------|
| `CalibrationState` extension | `online` flag + `online_status` | stdlib lock |
| Online sampler helper | Throttle / N-window → draft samples | numpy + existing sample types |
| Auto-commit gate | Five conjuncts → `apply_params` or reject | existing `is_valid_calibration_params` + fit |
| REST toggle | Enable/disable; refuse first-scale invent | FastAPI |
| Tests | Synthetic gate matrix | pytest + httpx (`dev` extra) |

**Hot-path integration (unchanged):**

```
DepthAnythingWorker.process → CalibrationState.apply_map → PerceptionStore.set_depth
```

Online fit **must not** run inside that path.

---

## Calibration math (stack implication)

**Reuse v0.3.** Same scale-only / scale+shift NumPy fit; same reject (`scale <= 0`, non-finite, residual too high, too few samples). **Do not add scipy.**

Online window = N draft samples, not a new estimator. Language/CLIP auto-scale is out of stack.

---

## Persistence (policy, not a new store)

| Rule | Stack meaning |
|------|----------------|
| Path unchanged | `$SENTRY_MODEL_CACHE/calibration/{safe_camera_id}.yaml` |
| Auto-commit | **Session-only** — no `save()` in the gate |
| YAML write | Explicit save / persist:true / documented opt-in only |
| Refuse | Existing fingerprint match; also blocks auto-commit |
| Disable-online | No file delete |
| Clear | Still deletes YAML (v0.3) |

**No platformdirs, no SQLite, no new extra.**

---

## UI wizard stack

Keep static Live Preview. Add a toggle + four-way online status near the existing calibration badge. Do not rebuild the wizard. REST, not a new WS protocol.

---

## Installation

```bash
# No new packages. Depth path still needs the existing depth extra:
uv sync --extra dev --extra depth
```

**`pyproject.toml`:** do **not** add an `online` or `calibration` extra. Do **not** bump 0.1.0.

---

## Alternatives Considered

| Category | Recommended | Alternative | Why not |
|----------|-------------|-------------|---------| 
| Fit | Reuse numpy v0.3 | scipy / sklearn / Kalman | New deps; overkill |
| Commit API | `apply_params` | New `auto_apply_map` | Second apply site |
| Persist | Session-only auto-commit | Write YAML every commit | Persist mismatch lock |
| UI | Static toggle | React panel | Explicitly deferred |
| Sampler | Throttle / N-window | Per-frame refit | Pitfall #5 lock |
| First scale | Apply / try_reapply | Online invent | Consent lock |

---

## What NOT to Use / NOT to Add

| Avoid | Why | Use instead |
|-------|-----|-------------|
| scipy / sklearn / filterpy | One reused linear fit | numpy + v0.3 reject |
| React / npm | Static UI lock | `index.html` toggle |
| Open3D / SLAM / COLMAP | Out of product | Affine refine only |
| New depth network | Not a model milestone | DAV2 + existing scale |
| ORT/TRT depth | PLAT-F03 | Torch/HF depth unchanged |
| platformdirs / sqlite | Persist already YAML | Existing store |
| Implicit YAML on auto-commit | Pitfall #3 lock | Session-only |

---

## Version Compatibility

Same pins as v0.3. Calibration does **not** import torch. No lockfile changes expected.

---

## Confidence Assessment

| Area | Level | Notes |
|------|-------|-------|
| No new pip deps | **HIGH** | All primitives shipped |
| Reuse fit + apply_params | **HIGH** | Code-verified |
| Session-only persist | **HIGH** | Policy, not a package |
| Window/throttle numbers | **MEDIUM** | Plan-phase |

---

## Opinionated defaults for roadmap

1. **Zero new dependencies**
2. **Reuse v0.3 fit/reject + `apply_params` + DepthLoop `apply_map`**
3. **Online default off**
4. **Auto-commit session-only**
5. **No per-frame fit on the hot path**
6. **Do not** add SLAM, React, scipy, chessboard-primary, depth ORT/TRT, or a new extra

---
*Stack research for: Sentry AI v0.4 Online Re-calibration*  
*Researched: 2026-08-15*
