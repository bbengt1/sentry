# Phase 1: Foundations & Contracts - Research

**Researched:** 2026-08-07  
**Domain:** Python packaging, Pydantic v2 contracts, plugin registry, multi-profile config  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Package/product name: **Sentry AI** / repo `sentry`
- Camera-only perception product for maker robotics
- Perception stream only — never motor commands
- Depth outputs MUST carry `depth_kind`: `relative` | `metric_estimated` | `metric_calibrated`
- Relative depth must never be labeled or field-named as meters (`depth_m` forbidden for relative)
- Config supports profiles: `desktop-gpu`, `jetson`, `cpu-fallback`
- Backend/device abstraction protocols exist even if only desktop is implemented in v1 early phases
- Plugin registry stubs for sources, model workers, sinks
- `camera_id` in schemas from day one (single camera v1; multi-cam later)
- Local open-source models only for core path (no mandatory cloud)
- Default weights commercially friendly (e.g. Depth Anything V2 **Small** Apache-2.0)
- Document Ultralytics AGPL and any NC weights as non-default / research-only in `THIRD_PARTY_MODELS.md`
- Python 3.11+, FastAPI later; Phase 1 can scaffold without full inference
- Prefer `uv` + `pyproject.toml` packaging
- Pydantic v2 for schemas
- Single-process architecture direction (Frame Bus later)

### Claude's Discretion
- Exact package directory layout (`src/sentry_ai/` vs `sentry/`)
- Test runner (pytest) and CI provider details
- Whether smoke CLI is `sentry` entry point vs `python -m sentry_ai`
- Minimal README structure for one-command start
- Whether config is YAML, TOML, or Pydantic settings / env

### Deferred Ideas (OUT OF SCOPE)
- Camera ingest, frame bus, live preview → Phase 2
- Detection / depth workers → Phases 3–4
- Free-space + `/v1` stream → Phase 5
- Interactive UI + open-vocab → Phase 6
- Edge TensorRT packs, ROS2/voice implementations → Phase 7 (stubs only in Phase 1)
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FOUND-01 | Installable Python package with documented one-command local start | `uv` + src layout + `[project.scripts]` smoke CLI; minimal README install path |
| FOUND-02 | Shared schemas `Frame` / `PerceptionFrame` with `frame_id`, `camera_id`, timestamps | Pydantic v2 models; nested completeness; no ad-hoc dicts |
| FOUND-03 | Depth typed (`relative` \| `metric_estimated` \| `metric_calibrated`); relative never labeled as meters | `DepthKind` enum + model validators forbidding `unit="m"` / `depth_m` on relative |
| FOUND-04 | Plugin registry stubs for camera sources, model workers, sinks | Hybrid: in-tree manual registry + `importlib.metadata` entry points |
| FOUND-05 | Commercially friendly defaults; `THIRD_PARTY_MODELS.md` | License table template; DAV2 Small Apache-2.0 default; AGPL/NC non-default |
| FOUND-06 | Device/backend abstraction for desktop-gpu / jetson / cpu-fallback (stubs OK) | `RuntimeProfile` enum + `InferenceBackend` / device `Protocol` stubs; profile YAML |
| MODEL-01 | Core path uses only local OSS models (no mandatory cloud) | Policy module + config field `cloud_inference: false` default; docs statement |
</phase_requirements>

## Summary

Phase 1 is a **contracts-and-skeleton** phase: ship an installable Python package that every later phase imports, with frozen schema types, plugin hooks, runtime profiles, and license policy — without cameras, models, FastAPI, or a web UI. The research stack for this phase is deliberately thin: **Python 3.11 + uv + pyproject.toml (src layout) + Pydantic v2 + pytest**. Heavy CV/ML packages (OpenCV, PyTorch, Ultralytics, FastAPI) stay out of the default dependency set until the phases that need them.

The critical design risk is freezing bad contracts. Architecture research already specifies `PerceptionFrame` with `frame_id`, `camera_id`, timestamps, completeness flags, and honest `depth_kind`. Pitfalls research forbids naming relative depth as meters and forbids desktop-only hardcoding. Phase 1 must encode those rules in types and docs so later phases cannot accidentally violate them.

**Primary recommendation:** Distribution name **`sentry-ai`**, import package **`sentry_ai`**, CLI entry point **`sentry`**, layout **`src/sentry_ai/`**, build with **hatchling** (or uv’s `uv_build`), schemas in **`sentry_ai.schemas`**, plugins via **manual registry + entry-point discovery**, config as **YAML profiles + env override**, smoke command **`sentry smoke`** against synthetic frames (no camera hardware).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Package install / CLI entry | API / Backend (process) | — | Installable library + console script; no browser yet |
| `Frame` / `PerceptionFrame` schemas | API / Backend | — | Shared types for bus, workers, API, UI later |
| Depth kind honesty rules | API / Backend | — | Validation must live in schema layer, not UI copy |
| Plugin registry (sources/workers/sinks) | API / Backend | — | Process bootstrap discovers plugins |
| Runtime profiles / config | API / Backend | Database / Storage (files) | YAML/env config files; no remote config service |
| Device / backend protocols | API / Backend | — | Inference device selection; stubs only in Phase 1 |
| Model license policy docs | CDN / Static (docs in repo) | — | `THIRD_PARTY_MODELS.md` is documentation artifact |
| Smoke / health against synthetic frames | API / Backend | — | CLI constructs synthetic `Frame`s in-process |
| Unit tests (schemas/plugins/config) | API / Backend | — | pytest in CI; no hardware |

## Standard Stack

### Core (Phase 1 install surface)

