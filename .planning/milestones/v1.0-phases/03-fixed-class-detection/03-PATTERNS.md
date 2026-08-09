# Phase 3: Fixed-Class Detection - Pattern Map

**Mapped:** 2026-08-07  
**Files analyzed:** 18 (new + modified)  
**Analogs found:** 17 / 18

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/models/detection/yolo_worker.py` | service / worker | transform (frame→detections) | `src/sentry_ai/plugins/builtins.py` (`NoopWorker`) | role-match |
| `src/sentry_ai/models/detection/mapping.py` | utility | transform | `src/sentry_ai/schemas/perception.py` (`Detection`) | partial |
| `src/sentry_ai/models/detection/loop.py` | service / loop | event-driven (bus subscriber) | `src/sentry_ai/capture/loop.py` (`CaptureLoop`) | exact |
| `src/sentry_ai/state/perception_store.py` | store | keep-latest pub-sub | `src/sentry_ai/bus/frame_bus.py` (`FrameBus`) | exact |
| `src/sentry_ai/models/detection/overlay.py` (or helper in routes) | utility | transform (draw) | `src/sentry_ai/api/routes_preview.py` (`_mjpeg_generator` + `cv2.imencode`) | role-match |
| `src/sentry_ai/models/cache.py` (or `backend/model_cache.py`) | utility / config | file-I/O | no close analog; use RESEARCH Pattern 3 | none |
| `src/sentry_ai/api/routes_detection.py` | route / controller | request-response | `src/sentry_ai/api/routes_preview.py` | exact |
| `src/sentry_ai/api/app.py` | config / factory | request-response | self (extend) | exact |
| `src/sentry_ai/api/deps.py` | config | — | self (extend `AppState`) | exact |
| `src/sentry_ai/api/routes_preview.py` | route | streaming | self (MJPEG + store overlay) | exact |
| `src/sentry_ai/cli.py` | config / entry | event-driven | self (`serve` lifecycle) | exact |
| `src/sentry_ai/ui/static/index.html` | component | request-response poll | self (status poll + footer metrics) | exact |
| `src/sentry_ai/config/models.py` | model / config | — | self (`ModelsConfig`) | exact |
| `src/sentry_ai/plugins/registry.py` + `pyproject.toml` entry points | config / plugin | — | `register_builtins` + `[project.entry-points."sentry_ai.workers"]` | exact |
| `src/sentry_ai/capture/status.py` (optional det fields) | model | request-response | self (`StatusSnapshot`) | exact |
| `THIRD_PARTY_MODELS.md` | docs | — | self + `tests/test_third_party_models_doc.py` | exact |
| `tests/test_detection_*.py` / `test_api_detection.py` / `test_model_cache.py` | test | — | `tests/test_api_preview.py`, `test_capture_loop_reconnect.py`, `test_frame_bus.py` | exact |
| `src/sentry_ai/models/__init__.py`, `detection/__init__.py`, `state/__init__.py` | package | — | `src/sentry_ai/bus/__init__.py`, `capture/__init__.py` | exact |

---

## Pattern Assignments

### `src/sentry_ai/models/detection/yolo_worker.py` (service/worker, transform)

**Analog:** `src/sentry_ai/plugins/builtins.py` (`NoopWorker`) + `src/sentry_ai/plugins/protocols.py` (`ModelWorker`)

**Protocol contract** (`plugins/protocols.py` lines 27–36):
```python
@runtime_checkable
class ModelWorker(Protocol):
    """Perception worker that processes an ImageFrame (or Frame identity).

    Phase 1 noop workers return None; later phases return PerceptionFrame.
    """

    name: str

    def process(self, frame: ImageFrame | object) -> object | None: ...
```

**Stub worker shape** (`plugins/builtins.py` lines 20–28):
```python
class NoopWorker:
    """Model worker stub that performs no inference."""

    name: str = "noop"

    def process(self, frame: ImageFrame | object) -> object | None:
        # Phase 1/2: no models — return None so callers can branch.
        _ = frame
        return None
