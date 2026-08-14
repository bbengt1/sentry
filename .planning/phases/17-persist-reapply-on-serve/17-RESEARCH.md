# Phase 17: Persist & Re-apply on Serve - Research

**Researched:** 2026-08-13
**Domain:** Per-`camera_id` YAML persist of applied calibration; fingerprint-gated auto-apply on `sentry serve`; clear that cannot resurrect
**Confidence:** HIGH

## Summary

Phase 16 shipped honest free-space meters when `depth.kind` is `metric_calibrated`. Calibration itself is still **in-memory only**: `CalibrationState.apply()` copies a wizard draft under lock; `cli.serve` constructs an empty `CalibrationState()`; `POST .../apply` and `POST .../clear` never touch disk. A restart always returns to relative / `metric_estimated` honesty even after a successful Apply. [VERIFIED: `control/calibration_state.py` has no YAML I/O and `apply()` requires draft; `cli.py` `calibration_state = CalibrationState()` with no load; `routes_calibration.py` apply/clear mutate state only; `config/load.py` is the existing `yaml.safe_load` analog; `models/cache.py` `default_cache_root()` + `SENTRY_MODEL_CACHE`.]

Phase 17 must deliver:

1. **YAML store + fingerprint refuse** (PER-01 / PER-03) — save `CalibrationParams` keyed by sanitized `camera_id`; hard-refuse auto-apply on fingerprint mismatch; never write depth maps.
2. **Serve re-apply + REST save/clear + status** (PER-02 / PER-04) — `sentry serve` auto-applies only a matching saved file; explicit save and `persist:true` on apply; Clear deletes the file so restart cannot resurrect; Cancel stays draft-only.

**Primary recommendation:** New I/O module `config/calibration_store.py` (STACK path, YAML, `yaml.safe_load` only, atomic temp+rename, no platformdirs). `CalibrationState.apply_params(params)` commits valid params **without** a wizard draft so the load path cannot fake samples. Serve calls a pure `try_reapply(state, path, live)` helper. DepthLoop remains the **sole map apply site** — persist only loads into `CalibrationState`. Additive persist status `none | applied | ignored_mismatch | error` is separate from `depth.kind`.

---

## Locked Decisions (authoritative)

| # | Decision | Value |
|---|----------|-------|
| 1 | Path | `$SENTRY_MODEL_CACHE` / `default_cache_root()` / `calibration/{safe_id}.yaml`. Follow STACK. **YAML not JSON. No platformdirs.** |
| 2 | Overrides | Optional `SENTRY_CALIBRATION_DIR` env (directory) + `sentry serve --calibration-file PATH` (explicit file) |
| 3 | I/O | `yaml.safe_load` only (never `yaml.load`). Pydantic `CalibrationParams` round-trip. Atomic temp+rename. **No depth maps on disk** (no samples, no crops, no freeze pins) |
| 4 | Key | Sanitized `camera_id` stem; reject `..`, `/`, `\\`, empty. **Not** profile YAML |
| 5 | Hard-refuse fields | `camera_id`, `depth_mode`, `model_id` always compared when the saved side is non-None (missing live value vs saved value is a mismatch). `width`/`height` compared **only when both sides non-None**. **Do not** add capture-backend / RTSP uniqueID fields this phase |
| 6 | Resolution at serve | File may have W×H while live sizes are still None at process start → load may match `camera_id`+mode+model first. If the file has W×H and a later live product mismatches → refuse + `clear_applied` (status `ignored_mismatch`) |
| 7 | Auto-apply | Only when file present **and** `fingerprints_match`. Corrupt or missing → soft inactive, **never** `metric_calibrated`. Visible reason |
| 8 | Load apply API | Add `CalibrationState.apply_params(params)` (or equivalent). Load path **must not** fake wizard samples / `set_draft_params`+`apply()` |
| 9 | Persist trigger | Explicit `POST /api/depth/calibration/save` **and** optional `persist: true` on apply. Serve auto-loads the **saved file only**. Apply-without-persist remains session-only |
| 10 | Clear vs Cancel | **Clear** deletes (or tombstones) the file so restart cannot resurrect. **Cancel** stays draft-only (no file delete, no `clear_applied`) |
| 11 | Status | Additive `calibration_persist`: `none | applied | ignored_mismatch | error`, **separate from** `depth.kind`. Serve banner line |
| 12 | Apply site | DepthLoop remains the sole map apply site. Persist **only** loads into `CalibrationState` (then existing `apply_map` / `promote_kind_unit`) |
| 13 | Constraints | Zero new deps; freeze DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; synthetic tests only; no wizard redesign beyond persist/clear-file; no FSD; docs are Phase 18; `CalibrationState` stays cold-path + `apply_map`; I/O is a separate store module (`config/calibration_store.py`) |

