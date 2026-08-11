# Phase 13: Honesty Contracts & CalibrationState - Research

**Researched:** 2026-08-11  
**Domain:** Depth kind/unit honesty contracts + in-process CalibrationState (draft vs applied)  
**Confidence:** HIGH

## Summary

Phase 13 is the **honesty-first foundation** of v0.3. Monocular depth already ships a `DepthKind` triad (`relative` | `metric_estimated` | `metric_calibrated`) and a wire rule that **relative forbids meters** — but `metric_calibrated` is **never produced**, free-space can still construct `units="m"` on relative/estimated kinds, `DepthPayload` allows `metric_calibrated` with `unit=None`, and `PerceptionStore.set_depth` accepts `relative` + `unit="m"` without rejection. [VERIFIED: codebase probe 2026-08-11]

This phase must lock the **promotion policy** and an in-process **`CalibrationState`** so later phases (scale math, wizard, free-space meters, persist) cannot invent meters. Deliver pure contracts + state + tests — **not** DepthLoop scale apply, wizard UI, free-space metric bands, or YAML I/O.

**Primary recommendation:** Extend validators for the full kind↔unit matrix; add store-level honesty assert; introduce thread-safe `CalibrationState` (draft vs applied) with fingerprint fields and a pure `promote_kind_unit()` gate; zero new pip dependencies.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Kind/unit honesty validators | API / Backend (schemas) | — | Wire contracts (`DepthPayload`, `FreeSpacePayload`) reject lies at model construction |
| Store product honesty gate | Database / Storage (`PerceptionStore`) | API assemble | In-process products must not accept relative+`m` even before wire |
| Promotion policy (`metric_calibrated` + `m`) | API / Backend (policy helpers) | DepthLoop (Phase 14 consumer) | Only applied+valid calibration may emit the pair; pure function for CI |
| Draft vs applied CalibrationState | API / Backend (control plane) | — | Mirror `PipelineState`: cold-path mutation, hot-path read; draft never promotes |
| Fingerprint fields (camera_id, size, mode/model) | API / Backend (params schema) | Persist I/O (Phase 17) | Design key now so wizard/persist do not diverge |
| Mode → kind mapping (`kind_for_mode`) | API / Backend (depth mapping) | — | Must **remain** non-calibrated; mode alone never yields `metric_calibrated` |
| DepthLoop map scale apply | API / Backend (DepthLoop) | — | **Out of phase 13** — Phase 14 plugs into state |
| Wizard REST / Live Preview | Frontend Server + Browser | — | **Out of phase 13** — Phase 15 |
| Free-space metric bands | API / Backend (spatial) | — | **Out of phase 13** — Phase 16; only lock schema forbid of uncalibrated `units="m"` |
| YAML persist / serve re-apply | Database / Storage (files) | CLI serve | **Out of phase 13** — Phase 17; fingerprint fields designed here |

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python | ≥3.11 | Runtime | [VERIFIED: `pyproject.toml`] |
| Pydantic 2 | 2.13.4 (pin ≥2.13,<3) | Calibration params + wire models (`extra=forbid`) | [VERIFIED: uv env] Matches all perception schemas |
| NumPy | 2.4.6 (pin ≥2.0,<2.5) | Present on depth path; **not required** for Phase 13 state/validators | [VERIFIED: uv env] Reserved for Phase 14 fit |
| FastAPI | 0.141.1 | Existing app injection surface (`AppState`) | [VERIFIED: uv env] Phase 13 may add optional `calibration_state` slot only if needed for unit tests; routes deferred to 15 |
| stdlib `threading` + `dataclasses` | — | Thread-safe `CalibrationState` | [VERIFIED: codebase] Same pattern as `PipelineState` / `PerceptionStore` |
| pytest | 9.1.1 (dev extra) | Contract + state unit tests | [VERIFIED: uv env] |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PyYAML | 6.0.3 | Persist later | **Do not use in Phase 13** — design fields only |
| OpenCV | 5.0.0 headless | Capture / free-space | Unchanged; no Phase 13 dependency |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `control/calibration_state.py` | `state/calibration_state.py` | State package is product store-focused; **control** matches `PipelineState` cold-path ownership [ASSUMED: package layout preference] |
| Pydantic-only CalibrationState | Pure dataclass + lock | Pydantic better for **params snapshot / later YAML**; runtime mutability better as locked dataclass (mirror PipelineState) |
| Store-level honesty assert | Wire-only validators | Wire alone leaves relative+`m` in store → snapshot/status can lie before assemble |