```

**Copy for Phase 3:**
- Class attribute `name: str = "yolo-fixed"` (plugin entry point name).
- `process(self, frame: ImageFrame) -> list[Detection]` (narrow return; still satisfies Protocol `object | None`).
- Accept `ImageFrame` and use `frame.image_bgr` (BGR uint8) — never open cameras.
- Thread-safe runtime conf via `threading.Lock` (see Shared Patterns → Runtime conf).
- Lazy / constructor load of YOLO after cache setup; optional injectable `predict`/`model` for tests (mirror how `NullBackend` avoids torch).

**Do not force through `InferenceBackend.infer`** — `backend/protocols.py` + `null.py` stay stubs; Ultralytics owns preprocess (`NullBackend` pattern: no torch import on non-detect path).

---

### `src/sentry_ai/models/detection/mapping.py` (utility, transform)

**Analog:** `src/sentry_ai/schemas/perception.py` (`Detection` schema) — pure function boundary; keep Ultralytics types out of wire models.

**Detection schema** (lines 48–55):
```python
class Detection(BaseModel):
    """Minimal detection placeholder; tightened in later detection phases."""

    model_config = ConfigDict(extra="forbid")

    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float] | list[float]
```

**Copy for Phase 3:**
- Pure function `results_to_detections(result) -> list[Detection]` (no I/O, no YOLO import required if duck-typed).
- Map `result.boxes.xyxy/conf/cls` + `result.names` → `Detection(...)`.
- Empty boxes → `[]` (not `None`); completeness is decided by store/loop, not mapping.
- Unit-test with fake Boxes-like objects (no weight download) — see `tests/conftest.py` factory style.

**Completeness assembly analog** (`cli.py` smoke lines 160–174):
```python
perception = PerceptionFrame.model_validate(
    {
        "schema_version": 1,
        "frame_id": meta.frame_id,
        "camera_id": meta.camera_id,
        "t_capture": meta.t_capture,
        "t_publish": meta.t_ingest,
        "completeness": Completeness(
            depth=False,
            detections=False,  # Phase 3: True when stage ran
            free_space=False,
        ).model_dump(),
    }
)
```
Phase 3 snapshot builder sets `detections=True` when store has a product (including empty list).

---

### `src/sentry_ai/models/detection/loop.py` (service/loop, event-driven)

**Analog:** `src/sentry_ai/capture/loop.py` (`CaptureLoop`) — **primary structural template**.

**Imports / constructor pattern** (lines 12–55):
```python
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from sentry_ai.bus.frame_bus import FrameBus
# ...

logger = logging.getLogger(__name__)

class CaptureLoop:
    def __init__(
        self,
        source: Any,
        bus: FrameBus,
        *,
        initial_backoff: float = DEFAULT_INITIAL_BACKOFF,
        # ...
    ) -> None:
        self._source = source
        self._bus = bus
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
```

**Lifecycle start/stop** (lines 105–132):
```python
def start(self) -> None:
    """Spawn daemon capture thread. Does not block on first frame."""
    with self._lock:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run,
            name=f"capture-{self.source_name}",
            daemon=True,
        )
        self._thread.start()

def stop(self) -> None:
    """Signal stop, join thread, close source. Idempotent."""
    self._stop.set()
    thread = None
    with self._lock:
        thread = self._thread
    if thread is not None and thread.is_alive():
        thread.join(timeout=5.0)
    # cleanup...
```

**Copy for `DetectionLoop`:**
| CaptureLoop | DetectionLoop |
|-------------|---------------|
| `source` + `bus` | `bus` + `worker` + `store` |
| `_run` reads `source.read()` | `_run` reads `bus.get_latest()` |
| publishes to bus | publishes to `PerceptionStore` |
| reconnect/backoff | skip same `frame_id`; short `Event.wait` sleep |
| owns camera open/close | **never** opens camera |
| `build_status` for API | optional det metrics on store or status merge |

**Run-loop skeleton** (adapt CaptureLoop `_run` + RESEARCH Pattern 1):
```python
def _run(self) -> None:
    while not self._stop.is_set():
        frame = self._bus.get_latest()
        if frame is None or frame.frame_id == self._last_frame_id:
            self._stop.wait(0.005)
            continue
        t0 = time.perf_counter()
        dets = self._worker.process(frame)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        self._last_frame_id = frame.frame_id
        self._store.set_detections(
            frame_id=frame.frame_id,
            camera_id=frame.camera_id,
            t_capture=frame.meta.t_capture,
            detections=dets or [],
            latency_ms=latency_ms,
        )
