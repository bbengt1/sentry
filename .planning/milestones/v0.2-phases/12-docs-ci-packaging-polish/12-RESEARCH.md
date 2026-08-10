# Phase 12: Docs, CI & Packaging Polish - Research

**Researched:** 2026-08-10  
**Domain:** Documentation honesty, AGPL lineage, CI/static packaging gates (no Jetson hardware)  
**Confidence:** HIGH

## Summary

Phase 12 is a **docs + test-hardening** closeout for v0.2 Edge Runtime. Live ORT/TRT factory behavior, sticky soft/strict fallback, dual-model guardrails, and export-doc keyword suites already shipped in Phases 8–11. What remains is **discoverability and consistency** of the export → place artifact → `sentry serve --profile …` narrative, **AGPL lineage for YOLO-derived `.onnx`/`.engine`**, and **CI/packaging locks** so contributors never need Jetson or TensorRT GPU in default GitHub Actions.

Evidence from the repo shows a clear split: `docs/export/*` and factory unit tests already describe live ORT/TRT correctly, while **top-level maker surfaces still carry v1.0 “export-only / still PyTorch” language** (`README.md`, `docs/desktop-gpu.md`, `scripts/export/README.md`). `THIRD_PARTY_MODELS.md` documents AGPL for YOLO/YOLOE weights but does **not** yet state that ORT/TRT artifacts derived from those weights stay under the same AGPL commercial caution. CI is already Jetson-free (`ubuntu-latest`, `uv sync --extra dev` only) but is **not locked by a static test**.

**Primary recommendation:** Plan 12-01 refreshes root + desktop + export hub docs into a numbered export→serve narrative (with/without UI), extends `THIRD_PARTY_MODELS` AGPL lineage for `.onnx`/`.engine`, and keyword-tests those claims (no FPS). Plan 12-02 hardens CI/packaging with static asserts on `.github/workflows/ci.yml`, gitignore for artifacts, and a consolidated selection/fallback matrix gate that reuses existing factory/honesty tests — no new runtime packages, no real YOLO engine loads.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| End-to-end edge serve narrative (EDGE-DOC-01) | Docs / CDN-static | CLI help text | Makers follow docs; code path already exists in factory + CLI |
| AGPL / THIRD_PARTY lineage (EDGE-DOC-02) | Docs | Keyword tests | License policy is documentation + static asserts, not runtime |
| Backend selection / missing-artifact honesty (EDGE-CI-01) | Unit tests (pytest) | API/status surface | Factory is sole author of `backend_live`; CI proves matrix with mocks |
| GHA without Jetson/TRT GPU (EDGE-CI-02) | CI workflow | Static workflow tests | Default job must stay `ubuntu-latest` + `uv sync --extra dev` |
| Packaging hygiene (no engines in wheel, no tensorrt extra) | `pyproject.toml` / hatch | Static packaging tests | Wheel only packages `src/sentry_ai` + profiles + UI static |
| No fake FPS claims | Docs keyword tests | Export + product docs | Measure-on-device language already partial; extend to root surfaces |
| Live ORT/TRT inference | API / Backend (already shipped) | — | Out of scope for new implementation; docs must match factory |

---

## Standard Stack

### Core (already in project — do not replace)

| Library / tool | Version (verified) | Purpose | Why Standard |
|----------------|--------------------|---------|--------------|
| Python | 3.11 (CI); local may be newer | Runtime | Project `requires-python >=3.11` `[VERIFIED: pyproject.toml + ci.yml]` |
| pytest | 9.1.1 (env) / `>=8` pin | Unit + keyword docs tests | Existing suite (~555 tests) `[VERIFIED: uv run]` |
| ruff | 0.16.1 (env) / `>=0.8` pin | Lint in CI | Existing CI step `[VERIFIED: uv run + ci.yml]` |
| uv | 0.11.x | Install/sync | CI + docs install path `[VERIFIED: ci.yml]` |
| hatchling | `>=1.26` | Wheel build | `packages = ["src/sentry_ai"]` only `[VERIFIED: pyproject.toml]` |
| GitHub Actions | `ubuntu-latest` + `astral-sh/setup-uv@v5` | CI | No self-hosted / GPU runners `[VERIFIED: .github/workflows/ci.yml]` |

### Supporting (docs/test patterns already established)

