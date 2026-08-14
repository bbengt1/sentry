# Phase 14: Scale Math + DepthLoop Plug-in - Pattern Map

**Mapped:** 2026-08-12  
**Files analyzed:** 8 (create/extend)  
**Analogs found:** 8 / 8  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/spatial/calibration.py` | utility | transform | `src/sentry_ai/spatial/free_space.py` (pure NumPy post) + Phase 13 validators purity | role-match |
| `src/sentry_ai/control/calibration_state.py` | store | request-response | same file (extend `apply_map`) + `pipeline_state.py` lock | exact |
| `src/sentry_ai/models/depth/loop.py` | loop | stream | same file (post-process before set_depth) | exact |
| `src/sentry_ai/cli.py` | config | construct | same file depth_loop construct + `PipelineState()` inject | exact |
| `src/sentry_ai/spatial/__init__.py` | config | — | same file lazy `__getattr__` | exact |
| `tests/test_calibration_fit.py` | test | — | `tests/test_free_space_bands.py` (pure NumPy) + `test_calibration_validators.py` | role-match |
| `tests/test_calibration_state.py` | test | — | same file (extend apply_map) | exact |
| `tests/test_depth_loop.py` | test | — | same file `FakeDepthWorker` | exact |

**Out of phase (do not pattern-map implementation):** wizard routes, `index.html`, free-space algorithm meter path, YAML persist, DetectionLoop, FrameBus, ORT-TRT factory.

---

## Pattern Assignments

### `src/sentry_ai/spatial/calibration.py` (utility, transform) — NEW

**Analog:** `spatial/free_space.py` — pure NumPy, no FastAPI, no loop imports.

**Imports pattern** (free_space style):
```python
"""Pure monocular scale/affine fit + reject gates (CAL-01/02).

NumPy only — no FastAPI, no DepthLoop, no CalibrationState mutation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
```

**Core pure-result pattern** (prefer frozen dataclass over raising for gate fails):
```python
@dataclass(frozen=True)
class CalibrationFitResult:
    ok: bool
    scale: float = 1.0
    offset: float = 0.0
    residual_rms: float | None = None
    sample_count: int = 0
    method: str = "known_distance"
    reason: str | None = None
```

**Error handling:** Length mismatch / programming errors may `raise ValueError`; product reject gates return `ok=False` with `reason` codes: `insufficient_valid_samples`, `absurd_scale`, `residual_rms_too_high`, `affine_requires_n_ge_2`.

**Do not:** import `CalibrationState`, FastAPI, torch, or mutate global state.

---

### `src/sentry_ai/control/calibration_state.py` (store) — EXTEND

**Analog:** same file + PipelineState lock discipline.

**Target addition:**
```python
def apply_map(self, depth_map: np.ndarray | None) -> np.ndarray | None:
    """Copy-on-write float32 scale*map+offset when applied+valid; else pass-through."""
```

**Imports:** add `import numpy as np` only for apply_map (Phase 13 avoided numpy — Phase 14 needs it here). Keep no FastAPI.

**Lock pattern:** Read scale/offset under lock; compute outside or inside but **never** mutate `_applied_params` in apply_map; always return new array when transforming.

**Pass-through:** `None` → `None`; not applied / invalid → return original map reference OK (or copy — prefer pass-through original when inactive to avoid alloc).

---

### `src/sentry_ai/models/depth/loop.py` (loop) — EXTEND

**Analog:** same file success path ~160–181.

**Constructor pattern today:**
```python
def __init__(self, bus: FrameBus, worker: Any, store: PerceptionStore) -> None:
```

**Target:**
```python
def __init__(
    self,
    bus: FrameBus,
    worker: Any,
    store: PerceptionStore,
    calibration: Any | None = None,  # CalibrationState | None
) -> None:
    ...
    self._calibration = calibration
```

**Success-path insert** (after `result = self._worker.process(frame)`, before `set_depth`):
```python
depth_map = getattr(result, "depth_map", None)
kind = getattr(result, "kind", DepthKind.RELATIVE)
unit = getattr(result, "unit", None)
if self._calibration is not None:
    kind, unit = self._calibration.promote_kind_unit(kind, unit)
    depth_map = self._calibration.apply_map(depth_map)
self._store.set_depth(..., depth_map=depth_map, kind=kind, unit=unit, ...)
```

**Do not:** change bus poll, enable gate, dependency-failure structure, or DetectionLoop analogs. Error products (`depth_map=None`) should still promote only if applied — prefer: still call promote_kind_unit for honesty consistency, apply_map(None)→None.

---

### `src/sentry_ai/cli.py` (construct) — EXTEND

**Analog:** `pipeline_state = PipelineState()` then inject into `create_app`; depth construct:
```python
depth_loop = DepthLoop(bus, depth_worker, store)
```

**Target:**
```python
from sentry_ai.control.calibration_state import CalibrationState
...
calibration_state = CalibrationState()
depth_loop = DepthLoop(bus, depth_worker, store, calibration=calibration_state)
```

**Phase 15 handoff:** optionally pass `calibration_state` into `create_app` later — **not required** in 14 if AppState slot absent; prefer inject into DepthLoop only unless create_app already has a clean kw. Do **not** add YAML load.

---

### `tests/test_calibration_fit.py` (test) — NEW

**Analog:** pure NumPy unit tests (`test_free_space_bands.py`) + reason-code asserts (`test_calibration_validators.py`).

```python
def test_fit_scale_median_recovers_known_scale() -> None:
    rng = np.random.default_rng(0)
    true_scale = 2.5
    observed = rng.uniform(0.5, 3.0, size=5)
    known = true_scale * observed
    result = fit_scale_median(observed, known)
    assert result.ok
    assert result.scale == pytest.approx(true_scale, rel=1e-6)
```

Cover: non-positive reject, absurd scale, residual too high, affine N=1 reject, affine recovers offset.

---

### `tests/test_depth_loop.py` (test) — EXTEND

**Analog:** existing `FakeDepthWorker` + wait_until.

```python
def test_loop_applies_calibration_scale_and_promotes(
    image_frame_factory: Callable[..., ImageFrame],
) -> None:
    bus = FrameBus()
    store = PerceptionStore()
    worker = FakeDepthWorker(value=2.0)
    calib = CalibrationState()
    # stage+apply valid params with scale=3, offset=0, fingerprint, sample_count>=1
    loop = DepthLoop(bus, worker, store, calibration=calib)
    ...
    # assert snap.kind == METRIC_CALIBRATED, unit=="m"
    # assert map mean ~= 6.0
```

Also: inactive calibration leaves RELATIVE + raw value.

---

## Shared Patterns

### 1. Pure NumPy spatial post (no ML imports)

**Source:** `spatial/free_space.py`  
**Apply to:** `spatial/calibration.py`

### 2. Control-plane lock + snapshot

**Source:** `control/calibration_state.py` / `pipeline_state.py`  
**Apply to:** `apply_map` reads under lock

### 3. Loop post-process before store write

**Source:** ARCHITECTURE + DepthLoop success path  
**Apply to:** promote + apply_map insert

### 4. Optional dependency injection with None default

**Source:** serve optional depth/detection loops  
**Apply to:** `DepthLoop(..., calibration=None)`

### 5. FakeDepthWorker synthetic integration

**Source:** `tests/test_depth_loop.py`  
**Apply to:** CAL-03 proofs

### 6. Zero new dependencies

**Source:** ROADMAP lock  
**Apply to:** all Phase 14 files — NumPy already present

### 7. Fit-time reject before draft

**Source:** RESEARCH locked decision #5  
**Apply to:** fitter returns `ok=False`; callers must not stage

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| — | — | All deliverables have in-repo analogs |

**Closest new concept:** residual RMS product gate numbers — locked in RESEARCH; no prior constant file — define module-level constants next to fitter.

---

## Metadata

**Analog search scope:** `spatial/`, `control/calibration_state.py`, `models/depth/loop.py`, `cli.py`, `tests/test_depth_loop.py`, `tests/test_calibration_state.py`, `tests/test_free_space_bands.py`  

**Pattern extraction date:** 2026-08-12  

**Key planner constraints from analogs:**
1. Keep fitter pure in `spatial/`; state only applies.  
2. DepthLoop 3-arg call sites must keep working (`calibration` optional).  
3. Reuse FakeDepthWorker; do not load HF in unit tests.  
4. Do not edit DetectionLoop / FrameBus / free-space algorithm / wizard / YAML.
