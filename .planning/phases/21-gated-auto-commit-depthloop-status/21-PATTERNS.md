# Phase 21: Gated auto-commit + DepthLoop/status — Pattern Map

**Mapped:** 2026-10-08
**Files analyzed:** `control/online_sampler.py`, `control/calibration_state.py` (`apply_params`, `set_online_status`, `clear_applied`), `control/calibration_persist.py` (`refuse_if_mismatch`), `config/calibration_store.py` (`fingerprints_match`), `models/depth/loop.py` (`_run`, `_live_fingerprint`), `spatial/free_space.py` (`DEFAULT_METRIC_MID_CUT_M`, `_meters_to_nearness`), `spatial/loop.py` (`reset_smoother`), `api/routes_calibration.py` (`_reset_free_space_smoother`, `/apply`), `api/routes_preview.py` (`calibration_online_status`), `cli.py` (`serve` wiring), `tests/test_online_sampler.py`, `tests/test_depth_loop.py`
**Analogs found:** wizard `/apply` (commit + smoother reset), Phase 20 fit branch (stage vs reject), `refuse_if_mismatch` (DepthLoop pre-apply guard)

## File Classification

| New/Modified File | Role | Closest Analog | Match |
|-------------------|------|----------------|-------|
| `src/sentry_ai/control/online_sampler.py` | gates + commit/refuse + horizon helper | Phase 20 `_fit_window`; `/apply` route | exact / role-match |
| `src/sentry_ai/control/calibration_state.py` | `apply_params(expect_applied=)`, `mark_online_rejected` | same file: `apply_params`, `clear_applied` | exact |
| `tests/test_online_auto_commit.py` (new) | gate matrix + horizon + atomicity | `tests/test_online_sampler.py` | exact |
| `tests/test_calibration_state.py` | guarded commit / reject-status honesty | same file | exact |
| `src/sentry_ai/models/depth/loop.py` | optional sampler hook before promote/apply | `refuse_if_mismatch` call in `_run` | exact |
| `src/sentry_ai/cli.py` | attach sampler after `FreeSpaceLoop` exists | `create_app(free_space_loop=...)` wiring | role-match |
| `tests/test_depth_loop_online.py` (new) | hook order, raw map, sole `apply_map`, mismatch | `tests/test_depth_loop.py` calibration tests | exact |

**Out of phase:** `spatial/calibration.py`, `schemas/calibration.py`, `calibration_store.py`, `calibration_persist.py`, `routes_calibration.py`, `routes_preview.py` (read-only; field exists), `index.html`, `pyproject.toml`, DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`.

---

## Pattern Assignments

### Guarded commit — EXTEND `apply_params` (21-01)

```python
def apply_params(
    self,
    params: CalibrationParams,
    *,
    expect_applied: CalibrationParams | None = None,
) -> CalibrationSnapshot:
    with self._lock:
        ok, reason = is_valid_calibration_params(params)
        if not ok:
            raise ValueError(f"invalid calibration params: {reason or 'unknown'}")
        if expect_applied is not None:
            if not self._online_enabled or self._applied_params is not expect_applied:
                raise ValueError("auto_commit_stale")
        self._applied_params = params
        self._draft_params = None
        self._draft_samples.clear()
        if expect_applied is not None:
            self._online_status = "auto_committed"
        return self._snapshot_unlocked()

def mark_online_rejected(self) -> bool:
    """Set online_status=rejected only while online is on."""
```

**Rules:** default `expect_applied=None` is byte-identical in behavior for `/apply`, `try_reapply`, and existing tests. Anchors and the online flag are untouched by both methods.

---

### Horizon helper — NEW pure function (21-01)

```python
from sentry_ai.spatial.free_space import DEFAULT_METRIC_MID_CUT_M

def horizon_median_m(raw_map: np.ndarray, scale: float, offset: float) -> float | None:
    """scale * median(finite > 0 raw) + offset, or None when no valid pixel."""
```

Refuse when `None` (`horizon_unknown`) or `>= DEFAULT_METRIC_MID_CUT_M` (`horizon_refused`). Import the constant; do not copy `3.0`.

---

### Gates + commit — EXTEND `_fit_window` (21-01)

**Analog:** `/apply` = commit then `_reset_free_space_smoother`. Phase 20 = stage only when `ok`.

- `_fit_window(raw_map, live_fingerprint)` receives the raw map `consider` already built.
- `auto_commit=False`: Phase 20 branch unchanged.
- `auto_commit=True`: order and tokens per 21-RESEARCH contract. Build the candidate `CalibrationParams` exactly as 20-02 does (applied fingerprint copy), but do **not** `set_draft_params`. Commit that object with `apply_params(candidate, expect_applied=applied)`.
- Any refuse: `clear_draft_params()` then `mark_online_rejected()`.
- Success: `self._window.clear()`, then `on_auto_commit()` in `try/except Exception` (log, keep commit).
- `OnlineSampleResult` gains no fields; `reason` carries the token.

**Do not:** call `set_online_status` directly; read `_draft_params`; call `apply()`; import `routes_*`, `persist`, or `loop`.

---

### DepthLoop hook — EXTEND `_run` (21-02)

```python
if self._calibration is not None:
    if depth_map is not None:
        live = self._live_fingerprint(frame, depth_map)
        refuse_if_mismatch(self._calibration, live)
        self._consider_online(frame, depth_map, live)   # NEW, raw map
    kind, unit = self._calibration.promote_kind_unit(kind, unit)   # unchanged
    depth_map = self._calibration.apply_map(depth_map)             # unchanged
