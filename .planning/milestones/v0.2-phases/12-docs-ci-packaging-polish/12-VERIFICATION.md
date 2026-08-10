---
phase: 12-docs-ci-packaging-polish
verified: 2026-08-10T21:31:06Z
status: passed
score: 11/11 must-haves verified
overrides_applied: 0
---

# Phase 12: Docs, CI & Packaging Polish Verification Report

**Phase Goal:** Makers can follow export → engine/onnx → `sentry serve` on desktop/Jetson without fake FPS claims; contributors merge safely without Jetson hardware

**Verified:** 2026-08-10T21:31:06Z  
**Status:** passed  
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Jetson/desktop edge serve docs cover export → engine/onnx → `sentry serve --profile …` (with or without UI) | ✓ VERIFIED | `docs/edge-serve.md` (133 lines): numbered steps 1–8 include export onnx/engine, place artifact, `sentry serve --profile`, §5 headless `--no-ui`, honesty banner/`backend_live` |
| 2 | AGPL Ultralytics remains documented for ORT/TRT artifacts derived from YOLO weights (`THIRD_PARTY_MODELS` lineage) | ✓ VERIFIED | `THIRD_PARTY_MODELS.md` §“Derived ORT / TRT artifacts (AGPL lineage)” covers `.onnx`/`.engine`, same commercial caution, evaluate obligations, not legal advice |
| 3 | Unit tests cover backend selection, missing-artifact honesty, and factory wiring without NVIDIA Jetson in CI | ✓ VERIFIED | Living matrix suites green: factory / honesty / artifact / ORT+TRT parity / EDGE-RT-04 (see Behavioral Spot-Checks); ownership documented in `tests/test_edge_ci_workflow.py` docstring |
| 4 | Default GitHub Actions does not require Jetson or TensorRT GPU | ✓ VERIFIED | `.github/workflows/ci.yml`: single `ubuntu-latest` job; `uv sync --extra dev` only; no self-hosted/jetson/tensorrt/cuda/gpu; ruff + pytest + `sentry health` |
| 5 | Makers can discover the numbered export→serve path from a hub linked at root README | ✓ VERIFIED | README docs table + Export section link `docs/edge-serve.md`; `docs/README.md` start-here row; `test_readme_links_edge_serve_doc` |
| 6 | Root README, desktop-gpu, and scripts/export no longer claim TensorRT is export-only or jetson is still-PyTorch-only | ✓ VERIFIED | Stale-phrase grep clean on hub surfaces; jetson profile row states live TRT when `.engine` + system TensorRT; scripts/export opener describes live fixed-class serve |
| 7 | Live fixed-class ORT/TRT conditions (preferred + artifact + dep) are discoverable from root README and the edge hub | ✓ VERIFIED | Both surfaces publish conditions triad table (torch / ORT / TRT / miss soft-fall) |
| 8 | No invented dual-model FPS or guaranteed realtime claims on edge hub surfaces | ✓ VERIFIED | Hub states “does not invent dual-model FPS” + measure-on-device; keyword forbid `30 fps dual-model` |
| 9 | Export index no longer defers desktop-gpu walkthrough to Phase 7 plan 07-03 | ✓ VERIFIED | `docs/export/README.md` links desktop-gpu + edge-serve; no `Phase 7 plan` / `07-03` |
| 10 | Static tests lock ci.yml so future edits cannot silently add Jetson/GPU requirements | ✓ VERIFIED | `tests/test_edge_ci_workflow.py` asserts ubuntu-latest, forbids self-hosted/tensorrt/jetson/cuda/gpu and ML extras |
| 11 | Packaging hygiene: no tensorrt optional extra; wheel force-include excludes `.engine`/`.onnx`/`.pt`; `*.engine`/`*.onnx` gitignored with `*.pt` | ✓ VERIFIED | tomllib: optional-deps keys `depth,detect,dev,onnx` only; force-include profiles+UI static only; `.gitignore` lines 44–46; zero tracked engines |

