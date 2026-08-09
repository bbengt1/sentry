# Phase 8: Backend Selection & Honesty - Pattern Map

**Mapped:** 2026-08-09  
**Files analyzed:** 12  
**Analogs found:** 12 / 12  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/models/detection/factory.py` | service (factory) | request-response (construct-time) | `src/sentry_ai/cli.py` (`_build_serve_source` + serve worker block) | role-match |
| `src/sentry_ai/config/artifact_paths.py` | utility | file-I/O (path resolve) | `scripts/export/export_yolo.py` (`validate_weights`) | exact |
| `src/sentry_ai/config/profile_runtime.py` | config / utility | transform | same file (extend `ProfileRuntime`) | exact |
| `src/sentry_ai/config/models.py` | model | CRUD (config load) | same file (`ModelsConfig` / `DeviceConfig`) | exact |
| `src/sentry_ai/cli.py` (`serve`) | controller (CLI) | request-response | same file (worker + banner blocks) | exact |
| `src/sentry_ai/capture/status.py` | model | request-response | same file (optional telemetry fields) | exact |
| `src/sentry_ai/api/routes_preview.py` | route / controller | request-response | same file (`api_status` enrichment) | exact |
| `src/sentry_ai/api/app.py` + `deps.py` | provider / config | request-response | same files (optional inject pattern) | exact |
| `src/sentry_ai/models/detection/yolo_worker.py` | service | batch/transform | same file (torch path stays default) | exact |
| `src/sentry_ai/backend/protocols.py` | protocol | request-response | same + `backend/null.py` | role-match |
| `tests/test_cli_serve.py` | test | transform (source inspect) | same file (`inspect.getsource` wiring tests) | exact |
| `tests/test_api_preview.py` / `test_profile_application.py` / new factory tests | test | request-response | existing status + profile + export path tests | exact |

## Pattern Assignments

### `src/sentry_ai/models/detection/factory.py` (service/factory, construct-time)

**Analog:** `src/sentry_ai/cli.py` — `_build_serve_source` (branch factory) + serve detection-worker construction (plug-in site).

**Imports pattern** (cli serve detection block, lines 359–367):
```python
from sentry_ai.models.cache import (
    configure_model_cache,
    tier_to_open_vocab_weight,
    tier_to_weight,
)
from sentry_ai.models.detection.loop import DetectionLoop
from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
```

**Branch factory pattern** (`_build_serve_source`, lines 40–95) — copy structure for backend selection:
```python
def _build_serve_source(*, source: str, device: int, path: str | None, url: str | None, camera_id: str | None) -> Any:
    name = source.strip().lower()
    if name == "synthetic":
        return SyntheticSource(...)
    if name == "usb":
        from sentry_ai.sources.opencv_source import UsbSource
        return UsbSource(...)
    # unknown → typer.echo + Exit(1)
```

**Current plug-in site to replace** (lines 374–379) — factory must produce the same duck-typed worker:
```python
worker = YoloDetectionWorker(
    weights=rt.detector_weights,
    conf=0.25,
    device=rt.device,
)
det_loop = DetectionLoop(bus, worker, store)  # UNCHANGED spine
```

**Target shape** (from research; implement in factory module):
```python
# sentry_ai.models.detection.factory
def build_detection_worker(rt: ProfileRuntime, *, conf: float = 0.25) -> Any:
    """Select fixed-class detector by preferred_backend; honest live identity."""
    backend = str(rt.preferred_backend).strip().lower()
    if backend in {"torch", "cpu"}:
        return YoloDetectionWorker(weights=rt.detector_weights, conf=conf, device=rt.device)
    if backend == "onnxruntime":
        # Phase 8: wire branch; may stub / torch with live=torch + reason until Phase 9
        ...
    if backend == "tensorrt":
        # Phase 8: wire branch; may stub / torch with live=torch + reason until Phase 10
        ...
    # default desktop path
    return YoloDetectionWorker(...)
```

**Graceful ImportError pattern** (lines 387–396) — keep at serve level, not inside DetectionLoop:
```python
except ImportError as exc:
    typer.echo(
        "detection disabled: detect extra not installed "
        f"({exc}). Install with: uv sync --extra detect",
        err=True,
    )
    worker = None
    det_loop = None