| Library | Version (verified) | Purpose | Why Standard |
|---------|-------------------|---------|--------------|
| Python | **3.11** (3.12 OK desktop; pin `.python-version` to 3.11) | Runtime | Locked by stack research; Jetson/Pi wheels mature [CITED: STACK.md] |
| uv | **0.11.x** (env has 0.11.23) | Project/env/lock | Official project workflow; `uv init` defaults to src layout [CITED: docs.astral.sh/uv] |
| hatchling | **1.31.0** | Build backend | Mature, PEP 621/639; good for publishable packages [VERIFIED: PyPI] |
| pydantic | **2.13.4** | Schemas / validation | FastAPI-native later; strict contracts [VERIFIED: PyPI] |
| pydantic-settings | **2.15.0** | Env overrides for profile/path | Optional but standard for `SENTRY_*` env [VERIFIED: PyPI] |
| PyYAML | **6.0.3** | Human-editable profile files | Matches STACK multi-profile YAML direction [VERIFIED: PyPI] |
| pytest | **9.1.1** (env also has 8.4.2) | Unit tests | De facto Python test runner [VERIFIED: PyPI] |
| ruff | **0.16.1** | Lint + format | Fast; configure in `pyproject.toml` [VERIFIED: PyPI] |

### Supporting (Phase 1 optional / recommended)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| typer | **0.27.1** | CLI (`sentry smoke`, `sentry health`) | Prefer over raw argparse for subcommands [VERIFIED: PyPI] |
| click | **8.4.2** | Typer dependency | Transitive; do not use directly unless needed [VERIFIED: PyPI] |
| packaging | **26.3** | Version helpers if needed | stdlib-adjacent; rarely needed Phase 1 [VERIFIED: PyPI] |

### Not in Phase 1 dependencies

| Package | Why deferred |
|---------|----------------|
| fastapi / uvicorn | Phase 2+ API shell |
| opencv-python-headless | Phase 2 camera / synthetic image arrays optional later |
| numpy | Phase 2+; Phase 1 synthetic frames can use empty metadata only |
| torch / ultralytics / transformers | Phases 3–4 models |
| supervision / orjson | Later overlay / stream phases |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| hatchling | `uv_build` 0.12.x | uv-native; slightly less ecosystem docs for complex packages |
| hatchling | setuptools | Heavier; fine but hatchling/`uv_build` cleaner for pure Python |
| typer | argparse / click alone | argparse more code; click is fine but typer is thinner for subcommands |
| YAML profiles | TOML-only config | TOML good; YAML more common for robotics profile trees [ASSUMED community preference] |
| entry points only | manual registry only | Manual alone blocks third-party plugins later |
| `src/sentry/` import | `sentry_ai` | **`sentry` is TAKEN on PyPI** by getsentry (v23.7.1) [VERIFIED: PyPI] |

**Installation (Phase 1):**

```bash
# From repo root after scaffold
uv venv --python 3.11
uv sync --all-extras   # or: uv pip install -e ".[dev]"
uv run sentry smoke
uv run pytest
```

**Package naming (prescriptive):**

| Surface | Name | Reason |
|---------|------|--------|
| Git repo | `sentry` | Existing / product brand |
| PyPI distribution | **`sentry-ai`** | `sentry` taken by getsentry [VERIFIED: PyPI 2026-08-07] |
| Import package | **`sentry_ai`** | PEP 8; matches dist name normalization |
| Console script | **`sentry`** | One-command product UX; document collision risk with unrelated tools |
| Module run | `python -m sentry_ai` | Fallback without entry point |

`sentry-ai`, `sentry_ai`, `sentryai` were **AVAILABLE** on PyPI at research time (HTTP 404). [VERIFIED: PyPI]

## Package Legitimacy Audit

> slopcheck was **not available** in the research environment. All packages below are tagged **`[ASSUMED]`** for legitimacy beyond registry existence. Planner should gate first install of any new third-party package behind normal human review if desired; these are all well-known ecosystem packages with multi-year history.

| Package | Registry | Age / status | Downloads | Source Repo | slopcheck | Disposition |
|---------|----------|--------------|-----------|-------------|-----------|-------------|
| pydantic | PyPI | Mature (v2 line) | High | github.com/pydantic/pydantic | n/a | Approved — `[ASSUMED]` legitimacy gate |
| pydantic-settings | PyPI | Mature | High | github.com/pydantic/pydantic-settings | n/a | Approved — `[ASSUMED]` |
| PyYAML | PyPI | Mature | High | github.com/yaml/pyyaml | n/a | Approved — `[ASSUMED]` |
| pytest | PyPI | Mature | High | github.com/pytest-dev/pytest | n/a | Approved — `[ASSUMED]` |
| ruff | PyPI | Mature | High | github.com/astral-sh/ruff | n/a | Approved — `[ASSUMED]` |
| typer | PyPI | Mature | High | github.com/fastapi/typer | n/a | Approved — `[ASSUMED]` |
| hatchling | PyPI | Mature | High | github.com/pypa/hatch | n/a | Approved — `[ASSUMED]` |
| uv / uv-build | PyPI / brew | Mature | High | github.com/astral-sh/uv | n/a | Approved — `[ASSUMED]` |

**Packages removed due to slopcheck [SLOP] verdict:** none (slopcheck unavailable)  
**Packages flagged as suspicious [SUS]:** none

*Planner: because slopcheck was unavailable, treat installs as normal well-known packages; no exotic new packages are recommended for Phase 1.*

## Architecture Patterns

### System Architecture Diagram (Phase 1 scope)

