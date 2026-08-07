# Phase 2: Camera Ingest & Live Preview - Pattern Map

**Mapped:** 2026-08-07  
**Files analyzed:** 22 (new + modified)  
**Analogs found:** 18 / 22  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/capture/image_frame.py` | model (runtime) | transform | `src/sentry_ai/schemas/frame.py` + `backend/null.py` | partial |
| `src/sentry_ai/capture/status.py` | model | request-response | `src/sentry_ai/schemas/enums.py` | role-match |
| `src/sentry_ai/capture/loop.py` | service | event-driven | `src/sentry_ai/plugins/builtins.py` (lifecycle) | partial |
| `src/sentry_ai/capture/__init__.py` | config | — | `src/sentry_ai/backend/__init__.py` | exact |
| `src/sentry_ai/bus/frame_bus.py` | service | pub-sub | *none* (RESEARCH Pattern 2) | none |
| `src/sentry_ai/bus/__init__.py` | config | — | `src/sentry_ai/backend/__init__.py` | exact |
| `src/sentry_ai/sources/opencv_source.py` | service | streaming | `src/sentry_ai/plugins/builtins.py` (`SyntheticSource`) | role-match |
| `src/sentry_ai/sources/synthetic.py` | service | streaming | `src/sentry_ai/plugins/builtins.py` (`SyntheticSource`) | exact |
| `src/sentry_ai/sources/errors.py` | utility | — | `builtins.SyntheticSource.read` raise style | partial |
| `src/sentry_ai/sources/__init__.py` | config | — | `src/sentry_ai/plugins/__init__.py` | exact |
| `src/sentry_ai/api/app.py` | controller | request-response | *none* (FastAPI new) | none |
| `src/sentry_ai/api/routes_preview.py` | route | streaming | *none* (MJPEG new) | none |
| `src/sentry_ai/api/deps.py` | middleware | request-response | *none* (app-state new) | none |
| `src/sentry_ai/api/__init__.py` | config | — | `src/sentry_ai/backend/__init__.py` | exact |
| `src/sentry_ai/ui/static/index.html` | component | request-response | *none* (static UI new) | none |
| `src/sentry_ai/cli.py` | controller | request-response | self (`health`/`smoke`) | exact |
| `src/sentry_ai/plugins/protocols.py` | middleware | request-response | self (`CameraSource`) | exact |
| `src/sentry_ai/plugins/builtins.py` | service | request-response | self (re-export / thin wrap) | exact |
| `src/sentry_ai/plugins/registry.py` | service | CRUD | self (`register_builtins`) | exact |
| `src/sentry_ai/config/models.py` | model | CRUD | self (`SourceConfig`) | exact |
| `pyproject.toml` | config | — | self (deps + entry-points) | exact |
| `tests/test_*.py` (new suite) | test | — | `tests/test_plugins_registry.py`, `test_cli_smoke.py` | role-match |

---

## Pattern Assignments

### `src/sentry_ai/capture/image_frame.py` (model/runtime, transform)

**Analog:** `src/sentry_ai/schemas/frame.py` (identity fields) + `src/sentry_ai/backend/null.py` (plain class, not Pydantic)

**Critical rule from Frame docstring** (lines 13–18 of `schemas/frame.py`):
```python
class Frame(BaseModel):
    """Minimal camera frame identity without image payload.

    Image arrays/bytes are intentionally omitted so Phase 1 contracts stay
    free of numpy/OpenCV dependencies.
    """
```

**Do not put numpy on Pydantic `Frame`.** Keep `Frame` identity-only (`extra="forbid"`, fields as today). New type is a plain `@dataclass` wrapping `meta: Frame` + `image_bgr`.

**Plain-class style from NullBackend** (lines 13–31 of `backend/null.py`):
```python
from __future__ import annotations

from typing import Any

from sentry_ai.schemas.enums import BackendName


