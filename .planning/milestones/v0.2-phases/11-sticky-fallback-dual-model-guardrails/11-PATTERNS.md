# Phase 11: Sticky Fallback & Dual-Model Guardrails - Pattern Map

**Mapped:** 2026-08-10  
**Files analyzed:** 18  
**Analogs found:** 18 / 18  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/models/detection/factory.py` | service (factory) | construct-time branch | same file — soft-fall ORT/TRT branches (lines 158–230) | exact |
| `src/sentry_ai/config/models.py` | model (config) | CRUD (config load) | same file `DeviceConfig` (lines 10–16) | exact |
| `src/sentry_ai/config/load.py` | config loader | transform (env→config) | same file `_parse_bool` + `SENTRY_ALLOW_CLOUD` (lines 21–29, 106–115) | exact |
| `src/sentry_ai/config/profile_runtime.py` | config / utility | transform | same file `ProfileRuntime` + `profile_runtime` (lines 28–109) | exact |
| `src/sentry_ai/cli.py` (`serve`) | controller (CLI) | request-response (construct) | same file factory + banner + ImportError gates (lines 470–646) | exact |
| `src/sentry_ai/capture/status.py` | model | request-response | same file optional backend_* fields (lines 74–77) | exact |
| `src/sentry_ai/api/app.py` | provider | request-response | same file `backend_*` kwargs → `app.state` (lines 37–84) | exact |
| `src/sentry_ai/api/deps.py` | provider | request-response | same file `AppState` backend_* (lines 29–32) | exact |
| `src/sentry_ai/api/routes_preview.py` | route | request-response | same file pass-through loop (lines 179–187) | exact |
| `src/sentry_ai/ui/static/index.html` | component (UI) | request-response (poll) | same file footer `req → live (reason)` (lines 449–465) | exact |
| `docs/configuration.md` | docs | N/A | same file preferred_backend + env table | exact |
| `docs/architecture.md` | docs | N/A | same file soft-fall ORT/TRT paragraphs | exact |
| `docs/export/yolo26-onnx-tensorrt.md` | docs | N/A | same file dual-model + “Phase 11 deferred” | exact |
| `docs/export/jetson-packaging.md` | docs | N/A | same file dual-model honesty + Phase 11 deferral | exact |
| `tests/test_detection_factory.py` | test | request-response | same file soft matrix + live success fixtures | exact |
| `tests/test_backend_honesty_status.py` | test | request-response | same file status pass-through triples | exact |
| `tests/test_export_docs.py` | test | N/A (keyword) | same file live ORT/TRT keyword style | exact |
| `tests/test_edge_rt04_torch_only.py` | test (NEW) | static / unit | `cli.py` serve depth/OV construction + `test_cli_serve` inspect pattern | role-match |

**Plans covered (expected):** 11-01 sticky resolve + soft/strict policy (BACK-03); 11-02 dual-model scope lock + operator surface (EDGE-RT-04).

**Unchanged / frozen (do not modify):** `DetectionLoop` scheduling / FrameBus / PerceptionStore / `/v1` routes / `artifact_paths.py` / live ORT-TRT loader mechanics (Phase 9–10). Optional residual load-failure sticky-pause is discretion only — prefer document residual if not hardening.

---

## Pattern Assignments

### `src/sentry_ai/models/detection/factory.py` (service, construct-time branch)

**Analog:** same file — soft-fall branches are the structural template; Phase 11 adds a soft/strict policy gate around them.  
**Plan:** 11-01 primary.

**Current soft-fall shape (TRT miss — copy structure for strict fork)** (lines 195–217):
```python
if requested == "tensorrt":
    path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
    if reject:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason=reject,
        )
    if path is None:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_artifact_missing",
        )
    if not _tensorrt_available():
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason="trt_dep_missing",
        )
```

**Recommended soft vs strict helper (new — extract miss returns):**
```python
def _miss(
    rt: ProfileRuntime,
    *,
    requested: str,
    reason: str,
    conf: float,
    model: Any | None,
    fallback_to_torch: bool,
) -> WorkerBuild:
    if fallback_to_torch:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested=requested,
            backend_live="torch",
            backend_reason=reason,
        )
    # Strict: never silent torch under preferred ORT/TRT
    return WorkerBuild(
        worker=None,
        backend_requested=requested,
        backend_live=None,  # or "none" — pick one vocabulary and test it
        backend_reason=reason,
    )
```

**WorkerBuild contract today** (lines 38–45) — may need `worker: Any | None` if strict returns `None`:
```python
@dataclass(frozen=True)
class WorkerBuild:
    """Detection worker plus honest preferred-vs-live backend identity."""

    worker: Any  # ModelWorker duck-type  # → Any | None for strict
    backend_requested: str
    backend_live: str  # → str | None if strict uses None
    backend_reason: str | None = None