| Pattern | Purpose | When to Use |
|---------|---------|-------------|
| Keyword / static doc tests (`tests/test_export_docs.py`, `tests/test_desktop_docs.py`, `tests/test_third_party_models_doc.py`) | Lock honesty language without hardware | EDGE-DOC-01/02 |
| Factory mock matrix (`tests/test_detection_factory.py`) | Selection + soft/strict reasons without Jetson | EDGE-CI-01 |
| Packaging static tests (`tests/test_pyproject_onnx_extra.py`) | No `tensorrt` extra; onnx CPU pin | Packaging hygiene |
| Optional `onnx` extra | CPU ORT for makers; **not** required in CI | Document only |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| New `docs/edge-serve.md` hub | Only patch `docs/export/*` | Hub mirrors `desktop-gpu.md` discoverability (recommended); patch-only risks README still lying |
| Real Jetson self-hosted GHA | Mock-only CI (status quo) | Hardware CI is deferred forever for EDGE-CI-02 — do not add |
| Legal counsel AGPL memo | Project policy language in THIRD_PARTY_MODELS | Policy doc is enough for EDGE-DOC-02; legal certainty is out of scope |

**Installation:** None — Phase 12 should **not** add packages.

**Version verification:** pytest 9.1.1, ruff 0.16.1 via `uv run` in this session (2026-08-10). CI pins Python 3.11 via `uv python install 3.11`.

---

## Package Legitimacy Audit

> Phase installs **no** external packages. Existing optional extras (`dev`, `detect`, `depth`, `onnx`) are unchanged.

| Package | Registry | Age | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|-----|-----------|-------------|-----------|-------------|
| — | — | — | — | — | n/a | **No new installs** |

**Packages removed due to slopcheck [SLOP] verdict:** none  
**Packages flagged as suspicious [SUS]:** none  
**slopcheck:** skipped — no candidate packages to install

---

## Architecture Patterns

### System Architecture Diagram

```text
Maker machine / Jetson
  │
  ├─(1) uv sync --extra detect [--extra onnx] [--extra depth]
  ├─(2) scripts/export/export_yolo.py --format onnx|engine
  │        └─ produces allowlisted yolo26{n,s,m}.onnx|.engine ON DEVICE
  ├─(3) Place artifact: SENTRY_DETECTOR_ONNX | SENTRY_DETECTOR_ENGINE
  │        or allowlisted cache/cwd stem (BACK-04)
  └─(4) sentry serve --profile cpu-fallback|jetson|desktop-gpu [--no-ui]
           │
           ▼
     build_detection_worker(profile_runtime)  ── once, sticky
           │
           ├─ preferred + artifact + dep  → backend_live=onnxruntime|tensorrt
           ├─ soft miss (default)         → backend_live=torch + reason
           └─ strict miss                 → worker=None, Exit(1)
           │
           ▼
     DetectionLoop / FrameBus / PerceptionStore / /v1  (frozen spine)
           │
           ▼
     Status/banner/UI: backend_requested vs backend_live + reason
```

### Recommended doc / test surface (no new runtime modules)

```text
docs/
├── edge-serve.md              # NEW (recommended hub) — export→serve numbered path
├── desktop-gpu.md             # FIX stale "not live TRT / still PyTorch"
├── README.md                  # Link edge hub; versioning honesty for v0.2
├── cli.md                     # Optional: edge profile + env examples
├── configuration.md           # Already accurate (reference, light touch)
├── architecture.md            # Already accurate (reference)
└── export/
    ├── README.md              # FIX Phase-7 deferral; point to edge hub
    ├── yolo26-onnx-tensorrt.md  # Already live ORT/TRT (light refresh)
    └── jetson-packaging.md    # Already strong (link from hub)

README.md                      # FIX Export section + jetson profile table
THIRD_PARTY_MODELS.md          # ADD AGPL lineage for derived .onnx/.engine
scripts/export/README.md       # FIX "stays on PyTorch profiles"
.github/workflows/ci.yml       # LOCK via static test (content likely unchanged)
.gitignore                     # ADD *.engine *.onnx (artifacts not committed)
tests/
├── test_export_docs.py        # EXTEND: e2e narrative + root README honesty
├── test_third_party_models_doc.py  # EXTEND: AGPL derived artifacts
├── test_edge_ci_workflow.py   # NEW: GHA no Jetson/GPU/tensorrt runner
├── test_pyproject_onnx_extra.py    # EXTEND optional: wheel force-include hygiene
└── test_detection_factory.py  # Reference matrix (likely no code change)
```