class NullBackend:
    """Records infer() calls and returns None without running models."""

    name: BackendName = BackendName.CPU

    def __init__(self) -> None:
        self.infer_calls: int = 0
        self._loaded: bool = False
```

**Imports pattern to copy:**
```python
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from sentry_ai.schemas.frame import Frame
```

**Core pattern (from RESEARCH, aligned with Frame field names):**
```python
@dataclass(slots=True)
class ImageFrame:
    meta: Frame
    image_bgr: np.ndarray  # HxWx3 uint8

    @property
    def frame_id(self) -> int:
        return self.meta.frame_id

    @property
    def camera_id(self) -> str:
        return self.meta.camera_id
```

**Property convenience mirrors Frame fields** used by CLI smoke (lines 102–105 of `cli.py`):
```python
"frame_id": frame.frame_id,
"camera_id": frame.camera_id,
"t_capture": frame.t_capture,
"t_publish": frame.t_ingest,
```
After protocol evolution, smoke/CLI should use `image_frame.meta` or properties, not assume bare `Frame`.

---

### `src/sentry_ai/capture/status.py` (model, request-response)

**Analog:** `src/sentry_ai/schemas/enums.py`

**Imports + StrEnum pattern** (lines 1–17 of `schemas/enums.py`):
```python
from __future__ import annotations

from enum import StrEnum


class DepthKind(StrEnum):
    """How depth values should be interpreted.
    ...
    """

    RELATIVE = "relative"
    METRIC_ESTIMATED = "metric_estimated"
    METRIC_CALIBRATED = "metric_calibrated"
```

**Copy for SourceStatus:**
```python
class SourceStatus(StrEnum):
    STARTING = "starting"
    STREAMING = "streaming"
    RECONNECTING = "reconnecting"
    ERROR = "error"
    STOPPED = "stopped"
```

**Status snapshot as Pydantic (if wire-facing)** — copy `DeviceInfo` / `extra="forbid"` from `backend/protocols.py` lines 28–36:
```python
class DeviceInfo(BaseModel):
    """Advisory device probe result (not a hard requirement at runtime)."""

    model_config = ConfigDict(extra="forbid")

    profile: RuntimeProfile
    backend: BackendName
    device_id: str
    available: bool = False
```

Use Pydantic for `/api/status` JSON; use StrEnum + dataclass for internal loop state if preferred. Prefer **Pydantic status DTO** so API responses match Phase 1 wire style.

---

### `src/sentry_ai/capture/loop.py` (service, event-driven)

**Analog:** `src/sentry_ai/plugins/builtins.py` open/read/close lifecycle (no existing thread analog)

**Lifecycle pattern** (lines 13–41 of `plugins/builtins.py`):
```python
class SyntheticSource:
    name: str = "synthetic"

    def __init__(self, camera_id: str = "synthetic0") -> None:
        self.camera_id = camera_id
        self._next_frame_id = 0
        self._open = False

    def open(self) -> None:
        self._open = True
        self._next_frame_id = 0

    def read(self) -> Frame:
        if not self._open:
            raise RuntimeError("SyntheticSource is not open; call open() first")
        ...
        return frame

    def close(self) -> None:
        self._open = False
```

**CLI try/finally resource cleanup** (lines 91–121 of `cli.py`) — apply to loop start/stop:
```python
source.open()
try:
    for _ in range(frames):
        frame = source.read()
        ...
finally:
    source.close()
    sink.close()
```

**Error raise style** when not open / disconnect — use explicit `RuntimeError` or dedicated `SourceDisconnected` with clear message (same spirit as `"SyntheticSource is not open; call open() first"`).

**No threading analog in repo.** Follow RESEARCH Pattern 3: daemon thread, status enum, exponential backoff (`0.25s → 5.0s`, factor `2.0`). Capture loop owns source lifecycle; never open cameras from FastAPI handlers.

---

### `src/sentry_ai/bus/frame_bus.py` (service, pub-sub)

**Analog:** none in codebase (first mailbox)

**Package layout to copy:** new top-level package like `backend/` — `__init__.py` with `__all__` re-exports.

**From `backend/__init__.py` (lines 1–13):**
```python
"""Device/backend abstraction stubs (FOUND-06)."""

