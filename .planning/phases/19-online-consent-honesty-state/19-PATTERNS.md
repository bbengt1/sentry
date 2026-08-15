# Phase 19: Online consent & honesty state — Pattern Map

**Mapped:** 2026-08-15
**Files analyzed:** `control/calibration_state.py`, `schemas/calibration.py`, `control/calibration_persist.py`, `api/routes_calibration.py`, `api/routes_preview.py` (`/api/status`), `tests/test_calibration_state.py`, `tests/test_calibration_persist.py`, `tests/test_api_calibration.py`
**Analogs found:** persist-status additive (17-01) + wizard REST extra=forbid (15-01)

## File Classification

| New/Modified File | Role | Closest Analog | Match |
|-------------------|------|----------------|-------|
| `src/sentry_ai/control/calibration_state.py` | session flag + status machine | same file: `_persist_status` + `set_persist_status` | exact |
| `src/sentry_ai/schemas/calibration.py` | snapshot additives | same file: `persist_status` / `persist_reason` on `CalibrationSnapshot` | exact |
| `src/sentry_ai/api/routes_calibration.py` | thin POST toggle | `CalibrationApplyBody` + cancel/clear handlers | role-match |
| `src/sentry_ai/api/routes_preview.py` | `/api/status` additives | existing `calibration_persist` block (Phase 17-02) | exact |
| `tests/test_calibration_state.py` | unit honesty | same file: apply/draft/persist tests | exact |
| `tests/test_calibration_persist.py` | try_reapply does not enable; disable ≠ delete YAML | same file: `try_reapply` / `clear_persisted` | exact |
| `tests/test_api_calibration.py` | REST 409 / Cancel / Clear / disable | same file: apply/cancel/clear | exact |

**Out of phase:** sampler module, `spatial/calibration.py` fit, DepthLoop, DetectionLoop, FrameBus, ORT-TRT, `kind_for_mode`, `index.html`, YAML schema for an online key, `pyproject` version, REQUIREMENTS checkbox closeout.

---

## Pattern Assignments

### `CalibrationState` online flag — EXTEND (19-01)

**Analog:** persist status fields added in 17-01 without changing `apply_map`.

```python
_ONLINE_STATUSES = frozenset(
    {"online_off", "online_draft", "auto_committed", "rejected"}
)

@dataclass
class CalibrationState:
    _online_enabled: bool = field(default=False, repr=False)
    _online_status: str = field(default="online_off", repr=False)
    # existing _lock, draft/applied, persist…

    def is_online(self) -> bool:
        with self._lock:
            return self._online_enabled

    def set_online(self, enabled: bool) -> CalibrationSnapshot:
        """Enable refused unless already applied. Disable is not Clear."""
        with self._lock:
            if enabled:
                if self._applied_params is None:
                    raise ValueError("online_requires_applied")
                self._online_enabled = True
                if self._online_status == "online_off":
                    self._online_status = "online_draft"
            else:
                self._online_enabled = False
                self._online_status = "online_off"
            return self._snapshot_unlocked()
```

**Rules:**
- `CalibrationState()` → `is_online() is False`, status `online_off`
- `set_online(True)` never calls `apply` / `apply_params` / `apply_map`
- `set_online(True)` when unapplied raises `ValueError("online_requires_applied")` and leaves state unchanged
- `set_online(True)` after `apply()` or `apply_params()` (including `try_reapply` match) succeeds; kind/unit still come only from applied+valid
- `set_online(False)` does **not** touch `_applied_params`, persist status, or draft
- `apply()` / `apply_params()` do **not** flip online on
- `clear_applied()` forces `online=False` + `online_off` (consent gone)
- `clear_draft()` does **not** change online flag/status
- Idempotent: `set_online(True)` when already on; `set_online(False)` when already off
- 19-01 may store `_online_status` internally but snapshot `online_status` + REST are 19-02. 19-01 **must** expose `online: bool` on the snapshot (ONL-01 flag surface)

**Do not:** new class; YAML I/O inside `CalibrationState`; sampler; auto-commit helper.

---

### `CalibrationSnapshot` additives

**Analog:** `persist_status: Literal[...] = "none"` (extra=forbid).

```python
class CalibrationSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # existing fields…
    online: bool = False  # 19-01
    online_status: Literal[
        "online_off", "online_draft", "auto_committed", "rejected"
    ] = "online_off"  # 19-02
```