```

**Worker duck-type contract** (`yolo_worker.py` lines 28–65) — factory products must expose:
```python
name: str
def process(frame) -> list[Detection]
def get_conf() -> float
def set_conf(conf: float) -> None
```

**Secondary analog:** `src/sentry_ai/backend/null.py` — no-op backend that never imports torch/ORT (for CI stubs).

**Do not touch:** `DetectionLoop` (`models/detection/loop.py`) — spine frozen (EDGE-RT-01).

---

### `src/sentry_ai/config/artifact_paths.py` (utility, file-I/O)

**Analog:** `scripts/export/export_yolo.py` `validate_weights` (lines 43–69) + `src/sentry_ai/models/cache.py` `KNOWN_WEIGHTS` / `configure_model_cache`.

**Basename allowlist + traversal rejection** (export_yolo.py lines 43–69):
```python
def validate_weights(weights: str) -> str:
    """Return basename if known; raise ValueError otherwise.

    Accepts basename only — rejects path traversal, absolute paths, nested paths.
    """
    if not weights or not str(weights).strip():
        raise ValueError("weights must be a non-empty basename from KNOWN_WEIGHTS")
    name = str(weights).strip()
    if name != Path(name).name:
        raise ValueError(
            f"invalid weights path {weights!r}: use basename only "
            f"(e.g. yolo26n.pt), not directories or absolute paths"
        )
    if ".." in name or name.startswith(".") and name not in KNOWN_WEIGHTS:
        raise ValueError(f"invalid weights path {weights!r}: path traversal rejected")
    if "/" in name or "\\" in name:
        raise ValueError(f"invalid weights path {weights!r}: basename only")
    if name not in KNOWN_WEIGHTS:
        raise ValueError(f"unknown weights {name!r}: must be in KNOWN_WEIGHTS allowlist (...)")
    return name
```

**Cache root resolution order** (`models/cache.py` lines 77–100) — mirror for artifact roots:
```python
# 1. explicit arg  2. SENTRY_MODEL_CACHE env  3. ~/.cache/sentry-ai
if cache_root is not None:
    root = Path(cache_root)
else:
    env = os.environ.get("SENTRY_MODEL_CACHE")
    root = Path(env) if env else default_cache_root()
weights_dir = root / "weights"
```

**Artifact resolution order** (research ARCHITECTURE — implement with allowlist):
```text
1. Explicit config/env: models.detector_onnx|engine | SENTRY_DETECTOR_ONNX|ENGINE
2. Cache weights dir: {weights_dir}/{stem}.onnx|.engine
3. Allowlisted basenames under cache (or CWD if policy allows)
4. Miss → None (never invent path; honesty / fallback at factory)
```

**Safe full-path pattern** (when absolute paths are allowed via config/env only):
```python
# After Path.resolve():
# - reject if ".." segments remain relative to allowlisted roots
# - require path.is_file() only at load time (resolve may return candidate)
# - suffix must be .onnx / .engine / .pt as appropriate
# - stem should map from detector_weights basename (yolo26n.pt → yolo26n)
resolved = Path(candidate).expanduser().resolve()
allowed_roots = [weights_dir.resolve(), ...]
if not any(resolved == root or root in resolved.parents for root in allowed_roots):
    raise ValueError(f"artifact path outside allowlist: {resolved}")
```

**Depth-tier allowlist style** (`models/depth/mapping.py` lines 67–79) — secondary pattern for strict raise-on-unknown:
```python
def assert_depth_tier_allowed(tier: str | None) -> str:
    ...
    raise ValueError(f"depth_tier {tier!r} refused: only ...")
```

---

### `src/sentry_ai/config/profile_runtime.py` (config, transform)

**Analog:** same file — extend frozen dataclass + pure helpers; no FastAPI/torch.

**Existing shape** (lines 24–35, 82–105):
```python
@dataclass(frozen=True)
class ProfileRuntime:
    profile: RuntimeProfile
    detector_weights: str
    open_vocab_weights: str
    depth_model_id: str
    depth_tier: str
    preferred_backend: str
    device: str | None
    device_id: str