**Installation:**

```bash
# Zero new packages for Phase 13
# Existing env is sufficient:
uv sync --extra dev
```

**Version verification:** [VERIFIED: `uv run python` 2026-08-11] pydantic 2.13.4, fastapi 0.141.1, numpy 2.4.6, pyyaml 6.0.3, pytest 9.1.1.

---

## Package Legitimacy Audit

> Phase 13 installs **no external packages**.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| — | — | — | — | — | n/a | No installs |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  

*slopcheck was not available at research time; no packages recommended for install, so no `[ASSUMED]` install risk.*

---

## Architecture Patterns

### System Architecture Diagram

```
                    ┌─────────────────────────────────────┐
                    │  CalibrationState (NEW, in-process) │
                    │  draft samples / draft params       │
                    │  applied params + valid flag        │
                    │  fingerprint fields                 │
                    │  promote_kind_unit() ───────────────┼──► only applied+valid
                    └──────────────────▲──────────────────┘     → metric_calibrated + "m"
                                       │
                                       │ (read later in Phase 14)
                                       │
FrameBus → DepthAnythingWorker.process
              │  kind/unit from kind_for_mode
              │  (never metric_calibrated)
              ▼
         [Phase 14] CalibrationState.apply_map + promote
              ▼
         PerceptionStore.set_depth  ◄── NEW: assert kind/unit honesty
              │
              ▼
         assemble → DepthPayload  ◄── NEW: calibrated requires unit="m"
              │                     ◄── existing: relative forbids unit
              ▼
         FreeSpacePayload           ◄── NEW: units="m" only if metric_calibrated
              │
              ▼
         /api/snapshot · /v1 · Live Preview status
```

Phase 13 implements the **left box + validators + store gate + tests**. DepthLoop hook, REST, UI, free-space metric path, and YAML are later phases but must consume this state shape.

### Recommended Project Structure

```
src/sentry_ai/
├── schemas/
│   ├── enums.py                 # DepthKind triad — UNCHANGED members
│   ├── validators.py            # EXTEND: full kind↔unit + free-space units
│   ├── perception.py            # EXTEND: model_validators call new helpers
│   └── calibration.py           # NEW: CalibrationFingerprint, CalibrationParams,
│                                #      CalibrationSnapshot (Pydantic, extra=forbid)
├── control/
│   ├── pipeline_state.py        # pattern reference — UNCHANGED
│   └── calibration_state.py     # NEW: thread-safe draft vs applied state
├── state/
│   └── perception_store.py      # EXTEND: set_depth honesty assert
└── models/depth/
    └── mapping.py               # VERIFY tests: kind_for_mode never calibrated

tests/
├── test_schemas_depth_kind.py           # EXTEND matrix
├── test_depth_kind_honesty.py           # EXTEND surfaces
├── test_calibration_validators.py       # NEW
├── test_calibration_state.py            # NEW
└── test_perception_store_depth_honesty.py  # NEW or extend test_perception_store
```

### Pattern 1: Single promotion gate

**What:** One pure function owns kind/unit promotion.  
**When to use:** Any path that would set `metric_calibrated` or `unit="m"` from calibration.  
**Example:**

```python
# Recommended API (in schemas/validators.py or control/calibration_state.py)
from sentry_ai.schemas.enums import DepthKind

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

**Source:** In-repo architecture research [CITED: `.planning/research/ARCHITECTURE.md` Validity rules]; mirrors v0.2 factory-only `backend_live` honesty.

### Pattern 2: Draft vs applied state machine

**What:** Fitting / staging never changes live product honesty.  
**When to use:** Wizard (Phase 15) and any future continuous-fit path.  
**States:**

```
idle
  → drafting (samples only; is_applied() == False)
  → draft_fit (params staged; is_applied() == False; promote still base)
  → applied  (is_applied() and is_valid() → promote pair)
  → cleared  (back to idle; base kind from mode)