### Pattern 1: Keyword-locked documentation honesty
**What:** Pytest reads markdown and asserts required phrases / forbids stale lies.  
**When to use:** Any claim that must survive future edits (live conditions, AGPL, no FPS).  
**Example:** Existing `tests/test_export_docs.py` pattern — extend for root README + THIRD_PARTY.

### Pattern 2: Mock factory matrix (no hardware)
**What:** Monkeypatch `_try_resolve_artifact` + dep probes; inject `FakeModel`.  
**When to use:** EDGE-CI-01 selection / missing-artifact / live success paths.  
**Example:** `tests/test_detection_factory.py` live ORT/TRT success + soft/strict miss matrix (already complete for functional coverage).

### Pattern 3: Packaging static gates
**What:** Parse `pyproject.toml` / workflow YAML as text or tomllib; assert absences.  
**When to use:** No `tensorrt` extra, no GPU runner, no engines in wheel includes.  
**Example:** `test_no_tensorrt_optional_extra` — clone for `ci.yml` and force-include.

### Anti-Patterns to Avoid
- **Re-implementing factory logic in Phase 12:** Behavior is done; only document and gate.
- **Adding self-hosted Jetson CI:** Violates EDGE-CI-02 and project milestone lock.
- **Inventing dual-model FPS tables:** Explicitly forbidden by roadmap success criteria.
- **Shipping `.engine` in wheel/repo:** TRT-02 still holds; Phase 12 only strengthens hygiene.
- **Silent README that still says “export-only”:** Creates split-brain with export docs (primary Phase 12 bug).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Live ORT/TRT loaders | New worker wrappers | Existing `build_detection_worker` + Ultralytics `YOLO("*.onnx|engine")` | Phases 9–10 already shipped |
| CI hardware matrix | Self-hosted Jetson runners | Mock factory + keyword docs tests | EDGE-CI-02; cost and flakiness |
| License engine | Custom license scanner | `THIRD_PARTY_MODELS.md` + keyword tests | Policy documentation is the requirement |
| FPS benchmarks in docs | Marketing tables | “Measure on device” language | Roadmap + Phase 10/11 lock |
| Doc test framework | Custom markdown AST harness | Simple `Path.read_text` keyword asserts | Established project pattern |

**Key insight:** Phase 12 value is **consistency locks**, not new inference code. The dangerous failure mode is stale top-level docs that undo Phases 9–11 honesty.

---

## Common Pitfalls

### Pitfall 1: Split-brain docs (export live vs README “export-only”)
**What goes wrong:** Makers read root README / desktop-gpu and believe TRT is still offline-only.  
**Why it happens:** Phases 9–11 updated `docs/export/*` but left v1.0 marketing language on hub surfaces.  
**How to avoid:** Single numbered export→serve path linked from README + docs/README; keyword tests on **root** README, not only `docs/export/README.md`.  
**Warning signs:** Phrases: “not a live TensorRT runtime”, “still PyTorch live”, “Live `sentry serve` stays on PyTorch profiles”.

### Pitfall 2: AGPL silence on derived artifacts
**What goes wrong:** Operators treat `.onnx`/`.engine` as license-free intermediates.  
**Why it happens:** `THIRD_PARTY_MODELS` only lists weight rows; export docs say “AGPL caution” without lineage sentence.  
**How to avoid:** Explicit lineage paragraph: YOLO-derived ORT/TRT artifacts inherit the same AGPL commercial caution as source weights; link Ultralytics license.  
**Warning signs:** No `.onnx` / `.engine` / “derived” in THIRD_PARTY_MODELS.

### Pitfall 3: Accidental artifact commits
**What goes wrong:** Large/non-portable `.engine` or `.onnx` land in git.  
**Why it happens:** `.gitignore` currently ignores `*.pt` only — not `*.engine` / `*.onnx`.  
**How to avoid:** Extend `.gitignore`; optional static test that no tracked `*.engine` exist.  
**Warning signs:** `git status` shows engine files after local export.

### Pitfall 4: “Hardening” by re-running real Ultralytics export in CI
**What goes wrong:** CI becomes slow, network-dependent, flaky.  
**Why it happens:** Confusion between `@pytest.mark.export` opt-in and default suite.  
**How to avoid:** Keep default suite mock-only; CI stays `uv sync --extra dev` without `detect`/`onnx` requirement for green.  
**Warning signs:** Workflow gains `tensorrt`, GPU labels, or `model.export` steps.