def profile_runtime(cfg: SentryConfig) -> ProfileRuntime:
    preferred = cfg.device.preferred_backend
    preferred_str = preferred.value if isinstance(preferred, BackendName) else str(preferred)
    device = device_for_backend(preferred, device_id)
    return ProfileRuntime(..., preferred_backend=preferred_str, device=device, ...)
```

**Honesty helper already present** (`device_for_backend`, lines 38–79) — never returns fake `"tensorrt"` device string:
```python
if b in {"torch", "tensorrt"}:
    ...
    # Never returns a fake "tensorrt" torch device string.
```

**Phase 8 extension fields** (research target; add optional with defaults):
```python
# Illustrative — planner discretion on exact names
detector_onnx_path: Path | None = None
detector_engine_path: Path | None = None
# live_backend may be set by factory AFTER artifact/probe, not only by profile_runtime
```

**Pure-helpers rule** (module docstring lines 1–5): no FastAPI, no torch import, no weight download.

---

### `src/sentry_ai/config/models.py` (model, config)

**Analog:** same file — additive optional fields with `extra="forbid"`.

**Pattern** (lines 10–27):
```python
class DeviceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    preferred_backend: BackendName | str = BackendName.CPU
    device_id: str = "cpu"

class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allow_cloud: bool = False
    detector_tier: str | None = None
    depth_tier: str | None = None
    # Phase 8 candidates (optional overrides — do not overload device_id):
    # detector_onnx: str | None = None
    # detector_engine: str | None = None
    # fallback_to_torch: bool = True
```

Keep `preferred_backend` as the **selector**; artifact paths are separate fields.

---

### `src/sentry_ai/cli.py` serve construction + banner (controller, request-response)

**Analog:** same file — construction order, ImportError gates, honesty notes.

**Construction sequence to preserve** (lines 338–443):
```python
rt = profile_runtime(cfg)
probe = probe_device(cfg.profile)
src = _build_serve_source(...)
bus = FrameBus()
loop = CaptureLoop(src, bus)
store = PerceptionStore()
# detection (optional extra) → depth (optional) → free_space always → create_app
```

**Replace only the YoloDetectionWorker construction** with factory; leave OV/depth/free-space as-is:
```python
# BEFORE
worker = YoloDetectionWorker(weights=rt.detector_weights, conf=0.25, device=rt.device)
# AFTER
from sentry_ai.models.detection.factory import build_detection_worker
worker = build_detection_worker(rt, conf=0.25)
# Optionally capture factory result metadata for banner/status:
# backend_requested, backend_live, backend_reason
```

**Banner pattern** (lines 446–489) — extend with requested vs live:
```python
typer.echo(f"sentry-ai {__version__} serve")
typer.echo(f"profile: {rt.profile.value}")
typer.echo(f"detector: {rt.detector_weights}")
typer.echo(f"preferred_backend: {rt.preferred_backend}")
typer.echo(f"device: {device_display}")
# Existing honesty notes (lines 458–471) — keep/evolve into backend_live lines:
if str(rt.preferred_backend) == "tensorrt":
    typer.echo(
        "note: preferred_backend=tensorrt → live path is still PyTorch "
        "CUDA if available; build engines via export recipes "
        "(not silent TRT inference)",
        err=True,
    )
elif str(rt.preferred_backend) == "onnxruntime":
    typer.echo(
        "note: preferred_backend=onnxruntime → live path is PyTorch CPU; "
        "ORT is the export target (not silent ORT inference)",
        err=True,
    )
```

**Phase 8 banner target** (BACK-02):
```python
typer.echo(f"backend_requested: {backend_requested}")
typer.echo(f"backend_live: {backend_live}")
# If they differ, one-line reason on stderr (same style as notes above)
```

**Lifecycle order** (lines 497–522) — do not reorder:
start: capture → det → depth → free_space → open_vocab  
stop: reverse

**No module-level torch** — tests assert `import torch` not in pre-`def serve` source.

---

### `src/sentry_ai/capture/status.py` StatusSnapshot fields (model)

**Analog:** same file — optional fields with defaults so older callers remain valid.

**Extension pattern** (lines 41–73) — add nullable fields at end:
```python
class StatusSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    # ... existing capture + det + depth + free_space + pipeline + ov ...
    # Optional open-vocab telemetry (Phase 6 OVD).
    ov_fps: float | None = None
    ov_latency_ms: float | None = None
    # Phase 8 honesty (BACK-02):
    backend_requested: str | None = None
    backend_live: str | None = None
    # optional later: backend_reason: str | None = None
