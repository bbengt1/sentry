# Phase 6: Developer Controls & Open-Vocab - Pattern Map

**Mapped:** 2026-08-08  
**Files analyzed:** 22  
**Analogs found:** 20 / 22  

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|----------------|---------------|
| `src/sentry_ai/api/routes_pipeline.py` | route | request-response | `src/sentry_ai/api/routes_detection.py` | exact |
| `src/sentry_ai/api/routes_open_vocab.py` | route | request-response | `src/sentry_ai/api/routes_detection.py` + `routes_depth.py` | exact |
| `src/sentry_ai/control/pipeline_state.py` | utility | request-response | `YoloDetectionWorker` conf lock + `PerceptionStore` lock | role-match |
| `src/sentry_ai/models/detection/yoloe_worker.py` | service | request-response | `src/sentry_ai/models/detection/yolo_worker.py` | exact |
| `src/sentry_ai/models/detection/open_vocab_loop.py` | service | event-driven | `src/sentry_ai/models/detection/loop.py` | exact |
| `src/sentry_ai/models/detection/loop.py` | service | event-driven | (self — add enable gate) | self-extend |
| `src/sentry_ai/models/depth/loop.py` | service | event-driven | `models/detection/loop.py` enable gate | role-match |
| `src/sentry_ai/spatial/loop.py` | service | event-driven | `models/detection/loop.py` + free_space cuts | role-match |
| `src/sentry_ai/state/perception_store.py` | store | CRUD | (self — fourth product slot) | self-extend |
| `src/sentry_ai/api/assemble.py` | utility | transform | (self — merge OV dets) | self-extend |
| `src/sentry_ai/api/routes_preview.py` | route | request-response | (self — status + MJPEG OV) | self-extend |
| `src/sentry_ai/api/app.py` | config | request-response | (self — wire new routers/workers) | self-extend |
| `src/sentry_ai/api/deps.py` | config | request-response | (self — AppState fields) | self-extend |
| `src/sentry_ai/cli.py` | config | event-driven | (self — OpenVocabLoop lifecycle) | self-extend |
| `src/sentry_ai/models/detection/overlay.py` | utility | transform | (self — dual color by source) | self-extend |
| `src/sentry_ai/models/cache.py` | config | file-I/O | (self — KNOWN_WEIGHTS) | self-extend |
| `src/sentry_ai/schemas/perception.py` | model | transform | (self — Detection.source) | self-extend |
| `src/sentry_ai/ui/static/index.html` | component | request-response | (self — conf slider + status poll) | self-extend |
| `THIRD_PARTY_MODELS.md` | config | — | (self — YOLOE AGPL row) | self-extend |
| `tests/test_pipeline_config.py` | test | request-response | `tests/test_api_detection.py` | exact |
| `tests/test_yoloe_worker.py` | test | request-response | `tests/test_detection_worker.py` | exact |
| `tests/test_open_vocab_loop.py` | test | event-driven | `tests/test_detection_loop.py` | exact |

## Pattern Assignments

### `src/sentry_ai/api/routes_pipeline.py` (route, request-response)

**Analog:** `src/sentry_ai/api/routes_detection.py` + `routes_depth.py`

**Imports / router skeleton** (detection lines 10–19; depth lines 7–14):
```python
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter()
```

**Pydantic body with `extra=forbid` + Field ranges** (detection lines 22–27; depth lines 17–22):
```python
class DetectionConfigUpdate(BaseModel):
    """Runtime conf update body (DET-03). Extra fields rejected."""

    model_config = ConfigDict(extra="forbid")

    conf: float = Field(ge=0.0, le=1.0)
```

**Pipeline body should mirror this shape** (from RESEARCH, apply same style):
```python
class PipelineConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    detection_enabled: bool | None = None
    depth_enabled: bool | None = None
    free_space_enabled: bool | None = None
    near_cut: float | None = Field(default=None, ge=0.0, le=1.0)
    mid_cut: float | None = Field(default=None, ge=0.0, le=1.0)
```

**Worker/store require + 503** (detection lines 38–55; depth lines 25–36):
```python
def _require_worker(request: Request) -> Any:
    worker = _detection_worker(request)
    if worker is None:
        raise HTTPException(
            status_code=503,
            detail="detection worker not available",
        )
    return worker
```

