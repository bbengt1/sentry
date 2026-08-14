# Phase 13: Honesty Contracts & CalibrationState - Pattern Map

**Mapped:** 2026-08-11  
**Files analyzed:** 11 (create/extend)  
**Analogs found:** 11 / 11  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/schemas/validators.py` | utility | transform | `src/sentry_ai/schemas/validators.py` (extend in place) | exact |
| `src/sentry_ai/schemas/perception.py` | model | request-response | `src/sentry_ai/schemas/perception.py` (`DepthPayload` validator) | exact |
| `src/sentry_ai/schemas/calibration.py` | model | request-response | `src/sentry_ai/schemas/perception.py` + `frame.py` | role-match |
| `src/sentry_ai/control/calibration_state.py` | store | request-response | `src/sentry_ai/control/pipeline_state.py` | exact |
| `src/sentry_ai/state/perception_store.py` | store | CRUD | `src/sentry_ai/state/perception_store.py` (`set_depth`) | exact |
| `src/sentry_ai/control/__init__.py` | config | — | `src/sentry_ai/control/__init__.py` | exact |
| `src/sentry_ai/schemas/__init__.py` | config | — | `src/sentry_ai/schemas/__init__.py` | exact |
| `src/sentry_ai/models/depth/mapping.py` | utility | transform | same file (verify-only; do not return calibrated) | exact |
| `tests/test_calibration_validators.py` | test | — | `tests/test_schemas_depth_kind.py` | role-match |
| `tests/test_calibration_state.py` | test | — | `tests/test_loop_enable_gates.py` (PipelineState block) | role-match |
| `tests/test_perception_store_depth_honesty.py` | test | — | `tests/test_perception_store.py` + `test_schemas_depth_kind.py` | role-match |
| `tests/test_schemas_depth_kind.py` | test | — | same file (extend matrix) | exact |
| `tests/test_depth_mapping.py` | test | — | same file (extend never-calibrated) | exact |

**Out of phase (do not pattern-map implementation):** `models/depth/loop.py`, wizard routes, free-space algorithm, YAML persist, `index.html`.

---

## Pattern Assignments

### `src/sentry_ai/schemas/validators.py` (utility, transform)

**Analog:** same file — extend the single shared honesty helper (FOUND-03 lineage).

**Imports pattern** (lines 1-5):
```python
"""Shared validation helpers for perception schemas."""

from __future__ import annotations

from sentry_ai.schemas.enums import DepthKind
```

**Core pattern today** (lines 8-11) — keep and generalize:
```python
def relative_depth_forbids_unit(kind: DepthKind, unit: str | None) -> None:
    """Raise ValueError when relative depth claims a physical unit (FOUND-03)."""
    if kind == DepthKind.RELATIVE and unit is not None:
        raise ValueError("relative depth must not set unit (meters forbidden)")
```

**Target core pattern** (copy structure: pure function, raise `ValueError`, no FastAPI/numpy):
```python
def assert_depth_kind_unit(kind: DepthKind, unit: str | None) -> None:
    """FOUND-03 / CAL-04 / CAL-05 honesty matrix."""
    if kind == DepthKind.RELATIVE:
        if unit is not None:
            raise ValueError("relative depth must not set unit (meters forbidden)")
        return
    if kind == DepthKind.METRIC_ESTIMATED:
        if unit != "m":
            raise ValueError("metric_estimated depth requires unit='m'")
        return
    if kind == DepthKind.METRIC_CALIBRATED:
        if unit != "m":
            raise ValueError("metric_calibrated depth requires unit='m' (CAL-04 pair)")
        return
    raise ValueError(f"unknown depth kind: {kind!r}")


def assert_free_space_units(depth_kind: DepthKind, units: str) -> None:
    """units='m' only when underlying depth is metric_calibrated."""
    if units == "m" and depth_kind != DepthKind.METRIC_CALIBRATED:
        raise ValueError(
            "free-space units='m' only allowed when depth_kind=metric_calibrated"
        )
    if units not in ("ordinal", "m"):
        raise ValueError(f"unknown free-space units: {units!r}")
```

**Compatibility:** Prefer implementing `assert_depth_kind_unit` and having `relative_depth_forbids_unit` call it (or re-export) so existing `DepthPayload` import keeps working until updated.

**Promotion gate** (pure; may live here or on `CalibrationState` — RESEARCH allows either; prefer validators for CI purity + state method wrapping it):
```python
def promote_kind_unit(
    base_kind: DepthKind,
    base_unit: str | None,
    *,
    applied: bool,
    valid: bool,
) -> tuple[DepthKind, str | None]:
    """Return wire kind/unit. Draft/invalid never promote."""
    if applied and valid:
        return DepthKind.METRIC_CALIBRATED, "m"
    return base_kind, base_unit