```

**Honesty invariants (do not break):**
- Factory remains sole author of `backend_live` / `backend_reason`.
- Soft default: `fallback_to_torch=True` → current behavior unchanged.
- Strict miss: **never** `backend_live="torch"` under preferred ORT/TRT; never `backend_live` in `{onnxruntime, tensorrt}` without live worker.
- Stable reason codes unchanged: `path_rejected` | `ort_artifact_missing` | `ort_dep_missing` | `trt_artifact_missing` | `trt_dep_missing` | `unsupported_backend`.
- No module-level `import onnxruntime` / `import tensorrt` (keep `find_spec` only).
- Do **not** re-resolve inside DetectionLoop.

**Log-once pattern analog** — `src/sentry_ai/models/device.py` lines 81–88 (construct-time warning, not per-frame):
```python
logger.warning(
    "Requested CUDA device %r but CUDA is unavailable "
    "(torch.cuda.is_available() is False); falling back to %r. "
    "Use --profile cpu-fallback or a machine with CUDA for the "
    "requested device policy.",
    requested,
    fallback,
)
```

**DetectionLoop sticky log-once analog** (for messaging style only — do **not** put factory resolve in loop) — `loop.py` lines 99–107:
```python
def _handle_dependency_failure(self, message: str, frame: Any) -> None:
    """Log once, record error product, pause stage to stop per-frame spam."""
    if not self._dep_failed:
        self._dep_failed = True
        logger.error(
            "Detection disabled: missing dependency (%s). "
            "Install with: uv sync --extra detect",
            message,
        )
```

**Recommended factory/serve log (call when `backend_reason is not None`, once at construct):**
```python
import logging
logger = logging.getLogger(__name__)

# Soft:
logger.warning(
    "detection backend soft-fallback: requested=%s live=%s reason=%s",
    build.backend_requested,
    build.backend_live,
    build.backend_reason,
)
# Strict:
logger.error(
    "detection backend strict-fail: requested=%s live=%s reason=%s",
    build.backend_requested,
    build.backend_live,
    build.backend_reason,
)
```

**API surface recommendation:**
```python
def build_detection_worker(
    rt: ProfileRuntime,
    *,
    conf: float = 0.25,
    model: Any | None = None,
    fallback_to_torch: bool | None = None,  # None → read from rt / default True
) -> WorkerBuild:
    ...
```

Prefer reading policy from `rt.fallback_to_torch` (plumbed from config) so serve does not re-parse env.

---

### `src/sentry_ai/config/models.py` (model, config)

**Analog:** same file — additive field with `extra="forbid"`.  
**Plan:** 11-01.

**DeviceConfig today** (lines 10–16):
```python
class DeviceConfig(BaseModel):
    """Device / backend preference (advisory in Phase 1; not executed)."""

    model_config = ConfigDict(extra="forbid")

    preferred_backend: BackendName | str = BackendName.CPU
    device_id: str = "cpu"
```

**Extension pattern (Phase 8 PATTERNS already foreshadowed):**
```python
class DeviceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_backend: BackendName | str = BackendName.CPU
    device_id: str = "cpu"
    # Phase 11 BACK-03: soft (True, default) vs strict (False)
    fallback_to_torch: bool = True