```

**Error handling:** Mirror CaptureLoop’s broad catch around process so worker exceptions set store error detail / log and keep thread alive (do not kill detection thread on one bad frame).

**Test analog:** `tests/test_capture_loop_reconnect.py` — fake sources, `_wait_until`, start/stop in try/finally. Detection loop tests should inject a fake worker (no YOLO) and assert bus-only reads (`inspect.getsource` no `VideoCapture` like `test_routes_preview_has_no_videocapture`).

---

### `src/sentry_ai/state/perception_store.py` (store, keep-latest)

**Analog:** `src/sentry_ai/bus/frame_bus.py` (`FrameBus` + `BusMetrics`)

**Structure** (lines 17–74):
```python
@dataclass
class BusMetrics:
    frames_published: int = 0
    frames_dropped: int = 0
    last_publish_t: float | None = None
    capture_fps: float = 0.0


class FrameBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: ImageFrame | None = None
        self._metrics = BusMetrics()
        # fps window fields...

    def publish(self, frame: ImageFrame) -> None:
        with self._lock:
            # overwrite semantics + metrics
            self._latest = frame
            ...

    def get_latest(self) -> ImageFrame | None:
        with self._lock:
            return self._latest

    def metrics_snapshot(self) -> BusMetrics:
        with self._lock:
            return BusMetrics(...)  # isolated copy
```

**Copy for `PerceptionStore`:**
- `threading.Lock` + single latest detection product slot (depth-1, not queue).
- Dataclass snapshot type (e.g. `DetectionProduct`: `frame_id`, `camera_id`, `t_capture`, `detections`, `latency_ms`, `conf`, `model_name`).
- `set_detections(...)` / `snapshot()` returning isolated copy (same isolation rule as `metrics_snapshot`).
- Optional FPS window for `det_fps` mirroring bus FPS math (lines 52–59).
- **No numpy** on the store wire path; store `list[Detection]` only.

**Test analog:** `tests/test_frame_bus.py` — none before publish, overwrite latest, isolated snapshot mutation safety, concurrent publish/read with threads.

---

### Overlay helper (draw detections) (utility, transform)

**Analog:** `src/sentry_ai/api/routes_preview.py` MJPEG encode path

**Current encode** (lines 50–74):
```python
async def _mjpeg_generator(
    bus: Any,
    jpeg_quality: int = JPEG_QUALITY,
) -> AsyncIterator[bytes]:
    """Yield multipart JPEG parts from the keep-latest bus slot."""
    boundary = BOUNDARY.encode()
    while True:
        item = bus.get_latest()
        if item is not None:
            ok, buf = cv2.imencode(
                ".jpg",
                item.image_bgr,
                [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality],
            )
            if ok:
                chunk = buf.tobytes()
                yield (
                    b"--" + boundary + b"\r\n"
                    + b"Content-Type: image/jpeg\r\n\r\n"
                    + chunk + b"\r\n"
                )
        await asyncio.sleep(MJPEG_SLEEP_S)
```

**Copy for Phase 3:**
- Keep generator async + `asyncio.sleep` (do not block event loop; never call YOLO here).
- Before `imencode`, copy BGR and draw from **store** detections (same list as snapshot):
```python
# OpenCV only — no supervision (CONTEXT discretion)
out = image_bgr.copy()
for d in detections:
    x1, y1, x2, y2 = map(int, d.bbox_xyxy)
    cv2.rectangle(out, (x1, y1), (x2, y2), (0, 255, 180), 2)
    label = f"{d.class_name} {d.confidence:.2f}"
    cv2.putText(out, label, (x1, max(0, y1 - 5)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 180), 1, cv2.LINE_AA)
```
- Inject store into generator (extend signature or read `request.app.state` before starting stream).
- Prefer pure `draw_detections(image_bgr, detections) -> np.ndarray` for unit tests (`test_detection_overlay.py`).

**Architecture invariant** (docstring lines 1–4 of routes_preview): handlers only call bus/store — never `source.read` / `VideoCapture`. Preserve `test_routes_preview_has_no_videocapture` spirit.

---

### `src/sentry_ai/models/cache.py` (utility, file-I/O) — **no close analog**

**Closest partial:** config load + env overrides; RESEARCH Pattern 3 is authoritative.

**Recommended shape** (from RESEARCH; implement as small pure helper):
```python
def configure_model_cache(
    cache_root: Path | None = None,
) -> Path:
    """Point Ultralytics weights_dir at Sentry-owned cache; return weights_dir."""
    # SENTRY_MODEL_CACHE / default ~/.cache/sentry-ai
    # mkdir weights; setdefault YOLO_CONFIG_DIR
    # settings.update({"weights_dir": ..., "sync": False})