---

## Architectural Responsibility Map

| Capability | Primary Tier | Rationale |
|------------|--------------|-----------|
| Path resolve + sanitize | `config/calibration_store.py` | Same family as `config/load.py` + `models/cache.py` |
| YAML save/load/delete | `config/calibration_store.py` | I/O isolated; no FastAPI; no DepthLoop |
| `fingerprints_match` | `config/calibration_store.py` (pure) | Golden tests without serve |
| `try_reapply` | `control/calibration_persist.py` | Orchestrates store + `apply_params`; no I/O in `CalibrationState` |
| `apply_params` | `control/calibration_state.py` | Load path must not invent draft samples |
| Persist status on snapshot | `CalibrationState` + `CalibrationSnapshot` | Additive; extra=forbid |
| Serve load + banner + `--calibration-file` | `cli.serve` | After source + depth worker exist so live fingerprint is real |
| Late W×H refuse | DepthLoop **before** `apply_map` | Calls `refuse_if_mismatch(live)`; not a second scale site |
| REST save / persist:true / clear-file | `routes_calibration.py` | Handlers still never `worker.process` / open cameras / `set_depth` |
| Status + banner | `/api/status` + serve echo | Separate from `depth_kind` |
| Depth scale | DepthLoop `apply_map` (Phase 14) | **Do not duplicate** |

---

## Standard Stack

Zero new packages. Existing PyYAML (`yaml.safe_load` / `safe_dump`) + Pydantic 2 `CalibrationParams` + pathlib + pytest. No platformdirs, no sqlite, no JSON persist.

```bash
uv sync --extra dev
uv run pytest tests/test_calibration_store.py tests/test_calibration_persist.py tests/test_calibration_state.py tests/test_api_calibration.py tests/test_cli_calibration_inject.py -q
```

---

## Architecture Patterns

```
Wizard Apply (session)
  → CalibrationState.apply()                    # draft → applied (Phase 15)
  → optional persist:true or POST .../save
       → calibration_store.save_params          # atomic YAML; no maps

sentry serve
  → CalibrationState()                          # empty
  → live = Fingerprint(camera_id, mode, model, W/H or None)
  → try_reapply(state, path, live)
       missing        → persist=none; stay inactive
       corrupt        → persist=error; stay inactive
       mismatch       → persist=ignored_mismatch; stay inactive
       match          → apply_params(params); persist=applied
  → DepthLoop(..., calibration=state)           # sole apply_map site
       on each success frame, if file/applied has W×H and live W×H now known:
         refuse_if_mismatch → clear_applied + persist=ignored_mismatch

POST .../clear
  → clear_applied + clear_draft + delete_params(path)
  → restart cannot resurrect

POST .../cancel
  → clear_draft only                            # file untouched
```