```

**Error handling:** Always `raise ValueError(...)` with explicit honesty message (matches `kind_for_mode` / `assert_depth_tier_allowed` style in `mapping.py` lines 39-43, 52-62).

---

### `src/sentry_ai/schemas/perception.py` (model, request-response)

**Analog:** same file — wire models with `extra=forbid` + `@model_validator(mode="after")`.

**Imports pattern** (lines 11-18):
```python
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.validators import relative_depth_forbids_unit
```

**Update import** to shared assert (keep relative helper if still exported):
```python
from sentry_ai.schemas.validators import assert_depth_kind_unit, assert_free_space_units
```

**Model config pattern** (lines 24-34, 73-76) — copy for any nested model:
```python
class DepthPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: DepthKind
    unit: Literal["m"] | None = None
    # ...
```

**Auth/guard pattern → honesty validator** (lines 42-45) — extend call site:
```python
@model_validator(mode="after")
def relative_must_not_claim_meters(self) -> DepthPayload:
    relative_depth_forbids_unit(self.kind, self.unit)
    return self
```

**Target** (rename or replace body; keep `@model_validator(mode="after")`):
```python
@model_validator(mode="after")
def kind_unit_honesty(self) -> DepthPayload:
    assert_depth_kind_unit(self.kind, self.unit)
    return self
```

**FreeSpacePayload gap** (lines 73-86) — currently comment-only honesty (`# "m" only if depth metric`). Add sibling validator:
```python
class FreeSpacePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: Literal["near_field_bands"] = "near_field_bands"
    depth_kind: DepthKind
    units: Literal["ordinal", "m"] = "ordinal"
    # ...

    @model_validator(mode="after")
    def free_space_units_honesty(self) -> FreeSpacePayload:
        assert_free_space_units(self.depth_kind, self.units)
        return self
```

**Policy note (from RESEARCH):** allow `metric_calibrated` + `units="ordinal"` until Phase 16; only forbid `units="m"` when not calibrated.

**Error handling:** Pydantic wraps raised `ValueError` as `ValidationError` — tests use `pytest.raises(ValidationError)` (see `tests/test_schemas_depth_kind.py` lines 28-30).

---

### `src/sentry_ai/schemas/calibration.py` (model, request-response) — NEW

**Analog:** `src/sentry_ai/schemas/perception.py` + `src/sentry_ai/schemas/frame.py`

**Imports pattern** (from `frame.py` lines 8-10 + perception Field usage):
```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field
```

**Core model pattern** — copy `ConfigDict(extra="forbid")`, identity Field constraints:
```python
# From frame.py lines 20-27 / perception Completeness lines 24-28
class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid")

    frame_id: int = Field(ge=0)
    camera_id: str = Field(min_length=1)
    # ...
```

**Target models** (RESEARCH design; follow same style):
```python
class CalibrationFingerprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    camera_id: str = Field(min_length=1)
    width: int | None = None
    height: int | None = None
    depth_mode: str | None = None  # relative | metric_indoor | metric_outdoor
    model_id: str | None = None
    schema_version: int = 1


class CalibrationParams(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: int = 1
    scale: float
    offset: float = 0.0
    method: str = "known_distance"  # known_distance | known_height | manual_scale
    sample_count: int = 0
    residual_rms: float | None = None
    fingerprint: CalibrationFingerprint
    created_at: float | None = None


class CalibrationSnapshot(BaseModel):
    """API/status-safe view of CalibrationState (Phase 15 will wire this)."""
    model_config = ConfigDict(extra="forbid")

    applied: bool = False
    valid: bool = False
    draft_sample_count: int = 0
    has_draft_params: bool = False
    # optional: scale / fingerprint when applied — keep status-safe, no bulk arrays
```

**Validation helper** (pure function in this module or validators.py — structural only, Phase 14 tightens residuals):
```python
def is_valid_calibration_params(params: CalibrationParams) -> tuple[bool, str | None]:
    import math
    if not math.isfinite(params.scale) or params.scale <= 0:
        return False, "scale_not_positive_finite"
    if not math.isfinite(params.offset):
        return False, "offset_not_finite"
    if not params.fingerprint.camera_id:
        return False, "missing_camera_id"
    if params.method == "manual_scale":
        return True, None
    if params.sample_count < 1:
        return False, "insufficient_samples"
    return True, None
```