```

**Cancel draft:** discards samples/draft params; **does not** clear an already-applied scale (Clear is explicit — Phase 15/17).  
**Apply:** copies valid draft → applied under lock.  
**Source:** [CITED: `.planning/research/PITFALLS.md` #5 Wizard UX thrash]

### Pattern 3: Mode never equals calibrated

**What:** `kind_for_mode` remains relative / metric_estimated only.  
**When to use:** Always.  
**Example:** Already shipped [VERIFIED: `src/sentry_ai/models/depth/mapping.py`]:

```python
def kind_for_mode(mode: str) -> tuple[DepthKind, str | None]:
    if mode == "relative":
        return DepthKind.RELATIVE, None
    if mode in ("metric_indoor", "metric_outdoor"):
        return DepthKind.METRIC_ESTIMATED, "m"
    raise ValueError(f"unknown depth_mode: {mode!r}")
```

Phase 13 **must not** change this to return `METRIC_CALIBRATED`.

### Pattern 4: Control-plane lock (PipelineState twin)

**What:** `CalibrationState` uses a private `threading.Lock`, `snapshot()` returns isolated dict/Pydantic model, mutators return snapshot.  
**When to use:** All draft/apply/clear.  
**Source:** [VERIFIED: `src/sentry_ai/control/pipeline_state.py`]

### Anti-Patterns to Avoid

- **`metric_calibrated` from `depth_mode` alone:** Lies — mode is model head, not user GT.  
- **Draft claims meters:** Compute/preview numbers OK; live kind must stay base until Apply.  
- **Wire-only honesty:** Store already accepts relative+`m` [VERIFIED] — robots/status can read store paths.  
- **Free-space `units="m"` for `metric_estimated`:** Explicitly forbidden by Phase 5 tests and v0.3 research.  
- **Implementing fit math / DepthLoop apply / REST / YAML in this phase:** Scope breach into 14–17.  
- **New pip deps (scipy, platformdirs, React):** Roadmap lock — zero new packages.  
- **FSD / “precise meters” language** on status snapshot strings.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Kind/unit matrix | Ad-hoc ifs in every route | Shared `assert_depth_kind_unit` + Pydantic validators | One regression surface; FOUND-03 lineage |
| Thread-safe flags | Global mutable dict | `CalibrationState` with lock + snapshot | Same races as pipeline flags without discipline |
| Fingerprint identity | Free-form status strings | Versioned `CalibrationFingerprint` model | Phase 17 refuse logic needs stable fields |
| Promotion branching | UI decides calibrated | `promote_kind_unit(applied, valid)` | UI/API parity (UI-06); single truth |
| Persist format now | Custom YAML writer | Design Pydantic fields only | Persist I/O is Phase 17 |

**Key insight:** Honesty is a **contract problem**, not a vision problem. Fix validators + state first so scale/UI cannot stamp meters on garbage.

---

## Common Pitfalls

### Pitfall 1: Pair honesty incomplete (relative forbids m, calibrated allows null)

**What goes wrong:** `DepthPayload(kind=metric_calibrated, unit=None)` validates today [VERIFIED]. CAL-04 requires the **pair**.  
**Why it happens:** Only `relative_depth_forbids_unit` exists.  
**How to avoid:** Add `metric_calibrated_requires_meters` (and optionally metric_estimated requires `"m"` for symmetry with `kind_for_mode`).  
**Warning signs:** Schema tests only cover relative rejection.

### Pitfall 2: Free-space schema accepts relative + `units="m"`

**What goes wrong:** `FreeSpacePayload(depth_kind=relative, units="m")` constructs successfully [VERIFIED]. Phase 16 could “flip a label” and pass schema.  
**Why it happens:** Comment-only rule in `perception.py`.  
**How to avoid:** Model validator: `units == "m"` **only if** `depth_kind == METRIC_CALIBRATED`. Relative **and** `metric_estimated` stay ordinal on the wire contract.  
**Warning signs:** No test for free-space relative+m rejection.

### Pitfall 3: Store accepts relative + unit=`"m"`

**What goes wrong:** `PerceptionStore.set_depth(..., kind=RELATIVE, unit="m")` succeeds [VERIFIED]. Snapshot/status paths can emit the lie without going through `DepthPayload` if any code bypasses assemble carefully — and assemble **will** fail only if it builds `DepthPayload` (it does for good depth). Still, product integrity requires store gate for CAL-05 “on store”.  
**How to avoid:** Call shared assert at start of `set_depth` (raise `ValueError`).  
**Warning signs:** Integration tests plant dishonest store fixtures “for convenience”.

### Pitfall 4: Draft equals applied

**What goes wrong:** Wizard compute sets live kind; Cancel cannot restore honesty.  
**How to avoid:** Separate `_draft_params` vs `_applied_params`; `is_applied()` only for applied; `promote_kind_unit` reads applied only.  
**Warning signs:** Single `params` field without stage flag.

### Pitfall 5: Fingerprint designed too late

**What goes wrong:** Phase 15/17 invent different keys → silent wrong-camera re-apply.  
**How to avoid:** Ship `CalibrationFingerprint` fields in Phase 13 even if unused by I/O.  
**Minimum fields (roadmap success criterion 4):**

| Field | Purpose |
|-------|---------|
| `camera_id` | Source identity on PerceptionFrame |
| `width` / `height` (or image size) | Resolution-sensitive scale |
| `depth_mode` | relative / metric_indoor / metric_outdoor |
| `model_id` | HF id / worker model name |
| `schema_version` / `version` | Forward-compatible load |

Optional later (Phase 17): capture backend path / uniqueID — not required to name in Phase 13 success criteria but leave room via optional fields or `extra` policy (**prefer explicit optional fields with `extra=forbid`**).

### Pitfall 6: Scope creep into scale apply

**What goes wrong:** Phase 13 PRs implement `apply_map` + DepthLoop hook without residual gates.  
**How to avoid:** State may expose `is_applied` / `applied_params` / **stub** `apply_map` that multiplies only if applied (optional), but **DepthLoop wiring is Phase 14**. Prefer Phase 13 without DepthLoop edits.  
**Warning signs:** Diffs in `models/depth/loop.py`, `routes_*`, `index.html`, `spatial/free_space.py`.

### Pitfall 7: Breaking existing metric_estimated path

**What goes wrong:** Over-tight validators reject estimated+`m` or force calibrated.  
**How to avoid:** Estimated remains valid with `unit="m"`; free-space for estimated remains ordinal.  
**Warning signs:** `test_metric_estimated_still_ordinal_units` or depth mapping tests red.

---

## Code Examples

### Full depth kind ↔ unit matrix (target)

```python
# Source: extend src/sentry_ai/schemas/validators.py
# Behavior verified gaps: relative+m rejected; calibrated+None currently allowed

