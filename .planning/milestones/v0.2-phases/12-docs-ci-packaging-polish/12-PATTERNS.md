# Phase 12: Docs, CI & Packaging Polish - Pattern Map

**Mapped:** 2026-08-10  
**Files analyzed:** 16  
**Analogs found:** 16 / 16  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `README.md` | docs | N/A (keyword-locked) | `docs/export/README.md` live ORT/TRT narrative | role-match |
| `docs/desktop-gpu.md` | docs | N/A | same file + `docs/export/jetson-packaging.md` live TRT | exact (self) / role-match |
| `docs/edge-serve.md` | docs (NEW hub) | N/A | `docs/desktop-gpu.md` numbered e2e path | role-match |
| `docs/export/README.md` | docs | N/A | same file live ORT/TRT sections (retire Phase 7 deferral) | exact |
| `scripts/export/README.md` | docs | N/A | `docs/export/README.md` live serve conditions | role-match |
| `docs/README.md` | docs (index) | N/A | same file Start-here table | exact |
| `THIRD_PARTY_MODELS.md` | docs (policy) | N/A | same file AGPL YOLO rows + References | exact |
| `CHANGELOG.md` | docs (optional) | N/A | same file Keep-a-Changelog structure | exact |
| `tests/test_export_docs.py` | test (keyword) | static file-I/O | same file live ORT/TRT + dual-model suite | exact |
| `tests/test_desktop_docs.py` | test (keyword) | static file-I/O | same file primary-path asserts | exact |
| `tests/test_third_party_models_doc.py` | test (keyword) | static file-I/O | same file AGPL/YOLO rows | exact |
| `tests/test_edge_serve_docs.py` | test (NEW, optional) | static file-I/O | `tests/test_desktop_docs.py` | role-match |
| `tests/test_edge_ci_workflow.py` | test (NEW) | static file-I/O | `tests/test_pyproject_onnx_extra.py` packaging static gates | role-match |
| `tests/test_pyproject_onnx_extra.py` | test (static) | static file-I/O | same file `test_no_tensorrt_optional_extra` | exact |
| `.gitignore` | config | N/A | same file `*.pt` artifact ignore | exact |
| `.github/workflows/ci.yml` | config (lock via test) | N/A | same file — content already correct | exact |

**Plans covered (expected):**  
- **12-01** — Edge serve docs + AGPL/export lineage (EDGE-DOC-01, EDGE-DOC-02)  
- **12-02** — CI/packaging static locks + selection matrix gate (EDGE-CI-01, EDGE-CI-02)

**Unchanged / frozen (do not modify runtime):**  
`build_detection_worker` / DetectionLoop / FrameBus / PerceptionStore / `/v1` / live ORT-TRT loaders / factory reason codes. Factory suite is a **verification reference**, not a rewrite target.

---

## Pattern Assignments

### `README.md` (docs, keyword-locked hub)

**Analog:** `docs/export/README.md` live ORT/TRT sections + `docs/export/jetson-packaging.md` profile table  
**Plan:** 12-01 primary.

**Stale language to remove** (verified lines 76, 285–290):
```markdown
| `jetson` | Jetson-class edge tiers (still PyTorch live) | `--profile jetson` |

## Export (ONNX / TensorRT)

Offline edge packaging recipes — **not** a live TensorRT runtime in Sentry v1.
Live `sentry serve` stays on **PyTorch** profiles (`desktop-gpu`, `jetson`,
`cpu-fallback`). Build TensorRT engines **on-device**; never copy `.engine`
across JetPack SKUs.
```

**Replacement shape — copy honesty from export hub** (`docs/export/README.md` lines 13–22, 62–86):
```markdown
## Export & live edge backends (ONNX / TensorRT)

Export recipes produce allowlisted `.onnx` / on-device `.engine` artifacts.
Live fixed-class serve can use:

| Backend | When live |
|---------|-----------|
| **Torch** (default) | Always available with `detect` extra |
| **ONNX Runtime** | `preferred_backend=onnxruntime` + allowlisted `.onnx` + `uv sync --extra onnx` |
| **TensorRT** | `preferred_backend=tensorrt` + allowlisted `.engine` + system/JetPack TensorRT (no pip extra) |

Missing artifact/dep → soft-fall to torch + honest `backend_reason` (strict opt-in via `SENTRY_FALLBACK_TO_TORCH=false`).
Build engines **on-device**; never copy `.engine` across JetPack SKUs.
Full path: [`docs/edge-serve.md`](docs/edge-serve.md) · recipes: [`docs/export/`](docs/export/).
```