```text
Developer shell
      │
      ▼
┌─────────────────┐
│  sentry CLI     │  health | smoke
│  (entry point)  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────┐
│  Config load    │────▶│ RuntimeProfile        │
│  YAML + env     │     │ desktop-gpu|jetson|   │
└────────┬────────┘     │ cpu-fallback          │
         │              └──────────────────────┘
         ▼
┌─────────────────┐     ┌──────────────────────┐
│ Plugin Registry │────▶│ sources / workers /   │
│ stubs           │     │ sinks (no-op + synth) │
└────────┬────────┘     └──────────────────────┘
         │
         ▼
┌─────────────────┐     ┌──────────────────────┐
│ Schemas         │────▶│ Frame                │
│ (Pydantic v2)   │     │ PerceptionFrame      │
│                 │     │ DepthKind + complete  │
└────────┬────────┘     └──────────────────────┘
         │
         ▼
┌─────────────────┐
│ Synthetic smoke │  construct N frames → validate → exit 0
│ (no camera/GPU) │
└─────────────────┘

Docs (repo root / docs):
  THIRD_PARTY_MODELS.md  ·  README one-command start  ·  MODEL policy
```

### Recommended Project Structure (Phase 1)

```text
sentry/                          # repo root
├── pyproject.toml
├── .python-version              # 3.11
├── README.md
├── LICENSE
├── THIRD_PARTY_MODELS.md
├── uv.lock                      # after first uv lock
├── src/
│   └── sentry_ai/
│       ├── __init__.py          # __version__
│       ├── __main__.py          # python -m sentry_ai
│       ├── cli.py               # typer app: health, smoke
│       ├── schemas/
│       │   ├── __init__.py      # re-export public models
│       │   ├── enums.py         # DepthKind, RuntimeProfile, BackendName
│       │   ├── frame.py         # Frame
│       │   ├── perception.py    # PerceptionFrame, Completeness, DepthPayload, ...
│       │   └── validators.py    # shared depth honesty rules
│       ├── config/
│       │   ├── __init__.py
│       │   ├── models.py        # Pydantic config tree
│       │   ├── load.py          # YAML load + profile merge + env
│       │   └── profiles/
│       │       ├── desktop-gpu.yaml
│       │       ├── jetson.yaml
│       │       └── cpu-fallback.yaml
│       ├── plugins/
│       │   ├── __init__.py
│       │   ├── registry.py      # register / get / discover
│       │   ├── protocols.py     # CameraSource, ModelWorker, Sink Protocols
│       │   └── builtins.py      # synthetic source stub, null sink, noop worker
│       ├── backend/
│       │   ├── __init__.py
│       │   └── protocols.py     # InferenceBackend, DeviceInfo stubs
│       └── policy/
│           ├── __init__.py
│           └── models.py        # local OSS only; default weight allowlist hooks
├── tests/
│   ├── conftest.py
│   ├── test_schemas_frame.py
│   ├── test_schemas_depth_kind.py
│   ├── test_schemas_perception.py
│   ├── test_config_profiles.py
│   ├── test_plugins_registry.py
│   ├── test_backend_protocols.py
│   └── test_cli_smoke.py
└── .github/workflows/ci.yml     # optional Wave 0: ruff + pytest
```

Aligns with architecture research layout (`sources/`, `plugins/`, …) but only creates **contract modules** now; empty packages for `bus/`, `api/`, etc. may be added as placeholders **only if** they do not invite premature implementation — prefer creating directories when phases need them.

### Pattern 1: src layout + installable package

**What:** Put import package under `src/` so tests and scripts always import the *installed* package, not a random tree path.  
**When to use:** Always for this product (will grow FastAPI, optional extras, plugins).  
**Why:** PyPA recommends src layout to prevent accidental use of undeclared files and to force editable install during development. [CITED: packaging.python.org src-layout-vs-flat-layout]

```toml
# pyproject.toml (illustrative)
[build-system]
requires = ["hatchling>=1.26"]
build-backend = "hatchling.build"

[project]
name = "sentry-ai"
version = "0.1.0"
description = "Camera-only perception for maker robotics"
readme = "README.md"
requires-python = ">=3.11"
license = "Apache-2.0"  # or project-chosen SPDX; confirm with user
dependencies = [
  "pydantic>=2.13,<3",
  "pydantic-settings>=2.15,<3",
  "pyyaml>=6.0.3",
  "typer>=0.27",
]

[project.optional-dependencies]
dev = ["pytest>=8", "ruff>=0.8"]

[project.scripts]
sentry = "sentry_ai.cli:app"

[project.entry-points."sentry_ai.sources"]
synthetic = "sentry_ai.plugins.builtins:SyntheticSource"

[project.entry-points."sentry_ai.workers"]
noop = "sentry_ai.plugins.builtins:NoopWorker"

[project.entry-points."sentry_ai.sinks"]
null = "sentry_ai.plugins.builtins:NullSink"

[tool.hatch.build.targets.wheel]
packages = ["src/sentry_ai"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = []  # rely on editable install; do NOT add src/ hacks if avoidable
```

### Pattern 2: Pydantic v2 schema contracts with depth honesty

**What:** Enum-typed depth + model validators that reject meter labeling on relative depth.  
**When to use:** All perception messages that carry depth.  
**Example:**