**Do not:** add motor/safety fields; do not use `extra="allow"`.

---

### `src/sentry_ai/control/calibration_state.py` (store / control-plane, request-response) — NEW

**Analog:** `src/sentry_ai/control/pipeline_state.py` (exact twin)

**Imports pattern** (lines 6-14):
```python
"""Thread-safe pipeline stage flags + free-space cutoffs (UI-03/UI-04).

Cold-path control plane only — no FastAPI imports, no inference.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from sentry_ai.spatial.free_space import DEFAULT_MID_CUT, DEFAULT_NEAR_CUT

__all__ = ["PipelineState"]
```

**Target imports** (mirror structure, no FastAPI):
```python
"""Thread-safe draft vs applied monocular calibration state (CAL-04/05).

Cold-path control plane only — no FastAPI imports, no DepthLoop, no YAML I/O.
DepthLoop (Phase 14) will call promote_kind_unit / apply_map; wizard (Phase 15)
mutates draft/apply via REST.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field

from sentry_ai.schemas.calibration import (
    CalibrationParams,
    CalibrationSnapshot,
    is_valid_calibration_params,
)
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.validators import promote_kind_unit as _promote_kind_unit

__all__ = ["CalibrationState"]
```

**Core lock + snapshot pattern** (pipeline_state.py lines 24-44):
```python
@dataclass
class PipelineState:
    """Thread-safe stage enable flags and free-space near/mid cutoffs."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    detection_enabled: bool = True
    # ...

    def snapshot(self) -> dict[str, Any]:
        """Return a full isolated copy of current pipeline config."""
        with self._lock:
            return {
                "detection_enabled": self.detection_enabled,
                # ...
            }
```

**Mutator under lock returns snapshot** (pipeline_state.py lines 46-107):
```python
def update(self, **kwargs: Any) -> dict[str, Any]:
    """Merge partial fields under lock; return full snapshot.

    Raises
    ------
    ValueError
        Unknown keys, non-bool flags, cuts outside [0, 1], or
        effective ``near_cut <= mid_cut``.
    """
    # validate outside or under lock; assign under lock; return snapshot
```

**Target CalibrationState surface** (same lock discipline; separate draft vs applied fields):
```python
@dataclass
class CalibrationState:
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    _draft_params: CalibrationParams | None = field(default=None, repr=False)
    _applied_params: CalibrationParams | None = field(default=None, repr=False)
    _draft_samples: list = field(default_factory=list, repr=False)  # optional Phase 13 stub

    def snapshot(self) -> CalibrationSnapshot: ...
    def set_draft_params(self, params: CalibrationParams) -> CalibrationSnapshot: ...
    def clear_draft(self) -> CalibrationSnapshot: ...
    def apply(self) -> CalibrationSnapshot:
        """Promote draft → applied if valid; else raise ValueError with reason."""
    def clear_applied(self) -> CalibrationSnapshot: ...
    def is_applied(self) -> bool: ...
    def is_valid_applied(self) -> bool: ...
    def promote_kind_unit(
        self, base_kind: DepthKind, base_unit: str | None
    ) -> tuple[DepthKind, str | None]:
        return _promote_kind_unit(
            base_kind,
            base_unit,
            applied=self.is_applied(),
            valid=self.is_valid_applied(),
        )
```

**Error handling pattern** (pipeline_state lines 17-21, 62-64, 90-93):
```python
def _validate_cut(name: str, value: float) -> float:
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    return v
# Unknown keys / invalid transitions → ValueError; failed apply must not mutate applied.
```

**Critical state rules:**
- Draft params never set `is_applied()` True.
- `apply()` copies valid draft → applied under lock; invalid raises without clearing applied.
- `clear_draft()` does **not** clear applied (explicit `clear_applied` only).
- Docstring handoff for Phase 14 DepthLoop (no hook in this phase).

---

### `src/sentry_ai/state/perception_store.py` (store, CRUD)

**Analog:** same file — `set_depth` currently accepts any kind/unit pair (honesty gap).

**Imports pattern** (lines 13-22) — add validator import:
```python
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Literal

from sentry_ai.models.depth.preprocess import depth_stats
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import Detection
# ADD:
from sentry_ai.schemas.validators import assert_depth_kind_unit
```