**Profiles table jetson cell — copy from jetson-packaging** (`docs/export/jetson-packaging.md` lines 24–29):
```markdown
| `jetson` | Edge / Jetson — live TRT when `.engine` + system TensorRT; else soft torch | `--profile jetson` |
```

**Keyword-test expectations** (extend `test_export_docs.py` / README tests):
- Forbid: `"not a live tensorrt runtime"`, `"still pytorch live"`
- Require: `docs/export` link, `sentry serve`, `--profile`, onnx + (tensorrt or `.engine`), no invented dual-model FPS

**Existing README link pattern to keep** (lines 17–32 documentation table) — add edge hub row next to export:
```markdown
| [docs/export/](docs/export/) | ONNX / TensorRT export recipes |
| [docs/edge-serve.md](docs/edge-serve.md) | Export → place artifact → `sentry serve` edge path |
```

---

### `docs/desktop-gpu.md` (docs, primary-path sibling)

**Analog:** same file structure + live TRT language from `docs/export/jetson-packaging.md`  
**Plan:** 12-01.

**Stale language to remove** (lines 113–125):
```markdown
# Jetson-class tiers (still PyTorch live path; TRT via export recipes)
uv run sentry serve --profile jetson --source usb --device 0
...
## What this path is not
- Not a measured FPS guarantee  
- Not a live TensorRT runtime (export recipes are offline packaging)  
```

**Replacement — keep FPS honesty, fix TRT claim:**
```markdown
# Jetson-class tiers — live TRT when allowlisted .engine + system TensorRT;
# otherwise soft torch + reason. See docs/edge-serve.md and docs/export/.
uv run sentry serve --profile jetson --source usb --device 0
...
## What this path is not
- Not a measured FPS guarantee  
- Not automatic multi-SKU TensorRT — engines are on-device only  
- Not multi-cam fusion …  
```

**Structure to preserve** (desktop-gpu is the successful hub template):
1. Title + “primary path” framing  
2. Profile table  
3. Prerequisites / Install  
4. Serve command + Expected stages (numbered)  
5. Model cache / Robot clients / `--no-ui`  
6. Related links  

**Analog for edge hub numbering:** this file’s “Expected stages” (lines 54–63) and headless block (lines 84–89).

---

### `docs/edge-serve.md` (docs NEW hub — recommended)

**Analog:** `docs/desktop-gpu.md` (e2e maker path) + `docs/export/README.md` live conditions + `docs/export/jetson-packaging.md` dual-model honesty  
**Plan:** 12-01.

**Recommended module shape (compose existing patterns — do not invent FPS):**
```markdown
# Edge serve — export → artifact → sentry serve

Numbered path for makers who want live fixed-class ORT/TRT on edge hardware.

## 1. Install extras
uv sync --extra detect [--extra onnx] [--extra depth]
# NO --extra tensorrt — use system / JetPack TensorRT on device

## 2. Export artifact (on-device for .engine)
uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx|engine

## 3. Place artifact / set env
# SENTRY_DETECTOR_ONNX | SENTRY_DETECTOR_ENGINE | allowlisted cache/cwd stem

## 4. Serve with profile
uv run sentry serve --profile cpu-fallback|jetson|desktop-gpu --source …

## 5. Headless (optional)
uv run sentry serve --profile jetson --source usb --device 0 --no-ui

## 6. Confirm honesty
# Banner / GET /api/status: backend_requested vs backend_live (+ backend_reason)

## 7. Soft vs strict
# Soft default: fallback_to_torch=true → torch + reason
# Strict: SENTRY_FALLBACK_TO_TORCH=false → fail-closed

## 8. Dual-model (measure on device)
# TRT/torch YOLO + torch DAV2 Small may share GPU — measure on device
# Continuous OV + TRT + DAV2 is not first-class; no dual-model FPS claims

## On-device validation checklist (manual)
1. export engine on this SKU
2. python -c "import tensorrt"
3. sentry serve --profile jetson …
4. confirm backend_live=tensorrt (or honest soft reason)
```