from sentry_ai.schemas.enums import DepthKind

def assert_depth_kind_unit(kind: DepthKind, unit: str | None) -> None:
    """FOUND-03 / CAL-04 / CAL-05 honesty matrix."""
    if kind == DepthKind.RELATIVE:
        if unit is not None:
            raise ValueError("relative depth must not set unit (meters forbidden)")
        return
    if kind == DepthKind.METRIC_ESTIMATED:
        # Mode path always uses "m"; allow only "m" or document None as invalid
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

**Note on metric_estimated + `unit=None`:** Today allowed [VERIFIED]. Requiring `"m"` aligns with `kind_for_mode` and strengthens honesty. Confirm no production path sets estimated+None (mapping always sets `"m"`). [VERIFIED: `kind_for_mode`]

### Calibration models (recommended)

```python
# Source: design from ARCHITECTURE.md + ROADMAP success criteria
# Suggested: src/sentry_ai/schemas/calibration.py

from pydantic import BaseModel, ConfigDict, Field

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
    # NOT a safety certificate — operator-provided scale only
```

### Validity (params structure — not residual math)

```python
def is_valid_calibration_params(params: CalibrationParams) -> tuple[bool, str | None]:
    """Structural validity for promotion. Residual thresholds refined in Phase 14."""
    import math
    if not math.isfinite(params.scale) or params.scale <= 0:
        return False, "scale_not_positive_finite"
    if not math.isfinite(params.offset):
        return False, "offset_not_finite"
    if not params.fingerprint.camera_id:
        return False, "missing_camera_id"
    # Method-specific sample floor — keep conservative defaults; Phase 14 may tighten
    if params.method == "manual_scale":
        return True, None
    if params.sample_count < 1:
        return False, "insufficient_samples"
    return True, None
```

**Scale clamps (exact bounds):** Phase-tuned in 14; Phase 13 may use a wide reject band (e.g. non-positive / non-finite only) tagged as provisional [ASSUMED: exact min/max scale].

### CalibrationState sketch