**Core set_depth pattern** (lines 221-270) — gate at start of method before product construction:
```python
def set_depth(
    self,
    frame_id: int,
    camera_id: str,
    t_capture: float,
    depth_map: Any,
    kind: DepthKind,
    unit: Literal["m"] | None,
    latency_ms: float,
    width: int | None = None,
    height: int | None = None,
    model_name: str | None = None,
    error: str | None = None,
) -> None:
    """Store latest depth product (keep-latest). Computes stats when map present."""
    assert_depth_kind_unit(kind, unit)  # NEW — raise ValueError before store write
    # ... existing stats + DepthProduct + lock write unchanged
```

**Lock pattern** (lines 144-145, 271-281) — do **not** hold lock during assert; assert before product build (cheap pure check). Existing write remains:
```python
with self._lock:
    self._latest_depth = product
    self._metrics.depth_frames += 1
    # ...
```

**Error handling:** `ValueError` from assert propagates to caller (DepthLoop later); no silent swallow. Stats path already uses best-effort `except Exception` (lines 252-253) — do **not** wrap honesty assert in that try.

---

### `src/sentry_ai/control/__init__.py` (config)

**Analog:** same file lines 1-7.

```python
"""Runtime control plane for perception pipeline stage flags and cutoffs."""

from __future__ import annotations

from sentry_ai.control.pipeline_state import PipelineState

__all__ = ["PipelineState"]
```

**Target:** export `CalibrationState` alongside `PipelineState`:
```python
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.control.pipeline_state import PipelineState

__all__ = ["CalibrationState", "PipelineState"]
```

---

### `src/sentry_ai/schemas/__init__.py` (config)

**Analog:** same file lines 1-27 — public re-exports.

Optionally re-export calibration models if other packages import from `sentry_ai.schemas`. Prefer explicit:
```python
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSnapshot,
)
# add to __all__
```
Planner discretion: tests may import from submodule path (`sentry_ai.schemas.calibration`) like `ObstacleCue` does in `test_schemas_perception.py` line 145.

---

### `src/sentry_ai/models/depth/mapping.py` (utility, transform) — VERIFY ONLY

**Analog:** same file — **must not** return `METRIC_CALIBRATED`.

**Core pattern** (lines 33-43):
```python
def kind_for_mode(mode: str) -> tuple[DepthKind, str | None]:
    """Map depth_mode config to (DepthKind, unit).

    - relative → RELATIVE, unit=None (never meters)
    - metric_indoor / metric_outdoor → METRIC_ESTIMATED, unit=\"m\"
    """
    if mode == "relative":
        return DepthKind.RELATIVE, None
    if mode in ("metric_indoor", "metric_outdoor"):
        return DepthKind.METRIC_ESTIMATED, "m"
    raise ValueError(f"unknown depth_mode: {mode!r}")
```

**Phase 13 change:** none to production code; extend tests only.

---

### `tests/test_calibration_validators.py` (test) — NEW

**Analog:** `tests/test_schemas_depth_kind.py` + free-space sections of `tests/test_schemas_perception.py`

**Imports pattern** (`test_schemas_depth_kind.py` lines 1-8):
```python
"""FOUND-03: DepthKind enum and relative-depth honesty rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentry_ai.schemas import DepthKind, DepthPayload
```

**Core assertion patterns** (lines 22-42):
```python
def test_depth_payload_relative_unit_none_ok() -> None:
    d = DepthPayload(kind=DepthKind.RELATIVE, unit=None)
    assert d.kind == DepthKind.RELATIVE
    assert d.unit is None


def test_depth_payload_relative_unit_m_rejected() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.RELATIVE, unit="m")


def test_depth_payload_metric_calibrated_unit_m_ok() -> None:
    d = DepthPayload(kind=DepthKind.METRIC_CALIBRATED, unit="m")
    assert d.kind == DepthKind.METRIC_CALIBRATED
    assert d.unit == "m"
```

**Target matrix cases** (add for Wave 0):
- `assert_depth_kind_unit` / `DepthPayload`: relative+m reject; calibrated+None reject; estimated+None reject (if policy locked); calibrated+m ok; estimated+m ok
- `FreeSpacePayload`: relative+`units="m"` reject; estimated+`units="m"` reject; calibrated+`units="m"` ok; calibrated+ordinal ok; relative+ordinal ok
- Direct unit tests on pure validators (not only pydantic) for clearer failure messages

**FreeSpace construction style** (`test_schemas_perception.py` lines 186-198):
```python
payload = FreeSpacePayload(
    depth_kind=DepthKind.RELATIVE,
    units="ordinal",
    obstacle_count=1,
    # ...
)
```

