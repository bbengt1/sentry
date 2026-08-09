# Phase 7: Edge Profiles & Extension Stubs - Pattern Map

**Mapped:** 2026-08-08  
**Files analyzed:** 18  
**Analogs found:** 16 / 18  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/config/profiles/{desktop-gpu,jetson,cpu-fallback}.yaml` | config | file-I/O | existing YAML profiles (self) | exact |
| `src/sentry_ai/config/models.py` | model | transform | self (`ModelsConfig` / `DeviceConfig`) | self-extend |
| `src/sentry_ai/config/load.py` | service | file-I/O | self (`load_config` merge + env) | self-extend |
| `src/sentry_ai/models/cache.py` (`tier_to_weight` + depth tier helper) | utility | transform | self `tier_to_weight` | exact |
| `src/sentry_ai/cli.py` (`serve` profile wiring + `--no-ui`) | config | request-response | self `serve` + optional-extra gates | exact |
| `src/sentry_ai/api/app.py` (optional UI / headless) | config | request-response | self `create_app` router include | self-extend |
| `src/sentry_ai/api/routes_preview.py` (root HTML gate) | route | request-response | self `root_preview` FileResponse | self-extend |
| `src/sentry_ai/backend/protocols.py` (`probe_device`) | service | request-response | self stub `probe_device` | self-extend |
| `src/sentry_ai/plugins/builtins.py` (voice no-op) | service | event-driven | `NoopWorker` / `NullSink` | exact |
| `src/sentry_ai/plugins/registry.py` + `pyproject.toml` entry points | config | transform | `register_builtins` + EP groups | exact |
| ROS2 scaffold (`extensions/ros2/` or `docs/ros2/` + optional module) | config | — | `docs/camera-sources.md` honesty matrix + `NullSink` | role-match |
| `docs/export/` or `scripts/export/` recipes | config | file-I/O | `docs/camera-sources.md` + `THIRD_PARTY_MODELS.md` | role-match |
| `README.md` (desktop path, edge honesty, headless, safety) | config | — | existing README phase sections | exact |
| `tests/test_config_profiles.py` (tier/backend assertions) | test | CRUD | self + `test_model_cache.py` | exact |
| `tests/test_cli_serve.py` (headless + profile flags) | test | request-response | self inspect-source + CliRunner | exact |
| `tests/test_api_preview.py` / headless TestClient | test | request-response | `test_api_preview.py` create_app + TestClient | exact |
| `tests/test_plugins_registry.py` (voice sink/worker) | test | CRUD | self register_builtins tests | exact |
| Multi-cam `camera_id` schema tests | test | transform | `test_schemas_frame.py` + `test_schemas_perception.py` | exact |
| Doc assertion tests (export / safety) | test | file-I/O | `test_third_party_models_doc.py` | exact |

## Pattern Assignments

### 1. Config / profile loading (EDGE-02)

**Analogs:**  
- `src/sentry_ai/config/load.py`  
- `src/sentry_ai/config/models.py`  
- `src/sentry_ai/config/profiles/*.yaml`  
- `src/sentry_ai/schemas/enums.py` (`RuntimeProfile`, `BackendName`)  
- `src/sentry_ai/models/cache.py` (`tier_to_weight`)  
- `src/sentry_ai/cli.py` serve (already applies `detector_tier`)

**YAML shape (copy exactly — do not invent new root keys without model fields):**

```yaml
# desktop-gpu.yaml / jetson.yaml / cpu-fallback.yaml
profile: desktop-gpu          # must match RuntimeProfile value
device:
  preferred_backend: torch    # BackendName: torch|onnxruntime|tensorrt|openvino|cpu
  device_id: "cuda:0"         # advisory string
models:
  allow_cloud: false
  defaults_commercially_friendly: true
  detector_tier: s            # n|s|m → YOLO weights
  depth_tier: small           # currently advisory; wire if implementing tier map
source:
  type: synthetic
```

**Current built-in tier matrix (already in YAML):**

| Profile | `preferred_backend` | `device_id` | `detector_tier` | `depth_tier` |
|---------|---------------------|------------|-----------------|--------------|
| `desktop-gpu` | `torch` | `cuda:0` | `s` | `small` |
| `jetson` | `tensorrt` | `0` | `n` | `small` |
| `cpu-fallback` | `onnxruntime` | `cpu` | `n` | `small` |

**Load + merge order** (`load.py` lines 84–117):

```python
# built-in profile YAML → optional user file deep_merge → env
# SENTRY_PROFILE selects profile when profile arg is None
# SENTRY_ALLOW_CLOUD always wins when set; else allow_cloud defaults false
# yaml.safe_load only (never yaml.load)
```

**Pydantic models** (`models.py`) — all `extra="forbid"`:

```python
class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    allow_cloud: bool = False
    defaults_commercially_friendly: bool = True
    detector_tier: str | None = None
    depth_tier: str | None = None
```

**How new fields attach:**
1. Add field to `DeviceConfig` / `ModelsConfig` / `SentryConfig` with default + `extra="forbid"`.
2. Set value in each profile YAML under the matching nested key.
3. Extend `load_config` only if env override is required (mirror `SENTRY_ALLOW_CLOUD` / `SENTRY_PROFILE`).
4. Consume in `cli.serve` (or worker constructors) — YAML alone is advisory until serve wires it.

**Detector tier already applied at serve** (`cli.py` lines 345–356):

```python
from sentry_ai.models.cache import configure_model_cache, tier_to_weight
configure_model_cache()
weights = tier_to_weight(cfg.models.detector_tier)
worker = YoloDetectionWorker(weights=weights, conf=0.25)
```

**`tier_to_weight`** (`cache.py` lines 23–52):

```python
_TIER_TO_WEIGHT: dict[str, str] = {
    "n": "yolo26n.pt",
    "s": "yolo26s.pt",
    "m": "yolo26m.pt",
}
DEFAULT_WEIGHT = "yolo26n.pt"

def tier_to_weight(tier: str | None) -> str:
    if tier is None:
        return DEFAULT_WEIGHT
    key = str(tier).strip().lower()
    return _TIER_TO_WEIGHT.get(key, DEFAULT_WEIGHT)
```

**Gaps for Phase 7 (wire, do not invent parallel systems):**
- `depth_tier` is loaded but **not** passed into `DepthAnythingWorker` today (always Small relative via `MODE_TO_MODEL`).
- `preferred_backend` / `device_id` are advisory; workers use `resolve_device()` (cuda > mps > cpu), not profile backend.
- Open-vocab weights are hard-coded `YOLOE_WEIGHTS` (`yoloe-26s-seg.pt`); edge path should prefer `yoloe-26n-seg.pt` on jetson/cpu (KNOWN_WEIGHTS already lists both).
- Profile default for serve is still `"cpu-fallback"` (typer Option); discretionary: auto-switch desktop-gpu when CUDA present vs keep cpu-fallback default.

**Enum set is fixed** (`enums.py` lines 21–26) — do not add profiles without updating enum + YAML + tests:

```python
class RuntimeProfile(StrEnum):
    DESKTOP_GPU = "desktop-gpu"
    JETSON = "jetson"
    CPU_FALLBACK = "cpu-fallback"
```

---

### 2. CLI flag patterns (EDGE-05 headless + profile)

**Analog:** `src/sentry_ai/cli.py` entire Typer surface.

**Typer app skeleton** (lines 26–30):

```python
app = typer.Typer(
    name="sentry",
    help="Sentry AI — camera-only perception",
    no_args_is_help=True,
)
```

**Option style for `serve`** (lines 262–301) — keyword options, defaults, multi-line help for privacy:

```python
@app.command()
def serve(
    source: str = typer.Option("synthetic", help="Source plugin: synthetic | usb | file | rtsp."),
    host: str = typer.Option(
        "127.0.0.1",
        help=(
            "Bind host (default localhost — MODEL-03). "
            "Setting 0.0.0.0 exposes the live camera on the LAN without auth "
            "(opt-in only)."
        ),
    ),
    port: int = typer.Option(8000, help="Bind port."),
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name (loaded for consistency; no ML).",
    ),
    camera_id: str | None = typer.Option(None, help="Optional camera_id override for Frame identity."),
) -> None:
```

**Headless flag — copy this option style (prescriptive):**

```python
no_ui: bool = typer.Option(
    False,
    "--no-ui",
    help="Serve perception API without Live Preview HTML/MJPEG UI (EDGE-05).",
),
# Optional env mirror (discretionary): SENTRY_HEADLESS=1 via load_config or os.environ
```

Prefer **`--no-ui` on `serve`** over a separate `sentry api` command (keeps one lifecycle: capture + workers + uvicorn). Env `SENTRY_HEADLESS` is discretionary dual input, same as `SENTRY_PROFILE`.

**Error / exit pattern** (used everywhere):

```python
try:
    cfg = load_config(profile=profile)
except (ValueError, FileNotFoundError, ValidationError) as exc:
    typer.echo(f"serve failed: config error: {exc}", err=True)
    raise typer.Exit(code=1) from exc

if cfg.models.allow_cloud:
    typer.echo(
        "serve failed: allow_cloud is true; default path must stay local OSS",
        err=True,
    )
    raise typer.Exit(code=1)
```

| Situation | Pattern |
|-----------|---------|
| User error (bad source, missing path/url, bad profile) | `typer.echo(..., err=True)` + `raise typer.Exit(code=1)` |
| Soft optional extra missing | log to stderr, set worker/loop `None`, continue serve |
| Non-localhost bind | warning on stderr, still run |
| Ctrl+C / interrupt | `sys.exit(130)` in `main()` |

**Optional extra soft-disable** (lines 344–390) — ImportError does not abort serve:

```python
try:
    # import worker + loop; construct with profile tiers
except ImportError as exc:
    typer.echo(
        "detection disabled: detect extra not installed "
        f"({exc}). Install with: uv sync --extra detect",
        err=True,
    )
    worker = None
    det_loop = None
```

**Banner lines** after `create_app` — add headless + profile + weights:

```python
typer.echo(f"sentry-ai {__version__} serve")
typer.echo(f"profile: {cfg.profile.value}")  # NEW: make profile visible
typer.echo(f"source: {src.name} camera_id=...")
typer.echo(f"bind: http://{bind}/  (Live Preview)")  # or "(headless API)" when no_ui
```

**Start/stop order** (do not reorder for headless — only UI changes):

```
Start: capture → det → depth → free_space → open_vocab
Stop:  open_vocab → free_space → depth → det → capture
```

Headless still starts all available perception loops; only static/MJPEG UI is skipped.

---

### 3. `create_app` / static UI mount (EDGE-05)

**Analogs:**  
- `src/sentry_ai/api/app.py`  
- `src/sentry_ai/api/routes_preview.py` (`root_preview`, MJPEG)

**Current factory** always mounts full preview router (`app.py` lines 23–96):

```python
def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
    perception_store: Any | None = None,
    # ... workers / loops ...
) -> FastAPI:
    app = FastAPI(
        title="Sentry AI — Live Preview",
        docs_url=None,   # OpenAPI disabled
        redoc_url=None,
        lifespan=lifespan,
    )
    # attach app.state.* then:
    app.include_router(preview_router)   # GET /, /api/status, /preview/mjpeg, ...
    app.include_router(detection_router)
    app.include_router(depth_router)
    app.include_router(pipeline_router)
    app.include_router(open_vocab_router)
    app.include_router(v1_router)
    return app
```

**Static UI is not Starlette `StaticFiles`** — it is a single FileResponse route:

```python
# routes_preview.py lines 36–39, 299–305
_INDEX_HTML = (
    Path(__file__).resolve().parents[1] / "ui" / "static" / "index.html"
)

@router.get("/", response_model=None)
async def root_preview() -> FileResponse | HTMLResponse:
    if _INDEX_HTML.is_file():
        return FileResponse(path=_INDEX_HTML, media_type="text/html; charset=utf-8")
```

Packaged via hatch force-include (`pyproject.toml` lines 74–77):

```toml
[tool.hatch.build.targets.wheel.force-include]
"src/sentry_ai/config/profiles" = "sentry_ai/config/profiles"
"src/sentry_ai/ui/static" = "sentry_ai/ui/static"
```

**Headless pattern (prescriptive — extend, do not invent a second app factory):**

```python
def create_app(..., enable_ui: bool = True) -> FastAPI:
    ...
    if enable_ui:
        app.include_router(preview_router)
    else:
        # Still need /api/status for ops? Prefer either:
        # (A) split status into a small always-on router, or
        # (B) keep preview_router but gate only GET / and MJPEG.
        # Perception API is v1_router + control routers — always include those.
        pass
    app.include_router(detection_router)
    # ... depth, pipeline, open_vocab, v1 always on
```

**Recommended minimal change for EDGE-05:**
1. Add `enable_ui: bool = True` to `create_app`.
2. When `False`: do **not** register `GET /` HTML and `/preview/mjpeg` (or return 404).  
   Keep `GET /api/status` and all perception/control APIs (`/v1/*`, `/api/detection/*`, etc.).
3. `cli.serve(..., no_ui=...)` passes `enable_ui=not no_ui`.
4. Tests: TestClient `GET /` → 404 (or absent) when headless; `GET /v1/snapshot` still 200.

**Do not:**
- Remove `ui/static` from the package for headless installs.
- Create a separate FastAPI app class.
- Mount React/Vite.
- Require UI assets to exist for API-only mode.

**Caller owns loop lifecycle** — `create_app` never starts threads (docstring line 40–42). Headless does not change that.

---

### 4. Plugin registry + entry points (EDGE-04 voice / ROS2 stubs)

**Analogs:**  
- `src/sentry_ai/plugins/protocols.py`  
- `src/sentry_ai/plugins/builtins.py`  
- `src/sentry_ai/plugins/registry.py`  
- `pyproject.toml` entry-point groups  
- `tests/test_plugins_registry.py`

**Protocols** (runtime_checkable):

```python
# CameraSource: name, open, read → ImageFrame, close
# ModelWorker:  name, process(frame) → object | None
# Sink:         name, emit(item), close
```

**No-op stubs** (`builtins.py`) — voice should twin this style:

```python
class NoopWorker:
    name: str = "noop"
    def process(self, frame: ImageFrame | object) -> object | None:
        _ = frame
        return None

class NullSink:
    name: str = "null"
    def emit(self, item: object) -> None:
        _ = item
    def close(self) -> None:
        return None
```

**Voice no-op (prescriptive):**

```python
# plugins/builtins.py or plugins/voice.py
class VoiceNoopSink:  # or VoiceNoopWorker if input path
    """EDGE-04: voice plugin stub — no ASR/TTS; documents extension point."""
    name: str = "voice-noop"
    def emit(self, item: object) -> None:
        _ = item  # discard perception events
    def close(self) -> None:
        return None
```

Register as **sink** (perception consumer) unless product needs mic input — then `ModelWorker`-like protocol is wrong; keep Sink for outbound TTS/events.

**Registry patterns** (`registry.py`):

```python
def register_sink(self, name: str, cls: type) -> None:
    if name in self._sinks:
        raise ValueError(f"duplicate sink plugin: {name}")
    self._sinks[name] = cls

def discover(self) -> None:
    # entry_points groups: sentry_ai.sources | workers | sinks
    # skip-if-present when name already registered (idempotent with builtins)
```

**`register_builtins` optional-import gate** (lines 103–123) — for heavy deps only:

```python
if "yolo-fixed" not in registry.list_workers():
    try:
        from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
    except ImportError:
        pass
    else:
        registry.register_worker("yolo-fixed", YoloDetectionWorker)
```

Voice no-op has **no heavy import** — register unconditionally like `null` / `noop`.

**Entry points** (`pyproject.toml` lines 57–69):

```toml
[project.entry-points."sentry_ai.sources"]
synthetic = "sentry_ai.plugins.builtins:SyntheticSource"
# ...

[project.entry-points."sentry_ai.workers"]
noop = "sentry_ai.plugins.builtins:NoopWorker"
yolo-fixed = "..."
depth-anything-v2-small = "..."

[project.entry-points."sentry_ai.sinks"]
null = "sentry_ai.plugins.builtins:NullSink"
# NEW:
# voice-noop = "sentry_ai.plugins.builtins:VoiceNoopSink"
```

**CLI discovery** (`cli.py` lines 33–37):

```python
def _build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtins(registry)
    registry.discover()
    return registry
```

`sentry health` lists sources/workers/sinks — voice-noop should appear in sinks after register.

**ROS2 scaffold — no production package today.** Closest patterns:
1. **Docs honesty matrix** like `docs/camera-sources.md` (limits table + deferred list).
2. **NullSink** as behavioral twin: importable class that accepts `PerceptionFrame`/dict and no-ops with a clear docstring "not a ROS2 node".
3. Optional layout (discretionary):
   - `docs/ros2-bridge.md` + `src/sentry_ai/extensions/ros2/bridge.py` with `NotImplementedError` / pass-through stub  
   - **Do not** add `rclpy` to core or optional extras for v1 stubs  
   - **Do not** invent a fourth plugin group; if registered, use `sentry_ai.sinks` → `ros2-stub`

---

### 5. Test patterns

**Analogs:**  
- `tests/test_config_profiles.py`  
- `tests/test_model_cache.py`  
- `tests/test_cli_serve.py`  
- `tests/test_cli_smoke.py`  
- `tests/test_plugins_registry.py`  
- `tests/test_api_preview.py` / `test_api_v1.py`  
- `tests/test_schemas_frame.py` / `test_schemas_perception.py`  
- `tests/test_third_party_models_doc.py`  
- `tests/test_backend_protocols.py`  
- `tests/conftest.py`

#### Profile / tier tests

```python
# test_config_profiles.py pattern
@pytest.mark.parametrize("profile", ["desktop-gpu", "jetson", "cpu-fallback"])
def test_allow_cloud_false_on_all_profiles(profile: str) -> None:
    cfg = load_profile(profile)
    assert cfg.models.allow_cloud is False

# Extend with EDGE-02 assertions:
# load_profile("desktop-gpu").models.detector_tier == "s"
# load_profile("jetson").device.preferred_backend == "tensorrt"
# load_profile("cpu-fallback").models.detector_tier == "n"
```

```python
# test_model_cache.py
assert tier_to_weight("n") == "yolo26n.pt"
assert tier_to_weight(None) == "yolo26n.pt"
```

#### CLI flags (inspect-source + CliRunner)

```python
# test_cli_serve.py — prefer source inspection for wiring; CliRunner for help/exit
runner = CliRunner()

def test_serve_help_shows_localhost_default() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    assert "127.0.0.1" in result.stdout

def test_serve_source_wires_detection_loop_lifecycle() -> None:
    source = inspect.getsource(cli_mod.serve)
    assert "tier_to_weight" in source
    assert "create_app" in source
```

**Headless tests should:**
1. Assert `--no-ui` in help / option default false.
2. `inspect.getsource(cli_mod.serve)` contains `no_ui` / `enable_ui`.
3. Optional: unit-test `create_app(enable_ui=False)` with TestClient — `GET /` not 200 HTML; `/v1/snapshot` works.

#### FastAPI TestClient + finally stop

```python
# test_api_preview.py / test_api_v1.py
source = SyntheticSource(camera_id="synthetic0", fps=0.0)
bus = FrameBus()
loop = CaptureLoop(source, bus)
loop.start()
try:
    app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
    with TestClient(app) as client:
        resp = client.get("/api/status")
        assert resp.status_code == 200
finally:
    loop.stop()
```

Inject fakes via `create_app(..., perception_store=..., detection_worker=...)` — never download weights.

#### Schema multi-cam `camera_id` (EDGE-04)

```python
# test_schemas_frame.py / test_schemas_perception.py already enforce:
# - camera_id required, min_length=1
# - empty string rejected
# - extra fields forbidden

# Extend multi-cam stub tests (no fusion):
def test_distinct_camera_ids_are_independent_identities() -> None:
    a = Frame(frame_id=0, camera_id="cam_left", t_capture=1.0)
    b = Frame(frame_id=0, camera_id="cam_right", t_capture=1.0)
    assert a.camera_id != b.camera_id
    # PerceptionFrame same contract
```

Also assert store products preserve `camera_id` (see `test_detection_loop.py` camA pattern). **No multi-process fusion tests.**

#### Plugin registration

```python
# test_plugins_registry.py
registry = PluginRegistry()
register_builtins(registry)
assert "null" in registry.list_sinks()
# NEW: assert "voice-noop" in registry.list_sinks()
registry.discover()  # still idempotent
```

#### Doc content tests

```python
# test_third_party_models_doc.py pattern
DOC_PATH = REPO_ROOT / "THIRD_PARTY_MODELS.md"
text = DOC_PATH.read_text(encoding="utf-8")
assert "Apache-2.0" in text
```

For export/safety docs: assert file exists + keywords (`ONNX`, `TensorRT`, `on-device`, `localhost`, `not autonomy` / `perception-only`, Jetson honesty). Do **not** require Jetson hardware in CI.

#### Backend probe honesty

```python
# test_backend_protocols.py
info = probe_device(RuntimeProfile.DESKTOP_GPU)
assert info.available is False  # Phase 1 honesty — change only if Phase 7 implements real probe
```

If real probe is added, keep tests that do not require CUDA; mock torch or gate with `torch.cuda.is_available()`.

---

### 6. Docs patterns in this repo

**Existing doc surfaces:**

| Doc | Role | Style to copy |
|-----|------|----------------|
| `README.md` | Maker entry: install, serve, optional extras, API tables, phase scopes | Short bash blocks; localhost privacy callout; link out for depth |
| `docs/camera-sources.md` | Feature matrix + **honest limits** table + deferred list + security notes | Best template for export/ROS2 docs |
| `THIRD_PARTY_MODELS.md` | License table + cache policy + default selection rules | Keep AGPL/NC non-default language |
| Doc tests | `tests/test_third_party_models_doc.py` | Existence + keyword assertions |

**`docs/camera-sources.md` honesty matrix pattern:**

```markdown
| Topic | Honest expectation |
|-------|--------------------|
| Latency | Often **100–500 ms** class... |

### Deferred (not in Phase 2)
- Full production feature X
```

**Export recipes (EDGE-03) should copy that honesty style:**

```markdown
# docs/export/onnx-tensorrt.md  (or docs/edge-export.md)

## Desktop GPU path (primary)
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --profile desktop-gpu --source synthetic

## PyTorch → ONNX (recipe)
# ultralytics export commands; no CI hardware requirement

## TensorRT on Jetson (on-device only)
# Build engine on target JetPack; do not ship prebuilt multi-SKU engines

## Honest limits
| Target | Detector | Depth | Open-vocab | Notes |
| Jetson-class | YOLO n | DAV2 Small | off / on-demand | measure FPS |
| CPU/lite | YOLO n | Small | off | spatial lite; no Pi dual-model realtime claim |
```

**Scripts location (discretionary):** prefer `docs/export/` recipes first; if executable, `scripts/export/*.py` or `scripts/export/*.sh` that call Ultralytics export API. CI must not require Jetson.

**README Phase 7 section pattern** (mirror Phase 3–6 sections):
1. One-command desktop GPU path as **primary maker path** (EDGE-01).
2. Profile table + `--profile` examples.
3. Headless: `sentry serve --no-ui`.
4. Link export + ROS2 stub docs.
5. Safety/privacy: localhost default, no auth on LAN bind, perception-only / non-autonomy, not a safety interlock (already partially at free-space section lines 208–216).

**Safety / privacy finalized language anchors (already in tree):**
- README lines 29–35: localhost default; `0.0.0.0` opt-in no auth.
- README lines 208–216: consumers honor stale/TTL; not a safety interlock.
- README lines 212–216: perception-only denylist (API-05).
- `cli.py` serve host help + non-localhost warning (lines 268–273, 431–436).
- `docs/camera-sources.md` Security notes.

Phase 7 should **consolidate** these into a short dedicated README subsection (or `docs/safety-privacy.md`) rather than inventing new policy constants unless needed.

---

### 7. Closest analogs per Phase 7 deliverable

| Deliverable | Plan | Closest analog(s) | What to copy |
|-------------|------|-------------------|--------------|
| Profiles select tiers/backends at serve | 07-01 | `cli.py` `tier_to_weight(cfg.models.detector_tier)` + profile YAMLs + `load_config` | Extend same path for depth/OV/backend hints; assert in `test_config_profiles.py` |
| Edge model tier map | 07-01 | `models/cache.py` `tier_to_weight` + `KNOWN_WEIGHTS` | Add `tier_to_depth_*` or document depth_tier=small only; OV n vs s by profile |
| Headless serve | 07-01 | `create_app` + `routes_preview.root_preview` + serve typer Options | `enable_ui` / `--no-ui`; keep v1 + control APIs |
| Desktop GPU E2E docs | 07-01 / 07-02 | README optional detect/depth sections | Primary path: `--profile desktop-gpu` + both extras |
| ONNX/TRT export recipes | 07-02 | `docs/camera-sources.md` honesty + `THIRD_PARTY_MODELS.md` | Docs/scripts only; no Jetson CI; on-device engine build notes |
| Jetson packaging notes | 07-02 | profile `jetson.yaml` + probe_device Jetson branch | Document TensorRT preferred_backend; no prebuilt engines |
| Multi-cam `camera_id` tests | 07-03 | `test_schemas_frame.py`, `test_schemas_perception.py`, store loop tests | Distinct ids; no fusion |
| ROS2 bridge scaffold | 07-03 | `NullSink` + `docs/camera-sources.md` deferred section | Importable no-op + README; no rclpy dep |
| Voice plugin no-op | 07-03 | `NullSink` / `NoopWorker` + EP sinks group | Register `voice-noop`; health lists it |
| Safety/privacy release docs | 07-03 | README privacy + free-space safety wording + API-05 | Finalize non-autonomy positioning |

---

## Shared Patterns

### Profile → serve wiring

**Source:** `cli.py` lines 308–356 + `cache.tier_to_weight`  
**Apply to:** detector weights, optional OV weight selection, depth model_id if tiered, banner output

```
load_config(profile) → assert not allow_cloud → tier_to_weight(detector_tier) → worker ctor
```

### Soft optional extras

**Source:** serve detect/depth ImportError blocks  
**Apply to:** any edge-only import (TRT runtime if ever added) — degrade with stderr hint, do not hard-fail serve

### Localhost privacy (MODEL-03)

**Source:** serve `--host` default `127.0.0.1`; warning when non-loopback  
**Apply to:** all headless/docs examples — default bind remains localhost

### Perception-only / non-autonomy

**Source:** `schemas/perception.py` docstring; `test_api_perception_only.py`; README API-05  
**Apply to:** ROS2 stub messages, voice stubs, export docs — no `cmd_vel` / motor fields

### Plugin skip-if-present discovery

**Source:** `registry.discover` + `register_builtins`  
**Apply to:** voice-noop / ros2-stub registration in builtins + entry points

### Doc honesty tables

**Source:** `docs/camera-sources.md`  
**Apply to:** export recipes, Jetson notes, Pi FPS claims (never claim unmeasured dual-model realtime)

### Injectable workers / no weight download in CI

**Source:** `YoloDetectionWorker(model=...)`, FakeModel tests  
**Apply to:** export script unit tests if any; never require TensorRT in pytest

---

## No Analog Found

| File / concern | Role | Data Flow | Reason |
|----------------|------|-----------|--------|
| Real TensorRT/ONNX **runtime** backend | service | request-response | Only `NullBackend` + advisory `BackendName`; workers use torch/ultralytics/transformers |
| Ultralytics **export CLI scripts** in-repo | config | file-I/O | No `scripts/` tree yet; invent from Ultralytics docs + camera-sources honesty style |
| Headless `enable_ui` flag | config | request-response | Preview router always included today; pattern is self-extend of `create_app` |

Planner should use RESEARCH/CONTEXT for export command wording; still mirror docs honesty + serve/create_app extension style.

---

## Anti-Patterns (do not invent)

| Anti-pattern | Why | Correct pattern |
|--------------|-----|-----------------|
| New profile names without `RuntimeProfile` enum + YAML + tests | Breaks FOUND-06 contract | Extend enum + three YAML files + `test_runtime_profile_enum_exact_set` |
| Parallel config system (env-only tiers, hard-coded weights ignoring profile) | Undermines EDGE-02 | `load_config` → `cfg.models.*` → worker ctor |
| Full TensorRT engine runtime in v1 | Out of scope; CI cannot cover Jetson SKUs | Recipes + on-device build notes only |
| Ship prebuilt `.engine` for every JetPack | CONTEXT deferred | Document on-device build |
| Separate `sentry api` process without capture | Breaks perception loops | `--no-ui` on same `serve` lifecycle |
| `StaticFiles` mount of whole UI tree for headless toggle | UI is single FileResponse today | Gate `root_preview` / MJPEG or skip preview router routes |
| ROS2 package with `rclpy` core dependency | Heavy; not v1 | Stub module + docs; optional future extra |
| Real voice ASR/TTS | EDGE-04 is no-op only | `VoiceNoopSink` twin of `NullSink` |
| Multi-cam fusion / calibration | Deferred | Schema `camera_id` tests only |
| Claim Pi dual-model realtime without FPS data | Honesty requirement | Limits table + measured-or-unknown wording |
| `allow_cloud: true` default on any profile | MODEL-01 | Keep false; test all profiles |
| `yaml.load` (unsafe) | T-1-01 | `yaml.safe_load` only |
| React/Vite rewrite | Deferred | Static HTML remains; headless skips it |
| Mandatory LAN auth | Deferred | Document risk; localhost default |

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/config/`, `backend/`, `plugins/`, `api/app.py`, `api/routes_preview.py`, `cli.py`, `models/cache.py`, `models/depth/`, `schemas/`, `docs/`, `README.md`, `THIRD_PARTY_MODELS.md`, `pyproject.toml`, `tests/test_config_profiles.py`, `test_cli_serve.py`, `test_plugins_registry.py`, `test_api_*.py`, `test_schemas_*.py`, `test_third_party_models_doc.py`, `test_backend_protocols.py`, `test_model_cache.py`

**Files scanned:** ~30 source + 15 test analogs  
**Pattern extraction date:** 2026-08-08  

**Key analog files (primary copy sources):**
1. `src/sentry_ai/config/load.py` + `profiles/*.yaml` — profile load/merge  
2. `src/sentry_ai/cli.py` — typer options, exit codes, tier wiring, serve lifecycle  
3. `src/sentry_ai/api/app.py` + `routes_preview.py` — UI mount / headless gate  
4. `src/sentry_ai/plugins/registry.py` + `builtins.py` + `pyproject.toml` EPs — stubs  
5. `docs/camera-sources.md` + `tests/test_third_party_models_doc.py` — export/safety docs  

---

## PATTERN MAPPING COMPLETE

**Phase:** 7 - Edge Profiles & Extension Stubs  
**Files classified:** 18  
**Analogs found:** 16 / 18  

### Coverage
- Files with exact analog: 10  
- Files with role-match / self-extend analog: 6  
- Files with no close analog: 2 (TRT runtime; in-repo export scripts)

### Key Patterns Identified
- Profiles: YAML + Pydantic `extra=forbid` + `load_config` merge; serve already applies `detector_tier` via `tier_to_weight` — extend that path  
- CLI: Typer Options with privacy help; `typer.Exit(1)` user errors; soft ImportError for extras  
- Headless: gate Live Preview FileResponse/MJPEG via `create_app(enable_ui=...)` + `--no-ui`; keep `/v1` and control APIs  
- Plugins: Protocol + builtins + entry points + skip-if-present discover; voice/ROS2 as NullSink-class stubs  
- Tests: parametrized profile loads, inspect-source serve wiring, TestClient, schema camera_id, doc keyword asserts  
- Docs: honesty matrices + deferred lists (`camera-sources.md`); consolidate safety/privacy  

### File Created
`.planning/phases/07-edge-profiles-extension-stubs/07-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