### Pitfall 5: Fake or implied FPS
**What goes wrong:** Milestone marketing invents dual-model realtime numbers.  
**Why it happens:** Pressure to “prove” Jetson first-class with numbers.  
**How to avoid:** Keep measure-on-device language; extend keyword forbid for guaranteed FPS on new hub surfaces.  
**Warning signs:** “30 FPS dual-model”, “guaranteed realtime” without methodology.

### Pitfall 6: Over-scoping CLI/runtime changes
**What goes wrong:** Phase bloats into factory refactors.  
**Why it happens:** Docs research surfaces residual load-failure risk (architecture residual note).  
**How to avoid:** Residual first-inference load errors stay documented only; no DetectionLoop rewrite in Phase 12.

---

## Code Examples

Verified patterns from this repository (not external libs):

### Keyword doc assert (export docs pattern)

```python
# Source: tests/test_export_docs.py (project pattern)
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

def test_root_readme_edge_live_path_honesty() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "not a live tensorrt runtime" not in lowered
    assert "docs/export" in text
    assert "sentry serve" in lowered
    assert "--profile" in text
    # Live path discoverable
    assert "onnx" in lowered and ("tensorrt" in lowered or ".engine" in text)
```

### THIRD_PARTY AGPL lineage assert (to add)

```python
# Source: extend tests/test_third_party_models_doc.py
def test_doc_agpl_lineage_for_derived_onnx_engine() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "agpl" in lowered
    assert ".onnx" in lowered or "onnx" in lowered
    assert ".engine" in lowered or "engine" in lowered
    assert "derived" in lowered or "export" in lowered or "lineage" in lowered
```

### CI workflow static lock (to add)

```python
# Source: new tests/test_edge_ci_workflow.py (recommended)
from pathlib import Path

def test_default_gha_no_jetson_or_tensorrt_gpu() -> None:
    yml = (Path(__file__).resolve().parents[1] / ".github/workflows/ci.yml").read_text()
    lowered = yml.lower()
    assert "ubuntu-latest" in lowered
    assert "self-hosted" not in lowered
    assert "tensorrt" not in lowered
    assert "jetson" not in lowered
    # Install path must not require GPU extras for default suite
    assert "uv sync --extra dev" in yml
    assert "--extra detect" not in yml
    assert "--extra onnx" not in yml
```

### Existing factory matrix (reference — do not rewrite)

```python
# Source: tests/test_detection_factory.py
# Live success when artifact + dep mocked; soft miss reasons:
#   ort_artifact_missing | ort_dep_missing | trt_artifact_missing |
#   trt_dep_missing | path_rejected | unsupported_backend
# Strict miss: worker is None, backend_live is None, same reason codes
```

---

## State of the Art (this repo)

| Old Approach (v1.0 / early v0.2 docs) | Current Approach (code + export docs) | When Changed | Impact for Phase 12 |
|--------------------------------------|----------------------------------------|--------------|---------------------|
| Export recipes only; serve always torch | Live fixed-class ORT + TRT via factory | Phases 9–10 | Root/hub docs must catch up |
| Soft-stub “loader not implemented” | Soft/strict sticky with reason codes | Phases 8, 11 | Docs already partially updated |
| Jetson profile “still PyTorch live” | Live TRT when `.engine` + system TRT | Phase 10 | Fix README + desktop-gpu |
| AGPL on `.pt` only in THIRD_PARTY | Need derived `.onnx`/`.engine` lineage | Phase 12 | EDGE-DOC-02 |
| CI without hardware | Same — mock suite | Phases 8–11 | Lock with static test (EDGE-CI-02) |