```python
# Suggested: src/sentry_ai/control/calibration_state.py
# Pattern: PipelineState

class CalibrationState:
    def __init__(self) -> None: ...

    def snapshot(self) -> CalibrationSnapshot:
        """API/status-safe view: applied?, valid?, draft sample count, fingerprint, scale?."""

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
        return promote_kind_unit(
            base_kind,
            base_unit,
            applied=self.is_applied(),
            valid=self.is_valid_applied(),
        )
```

Draft samples list can be a simple `list` on the state for Phase 15; Phase 13 may include empty sample API stubs or only params-level draft.

### Store gate

```python
# In PerceptionStore.set_depth — after resolving kind/unit args:
from sentry_ai.schemas.validators import assert_depth_kind_unit

assert_depth_kind_unit(kind, unit)
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Relative depth unlabeled | `DepthKind` + relative forbids unit | v1.0 FOUND-03 | Wire honesty baseline |
| Metric heads = “meters” | `metric_estimated` + unit m | v1.0 Phase 4 | Estimated ≠ calibrated |
| Calibrated enum reserved | Still never produced | through v0.2 | Phase 13–14 make it reachable honestly |
| Free-space always ordinal | Still always ordinal (including calibrated stub) | v1.0 Phase 5 | Phase 16 flips meters only for calibrated **with real path** |
| Backend honesty factory-only | v0.2 `backend_live` | v0.2 | Process template for calib promotion gate |

**Deprecated/outdated:**
- “Just set `unit=m` on relative maps” — product-breaking anti-pattern  
- Free-space label-only meters without metric algorithm — deferred / forbidden  
- Mode string as calibration — never  

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Prefer `control/calibration_state.py` over `state/` or `spatial/` for runtime state | Architecture | Mild package churn if planner prefers ARCHITECTURE’s `spatial/calibration.py` |
| A2 | Require `metric_estimated` → `unit="m"` (not None) | Validators | Low — mapping already always sets `"m"`; would break only dishonest fixtures |
| A3 | Structural validity only in Phase 13 (no residual RMS threshold yet) | Validity | Phase 14 must add residual reject before wizard Apply is trustworthy |
| A4 | Wide scale clamps deferred; non-positive/non-finite reject only | Validity | Absurd scales could be “applied” in unit tests until Phase 14 clamps |
| A5 | Optional `AppState.calibration_state` injection in Phase 13 is not required if state is unit-tested pure | Architecture | Phase 15 will need injection; can wait |
| A6 | `apply_map` not implemented in Phase 13 | Scope | If planner wants a stub multiply for early integration, keep DepthLoop unhooked |

**If empty rows of [ASSUMED] elsewhere:** Core honesty gaps and stack versions are verified.

---

## Open Questions

1. **Should `metric_estimated` + `unit=None` be rejected?**
   - What we know: mapping always emits `"m"`; wire allows None today.
   - What's unclear: any error-product path sets estimated without unit?
   - Recommendation: Reject for symmetry; grep error paths in plan; keep relative-only `unit=None`.

2. **Exact residual / scale clamp values**
   - What we know: research says phase-tuned.
   - What's unclear: min/max scale for maker cameras.
   - Recommendation: Phase 13 structural validity only; Phase 14 locks numbers with synthetic tests.

3. **Should `CalibrationState.apply_map` exist as a pure stub in Phase 13?**
   - What we know: Phase 14 owns scale math + DepthLoop.
   - Recommendation: **No DepthLoop hook.** Optional pure `apply_map` on state that raises if not applied, or multiplies with applied scale for unit tests of “applied transforms” — planner discretion; prefer minimal surface.

4. **Free-space: allow `metric_calibrated` + `units="ordinal"`?**
   - What we know: assemble still returns ordinal even for calibrated stub today [VERIFIED: `assemble._units_for_depth_kind`].
   - Recommendation: **Allow** ordinal on calibrated until Phase 16 implements real meters (avoids forcing lie the other way). Only forbid `units="m"` when not calibrated.

5. **Persist path YAML vs JSON / cache vs config**
   - Out of Phase 13; fingerprint fields only. Roadmap defers path to Phase 17.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python ≥3.11 | Runtime | ✓ | 3.11 via uv (host also has 3.14) | Use `uv run` |
| uv | Dev/test | ✓ | present | — |
| pytest (dev extra) | Validation | ✓ | 9.1.1 | `uv sync --extra dev` |
| pydantic / fastapi / numpy | Core | ✓ | see Standard Stack | — |
| Physical camera / room | — | n/a | — | **Not required** — synthetic tests only |
| New pip packages | — | n/a | — | None |

**Missing dependencies with no fallback:** none for Phase 13  

**Missing dependencies with fallback:** host `python3` without venv lacks `cv2`/`sentry_ai` — always use `uv run` for tests [VERIFIED].

---

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json`.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.1.1 (`dev` extra) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` `testpaths = ["tests"]` |
| Quick run command | `uv run pytest tests/test_schemas_depth_kind.py tests/test_calibration_validators.py tests/test_calibration_state.py tests/test_perception_store_depth_honesty.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CAL-05 | `DepthPayload` rejects relative + `unit="m"` | unit | `uv run pytest tests/test_schemas_depth_kind.py::test_depth_payload_relative_unit_m_rejected -q` | ✅ |
| CAL-05 | Nested PerceptionFrame rejects relative + m | unit | `uv run pytest tests/test_schemas_perception.py::test_nested_relative_depth_rejects_meters -q` | ✅ |
| CAL-05 | Snapshot/API relative has `unit` null | integration | `uv run pytest tests/test_depth_kind_honesty.py::test_relative_snapshot_unit_null_no_depth_m_key -q` | ✅ |
| CAL-05 | FreeSpacePayload rejects relative + `units="m"` | unit | `uv run pytest tests/test_calibration_validators.py -k free_space_relative -q` | ❌ Wave 0 |
| CAL-05 | FreeSpacePayload rejects metric_estimated + `units="m"` | unit | same | ❌ Wave 0 |
| CAL-05 | `PerceptionStore.set_depth` rejects relative + m | unit | `uv run pytest tests/test_perception_store_depth_honesty.py -q` | ❌ Wave 0 |
| CAL-04 | `DepthPayload` rejects metric_calibrated + `unit=None` | unit | new test in depth_kind / calibration_validators | ❌ Wave 0 |
| CAL-04 | `DepthPayload` accepts metric_calibrated + `unit="m"` | unit | `tests/test_schemas_depth_kind.py::test_depth_payload_metric_calibrated_unit_m_ok` | ✅ (keep) |
| CAL-04 | `promote_kind_unit` only when applied+valid | unit | `tests/test_calibration_state.py` | ❌ Wave 0 |
| CAL-04/05 | Draft fit does not report calibrated | unit | `tests/test_calibration_state.py` | ❌ Wave 0 |
| CAL-04 | Applied+valid → pair `(metric_calibrated, "m")` | unit | `tests/test_calibration_state.py` | ❌ Wave 0 |
| Success #4 | Fingerprint fields present on params/snapshot | unit | `tests/test_calibration_state.py` or schema tests | ❌ Wave 0 |
| Guard | `kind_for_mode` never returns calibrated | unit | `tests/test_depth_mapping.py` (extend assert) | ✅ partial — extend |
| Guard | metric_estimated free-space stays ordinal (compute path) | unit | `tests/test_free_space_bands.py::test_metric_estimated_still_ordinal_units` | ✅ (must stay green) |