```

**Rules:**
- Default `True` globally (including jetson) — soft remains maker default.
- Do **not** flip jetson YAML to `false` without explicit product lock.
- `extra="forbid"` means YAML must not invent undeclared keys; new field must be declared here first.

---

### `src/sentry_ai/config/load.py` (config loader, env override)

**Analog:** same file — `SENTRY_ALLOW_CLOUD` bool env parse.  
**Plan:** 11-01.

**Bool parse** (lines 21–29):
```python
def _parse_bool(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off", ""}:
        return False
    raise ValueError(f"invalid boolean env value: {value!r}")
```

**Env always-wins pattern** (lines 106–115) — copy for fallback:
```python
allow_cloud = _parse_bool(os.environ.get("SENTRY_ALLOW_CLOUD"), default=False)
models = data.setdefault("models", {})
if not isinstance(models, dict):
    raise ValueError("models config must be a mapping")
if "SENTRY_ALLOW_CLOUD" in os.environ:
    models["allow_cloud"] = allow_cloud
else:
    models.setdefault("allow_cloud", False)
```

**Recommended Phase 11 mirror:**
```python
# Env: SENTRY_FALLBACK_TO_TORCH=true|false  (default True when unset)
device = data.setdefault("device", {})
if not isinstance(device, dict):
    raise ValueError("device config must be a mapping")
if "SENTRY_FALLBACK_TO_TORCH" in os.environ:
    device["fallback_to_torch"] = _parse_bool(
        os.environ.get("SENTRY_FALLBACK_TO_TORCH"),
        default=True,
    )
else:
    device.setdefault("fallback_to_torch", True)
```

Document in `load_config` docstring env list next to `SENTRY_ALLOW_CLOUD`.

---

### `src/sentry_ai/config/profile_runtime.py` (config, transform)

**Analog:** same file — extend frozen dataclass + pure `profile_runtime`.  
**Plan:** 11-01.

**ProfileRuntime today** (lines 28–39):
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
```

**Composition site** (lines 86–109) — plumb new field:
```python
def profile_runtime(cfg: SentryConfig) -> ProfileRuntime:
    ...
    preferred = cfg.device.preferred_backend
    preferred_str = (
        preferred.value if isinstance(preferred, BackendName) else str(preferred)
    )
    device_id = cfg.device.device_id or "cpu"
    device = device_for_backend(preferred, device_id)
    fallback_to_torch = bool(getattr(cfg.device, "fallback_to_torch", True))

    return ProfileRuntime(
        ...
        preferred_backend=preferred_str,
        device=device,
        device_id=device_id,
        fallback_to_torch=fallback_to_torch,
    )
```

**Rules:** pure helpers only — no FastAPI, no torch, no weight download. Factory reads `rt.fallback_to_torch`.

**Test impact:** any hand-built `ProfileRuntime(...)` in tests must add the new field (see `test_detection_factory.py` lines 268–277, 285–294).

---

### `src/sentry_ai/cli.py` serve (controller, construct-time)

**Analog:** same file — one-shot factory + banner + optional-extra ImportError gates.  
**Plan:** 11-01 (strict wiring) + 11-02 (EDGE-RT-04 construction already correct — keep).

**Sticky factory call (already one-shot — keep)** (lines 505–511):
```python
# Factory selects loader branch from preferred_backend (EDGE-RT-02).
build = build_detection_worker(rt, conf=0.25)
worker = build.worker
backend_requested = build.backend_requested
backend_live = build.backend_live
backend_reason = build.backend_reason
det_loop = DetectionLoop(bus, worker, store)
```

**Strict fail-closed wiring (new — prefer Exit(1) per RESEARCH A2 discretion):**
```python
build = build_detection_worker(rt, conf=0.25)
worker = build.worker
backend_requested = build.backend_requested
backend_live = build.backend_live
backend_reason = build.backend_reason

if backend_reason is not None:
    # structured log once (or rely on factory log)
    ...

if worker is None:
    # Strict miss: do not start DetectionLoop; loud banner
    det_loop = None
    typer.echo(
        f"detection disabled (strict): requested={backend_requested} "
        f"reason={backend_reason}",
        err=True,
    )
    # RESEARCH preferred for automation clarity:
    raise typer.Exit(code=1)
else:
    det_loop = DetectionLoop(bus, worker, store)
```

**ImportError gate pattern to mirror for “detection off, process may continue”** (lines 519–531) — only if product chooses continue-with-detection-off instead of Exit(1):
```python
except ImportError as exc:
    typer.echo(
        "detection disabled: detect extra not installed "
        f"({exc}). Install with: uv sync --extra detect",
        err=True,
    )
    worker = None
    det_loop = None
    ...
```

**Banner honesty** (lines 611–617) — extend optionally with mode:
```python
if backend_requested is not None:
    typer.echo(f"backend_requested: {backend_requested}")
if backend_live is not None:
    typer.echo(f"backend_live: {backend_live}")
if backend_reason is not None:
    typer.echo(f"backend_reason: {backend_reason}", err=True)
# Optional Phase 11:
# typer.echo(f"fallback_to_torch: {rt.fallback_to_torch}")
```

**EDGE-RT-04 construction (already correct — do not route through factory)** (lines 512–562):
```python
ov_worker = YoloeOpenVocabWorker(
    weights=rt.open_vocab_weights,  # .pt YOLOE path
    conf=0.25,
    device=rt.device,
)
ov_loop = OpenVocabLoop(bus, ov_worker, store)  # mode=off default
...
depth_worker = DepthAnythingWorker(
    depth_mode="relative",
    model_id=rt.depth_model_id,
    device=rt.device,
)
depth_loop = DepthLoop(bus, depth_worker, store)
```

**create_app pass-through** (lines 580–597) — if `fallback_mode` / `fallback_to_torch` status field ships, inject here same as `backend_*`.

**Lifecycle freeze** (lines 643–646): start det only when `det_loop is not None`; never call `build_detection_worker` again after start.

---

### `src/sentry_ai/capture/status.py` (model, optional fields)

**Analog:** same file — nullable backend honesty fields.  
**Plan:** 11-01 optional `fallback_mode` / `fallback_to_torch`.

**Existing honesty fields** (lines 74–77):
```python
# Optional backend honesty (Phase 8 BACK-02); factory-authored only.
backend_requested: str | None = None
backend_live: str | None = None
backend_reason: str | None = None
```

**Extension pattern:**
```python
# Phase 11 BACK-03: soft vs strict policy surface (pass-through only).
fallback_to_torch: bool | None = None
# OR string mode: fallback_mode: Literal["soft", "strict"] | None = None
```

Prefer one field; keep `extra="forbid"` + default `None` for backward compatibility.

---

### `src/sentry_ai/api/app.py` + `deps.py` (provider)

**Analog:** same files — optional kwargs → `app.state` + `AppState`.  
**Plan:** 11-01 if status field ships.

**create_app kwargs today** (lines 37–39, 81–84):
```python
backend_requested: str | None = None,
backend_live: str | None = None,
backend_reason: str | None = None,
...
app.state.backend_requested = backend_requested
app.state.backend_live = backend_live
app.state.backend_reason = backend_reason
```

**AppState** (`deps.py` lines 29–32):
```python
backend_requested: str | None = None
backend_live: str | None = None
backend_reason: str | None = None
```

**Rule:** mirror any new field in **all four places**: `create_app` signature, `app.state.*`, `AppState`, `routes_preview` pass-through. Never recompute live from `preferred_backend`.

---

### `src/sentry_ai/api/routes_preview.py` (route, pass-through)

**Analog:** same file — backend honesty loop.  
**Plan:** 11-01 if new field.

**Pass-through only** (lines 179–187):
```python
# Phase 8 BACK-02: factory-authored backend honesty (pass-through only).
# Never recompute live from preferred_backend; never invent ORT/TRT live.
try:
    for field in ("backend_requested", "backend_live", "backend_reason"):
        value = getattr(request.app.state, field, None)
        if value is not None:
            data[field] = value
except Exception:  # noqa: BLE001 — status best-effort
    pass
```

**Extension:** add `"fallback_to_torch"` (or `"fallback_mode"`) to the field tuple. For bool `False`, note: current `if value is not None` works; do **not** use truthiness checks that drop `False`.

---

### `src/sentry_ai/ui/static/index.html` (component, poll display)

**Analog:** same file footer honesty.  
**Plan:** 11-01 optional; 11-02 keep triple.

**Footer pattern** (lines 449–465):
```javascript
// Phase 8 BACK-02: backend requested → live (factory-authored only).
if (elBackend) {
  var req = data && data.backend_requested ? String(data.backend_requested) : null;
  var live = data && data.backend_live ? String(data.backend_live) : null;
  if (req || live) {
    var pair = (req || "—") + " → " + (live || "—");
    var reason = data && data.backend_reason ? String(data.backend_reason) : null;
    if (reason && req && live && req !== live) {
      elBackend.textContent = pair + " (" + reason + ")";
      elBackend.title = reason;
    } else {
      elBackend.textContent = pair;
      elBackend.removeAttribute("title");
    }
  } else {
    elBackend.textContent = "—";
    elBackend.removeAttribute("title");
  }
}
```

**Strict UI note:** if `backend_live` is `null`/`None`, current JS shows `req → —` when only `req` is set — good enough. If reason should show when live is null, relax the `req && live && req !== live` guard to show reason whenever present and not live-equal-requested.

Optional: append soft/strict mode if status field ships.

---

### Docs honesty surfaces

**Analogs:**  
- `docs/configuration.md` (preferred_backend soft-fall + env table)  
- `docs/architecture.md` (ORT/TRT soft-fall paragraphs)  
- `docs/export/yolo26-onnx-tensorrt.md` (dual-model + “Phase 11 deferred”)  
- `docs/export/jetson-packaging.md` (dual-model honesty + Phase 11 deferral)

**Phase 11 deferred language to retire** (verified in tree):

| File | Current deferral language |
|------|---------------------------|
| `yolo26-onnx-tensorrt.md` | “Phase 11 owns first-class dual-model guardrails”; sticky thrash-free deferred to Phase 11 |
| `jetson-packaging.md` | “First-class dual-model scheduling guardrails are Phase 11”; sticky thrash-free (Phase 11) |

**Replace with shipped language (keyword-test friendly):**

| Topic | Required honesty |
|-------|------------------|
| Sticky resolve | Factory called **once** at serve construct; no per-frame re-probe of preferred backend |
| Soft default | `fallback_to_torch=true` (default): miss → torch worker + reason; serve continues |
| Strict opt-in | `fallback_to_torch=false` / `SENTRY_FALLBACK_TO_TORCH=false`: miss → fail-closed (no silent torch live claim) |
| Reason once | Banner + structured log at construct; status sticky fields |
| EDGE-RT-04 | Depth = torch/HF DAV2; OV = YOLOE `.pt`; neither uses detection factory ORT/TRT |
| Supported dual-model claim | TRT (or torch) fixed-class YOLO **+** torch DAV2 Small may share GPU — **measure on device** |
| Non-claim | Continuous open-vocab + TRT YOLO + DAV2 is **not** first-class this milestone |
| Knobs | disable depth; OV off/on_demand; nano tier; `--no-ui`; `nvidia-smi` |
| No FPS fiction | No published dual-model FPS tables without measurement protocol |

**configuration.md env table extension** (after lines 56–60 pattern):
```markdown
| `SENTRY_FALLBACK_TO_TORCH` | Soft (`true`, default) vs strict (`false`) when preferred ORT/TRT cannot go live |
| `SENTRY_DETECTOR_ONNX` | Explicit allowlisted `.onnx` path (live ORT) |
| `SENTRY_DETECTOR_ENGINE` | Explicit allowlisted `.engine` path (live TRT) |
```

---

### `tests/test_detection_factory.py` (test matrix extension)

**Analog:** same file — soft matrix + monkeypatch live fixtures.  
**Plan:** 11-01.

**Soft-fall baseline (keep green)** (lines 41–60):
```python
def test_jetson_tensorrt_soft_stub() -> None:
    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_artifact_missing"
```

**Monkeypatch live success** (lines 102–117) — reuse for strict-success (strict only changes miss path):
```python
monkeypatch.setattr(
    factory_mod,
    "_try_resolve_artifact",
    lambda rt, *, preferred: (engine_path, None),
)
monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: True)
```

**New strict matrix (copy soft structure, invert live claim):**

| Case | Setup | Expect |
|------|--------|--------|
| jetson soft default | no fixture | `live=torch`, worker is `YoloDetectionWorker`, reason `trt_artifact_missing` |
| jetson strict miss | `fallback_to_torch=False`, no artifact | `worker is None`, `live is None` (or `"none"`), reason set, **not** torch silent |
| ORT strict dep miss | path ok + dep False + strict | same fail-closed shape, reason `ort_dep_missing` |
| TRT strict path_rejected | reject + strict | reason `path_rejected`, no torch live claim |
| strict live success | artifact + dep + strict | still live TRT/ORT (policy only affects miss) |
| soft log once | caplog + reason set | one warning with reason code |
| sticky contract | inspect loop source / import graph | `build_detection_worker` **not** referenced in `loop.py` |
| module hygiene | existing | still no top-level ort/trt import |

**Hand-built ProfileRuntime** (lines 268–277) — add `fallback_to_torch=True` when field is required on dataclass.

**Log-once test shape (no existing caplog analog in suite — introduce):**
```python
def test_soft_fallback_logs_reason_once(caplog: pytest.LogCaptureFixture) -> None:
    import logging
    rt = _rt_for_profile("jetson")
    with caplog.at_level(logging.WARNING, logger="sentry_ai.models.detection.factory"):
        build = build_detection_worker(rt, model=FakeModel())
        # second call is ok for unit test of factory; sticky is process-level in serve
        _ = build_detection_worker(rt, model=FakeModel())
    assert build.backend_reason == "trt_artifact_missing"
    # Prefer: factory logs once per call is fine; serve must not re-call factory per frame
    assert any("soft-fallback" in r.message or "trt_artifact_missing" in r.message
               for r in caplog.records)
```

**Sticky contract test (static):**
```python
def test_detection_loop_does_not_call_factory() -> None:
    from sentry_ai.models.detection import loop as loop_mod
    source = inspect.getsource(loop_mod)
    assert "build_detection_worker" not in source
    assert "preferred_backend" not in source  # optional stronger guard
```

---

### `tests/test_backend_honesty_status.py` (status pass-through)

**Analog:** same file — TestClient triples.  
**Plan:** 11-01.

**Soft-stub fixture** (lines 76–100) — keep structure; optional mode field:
```python
loop, app = _running_app(
    backend_requested="tensorrt",
    backend_live="torch",
    backend_reason="trt_artifact_missing",
    # fallback_to_torch=True,  # if field ships
)
```

**Retired reason cleanup** (line 112 still uses legacy code):
```python
# BEFORE (retire if this file is touched)
backend_reason="ort_loader_not_implemented"
# AFTER
backend_reason="ort_artifact_missing"  # or ort_dep_missing
```

**Strict status triple (new):**
```python
def test_api_status_honesty_strict_unavailable() -> None:
    loop, app = _running_app(
        backend_requested="tensorrt",
        backend_live=None,  # or omit / "none"
        backend_reason="trt_artifact_missing",
        fallback_to_torch=False,
    )
    with TestClient(app) as client:
        data = client.get("/api/status").json()
        assert data["backend_requested"] == "tensorrt"
        assert data.get("backend_live") in (None, "none")
        assert data["backend_reason"] == "trt_artifact_missing"
        assert data.get("backend_live") not in ("tensorrt", "onnxruntime", "torch")
```

**Pass-through invariant:** status never invents live ORT/TRT; never recomputes from profile.

---

### `tests/test_export_docs.py` (keyword tests)

**Analog:** same file live ORT/TRT keyword style (lines 44–97).  
**Plan:** 11-01 docs + 11-02 dual-model.

**Read helper** (lines 19–26) — keep.

**New tests to add (mirror structure):**
```python
def test_docs_soft_vs_strict_and_sticky() -> None:
    blob = (
        _read("yolo26-onnx-tensorrt.md")
        + "\n"
        + _read("jetson-packaging.md")
        + "\n"
        + (REPO_ROOT / "docs" / "configuration.md").read_text(encoding="utf-8")
    ).lower()
    assert "sticky" in blob or "once" in blob or "one-shot" in blob or "serve construct" in blob
    assert "soft" in blob and ("strict" in blob or "fallback_to_torch" in blob)
    assert "fallback" in blob

def test_docs_dual_model_guardrails_edge_rt04() -> None:
    blob = (
        _read("yolo26-onnx-tensorrt.md") + "\n" + _read("jetson-packaging.md")
    ).lower()
    # Supported claim language
    assert "measure" in blob and ("device" in blob or "on-device" in blob or "on device" in blob)
    # Non-claim: continuous OV + TRT + DAV2 not first-class
    assert (
        "not" in blob
        and ("continuous" in blob or "open-vocab" in blob or "open vocab" in blob)
    )
    # No "Phase 11 deferred" after ship
    raw = _read("yolo26-onnx-tensorrt.md") + _read("jetson-packaging.md")
    assert "Phase 11 owns" not in raw
    assert "deferred to Phase 11" not in raw.lower() or "phase 11" not in raw.lower()
    # Careful: allow historical roadmap mentions if needed; prefer zero "Phase 11 deferred"
```

Keep existing live ORT/TRT + on-device / no-pip-tensorrt asserts.

---

### `tests/test_edge_rt04_torch_only.py` (NEW)

**Analogs:**  
- Serve construction: `cli.py` lines 512–562 (depth/OV separate constructors)  
- Inspect wiring: `tests/test_cli_serve.py` lines 313–345  
- Workers: `DepthAnythingWorker`, `YoloeOpenVocabWorker` (torch/HF / YOLOE `.pt` only)

**Recommended module shape:**
```python
"""EDGE-RT-04: depth and open-vocab stay torch paths; no factory ORT/TRT."""

import inspect
from sentry_ai import cli as cli_mod
from sentry_ai.models.depth import worker as depth_worker_mod
from sentry_ai.models.detection import yoloe_worker as yoloe_mod
from sentry_ai.models.detection import factory as factory_mod

def test_serve_depth_and_ov_not_via_detection_factory() -> None:
    source = inspect.getsource(cli_mod.serve)
    assert "DepthAnythingWorker" in source
    assert "YoloeOpenVocabWorker" in source
    assert "build_detection_worker" in source
    # Factory used once for fixed-class only — depth/OV constructed separately
    assert source.index("build_detection_worker") < source.index("DepthAnythingWorker")
    # No preferred_backend branch into depth
    depth_section_hint = "DepthAnythingWorker"
    assert "preferred_backend" not in source.split(depth_section_hint)[1][:400]

def test_depth_worker_source_has_no_ort_trt_live_claim() -> None:
    source = inspect.getsource(depth_worker_mod)
    assert "onnxruntime" not in source
    assert "tensorrt" not in source.lower() or "tensorrt" not in source  # no TRT path
    assert "build_detection_worker" not in source

def test_yoloe_worker_uses_pt_weights_default() -> None:
    assert yoloe_mod.DEFAULT_WEIGHTS.endswith(".pt")
    source = inspect.getsource(yoloe_mod.YoloeOpenVocabWorker)
    assert "YOLOE" in source
    assert "build_detection_worker" not in inspect.getsource(yoloe_mod)

def test_factory_is_fixed_class_only_doc_or_export() -> None:
    # Optional: factory module docstring still says fixed-class
    doc = factory_mod.__doc__ or ""
    assert "fixed-class" in doc.lower() or "detection" in doc.lower()
```

---

### `tests/test_cli_serve.py` (wiring inspect — extend if strict ships)

**Analog:** same file BACK-02 wiring tests (lines 313–349):
```python
assert "build_detection_worker" in source
assert "backend_requested" in source
assert "backend_live" in source
assert "backend_reason" in source
...
assert "backend_requested=backend_requested" in source
```

**Phase 11 extensions:**
```python
# Sticky: single factory call site in serve body
assert source.count("build_detection_worker(") == 1
# Strict path surfaces (if Exit(1) chosen)
# assert "typer.Exit" in source and ("strict" in source.lower() or "fallback" in source.lower())
# Depth/OV still separate
assert "DepthAnythingWorker" in source
assert "YoloeOpenVocabWorker" in source
```

---

## Shared Patterns

### Sticky one-shot resolve (BACK-03 core)
**Source:** `cli.py` lines 505–511 + `yolo_worker._ensure_model` once-per-worker  
**Apply to:** factory + serve only  
- Call `build_detection_worker` **once** during serve startup  
- Inject worker into `DetectionLoop`; never rebuild  
- Prove with inspect: factory not imported/called from `loop.py`  
- Do **not** invent a TTL/retry BackendResolver class

### Soft vs strict policy
**Source:** RESEARCH Pattern 1–2 + factory soft-fall branches  
**Apply to:** factory miss paths only  

| Mode | Config | Miss behavior |
|------|--------|---------------|
| Soft (default) | `fallback_to_torch=True` | torch worker + `backend_live=torch` + reason |
| Strict (opt-in) | `fallback_to_torch=False` | `worker=None`, no torch shadow, reason set, fail-closed serve |

Default soft **globally** (including jetson). Env: `SENTRY_FALLBACK_TO_TORCH` via `_parse_bool` mirror of `SENTRY_ALLOW_CLOUD`.

### Factory sole author of backend identity
**Source:** Phase 8–10 + `factory.py` WorkerBuild  
**Apply to:** factory write; status/banner/UI pass-through only  
- Soft: `backend_live="torch"` + stable reason  
- Live: `backend_live` in `{onnxruntime,tensorrt}` only on real live branch  
- Strict miss: never claim torch/ORT/TRT live under preferred miss  

### Reason logged once
**Source:** `device.resolve_device` warning + DetectionLoop dep sticky log  
**Apply to:** factory or serve immediately after factory when `backend_reason is not None`  
- Soft → `logger.warning`  
- Strict → `logger.error`  
- Never log inside DetectionLoop per frame for policy  

### Status / UI pass-through
**Source:** `routes_preview.py` 179–187 + `index.html` 449–465 + Phase 8  
**Apply to:** any new `fallback_*` field  
- Optional fields default None  
- Best-effort; never raise  
- Never recompute live from profile  

### EDGE-RT-04 torch scope lock
**Source:** `cli.py` depth/OV construction + depth/yoloe workers  
**Apply to:** serve construction + docs + new tests  
- Depth: `DepthAnythingWorker` (transformers + torch)  
- OV: `YoloeOpenVocabWorker(weights=rt.open_vocab_weights)` `.pt` YOLOE; mode off default  
- Never `build_detection_worker` for depth/OV  
- Dual-model: measure-on-device; no continuous OV+TRT+DAV2 first-class claim; no FPS fiction  

### Config plumbing chain
**Source:** Phase 8 profile/status patterns  
**Apply to:** `fallback_to_torch` end-to-end  
```text
DeviceConfig.fallback_to_torch
  → load.py env SENTRY_FALLBACK_TO_TORCH
  → ProfileRuntime.fallback_to_torch
  → build_detection_worker(...)
  → (optional) create_app / StatusSnapshot / banner / UI
```

### Spine freeze
**Source:** RESEARCH + EDGE-RT-01  
**Apply to:** all plans  
- Do **not** modify DetectionLoop scheduling, FrameBus, PerceptionStore, `/v1`  
- Optional residual: sticky-pause on first non-dep YOLO load failure (Pitfall 3) — document if skipped  

### Test styles

| Style | Analog | Use for |
|-------|--------|---------|
| Soft/strict factory matrix | `test_detection_factory.py` | BACK-03 policy |
| caplog once | new (mirror `device.py` log) | reason logged once |
| inspect.getsource | `test_cli_serve.py` | sticky single call; depth/OV separate |
| TestClient status | `test_backend_honesty_status.py` | pass-through + mode field |
| Doc keywords | `test_export_docs.py` | soft/strict/sticky/dual-model |
| Static EDGE-RT-04 | new `test_edge_rt04_torch_only.py` | depth/OV torch-only |

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| _(none for structure)_ | — | — | Soft/strict is a policy fork on existing soft-fall; all surfaces have Phase 8–10 analogs |

**Partial / invent-with-care only:**

| Concern | Guidance |
|---------|----------|
| `backend_live` vocabulary on strict miss | Prefer `None` (optional StatusSnapshot) over inventing `"unavailable"` that looks like a backend name; if string needed use `"none"` and test UI |
| Serve Exit(1) vs detection-off continue | RESEARCH prefers Exit(1) for automation; ImportError gate is the continue analog |
| caplog tests | No existing suite pattern — introduce with stdlib `caplog` |
| `fallback_mode` status field | Optional; copy backend_* pass-through chain if shipped |
| Residual live-load thrash | Optional hardening mirroring `_handle_dependency_failure`; else docs-only |

---

## Plan → Analog Quick Index

### 11-01 — Sticky resolve + soft/strict fallback policy (BACK-03)

| Work item | Copy from |
|-----------|-----------|
| Soft miss (keep) | `factory.py` ORT/TRT soft-fall branches 158–217 |
| Strict miss fork | New `_miss(...)` helper; soft branch as true path |
| Config field | `DeviceConfig` additive bool like Phase 8 foreshadow |
| Env override | `load.py` `_parse_bool` + `SENTRY_ALLOW_CLOUD` always-wins |
| Profile plumb | `profile_runtime.py` ProfileRuntime field + composition |
| Serve wiring | `cli.py` 505–531; Exit(1) or ImportError-style disable |
| Log once | `device.py` 81–88 style; optional DetectionLoop message tone |
| Status field (opt) | `status.py` / `app.py` / `deps.py` / `routes_preview` backend_* chain |
| Factory tests | `test_detection_factory.py` soft matrix + invert for strict |
| Sticky test | inspect `loop.py` has no factory call |
| Status tests | `test_backend_honesty_status.py`; retire `ort_loader_not_implemented` |
| Docs | configuration + architecture soft/strict table; sticky guarantee |
| Keyword tests | `test_export_docs.py` soft/strict/sticky |

### 11-02 — Dual-model scope lock + operator surface (EDGE-RT-04)

| Work item | Copy from |
|-----------|-----------|
| Depth construction lock | `cli.py` 533–562 `DepthAnythingWorker` |
| OV construction lock | `cli.py` 512–518 `YoloeOpenVocabWorker` + mode off |
| Worker torch-only proof | `depth/worker.py`, `yoloe_worker.py` source inspect |
| New test module | `tests/test_edge_rt04_torch_only.py` ← inspect patterns from `test_cli_serve.py` |
| Dual-model docs | `jetson-packaging.md` + `yolo26-onnx-tensorrt.md` — retire Phase 11 deferred |
| Operator status | Keep requested/live/reason footer; optional mode |
| Keyword tests | measure-on-device; continuous OV non-claim; no FPS fiction |
| No VRAM CI | docs knobs only |

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/models/detection/factory.py`, `loop.py`, `yoloe_worker.py`, `src/sentry_ai/models/depth/worker.py`, `src/sentry_ai/models/device.py`, `src/sentry_ai/config/{models,load,profile_runtime}.py`, `src/sentry_ai/cli.py`, `src/sentry_ai/capture/status.py`, `src/sentry_ai/api/{app,deps,routes_preview}.py`, `src/sentry_ai/ui/static/index.html`, `docs/{configuration,architecture}.md`, `docs/export/{yolo26-onnx-tensorrt,jetson-packaging}.md`, `tests/test_{detection_factory,backend_honesty_status,export_docs,cli_serve}.py`, `.planning/phases/{08,10}-*/{08,10}-PATTERNS.md`, `.planning/phases/11-sticky-fallback-dual-model-guardrails/11-RESEARCH.md`

**Files scanned:** ~30  
**Pattern extraction date:** 2026-08-10  
**Primary analogs for 11-01 / 11-02:** factory soft-fall branches + `SENTRY_ALLOW_CLOUD` env parse + serve one-shot factory wiring + status pass-through chain + DetectionLoop/device log-once messaging + depth/OV separate constructors.