```python
# Source: Pydantic v2 models + project PITFALLS (depth_kind rules)
from enum import Enum
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

class DepthKind(str, Enum):
    RELATIVE = "relative"
    METRIC_ESTIMATED = "metric_estimated"
    METRIC_CALIBRATED = "metric_calibrated"

class Completeness(BaseModel):
    model_config = ConfigDict(extra="forbid")
    depth: bool = False
    detections: bool = False
    free_space: bool = False

class DepthPayload(BaseModel):
    """Wire-facing depth metadata. Bulk arrays stay out of Phase 1 smoke."""
    model_config = ConfigDict(extra="forbid")
    kind: DepthKind
    unit: Literal["m"] | None = None
    width: int | None = None
    height: int | None = None
    # Intentionally NO field named depth_m

    @model_validator(mode="after")
    def relative_must_not_claim_meters(self) -> "DepthPayload":
        if self.kind == DepthKind.RELATIVE and self.unit is not None:
            raise ValueError("relative depth must not set unit (meters forbidden)")
        if self.kind != DepthKind.RELATIVE and self.unit is None:
            # metric kinds should declare unit when present
            pass
        return self

class Frame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    frame_id: int = Field(ge=0)
    camera_id: str = Field(min_length=1)
    t_capture: float  # document: seconds, monotonic or epoch — pick one in docs
    t_ingest: float | None = None
    # image bytes/array: deferred; optional placeholder for later
    width: int | None = None
    height: int | None = None

class PerceptionFrame(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    frame_id: int = Field(ge=0)
    camera_id: str
    t_capture: float
    t_publish: float | None = None
    completeness: Completeness = Field(default_factory=Completeness)
    depth: DepthPayload | None = None
    detections: list[dict] | None = None  # tighten in Phase 3
    free_space: dict | None = None        # tighten in Phase 5
    stats: dict | None = None
```

**Timestamp policy (recommend default):** use **`time.time()` epoch seconds (float)** for `t_capture` / `t_publish` on the wire for robot clients; optionally also store `t_mono` (monotonic) for internal latency math later. Document the choice in schema module docstring so Phase 2 does not invent a second convention. [ASSUMED — no locked decision]

### Pattern 3: Hybrid plugin registry

**What:** Built-in plugins registered in code; third-party via entry points.  
**When to use:** Sources, workers, sinks (and later bridges).  
**Why entry points:** PyPA standard discovery via package metadata; works across separately installed packages. [CITED: packaging.python.org creating-and-discovering-plugins]

```python
# Source: importlib.metadata entry_points (Python 3.10+)
from __future__ import annotations
from importlib.metadata import entry_points
from typing import Any, Callable, Protocol

class CameraSource(Protocol):
    name: str
    def open(self) -> None: ...
    def read(self) -> Any: ...  # later: Frame
    def close(self) -> None: ...

class PluginRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, type] = {}
        self._workers: dict[str, type] = {}
        self._sinks: dict[str, type] = {}

    def register_source(self, name: str, cls: type) -> None:
        if name in self._sources:
            raise ValueError(f"duplicate source plugin: {name}")
        self._sources[name] = cls

    def discover(self) -> None:
        for ep in entry_points(group="sentry_ai.sources"):
            self.register_source(ep.name, ep.load())
        for ep in entry_points(group="sentry_ai.workers"):
            self._workers[ep.name] = ep.load()
        for ep in entry_points(group="sentry_ai.sinks"):
            self._sinks[ep.name] = ep.load()

    def get_source(self, name: str) -> type:
        return self._sources[name]
```

**Phase 1 builtins:** `synthetic` source (yields schema-valid synthetic Frames without OpenCV), `noop` worker, `null` sink. Real USB/file/RTSP in Phase 2.

### Pattern 4: Multi-profile config

**What:** Named profiles select default backends/model tiers without hardcoding CUDA.  
**When to use:** All runtime entry points.  

```yaml
# src/sentry_ai/config/profiles/desktop-gpu.yaml
profile: desktop-gpu
device:
  preferred_backend: torch   # stub enum; not executed in Phase 1
  device_id: "cuda:0"        # advisory; code must not assume present
models:
  allow_cloud: false         # MODEL-01
  defaults_commercially_friendly: true
source:
  type: synthetic            # Phase 1 default for smoke
```

```yaml
# jetson.yaml — same schema, different defaults
profile: jetson
device:
  preferred_backend: tensorrt
  device_id: "0"
models:
  allow_cloud: false
  detector_tier: n
  depth_tier: small
```

```yaml
# cpu-fallback.yaml
profile: cpu-fallback
device:
  preferred_backend: onnxruntime
  device_id: "cpu"
models:
  allow_cloud: false
  detector_tier: n
  depth_tier: small
```

Load order (recommended):

1. Built-in profile YAML for `RuntimeProfile`
2. Optional user config file (`~/.config/sentry-ai/config.yaml` or `./sentry.yaml`)
3. Env overrides: `SENTRY_PROFILE`, `SENTRY_ALLOW_CLOUD` (must default false)

Use Pydantic models for the merged tree; use `pydantic-settings` only for the thin env layer. [ASSUMED composition pattern]

### Pattern 5: Device / backend protocols (stubs)

```python
from typing import Any, Protocol, runtime_checkable
from enum import Enum

class BackendName(str, Enum):
    TORCH = "torch"
    ONNXRUNTIME = "onnxruntime"
    TENSORRT = "tensorrt"
    OPENVINO = "openvino"
    CPU = "cpu"

class RuntimeProfile(str, Enum):
    DESKTOP_GPU = "desktop-gpu"
    JETSON = "jetson"
    CPU_FALLBACK = "cpu-fallback"

@runtime_checkable
class InferenceBackend(Protocol):
    name: BackendName
    def load(self) -> None: ...
    def infer(self, tensor: Any) -> Any: ...
    def close(self) -> None: ...

class DeviceInfo(BaseModel):
    profile: RuntimeProfile
    backend: BackendName
    device_id: str
    available: bool = False  # Phase 1: probe stub returns False without torch
```

Phase 1 ships **protocols + a `NullBackend` stub** that records calls; no real inference.

### Pattern 6: Smoke CLI that becomes one-command start