from __future__ import annotations

from sentry_ai.backend.null import NullBackend
from sentry_ai.backend.protocols import DeviceInfo, InferenceBackend, probe_device

__all__ = [
    "DeviceInfo",
    "InferenceBackend",
    "NullBackend",
    "probe_device",
]
```

**Core algorithm:** RESEARCH Pattern 2 (`FrameBus` depth-1 + `threading.Lock` + overwrite drop count). Planner should paste RESEARCH excerpt rather than inventing queue semantics.

**Metrics field naming alignment** with `PerceptionFrame.stats` (optional dict of floats/ints) — prefer explicit typed `BusMetrics` dataclass over loose dict for Phase 2 status API.

---

### `src/sentry_ai/sources/synthetic.py` (service, streaming)

**Analog:** `src/sentry_ai/plugins/builtins.py` — **exact match; upgrade in place or move + re-export**

**Full current stub to evolve** (lines 13–41):
```python
class SyntheticSource:
    """Yields schema-valid synthetic Frames without camera hardware."""

    name: str = "synthetic"

    def __init__(self, camera_id: str = "synthetic0") -> None:
        self.camera_id = camera_id
        self._next_frame_id = 0
        self._open = False

    def open(self) -> None:
        self._open = True
        self._next_frame_id = 0

    def read(self) -> Frame:
        if not self._open:
            raise RuntimeError("SyntheticSource is not open; call open() first")
        now = time.time()
        frame = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
        )
        self._next_frame_id += 1
        return frame

    def close(self) -> None:
        self._open = False
```

**Preserve:**
- Class attribute `name: str = "synthetic"`
- Constructor default `camera_id="synthetic0"`
- Monotonic `_next_frame_id` reset on `open()`
- `_open` guard + clear RuntimeError message
- `time.time()` for `t_capture` / `t_ingest` (epoch seconds — Frame module docstring)

**Change:**
- `read() -> ImageFrame` with patterned BGR `np.ndarray`
- Set `width`/`height` on `Frame` meta (fields already exist on schema)
- Optional `fps` sleep for serve demos (not required for unit tests — tests can set high fps / zero sleep)

**Entry point remains** `sentry_ai.plugins.builtins:SyntheticSource` unless moved; if moved to `sources/synthetic.py`, update `pyproject.toml` entry point and re-export from builtins for stability:
```toml
[project.entry-points."sentry_ai.sources"]
synthetic = "sentry_ai.plugins.builtins:SyntheticSource"
```

**Recommended:** implement real class in `sources/synthetic.py`, re-export from `plugins/builtins.py` so entry point path stays valid without a breaking change.

---

### `src/sentry_ai/sources/opencv_source.py` (service, streaming)

**Analog:** same `SyntheticSource` Protocol shape; no OpenCV code exists yet

**Protocol contract to implement** (`plugins/protocols.py` lines 13–23, after evolution):
```python
@runtime_checkable
class CameraSource(Protocol):
    """Camera or synthetic frame source."""

    name: str

    def open(self) -> None: ...

    def read(self) -> ImageFrame: ...  # was Frame

    def close(self) -> None: ...
```

**Naming conventions to copy:**
- Class name: `PascalCase` + role (`SyntheticSource` → `OpenCVSource`)
- `name: str` class attribute for plugin id (`"usb"` / `"file"` / `"rtsp"` or shared `"opencv"`)
- Private state with leading underscore (`_cap`, `_open`, `_next_frame_id`)
- Docstring states what deps are/are not pulled

**Frame construction pattern** from builtins:
```python
frame = Frame(
    frame_id=self._next_frame_id,
    camera_id=self.camera_id,
    t_capture=now,
    t_ingest=now,
    width=w,
    height=h,
)
```

**Registry registration pattern** — extend `register_builtins` (lines 86–97 of `registry.py`):
```python
def register_builtins(registry: PluginRegistry) -> None:
    from sentry_ai.plugins.builtins import NoopWorker, NullSink, SyntheticSource

    if "synthetic" not in registry.list_sources():
        registry.register_source("synthetic", SyntheticSource)
    ...