Anti-patterns: JSON under `~/.config` / platformdirs (ARCHITECTURE opinion — **overruled by STACK + lock #1**); merge scale into profile YAML; `yaml.load`; write depth maps or freeze pins; fake `add_draft_sample` on load; auto-save on every apply; Cancel deleting the file; auto-apply on mismatch; second `apply_map` outside DepthLoop; capture-backend / RTSP uniqueID fields this phase; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode` edits; wizard redesign; FSD copy; docs polish (18).

---

## Common Pitfalls

1. **Wrong-camera / wrong-model silent re-apply (PER-03 / PITFALLS #3)** — file exists, fingerprint ignored, serve stamps `metric_calibrated`. **Lock #5/#7:** `fingerprints_match` before `apply_params`.
2. **Resolution drift after load (lock #6)** — serve-time live W×H is often None; a later 1280×720 product vs saved 1920×1080 must refuse/clear, not keep scaling.
3. **Corrupt file crash or fake calibrated (lock #7)** — `safe_load` + `model_validate` failure → `error`, inactive, never promote.
4. **Clear leaves orphan YAML (PER-04)** — restart re-applies. Clear **must** delete/tombstone.
5. **Cancel deletes the file (WIZ-02 / lock #10)** — Cancel is draft-only. Already-applied + saved file stays until Clear.
6. **Load fakes wizard samples (lock #8)** — `set_draft_params` + `apply()` would lie about `sample_count` / draft. Use `apply_params`.
7. **Auto-persist on apply (lock #9)** — session Apply without save must not write YAML. Robots opt in via save or `persist:true`.
8. **Path traversal (lock #4)** — `camera_id` of `../etc/passwd` must reject, not escape the calibration dir.
9. **Depth maps on disk (lock #3 / STACK)** — privacy + size. Persist scale/offset + fingerprint only.
10. **Second apply site (lock #12)** — persist must not scale maps in CLI/routes/store.
11. **Scope creep** — uniqueID/RTSP fingerprint fields, profile YAML, platformdirs, wizard chrome, docs (18), FSD, DetectionLoop/FrameBus/ORT/`kind_for_mode`.

---

## Code Examples

See `17-PATTERNS.md` for full target APIs. Summary:

```python
def default_calibration_dir() -> Path:
    env = os.environ.get("SENTRY_CALIBRATION_DIR")
    if env:
        return Path(env)
    cache = os.environ.get("SENTRY_MODEL_CACHE")
    root = Path(cache) if cache else default_cache_root()
    return root / "calibration"

def safe_camera_stem(camera_id: str) -> str:
    # reject empty, "..", "/", "\\"; allow [A-Za-z0-9._-]+ after sanitize
    ...

def fingerprints_match(
    saved: CalibrationFingerprint,
    live: CalibrationFingerprint,
) -> tuple[bool, str | None]:
    if saved.camera_id != live.camera_id:
        return False, "camera_id"
    if saved.depth_mode is not None and saved.depth_mode != live.depth_mode:
        return False, "depth_mode"
    if saved.model_id is not None and saved.model_id != live.model_id:
        return False, "model_id"
    if (
        saved.width is not None
        and live.width is not None
        and saved.width != live.width
    ) or (
        saved.height is not None
        and live.height is not None
        and saved.height != live.height
    ):
        return False, "resolution"
    return True, None
```

`try_reapply` (control plane, not I/O):

```python
def try_reapply(
    state: CalibrationState,
    path: Path,
    live: CalibrationFingerprint,
) -> ReapplyResult:
    loaded = load_params(path)          # none | ok | error
    if loaded.status == "none":
        state.set_persist_status("none")
        return ReapplyResult("none", path=path)
    if loaded.status == "error":
        state.set_persist_status("error", loaded.reason)
        return ReapplyResult("error", reason=loaded.reason, path=path)
    ok, why = fingerprints_match(loaded.params.fingerprint, live)
    if not ok:
        state.set_persist_status("ignored_mismatch", why)
        return ReapplyResult("ignored_mismatch", reason=why, path=path)
    state.apply_params(loaded.params)   # no draft samples
    state.set_persist_status("applied")
    return ReapplyResult("applied", path=path)
```

Late size (DepthLoop, before `apply_map`):

```python
ok, why = fingerprints_match(applied.fingerprint, live_now)
if not ok:
    state.clear_applied()
    state.set_persist_status("ignored_mismatch", why)
# then existing promote_kind_unit + apply_map
```

---

## Open Questions (RESOLVED)

1. Cache root vs `~/.config` JSON? → **STACK:** `$SENTRY_MODEL_CACHE` / `default_cache_root()` / YAML. No platformdirs.
2. Auto-apply vs inactive-until-wizard? → **Auto-apply** when file present **and** fingerprints match (headless robots).
3. Persist on every Apply? → **No.** Explicit save + optional `persist:true`. Session apply remains valid.
4. Clear vs tombstone? → **Delete the file** (unlink). Missing file is `none`. A tombstone file is allowed only if delete is not possible; prefer unlink.
5. Capture uniqueID / RTSP host this phase? → **No.** `camera_id` + mode + model + optional W×H only.
6. Load via fake wizard samples? → **No.** `apply_params`.
7. Who scales maps after load? → **DepthLoop `apply_map` only.**
8. When are W×H compared? → Both sides non-None. Serve may apply first; later product mismatch clears.

---

## Validation Architecture

| Req ID | Behavior | File | Plan |
|--------|----------|------|------|
| PER-01 | Save `CalibrationParams` YAML keyed by sanitized `camera_id` | `test_calibration_store.py` | 17-01 |
| PER-03 | Mismatch refuses apply; stay inactive | `test_calibration_store.py` + persist helper | 17-01 |
| PER-02 | Serve / `try_reapply` matching file → applied without wizard | `test_calibration_persist.py` + CLI inspect | 17-02 |
| PER-04 | Clear deletes file; restart load is `none`; Cancel does not delete | `test_api_calibration.py` + store delete | 17-02 |
| Guard | Corrupt YAML → error, never calibrated | store + persist tests | 17-01 / 17-02 |
| Guard | No depth maps on disk; `safe_load` only; path traversal rejected | `test_calibration_store.py` | 17-01 |
| Guard | Additive persist status + banner; `depth.kind` unchanged by status helper | status / CLI tests | 17-02 |

Seed (must stay green while planning; execute uses the same plus new cases):

```bash
uv run pytest tests/test_calibration_state.py tests/test_calibration_fit.py tests/test_api_calibration.py tests/test_cli_calibration_inject.py tests/test_depth_loop.py -q
```

---

## Security Domain

| Threat | Mitigation |
|--------|------------|
| Wrong camera/model auto-apply | `fingerprints_match` before `apply_params` |
| Path traversal via `camera_id` | `safe_camera_stem` reject `..` / separators |
| YAML bomb / arbitrary object | `yaml.safe_load` only + Pydantic `extra=forbid` |
| Torn write | temp file + `os.replace` |
| Depth map / PII on disk | persist params + fingerprint only |
| Clear-then-resurrect | unlink on Clear |
| `yaml.load` / platformdirs / new deps | grep + lock #13 |
| FSD / motor fields | extra=forbid; out of scope |

---

## Phase Requirements

| ID | Research Support |
|----|------------------|
| PER-01 | YAML save keyed by sanitized `camera_id` + fingerprint fields |
| PER-02 | `try_reapply` on serve; matching file → `apply_params` |
| PER-03 | Hard-refuse mismatch; visible `ignored_mismatch` |
| PER-04 | Clear deletes file; Cancel draft-only |

### Must ship
1. `config/calibration_store.py` (path, sanitize, save/load/delete, `fingerprints_match`)
2. `CalibrationState.apply_params` + persist status fields
3. `try_reapply` orchestration (no fake samples)
4. Serve load + `--calibration-file` + banner
5. REST save + `persist:true` on apply + Clear deletes file
6. Late W×H refuse/clear
7. Synthetic tests; zero new deps

### Must not ship
Capture-backend / RTSP uniqueID fingerprint fields; profile YAML merge; platformdirs; JSON persist; depth maps on disk; auto-save on every apply; Cancel-deletes-file; second `apply_map`; DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; wizard redesign; FSD/interlock/motor; docs polish (18).

---

## RESEARCH COMPLETE

**Phase:** 17 - Persist & Re-apply on Serve
**Confidence:** HIGH

Key findings: STACK path + YAML + `safe_load` + atomic write; key by sanitized `camera_id`; hard-refuse `camera_id`/mode/model and W×H when both known; `apply_params` for load; serve auto-applies matching files only; Clear deletes the file; persist status is separate from `depth.kind`; DepthLoop stays the sole scale site.

Ready for planning.
