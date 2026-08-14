# Phase 18: Docs + Synthetic CI Polish - Research

**Researched:** 2026-08-14
**Domain:** Operator calibration hub, honesty-doc refresh, hardware-free CI inventory lock
**Confidence:** HIGH
**Research flag:** Skip (SUMMARY: content + test expansion; no new runtime design)

## Summary

Phases 13–17 shipped the v0.3 wire: honesty triad, NumPy fit, DepthLoop `apply_map`, wizard REST/UI, free-space meters **only** when `metric_calibrated`, YAML persist + fingerprint refuse. **Docs and CI copy did not catch up.** Hub surfaces still describe free-space as v1-always-ordinal, omit the wizard/persist path, and never mention `metric_calibrated` as an operator-reachable kind. Default GHA is already Jetson-free (`uv sync --extra dev` + ruff + pytest + `sentry health`) and must stay that way.

**Primary recommendation:** Plan **18-01** adds `docs/calibration.md` (operator hub) and refreshes stale hubs under keyword tests (TDD, Phase 12 pattern). Plan **18-02** locks OPS-03 with a thin honesty-matrix test that **documents existing synthetic suites** — no new product code, no `--extra depth`, no room/Jetson/CUDA in CI.

---

## Stale-phrase table (must disappear from current-tense hubs)

Verified on `main` @ `08f636aa` (Phase 17-02 merged).

| Surface | Stale / missing claim | Replacement (locked)
|---------|----------------------|----------------------|
| `README.md` Free-space | `units` (v1 always **ordinal** — not calibrated meters) | `units="m"` **iff** `depth.kind=metric_calibrated` + 1.5/3.0 m cuts; else ordinal |
| `docs/perception-frame.md` | v0.1 free-space **ordinal** (not calibrated meters); **No `distance_m`** | Same triad; optional `distance_m` on cues **only when calibrated** |
| `docs/safety-and-privacy.md` | Free-space cues **are ordinal** (unqualified) | Ordinal unless calibrated; still **not** a safety interlock / not FSD |
| `docs/desktop-gpu.md` | Depth “never labeled as meters”; free-space “ordinal nearness bands” only | Relative default never m; calibrated path exists via wizard |
| `docs/architecture.md` | No CalibrationState / persist; “optional metric labels” only | DepthLoop plug-in + STACK YAML persist; estimated ≠ calibrated |
| `docs/api-reference.md` | No `/api/depth/calibration/*`; no persist status | Wizard REST + `calibration_persist` additive |
| `docs/cli.md` | No `--calibration-file` / persist banner | Flag + `calibration: none\|applied\|ignored_mismatch\|error` |
| `docs/configuration.md` | Cache layout has weights/hf only; no `SENTRY_CALIBRATION_DIR` | `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml` |
| `docs/README.md` | No calibration row; versioning still “v0.2 Edge Runtime” | Link hub; note v0.3 UX (package stays **0.1.0**) |
| `CHANGELOG.md` Unreleased | v0.2 edge-doc notes only | Add v0.3 operator-docs honesty; **do not** rewrite `[0.1.0]` history |

**Keep (not stale):** safety “not an autonomous driving / FSD stack”; perception-only denylist; localhost default; “not a safety interlock”; CHANGELOG `[0.1.0]` historical ordinal wording.

---

## Persist / honesty locks (authoritative — do not reopen)