### Sampling Rate

- **Per task commit:** quick command above (target &lt; 30s)  
- **Per wave merge:** `uv run pytest -q`  
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_calibration_validators.py` — full kind↔unit matrix + free-space units matrix (CAL-04, CAL-05)
- [ ] `tests/test_calibration_state.py` — draft vs applied, promote gate, fingerprint fields, clear/apply
- [ ] `tests/test_perception_store_depth_honesty.py` — store rejects dishonest kind/unit (or extend `test_perception_store.py`)
- [ ] Extend `tests/test_depth_mapping.py` — explicit `assert kind != METRIC_CALIBRATED` for all modes
- [ ] Extend `tests/test_schemas_depth_kind.py` — calibrated requires `m`; optional estimated requires `m`
- [ ] Framework install: none — use existing `uv sync --extra dev`

*(No new pytest plugins required.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Localhost maker tool; no new auth surface in Phase 13 |
| V3 Session Management | no | — |
| V4 Access Control | no | CalibrationState not yet networked (Phase 15 routes later) |
| V5 Input Validation | yes | Pydantic `extra=forbid` on calibration models; structural validity on scale/offset |
| V6 Cryptography | no | No secrets in calib state; no hashing required for Phase 13 |

### Known Threat Patterns for monocular calibration honesty

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Unit spoofing (relative labeled meters) | Spoofing / Tampering | Validators + store assert + promote gate |
| Draft treated as applied | Spoofing | Explicit applied flag; promote only applied+valid |
| Fingerprint omission → later wrong-camera auto-apply | Tampering | Require fingerprint fields on params model now |
| Absurd scale as “calibrated truth” | Tampering | Structural reject non-finite/≤0; residual clamps Phase 14 |
| Motor/safety fields sneak into calib models | Elevation | `extra=forbid`; perception-only boundary unchanged |
| Injection via free-form method strings | Tampering | Prefer `Literal` methods or allowlist validation |

Phase 13 does **not** add network attack surface if routes stay deferred. If planner injects `AppState` only, no new HTTP endpoints.

---

## Project Constraints (from PROJECT.md / roadmap locks)

No root `CLAUDE.md` in this repo. Constraints from project planning (treat as locked for research):

- **Zero new pip dependencies** for v0.3 calibration  
- **Post-process scale in DepthLoop** (Phase 14) — not worker, not free-space, not UI  
- **`metric_calibrated` + `unit="m"` only when applied and valid**  
- **Free-space meters only after real metric path** (Phase 16) — not label-only  
- **Persist per camera_id with fingerprint refuse** (Phase 17) — design fingerprint here  
- **Static wizard + REST** (Phase 15) — no React  
- **No FSD / vehicle-grade claims**  
- **Spine freeze:** DetectionLoop / FrameBus / ORT-TRT factory untouched  
- **Synthetic CI tests** — no physical room  
- **Apache-2.0** application code; perception-only API (no motor fields)

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAL-04 | When calibration is applied and valid, depth products use `depth_kind=metric_calibrated` and `unit="m"` together | `promote_kind_unit`; calibrated-requires-m validator; CalibrationState apply/valid; tests for pair |
| CAL-05 | Relative and uncalibrated depth never claim meters on store, snapshot, Live Preview, and `/v1` | Store assert; keep relative forbids unit; free-space units matrix; existing snapshot honesty tests; draft does not promote |

**Success criteria mapping:**

| # | Criterion | Research deliverable |
|---|-----------|----------------------|
| 1 | Relative/uncalibrated never emit `unit="m"` on store/snapshot/v1 | Store gate + DepthPayload + free-space validators + tests |
| 2 | Draft vs applied; draft not calibrated | CalibrationState state machine + tests |
| 3 | Only applied+valid → pair together | `promote_kind_unit` + `is_valid_calibration_params` |
| 4 | Fingerprint fields for later persist | `CalibrationFingerprint` on params/snapshot |

**Explicitly out of phase:** scale fit math (14), wizard UI (15), free-space meters path (16), YAML persist (17), docs polish (18).

---

## Implementation Prescription (for planner)

### Must ship

1. **`assert_depth_kind_unit`** (or equivalent) covering:
   - relative → unit is None  
   - metric_calibrated → unit is `"m"`  
   - metric_estimated → unit is `"m"` (recommended)  
2. **`assert_free_space_units`** — `"m"` only for `metric_calibrated`  
3. Wire into `DepthPayload` and `FreeSpacePayload` model validators  
4. **`PerceptionStore.set_depth`** calls depth kind/unit assert  
5. **`CalibrationFingerprint` + `CalibrationParams` + snapshot model** (Pydantic)  
6. **`CalibrationState`**: draft vs applied, apply/clear_draft/clear_applied, `is_applied`, `is_valid_applied`, `promote_kind_unit`, fingerprint on params  
7. **Tests** for matrix + state machine + store rejection + kind_for_mode never calibrated  

### Must not ship

- DepthLoop / worker / free-space algorithm changes (beyond schema if free_space result types unchanged)  
- REST routes / index.html wizard  
- YAML load/save  
- Residual RMS thresholds as product policy (unless trivial structural)  
- New dependencies  

### Minimal DepthLoop note for Phase 14 handoff

Document in code docstring on `CalibrationState`:

```
DepthLoop (Phase 14):
  result = worker.process(frame)
  kind, unit = state.promote_kind_unit(result.kind, result.unit)
  depth_map = state.apply_map(result.depth_map)  # Phase 14
  store.set_depth(..., kind=kind, unit=unit, depth_map=depth_map)