**GET returns full snapshot; PATCH mutates cold path only** (detection lines 75–100; depth lines 39–68):
```python
@router.get("/api/detection/config")
async def get_detection_config(request: Request) -> dict[str, Any]:
    worker = _require_worker(request)
    payload: dict[str, Any] = {"conf": float(worker.get_conf())}
    # optional metadata...
    return payload

@router.patch("/api/detection/config")
async def patch_detection_config(
    body: DetectionConfigUpdate,
    request: Request,
) -> dict[str, Any]:
    worker = _require_worker(request)
    worker.set_conf(body.conf)
    return {"conf": float(worker.get_conf())}
```

**Apply to pipeline:**
- Read `pipeline_state` from `request.app.state` (not workers).
- PATCH: call `pipeline_state.update(**partial)`; validate `near_cut > mid_cut` → 422.
- Side-effect: push enable flags into loops (`loop.set_enabled`) and cutoffs into FreeSpaceLoop.
- Handlers never open cameras or run inference (same docstring contract as detection/depth).

**Validation of near>mid:** new for Phase 6 — raise `HTTPException(422, detail=...)` after Pydantic Field ranges, before applying.

---

### `src/sentry_ai/api/routes_open_vocab.py` (route, request-response)

**Analog:** `src/sentry_ai/api/routes_detection.py` (conf PATCH) + `routes_depth.py` (enum mode PATCH)

**Mode + conf body pattern** (depth Literal mode lines 17–22 + detection conf Field):
```python
class DepthConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    depth_mode: Literal["relative", "metric_indoor", "metric_outdoor"]
```

**Open-vocab config body should combine:**
```python
class OpenVocabConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str | None = None          # or classes: list[str]
    mode: Literal["off", "on_demand", "continuous"] | None = None
    conf: float | None = Field(default=None, ge=0.0, le=1.0)
    every_n: int | None = Field(default=None, ge=1, le=60)
```

**503 when worker missing** — copy `_require_worker` from detection (lines 48–55), detail `"open-vocab worker not available"`.

**POST `/api/open-vocab/run`** — no exact analog; closest is PATCH that only arms state (cold path). Pattern:
- Arm one-shot on OpenVocabLoop; do **not** call `worker.process` on request thread.
- Return 200/202 with `{mode, armed: true, classes: [...]}`.

**Security (from RESEARCH):** cap class count (≤32) and string length (≤64); strip empties before `set_prompt_classes`.

---

### `src/sentry_ai/control/pipeline_state.py` (utility, request-response)

**Analog:** thread-safe knobs from `YoloDetectionWorker` conf lock + `DepthAnythingWorker` mode lock + `PerceptionStore` lock discipline.

**Conf lock pattern** (`yolo_worker.py` lines 60–81):
```python
self._conf_lock = threading.Lock()
self._conf = self._validate_conf(conf)

def set_conf(self, conf: float) -> None:
    value = self._validate_conf(conf)
    with self._conf_lock:
        self._conf = value

def get_conf(self) -> float:
    with self._conf_lock:
        return self._conf
```

**Depth mode lock** (`depth/worker.py` lines 78–106):
```python
self._depth_mode_lock = threading.Lock()
self._depth_mode = depth_mode

def get_depth_mode(self) -> str:
    with self._depth_mode_lock:
        return self._depth_mode

def set_depth_mode(self, mode: str) -> None:
    if mode not in MODE_TO_MODEL:
        raise ValueError(...)
    with self._depth_mode_lock:
        self._depth_mode = mode
```

**Store lock + snapshot isolation** (`perception_store.py` lines 115–126, 167–182):
```python
def __init__(self) -> None:
    self._lock = threading.Lock()
    self._latest: DetectionProduct | None = None
    # ...

def snapshot(self) -> DetectionProduct | None:
    with self._lock:
        if self._latest is None:
            return None
        p = self._latest
        return DetectionProduct(...)  # isolated copy
```

**PipelineState shape (prescriptive, RESEARCH Pattern 1):**
```python
@dataclass
class PipelineState:
    _lock: threading.Lock = field(default_factory=threading.Lock)
    detection_enabled: bool = True
    depth_enabled: bool = True
    free_space_enabled: bool = True
    near_cut: float = 0.72  # DEFAULT_NEAR_CUT from free_space.py
    mid_cut: float = 0.45   # DEFAULT_MID_CUT

    def snapshot(self) -> dict: ...
    def update(self, **kwargs) -> dict: ...  # validate + lock; return full snapshot
```

