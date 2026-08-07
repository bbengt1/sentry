# Phase 4: Monocular Depth - Pattern Map

**Mapped:** 2026-08-07  
**Files analyzed:** 17 (new + modified)  
**Analogs found:** 16 / 17

Phase 4 is a **structural twin of Phase 3 detection**. Prefer rename-and-adapt over inventing new lifecycle, store, or HTTP patterns. Schemas (`DepthKind`, `DepthPayload`, validators) already ship — wire honesty, do not redesign contracts.

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/models/depth/loop.py` | service (daemon loop) | event-driven / keep-latest | `src/sentry_ai/models/detection/loop.py` | **exact** |
| `src/sentry_ai/models/depth/worker.py` | service (ModelWorker) | transform (frame→product) | `src/sentry_ai/models/detection/yolo_worker.py` | **exact** |
| `src/sentry_ai/models/depth/mapping.py` | utility | transform | `src/sentry_ai/models/detection/mapping.py` | role-match |
| `src/sentry_ai/models/depth/preprocess.py` | utility | transform | `src/sentry_ai/models/detection/mapping.py` (pure helpers) | role-match |
| `src/sentry_ai/models/depth/colormap.py` | utility | transform (array→BGR) | `src/sentry_ai/models/detection/overlay.py` | **exact** |
| `src/sentry_ai/models/depth/__init__.py` | config (package) | — | `src/sentry_ai/models/detection/__init__.py` | **exact** |
| `src/sentry_ai/state/perception_store.py` | store (extend) | keep-latest / CRUD | same file (DetectionProduct half) | **exact** |
| `src/sentry_ai/models/cache.py` | utility (extend) | file-I/O / config | same file (`configure_model_cache`) | role-match |
| `src/sentry_ai/api/deps.py` | config (DI) | request-response | same file (`detection_worker`) | **exact** |
| `src/sentry_ai/api/app.py` | config (factory) | request-response | same file (`create_app`) | **exact** |
| `src/sentry_ai/api/routes_detection.py` | controller (extend snapshot) | request-response | same file (`api_snapshot`) | **exact** |
| `src/sentry_ai/api/routes_preview.py` | controller (extend status/MJPEG) | streaming + request-response | same file (`api_status`, `_mjpeg_generator`) | **exact** |
| `src/sentry_ai/api/routes_depth.py` | controller (optional) | request-response | `src/sentry_ai/api/routes_detection.py` (config routes) | role-match |
| `src/sentry_ai/cli.py` | config / lifecycle | event-driven | same file (`serve` detection block) | **exact** |
| `src/sentry_ai/ui/static/index.html` | component (extend) | request-response poll | same file (det metrics footer) | **exact** |
| `pyproject.toml` | config | — | `[project.optional-dependencies] detect` | **exact** |
| `tests/test_depth_*.py` (+ extends) | test | — | `tests/test_detection_*.py`, `test_api_*`, `test_perception_store.py` | **exact** |

Schemas already present (do not reinvent):  
`schemas/enums.py` (`DepthKind`), `schemas/perception.py` (`DepthPayload`, `Completeness.depth`), `schemas/validators.py`, `policy/models.py` (`DEFAULT_DEPTH_WEIGHT_KEY`).

---

## Pattern Assignments

### `src/sentry_ai/models/depth/loop.py` (service, keep-latest)

**Analog:** `src/sentry_ai/models/detection/loop.py` — **structural twin; rename fields only**

**Imports / structure** (lines 1–19):
```python
"""DepthLoop: daemon thread reads FrameBus, writes PerceptionStore.

Structural twin of DetectionLoop — never opens cameras or owns capture I/O.
Keep-latest: skip when frame_id matches last processed; short Event.wait sleep.
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.state.perception_store import PerceptionStore
```

**Lifecycle pattern** (lines 47–69) — copy `start`/`stop`/`_lock`/`_stop`/`daemon` Thread:
```python
def start(self) -> None:
    with self._lock:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="depth",  # only change: "detection" → "depth"
            daemon=True,
        )
        self._thread.start()
```

**Core keep-latest + error-alive pattern** (lines 71–118) — map to `set_depth`:
```python
def _run(self) -> None:
    while not self._stop.is_set():
        frame = self._bus.get_latest()
        if frame is None or frame.frame_id == self._last_frame_id:
            self._stop.wait(0.005)
            continue
        if self._last_frame_id is not None:
            gap = frame.frame_id - self._last_frame_id - 1
            if gap > 0:
                self._store.record_depth_drop(gap)  # mirror record_drop
        t0 = time.perf_counter()
        model_name = str(getattr(self._worker, "name", "unknown"))
        try:
            result = self._worker.process(frame)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._last_frame_id = frame.frame_id
            self._store.set_depth(
                frame_id=frame.frame_id,
                camera_id=frame.camera_id,
                t_capture=frame.meta.t_capture,
                depth_map=result.depth_map,
                kind=result.kind,
                unit=result.unit,
                latency_ms=latency_ms,
                model_name=model_name,
                error=None,
            )
        except Exception as exc:  # noqa: BLE001 — keep thread alive
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._last_frame_id = frame.frame_id
            logger.exception("Depth worker failed frame_id=%s: %s", frame.frame_id, exc)
            self._store.set_depth(
                frame_id=frame.frame_id,
                camera_id=frame.camera_id,
                t_capture=frame.meta.t_capture,
                depth_map=None,
                kind=...,  # worker default kind or relative
                unit=None,
                latency_ms=latency_ms,
                model_name=model_name,
                error=str(exc),
            )
```

**Test analog:** `tests/test_detection_loop.py` — Fake worker, `_wait_until`, skip same `frame_id`, survive exception, `inspect.getsource` asserts no `VideoCapture`.

---

### `src/sentry_ai/models/depth/worker.py` (service, ModelWorker)

**Analog:** `src/sentry_ai/models/detection/yolo_worker.py`

**Injectable model + lazy load** (lines 49–62, 85–123) — critical CI pattern:
```python
class DepthAnythingWorker:
    name: str = "depth-anything-v2-small"

    def __init__(
        self,
        model_id: str = "depth-anything/Depth-Anything-V2-Small-hf",
        depth_mode: str = "relative",  # relative | metric_indoor | metric_outdoor
        device: str | None = None,
        model: Any | None = None,       # inject for tests — never HF download
        processor: Any | None = None,   # inject AutoImageProcessor stand-in
    ) -> None:
        self._model = model
        self._processor = processor
        self._load_lock = threading.Lock()
        ...

    def _ensure_model(self) -> tuple[Any, Any]:
        if self._model is not None and self._processor is not None:
            return self._model, self._processor
        with self._load_lock:
            if self._model is not None and self._processor is not None:
                return self._model, self._processor
            configure_model_cache()  # must set HF_HOME before from_pretrained
            try:
                from transformers import AutoImageProcessor, AutoModelForDepthEstimation
            except ImportError as exc:
                raise ImportError(
                    "transformers is required for DepthAnythingWorker. "
                    "Install the depth extra: uv sync --extra depth"
                ) from exc
            ...
```

**Device resolution** (lines 27–41) — reuse or thin-copy `resolve_device`:
```python
def resolve_device(device: str | None = None) -> str:
    """Pick inference device: explicit arg, else cuda > mps > cpu."""
    # Prefer shared util if extracted; copy-paste OK (RESEARCH A5).
```

**process contract** (lines 127–153) — consume `frame.image_bgr` only:
```python
def process(self, frame: ImageFrame | object) -> DepthResult:
    image_bgr = getattr(frame, "image_bgr", None)
    if image_bgr is None:
        logger.warning("DepthAnythingWorker.process: frame missing image_bgr")
        # return empty/error result — never open camera
    # 1) BGR→RGB  2) processor  3) model  4) interpolate HxW  5) kind/unit from mode
```

**Protocol:** `src/sentry_ai/plugins/protocols.py` lines 27–36 (`ModelWorker.name` + `process`).

**Test analog:** `tests/test_detection_worker.py` — `FakeModel` inject, protocol check, `inspect.getsource` no `VideoCapture`.

---

### `src/sentry_ai/models/depth/mapping.py` (utility, transform)

**Analog:** `src/sentry_ai/models/detection/mapping.py`

**Pure transform conventions** (lines 1–14, 55–60):
- No I/O, no heavy imports required for unit tests
- Empty/missing → safe empty product (not `None` for list paths)
- Completeness decided by store/loop, not mapper

**Depth-specific content** (from RESEARCH, not detection file):
```python
MODE_TO_MODEL = {
    "relative": "depth-anything/Depth-Anything-V2-Small-hf",
    "metric_indoor": "depth-anything/Depth-Anything-V2-Metric-Indoor-Small-hf",
    "metric_outdoor": "depth-anything/Depth-Anything-V2-Metric-Outdoor-Small-hf",
}

def kind_for_mode(mode: str) -> tuple[DepthKind, str | None]:
    if mode == "relative":
        return DepthKind.RELATIVE, None
    if mode in ("metric_indoor", "metric_outdoor"):
        return DepthKind.METRIC_ESTIMATED, "m"
    raise ValueError(f"unknown depth_mode: {mode}")
```

Kind/unit must come from **configured mode**, never float-range heuristics.

**Schema honesty already enforced:**
```1:11:src/sentry_ai/schemas/validators.py
def relative_depth_forbids_unit(kind: DepthKind, unit: str | None) -> None:
    if kind == DepthKind.RELATIVE and unit is not None:
        raise ValueError("relative depth must not set unit (meters forbidden)")
```

---

### `src/sentry_ai/models/depth/preprocess.py` (utility, transform)

**Analog role:** pure helpers like `mapping.py` / overlay — no worker I/O.

**Patterns to implement** (RESEARCH Code Examples):
```python
def bgr_to_rgb_uint8(image_bgr: np.ndarray) -> np.ndarray:
    assert image_bgr.ndim == 3 and image_bgr.shape[2] == 3
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)

def depth_stats(depth: np.ndarray) -> dict[str, float]:
    finite = depth[np.isfinite(depth)]
    return {
        "min": float(finite.min()) if finite.size else 0.0,
        "max": float(finite.max()) if finite.size else 0.0,
        "mean": float(finite.mean()) if finite.size else 0.0,
    }
```

**Test analog:** `tests/test_detection_mapping.py` style — pure unit tests, no torch.

---

### `src/sentry_ai/models/depth/colormap.py` (utility, array→BGR)

**Analog:** `src/sentry_ai/models/detection/overlay.py`

**Pure OpenCV helper conventions** (lines 1–51):
```python
"""Server-side depth colormap (DEPTH-03).

