# Phase 17: Persist & Re-apply on Serve - Pattern Map

**Mapped:** 2026-08-13
**Files analyzed:** 12 (create/extend)
**Analogs found:** 12 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/config/calibration_store.py` | store I/O | path→YAML | `config/load.py` (`yaml.safe_load`) + `models/cache.py` (`default_cache_root`) | role-match |
| `src/sentry_ai/control/calibration_persist.py` | orchestrate | load→match→`apply_params` | new; closest is serve-time factory inject | new |
| `src/sentry_ai/control/calibration_state.py` | state | apply without draft | same file (`apply` requires draft today) | exact |
| `src/sentry_ai/schemas/calibration.py` | schema | snapshot persist fields | same file (`CalibrationSnapshot` extra=forbid) | exact |
| `src/sentry_ai/cli.py` | construct | serve load + banner | same file (`CalibrationState()` empty today) | exact |
| `src/sentry_ai/api/routes_calibration.py` | endpoint | save / persist:true / clear-file | same file apply/clear (in-memory) | exact |
| `src/sentry_ai/api/routes_preview.py` | status | additive persist field | same file Phase 15 `calibration_active` | exact |
| `src/sentry_ai/api/app.py` | inject | `calibration_path` on app.state | same file `calibration_state=` | exact |
| `src/sentry_ai/models/depth/loop.py` | loop | late W×H refuse before `apply_map` | same file Phase 14 hook | exact |
| `tests/test_calibration_store.py` | test | — | `test_config_profiles.py` + `test_model_cache.py` | role-match |
| `tests/test_calibration_persist.py` | test | — | `test_calibration_state.py` compose | role-match |
| `tests/test_api_calibration.py` | test | — | same file apply/clear/cancel | exact |
| `tests/test_cli_calibration_inject.py` | test | — | same file inspect-source inject | exact |
| `tests/test_depth_loop.py` | test | — | same file FakeDepthWorker apply | exact |

**Out of phase (do not pattern-map implementation):** capture uniqueID / RTSP fingerprint fields, profile YAML merge, platformdirs, wizard HTML redesign, docs polish (18), DetectionLoop, FrameBus, ORT-TRT factory, `kind_for_mode`, FSD/motor.

---

## Pattern Assignments

### `src/sentry_ai/config/calibration_store.py` (I/O) — NEW (17-01)

**Analog:** `config/load.py` `_read_yaml` uses `yaml.safe_load` only; `models/cache.py` resolves `SENTRY_MODEL_CACHE` then `default_cache_root()`.

**Target:**

```python
def default_calibration_dir() -> Path:
    """SENTRY_CALIBRATION_DIR or {cache_root}/calibration.
    cache_root = SENTRY_MODEL_CACHE or default_cache_root().
    Does not create the directory (save does).
    """

def safe_camera_stem(camera_id: str) -> str:
    """Sanitize to a single path stem. Reject empty, '..', '/', '\\\\'."""

def calibration_path(
    camera_id: str,
    *,
    directory: Path | None = None,
    explicit_file: Path | None = None,
) -> Path:
    """explicit_file wins; else directory/default_calibration_dir() / {stem}.yaml."""

def fingerprints_match(
    saved: CalibrationFingerprint,
    live: CalibrationFingerprint,
) -> tuple[bool, str | None]:
    """Return (True, None) or (False, reason_code).
    camera_id always; depth_mode/model_id when saved side non-None;
    width/height only when both sides non-None.
    """

def save_params(params: CalibrationParams, path: Path) -> Path:
    """Atomic temp+os.replace. yaml.safe_dump of params.model_dump(mode='python').
    Strip any depth_map / samples / freeze keys if present. mkdir parents.
    """

def load_params(path: Path) -> LoadResult:
    """missing → status=none; safe_load + CalibrationParams.model_validate
    → ok; else error (do not raise to callers of try_reapply).
    """

def delete_params(path: Path) -> bool:
    """Unlink if exists. True if a file was removed. Missing is False, not error.
    """
```

```python
@dataclass(frozen=True)
class LoadResult:
    status: Literal["none", "ok", "error"]
    params: CalibrationParams | None = None
    reason: str | None = None