```

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase] `src/sentry_ai/schemas/enums.py` — DepthKind triad  
- [VERIFIED: codebase] `src/sentry_ai/schemas/validators.py` — relative-only forbid today  
- [VERIFIED: codebase] `src/sentry_ai/schemas/perception.py` — DepthPayload / FreeSpacePayload  
- [VERIFIED: codebase] `src/sentry_ai/state/perception_store.py` — set_depth no honesty assert  
- [VERIFIED: codebase] `src/sentry_ai/models/depth/mapping.py` — kind_for_mode never calibrated  
- [VERIFIED: codebase] `src/sentry_ai/api/assemble.py` — free-space units always ordinal stub  
- [VERIFIED: codebase] `src/sentry_ai/control/pipeline_state.py` — control-plane lock pattern  
- [VERIFIED: uv probe 2026-08-11] FreeSpacePayload allows relative+`m`; DepthPayload allows calibrated+None; store allows relative+`m`  
- [VERIFIED: tests] `tests/test_schemas_depth_kind.py`, `test_depth_kind_honesty.py`, `test_depth_mapping.py`, `test_free_space_bands.py`  
- [CITED: `.planning/research/ARCHITECTURE.md`] CalibrationState placement, promotion rules, spine insert point  
- [CITED: `.planning/research/PITFALLS.md`] Silent unit lies, draft thrash, fingerprint hazards  
- [CITED: `.planning/research/SUMMARY.md`] Phase 13 deliverables, zero deps  
- [CITED: `.planning/ROADMAP.md`] Phase 13 success criteria; phases 14–18 deferrals  
- [CITED: `.planning/REQUIREMENTS.md`] CAL-04, CAL-05  
- [CITED: `.planning/PROJECT.md`] v0.3 goals, no FSD, camera-only  

### Secondary (MEDIUM confidence)

- [CITED: `.planning/research/STACK.md`] Module path suggestions (`control/` vs `spatial/`)  
- [CITED: `.planning/research/FEATURES.md`] Maker expectations for apply/cancel honesty  

### Tertiary (LOW confidence)

- Exact scale min/max clamps and residual RMS numbers — deferred Phase 14  

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — zero new deps; versions verified via uv  
- Architecture: **HIGH** — code-verified spine + research consensus on CalibrationState  
- Pitfalls: **HIGH** — honesty gaps reproduced with live probes  
- Validity thresholds: **MEDIUM** — structural only; residual clamps later  

**Research date:** 2026-08-11  
**Valid until:** ~2026-09-10 (stable contracts; re-check if DepthPayload/store change)

---

## RESEARCH COMPLETE

**Phase:** 13 - Honesty Contracts & CalibrationState  
**Confidence:** HIGH

### Key Findings

1. **Honesty gaps are real today:** free-space schema allows relative+`units="m"`, depth allows `metric_calibrated` without `unit="m"`, and `PerceptionStore` accepts relative+`m` — all verified by runtime probe.  
2. **Promotion must be pure and state-gated:** only `applied and valid` → `(metric_calibrated, "m")`; draft never promotes; `kind_for_mode` must stay non-calibrated.  
3. **`CalibrationState` belongs on the control plane** (PipelineState twin): draft vs applied, fingerprint fields on params, snapshot for later status/API — no DepthLoop/UI/YAML in this phase.  
4. **Zero new packages;** extend `validators.py` + new `schemas/calibration.py` + `control/calibration_state.py` + store assert.  
5. **Wave 0 tests required** for free-space matrix, store rejection, state machine, and calibrated pair enforcement; existing relative-forbids-m tests remain the regression baseline.

### File Created

`.planning/phases/13-honesty-contracts-calibrationstate/13-RESEARCH.md`

### Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | No new deps; versions verified |
| Architecture | HIGH | Code + milestone research agree on insert point and state model |
| Pitfalls | HIGH | Live probe confirmed contract holes |

### Open Questions

- metric_estimated + unit=None reject? (recommend yes)  
- Exact residual/scale clamps (Phase 14)  
- Whether Phase 13 includes pure `apply_map` stub (prefer no DepthLoop hook)

### Ready for Planning

Research complete. Planner can now create PLAN.md files.