Defaults source: `spatial/free_space.py` lines 32–33:
```python
DEFAULT_NEAR_CUT = 0.72
DEFAULT_MID_CUT = 0.45
```

---

### `src/sentry_ai/models/detection/yoloe_worker.py` (service, request-response)

**Analog:** `src/sentry_ai/models/detection/yolo_worker.py` (exact structural twin)

**Imports + defaults** (lines 1–24):
```python
from __future__ import annotations

import logging
import threading
from typing import Any

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.models.cache import configure_model_cache
from sentry_ai.models.detection.mapping import results_to_detections
from sentry_ai.schemas.perception import Detection

DEFAULT_CONF = 0.25
DEFAULT_IMGSZ = 640
DEFAULT_WEIGHTS = "yoloe-26s-seg.pt"  # Phase 6 default (not yolo26n.pt)
```

**Injectable model + conf lock + double-checked load** (lines 49–123):
```python
def __init__(
    self,
    weights: str = DEFAULT_WEIGHTS,
    conf: float = DEFAULT_CONF,
    device: str | None = None,
    model: Any | None = None,
) -> None:
    self._weights = weights
    self._device_arg = device
    self._device: str | None = None
    self._model = model
    self._conf_lock = threading.Lock()
    self._conf = self._validate_conf(conf)
    self._load_lock = threading.Lock()

def _ensure_model(self) -> Any:
    if self._model is not None:
        return self._model
    with self._load_lock:
        if self._model is not None:
            return self._model
        configure_model_cache()
        # Phase 6: from ultralytics import YOLOE  (not YOLO)
        ...
```

**process path** (lines 127–153) — keep predict kwargs contract:
```python
results = model.predict(
    source=image_bgr,
    conf=conf,
    imgsz=DEFAULT_IMGSZ,
    device=device,
    verbose=False,
    save=False,
)
if not results:
    return []
return results_to_detections(results[0])
```

**Phase 6 deltas only:**
1. Load `YOLOE(weights)` instead of `YOLO(weights)`.
2. Add prompt lock + `set_prompt_classes` / dirty flag; call `model.set_classes(classes)` only when dirty (not every frame).
3. Tag returned Detection with `source="open_vocab"` after mapping (once schema field exists).
4. Empty classes → return `[]` without predict.
5. `name = "yoloe-open-vocab"`; implement `ModelWorker` protocol (`plugins/protocols.py` lines 27–36).

**Reuse:** `results_to_detections` from `mapping.py` — boxes only; ignore masks for v1.

**resolve_device** — copy verbatim from `yolo_worker.py` lines 27–41.

---

### `src/sentry_ai/models/detection/open_vocab_loop.py` (service, event-driven)

**Analog:** `src/sentry_ai/models/detection/loop.py` (exact structural twin)

**Class skeleton + start/stop** (lines 21–69):
```python
class DetectionLoop:
    def __init__(self, bus: FrameBus, worker: Any, store: PerceptionStore) -> None:
        self._bus = bus
        self._worker = worker
        self._store = store
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_frame_id: int | None = None

    def start(self) -> None:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run, name="detection", daemon=True,
            )
            self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        # join timeout=5.0; clear _thread
```

**Keep-latest + error keep-alive** (lines 71–118):
```python
def _run(self) -> None:
    while not self._stop.is_set():
        frame = self._bus.get_latest()
        if frame is None or frame.frame_id == self._last_frame_id:
            self._stop.wait(0.005)
            continue
        t0 = time.perf_counter()
        try:
            dets = self._worker.process(frame)
            latency_ms = (time.perf_counter() - t0) * 1000.0
            self._last_frame_id = frame.frame_id
            self._store.set_detections(...)  # Phase 6: set_open_vocab instead
        except Exception as exc:  # noqa: BLE001 — keep thread alive
            logger.exception(...)
            self._store.set_detections(..., detections=[], error=str(exc))
```

