# Phase 20: Online sample + fit/reject — Pattern Map

**Mapped:** 2026-10-01
**Files analyzed:** `control/calibration_state.py`, `spatial/calibration.py`, `api/routes_calibration.py` (`_read_observed_raw`, sample 409, compute staging), `models/depth/loop.py` (apply-before-store), `config/calibration_store.py` (banned `samples` key), `tests/test_calibration_state.py`, `tests/test_calibration_fit.py`
**Analogs found:** wizard draft vs applied (Phase 13/15) + fit-time reject that does not stage (Phase 14/15 compute)

## File Classification

| New/Modified File | Role | Closest Analog | Match |
|-------------------|------|----------------|-------|
| `src/sentry_ai/control/online_sampler.py` | throttle + window + draft fit | `routes_calibration.compute_calibration` staging rule, without HTTP | role-match |
| `src/sentry_ai/control/calibration_state.py` | anchors + replace/clear draft params | same file: `apply` / `clear_draft` / `clear_applied` | exact |
| `tests/test_online_sampler.py` | synthetic window + reject | `tests/test_calibration_fit.py` + state honesty tests | role-match |
| `tests/test_calibration_state.py` | anchor capture does not enable online | same file: `apply` tests | exact |

**Out of phase:** `models/depth/loop.py`, `spatial/calibration.py` gate constants, `routes_calibration.py`, `routes_preview.py`, `index.html`, `calibration_store.py`, `pyproject.toml`, DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`.

---

## Pattern Assignments

### Consent anchors — EXTEND `apply` / `clear_applied` (20-01)

**Analog:** `clear_applied` already forces online off under the same lock (19-01). Anchor capture is the same kind of bookkeeping, not a new commit path.

```python
@dataclass(frozen=True)
class ConsentAnchor:
    known_meters: float
    point_uv: tuple[float, float] | None = None
    bbox_xyxy: tuple[float, float, float, float] | None = None


def _anchors_from_samples(samples: list[Any]) -> tuple[ConsentAnchor, ...]:
    """Keep samples with known_meters > 0 and exactly one of point_uv or bbox."""
    ...
```

**Rules:**

- On `apply()` success, after the draft params pass `is_valid_calibration_params` and **before** draft samples are cleared: `_consent_anchors = _anchors_from_samples(self._draft_samples)`.
- A raise (`no draft`, invalid draft) leaves anchors, applied, and online untouched.
- `apply()` still does not set `_online_enabled`.
- `apply_params()` does not read or write anchors.
- `clear_applied()` sets `_consent_anchors = ()` along with the existing online-off reset.
- `clear_draft()` does not touch anchors.
- `set_online(False)` does not touch anchors.
- `get_consent_anchors()` returns a copy. No snapshot field.

**Do not:** YAML I/O; invent anchors inside `try_reapply`.

---

### Draft window — EXTEND state, do not add a list (20-01)

```python
def replace_draft_samples(self, samples: list[Any]) -> CalibrationSnapshot:
    """Replace draft samples only. Does not touch params, applied, or online."""

def clear_draft_params(self) -> CalibrationSnapshot:
    """Drop staged params only. Samples, applied, anchors, and online stay."""
```

`clear_draft` remains the Cancel path (params **and** samples). Reject must not call it.

---

### `OnlineSampler.consider` — NEW module (20-01 window, 20-02 fit)

**Analog:** `compute_calibration` calls `fit_scale_median` and `set_draft_params` only when `result.ok`. The sampler is that rule plus a throttle, with no `HTTPException` and no `apply`.

```python
ONLINE_WINDOW_N = 8
ONLINE_MIN_INTERVAL_S = 1.0

@dataclass(frozen=True)
class OnlineSampleResult:
    accepted: bool
    reason: str
    fit_ok: bool | None = None

class OnlineSampler:
    def __init__(self, state: CalibrationState, *, window_n: int = ONLINE_WINDOW_N,
                 min_interval_s: float = ONLINE_MIN_INTERVAL_S) -> None: ...

    def consider(self, depth_map, *, frame_id: int | None, now_s: float,
                 map_space: Literal["raw", "applied"] = "raw") -> OnlineSampleResult: ...