```

**build_status base** (`capture/loop.py` lines 81–101) only fills capture fields. Enrichment for det/depth/pipeline already happens in `routes_preview.api_status` — **prefer same enrichment site** for backend identity (or set on snapshot via app.state if injected at create_app).

---

### `src/sentry_ai/api/routes_preview.py` `/api/status` (route, request-response)

**Analog:** same file — best-effort enrichment from `app.state` after `loop.build_status`.

**Core status handler** (lines 83–178):
```python
@router.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    loop = _capture_loop(request)
    snapshot = loop.build_status(bind=_bind(request))
    data = snapshot.model_dump()
    # Enrich from store / worker / pipeline_state / open_vocab_loop
    pipeline_state = getattr(request.app.state, "pipeline_state", None)
    if pipeline_state is not None:
        try:
            pipe = pipeline_state.snapshot()
            data["detection_enabled"] = pipe.get("detection_enabled")
            ...
        except Exception:  # noqa: BLE001 — status is best-effort
            pass
    return data
```

**Phase 8 enrichment** (copy pipeline_state style):
```python
# Prefer explicit app.state fields set by create_app / serve
backend_requested = getattr(request.app.state, "backend_requested", None)
backend_live = getattr(request.app.state, "backend_live", None)
if backend_requested is not None:
    data["backend_requested"] = backend_requested
if backend_live is not None:
    data["backend_live"] = backend_live
# Never invent backend_live=tensorrt|onnxruntime when torch worker is running
```

**Best-effort rule:** status must not raise if factory metadata missing (Phase 2 callers).

---

### `src/sentry_ai/api/app.py` + `deps.py` (provider)

**Analog:** same files — optional kwargs default `None`, attach to `app.state`.

**Injection pattern** (`app.py` lines 23–94):
```python
def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
    perception_store: Any | None = None,
    detection_worker: Any | None = None,
    # ... existing optional loops ...
    # Phase 8 candidates:
    # backend_requested: str | None = None,
    # backend_live: str | None = None,
) -> FastAPI:
    app.state.detection_worker = detection_worker
    # app.state.backend_requested = backend_requested
    # app.state.backend_live = backend_live
```

Mirror fields on `AppState` dataclass in `deps.py` for typed convenience.

---

### Path validation tests (utility, test)

**Analog:** `tests/test_export_script_cli.py` lines 45–75, 107–122.

```python
def test_validate_weights_rejects_path_traversal() -> None:
    mod = _import_export_module()
    for bad in (
        "../../etc/passwd",
        "../yolo26n.pt",
        "/tmp/yolo26n.pt",
        "subdir/yolo26n.pt",
        "yolo26n.pt/../evil.pt",
    ):
        with pytest.raises(ValueError):
            mod.validate_weights(bad)
```

Apply same cases to artifact path resolver (plus outside-allowlist absolute paths).

---

### CLI serve wiring tests (`tests/test_cli_serve.py`)

**Analog:** same file — `inspect.getsource(cli_mod.serve)` structural assertions.

**Profile wiring test** (lines 224–237) — extend for factory:
```python
def test_serve_applies_profile_runtime() -> None:
    source = inspect.getsource(cli_mod.serve)
    assert "profile_runtime" in source
    assert "rt.detector_weights" in source
    assert "device=rt.device" in source
    assert "preferred_backend" in source
    assert "tensorrt" in source
    assert "onnxruntime" in source