**OpenVocabLoop deltas (RESEARCH Pattern 5):**
- Thread name `"open-vocab"`.
- Write **`store.set_open_vocab`** only — never `set_detections` (dual-writer anti-pattern).
- Modes: `off` / `on_demand` / `continuous` behind lock.
- `off`: sleep 10ms, no process (same as enable-gate).
- `on_demand`: process one latest frame when armed, then idle.
- `continuous`: process every `every_n` frames (default 3) or min interval.
- Add `_enabled` Event + `set_enabled` (shared Pattern below).

---

### Loop enable gates — DetectionLoop / DepthLoop / FreeSpaceLoop (service, event-driven)

**Analog base:** existing `_run` loops; enable gate is **new** but follows existing `_stop.wait` sleep pattern.

**Where to insert** (DetectionLoop `_run` top, lines 71–76):
```python
while not self._stop.is_set():
    # NEW: enable gate — pause without teardown
    if not self._enabled.is_set():
        self._stop.wait(0.01)
        continue
    frame = self._bus.get_latest()
    if frame is None or frame.frame_id == self._last_frame_id:
        self._stop.wait(0.005)
        continue
```

**set_enabled API (prescriptive):**
```python
def set_enabled(self, enabled: bool) -> None:
    if enabled:
        self._enabled.set()
    else:
        self._enabled.clear()
        # optional: clear stage product once so completeness/overlays drop
```

**Defaults:** `_enabled = threading.Event(); _enabled.set()` at init (stages on by default).

**Do not** call `loop.stop()` for UI toggles — only on serve shutdown (`cli.py` lines 428–435).

**FreeSpaceLoop cutoffs** (`spatial/loop.py` lines 85–108):
- Hold `near_cut` / `mid_cut` behind lock on FreeSpaceLoop.
- Pass into existing kwargs of `compute_free_space` (already accepts them — `free_space.py` lines 144–151):
```python
result = compute_free_space(
    depth.depth_map,
    kind=depth.kind,
    smoother=self._smoother,
    near_cut=self.get_near_cut(),  # NEW
    mid_cut=self.get_mid_cut(),    # NEW
)
```
- FreeSpaceLoop does **not** read FrameBus — only `store.snapshot_depth()` (line 87). Enable gate still applies before depth poll.

---

### `src/sentry_ai/state/perception_store.py` (store, CRUD)

**Analog:** existing FreeSpaceProduct fourth-slot pattern (lines 66–87, 278–352)

**Product dataclass pattern:**
```python
@dataclass
class FreeSpaceProduct:
    frame_id: int
    camera_id: str
    t_capture: float
    t_compute: float
    latency_ms: float
    # ... stage-specific fields
    error: str | None = None
```

**OpenVocabProduct should mirror DetectionProduct** (lines 28–39):
```python
@dataclass
class OpenVocabProduct:
    frame_id: int
    camera_id: str
    t_capture: float
    detections: list[Detection]
    latency_ms: float
    conf: float | None = None
    model_name: str | None = None
    prompt: str | None = None  # optional audit
    error: str | None = None
```

**set / snapshot / metrics** — copy `set_detections` / `snapshot` / FPS window (lines 128–182, 354–370):
- `set_open_vocab(...)` → `_latest_open_vocab`, `ov_frames`, `ov_fps`, `last_ov_latency_ms`
- `snapshot_open_vocab()` → isolated list copy
- `record_open_vocab_drop`
- Extend `StoreMetrics` with `ov_*` fields

**Clear on disable:** no `clear_*` exists today — either:
1. Add `clear_open_vocab()` / `clear_detections()` setting slot to None under lock, or
2. `set_*` with empty product + error=`"disabled"` once.

Prefer explicit clear methods for honest completeness (RESEARCH A4).

---

### `src/sentry_ai/api/assemble.py` (utility, transform)

**Analog:** self — merge path at lines 97–252

**Snapshot three products** (lines 110–115):
```python
det = store.snapshot()
depth = store.snapshot_depth()
free = store.snapshot_free_space()
# NEW: ov = store.snapshot_open_vocab()
```

**Completeness = presence** (lines 124–129, 243–247):
```python
det_present = det is not None
# NEW: detections complete if det OR ov present
completeness=Completeness(
    detections=det_present,  # extend: det_present or ov_present
    depth=depth_good,
    free_space=free_good,
)
```

**Detections list merge** (line 249):
```python
detections=list(det.detections) if det is not None else None
# NEW: fixed first, then OV (tag source); None only if both absent
```