**Copy live condition tables from** `docs/export/yolo26-onnx-tensorrt.md` lines 7–12 and jetson dual-model block lines 60–76.  
**Link out** to detail pages rather than duplicating full export recipes.

**Keyword-test surface:** if file is created, either extend `test_export_docs.py` or add `tests/test_edge_serve_docs.py` mirroring `test_desktop_docs.py`.

---

### `docs/export/README.md` (docs, export index)

**Analog:** same file — already accurate live ORT/TRT; only retire deferral  
**Plan:** 12-01.

**Stale deferral to remove** (lines 88–89):
```markdown
Full desktop-GPU walkthrough is covered in a later release doc (Phase 7 plan
07-03). Edge packaging details live in [jetson-packaging.md](jetson-packaging.md).
```

**Replacement:**
```markdown
Full desktop-GPU walkthrough: [desktop-gpu.md](../desktop-gpu.md).  
End-to-end export → serve path: [edge-serve.md](../edge-serve.md).  
Edge packaging details: [jetson-packaging.md](jetson-packaging.md).
```

**Keep intact** (already keyword-tested by `test_export_docs.py`):
- Live ORT/TRT conditions (lines 13–22, 62–86)  
- Hard rules: on-device, never copy, no prebuilt, measure FPS, AGPL, dual-model sticky (lines 35–49)  
- Soft-fall reason codes  

---

### `scripts/export/README.md` (docs, script hub)

**Analog:** `docs/export/README.md` live serve paragraph  
**Plan:** 12-01.

**Stale opener** (lines 1–4):
```markdown
Offline helpers for makers packaging YOLO weights. **Not** imported by the
`sentry_ai` runtime. Live `sentry serve` stays on PyTorch profiles.
```

**Replacement pattern:**
```markdown
Offline helpers for makers packaging YOLO weights. **Not** imported by the
`sentry_ai` runtime. Live fixed-class serve can use exported `.onnx` / `.engine`
when preferred backend + artifact + dep conditions are met (see
[`docs/export/README.md`](../../docs/export/README.md) and
[`docs/edge-serve.md`](../../docs/edge-serve.md)); otherwise soft-falls to torch.
```

**Keep:** allowlist safety table, on-device engine rule, AGPL pointer, command examples.

---

### `docs/README.md` (docs index)

**Analog:** same file Start-here table (lines 8–21)  
**Plan:** 12-01 light touch.

**Add row pattern:**
```markdown
| [edge-serve.md](edge-serve.md) | Export → artifact → `sentry serve` edge path (ORT/TRT) |
| [export/README.md](export/README.md) | ONNX / TensorRT export recipes (edge packaging) |
```

**Optional versioning note** (lines 31–39 table) — if milestone language updates:
```markdown
| Planning milestone (GSD) | v0.2 Edge Runtime (package may still be 0.1.0) |
```
Do **not** bump package version unless product decides a release cut.

---

### `THIRD_PARTY_MODELS.md` (docs, AGPL lineage)

**Analog:** same file YOLO/YOLOE AGPL rows + References  
**Plan:** 12-01 EDGE-DOC-02.

**Current gap:** AGPL documented for `.pt` weights only; no derived `.onnx`/`.engine` lineage.

**Extension pattern — add section after license table or under Default selection rules:**
```markdown
## Derived ORT / TRT artifacts (AGPL lineage)

Artifacts **exported from** AGPL Ultralytics YOLO / YOLOE weights (including
`.onnx` graphs and TensorRT `.engine` files produced via `model.export` /
`scripts/export/export_yolo.py`) remain subject to the **same AGPL commercial
caution** as the source weights. Operators must evaluate AGPL obligations before
redistributing those artifacts — this is **project policy documentation, not
legal advice**. See the Ultralytics license in References.

| Derived artifact | Source weights | License caution |
|------------------|----------------|-----------------|
| `yolo26{n,s,m}.onnx` | YOLO26 AGPL `.pt` | Same AGPL commercial caution |
| `yolo26{n,s,m}.engine` | YOLO26 AGPL `.pt` (on-device export) | Same AGPL commercial caution |
| YOLOE `.onnx` (experimental) | YOLOE AGPL `.pt` | Same AGPL commercial caution |
```

