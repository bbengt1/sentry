---
phase: 13-honesty-contracts-calibrationstate
verified: 2026-08-11T14:09:01Z
status: passed
score: 10/10 must-haves verified
overrides_applied: 0
---

# Phase 13: Honesty Contracts & CalibrationState Verification Report

**Phase Goal:** Depth honesty contracts and an in-process CalibrationState make `metric_calibrated` + meters reachable only when applied and valid — relative depth can never claim meters

**Verified:** 2026-08-11T14:09:01Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | ------- | ---------- | -------------- |
| 1 | Relative (and uncalibrated) depth products reject or never emit `unit="m"` on store / snapshot / `/v1` contracts | ✓ VERIFIED | `assert_depth_kind_unit` rejects relative+`m` and estimated without `m`; `DepthPayload.kind_unit_honesty` + `FreeSpacePayload.free_space_units_honesty` enforce on wire; `PerceptionStore.set_depth` gates before product write; assemble builds `DepthPayload`/`FreeSpacePayload` for `/v1` |
| 2 | `CalibrationState` distinguishes draft vs applied; draft/staging alone does not report as calibrated | ✓ VERIFIED | Separate `_draft_params` / `_applied_params`; `set_draft_params` leaves `is_applied=False` and promote returns base pair (`tests/test_calibration_state.py::test_draft_params_do_not_apply_or_promote`) |
| 3 | Only applied + valid calibration yields pair `depth_kind=metric_calibrated` and `unit="m"` | ✓ VERIFIED | Pure `promote_kind_unit(..., applied=True, valid=True) → (METRIC_CALIBRATED, "m")`; `CalibrationState.promote_kind_unit` passes live applied+valid flags; draft / invalid / cleared applied all return base |
| 4 | Calibration params include fingerprint fields (camera_id, resolution/size, depth mode/model) | ✓ VERIFIED | `CalibrationFingerprint`: `camera_id` (required min_length=1), `width`, `height`, `depth_mode`, `model_id`, `schema_version`; nested required on `CalibrationParams`; snapshot exposes fingerprint when applied |
| 5 | Free-space `units="m"` only when `depth_kind=metric_calibrated`; calibrated+ordinal remains allowed | ✓ VERIFIED | `assert_free_space_units` + FreeSpacePayload matrix tests; estimated/relative + `m` raise; calibrated + ordinal/m both ok |
| 6 | `PerceptionStore.set_depth` rejects dishonest kind/unit before any product write | ✓ VERIFIED | Gate at start of `set_depth` (outside stats try/except); reject leaves `snapshot_depth()` None or prior product unchanged |
| 7 | `kind_for_mode` never returns `METRIC_CALIBRATED` for any mode | ✓ VERIFIED | Production mapping returns RELATIVE or METRIC_ESTIMATED only; `test_kind_for_mode_never_calibrated` parametrized for relative/metric_indoor/metric_outdoor |
| 8 | Invalid apply raises without mutating already-applied; `clear_draft` does not clear applied; `clear_applied` restores base promotion | ✓ VERIFIED | `test_failed_apply_does_not_wipe_prior_applied`, `test_clear_draft_after_apply_leaves_applied`, `test_clear_applied_restores_base_promotion` |
| 9 | Structural validity rejects non-positive/non-finite scale and non-finite offset; residual RMS deferred | ✓ VERIFIED | `is_valid_calibration_params` uses `math.isfinite`; sample floor for non-manual methods; no residual threshold policy in Phase 13 |
| 10 | No DepthLoop hook, REST/UI, YAML I/O, or `apply_map` shipped (phase boundary held) | ✓ VERIFIED | Phase commits touch only validators/perception/store/calibration schemas+state + tests; no `def apply_map`; Phase 14 handoff documented in `calibration_state.py` module docstring |