**Stats** — append `ov_latency_ms`, `ov_fps`, `ov_age_ms`, `ov_stale` like det/depth/fs blocks (lines 139–200).

**TTL:** add `"open_vocab": 500.0` (or share detections TTL) in `DEFAULT_TTL_MS` (lines 28–32).

**Never attach bulk arrays** (comment line 213) — OV is boxes only; same rule.

---

### `src/sentry_ai/api/routes_preview.py` (route, request-response)

**Analog:** self — status telemetry (lines 78–137) + MJPEG draw order (lines 186–211)

**Status enrichment pattern:**
```python
if store is not None:
    product = store.snapshot()
    metrics = store.metrics_snapshot()
    if product is not None:
        data["detections_count"] = len(product.detections)
        data["det_latency_ms"] = product.latency_ms
    data["det_fps"] = metrics.det_fps
    # depth + free_space blocks already present
    # NEW: ov_fps, ov_latency_ms, ov_count, ov_mode from store + open_vocab_worker
```

**MJPEG draw order** (lines 190–211) — depth blend → free-space → detection boxes:
```python
image = blend_depth(...)
image = draw_free_space(...)
product = store.snapshot()
if product is not None:
    image = draw_detections(image, product.detections)
# NEW: ov = store.snapshot_open_vocab()
#      if ov: image = draw_detections(image, ov.detections)  # dual color via source
```

Alternatively assemble merged list once and call `draw_detections` once with source-colored boxes.

**Handlers never run inference** — docstring contract lines 1–9.

---

### `src/sentry_ai/models/detection/overlay.py` (utility, transform)

**Analog:** self (lines 18–51)

```python
_BOX_COLOR = (0, 255, 180)  # fixed-class cyan BGR
# NEW: _OV_BOX_COLOR = (255, 0, 255)  # magenta BGR for open-vocab

def draw_detections(image_bgr, detections):
    out = image_bgr.copy()
    for det in detections:
        color = _OV_BOX_COLOR if getattr(det, "source", "fixed") == "open_vocab" else _BOX_COLOR
        # optional label prefix "ov:" for open_vocab
        cv2.rectangle(out, (x1, y1), (x2, y2), color, _BOX_THICKNESS)
        ...
```

Keep pure OpenCV — no ultralytics import (module docstring).

---

### `src/sentry_ai/schemas/perception.py` (model, transform)

**Analog:** self — Detection (lines 48–55)

```python
class Detection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    class_name: str
    confidence: float
    bbox_xyxy: tuple[float, float, float, float] | list[float]
    # NEW additive optional field:
    source: Literal["fixed", "open_vocab"] = "fixed"
```

Keep `extra=forbid`. Default `"fixed"` so existing fixed-class paths need no change.  
PerceptionFrame stays perception-only — no motor fields (module docstring lines 8–9).

---

### `src/sentry_ai/api/app.py` + `deps.py` (config)

**Analog:** self

**create_app signature + state attach** (`app.py` lines 21–74):
```python
def create_app(
    *,
    bus: FrameBus,
    capture_loop: CaptureLoop,
    bind: str = "127.0.0.1:8000",
    perception_store: Any | None = None,
    detection_worker: Any | None = None,
    depth_worker: Any | None = None,
    # NEW:
    # open_vocab_worker: Any | None = None,
    # pipeline_state: Any | None = None,
    # open_vocab_loop: Any | None = None,  # only if routes need arm()
) -> FastAPI:
    ...
    app.include_router(preview_router)
    app.include_router(detection_router)
    app.include_router(depth_router)
    # NEW: pipeline_router, open_vocab_router
    app.include_router(v1_router)
```

**AppState dataclass** (`deps.py` lines 13–22):
```python
@dataclass
class AppState:
    bus: FrameBus
    capture_loop: CaptureLoop
    bind: str
    perception_store: Any | None = None
    detection_worker: Any | None = None
    depth_worker: Any | None = None
    # NEW: open_vocab_worker, pipeline_state
```

Caller owns loop lifecycle — `create_app` does not start threads (docstring line 32).

---

### `src/sentry_ai/cli.py` serve lifecycle (config, event-driven)

**Analog:** self lines 339–435