**Keep:** Apache DAV2 Small default, NC never default, model cache table, Ultralytics license URL (line 54).

**Policy wording rule (RESEARCH A1):** “evaluate AGPL obligations” / “same commercial caution” — **not** “we certify compliance.”

---

### `CHANGELOG.md` (docs, optional Unreleased)

**Analog:** same file Keep-a-Changelog (lines 1–47)  
**Plan:** 12-01 optional.

**Pattern for Unreleased (do not invent FPS; do not bump version unless release cut):**
```markdown
## [Unreleased]

### Changed
- Document live fixed-class ORT/TRT serve conditions (preferred + artifact + dep)
- Root/desktop/export hub honesty: retire “export-only / still PyTorch live” language
- AGPL lineage for YOLO-derived `.onnx` / `.engine` in THIRD_PARTY_MODELS

### Known limitations
- Real engine load remains on-device / manual; default CI is mock-only
```

Retire/soft-edit 0.1.0 known-limitation line 42 if it still claims ORT/TRT are export-only only — prefer Unreleased note rather than rewriting history.

---

### `tests/test_export_docs.py` (test, keyword — primary EDGE-DOC-01 lock)

**Analog:** same file (entire module)  
**Plan:** 12-01 Wave 0 + GREEN.

**Imports / helpers pattern** (lines 1–26) — keep and optionally extend paths:
```python
"""EDGE-03: Export docs honesty keyword assertions (no Jetson / no GPU)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "docs" / "export"

def _read(name: str) -> str:
    path = EXPORT_DIR / name
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")
```

**Existing live ORT/TRT style to clone** (lines 44–97) for root README / hub:
```python
def test_export_docs_live_ort_conditions_and_onnx_extra() -> None:
    yolo = _read("yolo26-onnx-tensorrt.md").lower()
    readme = _read("README.md").lower()
    blob = yolo + "\n" + readme
    assert "onnxruntime" in blob or "onnx runtime" in blob
    assert "live" in blob
    assert "extra onnx" in blob or "--extra onnx" in blob
    ...
```

**New tests to add (mirror structure from RESEARCH + existing dual-model tests):**
```python
def test_root_readme_edge_live_path_honesty() -> None:
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    # Forbid v1.0 export-only lies
    assert "not a live tensorrt runtime" not in lowered
    assert "still pytorch live" not in lowered
    # Discoverability
    assert "docs/export" in text
    assert "sentry serve" in lowered
    assert "--profile" in text
    assert "onnx" in lowered and ("tensorrt" in lowered or ".engine" in text)


def test_scripts_export_readme_not_pytorch_only() -> None:
    text = (REPO_ROOT / "scripts" / "export" / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "stays on pytorch profiles" not in lowered
    assert "live" in lowered or "onnx" in lowered or "engine" in lowered


def test_export_index_no_phase7_deferral() -> None:
    text = _read("README.md")
    assert "Phase 7 plan" not in text
    assert "07-03" not in text
    # Point at existing hubs
    assert "desktop-gpu" in text.lower() or "edge-serve" in text.lower()


def test_edge_hub_e2e_narrative_if_present() -> None:
    hub = REPO_ROOT / "docs" / "edge-serve.md"
    # If planner ships hub, lock numbered path; else skip or assert section elsewhere
    if not hub.is_file():
        pytest.skip("docs/edge-serve.md not shipped")
    text = hub.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "export" in lowered
    assert "sentry serve" in lowered
    assert "--profile" in text
    assert "--no-ui" in text or "headless" in lowered
    assert "backend_live" in lowered or "backend_requested" in lowered
    assert "measure" in lowered
    assert "30 fps dual-model" not in lowered
```

**Keep green without change:** dual-model measure-on-device (211–224), continuous OV non-claim (226–236), sticky/soft/strict (239–251), no Phase 11 deferral (254–264), no guaranteed FPS (267–282).

---

### `tests/test_desktop_docs.py` (test, keyword)

**Analog:** same file  
**Plan:** 12-01.

**Existing pattern** (lines 12–39) — extend with stale-language forbid:
```python
def test_desktop_doc_covers_primary_maker_path() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "desktop-gpu" in lowered
    ...
    assert "--no-ui" in text or "headless" in lowered
```