```

**Rules:**

- Check order and reason tokens are the RESEARCH contract (`online_off`, `not_applied`, `no_anchors`, `frame_not_advanced`, `throttled`, `bad_applied_scale`, `empty_roi`, `window_short`, `fit_rejected`, `draft_staged`).
- Failures before accept do not append, do not move `last_accept_s` / `last_frame_id`, and do not fit.
- `map_space="applied"` copies `scale` and `offset` from `get_applied_params()`, then computes outside the state lock. Formula: `(map - offset) / scale`. Non-finite or `scale <= 0` → `bad_applied_scale`.
- Point and bbox reads: finite and `> 0` only, same index clipping as `_read_observed_raw`. Implement the read in `online_sampler.py`. Do not import `routes_calibration` or FastAPI.
- Every anchor must read or the frame is `empty_roi`.
- Each stored sample is a `CalibrationSample` with anchor geometry, new `observed_raw`, `frame_id`, and `note="online"`.
- Window is a deque of accepted frames, maxlen `window_n`. `replace_draft_samples` with the flattened window after each accept.
- 20-01 ships `consider` through `window_short` only (no `fit_scale_median` call). 20-02 adds the fit branch once `len(window) >= window_n`.
- Fit branch: `fit_scale_median(observed, known, method="known_distance")`. `ok=False` → `clear_draft_params`, `fit_ok=False`, reason `fit_rejected`. `ok=True` → `CalibrationParams` copied from the **applied** fingerprint, `set_draft_params`, `fit_ok=True`, reason `draft_staged`.
- Sampler does not call `apply`, `apply_params`, `apply_map`, `set_online`, `set_online_status`, `clear_applied`, `clear_draft`, or any persist helper.
- Own a `threading.Lock` around `consider` so throttle bookkeeping is single-threaded. Do not call back into the sampler from `CalibrationState`.

**Do not:** default `map_space="applied"`; sleep; read `PerceptionStore` inside the sampler (caller passes the array).

---

### Fit reuse — CALL, do not edit (20-02)

**Analog:** `tests/test_calibration_fit.py` already locks absurd scale and residual. Online tests build synthetic pairs and assert the sampler's **staging** behavior, not new math.

A passing window of identical pairs `(observed=raw, known=scale*raw)` stages a draft scale near the applied scale and leaves `get_applied_params().scale` identical.

A failing window (inconsistent known-meters across two anchors, or a ratio `>= MAX_SCALE`) leaves `has_draft_params` false.

---

### Tests

**20-01** (`tests/test_online_sampler.py`, extend `tests/test_calibration_state.py`):

- `OnlineSampler(state).window_n == 8` and `min_interval_s == 1.0`
- `apply()` with two draft samples captures two anchors and leaves `is_online()` false
- `apply()` with params and **no** samples sets anchors to `()`
- `apply()` raise does not replace a previous anchor set
- `apply_params` leaves anchors in place
- `clear_applied` clears anchors and forces online off
- `clear_draft` after a partial window: samples gone, anchors remain, applied remains, online remains
- `set_online(False)`: applied, anchors, and existing draft samples remain; further `consider` returns `online_off` and does not append
- Online off / unapplied / no anchors / same `now_s` / non-increasing `frame_id`: no draft samples
- Eight calls at `now_s = 0..7` with distinct frame ids reach `window_short` through frame 7 and do **not** set draft params (fit is 20-02)
- `map_space="applied"` on `scale * raw + offset` stores `observed_raw` equal to the pre-apply value
- `map_space="raw"` on that same scaled array stores the scaled value (caller bug, documented)
- Monkeypatch `apply` / `apply_params` / `apply_map` to raise; `consider` still returns
- No YAML file appears beside a `tmp_path` that already holds a persisted calibration

**20-02** (same test module):

- Eighth accept of a consistent raw window → `draft_staged`, `has_draft_params`, `fit_ok is True`, applied scale unchanged, `snapshot.scale` still the applied scale, `online_status == "online_draft"`, `promote_kind_unit` unchanged
- Inconsistent anchors or `absurd_scale` → `fit_rejected`, `has_draft_params` false, samples still the window, applied scale unchanged, status still `online_draft`
- A later rejected window clears draft params that an earlier pass staged
- `rg` of `online_sampler.py` has no `apply_params(`, `apply_map(`, `.apply(`, or persist imports
- `models/depth/loop.py` does not import `online_sampler`

---

## Shared Patterns

1. **Draft versus applied** — window and fit params are draft. `snapshot.scale` stays applied.
2. **Cold path** — caller supplies the array and the clock. DepthLoop stays the sole `apply_map` site.
3. **Cancel / Clear / disable** — same matrix as 19-02, plus anchors follow consent (Clear) not the flag (disable) and not the window (Cancel).
4. **TDD** — RED tests, then GREEN. 20-02's fit tests fail against a 20-01 sampler that never fits.
5. **Zero new dependencies / frozen spine.**

---

## Metadata

**Analog search scope:** Phase 15 sample/compute, Phase 14 fit gates, Phase 19 online flag and Cancel/Clear/disable.

**Key planner constraints:** N=8, 1.0 s, pre-apply raw, draft only, same fit, no status enum writes, no DepthLoop hook.