**Optional extra + ImportError soft-disable** (detection block lines 339–358):
```python
worker: Any | None = None
det_loop: Any | None = None
try:
    from sentry_ai.models.detection.loop import DetectionLoop
    from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
    configure_model_cache()
    worker = YoloDetectionWorker(weights=weights, conf=0.25)
    det_loop = DetectionLoop(bus, worker, store)
except ImportError as exc:
    typer.echo("detection disabled: detect extra not installed ...", err=True)
```

**Open-vocab wiring (same detect extra — no new ImportError gate required if YOLOE always in ultralytics):**
```python
# After det_loop setup; YOLOE uses same detect extra
ov_worker = YoloeOpenVocabWorker(weights="yoloe-26s-seg.pt", conf=0.25)
ov_loop = OpenVocabLoop(bus, ov_worker, store)  # default mode off
```

**Start/stop order** (lines 414–435):
```
# Start: capture → det → depth → free_space → open_vocab
# Stop reverse: free_space → depth → det → capture  (+ ov before free_space stop)
loop.start()
if det_loop: det_loop.start()
if depth_loop: depth_loop.start()
free_space_loop.start()
# NEW: ov_loop.start()  # thread alive; mode=off sleeps
```

Pass `pipeline_state`, workers, store into `create_app`.  
Stage toggles must **not** stop capture/serve.

---

### `src/sentry_ai/models/cache.py` (config)

**Analog:** self lines 12–19

```python
KNOWN_WEIGHTS: frozenset[str] = frozenset(
    {
        "yolo26n.pt",
        "yolo26s.pt",
        "yolo26m.pt",
        # NEW Phase 6:
        "yoloe-26s-seg.pt",
        "yoloe-26n-seg.pt",  # edge doc path
    }
)
```

`configure_model_cache` already points Ultralytics `weights_dir` at Sentry cache — YOLOE downloads land there automatically.

---

### `src/sentry_ai/ui/static/index.html` (component, request-response)

**Analog:** self — conf slider + status poll (lines 183–446)

**Debounced PATCH** (lines 207–208, 398–436):
```javascript
var STATUS_POLL_MS = 500;
var CONF_DEBOUNCE_MS = 150;

function patchConf(value) {
  fetch("/api/detection/config", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conf: value }),
  })
    .then(...)
    .catch(function () { /* non-fatal: status poll refreshes */ });
}

confSlider.addEventListener("input", function () {
  if (confFromServer) return;
  var v = parseFloat(confSlider.value);
  elConf.textContent = formatNum(v, 2);
  if (confTimer) clearTimeout(confTimer);
  confTimer = setTimeout(function () {
    confTimer = null;
    patchConf(v);
  }, CONF_DEBOUNCE_MS);
});
```

**Status poll + apply** (lines 377–396, 259–375):
```javascript
function pollStatus() {
  fetch("/api/status", { cache: "no-store" })
    .then(function (resp) { return resp.json(); })
    .then(function (data) { applyStatus(data); })
    .catch(...);
}
pollStatus();
setInterval(pollStatus, STATUS_POLL_MS);
```

**Phase 6 UI extensions (from 06-UI-SPEC layout):**
1. Stage checkboxes → debounced/immediate PATCH `/api/pipeline/config` `{detection_enabled, ...}`.
2. Free-space near/mid sliders → same pipeline PATCH (validate client-side near>mid; server 422 is source of truth).
3. Keep existing conf slider → still `/api/detection/config`.
4. Open-vocab: text input + Run button → PATCH/POST open-vocab config+run; continuous checkbox.
5. Footer telemetry: add `det_fps`, `depth_fps`, `free_space_fps`, `ov_ms`/`ov_fps` from status (fields mostly already on `/api/status` for det/depth/fs).
6. AGPL note: first OV Run may download weights (extend existing note lines 196–201).
7. No React rewrite; extend static HTML only.
8. No motor / safe-to-drive language.

**Server→UI sync flag pattern** (`confFromServer`) prevents slider feedback loops — reuse for stage toggles and cutoffs.

---

### Tests

#### `tests/test_pipeline_config.py` / `tests/test_api_open_vocab.py`

**Analog:** `tests/test_api_detection.py` + `tests/test_api_depth.py`