```text
sentry health     # print version, profile, plugin list, schema_version
sentry smoke      # build synthetic Frames → PerceptionFrame validate → exit 0
sentry            # later: start full stack (Phase 2+); Phase 1 can show help
```

```python
# cli.py sketch
import typer
app = typer.Typer(name="sentry", help="Sentry AI — camera-only perception")

@app.command()
def health(profile: str = "cpu-fallback") -> None: ...

@app.command()
def smoke(frames: int = 3, profile: str = "cpu-fallback") -> None: ...

def main() -> None:
    app()
```

README one-command path (Phase 1):

```bash
uv sync
uv run sentry smoke
```

Later phases extend `sentry start` without renaming the entry point.

### Pattern 7: THIRD_PARTY_MODELS.md

Minimum table columns:

| Model / weights | Role | License | Default? | Notes |
|-----------------|------|---------|----------|-------|
| Depth Anything V2 **Small** | Depth | Apache-2.0 | **Yes** | Commercially friendly |
| Depth Anything V2 Base/Large/Giant | Depth | CC-BY-NC-4.0 | **No** | Research-only; NC |
| DAV2 Metric indoor/outdoor | Depth metric | Check per weight | Optional | Domain-specific heads |
| YOLO26 (via Ultralytics) | Fixed detect | AGPL-3.0 (Ultralytics) | Planned Phase 3 | Document AGPL for commercial forks |
| YOLOE | Open-vocab | AGPL-3.0 (Ultralytics) | Planned Phase 6 | Non-blocking for Phase 1 |

Policy text (MODEL-01):

- Core inference path is **local OSS only**.
- No cloud API keys required for default install or smoke.
- `allow_cloud: false` is the default config; enabling cloud is non-default and out of v1 core.

### Anti-Patterns to Avoid

- **Import package named `sentry`:** PyPI collision with getsentry; import confusion forever.
- **Ad-hoc dicts for frames:** freezes nothing; breaks OpenAPI later.
- **Field `depth_m` without kind:** violates FOUND-03 / pitfalls.
- **Installing torch in Phase 1:** slow CI, unrelated to contracts.
- **Implementing Frame Bus “while we’re here”:** Phase 2 scope.
- **Hardcoding `cuda:0` in shared code paths:** desktop-only trap.
- **Namespace-package plugins only:** more fragile than entry points for v1.
- **`extra="ignore"` on PerceptionFrame:** silently drops API fields; use `extra="forbid"` on wire models.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Schema validation / JSON schema | Custom validators everywhere | Pydantic v2 `BaseModel` | Coercion, errors, JSON schema for OpenAPI later |
| CLI parsing | Custom sys.argv | Typer (or argparse) | Subcommands, help, exit codes |
| Plugin discovery | Filesystem walk of site-packages | `importlib.metadata.entry_points` | Standard, install-time declared |
| Config merge | Nested dict deep-merge DIY | Pydantic model validate of merged dict | Typed errors |
| Lint/format | flake8+black+isort trio | Ruff | One tool |
| Env management | bare pip + requirements drift | uv lock | Reproducible |
| Enum string stability | magic strings | `enum.Enum` / `str, Enum` | Serialization + validation |

**Key insight:** Phase 1 value is **contracts**, not infrastructure cleverness. Prefer stdlib + Pydantic over new frameworks.

## Common Pitfalls

### Pitfall 1: Freezing relative depth as meters
**What goes wrong:** API field `depth_m` or `unit: m` on relative models; robots trust fake distances.  
**Why it happens:** Colorized depth demos look metric.  
**How to avoid:** `DepthKind` enum + validators; forbid `depth_m` field name entirely; tests for rejection.  
**Warning signs:** Any test fixture using meters without `metric_*` kind.

### Pitfall 2: Package name collision with getsentry
**What goes wrong:** `pip install sentry` installs error tracking server, not this product.  
**Why it happens:** Product name “Sentry” is already a major OSS brand.  
**How to avoid:** PyPI name `sentry-ai`; import `sentry_ai`; mention disambiguation in README.  
**Warning signs:** `import sentry` resolving to wrong package.

### Pitfall 3: Flat layout import shadows
**What goes wrong:** Tests pass without packaging because `./sentry_ai` is on `sys.path`; wheels miss files.  
**Why it happens:** Flat layout convenience.  
**How to avoid:** src layout + editable install in CI (`uv sync`).  
**Warning signs:** Tests fail in CI after packaging but pass locally from repo root.

### Pitfall 4: Plugin registry without discovery path
**What goes wrong:** Only hard-coded imports; external plugins impossible without core edits.  
**Why it happens:** “We’ll add entry points later.”  
**How to avoid:** Declare entry-point groups in Phase 1 even with one builtin each.  
**Warning signs:** `if name == "usb": return UsbSource()` sprawl.

### Pitfall 5: Profile names only in docs
**What goes wrong:** Strings diverge (`jetson` vs `jetson-orin` vs `edge`).  
**Why it happens:** Free-form YAML.  
**How to avoid:** `RuntimeProfile` enum with exactly three values from requirements; reject unknown.  
**Warning signs:** Profile-specific `if` branches on arbitrary strings.

### Pitfall 6: Smoke test that needs a camera
**What goes wrong:** CI fails on headless runners.  
**Why it happens:** Smoke coupled to OpenCV VideoCapture.  
**How to avoid:** Synthetic source only for Phase 1 smoke; no OpenCV dependency.  
**Warning signs:** ImportError on `cv2` in CI.