**Add:**
```python
def test_desktop_doc_no_stale_non_live_trt_claim() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "not a live tensorrt runtime" not in lowered
    assert "still pytorch live" not in lowered
    # Positive: jetson / export / live conditions discoverable
    assert "tensorrt" in lowered or "export" in lowered or "engine" in lowered
```

---

### `tests/test_third_party_models_doc.py` (test, keyword — EDGE-DOC-02)

**Analog:** same file YOLO AGPL tests  
**Plan:** 12-01.

**Imports / path pattern** (lines 1–8):
```python
"""FOUND-05: THIRD_PARTY_MODELS.md license documentation."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "THIRD_PARTY_MODELS.md"
```

**Existing AGPL row style** (lines 39–49) — clone for derived artifacts:
```python
def test_doc_yolo_phase3_active_agpl_and_cache() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "yolo26" in lowered or "yolo" in lowered
    assert "agpl" in lowered
    ...
```

**New test (RESEARCH shape):**
```python
def test_doc_agpl_lineage_for_derived_onnx_engine() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "agpl" in lowered
    assert ".onnx" in lowered or "onnx" in lowered
    assert ".engine" in lowered or "engine" in lowered
    assert (
        "derived" in lowered
        or "export" in lowered
        or "lineage" in lowered
        or "same agpl" in lowered
        or "commercial caution" in lowered
    )
    # Policy honesty: not a legal certification
    # (optional soft check) caution / evaluate language present
    assert "caution" in lowered or "obligations" in lowered or "evaluate" in lowered
```

Keep existing Apache Small / NC / YOLOE tests green.

---

### `tests/test_edge_serve_docs.py` (test NEW, optional)

**Analog:** `tests/test_desktop_docs.py` + `tests/test_export_docs.py`  
**Plan:** 12-01 only if `docs/edge-serve.md` is created.

**Module shape:**
```python
"""EDGE-DOC-01: Edge serve hub keyword assertions (no hardware)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "edge-serve.md"
README_PATH = REPO_ROOT / "README.md"


def test_edge_serve_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_edge_serve_numbered_export_to_serve_path() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "export" in lowered
    assert "sentry serve" in lowered
    assert "--profile" in text
    assert "onnx" in lowered
    assert "tensorrt" in lowered or ".engine" in text
    assert "--no-ui" in text or "headless" in lowered
    assert "backend_live" in lowered or "backend_requested" in lowered
    assert "fallback" in lowered or "soft" in lowered
    assert "measure" in lowered
    assert "30 fps dual-model" not in lowered
    assert "guaranteed" not in lowered or "fps" not in lowered


def test_readme_links_edge_serve_doc() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    assert "docs/edge-serve.md" in readme or "edge-serve" in readme
```

**Alternative:** fold these into `test_export_docs.py` to avoid a new file if diff budget is tight (RESEARCH open question).

---

### `tests/test_edge_ci_workflow.py` (test NEW — EDGE-CI-02)

**Analog:** `tests/test_pyproject_onnx_extra.py` static packaging gates + RESEARCH CI example  
**Plan:** 12-02 primary.

**Packaging static-gate pattern** (`test_pyproject_onnx_extra.py` lines 1–38):
```python
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"

def test_no_tensorrt_optional_extra() -> None:
    extras = _optional_deps()
    assert "tensorrt" not in extras
```

**New module (RESEARCH Code Examples, adapted to real `ci.yml`):**
```python
"""EDGE-CI-02: Default GitHub Actions stays Jetson/GPU-free."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def test_default_gha_no_jetson_or_tensorrt_gpu() -> None:
    yml = CI_YML.read_text(encoding="utf-8")
    lowered = yml.lower()
    assert CI_YML.is_file()
    assert "ubuntu-latest" in lowered
    assert "self-hosted" not in lowered
    assert "tensorrt" not in lowered
    assert "jetson" not in lowered
    # Install path must not require GPU extras for default suite
    assert "uv sync --extra dev" in yml
    assert "--extra detect" not in yml
    assert "--extra onnx" not in yml
    assert "--extra depth" not in yml
    # Smoke steps present (current workflow contract)
    assert "ruff check" in yml or "ruff" in lowered
    assert "pytest" in lowered
    assert "sentry health" in yml


def test_ci_single_job_no_gpu_labels() -> None:
    yml = CI_YML.read_text(encoding="utf-8")
    lowered = yml.lower()
    # No CUDA / GPU runner labels
    assert "cuda" not in lowered
    assert "gpu" not in lowered
    assert "runs-on:" in lowered
```