```

**Do not:** import FastAPI, DepthLoop, FrameBus; call `yaml.load`; write maps; use platformdirs; key by profile name.

---

### `src/sentry_ai/control/calibration_persist.py` (orchestrate) — NEW (17-01)

**Analog:** none in-repo. Keep I/O out of `CalibrationState` (lock #13).

**Target:**

```python
@dataclass(frozen=True)
class ReapplyResult:
    status: Literal["none", "applied", "ignored_mismatch", "error"]
    reason: str | None = None
    path: Path | None = None

def try_reapply(
    state: CalibrationState,
    path: Path,
    live: CalibrationFingerprint,
) -> ReapplyResult:
    """Load + match + apply_params. Soft-fail corrupt/missing. Never fake samples."""

def persist_applied(state: CalibrationState, path: Path) -> Path:
    """save_params(get_applied_params()). Raise ValueError if not applied."""

def clear_persisted(state: CalibrationState, path: Path) -> None:
    """clear_applied + clear_draft + delete_params. Used by REST Clear, not Cancel."""

def refuse_if_mismatch(
    state: CalibrationState,
    live: CalibrationFingerprint,
) -> str | None:
    """If applied and fingerprints_match fails → clear_applied + persist=ignored_mismatch.
    Return reason or None. DepthLoop calls this before apply_map (17-02).
    """
```

**Do not:** open cameras; scale maps; import DetectionLoop.

---

### `src/sentry_ai/control/calibration_state.py` — EXTEND (17-01)

**Analog:** `apply()` requires `_draft_params` and copies draft → applied.

**Target:**

```python
def apply_params(self, params: CalibrationParams) -> CalibrationSnapshot:
    """Commit valid params as applied without a wizard draft.
    Raises ValueError if structurally invalid. Clears draft on success
    (same as apply()). Does not invent samples.
    """

def set_persist_status(
    self,
    status: Literal["none", "applied", "ignored_mismatch", "error"],
    reason: str | None = None,
) -> None: ...

def get_persist_status(self) -> tuple[str, str | None]: ...
```

`CalibrationSnapshot` (17-01) additive:

```python
persist_status: Literal["none", "applied", "ignored_mismatch", "error"] = "none"
persist_reason: str | None = None
```

`apply()` / `clear_applied()` / `clear_draft()` stay. `clear_applied` should set persist status to `none` only when the caller is Clear/refuse — `try_reapply` and routes own the precise status. Discretion: `clear_applied` sets persist to `none` unless a subsequent `set_persist_status` overwrites (refuse_if_mismatch does).

**Do not:** open files inside `CalibrationState`; add YAML imports.

---

### `src/sentry_ai/cli.py` — EXTEND (17-02)

**Analog:** hoists `CalibrationState()` then injects into DepthLoop + `create_app`. Banner lines for backend_live.

**Target:** After source + `depth_worker` exist (so live `camera_id` / mode / model are real), before `create_app`:

```python
from sentry_ai.config.calibration_store import calibration_path
from sentry_ai.control.calibration_persist import try_reapply
from sentry_ai.schemas.calibration import CalibrationFingerprint

path = calibration_path(
    getattr(src, "camera_id", None) or camera_id or "unknown",
    explicit_file=calibration_file,  # --calibration-file
)
live = CalibrationFingerprint(
    camera_id=str(getattr(src, "camera_id", None) or camera_id or "unknown"),
    width=None,
    height=None,
    depth_mode=str(depth_worker.get_depth_mode()) if depth_worker else None,
    model_id=getattr(depth_worker, "model_id", None) if depth_worker else None,
)
reapply = try_reapply(calibration_state, path, live)
# banner
typer.echo(f"calibration: {reapply.status}" + (f" reason={reapply.reason}" if reapply.reason else ""))
```

Add `--calibration-file` option. Pass `calibration_path=path` into `create_app` so REST save/clear use the same file.

**Do not:** scale maps in CLI; auto-save; load profile YAML.

---

### `src/sentry_ai/api/app.py` + `routes_calibration.py` + `routes_preview.py` — EXTEND (17-02)

**Analog:** `create_app(..., calibration_state=)`; apply/clear already exist; status already has `calibration_active`.

**Target:**

```python
# create_app
calibration_path: Path | str | None = None
app.state.calibration_path = Path(calibration_path) if calibration_path else None

# POST /api/depth/calibration/save
#   persist_applied(state, path); 422 if not applied; 503 if no path/state

# POST /api/depth/calibration/apply  body optional {persist: bool = false}
#   existing apply(); if persist: persist_applied(...)