---

### `tests/test_calibration_state.py` (test) — NEW

**Analog:** `tests/test_loop_enable_gates.py` PipelineState block (lines 127-170)

**Core unit-test style** (no FastAPI for pure state):
```python
def test_pipeline_state_defaults() -> None:
    state = PipelineState()
    snap = state.snapshot()
    assert snap["detection_enabled"] is True
    # ...


def test_pipeline_state_partial_update() -> None:
    state = PipelineState()
    snap = state.update(detection_enabled=False, near_cut=0.8)
    assert snap["detection_enabled"] is False
    # ...


def test_pipeline_state_rejects_near_le_mid() -> None:
    state = PipelineState()
    try:
        state.update(near_cut=0.3, mid_cut=0.5)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass
    # Original values preserved
    snap = state.snapshot()
    assert snap["near_cut"] == DEFAULT_NEAR_CUT
```

**Target cases for CalibrationState:**
- defaults: not applied, not valid, promote returns base kind/unit
- set_draft_params → still not applied; promote stays base
- apply invalid draft → ValueError; applied unchanged
- apply valid draft → `is_applied` + `is_valid_applied`; promote → `(METRIC_CALIBRATED, "m")`
- clear_draft does not clear applied
- clear_applied restores base promotion
- fingerprint fields present on params/snapshot
- structural invalid scale ≤0 / non-finite rejected

**Optional concurrent smoke:** `test_perception_store.py` concurrent write style only if needed; PipelineState tests stay single-threaded.

---

### `tests/test_perception_store_depth_honesty.py` (test) — NEW

**Analog:** `tests/test_perception_store.py` set_depth helpers (lines 180-236)

**Core set_depth happy path** (lines 180-200):
```python
def test_set_depth_returns_product_fields() -> None:
    store = PerceptionStore()
    depth = np.arange(12, dtype=np.float32).reshape(3, 4)
    store.set_depth(
        frame_id=5,
        camera_id="camD",
        t_capture=2.5,
        depth_map=depth,
        kind=DepthKind.RELATIVE,
        unit=None,
        latency_ms=8.0,
        model_name="depth-anything-v2-small",
    )
    snap = store.snapshot_depth()
    assert snap is not None
    assert snap.kind == DepthKind.RELATIVE
    assert snap.unit is None
```

**Target honesty cases:**
```python
def test_set_depth_rejects_relative_with_meters() -> None:
    store = PerceptionStore()
    with pytest.raises(ValueError, match="relative|meters|unit"):
        store.set_depth(
            frame_id=1,
            camera_id="cam0",
            t_capture=1.0,
            depth_map=np.ones((2, 2), dtype=np.float32),
            kind=DepthKind.RELATIVE,
            unit="m",
            latency_ms=1.0,
        )
    assert store.snapshot_depth() is None  # no partial write


def test_set_depth_rejects_calibrated_without_meters() -> None:
    # metric_calibrated + unit=None → ValueError; store empty
    ...


def test_set_depth_accepts_estimated_with_m() -> None:
    # keep existing metric_estimated path green
    ...
```

---

### `tests/test_schemas_depth_kind.py` (test) — EXTEND

**Analog:** same file.

Add:
- `test_depth_payload_metric_calibrated_unit_none_rejected`
- optionally `test_depth_payload_metric_estimated_unit_none_rejected` (RESEARCH A2)

Keep existing relative reject + calibrated+m ok as regression baseline.

---

### `tests/test_depth_mapping.py` (test) — EXTEND

**Analog:** same file lines 20-35.

Add explicit never-calibrated guard:
```python
@pytest.mark.parametrize("mode", ["relative", "metric_indoor", "metric_outdoor"])
def test_kind_for_mode_never_calibrated(mode: str) -> None:
    kind, _unit = kind_for_mode(mode)
    assert kind != DepthKind.METRIC_CALIBRATED
```

Do **not** change production mapping.

---

### Existing regression surfaces (do not break)

| File | Role in Phase 13 |
|------|------------------|
| `tests/test_depth_kind_honesty.py` | Snapshot/API relative unit null — must stay green; plant only honest store fixtures |
| `tests/test_free_space_bands.py` | `test_metric_estimated_still_ordinal_units` — compute path ordinal; schema still allows ordinal on estimated |
| `tests/test_schemas_perception.py` | Nested relative meters rejection; free-space extras forbid |
| `src/sentry_ai/api/assemble.py` `_units_for_depth_kind` (lines 95-99) | **Out of phase** for metric free-space path; currently always ordinal — leave alone unless schema force requires it |