**Fake worker + create_app inject** (detection test lines 20–65):
```python
class FakeDetectionWorker:
    name = "fake-det"
    def __init__(self, conf: float = 0.25) -> None:
        self._conf = conf
    def set_conf(self, conf: float) -> None: ...
    def get_conf(self) -> float: ...
    def process(self, frame: Any) -> list[Detection]:
        return []  # handlers must never call process

def _app(*, store=None, worker=None, inject=True):
    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    bus = FrameBus()
    loop = CaptureLoop(source, bus)
    kwargs = {"bus": bus, "capture_loop": loop, "bind": "127.0.0.1:8000"}
    if inject:
        kwargs["perception_store"] = store or PerceptionStore()
        kwargs["detection_worker"] = worker or FakeDetectionWorker()
        # NEW: pipeline_state, open_vocab_worker
    return create_app(**kwargs), loop
```

**Assert handlers never call process** — depth FakeWorker raises `AssertionError` on process (`test_api_depth.py` lines 38–40).

**TestClient + finally loop.stop()** pattern throughout.

#### `tests/test_yoloe_worker.py`

**Analog:** `tests/test_detection_worker.py` FakeModel (lines 19–53)

```python
class FakeModel:
    def __init__(self, results=None):
        self.calls = []
        self.set_classes_calls = []  # NEW for YOLOE
        self._results = results

    def set_classes(self, classes, embeddings=None):
        self.set_classes_calls.append(list(classes))

    def predict(self, **kwargs):
        self.calls.append(kwargs)
        ...
```

Assert: `set_classes` once per prompt change, not every process; empty prompt → `[]`; conf applies next process; no weight download (inject model).

#### `tests/test_open_vocab_loop.py` / enable-gate tests

**Analog:** `tests/test_detection_loop.py` FakeDetectionWorker + `_wait_until` (lines 20–80)

```python
def _wait_until(predicate, *, timeout=2.0, interval=0.01) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return False
```

Assert: disabled → `process_calls` stays 0; re-enable resumes; on_demand runs once; continuous respects every_n; fixed DetectionLoop process_calls independent when OV runs.

#### `tests/test_assemble_open_vocab.py`

**Analog:** `tests/test_assemble_perception_frame.py` — seed store products, call `assemble_perception_frame`, assert merge order + `source` tags + completeness.

---

## Shared Patterns

### Cold-path control plane (no inference in handlers)

**Source:** `routes_detection.py` docstring lines 1–4; `routes_depth.py` lines 1–4  
**Apply to:** `routes_pipeline.py`, `routes_open_vocab.py`, all PATCH handlers

Handlers only mutate thread-safe flags/thresholds/prompts. Inference stays on daemon loop threads.

```python
"""Handlers only read PerceptionStore / call worker.set_conf.
They never open cameras or run model inference.
"""
```

### Thread-safe runtime knobs

**Source:** `yolo_worker.py` conf lock (lines 64–81); `depth/worker.py` mode lock (lines 91–106)  
**Apply to:** PipelineState, FreeSpaceLoop cutoffs, YoloeOpenVocabWorker prompt+conf, loop enable Events

Lock around read/write; validate before lock; next `process`/iteration sees new value.

### Daemon loop lifecycle (start idempotent / stop join)

**Source:** `DetectionLoop` / `DepthLoop` / `FreeSpaceLoop` start/stop  
**Apply to:** OpenVocabLoop + enable gates on existing loops

```python
# start: if alive return; clear stop; Thread(daemon=True).start()
# stop: stop.set(); join(timeout=5.0); _thread = None
# errors: except Exception keep thread alive; write error product
```

**UI toggle ≠ stop()** — only enable flag.

### Keep-latest FrameBus / store

**Source:** DetectionLoop lines 73–76; PerceptionStore set overwrites  
**Apply to:** OpenVocabLoop frame selection; OpenVocabProduct mailbox

Skip if `frame_id == _last_frame_id`; short `Event.wait(0.005)`.

### Injectable model for tests (no weight download)

**Source:** `YoloDetectionWorker(model=...)`; `tests/test_detection_worker.py` FakeModel  
**Apply to:** YoloeOpenVocabWorker; all OV unit tests

```python
worker = YoloDetectionWorker(model=FakeModel(), conf=0.25)
```

### AppState injection via create_app

**Source:** `app.py` + `deps.py` + `cli.py` serve  
**Apply to:** pipeline_state, open_vocab_worker on `app.state`