**Current workflow content already compliant** (`.github/workflows/ci.yml` lines 1–33) — test locks it; do **not** add runners or GPU extras.

---

### `tests/test_pyproject_onnx_extra.py` (test, packaging hygiene)

**Analog:** same file  
**Plan:** 12-02 optional extend.

**Keep green:**
- `test_onnx_extra_exists_with_locked_pin`  
- `test_no_tensorrt_optional_extra`  
- `test_onnx_extra_does_not_pin_gpu_ort`  

**Optional force-include hygiene** (read hatch block from `pyproject.toml` lines 79–84):
```python
def test_wheel_force_include_has_no_engines_or_onnx() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    # force-include only profiles + UI static
    assert 'packages = ["src/sentry_ai"]' in text or "packages = [" in text
    assert "src/sentry_ai/config/profiles" in text
    assert "src/sentry_ai/ui/static" in text
    # Must not package model artifacts
    assert ".engine" not in text
    # .onnx might appear only in comments about optional extra — be careful:
    # assert no force-include path ends with .onnx/.engine
    data = tomllib.loads(text)
    force = data.get("tool", {}).get("hatch", {}).get("build", {}).get(
        "targets", {}
    ).get("wheel", {}).get("force-include", {})
    for src, dst in force.items():
        assert not str(src).endswith((".engine", ".onnx", ".pt"))
        assert not str(dst).endswith((".engine", ".onnx", ".pt"))
```

---

### `.gitignore` (config, artifact hygiene)

**Analog:** same file `*.pt` line (line 42)  
**Plan:** 12-02.

**Current** (ends with weights only):
```gitignore
*.pt
```

**Extension pattern:**
```gitignore
# Local model weights / export artifacts (never commit engines or graphs)
*.pt
*.engine
*.onnx
```

**Optional static test companion:**
```python
def test_gitignore_ignores_engine_and_onnx() -> None:
    text = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "*.engine" in text
    assert "*.onnx" in text
    assert "*.pt" in text
```

Place in `test_edge_ci_workflow.py` or packaging module.

---

### `.github/workflows/ci.yml` (config — lock, likely no edit)

**Analog:** same file  
**Plan:** 12-02.

**Canonical content to preserve** (full file):
```yaml
name: CI

on:
  push:
  pull_request:

jobs:
  lint-and-test:
    name: Lint & test (Python 3.11)
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v4
      - name: Install uv
        uses: astral-sh/setup-uv@v5
        with:
          enable-cache: true
      - name: Set up Python 3.11
        run: uv python install 3.11
      - name: Install dependencies
        run: uv sync --extra dev
      - name: Ruff
        run: uv run ruff check src tests
      - name: Pytest
        run: uv run pytest -q
      - name: CLI health smoke
        run: uv run sentry health
```

**Rules:** do not add `detect`/`onnx`/`depth`/`tensorrt` extras; do not add self-hosted/GPU runners; do not run real `model.export`.

---

### EDGE-CI-01 matrix (reference only — no rewrite)

**Analog:** `tests/test_detection_factory.py` (already complete)  
**Plan:** 12-02 verification gate.

**Soft miss baseline** (lines 41–60):
```python
def test_jetson_tensorrt_soft_stub() -> None:
    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_artifact_missing"
```

**Living matrix (document in plan verification, not new product code):**

| Case | Expect |
|------|--------|
| desktop-gpu default | live=torch, reason=None |
| jetson no artifact (soft) | live=torch, reason=`trt_artifact_missing` |
| cpu-fallback no artifact (soft) | live=torch, reason=`ort_artifact_missing` |
| ORT live mock | artifact + dep → live=`onnxruntime` |
| TRT live mock | artifact + dep → live=`tensorrt` |
| strict miss | worker=None, live=None, same reason codes |
| sticky | factory once at serve; not in DetectionLoop |