| # | Lock | Value |
|---|------|-------|
| 1 | Persist path | **STACK:** `$SENTRY_MODEL_CACHE/calibration/{safe_id}.yaml` (else `default_cache_root()`). Optional `SENTRY_CALIBRATION_DIR` + `--calibration-file`. YAML. **Not** `~/.config` JSON / platformdirs |
| 2 | Honesty triad | Relative **never** `unit="m"`. `metric_estimated` ≠ calibrated. `metric_calibrated` + `m` **only** when applied+valid. Draft **never** claims calibrated |
| 3 | Free-space | `units="m"` iff `metric_calibrated` **and** absolute 1.5 / 3.0 m cuts. Else ordinal. Optional `distance_m` when calibrated. `nearness_*` stay 0..1 |
| 4 | Cancel vs Clear | **Cancel** = draft-only (no file delete, no `clear_applied`). **Clear** deletes YAML so restart cannot resurrect |
| 5 | Persist status | Additive `none \| applied \| ignored_mismatch \| error`, **separate from** `depth.kind` |
| 6 | Wizard copy | Approximate metric scale; monocular; **not vehicle-grade**; not FSD |
| 7 | Keyword tests | Forbid stale “always ordinal” / FSD-as-claim / “precise meters” / autonomous-as-claim |
| 8 | CI | Do **not** require room, Jetson, CUDA, `--extra depth`. Keep `ci.yml`: `uv sync --extra dev` + ruff + pytest + `sentry health` |
| 9 | Constraints | Zero new deps; no product-feature creep; freeze DetectionLoop / FrameBus / ORT-TRT / `kind_for_mode`; **do not** bump `pyproject` 0.1.0 |
| 10 | Milestone | After 18 **merges**, v0.3 reqs are closable; `/gsd:complete-milestone` is a **later** step |

---

## Existing test inventory (OPS-03 — already synthetic)

| Theme | Files | Phase |
|-------|-------|-------|
| Fit / reject | `tests/test_calibration_fit.py` | 14 |
| Apply / state | `tests/test_calibration_state.py`, `tests/test_depth_loop.py`, `tests/test_cli_calibration_inject.py` | 13–17 |
| Kind/unit honesty | `tests/test_calibration_validators.py`, `tests/test_depth_kind_honesty.py`, `tests/test_perception_store_depth_honesty.py`, `tests/test_schemas_depth_kind.py` | 13 |
| Free-space meters | `tests/test_free_space_bands.py`, `tests/test_free_space_loop.py`, `tests/test_assemble_perception_frame.py`, `tests/test_api_calibration_smoother.py` | 16 |
| Persist / serve | `tests/test_calibration_store.py`, `tests/test_calibration_persist.py`, `tests/test_api_calibration.py` | 17 |
| Docs keywords (v0.2) | `tests/test_export_docs.py`, `tests/test_desktop_docs.py`, `tests/test_edge_serve_docs.py`, `tests/test_safety_docs.py`, `tests/test_third_party_models_doc.py` | 12 |
| CI lock | `tests/test_edge_ci_workflow.py` | 12 |

**Gap:** no operator calibration hub; no keyword lock against “always ordinal”; no living v0.3 matrix module. **Not a gap:** room/Jetson/CUDA in default CI (already forbidden).

---

## Plan split

| Plan | Wave | Req | Delivers |
|------|------|-----|----------|
| **18-01** | 1 | OPS-02 | `docs/calibration.md` + refresh stale hubs + TDD keyword tests |
| **18-02** | 2 (`depends_on: 18-01`) | OPS-03 | Thin `tests/test_v03_honesty_matrix.py` + confirm `ci.yml` / `test_edge_ci_workflow.py` lock; **no runtime product code** |

---

## Must not ship

- New product features, REST handlers, wizard HTML redesign, second `apply_map`
- DetectionLoop / FrameBus / ORT-TRT factory / `kind_for_mode` edits
- New pip deps; `pyproject` 0.1.0 → 0.3.0 bump
- `~/.config` JSON / platformdirs persist docs (ARCHITECTURE opinion overruled)
- CI: `--extra depth` / detect / onnx / tensorrt; Jetson; CUDA; physical room; real DAV2 weights
- FSD / vehicle-grade / precise-meter / autonomy-as-capability claims
- Closing REQUIREMENTS checkboxes or running complete-milestone in this phase

---

## RESEARCH COMPLETE

**Phase:** 18 - Docs + Synthetic CI Polish
**Confidence:** HIGH

Key findings: split-brain is docs-only; persist/honesty already locked on the wire; CI already hardware-free — lock it and write the operator hub.

Ready for planning.