No process globals; TestClient injects fakes.

### Perception-only wire contracts

**Source:** `schemas/perception.py` extra=forbid; API-05  
**Apply to:** new Detection.source field; pipeline/OV JSON bodies; UI copy

No motor/velocity/command fields. Extend denylist tests if new routes add keys.

### Status + MJPEG from store truth (UI-06)

**Source:** `routes_preview.py`  
**Apply to:** OV telemetry on status; OV boxes on MJPEG

UI and `/v1` share PerceptionStore; never invent free-space or OV from raw depth.

### Serve lifecycle order

**Source:** `cli.py` lines 414–435  
**Apply to:** OpenVocabLoop registration

Start: capture → det → depth → free_space → open_vocab  
Stop: reverse. Capture always-on regardless of stage toggles.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| Open-vocab **mode scheduler** (`off`/`on_demand`/`continuous`) | service | event-driven | Existing loops are continuous keep-latest only; scheduler is new but built on DetectionLoop skeleton |
| Explicit product **clear** methods | store | CRUD | Store only has set/snapshot today; clear-on-disable is a small additive API |

Planner should use RESEARCH.md Patterns 2, 5, 6 for these; still mirror DetectionLoop/store isolation style.

---

## Anti-Patterns (do not copy)

| Anti-pattern | Why | Correct pattern |
|--------------|-----|-----------------|
| UI hide-only toggles | Violates UI-03 | Enable gate skips `worker.process` |
| `loop.stop()`/`start()` per toggle | Join races, GPU thrash | `_enabled` Event for serve lifetime |
| OV + fixed both call `set_detections` | Writer thrash | `OpenVocabProduct` + assemble merge |
| `set_classes` every frame | CLIP encode cost | Dirty-flag once per prompt change |
| Inference in FastAPI handler | Blocks event loop | Arm loop; process on worker thread |
| React/Vite rewrite | CONTEXT deferred | Extend `ui/static/index.html` |
| New pip package for YOLOE | Already in detect extra | Same ultralytics install |

---

## Metadata

**Analog search scope:**  
`src/sentry_ai/api/`, `models/detection/`, `models/depth/`, `spatial/`, `state/`, `schemas/`, `ui/static/`, `cli.py`, `plugins/`, `tests/test_api_*.py`, `tests/test_detection_*.py`, `tests/test_depth_*.py`, `tests/test_cli_serve.py`

**Files scanned:** ~35 source + 12 test analogs  
**Pattern extraction date:** 2026-08-08  

**Key analog files (primary copy sources):**
1. `src/sentry_ai/api/routes_detection.py` — GET/PATCH config control plane  
2. `src/sentry_ai/models/detection/yolo_worker.py` — injectable worker + conf lock  
3. `src/sentry_ai/models/detection/loop.py` — daemon keep-latest loop  
4. `src/sentry_ai/state/perception_store.py` — multi-product mailbox + metrics  
5. `src/sentry_ai/ui/static/index.html` — debounced PATCH + status poll console  

---

## PATTERN MAPPING COMPLETE

**Phase:** 6 - Developer Controls & Open-Vocab  
**Files classified:** 22  
**Analogs found:** 20 / 22  

### Coverage
- Files with exact analog: 8  
- Files with role-match / self-extend analog: 12  
- Files with no close analog: 2 (OV scheduler modes; store clear API — still patterned on loops/store)

### Key Patterns Identified
- All cold-path config routes: FastAPI `APIRouter` + Pydantic `extra=forbid` + Field ranges + 503 if dependency missing; never run inference  
- Runtime knobs: `threading.Lock` + get/set (conf, mode, cuts, enable Event)  
- Stage workers: daemon loops with keep-latest FrameBus, error-keep-alive, start/stop join — **add enable gate, do not tear down**  
- Open-vocab: structural twin of YoloDetectionWorker + DetectionLoop writing a **fourth store product**; assemble merges with `Detection.source`  
- Live Preview: extend static HTML conf-slider + 500ms status poll; debounced PATCH for thresholds  
- Tests: inject FakeModel/FakeWorker via create_app; never download YOLOE weights in CI  

### File Created
`.planning/phases/06-developer-controls-open-vocab/06-PATTERNS.md`

### Ready for Planning
Pattern mapping complete. Planner can now reference analog patterns in PLAN.md files.