### Pitfall 7: License landmines in defaults
**What goes wrong:** Default model path points at CC-BY-NC weights.  
**Why it happens:** Base/Large look better in demos.  
**How to avoid:** `THIRD_PARTY_MODELS.md` + policy module listing default allowlist; NC marked research-only.  
**Warning signs:** Docs “recommended weights” without license column.

### Pitfall 8: Scope creep into bus/API
**What goes wrong:** Phase 1 becomes half of Phase 2.  
**Why it happens:** Architecture diagram is exciting.  
**How to avoid:** Explicit “What NOT to build”; success criteria only install + smoke + schemas + stubs.  
**Warning signs:** PR adds FastAPI routes or VideoCapture.

## Code Examples

### Synthetic Frame factory (smoke)

```python
# Source: project architecture Frame shape
from time import time
from sentry_ai.schemas import Frame, PerceptionFrame, Completeness, DepthKind, DepthPayload

def make_synthetic_frame(frame_id: int, camera_id: str = "synthetic0") -> Frame:
    now = time()
    return Frame(
        frame_id=frame_id,
        camera_id=camera_id,
        t_capture=now,
        t_ingest=now,
        width=640,
        height=480,
    )

def make_partial_perception(frame: Frame) -> PerceptionFrame:
    return PerceptionFrame(
        frame_id=frame.frame_id,
        camera_id=frame.camera_id,
        t_capture=frame.t_capture,
        t_publish=time(),
        completeness=Completeness(depth=False, detections=False, free_space=False),
        depth=None,
    )
```

### Depth honesty tests

```python
import pytest
from pydantic import ValidationError
from sentry_ai.schemas import DepthPayload, DepthKind

def test_relative_rejects_unit_meters():
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.RELATIVE, unit="m")

def test_relative_ok_without_unit():
    d = DepthPayload(kind=DepthKind.RELATIVE, unit=None)
    assert d.kind == DepthKind.RELATIVE

def test_metric_estimated_allows_meters():
    d = DepthPayload(kind=DepthKind.METRIC_ESTIMATED, unit="m")
    assert d.unit == "m"
```

### Profile load