```

**Test analog:** pure path tests like `tests/test_third_party_models_doc.py` (filesystem assertions, no network) + `tests/test_config_profiles.py` style for env/config.

---

### `src/sentry_ai/api/routes_detection.py` (route, request-response)

**Analog:** `src/sentry_ai/api/routes_preview.py`

**Imports + app.state accessors** (lines 7–39):
```python
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

router = APIRouter()


def _bus(request: Request) -> Any:
    return request.app.state.bus


def _capture_loop(request: Request) -> Any:
    return request.app.state.capture_loop
```

**Status handler pattern** (lines 42–47):
```python
@router.get("/api/status")
async def api_status(request: Request) -> dict[str, Any]:
    """Return capture status + bus metrics as JSON."""
    loop = _capture_loop(request)
    snapshot = loop.build_status(bind=_bind(request))
    return snapshot.model_dump()
```

**Copy for detection routes:**
```python
# Helpers
def _store(request: Request) -> Any:
    return request.app.state.perception_store

def _detection_worker(request: Request) -> Any:
    return getattr(request.app.state, "detection_worker", None)

# GET /api/snapshot → PerceptionFrame.model_dump() from store
# GET /api/detection/config → conf + weight + device
# PATCH /api/detection/config → Pydantic body Field(ge=0, le=1); worker.set_conf
```

**Validation pattern:** Pydantic models with `ConfigDict(extra="forbid")` as in `schemas/perception.py` and `capture/status.py` `StatusSnapshot`.

**HTTP errors:** FastAPI `HTTPException(503, ...)` when worker/store missing (RESEARCH sketch) — Phase 2 routes currently assume loop always injected; detection may be optional-extra so 503 is appropriate.

**Test analog:** `tests/test_api_preview.py`:
```python
app = create_app(bus=bus, capture_loop=loop, bind="127.0.0.1:8000")
with TestClient(app) as client:
    resp = client.get("/api/status")
    assert resp.status_code == 200
```
Extend `create_app` kwargs for store/worker; use `TestClient` for PATCH/GET snapshot.

---

### `src/sentry_ai/api/app.py` + `deps.py` (factory / config)

**Analog:** self — current injection pattern.

**`create_app`** (app.py lines 13–34):
```python
def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
) -> FastAPI:
    app = FastAPI(
        title="Sentry AI — Live Preview",
        docs_url=None,
        redoc_url=None,
    )
    app.state.bus = bus
    app.state.capture_loop = capture_loop
    app.state.bind = bind
    app.state.deps = AppState(bus=bus, capture_loop=capture_loop, bind=bind)
    app.include_router(preview_router)
    return app
```

**`AppState`** (deps.py lines 13–19):
```python
@dataclass
class AppState:
    bus: FrameBus
    capture_loop: CaptureLoop
    bind: str
```

**Copy for Phase 3:**
- Add optional kwargs: `perception_store`, `detection_worker` (and/or `detection_loop` if status needs it).
- Attach on `app.state.*` **and** extend `AppState` dataclass (keep both in sync as today).
- `app.include_router(detection_router)` next to preview router.
- Caller (`cli.serve`) owns DetectionLoop lifecycle — factory still does **not** start threads (same contract as CaptureLoop).

---

### `src/sentry_ai/cli.py` (`serve` lifecycle)

**Analog:** self — `serve` command (lines 249–281)

```python
from sentry_ai.api.app import create_app
from sentry_ai.bus.frame_bus import FrameBus
from sentry_ai.capture.loop import CaptureLoop

src = _build_serve_source(...)
bus = FrameBus()
loop = CaptureLoop(src, bus)
bind = f"{host}:{port}"
app_asgi = create_app(bus=bus, capture_loop=loop, bind=bind)

loop.start()
try:
    import uvicorn
    uvicorn.run(app_asgi, host=host, port=port, log_level="info")
finally:
    loop.stop()
```

**Copy for Phase 3:**
```python
store = PerceptionStore()
# optional-extra: import YoloDetectionWorker; clear error if missing
configure_model_cache(...)
worker = YoloDetectionWorker(conf=0.25, weights=tier_to_weight(cfg.models.detector_tier))
det_loop = DetectionLoop(bus, worker, store)
app_asgi = create_app(
    bus=bus,
    capture_loop=loop,
    bind=bind,
    perception_store=store,
    detection_worker=worker,
)
loop.start()
det_loop.start()
try:
    uvicorn.run(...)