# POST /api/depth/calibration/clear
#   existing clear + delete_params / clear_persisted (file gone)

# POST /api/depth/calibration/cancel
#   unchanged — no file I/O

# GET /api/status additive:
#   calibration_persist = snap.persist_status
#   calibration_persist_reason = snap.persist_reason  # omit if None
```

Apply body stays optional (`None` → persist false) so existing tests that POST apply with empty/no body stay green.

**Do not:** `worker.process`; `set_depth`; open cameras; Cancel-deletes-file; require persist on apply.

---

### `src/sentry_ai/models/depth/loop.py` — EXTEND (17-02, late size only)

**Analog:** already calls `promote_kind_unit` + `apply_map` after `worker.process`.

**Target:** Before `apply_map`, if calibration is present and applied, build a live fingerprint from the current frame/product (camera_id, depth_map HxW, worker mode/model) and call `refuse_if_mismatch`. Then existing promote + apply_map (which become no-ops if just cleared).

**Do not:** load YAML in DepthLoop; re-scale; touch DetectionLoop/FrameBus.

---

### Tests

| File | Plan | Analog behavior |
|------|------|-----------------|
| `tests/test_calibration_store.py` | 17-01 | tmp_path YAML round-trip; sanitize; match matrix; atomic write; no maps; corrupt → error |
| `tests/test_calibration_persist.py` | 17-01 | `try_reapply` match/mismatch/missing/corrupt; `apply_params` without samples; `clear_persisted` unlinks |
| `tests/test_calibration_state.py` | 17-01 | `apply_params` valid/invalid; existing `apply()` still requires draft |
| `tests/test_api_calibration.py` | 17-02 | save; persist:true; apply without persist writes nothing; clear deletes; cancel does not |
| `tests/test_cli_calibration_inject.py` | 17-02 | inspect `--calibration-file`, `try_reapply`, banner |
| `tests/test_depth_loop.py` | 17-02 | applied + file W×H vs later live size → cleared, maps unscaled |
| `tests/test_api_calibration_smoother.py` | 17-02 | stay green (clear still resets smoother) |

---

## Shared Patterns

### 1. `yaml.safe_load` only
**Source:** `config/load.py` T-1-01
**Apply to:** `load_params`

### 2. Cache-root layout, no platformdirs
**Source:** `models/cache.py` `default_cache_root` / `SENTRY_MODEL_CACHE`
**Apply to:** `default_calibration_dir`

### 3. Atomic replace
**Source:** common persist hazard (PITFALLS #3)
**Apply to:** `save_params` temp + `os.replace`

### 4. Soft-fail corrupt
**Source:** STACK load policy; v0.2 backend honesty
**Apply to:** `try_reapply` never promotes on error

### 5. Draft vs applied
**Source:** Phase 15 Cancel = `clear_draft`; Clear = `clear_applied`
**Apply to:** Cancel does not delete YAML; Clear does

### 6. Additive status
**Source:** Phase 15 `calibration_active` on `/api/status`
**Apply to:** `calibration_persist` + reason; never overwrite `depth_kind`

### 7. Consume DepthLoop for scale
**Source:** Phase 14/16
**Apply to:** persist never calls `apply_map`

### 8. Zero new dependencies
**Source:** ROADMAP lock
**Apply to:** all Phase 17 files

---

## No Analog Found

| File | Role | Reason |
|------|------|--------|
| `control/calibration_persist.py` | orchestrate | New; keep I/O out of `CalibrationState` |
| `fingerprints_match` | honesty | New; closest is `is_valid_calibration_params` (structural only) |

---

## Metadata

**Analog search scope:** `config/load.py`, `models/cache.py`, `control/calibration_state.py`, `cli.py` serve, `api/routes_calibration.py`, `api/routes_preview.py`, `api/app.py`, `models/depth/loop.py`, `schemas/calibration.py`, `tests/test_calibration_state.py`, `tests/test_api_calibration.py`, `tests/test_cli_calibration_inject.py`, `tests/test_config_profiles.py`

**Pattern extraction date:** 2026-08-13

**Key planner constraints from analogs:**
1. I/O lives in `config/`, not inside `CalibrationState`.
2. `apply()` keeps requiring draft; load uses `apply_params`.
3. Cancel ≠ Clear (file edition of the same rule).
4. Do not edit DetectionLoop / FrameBus / ORT factory / `kind_for_mode` / wizard HTML / docs.