```python
from pathlib import Path
import yaml
from sentry_ai.config.models import SentryConfig
from sentry_ai.schemas.enums import RuntimeProfile

def load_profile(profile: RuntimeProfile) -> SentryConfig:
    path = Path(__file__).parent / "profiles" / f"{profile.value}.yaml"
    data = yaml.safe_load(path.read_text())
    return SentryConfig.model_validate(data)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| setup.py / setup.cfg | PEP 621 `pyproject.toml` | 2020+ | Single metadata file |
| license table `{text=}` | SPDX `license = "Apache-2.0"` (PEP 639) | 2024–2025 backends | Use modern hatchling/setuptools |
| pkg_resources entry points | `importlib.metadata.entry_points` | 3.10+ | No setuptools runtime dep |
| Pydantic v1 `class Config` | v2 `model_config = ConfigDict(...)` | Pydantic 2 | Use v2 only |
| flat layout default | src layout (`uv init`) | uv modern default | Prefer src |

**Deprecated/outdated:**
- `pkg_resources.iter_entry_points` — use `importlib.metadata`
- Pydantic v1 `.dict()` / `.parse_obj()` — use `.model_dump()` / `.model_validate()`
- Naming import package `sentry` — blocked by PyPI

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Product license SPDX choice (recommend Apache-2.0 for code) not locked by user | Standard Stack / pyproject | Must confirm before publish |
| A2 | Wire timestamps as epoch float seconds | Schemas | Robot clients may prefer int ms or monotonic-only |
| A3 | YAML preferred over pure TOML for profiles | Config | User may prefer TOML-only; low risk |
| A4 | Typer for CLI vs argparse | CLI | Style only |
| A5 | hatchling over uv_build | Packaging | Both valid; uv_build is uv-default |
| A6 | Detection/free_space typed as loose dict until later phases | Schemas | May need earlier tightening for OpenAPI |
| A7 | No OpenCV/numpy in Phase 1 smoke | Smoke | Synthetic frames metadata-only may feel “empty” but meets contracts |
| A8 | Package legitimacy of well-known libs without slopcheck | Package Audit | Residual supply-chain process gap only |

**If empty:** N/A — assumptions listed above need planner/user confirmation where marked.

## Open Questions

1. **Product SPDX license for Sentry AI code itself**
   - What we know: model licenses documented separately; product license not locked in CONTEXT.
   - What's unclear: Apache-2.0 vs MIT vs AGPL for the application.
   - **Recommendation:** Apache-2.0 for application code (maker-friendly, matches DAV2 Small); keep Ultralytics AGPL as *dependency* concern documented in THIRD_PARTY_MODELS.md.

2. **Timestamp convention (epoch vs monotonic)**
   - What we know: architecture uses `t_capture` float; pitfalls want age/latency.
   - What's unclear: single field vs dual (`t_capture_wall`, `t_mono`).
   - **Recommendation:** `t_capture: float` epoch seconds on wire; add optional `t_mono: float | None = None` for internal latency in Phase 2 without breaking schema_version 1 if additive.

3. **CLI name collision**
   - What we know: console script `sentry` is best product UX; getsentry package is also `sentry`.
   - What's unclear: whether dual install is a real maker issue.
   - **Recommendation:** ship `sentry` script; document `python -m sentry_ai` fallback; do not name PyPI dist `sentry`.

4. **How complete should PerceptionFrame nested types be in Phase 1?**
   - What we know: FOUND-02/03 need frame identity + depth_kind; detections/free_space fully shaped later.
   - **Recommendation:** Fully type `Frame`, `Completeness`, `DepthPayload`, `PerceptionFrame` shell; leave `detections` / `free_space` as optional structured placeholders (typed models with minimal fields) rather than bare `dict` if low cost — prefer thin `Detection` / `FreeSpacePayload` stubs with `extra="forbid"` and few fields.

5. **CI provider**
   - Discretion: GitHub Actions assumed if remote is GitHub.
   - **Recommendation:** `.github/workflows/ci.yml` with Python 3.11, `uv sync`, `ruff check`, `pytest`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11 | runtime | ✓ | 3.11.15 | 3.12.13 also present; avoid 3.14 for project pin |
| Python 3.14 (system) | — | ✓ | 3.14.6 | Do **not** set as project default (ML wheels lag) |
| uv | packaging | ✓ | 0.11.23 | pip + venv |
| pytest | tests | ✓ | 8.4.2 (global) | install via project dev extra (PyPI 9.1.1) |
| ruff | lint | ✓ | 0.7.4 (global) / 0.16.1 PyPI | install via dev extra |
| node | frontend | ✓ | v26.3.1 | **Not needed Phase 1** |
| pydantic (global) | — | ✓ | 2.12.5 | Project should pin ≥2.13 via uv |
| torch / CUDA | inference | not checked | — | **Not required Phase 1** |
| OpenCV | camera | not required | — | **Not required Phase 1** |
| slopcheck | package audit | ✗ | — | Mark packages [ASSUMED]; human review |

**Missing dependencies with no fallback:** none for Phase 1.

**Missing dependencies with fallback:** slopcheck (process only); torch/OpenCV intentionally deferred.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — this section is required.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (pin ≥8 in dev extra; PyPI current 9.1.1) |
| Config file | `pyproject.toml` → `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest -q tests/test_schemas_depth_kind.py tests/test_schemas_frame.py` |
| Full suite command | `uv run pytest -q` |
| Lint | `uv run ruff check src tests` |
| Smoke | `uv run sentry smoke` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FOUND-01 | Package imports; CLI entry works | smoke | `uv run sentry health` | ❌ Wave 0 |
| FOUND-01 | Documented install path | manual | README review | ❌ Wave 0 |
| FOUND-02 | Frame requires frame_id, camera_id, timestamps | unit | `pytest tests/test_schemas_frame.py -q` | ❌ Wave 0 |
| FOUND-02 | PerceptionFrame carries identity fields | unit | `pytest tests/test_schemas_perception.py -q` | ❌ Wave 0 |
| FOUND-03 | DepthKind enum has three values | unit | `pytest tests/test_schemas_depth_kind.py -q` | ❌ Wave 0 |
| FOUND-03 | relative + unit=m raises | unit | same | ❌ Wave 0 |
| FOUND-03 | No `depth_m` field on DepthPayload | unit | `assert "depth_m" not in DepthPayload.model_fields` | ❌ Wave 0 |
| FOUND-04 | Registry lists source/worker/sink stubs | unit | `pytest tests/test_plugins_registry.py -q` | ❌ Wave 0 |
| FOUND-04 | Entry point groups discoverable or builtins registered | unit | same | ❌ Wave 0 |
| FOUND-05 | THIRD_PARTY_MODELS.md exists and mentions Apache-2.0 Small + AGPL/NC | unit/smoke | file existence + content grep test | ❌ Wave 0 |
| FOUND-06 | RuntimeProfile enum has desktop-gpu, jetson, cpu-fallback | unit | `pytest tests/test_config_profiles.py -q` | ❌ Wave 0 |
| FOUND-06 | Each profile YAML loads to SentryConfig | unit | same | ❌ Wave 0 |
| FOUND-06 | InferenceBackend protocol / NullBackend stub importable | unit | `pytest tests/test_backend_protocols.py -q` | ❌ Wave 0 |
| MODEL-01 | Config default `allow_cloud` is False | unit | `pytest tests/test_config_profiles.py -q` | ❌ Wave 0 |
| MODEL-01 | Policy module documents local-only core path | unit | import policy constants | ❌ Wave 0 |
| Success #1 | smoke exits 0 on synthetic frames | smoke | `uv run sentry smoke` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** `uv run pytest -q` (target < 30s; no ML)
- **Per wave merge:** full pytest + `uv run sentry smoke` + `ruff check`
- **Phase gate:** full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/conftest.py` — shared fixtures (synthetic Frame factory)
- [ ] `tests/test_schemas_frame.py` — FOUND-02
- [ ] `tests/test_schemas_depth_kind.py` — FOUND-03
- [ ] `tests/test_schemas_perception.py` — FOUND-02/03 completeness
- [ ] `tests/test_config_profiles.py` — FOUND-06, MODEL-01
- [ ] `tests/test_plugins_registry.py` — FOUND-04
- [ ] `tests/test_backend_protocols.py` — FOUND-06
- [ ] `tests/test_cli_smoke.py` — FOUND-01 (Typer CliRunner or subprocess)
- [ ] `tests/test_third_party_models_doc.py` — FOUND-05 file presence + key license strings
- [ ] `pyproject.toml` package scaffold — FOUND-01
- [ ] Optional: `.github/workflows/ci.yml` — ruff + pytest on 3.11

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no (Phase 1 local CLI only) | — |
| V3 Session Management | no | — |
| V4 Access Control | no | — |
| V5 Input Validation | **yes** | Pydantic v2 models; `extra="forbid"` on wire schemas |
| V6 Cryptography | no | — |
| V10 Malicious Code / Supply chain | **yes (light)** | Pin deps via `uv.lock`; document model weight licenses; no auto-download in Phase 1 |
| V14 Configuration | **yes** | Profiles validated; `allow_cloud` default false |