```

**New assertions to add (planner):**
```python
assert "build_detection_worker" in source
assert "backend_requested" in source
assert "backend_live" in source
# Torch path still constructible; DetectionLoop still used
assert "DetectionLoop" in source
# No direct YoloDetectionWorker(...) in serve if fully factory-driven
# (or allow import only inside factory)
```

**Lifecycle / order tests** (lines 103–221) — keep; factory must not break start/stop order.

---

### Status API tests (`tests/test_api_preview.py`)

**Analog:** `test_api_status_includes_pipeline_stage_flags` (lines 649–707) + `test_api_status_returns_expected_keys` (lines 50–68).

```python
def test_api_status_includes_pipeline_stage_flags() -> None:
    app = create_app(..., pipeline_state=state)
    with TestClient(app) as client:
        data = client.get("/api/status").json()
        assert data["detection_enabled"] is False
    # Without injection, keys omitted (None) — not forced false
    app2 = create_app(bus=bus2, capture_loop=loop2, bind="...")
    assert client.get("/api/status").json().get("detection_enabled") is None
```

**Phase 8 TestClient pattern:**
```python
app = create_app(
    bus=bus,
    capture_loop=loop,
    bind="127.0.0.1:8000",
    backend_requested="tensorrt",
    backend_live="torch",  # honest when TRT not loaded
)
with TestClient(app) as client:
    data = client.get("/api/status").json()
    assert data["backend_requested"] == "tensorrt"
    assert data["backend_live"] == "torch"
```

---

### Profile runtime tests (`tests/test_profile_application.py`)

**Analog:** same file — parametrize profiles + honesty for tensorrt device string.

```python
@pytest.mark.parametrize(
    ("profile", "detector_w", "ov_w", "backend"),
    [
        ("desktop-gpu", "yolo26s.pt", "yoloe-26s-seg.pt", "torch"),
        ("jetson", "yolo26n.pt", "yoloe-26n-seg.pt", "tensorrt"),
        ("cpu-fallback", "yolo26n.pt", "yoloe-26n-seg.pt", "onnxruntime"),
    ],
)
def test_profile_runtime_all_profiles(...):
    rt = profile_runtime(load_config(profile=profile))
    assert str(rt.preferred_backend) == backend

def test_profile_runtime_jetson_device_not_tensorrt_string() -> None:
    rt = profile_runtime(load_config(profile="jetson"))
    assert "tensorrt" not in str(rt.device).lower()