**Score:** 10/10 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | ----------- | ------ | ------- |
| `src/sentry_ai/schemas/validators.py` | `assert_depth_kind_unit`, `assert_free_space_units`, `promote_kind_unit`, compatibility `relative_depth_forbids_unit` | ✓ VERIFIED | Full kind↔unit matrix + free-space units + pure promote; substantive, pure stdlib+enums |
| `src/sentry_ai/schemas/perception.py` | DepthPayload + FreeSpacePayload model validators call shared asserts | ✓ VERIFIED | `kind_unit_honesty` / `free_space_units_honesty` after-mode validators |
| `src/sentry_ai/state/perception_store.py` | `set_depth` honesty gate | ✓ VERIFIED | `assert_depth_kind_unit(kind, unit)` before stats/product/lock |
| `src/sentry_ai/schemas/calibration.py` | Fingerprint/Params/Snapshot + structural validity | ✓ VERIFIED | `extra=forbid`; `is_valid_calibration_params` |
| `src/sentry_ai/control/calibration_state.py` | Thread-safe draft/apply/clear + promote wrapper | ✓ VERIFIED | Lock + snapshot mutators; wraps pure promote |
| `src/sentry_ai/control/__init__.py` | Export `CalibrationState` | ✓ VERIFIED | In `__all__` with `PipelineState` |
| `src/sentry_ai/schemas/__init__.py` | Re-export calibration models | ✓ VERIFIED | Fingerprint/Params/Snapshot exported |
| `tests/test_calibration_validators.py` | Kind/unit + free-space + promote matrix | ✓ VERIFIED | Substantive coverage |
| `tests/test_calibration_state.py` | Models + state machine | ✓ VERIFIED | Full draft/apply/clear/promote + fingerprint |
| `tests/test_perception_store_depth_honesty.py` | Store reject without partial write | ✓ VERIFIED | Relative+m, calibrated+None reject; honest accepts |
| `tests/test_schemas_depth_kind.py` | Calibrated/estimated unit=None rejection | ✓ VERIFIED | Extended in phase |
| `tests/test_depth_mapping.py` | Never-calibrated mode guard | ✓ VERIFIED | Parametrized test |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | --- | --- | ------ | ------- |
| `DepthPayload` | `assert_depth_kind_unit` | `@model_validator(mode="after")` `kind_unit_honesty` | ✓ WIRED | `perception.py:48-51` |
| `FreeSpacePayload` | `assert_free_space_units` | `@model_validator(mode="after")` `free_space_units_honesty` | ✓ WIRED | `perception.py:95-98` |
| `PerceptionStore.set_depth` | `assert_depth_kind_unit` | Call before `DepthProduct` construction | ✓ WIRED | `perception_store.py:237-239` |
| pure `promote_kind_unit` | `CalibrationState.promote_kind_unit` | Wrapper passes `applied`/`valid` under lock | ✓ WIRED | `calibration_state.py:123-135` imports as `_promote_kind_unit` |
| `CalibrationState.apply` | `is_valid_calibration_params` | Reject invalid draft without clearing applied | ✓ WIRED | `apply()` lines 91-96 raise; applied only assigned on success |
| `CalibrationParams.fingerprint` | `CalibrationFingerprint` | Required nested model `extra=forbid` | ✓ WIRED | `calibration.py:49` |
| Wire models | `/v1` assemble path | `assemble.py` builds `DepthPayload`/`FreeSpacePayload` | ✓ WIRED | Honesty enforced when frame is constructed |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| `CalibrationState.promote_kind_unit` | `applied` / `valid` | Live `_applied_params` + `is_valid_calibration_params` | Yes — flags derived from real staged/applied params, not hardcoded | ✓ FLOWING |
| `CalibrationState.snapshot` | `scale` / `fingerprint` / `applied` | `_applied_params` under lock | Yes — optional fields populated only when applied | ✓ FLOWING |
| `DepthPayload` / store depth | `kind` / `unit` | Caller + assert gate | Yes — reject path raises; accept path stores caller values | ✓ FLOWING |

No hollow/static stubs: promotion never hardcodes calibrated without applied+valid; draft path returns base pair.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| Phase 13 pytest suite | `uv run pytest tests/test_calibration_validators.py tests/test_calibration_state.py tests/test_schemas_depth_kind.py tests/test_perception_store_depth_honesty.py tests/test_depth_mapping.py tests/test_depth_kind_honesty.py tests/test_free_space_bands.py tests/test_schemas_perception.py -q` | **115 passed** | ✓ PASS |
| Import smoke + promote/draft/fingerprint script | `uv run python -c "..."` (DepthPayload reject, draft no promote, apply promotes, fingerprint fields, failed apply preserves applied) | `SPOT_CHECKS_OK` | ✓ PASS |
| No `apply_map` in tree | `rg 'def apply_map' src/sentry_ai/` | no matches | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No phase-declared or conventional probes for this library phase | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| CAL-04 | 13-01, 13-02 | When calibration is applied and valid, depth products use `depth_kind=metric_calibrated` and `unit="m"` together | ✓ SATISFIED | Pure + state promote only when applied+valid; kind↔unit matrix requires calibrated pair with `"m"`; store accepts calibrated+`m` only |
| CAL-05 | 13-01, 13-02 | Relative and uncalibrated depth never claim meters on store, snapshot, Live Preview, and `/v1` | ✓ SATISFIED | Store gate + wire validators + free-space units gate; `/v1` assemble uses honest wire models. Live Preview UI not in this phase — honesty enforced at contract layer Live Preview will consume (Phase 15) |

**Orphaned requirements:** None — REQUIREMENTS.md maps only CAL-04, CAL-05 to Phase 13; both claimed by plans.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder stubs in phase-modified source | — | Clean |

Debt-marker gate: **pass** (no unreferenced TBD/FIXME/XXX).

Scope boundary commits (no forbidden paths):
- `7aef5bf`, `b9f1578`, `5fff0a6`, `a7d41df`, `ca3ce3a`, `722840a`, `362517b`, `20ce564` — only schemas/validators/store/control/tests; no `models/depth/loop.py`, free-space algorithm, routes, or `index.html`.

### Human Verification Required

None. Pure in-process contracts and state machine fully covered by automated unit tests; no UI, visual, or real-time behavior in this phase's deliverables.

### Gaps Summary

No gaps. All roadmap success criteria (SC1–SC4) and plan must-haves are implemented, wired, and regression-tested. Intentional out-of-scope items (DepthLoop plug-in, wizard REST/UI, free-space meter path, YAML persist, residual RMS thresholds, `apply_map`) belong to Phases 14–17 and are not Phase 13 failures.

---

_Verified: 2026-08-11T14:09:01Z_
_Verifier: Claude (gsd-verifier)_