```

- `_consider_online` no-ops when `self._online_sampler is None`; calls `consider(depth_map, frame_id=frame.frame_id, now_s=time.monotonic(), live_fingerprint=live)`; catches `Exception` and logs once per distinct message.
- `set_online_sampler(sampler | None)` under `self._lock`.
- No import of `OnlineSampler` at module top is required (duck-typed `Any`), matching `calibration: Any`.

### Serve wiring (21-02)

```python
def _attach_online_sampler(depth_loop, calibration_state, free_space_loop) -> None:
    if depth_loop is None or calibration_state is None:
        return
    depth_loop.set_online_sampler(
        OnlineSampler(calibration_state, auto_commit=True,
                      on_auto_commit=free_space_loop.reset_smoother)
    )
```

Called in `serve` right after `free_space_loop = FreeSpaceLoop(store)`. Testable without starting `serve`.

---

### Tests

**21-01** (`tests/test_online_auto_commit.py`, extend `tests/test_calibration_state.py`):

- Success fixture: anchor known 2.0, raw map 1.0, applied scale 2.0 → candidate 2.0, `d_med = 2.0 m`. Eighth accept with matching `live_fingerprint` → `committed`; `online_status == "auto_committed"`; `get_applied_params()` is the new object (scale ≈ 2.0); draft params and window empty; callback called once; `is_online()` still True
- Re-scale success: applied 1.5, raw 1.0, known 2.0 → applied becomes ≈ 2.0
- `fit_rejected` (two anchors 1 m / 10 m) → `rejected`; applied object identical; callback not called
- `horizon_refused`: known 1000 on raw 1.0 (the Phase 20 in-range case) → applied unchanged, `has_draft_params` False, status `rejected`
- Boundary: `d_med` exactly 3.0 → refused; 2.99 → committed
- `horizon_unknown`: raw map of NaN except anchor pixel is impossible (empty_roi first), so test the helper directly on all-NaN / all-≤0 → None
- Offset lock: helper/gate refuses a candidate with `offset=0.5` (unit-test the gate function with a hand-built `FitResult`-like object)
- `fingerprint_unavailable` (`live_fingerprint=None`) and `fingerprint_mismatch` (camera_id / resolution) → `rejected`, applied unchanged
- `expect_applied` stale: monkeypatch `online_sampler.fingerprints_match` with a stub that calls `state.clear_applied()` and returns `(True, None)` → `commit_stale`, `is_applied()` False, status `online_off` (Clear wins)
- `mark_online_rejected` after `set_online(False)` returns False and status stays `online_off`
- `apply_params(params)` without `expect_applied` leaves `online_status` unchanged (wizard/persist path)
- Wizard path untouched: `apply()` with a draft scale 1000 still applies (no horizon gate) and does not change `online_status`
- `auto_commit=False` default: every Phase 20 test in `tests/test_online_sampler.py` passes unmodified
- No YAML: tmp_path bytes unchanged after `committed`; `persist_status` unchanged
- Sampler never calls `apply()` / `apply_map` (monkeypatch raise); `apply_params` called only with `expect_applied`

**21-02** (`tests/test_depth_loop_online.py`):

- Fake worker + applied state + sampler spy: `consider` receives the **raw** worker map (identity / equal values), not the scaled map, and `live_fingerprint` with HxW from the map
- Order: `refuse_if_mismatch` → `consider` → `promote_kind_unit` → `apply_map` (call-order recorder)
- Commit on frame N: the stored depth for frame N uses the new scale and `metric_calibrated` (same frame, no mixed state)
- Sampler raising does not kill the loop; frame stored with last applied scale
- Mismatch frame: `refuse_if_mismatch` clears applied → `consider` returns `online_off`/`not_applied`; persist status `ignored_mismatch`; no commit
- `_attach_online_sampler` with a `FreeSpaceLoop` spy: auto-commit calls `reset_smoother` once; reject does not
- `GET /api/status` reports `calibration_online_status` `auto_committed` then `rejected` while `depth.kind` stays `metric_calibrated` and persist status unchanged
- Sole site: AST/rg test that `apply_map(` is called only in `models/depth/loop.py` under `src/`
- `sampler=None` (default) keeps every existing `tests/test_depth_loop.py` case green

---

## Shared Patterns

1. **One commit door** — `apply_params(expect_applied=)` under the state lock; Clear/disable win races.
2. **Last consented scale is sticky** — every refuse leaves the applied object identical (`is` check in tests).
3. **Raw in, meters out** — sampler sees pre-apply raw; only DepthLoop transforms.
4. **Three planes** — `online_status` vs `depth.kind` vs persist status, each asserted separately.
5. **TDD** — RED then GREEN per plan; injected `now_s`, no sleep, synthetic maps.
6. **Zero new dependencies / frozen spine.**

---

## Metadata

**Analog search scope:** Phase 15 `/apply`, Phase 17 `refuse_if_mismatch`, Phase 19 status plane, Phase 20 sampler.

**Key planner constraints:** six conjuncts, horizon `scale*median(raw)+offset >= 3.0` refuses, scale-only, guarded `apply_params`, status = last decision, DepthLoop sole `apply_map`, smoother reset via callback, no YAML.