Pure OpenCV helper — no transformers, no camera I/O. Used by MJPEG encode
and unit-tested with synthetic arrays.
"""
from __future__ import annotations
import cv2
import numpy as np

__all__ = ["colorize_depth", "blend_depth"]

def draw_detections(...):  # analog structure
    out = image_bgr.copy()  # always copy; never mutate input
    ...
    return out
```

**Depth colormap body** (RESEARCH Pattern 6):
```python
def colorize_depth(depth_map: np.ndarray) -> np.ndarray:
    # COLORMAP_TURBO; min-max normalize finite values → uint8
    norm = cv2.normalize(depth_map, None, 0, 255, cv2.NORM_MINMAX)
    return cv2.applyColorMap(norm.astype(np.uint8), cv2.COLORMAP_TURBO)

def blend_depth(rgb_bgr: np.ndarray, depth_map: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    color = colorize_depth(depth_map)
    return cv2.addWeighted(rgb_bgr, 1.0 - alpha, color, alpha, 0)
```

**Rules:** Never draw unit text `"m"` when kind is relative. Empty/error → caller skips blend (don't crash stream).

**Test analog:** `tests/test_detection_overlay.py` — copy vs mutate, shape, synthetic arrays.

---

### `src/sentry_ai/models/depth/__init__.py` (package)

**Analog:** `src/sentry_ai/models/detection/__init__.py`

**Lazy `__getattr__`** (lines 16–26) — avoid heavy imports on package touch:
```python
def __getattr__(name: str) -> Any:
    if name == "DepthAnythingWorker":
        from sentry_ai.models.depth.worker import DepthAnythingWorker
        return DepthAnythingWorker
    if name == "DepthLoop":
        from sentry_ai.models.depth.loop import DepthLoop
        return DepthLoop
    raise AttributeError(...)
```

---

### `src/sentry_ai/state/perception_store.py` (store, extend)

**Analog:** same file — dual product, one lock, keep-latest

**Existing DetectionProduct / set / snapshot** (lines 22–123) — **do not break**. Add parallel:

```python
@dataclass
class DepthProduct:
    frame_id: int
    camera_id: str
    t_capture: float
    kind: DepthKind
    unit: Literal["m"] | None
    width: int
    height: int
    latency_ms: float
    depth_map: Any  # np.ndarray HxW float32 — in-process only
    min_value: float | None = None
    max_value: float | None = None
    mean_value: float | None = None
    model_name: str | None = None
    error: str | None = None
```

**Mirror methods:**
| Detection | Depth twin |
|-----------|------------|
| `_latest: DetectionProduct \| None` | `_latest_depth: DepthProduct \| None` |
| `set_detections(...)` | `set_depth(...)` |
| `snapshot()` | `snapshot_depth()` |
| `record_drop` | `record_depth_drop` |
| `StoreMetrics.det_*` | extend metrics: `depth_frames`, `depth_frames_dropped`, `depth_fps`, `last_depth_latency_ms` |

**Isolation rules (copy from detection snapshot, lines 98–113):**
- `snapshot_depth()` returns isolated copy under lock
- **JSON isolation:** API path must not serialize `depth_map` — metadata + stats only into `DepthPayload`
- When copying product for wire, omit or strip `depth_map` (or store array only in-process field that snapshot for API does not dump)

**Test analog:** `tests/test_perception_store.py` — keep-latest overwrite, isolated copy, concurrent set/snapshot, error field.

---

### `src/sentry_ai/models/cache.py` (utility, extend)

**Analog:** same file `configure_model_cache` (lines 53–84)

**Existing root resolution** (lines 66–70):
```python
if cache_root is not None:
    root = Path(cache_root)
else:
    env = os.environ.get("SENTRY_MODEL_CACHE")
    root = Path(env) if env else default_cache_root()
```

**Extend pattern** — after root resolved, also set HF home (sibling of `weights/`):
```python
hf_home = root / "hf"
hf_home.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("HF_HOME", str(hf_home))
# Ultralytics path unchanged: root / "weights"
```

Keep YOLO path intact; HF is sibling dir under same `SENTRY_MODEL_CACHE` root. Call **before** first `from_pretrained`.

**Test analog:** `tests/test_model_cache.py` — env override, tmp_path, idempotent; add asserts for `HF_HOME` under root.

---

### `src/sentry_ai/api/deps.py` + `app.py` (DI)

**Analog:** same files for `detection_worker`

**deps.py** (lines 13–21) — add field:
```python
@dataclass
class AppState:
    bus: FrameBus
    capture_loop: CaptureLoop
    bind: str
    perception_store: Any | None = None
    detection_worker: Any | None = None
    depth_worker: Any | None = None  # NEW
```

**app.py** (lines 16–50) — inject parallel kwarg; handlers never run inference:
```python
def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
    perception_store: Any | None = None,
    detection_worker: Any | None = None,
    depth_worker: Any | None = None,  # NEW
) -> FastAPI:
    app.state.depth_worker = depth_worker
    ...
```

Optional: `include_router(depth_router)` if `routes_depth.py` is implemented.

---

### `src/sentry_ai/api/routes_detection.py` (controller, extend snapshot)

**Analog:** same file `api_snapshot` (lines 56–89)

**Current pattern** — store-only, builds `PerceptionFrame`, `completeness.depth=False` hardcoded:
```python
@router.get("/api/snapshot")
async def api_snapshot(request: Request) -> dict[str, Any]:
    store = _require_store(request)
    product = store.snapshot()
    if product is None:
        raise HTTPException(status_code=404, detail="no detection product yet")
    frame = PerceptionFrame(
        ...
        completeness=Completeness(detections=True, depth=False, free_space=False),
        detections=list(product.detections),
        stats={"det_latency_ms": product.latency_ms, ...},
    )
    return frame.model_dump()
```

**Phase 4 changes (RESEARCH Pattern 5):**
1. Load **both** `store.snapshot()` and `store.snapshot_depth()`
2. **404 policy:** empty only when **neither** product exists; depth-only or det-only → 200 with completeness flags
3. Build `DepthPayload` from depth product metadata only (no map):
```python
depth_payload = DepthPayload(
    kind=depth_product.kind,
    unit=depth_product.unit,  # None for relative — validator enforces
    width=depth_product.width,
    height=depth_product.height,
)
# completeness.depth = depth_product is not None and depth_product.error is None
# stats: depth_latency_ms, depth_min/max/mean, det_frame_id / depth_frame_id
```
4. Never put `depth_map` on wire
5. Keep architecture asserts: no `VideoCapture`, no `predict` / inference in routes

**Wire schema already ready** (`schemas/perception.py` lines 31–45):
```python
class DepthPayload(BaseModel):
    kind: DepthKind
    unit: Literal["m"] | None = None
    width: int | None = None
    height: int | None = None
    # Intentionally NO field named depth_m
```

---

### `src/sentry_ai/api/routes_preview.py` (controller, status + MJPEG)

**Analog:** same file — det field merge + overlay before encode

**Status merge** (lines 53–79) — mirror for depth:
```python
# After det_* block, when store present:
depth_product = store.snapshot_depth()  # new method
depth_metrics = store.metrics_snapshot()
if depth_product is not None and depth_product.error is None:
    data["depth_latency_ms"] = depth_product.latency_ms
    data["depth_frame_id"] = depth_product.frame_id
    data["depth_kind"] = depth_product.kind  # string value
    if depth_product.unit is not None:
        data["depth_unit"] = depth_product.unit  # omit when null (relative honesty)
if depth_product is not None and depth_product.error:
    data["depth_error"] = depth_product.error
data["depth_fps"] = depth_metrics.depth_fps  # when metrics extended
```

**MJPEG generator** (lines 82–116) — blend depth then draw detections:
```python
async def _mjpeg_generator(bus, store=None, jpeg_quality=JPEG_QUALITY):
    while True:
        item = bus.get_latest()
        if item is not None:
            image = item.image_bgr
            if store is not None:
                depth_product = store.snapshot_depth()
                if (
                    depth_product is not None
                    and depth_product.error is None
                    and depth_product.depth_map is not None
                ):
                    image = blend_depth(image, depth_product.depth_map, alpha=0.45)
                product = store.snapshot()
                if product is not None:
                    image = draw_detections(image, product.detections)
            ok, buf = cv2.imencode(...)
        await asyncio.sleep(MJPEG_SLEEP_S)
```

**Architecture invariants (tests already enforce):**
- No `cv2.VideoCapture` / `worker.process` / `.predict(` in routes
- Temporal skew (depth/det `frame_id` lagging RGB) accepted intentionally
- Empty depth product → RGB (+ det boxes) only; stream stays 200

**Test analog:** `tests/test_api_preview.py` — `test_mjpeg_generator_with_store_overlay_still_jpeg`, `test_api_status_includes_det_fields_when_store_present`.

---

### `src/sentry_ai/api/routes_depth.py` (controller, optional)

**Analog:** `routes_detection.py` config routes (lines 92–117)

Only if Phase 4 includes runtime `depth_mode` toggle (RESEARCH: optional; serve-time config is enough for DEPTH-04).

```python
class DepthConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    depth_mode: Literal["relative", "metric_indoor", "metric_outdoor"]

@router.get("/api/depth/config")
@router.patch("/api/depth/config")
# _require_worker → depth_worker; 503 if missing
# Never run inference in handler
```

---

### `src/sentry_ai/cli.py` (lifecycle)

**Analog:** `serve` detection optional-extra block (lines 266–319)

```python
# Optional monocular depth (requires `uv sync --extra depth`).
depth_worker: Any | None = None
depth_loop: Any | None = None
try:
    from sentry_ai.models.cache import configure_model_cache
    from sentry_ai.models.depth.loop import DepthLoop
    from sentry_ai.models.depth.worker import DepthAnythingWorker

    configure_model_cache()  # HF_HOME under SENTRY_MODEL_CACHE
    depth_worker = DepthAnythingWorker(depth_mode="relative")  # or from cfg
    depth_loop = DepthLoop(bus, depth_worker, store)
except ImportError as exc:
    typer.echo(
        "depth disabled: depth extra not installed "
        f"({exc}). Install with: uv sync --extra depth",
        err=True,
    )
    depth_worker = None
    depth_loop = None

app_asgi = create_app(
    ...,
    perception_store=store,
    detection_worker=worker,
    depth_worker=depth_worker,
)

loop.start()
if det_loop is not None:
    det_loop.start()
if depth_loop is not None:
    depth_loop.start()
try:
    uvicorn.run(...)
finally:
    if depth_loop is not None:
        depth_loop.stop()
    if det_loop is not None:
        det_loop.stop()
    loop.stop()
```

**Test analog:** `tests/test_cli_serve.py` `test_serve_source_wires_detection_loop_lifecycle` — inspect source for `DepthLoop`, degrade message, no module-level `import torch`.

---

### `src/sentry_ai/ui/static/index.html` (component)

**Analog:** same file det metrics (lines 149–172, 229–236)

Add footer rows + `applyStatus` fields:
```html
<div>Depth: <strong id="metric-depth-kind">—</strong></div>
<div>Depth ms: <strong id="metric-depth-ms">—</strong></div>
```

```javascript
// In applyStatus — never label relative as meters
elDepthKind.textContent =
  (data && data.depth_kind) ? String(data.depth_kind) : "—";
// Optional human label: if depth_kind === "relative" show "relative (not meters)"
elDepthMs.textContent =
  (data && typeof data.depth_latency_ms === "number")
    ? formatNum(data.depth_latency_ms, 1)
    : "—";
// Do NOT display depth_unit as "m" when kind is relative (omit field server-side)
```

Colormap is **server-drawn** on MJPEG — browser only polls status (parity with detection boxes). No client-side depth decode.

**Test:** extend `test_root_serves_live_preview_html` for Depth / Depth ms strings.

---

### `pyproject.toml` (optional-extra)

**Analog:** `detect` extra (lines 33–43)

```toml
# Monocular depth (Phase 4). Install: uv sync --extra dev --extra depth
depth = [
  "torch>=2.2,<3",
  "transformers>=4.45,<6",
  "huggingface-hub>=0.23,<2",
  "pillow>=10,<13",
]
```

Optional entry-point worker registration (mirror yolo-fixed):
```toml
[project.entry-points."sentry_ai.workers"]
# depth-anything-v2-small = "sentry_ai.models.depth.worker:DepthAnythingWorker"
```

---

### Tests (mirror Phase 3 file set)

| New / extend test | Analog |
|-------------------|--------|
| `tests/test_depth_loop.py` | `test_detection_loop.py` |
| `tests/test_depth_worker.py` | `test_detection_worker.py` |
| `tests/test_depth_preprocess.py` | `test_detection_mapping.py` (pure) |
| `tests/test_depth_colormap.py` | `test_detection_overlay.py` |
| `tests/test_perception_store.py` (extend) | same — `set_depth` / isolation |
| `tests/test_api_depth.py` or extend `test_api_detection.py` | snapshot completeness.depth |
| `tests/test_api_preview.py` (extend) | status depth_* + MJPEG with depth product |
| `tests/test_model_cache.py` (extend) | HF_HOME under SENTRY_MODEL_CACHE |
| `tests/test_cli_serve.py` (extend) | DepthLoop lifecycle + degrade |
| `tests/test_third_party_models_doc.py` (extend) | Phase 4 depth active wording |
| `tests/test_schemas_depth_kind.py` | **keep green** — do not regress |

**Shared test fixtures:** `conftest.py` `image_frame_factory`; inject fake model/processor like `FakeModel` in worker tests — never network/HF.

---

## Shared Patterns

### 1. FrameBus → daemon worker → PerceptionStore (never cameras in workers)

**Source:** `models/detection/loop.py`, `capture/loop.py` ownership  
**Apply to:** `DepthLoop`, `DepthAnythingWorker`, all depth routes

- CaptureLoop sole camera owner
- Workers only read `frame.image_bgr`
- Handlers only `bus.get_latest` / `store.snapshot*` / conf-style setters
- Architecture tests: `inspect.getsource` asserts no `VideoCapture`

### 2. Injectable heavy deps for CI

**Source:** `YoloDetectionWorker.__init__(model=...)`  
**Apply to:** `DepthAnythingWorker(model=, processor=)`

- Unit tests never call `from_pretrained` / hub
- Lazy load only when both injected objects are None
- ImportError message points at `uv sync --extra depth`

### 3. Keep-latest + drop counting + error-alive

**Source:** `DetectionLoop._run` + `PerceptionStore.set_detections` / `record_drop`  
**Apply to:** DepthLoop + store depth half

- Skip same `frame_id`
- Gap → drop metric
- Exception → product with `error=`, thread continues
- Latency via `time.perf_counter()`

### 4. Single store, dual products, UI/API one truth

**Source:** `PerceptionStore` + `routes_preview` overlay from store + `routes_detection` snapshot  
**Apply to:** depth product, colormap, snapshot DepthPayload

- One `PerceptionStore` instance (not DepthStore class)
- Server draws overlays from store; status polls same fields
- Wire path: metadata only; ndarray in-process for colormap / Phase 5

### 5. Optional-extra degrade on serve

**Source:** `cli.py` serve detection try/import  
**Apply to:** depth extra

- try import worker+loop; on ImportError message + continue capture-only
- start/stop loops in nested finally order (depth → det → capture)

### 6. Model cache under SENTRY_MODEL_CACHE

**Source:** `models/cache.py`  
**Apply to:** HF downloads

- Root: arg → env → `~/.cache/sentry-ai`
- YOLO: `weights/`; HF: `hf/` (`HF_HOME`)
- Offline after first download

### 7. Depth honesty (FOUND-03 / DEPTH-04)

**Source:** `DepthKind`, `DepthPayload` validator, `test_schemas_depth_kind.py`  
**Apply to:** mapping, snapshot, status, UI copy

- Relative → `unit=None`; never `"m"` label
- Metric mode → `DepthKind.METRIC_ESTIMATED` + `unit="m"` only when enabled
- No `depth_m` field ever
- Kind from config mode, not float heuristics

### 8. Status / telemetry field naming

**Source:** det fields in `routes_preview.api_status`  
**Apply to:** depth twins

| Detection | Depth |
|-----------|-------|
| `det_latency_ms` | `depth_latency_ms` |
| `det_fps` | `depth_fps` |
| `det_frame_id` | `depth_frame_id` |
| `detections_count` | `depth_kind` (+ optional unit) |
| `det_conf` | `depth_unit` (omit if null) |

### 9. FastAPI route style

**Source:** `routes_detection.py`, `routes_preview.py`  
**Apply to:** all API extensions

- `APIRouter`, `Request` → `request.app.state.*`
- Pydantic body with `ConfigDict(extra="forbid")` + Field bounds
- 503 missing store/worker; 404 empty products (adjusted multi-product rule)
- Return `model_dump()` dicts; no inference in handlers

### 10. Device selection

**Source:** `yolo_worker.resolve_device`  
**Apply to:** depth worker load

- cuda → mps → cpu; never hardcode CUDA
- Prefer extract to `models/device.py` if both import it; copy OK

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| HF `AutoModelForDepthEstimation` inference body | service internals | transform | No transformers depth path in repo yet — use RESEARCH Pattern 3 + HF model card; still wrap with **YoloDetectionWorker lifecycle** (inject, lazy load, process signature) |
| Binary depth wire protocol | — | — | Out of scope Phase 4 |
| Free-space / Spatial Post | — | — | Phase 5 |

Everything else has a Phase 3 (or Phase 1 schema) twin.

---

## Planner Quick Reference: Phase 3 → Phase 4 Rename Map

| Phase 3 | Phase 4 |
|---------|---------|
| `DetectionLoop` | `DepthLoop` |
| `YoloDetectionWorker` | `DepthAnythingWorker` |
| `list[Detection]` product | `DepthProduct` (+ in-process `depth_map`) |
| `set_detections` / `snapshot` | `set_depth` / `snapshot_depth` |
| `draw_detections` | `colorize_depth` + `blend_depth` |
| `results_to_detections` | `kind_for_mode` + tensor→map mapping |
| `det_*` status fields | `depth_*` status fields |
| `extra detect` / ultralytics | `extra depth` / transformers+torch+pillow |
| conf PATCH | optional `depth_mode` PATCH or serve-time only |
| YOLO `weights_dir` | HF `HF_HOME` under same cache root |

**Plan shape (from RESEARCH):**
1. **04-01:** extra + cache HF + preprocess/mapping/worker + DepthLoop + store + unit tests (DEPTH-01)
2. **04-02:** snapshot DepthPayload + completeness, MJPEG colormap, status/UI, metric labeling, serve lifecycle, docs (DEPTH-02/03/04)

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/models/detection/`, `state/`, `api/`, `models/cache.py`, `schemas/`, `cli.py`, `ui/static/`, `plugins/protocols.py`, `policy/`, `tests/test_detection_*`, `test_api_*`, `test_perception_store.py`, `test_model_cache.py`, `test_cli_serve.py`, `test_schemas_depth_kind.py`

**Files scanned:** ~25 source + ~12 tests  
**Pattern extraction date:** 2026-08-07  
**Strong analogs used:** DetectionLoop, YoloDetectionWorker, overlay, PerceptionStore, routes_preview, routes_detection, cache, cli serve, UI footer, optional-extra detect