### Known Threat Patterns for this phase

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Malicious YAML config | Tampering | Pydantic validation; no `yaml.load` unsafe loader — use `safe_load` |
| Dependency confusion / wrong package `sentry` | Spoofing | Distinct name `sentry-ai`; README disambiguation |
| Future model weight supply chain | Tampering | Pin hashes later (Phase 3+); document in THIRD_PARTY_MODELS |
| Accidental cloud enablement | Info disclosure | Default `allow_cloud=false`; tests |
| Safety overclaim in docs | Elevation of privilege (product misuse) | Perception-only language; no motor commands in schemas |

## What NOT to Build in Phase 1

| Do NOT build | Belongs in |
|--------------|------------|
| OpenCV / USB / RTSP / file capture | Phase 2 |
| Frame Bus / keep-latest queues | Phase 2 |
| FastAPI routes, WebSocket, MJPEG | Phase 2 |
| Web UI / React / Vite | Phase 2+ |
| YOLO / Ultralytics inference | Phase 3 |
| Depth Anything inference | Phase 4 |
| Free-space / Spatial Post | Phase 5 |
| Real TensorRT / ONNX Runtime execution | Phase 7 (protocols only now) |
| ROS2 bridge implementation | Phase 7 stubs only if time; not required for FOUND-* |
| Model weight download / HF cache | Phase 3–4 |
| Docker / JetPack images | Phase 7 |
| Auth, LAN bind, TLS | Phase 2+ defaults |

## Recommended Plan Split (for planner)

Matches ROADMAP (3 plans):

| Plan | Deliverables | Reqs |
|------|--------------|------|
| **01-01 Scaffold** | `pyproject.toml`, src layout, uv lock, ruff/pytest config, `sentry` CLI skeleton, README install, CI smoke | FOUND-01 |
| **01-02 Schemas + config** | `Frame`, `PerceptionFrame`, `DepthKind`, completeness, profile YAMLs, config load, MODEL-01 flags | FOUND-02, FOUND-03, FOUND-06 (profiles), MODEL-01 |
| **01-03 Plugins + licenses + backends** | Registry + entry points + builtins, `InferenceBackend` stubs, `THIRD_PARTY_MODELS.md`, full `sentry smoke` | FOUND-04, FOUND-05, FOUND-06 (device stubs) |

## Sources

### Primary (HIGH confidence)
- [PyPA Writing pyproject.toml](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/) — scripts, entry points, PEP 639 license
- [PyPA src vs flat layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [PyPA Creating and discovering plugins](https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/) — entry points via `importlib.metadata`
- [uv Projects guide](https://docs.astral.sh/uv/guides/projects/) — src layout default, lockfile, scripts
- [Pydantic v2 Models](https://pydantic.dev/docs/validation/latest/concepts/models/) — BaseModel, validators, ConfigDict
- PyPI registry checks 2026-08-07 — `sentry` TAKEN; `sentry-ai` AVAILABLE; versions for pydantic 2.13.4, hatchling 1.31.0, etc.
- Project research: `.planning/research/{SUMMARY,STACK,ARCHITECTURE,PITFALLS}.md`
- Phase context: `01-CONTEXT.md`, `REQUIREMENTS.md`, `ROADMAP.md`

### Secondary (MEDIUM confidence)
- Typer as CLI layer over Click — common FastAPI-adjacent pattern [ASSUMED community standard; package exists on PyPI]
- Dual timestamp fields for latency — pattern from architecture latency budgets [ASSUMED composition]

### Tertiary (LOW confidence)
- Exact user SPDX for application code — not locked

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — versions verified on PyPI; uv/PyPA docs current; aligns with STACK.md
- Architecture: **HIGH** — constrained by ARCHITECTURE.md + CONTEXT locked decisions; Phase 1 scope clear
- Pitfalls: **HIGH** — depth_kind and license issues already researched project-wide
- Package name: **HIGH** — PyPI collision verified
- Config format YAML vs TOML: **MEDIUM** — discretion; recommendation is YAML

**Research date:** 2026-08-07  
**Valid until:** ~2026-09-07 (packaging ecosystem stable; re-check PyPI name availability before publish)

---

## RESEARCH COMPLETE

**Phase:** 1 - Foundations & Contracts  
**Confidence:** HIGH

### Key Findings
1. **Do not use import/PyPI name `sentry`** — taken by getsentry; use **`sentry-ai` / `sentry_ai`**, CLI **`sentry`**.
2. **Phase 1 deps stay thin:** pydantic, pyyaml, typer, pytest, ruff — **no** torch/OpenCV/FastAPI.
3. **Depth honesty is a schema validator problem**, not a docs-only problem: `DepthKind` + forbid meters on relative.
4. **Plugins:** hybrid manual registry + `importlib.metadata` entry points (`sentry_ai.sources|workers|sinks`).
5. **Profiles:** exact enum `desktop-gpu` | `jetson` | `cpu-fallback` with YAML + env; backend `Protocol` stubs only.
6. **Success path:** `uv sync && uv run sentry smoke && uv run pytest` on synthetic frames.

### File Created
`/Users/brentbengtson/github-files/sentry/.planning/phases/01-foundations-contracts/01-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | PyPI + uv/PyPA docs verified |
| Architecture | HIGH | Project research + locked CONTEXT |
| Pitfalls | HIGH | PITFALLS.md + packaging collision verified |

### Open Questions
- Application SPDX license (recommend Apache-2.0)
- Timestamp epoch vs dual mono field (recommend epoch + optional mono later)
- CLI name `sentry` vs `sentry-ai` (recommend `sentry` + module fallback)

### Ready for Planning
Research complete. Planner can now create PLAN.md files (01-01, 01-02, 01-03).  
**Note:** Per instructions, this research was **not** git-committed.