```
Add `usb` / `file` / `rtsp` with same skip-if-present guards. Prefer factories or thin subclasses if one `OpenCVSource` serves all targets.

**pyproject entry points** to mirror existing groups (lines 38–45 of `pyproject.toml`):
```toml
[project.entry-points."sentry_ai.sources"]
synthetic = "sentry_ai.plugins.builtins:SyntheticSource"
# add:
# usb = "..."
# file = "..."
# rtsp = "..."
```

---

### `src/sentry_ai/sources/errors.py` (utility)

**Analog:** raise style in builtins + config load

**Existing error patterns:**
- `RuntimeError("SyntheticSource is not open; call open() first")` — operational state
- `ValueError(f"duplicate source plugin: {name}")` — registry invariants (`registry.py` line 29)
- `FileNotFoundError` / `ValueError` for config (`load.py`)
- CLI: catch, `typer.echo(..., err=True)`, `raise typer.Exit(code=1) from exc`

**Recommended:**
```python
class SourceError(RuntimeError):
    """Base error for camera source failures."""

class SourceDisconnected(SourceError):
    """Read failed because the source disconnected or hit EOF."""
```
Subclass `RuntimeError` so existing `except RuntimeError` mental model still works; prefer catching `SourceError` in capture loop.

---

### `src/sentry_ai/api/app.py` + `routes_preview.py` + `deps.py` (controller/route)

**Analog:** none for FastAPI — copy **project conventions** from CLI + package factories

**Factory style** from CLI registry builder (lines 27–31 of `cli.py`):
```python
def _build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtins(registry)
    registry.discover()
    return registry
```
→ `create_app(bus, capture_loop, ...) -> FastAPI` factory (inject deps; no global singleton if avoidable).

**CLI option style** for `serve` (lines 34–40 of `cli.py`):
```python
@app.command()
def health(
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name.",
    ),
) -> None:
```

**Serve command shape to add:**
```python
@app.command()
def serve(
    source: str = typer.Option("synthetic", help="Source plugin name."),
    host: str = typer.Option("127.0.0.1", help="Bind host (default localhost; MODEL-03)."),
    port: int = typer.Option(8000, help="Bind port."),
    device: int = typer.Option(0, help="USB device index."),
    path: str | None = typer.Option(None, help="File path for file source."),
    url: str | None = typer.Option(None, help="RTSP/URL for network source."),
    profile: str = typer.Option("cpu-fallback", help="Runtime profile name."),
) -> None:
    ...
```

**Error reporting for serve** — same as smoke config failure (lines 73–77 of `cli.py`):
```python
try:
    cfg = load_config(profile=profile)
except (ValueError, FileNotFoundError, ValidationError) as exc:
    typer.echo(f"smoke failed: config error: {exc}", err=True)
    raise typer.Exit(code=1) from exc
```

**Default bind:** hard-default `"127.0.0.1"` (MODEL-03). Document LAN opt-in in help string.

**MJPEG / StreamingResponse:** no in-repo analog — use RESEARCH Pattern 4 verbatim.

**Static packaging:** follow hatch force-include for non-Python assets (`pyproject.toml` lines 50–52):
```toml
[tool.hatch.build.targets.wheel.force-include]
"src/sentry_ai/config/profiles" = "sentry_ai/config/profiles"
```
Add similar line for `ui/static` if StaticFiles needs packaged HTML in wheels.

---

### `src/sentry_ai/plugins/protocols.py` (middleware/protocol evolution)

**Analog:** self — exact Protocol style

**Current CameraSource** (lines 13–23):
```python
@runtime_checkable
class CameraSource(Protocol):
    """Camera or synthetic frame source."""

    name: str

    def open(self) -> None: ...

    def read(self) -> Frame: ...

    def close(self) -> None: ...