**Deprecated/outdated language to remove:**
- README: “not a live TensorRT runtime in Sentry v1”
- README profile table: jetson “still PyTorch live”
- `docs/desktop-gpu.md`: “still PyTorch live path”; “Not a live TensorRT runtime”
- `scripts/export/README.md`: “Live `sentry serve` stays on PyTorch profiles”
- `docs/export/README.md`: “later release doc (Phase 7 plan 07-03)” deferral (desktop-gpu.md already exists)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | YOLO-derived `.onnx`/`.engine` should be documented under the same AGPL commercial caution as Ultralytics YOLO weights (project policy) | EDGE-DOC-02 | Legal nuance may differ by jurisdiction; docs should say “evaluate AGPL obligations” not “we certify compliance” |
| A2 | A dedicated `docs/edge-serve.md` hub is better UX than only patching export docs | Architecture Patterns | Alternative: expand jetson-packaging + README only — still acceptable if e2e steps are keyword-tested |
| A3 | No package version bumps or new extras are required for Phase 12 | Standard Stack | If CI later needs `httpx2` for Starlette warning, that is orthogonal cleanup |
| A4 | Default CI remains without `detect`/`onnx` extras and full suite stays green | EDGE-CI-02 | If a test accidentally imports heavy deps at collection, CI could break — factory already avoids hard imports |

**If A1 needs user confirmation:** Prefer policy wording: “Artifacts exported from AGPL Ultralytics YOLO weights remain subject to the same AGPL commercial caution — see Ultralytics license; not legal advice.”

---

## Open Questions

1. **Dedicated `docs/edge-serve.md` vs expand existing files only?**
   - What we know: `desktop-gpu.md` is the successful primary-path pattern; export docs are accurate but secondary.
   - What's unclear: User preference for new file vs minimal diff.
   - Recommendation: **Add thin `docs/edge-serve.md` hub** with numbered steps + links into export detail pages; fix root README/desktop-gpu; keyword-test hub + README. Planner may collapse to “no new file” if diff budget is tight — success criteria still require a followable e2e path.

2. **Should CHANGELOG get an Unreleased / 0.2.0 section for live ORT/TRT?**
   - What we know: CHANGELOG 0.1.0 still says export recipes only.
   - What's unclear: Whether packaging polish includes changelog/version bump.
   - Recommendation: Add **Unreleased** notes for live ORT/TRT docs honesty; **do not** bump package version unless user wants a release cut in this phase.

3. **Manual Jetson validation checklist ownership?**
   - What we know: Real engine load remains manual-only (Phases 10–11).
   - What's unclear: Whether Phase 12 ships a short checklist in docs or only defers.
   - Recommendation: Short “On-device validation checklist” in edge hub (export → import tensorrt → serve → confirm `backend_live`) — manual, not CI.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| uv | docs install recipes / CI | ✓ | 0.11.23 | — |
| Python 3.11+ | project | ✓ | 3.14.6 local; CI 3.11 | CI pins 3.11 |
| pytest | EDGE-CI tests | ✓ | 9.1.1 | — |
| ruff | CI lint | ✓ | 0.16.1 | — |
| onnxruntime | live ORT on maker machine | ✗ (not in default env) | — | Soft-fall / optional `onnx` extra; CI mocks |
| system tensorrt | live TRT | ✗ | — | Soft-fall; CI mocks; on-device only |
| Jetson hardware | real TRT UAT | ✗ | — | Manual-only; not Phase 12 gate |
| GitHub Actions | EDGE-CI-02 | ✓ (workflow present) | ubuntu-latest | — |

**Missing dependencies with no fallback:** none for Phase 12 execution (docs + unit tests only).

**Missing dependencies with fallback:** onnxruntime, tensorrt, Jetson — all intentionally mocked/documented.

**Step 2.6 note:** No new external services required.