Copy both under the existing lock in `_snapshot_unlocked`. Do **not** put `online_status` on `CalibrationParams` (that would persist it).

`auto_committed` / `rejected` are valid snapshot values (constructible in tests) but Phase 19 production transitions never set them.

---

### Cancel / Clear / disable matrix (19-02)

| Action | Draft | Applied | YAML | Online flag | `online_status` |
|--------|-------|---------|------|-------------|-----------------|
| Cancel (`clear_draft`) | cleared | unchanged | unchanged | unchanged | unchanged |
| Clear (`clear_persisted` / `clear_applied`) | cleared | cleared | deleted | **False** | **online_off** |
| Disable (`set_online(False)`) | unchanged | unchanged | unchanged | False | online_off |
| Enable after applied | unchanged | unchanged | unchanged | True | online_draft |
| Enable while unapplied | unchanged | unchanged | unchanged | False | online_off (raise / 409) |

`clear_persisted` already calls `clear_applied` + `clear_draft` + `delete_params`. Implement the online reset **inside `clear_applied`** so Clear, `refuse_if_mismatch`, and any future wipe stay honest. Disable must **not** call `clear_applied` or `delete_params`.

---

### Thin REST toggle (19-02)

**Analog:** `CalibrationApplyBody` + `_parse_json_body` / extra=forbid; 409 already used for `calibration_already_applied`.

```python
class CalibrationOnlineBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool

@router.post("/api/depth/calibration/online")
async def set_calibration_online(body: CalibrationOnlineBody, request: Request):
    state = _require_calibration_state(request)
    try:
        state.set_online(body.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _snapshot_payload(request, state)
```

`GET /api/depth/calibration` already returns `snapshot().model_dump()` — no new GET route.

Handlers never call `apply_map`, `worker.process`, PerceptionStore writes, or YAML save/delete.

---

### `/api/status` additives (19-02)

**Analog:** existing calibration block in `routes_preview.py` (never sets `depth_kind` from draft).

```python
data["calibration_online"] = bool(snap.online)
data["calibration_online_status"] = snap.online_status
```

Do **not** overwrite `depth_kind`, `depth_unit`, `calibration_persist`, or `calibration_active`. A frame may be `metric_calibrated` + persist `applied` + `online_off`.

---

### Tests

**19-01** (`tests/test_calibration_state.py`, extend `tests/test_calibration_persist.py`):
- boot: `is_online() is False`; snapshot `online is False`
- `set_online(True)` unapplied → `ValueError`; still not applied; kind stays relative
- after `apply()` / `apply_params()`: `set_online(True)` ok; `promote_kind_unit` still calibrated only because applied (not because online)
- `set_online(True)` does not change scale / does not call persist
- `try_reapply` match → applied + `is_online() is False`
- existing apply/draft/`apply_map` tests stay green

**19-02** (same + `tests/test_api_calibration.py`):
- snapshot `online_status` defaults `online_off`; extra=forbid still rejects unknown keys
- Cancel after enable: draft gone, applied+online stay
- Clear after enable: not applied, YAML gone, online off
- Disable after enable: applied+YAML stay, online off
- POST enable unapplied → 409; POST enable applied → 200 + `online_draft`
- POST disable → 200 + `online_off` + file still exists
- `/api/status` exposes `calibration_online` / `calibration_online_status` without collapsing into `depth_kind`

---

## Shared Patterns

1. **Additive snapshot fields** — same as persist status (17-01): defaults, `extra=forbid`, copy under lock.
2. **Cold-path only** — `CalibrationState` still imports no FastAPI, no YAML, no DepthLoop.
3. **REST extra=forbid + 409 for consent** — same as sample-while-applied.
4. **Three planes** — kind / persist / online never share a field name.
5. **TDD** — RED tests then GREEN (Phase 13/17/18).
6. **Zero new dependencies / frozen spine.**

---

## Metadata

**Analog search scope:** Phase 13 `CalibrationState`, Phase 17 persist-status additive, Phase 15 wizard REST, `tests/test_api_calibration.py` cancel/clear.

**Key planner constraints:** session flag; refuse enable-unapplied; Cancel ≠ Clear ≠ disable; no sampler/auto-commit/`apply_map`.