finally:
    det_loop.stop()
    loop.stop()
```

- Keep `allow_cloud` gate (lines 242–247).
- Load profile for `detector_tier` → weight mapping (`n`→`yolo26n.pt`, prefer `s` for desktop).
- Localhost bind warning pattern unchanged (lines 268–273).

---

### `src/sentry_ai/ui/static/index.html` (component)

**Analog:** self — status poll + footer metrics.

**Poll loop** (lines 129–212):
```javascript
var STATUS_POLL_MS = 500;
// ...
function pollStatus() {
  fetch("/api/status", { cache: "no-store" })
    .then(function (resp) {
      if (!resp.ok) throw new Error("status HTTP " + resp.status);
      return resp.json();
    })
    .then(function (data) { applyStatus(data); })
    .catch(function () { /* error pill + banner */ });
}
pollStatus();
setInterval(pollStatus, STATUS_POLL_MS);
```

**Copy for Phase 3:**
- Footer metrics: det count, det latency ms, conf (extend `applyStatus` from `/api/status` fields).
- Conf slider → debounced `fetch("/api/detection/config", { method: "PATCH", headers: {"Content-Type":"application/json"}, body: JSON.stringify({conf: v}) })`.
- Keep single `<img src="/preview/mjpeg">` (server-drawn boxes; no canvas).
- Preserve UI copy constraints tested in `test_root_serves_live_preview_html`: no “autonomous” / “safe to drive”.
- Optional first-run note: model may download once (MODEL-02).

---

### `src/sentry_ai/config/models.py` (config)

**Analog:** self — `ModelsConfig` (lines 19–27)

```python
class ModelsConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_cloud: bool = False
    defaults_commercially_friendly: bool = True
    detector_tier: str | None = None
    depth_tier: str | None = None
```

**Copy for Phase 3 (optional fields):**
- `detector_conf: float = 0.25` and/or `weights: str | None = None`, `cache_dir: str | None = None` if YAML-driven; else keep conf as runtime-only on worker and map tier→weight in code.
- Profiles already set `detector_tier: n|m` (`cpu-fallback.yaml`, `desktop-gpu.yaml`) — honor tier map; RESEARCH recommends desktop `s` (profile change is discretionary).

---

### Plugin registration (`registry` + `pyproject.toml`)

**Analog:** `plugins/registry.py` `register_builtins` + entry points

**Builtins registration** (lines 86–104):
```python
if "noop" not in registry.list_workers():
    registry.register_worker("noop", NoopWorker)
```

**Entry points** (`pyproject.toml` lines 49–50):
```toml
[project.entry-points."sentry_ai.workers"]
noop = "sentry_ai.plugins.builtins:NoopWorker"
```

**Copy for Phase 3:**
```toml
yolo-fixed = "sentry_ai.models.detection.yolo_worker:YoloDetectionWorker"

[project.optional-dependencies]
detect = ["ultralytics-opencv-headless>=8.4.33,<9"]
# keep dev as-is; CI unit tests mock YOLO without extra when possible
```
- Optional: register in `register_builtins` only if import succeeds (graceful degrade without torch).
- Skip-if-present discovery remains idempotent.

---

### Tests (new modules)

| New test file | Closest analog | Patterns to copy |
|---------------|----------------|------------------|
| `tests/test_detection_mapping.py` | `tests/test_schemas_perception.py` | pure pydantic/assert, no I/O |
| `tests/test_detection_worker.py` | `tests/test_backend_protocols.py` + NoopWorker | inject fake model; no download |
| `tests/test_detection_loop.py` | `tests/test_capture_loop_reconnect.py` | fake worker, bus publish, `_wait_until`, start/stop finally |
| `tests/test_detection_overlay.py` | pure function unit style | known bbox → pixel checks |
| `tests/test_api_detection.py` | `tests/test_api_preview.py` | `create_app` + `TestClient`, no VideoCapture |
| `tests/test_model_cache.py` | path/doc tests | tmp_path, env, no network |
| extend `test_third_party_models_doc.py` | self | assert YOLO AGPL + Phase 3 status language |
| fixtures | `tests/conftest.py` `make_image_frame` | fake YOLO result factory |

**Shared test helpers to reuse:**
- `make_image_frame` / `image_frame_factory` from `conftest.py`
- `_wait_for_frame` / `_wait_until` from preview & capture tests
- Architecture source-inspect: assert no `VideoCapture` in detection routes/loop

---

## Shared Patterns

### Thread lifecycle (daemon worker loops)
**Source:** `src/sentry_ai/capture/loop.py` lines 50–55, 105–132  
**Apply to:** `DetectionLoop`  
```python
self._stop = threading.Event()
self._thread: threading.Thread | None = None
# start: clear event, Thread(target=_run, name=..., daemon=True).start()
# stop: set event, join(timeout=5.0), idempotent
```

### Keep-latest + lock + isolated snapshot
**Source:** `src/sentry_ai/bus/frame_bus.py` lines 38–74  
**Apply to:** `PerceptionStore`, any det metrics  
```python
with self._lock:
    self._latest = product