---

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — section required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest ≥8 (env 9.1.1) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` (`testpaths = ["tests"]`) |
| Quick run command | `uv run pytest tests/test_export_docs.py tests/test_third_party_models_doc.py tests/test_detection_factory.py tests/test_pyproject_onnx_extra.py tests/test_edge_ci_workflow.py tests/test_desktop_docs.py -q` |
| Full suite command | `uv run pytest -q` |
| Lint | `uv run ruff check src tests` |
| Hardware policy | No Jetson, no system TensorRT, no real `.engine`/`.onnx` load, no weight download in default CI |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDGE-DOC-01 | Export→engine/onnx→`sentry serve --profile …` (± `--no-ui`) narrative discoverable | keyword | `uv run pytest tests/test_export_docs.py tests/test_desktop_docs.py -q` | ⚠️ partial — export yes; root README / hub e2e **Wave 0** |
| EDGE-DOC-01 | No stale “not live TRT / still PyTorch only” on hub surfaces | keyword | extend export/desktop/readme tests | ❌ Wave 0 |
| EDGE-DOC-01 | No fake dual-model FPS guarantees on edge hub | keyword | `test_export_docs_no_guaranteed_dual_model_fps` + hub | ⚠️ export only |
| EDGE-DOC-02 | AGPL documented for ORT/TRT artifacts derived from YOLO | keyword | `uv run pytest tests/test_third_party_models_doc.py -q` | ⚠️ AGPL yes; **derived .onnx/.engine lineage** Wave 0 |
| EDGE-CI-01 | Backend selection matrix (torch/ORT/TRT) | unit | `uv run pytest tests/test_detection_factory.py -q` | ✅ |
| EDGE-CI-01 | Missing-artifact / dep / path honesty soft+strict | unit | `uv run pytest tests/test_detection_factory.py -k 'missing or rejected or strict or soft' -q` | ✅ |
| EDGE-CI-01 | Factory wiring sticky; no DetectionLoop re-resolve | unit | factory sticky + serve single call-site tests | ✅ |
| EDGE-CI-01 | Status honesty pass-through | unit | `uv run pytest tests/test_backend_honesty_status.py -q` | ✅ |
| EDGE-CI-01 | Artifact allowlist | unit | `uv run pytest tests/test_artifact_paths.py -q` | ✅ |
| EDGE-CI-01 | Parity mocks ORT/TRT Detection contract | unit | `tests/test_ort_parity.py` `tests/test_trt_parity.py` | ✅ |
| EDGE-CI-02 | Default GHA no Jetson / TensorRT GPU / self-hosted | static | new `tests/test_edge_ci_workflow.py` | ❌ Wave 0 |
| EDGE-CI-02 | CI install does not require detect/onnx/tensorrt extras | static | same workflow test | ❌ Wave 0 |
| Packaging | No `tensorrt` optional extra | static | `tests/test_pyproject_onnx_extra.py::test_no_tensorrt_optional_extra` | ✅ |
| Packaging | No engines in wheel force-include | static | extend pyproject tests | ⚠️ informal only |
| Packaging | `*.engine`/`*.onnx` gitignore hygiene | static/config | `.gitignore` + optional test | ❌ Wave 0 |

### Existing coverage snapshot (EDGE-CI-01 nearly complete)

| Suite | ~Tests | Role |
|-------|--------|------|
| `test_detection_factory.py` | 37 | Selection, live mock success, soft/strict matrix, sticky |
| `test_backend_honesty_status.py` | 14+ | Status/banner fields |
| `test_artifact_paths.py` | 13 | Allowlist resolution |
| `test_ort_parity.py` / `test_trt_parity.py` | 4 each | Detection contract without hardware |
| `test_export_docs.py` | 16+ | Export-doc honesty keywords |
| `test_pyproject_onnx_extra.py` | 4 | onnx pin + no tensorrt extra |
| `test_edge_rt04_torch_only.py` | 5 | Depth/OV not factory-routed |
| `test_third_party_models_doc.py` | 7 | AGPL/Apache rows — **not** derived artifacts yet |

**~105 tests** already collect in the edge-related subset without Jetson. Full suite **~555** tests.

### Sampling Rate

- **Per task commit:** quick run command above  
- **Per wave merge:** full suite + `uv run ruff check src tests`  
- **Phase gate:** full suite green + `uv run sentry health` (matches CI) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] Extend keyword tests for **root `README.md`** + **`docs/desktop-gpu.md`** + **`scripts/export/README.md`** — forbid stale non-live TRT language; require export→serve discoverability (EDGE-DOC-01)
- [ ] Extend `tests/test_third_party_models_doc.py` — AGPL lineage for derived `.onnx`/`.engine` (EDGE-DOC-02)
- [ ] Add `tests/test_edge_ci_workflow.py` — GHA `ubuntu-latest`, no self-hosted/jetson/tensorrt, `uv sync --extra dev` only (EDGE-CI-02)
- [ ] Optional: extend packaging tests for hatch force-include hygiene + `.gitignore` `*.engine`/`*.onnx`
- [ ] Optional: `tests/test_edge_serve_docs.py` if new hub file is created (mirror `test_desktop_docs.py`)
- [ ] Framework install: already present via `uv sync --extra dev` — no Wave 0 framework install

*(Factory/honesty/parity suites are **not** Wave 0 missing — they already cover EDGE-CI-01 functional matrix. Phase 12 “hardening” is locks + docs, not re-writing factory tests.)*

---

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no | Perception API remains unauthenticated localhost-default (existing safety docs) |
| V3 Session Management | no | — |
| V4 Access Control | no (docs phase) | Artifact path allowlist already BACK-04 |
| V5 Input Validation | yes (docs only) | Document only allowlisted env paths (`SENTRY_DETECTOR_*`, `SENTRY_ARTIFACT_ROOT`) |
| V6 Cryptography | no | — |
| V10 Malicious Code / Supply chain | yes | No new deps; no tensorrt pip; no engines in wheel; CI static lock |

### Known Threat Patterns for docs/CI polish

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Docs instruct path traversal for engines | Tampering | Only document allowlisted env/cache stems; never arbitrary download URLs |
| CI gains GPU/self-hosted runner silently | Elevation / Availability | Static workflow test (EDGE-CI-02) |
| AGPL weights redistributed without notice | (compliance) | THIRD_PARTY lineage + README/export AGPL caution |
| Prebuilt multi-SKU engines shipped | Tampering / Denial | gitignore + docs forbid + existing keyword tests |
| Fake performance claims mislead safety users | Spoofing (integrity of claims) | No FPS guarantees; measure-on-device language |

---

## Project Constraints (from CLAUDE.md)

No project-root `CLAUDE.md` / `AGENTS.md` found in the Sentry workspace. Parent user skill note references graphify only — **no additional coding constraints** beyond repository conventions already used:

- Perception-only (no motor APIs)
- Depth honesty (relative ≠ meters)
- Local OSS default (`allow_cloud: false`)
- Localhost default bind
- Optional extras; core/tests mock heavy ML
- Keyword/static tests for docs honesty
- No `tensorrt` pip extra; on-device engines only

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EDGE-DOC-01 | Jetson/desktop edge serve docs cover export → engine/onnx → `sentry serve --profile …` (with or without UI) | Numbered hub path; fix README/desktop-gpu/scripts/export stale language; keyword tests on hub + root |
| EDGE-DOC-02 | AGPL Ultralytics remains documented for ORT/TRT artifacts derived from YOLO weights | Extend `THIRD_PARTY_MODELS.md` lineage + `test_third_party_models_doc.py` |
| EDGE-CI-01 | Unit tests cover backend selection, missing-artifact honesty, factory wiring without Jetson | **Already largely green** — factory/honesty/artifact/parity suites; Phase 12 consolidates gates + docs tests |
| EDGE-CI-02 | No required Jetson or TensorRT GPU in GitHub Actions | `ci.yml` already compliant — add static workflow lock test |

### Roadmap success criteria mapping

| SC | Research finding |
|----|------------------|
| 1. Edge serve docs cover e2e export→serve ± UI | Partial in export/*; **missing cohesive hub + root honesty** |
| 2. AGPL for ORT/TRT derived artifacts | AGPL for weights yes; **derived lineage missing** |
| 3. Unit tests selection/honesty/factory w/o Jetson | **Met in code**; lock + document matrix in plan |
| 4. Default GHA no Jetson/TRT GPU | **Met in workflow**; needs static test lock |

### Planned plan split (from roadmap — research confirms)

| Plan | Focus | Primary reqs |
|------|-------|--------------|
| **12-01** | Edge serve docs + AGPL/export lineage refresh | EDGE-DOC-01, EDGE-DOC-02 |
| **12-02** | CI selection/fallback matrix hardening (no Jetson in GHA) | EDGE-CI-01, EDGE-CI-02 + packaging hygiene |

---

## Prescriptive planner guidance

### 12-01 must change

1. **Root `README.md`**
   - Replace Export section “not a live TensorRT runtime” with live ORT/TRT conditions + link to edge hub/export.
   - Fix profiles table: jetson is live TRT when conditions met (not “still PyTorch live”).
   - Keep no FPS invention.
2. **`docs/desktop-gpu.md`**
   - Remove “Not a live TensorRT runtime”; update jetson profile note to live TRT conditions + link export/edge hub.
3. **`docs/edge-serve.md` (recommended new)** or equivalent single e2e section with numbered steps:
   1. Install extras  
   2. Export onnx/engine (on-device for engine)  
   3. Place artifact / set env  
   4. `sentry serve --profile cpu-fallback|jetson …`  
   5. Headless `--no-ui`  
   6. Confirm status `backend_requested` / `backend_live`  
   7. Soft vs strict pointer  
   8. Dual-model measure-on-device; no FPS claim  
4. **`docs/export/README.md`**: remove Phase 7/07-03 deferral; point to desktop-gpu + edge hub; keep live recipes.  
5. **`scripts/export/README.md`**: remove “serve stays on PyTorch profiles”; point to live conditions.  
6. **`THIRD_PARTY_MODELS.md`**: AGPL lineage section for derived `.onnx`/`.engine` from YOLO/YOLOE weights.  
7. **`docs/README.md`**: link edge path; optional versioning note that package is 0.1.0 while planning milestone is v0.2 edge runtime.  
8. **Keyword tests** for all of the above (TDD: RED then GREEN).

### 12-02 must change

1. **`tests/test_edge_ci_workflow.py`** (new) locking `.github/workflows/ci.yml`.  
2. **Confirm EDGE-CI-01 matrix** via existing factory suite in plan verification (no rewrite unless a gap is found during RED).  
3. **Packaging hygiene:** `.gitignore` `*.engine` `*.onnx`; optional force-include assert; keep `test_no_tensorrt_optional_extra`.  
4. **Do not** modify CI to install GPU extras or add runners.  
5. Optional: single test module docstring or comment table mapping reason codes × soft/strict as living matrix documentation.

### Out of scope (do not plan)

- Live ORT/TRT for depth or open-vocab  
- Prebuilt multi-SKU engines in wheel  
- Real Jetson GHA  
- DetectionLoop / FrameBus / `/v1` redesign  
- FPS benchmark publication  
- `tensorrt` pip extra  
- New runtime dependencies  

---

## Sources

### Primary (HIGH confidence)

- [VERIFIED: codebase] `.github/workflows/ci.yml` — single `ubuntu-latest` job; `uv sync --extra dev`; ruff + pytest + `sentry health`
- [VERIFIED: codebase] `pyproject.toml` — extras `dev|detect|depth|onnx`; no tensorrt; hatch wheel packages + profiles + UI static only
- [VERIFIED: codebase] `README.md` L76, L287–290 — stale non-live TRT language
- [VERIFIED: codebase] `docs/desktop-gpu.md` L113–124 — stale PyTorch-only / not-live-TRT claims
- [VERIFIED: codebase] `docs/export/{README,yolo26-onnx-tensorrt,jetson-packaging}.md` — live ORT/TRT conditions, dual-model, sticky policy
- [VERIFIED: codebase] `THIRD_PARTY_MODELS.md` — AGPL for YOLO/YOLOE weights; no derived artifact lineage
- [VERIFIED: codebase] `tests/test_detection_factory.py` — full soft/strict + live mock matrix
- [VERIFIED: codebase] `tests/test_export_docs.py` — export-doc keyword suite (not root README live claims)
- [VERIFIED: codebase] `.gitignore` — `*.pt` only among weight artifacts
- [VERIFIED: roadmap] `.planning/ROADMAP.md` Phase 12 SCs + plans 12-01/12-02
- [VERIFIED: requirements] `.planning/REQUIREMENTS.md` EDGE-DOC-01/02, EDGE-CI-01/02
- [VERIFIED: prior summaries] Phase 10-02 / 11-02 SUMMARY — deferred EDGE-DOC/CI to Phase 12

### Secondary (MEDIUM confidence)

- [CITED: .planning/research/SUMMARY.md] Phase 12 seed intent — export→serve narrative, CI matrix, AGPL for onnx/engine, no hero FPS
- [ASSUMED] Ultralytics AGPL commercial implications for exported graphs — document as caution, not legal certification

### Tertiary (LOW confidence)

- None material for planning

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — no new stack; versions verified in env/CI files
- Architecture / gaps: **HIGH** — stale hub language and AGPL lineage gap confirmed by direct file reads
- Pitfalls: **HIGH** — grounded in prior phase decisions and current split-brain docs
- Legal AGPL nuance: **MEDIUM/LOW** — policy documentation is clear; formal legal force of “derived artifact” is [ASSUMED]

**Research date:** 2026-08-10  
**Valid until:** 2026-09-09 (30 days; docs/CI surface is stable)

**Graph context:** `.planning/graphs/graph.json` absent — no graphify queries run.

**CONTEXT.md:** absent — no discuss-phase locked decisions; research follows roadmap requirements only.