**Plan 12-02 verification command:**
```bash
uv run pytest tests/test_detection_factory.py tests/test_backend_honesty_status.py tests/test_artifact_paths.py tests/test_ort_parity.py tests/test_trt_parity.py tests/test_edge_rt04_torch_only.py -q
```

Do **not** re-implement factory logic in Phase 12.

---

## Shared Patterns

### Keyword-locked documentation honesty
**Source:** `tests/test_export_docs.py`, `tests/test_desktop_docs.py`, `tests/test_third_party_models_doc.py`, `tests/test_safety_docs.py`  
**Apply to:** All Phase 12 doc edits  

| Convention | Detail |
|------------|--------|
| Read via `Path.read_text(encoding="utf-8")` | No markdown AST harness |
| `REPO_ROOT = Path(__file__).resolve().parents[1]` | All doc tests |
| Lowercase blob for soft keywords | Keep original case for exact forbid phrases |
| Positive + negative asserts | Require discoverability; forbid stale lies |
| No hardware | Never load `.engine`/`.onnx` graphs |

**Forbid phrases (hub surfaces after Phase 12):**
- `not a live TensorRT runtime` / `not a live tensorrt runtime`
- `still PyTorch live` / `still pytorch live`
- `Live sentry serve stays on PyTorch profiles` / `stays on pytorch profiles`
- `Phase 7 plan` / `07-03` deferral on export index
- Dual-model FPS guarantees (`30 fps dual-model`, bare `guaranteed` + FPS)

**Require phrases (edge narrative):**
- `sentry serve` + `--profile`
- export path (`docs/export` and/or `scripts/export`)
- onnx + (tensorrt or `.engine`)
- soft/fallback or reason codes somewhere on export path
- measure-on-device for dual-model
- AGPL caution + derived `.onnx`/`.engine` lineage on THIRD_PARTY

### Numbered e2e hub docs
**Source:** `docs/desktop-gpu.md`  
**Apply to:** `docs/edge-serve.md` (new) and root README Export rewrite  

```text
Install → Export → Place artifact / env → Serve --profile → optional --no-ui
  → Confirm backend_requested/live → Soft/strict pointer → Dual-model measure-only
```

Link detail pages; do not duplicate full Ultralytics recipes.

### Live ORT/TRT honesty language (already shipped in export/*)
**Source:** `docs/export/README.md`, `yolo26-onnx-tensorrt.md`, `jetson-packaging.md`  
**Apply to:** Root README, desktop-gpu, scripts/export README  

| Backend | Live conditions (copy this triad) |
|---------|-----------------------------------|
| ORT | preferred=onnxruntime + allowlisted `.onnx` + `onnx` extra |
| TRT | preferred=tensorrt + allowlisted `.engine` + system/JetPack `tensorrt` |
| Miss | soft torch + reason; strict fail-closed via `fallback_to_torch=false` |

Never: project `tensorrt` pip extra; prebuilt multi-SKU engines; invent FPS.

### AGPL policy documentation
**Source:** `THIRD_PARTY_MODELS.md` YOLO/YOLOE rows + Ultralytics license link  
**Apply to:** EDGE-DOC-02 lineage section + export AGPL cautions  

- Same commercial caution as source weights for derived graphs/engines  
- “Not legal advice” / “evaluate obligations” tone  
- Keyword-test via `test_third_party_models_doc.py`

### Static packaging / CI gates
**Source:** `tests/test_pyproject_onnx_extra.py` + `.github/workflows/ci.yml`  
**Apply to:** 12-02  

| Gate | Assert |
|------|--------|
| No `tensorrt` optional extra | tomllib extras |
| Wheel force-include | profiles + UI static only; no `.engine`/`.onnx` |
| GHA runner | `ubuntu-latest` only |
| GHA install | `uv sync --extra dev` only |
| GHA forbidden | self-hosted, jetson, tensorrt, cuda/gpu labels, detect/onnx extras |
| gitignore | `*.pt`, `*.engine`, `*.onnx` |

### TDD for docs (RED → GREEN)
**Source:** Phase 11 PATTERNS + existing keyword suites  
**Apply to:** 12-01 and 12-02  

1. Write/extend keyword or static tests first (Wave 0)  
2. Confirm RED on stale language / missing lineage / missing CI lock  
3. Edit docs/config until GREEN  
4. Full suite + ruff  