```

**Phase 8 factory unit tests** (new file suggested: `tests/test_detection_factory.py` or extend profile tests):
- desktop-gpu → torch worker, `backend_live=torch`
- jetson preferred tensorrt without engine → live torch (or NotImplemented stub) with **requested=tensorrt**, **live≠tensorrt**
- cpu-fallback preferred onnxruntime without onnx → live torch/cpu honesty
- path resolver rejects `../`, absolute outside allowlist

**Backend probe analog:** `tests/test_backend_protocols.py` — `probe_device` never raises; shape per profile.

---

## Shared Patterns

### Factory plug-in at serve only (EDGE-RT-01 / BACK-01)

**Source:** `cli.py` serve + research ARCHITECTURE  
**Apply to:** detection worker construction only  

- DetectionLoop / FrameBus / PerceptionStore / `/v1` **frozen**
- Open-vocab + depth stay PyTorch this milestone
- Branch selection mirrors `_build_serve_source` (explicit if/elif, local imports for optional deps)

### Backend honesty (BACK-02)

**Source:** `cli.py` lines 458–471 honesty notes + `device_for_backend` never fakes tensorrt device  
**Apply to:** factory return metadata, serve banner, `/api/status`  

| Field | Meaning |
|-------|---------|
| `backend_requested` / `preferred_backend` | Operator intent from profile |
| `backend_live` | What is actually running (`torch` while ORT/TRT stubs) |

**Rule:** never claim `backend_live=tensorrt|onnxruntime` when torch worker is live.

### Optional StatusSnapshot fields

**Source:** `capture/status.py`  
**Apply to:** `backend_requested`, `backend_live`  

- `extra="forbid"`
- defaults `None` for backward compatibility
- enrich in `api_status` from `app.state` (same as pipeline/ov)

### Path allowlist (BACK-04)

**Source:** `export_yolo.validate_weights` + `models.cache.KNOWN_WEIGHTS` + `configure_model_cache`  
**Apply to:** `.onnx` / `.engine` / optional absolute overrides  

- Basename-only for known stems
- Absolute paths only if under allowlisted roots (cache, explicit env, config)
- Reject `..`, nested relative, unknown basenames
- No prebuilt engines in wheel

### Graceful extras / never-raise probes

**Source:** serve `ImportError` gates; `probe_device` never-raises  
**Apply to:** ORT/TRT optional imports in factory  

```python
# probe_device — never raises, never hard-fails serve
# factory ImportError for onnxruntime/tensorrt packages → honest fallback or clear error
```

### Test styles

| Style | Analog | Use for |
|-------|--------|---------|
| `inspect.getsource(cli_mod.serve)` | `test_cli_serve.py` | Factory + banner wiring without binding server |
| `TestClient` + `create_app` | `test_api_preview.py` | `/api/status` backend fields |
| Pure unit + `load_config` | `test_profile_application.py` | profile → preferred_backend / device honesty |
| Path traversal matrix | `test_export_script_cli.py` | artifact resolver |
| Mock optional deps | `test_backend_protocols.py` | missing torch/ORT without GPU |

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| — | — | — | All Phase 8 surfaces have close analogs; ORT/TRT **live loaders** intentionally deferred (Phases 9–10) — Phase 8 stubs copy `NullBackend` / honesty notes |

**Note:** There is no existing `build_detection_worker` module — closest are `_build_serve_source` (branch factory) and the inline `YoloDetectionWorker(...)` construction in `serve`. Live ORT/TRT InferenceBackend adapters do not exist yet beyond `NullBackend` + Protocol.

## Closest Analogs Table (planner quick ref)

| Concern | Copy from | Lines / symbol |
|---------|-----------|----------------|
| Worker construction plug-in | `src/sentry_ai/cli.py` | 353–396 `YoloDetectionWorker` + `DetectionLoop` |
| Branch factory style | `src/sentry_ai/cli.py` | 40–95 `_build_serve_source` |
| Torch worker contract | `src/sentry_ai/models/detection/yolo_worker.py` | `YoloDetectionWorker` process/conf |
| Profile → weights/backend | `src/sentry_ai/config/profile_runtime.py` | `ProfileRuntime`, `device_for_backend`, `profile_runtime` |
| Preferred backend enum | `src/sentry_ai/schemas/enums.py` | `BackendName` |
| Device probe (advisory) | `src/sentry_ai/backend/protocols.py` | `probe_device`, `DeviceInfo` |
| Stub backend | `src/sentry_ai/backend/null.py` | `NullBackend` |
| Status field extension | `src/sentry_ai/capture/status.py` | optional `None` fields on `StatusSnapshot` |
| `/api/status` enrichment | `src/sentry_ai/api/routes_preview.py` | `api_status` + pipeline_state block |
| App injection | `src/sentry_ai/api/app.py`, `deps.py` | optional kwargs → `app.state` |
| Banner honesty | `src/sentry_ai/cli.py` | 446–471 preferred_backend notes |
| Path allowlist | `scripts/export/export_yolo.py` | `validate_weights` |
| Cache roots / known weights | `src/sentry_ai/models/cache.py` | `KNOWN_WEIGHTS`, `configure_model_cache` |
| Serve inspect tests | `tests/test_cli_serve.py` | `test_serve_applies_profile_runtime` et al. |
| Status TestClient tests | `tests/test_api_preview.py` | pipeline/det status tests |
| Profile honesty tests | `tests/test_profile_application.py` | all profile + tensorrt device tests |
| Traversal tests | `tests/test_export_script_cli.py` | `test_validate_weights_rejects_path_traversal` |

## Metadata

**Analog search scope:**  
`src/sentry_ai/cli.py`, `config/`, `models/detection/`, `models/cache.py`, `models/device.py`, `backend/`, `capture/status.py`, `api/routes_preview.py`, `api/app.py`, `api/deps.py`, `scripts/export/export_yolo.py`, `tests/test_cli_serve.py`, `tests/test_api_preview.py`, `tests/test_profile_application.py`, `tests/test_export_script_cli.py`, `tests/test_backend_protocols.py`, `.planning/research/ARCHITECTURE.md`

**Files scanned:** ~25  
**Pattern extraction date:** 2026-08-09  
**Plans this map supports:** 08-01 (factory + artifact + profile), 08-02 (status/banner honesty)