```

**Evolve imports + return type:**
```python
from typing import Protocol, runtime_checkable

from sentry_ai.capture.image_frame import ImageFrame  # new


@runtime_checkable
class CameraSource(Protocol):
    name: str
    def open(self) -> None: ...
    def read(self) -> ImageFrame: ...
    def close(self) -> None: ...
```

**ModelWorker still takes Frame or ImageFrame?** Phase 2 workers are stubs — leave `process(self, frame: Frame)` or widen to `ImageFrame` when updating builtins. Prefer updating `NoopWorker.process` to accept `ImageFrame` (or `object`) so Protocol stays coherent; Phase 3 will harden.

**runtime_checkable + isinstance tests** — see `test_backend_protocols.py` line 32–34:
```python
def test_null_backend_is_inference_backend() -> None:
    backend = NullBackend()
    assert isinstance(backend, InferenceBackend)
```
Add similar for upgraded `SyntheticSource` / `OpenCVSource` vs `CameraSource`.

---

### `src/sentry_ai/config/models.py` (`SourceConfig` extension)

**Analog:** self — `SourceConfig` (lines 30–35):
```python
class SourceConfig(BaseModel):
    """Camera / frame source selection."""

    model_config = ConfigDict(extra="forbid")

    type: str = "synthetic"
```

**When extending, keep `extra="forbid"`** and optional fields with defaults:
```python
class SourceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str = "synthetic"
    device: int | None = None
    path: str | None = None
    url: str | None = None
    camera_id: str | None = None
```

**Config model conventions** from same file:
- `model_config = ConfigDict(extra="forbid")` on every model
- `Field(default_factory=...)` for nested models
- Docstrings reference requirement IDs where useful

CLI flags override profile `source.*` for Phase 2 DX (RESEARCH open question #5).

---

### Package `__init__.py` layout

**Analog:** `backend/__init__.py`, `plugins/__init__.py`, `schemas/__init__.py`

Pattern:
1. Module docstring (one line + purpose)
2. `from __future__ import annotations`
3. Explicit imports of public symbols
4. `__all__ = [...]` sorted list

New packages `capture`, `bus`, `sources`, `api` should follow this — do **not** re-export everything at `sentry_ai` root (`__init__.py` currently only exports `__version__`).

---

### Tests (new suite)

**Analogs:**

| New test file | Closest analog | What to copy |
|---------------|----------------|--------------|
| `test_sources_synthetic.py` | `test_plugins_registry.py` | open/read/close, frame_id monotonic, finally close |
| `test_sources_file.py` / `test_sources_opencv.py` | same + mock patterns | construct source, assert read metadata |
| `test_frame_bus.py` | pure unit like `test_schemas_frame.py` | no fixtures required; direct asserts |
| `test_capture_loop_reconnect.py` | lifecycle tests in registry/backend | state transitions, no hardware |
| `test_api_preview.py` | *new* httpx ASGI | TestClient against `create_app` |
| `test_cli_serve.py` | `test_cli_smoke.py` | `CliRunner`, exit codes, stdout asserts |

**Synthetic source test pattern** (lines 31–45 of `test_plugins_registry.py`) — **must update** when return type becomes `ImageFrame`:
```python
def test_synthetic_source_read_returns_valid_frame() -> None:
    source = SyntheticSource(camera_id="synthetic0")
    source.open()
    try:
        frame = source.read()
        assert isinstance(frame, Frame)  # → ImageFrame; assert frame.meta is Frame
        assert frame.camera_id == "synthetic0"
        assert frame.frame_id == 0

        frame2 = source.read()
        assert frame2.frame_id == 1
        Frame.model_validate(frame.model_dump())  # → frame.meta.model_dump()
    finally:
        source.close()
```

**CLI test pattern** (lines 1–18 of `test_cli_smoke.py`):
```python
from typer.testing import CliRunner

