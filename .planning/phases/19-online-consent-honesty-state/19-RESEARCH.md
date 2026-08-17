# Phase 19: Online consent & honesty state — Research

**Researched:** 2026-08-15
**Domain:** Opt-in default-off online flag + first-scale consent lock + Cancel/Clear/disable-online honesty
**Confidence:** HIGH
**Research flag:** Standard (extend `CalibrationState` / status; no new math)

## Summary

v0.3 already ships draft vs applied, wizard Apply, persist `try_reapply`, Cancel=`clear_draft`, Clear=`clear_applied`+YAML, and `metric_calibrated` only when applied+valid. Phase 19 adds **policy/state only**: an opt-in **session** online flag that boots **off**, cannot invent the first scale, and cannot be confused with Clear. Sampler, auto-commit, persist-policy change, and DepthLoop `apply_map` edits are **Phases 20–21**.

**Primary recommendation:** Extend `CalibrationState` (same lock / snapshot) with `_online_enabled` default `False` and a four-way `online_status`. Do **not** add `OnlineRecalState` (second lock / second snapshot). Do **not** persist the flag to YAML. Serve always constructs `CalibrationState()` with online off; matching `try_reapply` is first-scale consent and still leaves online off.

---

## Locked decisions (do not reopen)

| # | Lock | Value |
|---|------|-------|
| 1 | Default | Online **off** at `CalibrationState()` / serve boot |
| 2 | First scale | First `metric_calibrated` still wizard `apply()` or matching persist `try_reapply`. Enabling online **never** calls `apply` / `apply_params` / `apply_map` |
| 3 | Enable while unapplied | **Refuse** (`ValueError` `online_requires_applied` / REST **409**). Stay `online=False`, `online_status=online_off`. Not “enable-but-idle” |
| 4 | Draft ≠ meters | WIZ-04 holds. Phase 19 does not add a sampler; draft still never promotes |
| 5 | Cancel | Still `clear_draft` only. Applied, YAML, and online flag/status **unchanged** |
| 6 | Clear | Still applied + YAML (`clear_persisted`). Because first-scale consent is gone, Clear **also** forces `online=False` + `online_off` — this is not “disable = Clear” |
| 7 | Disable-online ≠ Clear | `set_online(False)` flips flag + `online_off` only. Applied params, persist status, and YAML file **remain** |
| 8 | Status plane | `online_off` / `online_draft` / `auto_committed` / `rejected` — **separate from** `depth.kind` and persist `none\|applied\|ignored_mismatch\|error` |
| 9 | Phase 19 transitions | Boot/disable/Clear → `online_off`. Enable after applied → `online_draft` (idle; no samples yet). **Never** set `auto_committed` or `rejected` in this phase (enum exists for 21) |
| 10 | Persist of flag | **Session only.** No YAML key, no env, no CLI flag this phase |
| 11 | Home for flag | `CalibrationState` fields + `CalibrationSnapshot` additives (`extra=forbid` unchanged). Not a new class |
| 12 | Out of phase | Sampler, auto-commit, persist policy, DepthLoop `apply_map`, DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`, Live Preview toggle, FSD copy, new deps |

---

## Current APIs (code-verified on main)

| Surface | Today | Phase 19 touch |
|---------|-------|----------------|
| `CalibrationState` | draft/applied, `apply` / `apply_params` / `apply_map`, `clear_draft` / `clear_applied`, persist status | Add `_online_enabled`, `_online_status`, `is_online`, `set_online` |
| `CalibrationSnapshot` | `applied`, `valid`, draft counts, scale/method/fingerprint, `persist_status` / `persist_reason` | Add `online: bool = False`; `online_status` default `online_off` |
| `try_reapply` | match → `apply_params`; mismatch/error/none stay inactive | **Unchanged.** After match, `is_applied()` True and `is_online()` False |
| Cancel route | `clear_draft` + drop freeze pin; no smoother reset | **Unchanged** except snapshot now includes online fields |
| Clear route | `clear_persisted` (applied + draft + delete YAML) + smoother reset | Must leave online off (consent gone); must **not** be how disable is implemented |
| `GET /api/depth/calibration` | `_snapshot_payload` = `snapshot().model_dump()` + samples + frozen | Additive fields appear automatically once snapshot grows |
| `GET /api/status` | `calibration_active`, `calibration_persist`, scale/method | Additive `calibration_online` + `calibration_online_status` (19-02). Never overwrite `depth_kind` or persist |
| DepthLoop `apply_map` | Sole map apply site | **Frozen** |

---

## Plan split

| Plan | Wave | Req | Delivers |
|------|------|-----|----------|
| **19-01** | 1 | ONL-01 (flag), ONL-02 | Session flag default off; `set_online` first-scale lock; `apply` / `apply_params` / `try_reapply` still the only first-scale paths |
| **19-02** | 2 (`depends_on: 19-01`) | ONL-06 + ONL-01 status | Cancel/Clear/disable-online matrix; four-way `online_status` on snapshot + GET; thin `POST /api/depth/calibration/online` |

---

## Considered and rejected

| Idea | Why not |
|------|---------|
| New `OnlineRecalState` | Second lock / second snapshot; research + user brief prefer `CalibrationState` |
| YAML persist of the flag | Restarts would surprise headless robots; user + research: session + status field |
| Enable-while-unapplied as idle-on | Phase 20 could then sample toward a first scale. Refuse is the honesty lock |
| CLI / env toggle this phase | Serve boot-off is enough; REST thin POST is the operator surface (19-02) |
| Live Preview toggle this phase | Status + REST first; UI copy is Phase 22 |
| Sampler / `apply_params` auto-commit / `apply_map` edits | Phases 20–21 |

---

## Must not ship (this phase)

- Online sampler, N-window, throttle, residual gate, auto-commit
- Persist policy change (auto-commit still does not exist; YAML write rules stay v0.3)
- DepthLoop `apply_map` formula or call-site changes
- DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`
- New pip deps; `pyproject` 0.1.0 bump; FSD / vehicle-grade claims
- Collapsing `online_status` into `depth.kind` or persist status

---

## RESEARCH COMPLETE

**Phase:** 19 — Online consent & honesty state
**Confidence:** HIGH

Key findings: consent-once + default-off is a `CalibrationState` session flag; first scale stays Apply / `try_reapply`; Cancel/Clear stay v0.3; disable-online is not Clear; four-way status is a third plane.

Ready for planning.