**Score:** 11/11 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| -------- | -------- | ------ | ------- |
| `docs/edge-serve.md` | Numbered export→serve e2e hub | ✓ VERIFIED | 133 lines; steps 1–8 + checklist + related links; min_lines 40 met |
| `README.md` | Honest live ORT/TRT Export + jetson row + edge hub link | ✓ VERIFIED | Profiles table + Export section + docs table row |
| `docs/desktop-gpu.md` | Jetson/TRT language matches live factory | ✓ VERIFIED | Live TRT when `.engine` + system TRT; “What this path is not” no longer non-live TRT |
| `docs/export/README.md` | Links desktop-gpu + edge-serve; Phase 7 deferral removed | ✓ VERIFIED | Lines 88–90 point at hubs |
| `scripts/export/README.md` | Live serve conditions pointer; not PyTorch-only | ✓ VERIFIED | Opener states live when preferred+artifact+dep |
| `docs/README.md` | Start-here link to edge-serve | ✓ VERIFIED | Row + package 0.1.0 vs milestone v0.2 note |
| `THIRD_PARTY_MODELS.md` | Derived ORT/TRT AGPL lineage | ✓ VERIFIED | Section + table + Ultralytics license ref |
| `tests/test_edge_serve_docs.py` | Edge hub narrative keyword lock | ✓ VERIFIED | exists/numbered path/README link |
| `tests/test_export_docs.py` | Root/export EDGE-DOC-01 locks | ✓ VERIFIED | `test_root_readme_edge_live_path_honesty`, scripts/export, export index |
| `tests/test_desktop_docs.py` | No stale non-live TRT claims | ✓ VERIFIED | `test_desktop_doc_no_stale_non_live_trt_claim` |
| `tests/test_third_party_models_doc.py` | AGPL lineage keyword lock | ✓ VERIFIED | `test_doc_agpl_lineage_for_derived_onnx_engine` |
| `tests/test_edge_ci_workflow.py` | EDGE-CI-02 static + EDGE-CI-01 ownership | ✓ VERIFIED | 3 tests + living matrix docstring |
| `tests/test_pyproject_onnx_extra.py` | No tensorrt extra + force-include hygiene | ✓ VERIFIED | `test_wheel_force_include_has_no_engines_or_onnx` |
| `.gitignore` | `*.engine` / `*.onnx` with `*.pt` | ✓ VERIFIED | Lines 43–46 with comment |
| `.github/workflows/ci.yml` | Jetson-free default CI | ✓ VERIFIED | Content compliant; left as-is (locked by tests) |
| `tests/test_detection_factory.py` | EDGE-CI-01 matrix (verify-only ref) | ✓ VERIFIED | Suite green; factory not rewritten in phase commits |

### Key Link Verification

| From | To | Via | Status | Details |
| ---- | -- | --- | ------ | ------- |
| `README.md` | `docs/edge-serve.md` | docs table + Export section | ✓ WIRED | `edge-serve` matches at lines 31, 306 |
| `docs/edge-serve.md` | `docs/export/*` + `sentry serve --profile` | numbered steps | ✓ WIRED | export commands, `--profile`, related table |
| `THIRD_PARTY_MODELS.md` | derived `.onnx`/`.engine` AGPL caution | lineage section | ✓ WIRED | Derived section + Ultralytics license link |
| Keyword tests | hub surfaces | `Path.read_text` asserts | ✓ WIRED | export/desktop/edge/third_party suites |
| `tests/test_edge_ci_workflow.py` | `.github/workflows/ci.yml` | static asserts | ✓ WIRED | `CI_YML.read_text` + ubuntu-latest / forbids |
| `tests/test_pyproject_onnx_extra.py` | `pyproject.toml` | tomllib optional-deps + force-include | ✓ WIRED | no tensorrt; force-include clean |
| EDGE-CI-01 verification | `build_detection_worker` matrix | factory/honesty/parity suites | ✓ WIRED | suites green; docstring maps ownership |

### Data-Flow Trace (Level 4)