---

## Shared Patterns

### 1. Pydantic wire models (`extra=forbid` + after-validator)

**Source:** `src/sentry_ai/schemas/perception.py` lines 24-45  
**Apply to:** `DepthPayload`, `FreeSpacePayload`, all `schemas/calibration.py` models

```python
model_config = ConfigDict(extra="forbid")

@model_validator(mode="after")
def kind_unit_honesty(self) -> DepthPayload:
    assert_depth_kind_unit(self.kind, self.unit)
    return self
```

### 2. Pure honesty helpers raise `ValueError`

**Source:** `src/sentry_ai/schemas/validators.py` lines 8-11; `models/depth/mapping.py` lines 39-43  
**Apply to:** `assert_depth_kind_unit`, `assert_free_space_units`, `promote_kind_unit`, `CalibrationState.apply`

```python
if kind == DepthKind.RELATIVE and unit is not None:
    raise ValueError("relative depth must not set unit (meters forbidden)")
```

### 3. Control-plane lock + snapshot + mutator returns snapshot

**Source:** `src/sentry_ai/control/pipeline_state.py` lines 24-107  
**Apply to:** `CalibrationState`

```python
_lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

def snapshot(self) -> ...:
    with self._lock:
        return ...  # isolated copy

def apply(self) -> ...:
    with self._lock:
        # validate; mutate; return snapshot
```

Cold-path only: **no FastAPI imports**, no inference, no numpy required.

### 4. Store product gate at write boundary

**Source:** `src/sentry_ai/state/perception_store.py` `set_depth` (lines 221-270)  
**Apply to:** depth honesty assert before `DepthProduct` construction

Mirror of wire-level honesty: store must not hold relative+`m` even if a caller bypasses `DepthPayload`.

### 5. Mode ≠ calibrated (mapping honesty)

**Source:** `src/sentry_ai/models/depth/mapping.py` lines 33-43  
**Apply to:** all promotion paths — mode gives base kind only; calibration state alone promotes

### 6. pytest ValidationError / ValueError contract tests

**Source:** `tests/test_schemas_depth_kind.py` lines 28-30; `tests/test_loop_enable_gates.py` lines 151-170  
**Apply to:** all new Wave 0 tests

```python
with pytest.raises(ValidationError):
    DepthPayload(kind=DepthKind.RELATIVE, unit="m")

# pure state / store:
with pytest.raises(ValueError, match="..."):
    ...
# and assert prior state preserved after failed mutation
```

### 7. Package exports via `__all__`

**Source:** `src/sentry_ai/control/__init__.py`, `schemas/__init__.py`  
**Apply to:** re-export new public types deliberately; keep private helpers unexported if only used internally.

### 8. Zero new dependencies

**Source:** project lock + RESEARCH Standard Stack  
**Apply to:** all Phase 13 files — stdlib `threading`/`dataclasses`/`math` + existing pydantic only.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All Phase 13 deliverables have in-repo analogs (PipelineState twin, validators extend, schema models, store gate, pytest contract style) |

**Closest "new concept" notes for planner (still patterned):**
- Draft vs applied state machine has no identical twin, but **PipelineState** supplies lock/snapshot/mutator mechanics; **backend_live honesty** (`tests/test_backend_honesty_status.py`) supplies the product principle of “never claim a stronger status than truth” without a code twin for draft/apply.
- `promote_kind_unit` is new pure API — pattern after `kind_for_mode` return shape `(DepthKind, str | None)`.

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/schemas/`, `src/sentry_ai/control/`, `src/sentry_ai/state/`, `src/sentry_ai/models/depth/`, `src/sentry_ai/api/assemble.py`, `tests/test_schemas_*`, `tests/test_depth_*`, `tests/test_perception_store.py`, `tests/test_loop_enable_gates.py`, `tests/test_free_space_bands.py`

**Files scanned:** ~25 primary sources + related tests  
**Pattern extraction date:** 2026-08-11  

**Key planner constraints from analogs:**
1. Extend validators first; wire models call shared asserts; store calls same assert.
2. New runtime state lives under `control/` next to `PipelineState`, not under `state/` product store.
3. Calibration Pydantic models are field-design only (no YAML).
4. Do not edit DepthLoop / free-space algorithm / REST / UI this phase.
5. Keep `kind_for_mode` non-calibrated; only `promote_kind_unit(applied, valid)` yields the calibrated pair.