### No runtime scope creep
**Source:** RESEARCH anti-patterns + Phase 11 spine freeze  
**Apply to:** all plans  

- Do not rewrite factory, DetectionLoop, FrameBus, `/v1`  
- Do not add Jetson self-hosted CI  
- Do not add packages or `tensorrt` extra  
- Do not publish dual-model FPS tables  

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| _(none for structure)_ | — | — | Every Phase 12 surface has a same-repo keyword/static-doc or packaging analog |

**Partial / invent-with-care only:**

| Concern | Guidance |
|---------|----------|
| New `docs/edge-serve.md` vs expand-only | Prefer thin hub (desktop-gpu pattern); if collapsed, put numbered e2e in README + export README and still keyword-test |
| CHANGELOG Unreleased | Optional; do not bump 0.1.0 → 0.2.0 unless release cut is explicit |
| gitignore `*.onnx` | May hide intentional small fixtures — verify no tracked test fixtures use committed `.onnx`; research says none required |
| Workflow YAML parser | Prefer plain text asserts (like pyproject text tests); no PyYAML dependency required |
| Factory matrix “consolidation” | Verification command + optional docstring table only — no new runtime module |

---

## Plan → Analog Quick Index

### 12-01 — Edge serve docs + AGPL lineage (EDGE-DOC-01, EDGE-DOC-02)

| Work item | Copy from |
|-----------|-----------|
| Root README Export rewrite | `docs/export/README.md` 13–22, 62–86 live conditions |
| Root README jetson row | `docs/export/jetson-packaging.md` 24–29 profile table |
| desktop-gpu stale TRT fix | same file “What this path is not” + jetson live language |
| New edge hub (recommended) | `docs/desktop-gpu.md` structure + export live triad + jetson dual-model 60–76 |
| export/README Phase 7 deferral | Replace with links to desktop-gpu + edge-serve |
| scripts/export/README PyTorch-only | export README live serve paragraph |
| docs/README index row | same file Start-here table pattern |
| THIRD_PARTY derived AGPL | same file AGPL YOLO rows + new lineage section |
| Keyword tests README/desktop/export | `tests/test_export_docs.py` live ORT/TRT style |
| Keyword tests AGPL lineage | `tests/test_third_party_models_doc.py` |
| Optional edge hub tests | `tests/test_desktop_docs.py` shape |
| Optional CHANGELOG | Keep-a-Changelog Unreleased |

### 12-02 — CI + packaging locks (EDGE-CI-01, EDGE-CI-02)

| Work item | Copy from |
|-----------|-----------|
| New `test_edge_ci_workflow.py` | `test_pyproject_onnx_extra.py` static assert style + RESEARCH CI example |
| Confirm ci.yml unchanged | `.github/workflows/ci.yml` current content |
| gitignore `*.engine` `*.onnx` | `.gitignore` `*.pt` line |
| Optional force-include assert | `pyproject.toml` hatch force-include 79–84 + packaging tests |
| Keep no-tensorrt extra | `test_no_tensorrt_optional_extra` |
| EDGE-CI-01 matrix gate | `tests/test_detection_factory.py` (+ honesty/artifact/parity) — verify only |
| Dual-model/torch-only lock | existing `test_edge_rt04_torch_only.py` — verify only |

---

## Metadata

**Analog search scope:**  
`README.md`, `docs/{README,desktop-gpu,export/*}.md`, `scripts/export/README.md`, `THIRD_PARTY_MODELS.md`, `CHANGELOG.md`, `.github/workflows/ci.yml`, `.gitignore`, `pyproject.toml` (hatch + extras), `tests/test_{export_docs,desktop_docs,third_party_models_doc,safety_docs,pyproject_onnx_extra,detection_factory,edge_rt04_torch_only}.py`, `.planning/phases/11-sticky-fallback-dual-model-guardrails/11-PATTERNS.md`, `.planning/phases/12-docs-ci-packaging-polish/{12-RESEARCH,12-VALIDATION}.md`

**Files scanned:** ~25  
**Pattern extraction date:** 2026-08-10  
**Primary analogs for 12-01 / 12-02:** export-doc keyword suite + desktop-gpu hub structure + THIRD_PARTY AGPL rows + pyproject static packaging gates + existing Jetson-free `ci.yml` locked by new workflow tests.