from sentry_ai.cli import app

runner = CliRunner()


def test_health_exits_zero_and_prints_version() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
```

For `serve` tests: prefer invoking option parsing / help / default host without binding a long-lived server, or start uvicorn briefly with synthetic source and httpx against it. MODEL-03 assertion: inspect Typer option default for `--host` == `127.0.0.1`.

**conftest factory pattern** (lines 15–34 of `conftest.py`):
```python
def make_synthetic_frame(
    frame_id: int,
    camera_id: str = "synthetic0",
) -> Frame:
    ...
```
Add `make_image_frame(...)` helper that builds `ImageFrame` with a small zeros/pattern array for bus/API tests.

**Test file naming:** `tests/test_<area>_<topic>.py` — flat under `tests/`, no nested packages yet.

**Import style in tests:** absolute `from sentry_ai....`; `from __future__ import annotations`; typed tests (`-> None`).

**Parametrize style** from `test_config_profiles.py` for multi-source kinds if useful.

---

### `pyproject.toml` dependency pattern

**Current runtime deps** (lines 22–27):
```toml
dependencies = [
  "pydantic>=2.13,<3",
  "pydantic-settings>=2.15,<3",
  "pyyaml>=6.0.3",
  "typer>=0.27",
]
```

**Add** (from RESEARCH; keep version floors consistent with existing style):
```toml
"opencv-python-headless>=4.10,<6",
"numpy>=2.0,<2.5",
"fastapi>=0.141,<1",
"uvicorn[standard]>=0.52,<1",
```

**Dev extras** (lines 29–33) — add:
```toml
"httpx>=0.28",
```

**Entry points** — extend `sentry_ai.sources` group; leave workers/sinks unchanged.

**Ruff:** already `target-version = "py311"`, selects `E,F,I,UP,B` — new code must pass import-sort (`I`) and pyupgrade (`UP`).

---

## Shared Patterns

### 1. `from __future__ import annotations` everywhere
**Source:** every Phase 1 module  
**Apply to:** all new Python files

### 2. Protocol + concrete class separation
**Source:** `plugins/protocols.py` + `plugins/builtins.py`, `backend/protocols.py` + `backend/null.py`  
**Apply to:** `CameraSource` protocol stays in `plugins/`; real sources live in `sources/`; builtins re-export or thin-wrap.

### 3. open / use / close with try/finally
**Source:** `cli.py` smoke (lines 91–121), `test_plugins_registry.py` (lines 32–45)  
**Apply to:** capture loop, any source usage in CLI serve, all source tests

### 4. Epoch seconds timestamps (`time.time()`)
**Source:** `schemas/frame.py` docstring; `builtins.SyntheticSource`  
**Apply to:** all `t_capture` / `t_ingest` assignment; status `t_capture` field

### 5. Pydantic wire types: `extra="forbid"`
**Source:** `Frame`, `DeviceInfo`, `SourceConfig`, `PerceptionFrame`  
**Apply to:** status API DTOs; never put numpy on Pydantic models

### 6. Runtime types: plain classes / dataclasses (no Pydantic)
**Source:** `NullBackend`, `SyntheticSource`, `PluginRegistry`  
**Apply to:** `ImageFrame`, `FrameBus`, capture loop, OpenCV handle ownership

### 7. Plugin discovery: register + entry points + skip-if-present
**Source:** `registry.py` `discover()` / `register_builtins()`  
**Apply to:** usb/file/rtsp registration; keep discover idempotent

### 8. CLI: Typer app, `typer.Option` defaults, stderr errors, `typer.Exit`
**Source:** `cli.py`  
**Apply to:** `sentry serve`

### 9. Package public surface via `__all__`
**Source:** `backend/__init__.py`, `plugins/__init__.py`  
**Apply to:** `capture`, `bus`, `sources`, `api` packages

### 10. Tests: flat `tests/test_*.py`, CliRunner, pytest.raises, absolute imports
**Source:** entire `tests/` suite  
**Apply to:** all Phase 2 tests; update existing synthetic/registry assertions for `ImageFrame`

### 11. Localhost-first privacy (MODEL-03)
**Source:** planning constraints + RESEARCH  
**Apply to:** serve default host `127.0.0.1`; help text warns on `0.0.0.0`

### 12. Sources → bus only; UI is subscriber
**Source:** CONTEXT locked decisions + ARCHITECTURE  
**Apply to:** capture loop publishes; FastAPI only `get_latest()`; no `VideoCapture` in request handlers

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sentry_ai/bus/frame_bus.py` | service | pub-sub | No mailbox/queue/pubsub in Phase 1 |
| `src/sentry_ai/api/app.py` | controller | request-response | No FastAPI/ASGI app yet |
| `src/sentry_ai/api/routes_preview.py` | route | streaming | No HTTP routes or StreamingResponse |
| `src/sentry_ai/api/deps.py` | middleware | request-response | No request-scoped/app-state deps |
| `src/sentry_ai/ui/static/index.html` | component | request-response | No frontend assets yet |
| `src/sentry_ai/capture/loop.py` (threading) | service | event-driven | No threads/async tasks; only lifecycle analog |