# getters return copies / immutable snapshots, never live mutable metrics objects
```

### FrameBus subscriber (never open cameras)
**Source:** `routes_preview.py` docstring + `FrameBus.get_latest`  
**Apply to:** DetectionLoop, MJPEG, snapshot  
```python
frame = bus.get_latest()  # non-blocking, non-consuming
# never source.read() / cv2.VideoCapture in workers or handlers
```

### ModelWorker plugin surface
**Source:** `plugins/protocols.py` + `builtins.NoopWorker` + entry points  
**Apply to:** `YoloDetectionWorker`  
- `name: str` + `process(frame) -> ...`  
- Register `yolo-fixed` entry point  

### Runtime conf (thread-safe)
**Source:** RESEARCH Pattern 5 (no existing conf lock — new; mirror FrameBus lock style)  
**Apply to:** worker + PATCH route  
```python
with self._lock:
    conf = self._conf
# predict(..., conf=conf) each process() call — do not freeze conf at load
```

### FastAPI DI via `app.state`
**Source:** `api/app.py`, `api/deps.py`, `routes_preview.py`  
**Apply to:** all new routes  
```python
request.app.state.bus
request.app.state.capture_loop
# Phase 3 additions:
request.app.state.perception_store
request.app.state.detection_worker
```

### OpenCV encode / draw (headless)
**Source:** `routes_preview.py` + project dep `opencv-python-headless`  
**Apply to:** overlay + JPEG  
- Use existing OpenCV; do **not** add `supervision`  
- Prefer `ultralytics-opencv-headless` optional extra to avoid GUI OpenCV conflict  

### Pydantic wire models
**Source:** `schemas/perception.py`, `capture/status.py`  
**Apply to:** snapshot responses, PATCH body, optional StatusSnapshot extensions  
```python
model_config = ConfigDict(extra="forbid")
# Field(ge=0.0, le=1.0) for conf
```

### CLI serve lifecycle ownership
**Source:** `cli.py` serve  
**Apply to:** detection thread  
- Factory does not start loops; CLI starts capture + detection, stops in `finally`  

### Local-OSS gates
**Source:** `cli.py` smoke/serve `allow_cloud` checks; `THIRD_PARTY_MODELS.md`  
**Apply to:** model load path + docs  
- Document Ultralytics AGPL; update table from “Planned Phase 3” → active Phase 3 status  

### Testing without ML weights
**Source:** Phase 2 tests never import torch; `NullBackend` comment  
**Apply to:** all DET unit tests  
- Mock YOLO / inject FakeDetectionWorker  
- Optional-extra `detect` for real-model manual runs only  

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/sentry_ai/models/cache.py` (Ultralytics `weights_dir` / `YOLO_CONFIG_DIR` setup) | utility | file-I/O | No existing model download/cache helper; implement from RESEARCH Pattern 3 + Ultralytics settings API |

Partial gaps (use RESEARCH code sketches, not empty design):
- Ultralytics `Results` → `Detection` mapping (schema exists; converter does not)
- Runtime conf PATCH body model (new; follow Pydantic forbid-extra style)

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/{bus,capture,api,plugins,backend,schemas,cli,ui,config,sources,policy}/`, `tests/`, `pyproject.toml`, `THIRD_PARTY_MODELS.md`, Phase 3 CONTEXT/RESEARCH  

**Files scanned:** ~35 source + ~18 test modules  

**Pattern extraction date:** 2026-08-07  

**Key takeaway for planner:** Phase 3 is mostly **composition of Phase 2 patterns** — CaptureLoop-shaped DetectionLoop, FrameBus-shaped PerceptionStore, routes_preview-shaped detection routes, NoopWorker-shaped YoloDetectionWorker — plus one greenfield cache helper and Ultralytics mapping.