N/A for dynamic UI data — phase delivers static documentation, CI workflow locks, and packaging hygiene. Keyword tests read real file contents (not hardcoded empty fixtures).

| Artifact | Data Variable | Source | Produces Real Data | Status |
| -------- | ------------- | ------ | ------------------ | ------ |
| Keyword doc tests | `text` / `yml` | `Path.read_text` of repo files | Yes — live markdown/YAML | ✓ FLOWING |
| Packaging tests | tomllib force-include / optional-deps | `pyproject.toml` | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| -------- | ------- | ------ | ------ |
| EDGE-DOC keyword suite | `uv run pytest tests/test_export_docs.py tests/test_desktop_docs.py tests/test_third_party_models_doc.py tests/test_edge_serve_docs.py -q` | included in 120 passed | ✓ PASS |
| EDGE-CI-02 + packaging | `uv run pytest tests/test_edge_ci_workflow.py tests/test_pyproject_onnx_extra.py -q` | included in 120 passed | ✓ PASS |
| EDGE-CI-01 matrix | factory + honesty + artifact + ort/trt parity + edge_rt04 + ci/packaging | **120 passed** in 2.09s | ✓ PASS |
| Stale hub phrases absent | `rg` forbid list on hub surfaces | no matches | ✓ PASS |
| No tracked engines | `git ls-files '*.engine' '*.onnx'` | empty | ✓ PASS |

### Probe Execution

| Probe | Command | Result | Status |
| ----- | ------- | ------ | ------ |
| — | — | No phase-declared or conventional `scripts/*/tests/probe-*.sh` for this docs/CI phase | SKIP |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| ----------- | ---------- | ----------- | ------ | -------- |
| EDGE-DOC-01 | 12-01 | Export → engine/onnx → `sentry serve --profile` (± UI) docs | ✓ SATISFIED | `docs/edge-serve.md` + hub links + keyword suite |
| EDGE-DOC-02 | 12-01 | AGPL caution for YOLO-derived ORT/TRT artifacts | ✓ SATISFIED | `THIRD_PARTY_MODELS.md` Derived section + test lock |
| EDGE-CI-01 | 12-02 | Backend selection / honesty / factory without Jetson | ✓ SATISFIED | Matrix suites green; ownership docstring |
| EDGE-CI-02 | 12-02 | No required Jetson or TensorRT GPU in GHA | ✓ SATISFIED | `ci.yml` + static workflow tests |

No orphaned Phase 12 requirements — all four mapped IDs are claimed by plans and satisfied.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
| ---- | ---- | ------- | -------- | ------ |
| — | — | No `TBD`/`FIXME`/`XXX`/`TODO`/`HACK`/placeholder stubs in phase deliverables | — | Clean |
| — | — | No empty handlers or “not implemented” returns in phase files | — | Clean |
| — | — | Package version remains `0.1.0` (correct — plan forbids 0.2.0 bump) | ℹ️ Info | Intentional |

### Confirmation Bias Counter (disconfirmation pass)

1. **Partial requirement check:** EDGE-DOC-01 “with or without UI” — both path and `--no-ui` are present in hub §4–5; not partial.
2. **Test vs behavior:** Keyword tests are substring locks (do not prove a human completes on-device export). Acceptable: real Jetson/hardware validation was explicitly out of scope for Phase 12.
3. **Error path:** Deleting/editing `ci.yml` to add GPU extras fails static tests; missing gitignore lines fail `test_gitignore_ignores_engine_and_onnx`. Covered.

### Human Verification Required

None required for phase gate. Goal is documentation honesty + CI/packaging locks, fully keyword- and suite-locked without hardware.

Optional (non-blocking) maker smoke if desired later: follow `docs/edge-serve.md` on a real NVIDIA host — not a Phase 12 success criterion.

### Gaps Summary

No gaps. All roadmap success criteria and plan must_haves are present, substantive, wired, and covered by green automated suites.

---

_Verified: 2026-08-10T21:31:06Z_  
_Verifier: Claude (gsd-verifier)_