For these, use RESEARCH.md sections:
- Pattern 2 FrameBus
- Pattern 3 Capture thread + reconnect
- Pattern 4 FastAPI MJPEG + static HTML
- Pattern 5 CLI `sentry serve`
- UI-SPEC status pill + FPS/drops

---

## Protocol / Test Migration Checklist

When `CameraSource.read() -> ImageFrame`:

| Existing consumer | File | Required change |
|-------------------|------|-----------------|
| `SyntheticSource.read` | `plugins/builtins.py` or `sources/synthetic.py` | return `ImageFrame` |
| Smoke CLI unwrap | `cli.py` lines 94–105 | use `image.meta` fields for PerceptionFrame |
| Registry test | `test_plugins_registry.py` | assert `ImageFrame`; validate `meta` |
| Protocol import | `plugins/protocols.py` | import `ImageFrame` |
| Optional worker | `NoopWorker.process` | accept `ImageFrame` |
| Frame schema tests | `test_schemas_frame.py` | **keep** identity-only (no image) — must stay green |

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/**`, `tests/**`, `pyproject.toml`, phase CONTEXT/RESEARCH

**Files scanned:** ~30 source/test modules  
**Pattern extraction date:** 2026-08-07  
**Strongest analogs:** `plugins/builtins.py` (sources), `plugins/protocols.py` (Protocol style), `cli.py` (serve command), `schemas/enums.py` (status enum), `backend/__init__.py` (package layout), `test_plugins_registry.py` + `test_cli_smoke.py` (tests)

---

## PATTERN MAPPING COMPLETE

**Phase:** 2 - Camera Ingest & Live Preview  
**Files classified:** 22  
**Analogs found:** 18 / 22  

### Coverage
- Files with exact analog: 8  
- Files with role-match / partial analog: 10  
- Files with no analog: 6  

### Key Patterns Identified
- Keep Pydantic `Frame` identity-only (`extra="forbid"`); add runtime `ImageFrame` dataclass for BGR  
- Camera sources implement `name` + `open`/`read`/`close` with `_open` guards and `time.time()` timestamps  
- New packages follow `backend/`-style `__init__.py` + `__all__`; do not pollute root package  
- Plugin registry: in-tree register + entry points + skip-if-present; extend for usb/file/rtsp  
- CLI Typer commands with Option defaults; `serve` defaults host `127.0.0.1`  
- Tests: flat files, open/read/close try/finally, CliRunner for CLI; update ImageFrame assertions in existing tests  
- No in-repo analog for FrameBus/FastAPI/MJPEG/threading — use RESEARCH Patterns 2–5  

### File Created
`.planning/phases/02-camera-ingest-live-preview/02-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
