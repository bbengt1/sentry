# Phase 2: Camera Ingest & Live Preview - Research

**Researched:** 2026-08-07  
**Domain:** OpenCV camera capture, keep-latest frame bus, FastAPI MJPEG live preview  
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Sources write to **Frame Bus only**; workers never open cameras
- **Keep-latest** drop policy; never unbounded capture queues
- **UI is a subscriber**, not on the inference hot path
- Single camera first; `camera_id` already on Frame
- Localhost default bind
- OpenCV headless first; PyAV/GStreamer when RTSP needs it
- MJPEG/WS JPEG preview first; WebRTC later if lag hurts
- Phase 1 package: `sentry-ai` / `sentry_ai`, CLI `sentry`

### From Phase 1 shipped code (must respect)
- `CameraSource` protocol: `open()`, `read() -> Frame`, `close()`, `name`
- `Frame` has `frame_id`, `camera_id`, `t_capture`, optional `t_ingest`, `width`/`height`
- Plugin registry + entry points for sources
- Built-in `synthetic` source exists as stub — upgrade or replace with real synthetic that can feed bus

### Claude's Discretion
- Whether Frame gains `image_jpeg: bytes` / numpy buffer vs separate `FrameBuffer` type
- Threading model: capture thread + async FastAPI vs all asyncio
- Static HTML vs minimal Vite for preview page (research recommended MJPEG/WS first — lean HTML is OK for Phase 2)
- Exact reconnect backoff policy
- Whether `sentry serve` / `sentry preview` is the CLI entry for the server

### Deferred Ideas (OUT OF SCOPE)
- Detection / depth / free-space → Phases 3–5
- Interactive controls / open-vocab → Phase 6
- Full `/v1` perception stream → Phase 5
- WebRTC → post-v1 if needed
- Edge packaging → Phase 7
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CAM-01 | USB UVC capture via OpenCV (or equivalent) | `OpenCVSource` with `VideoCapture(index)`; CAP_PROP buffer=1; MJPG fourcc preferred |
| CAM-02 | File / video sources for local dev and CI | `OpenCVSource` with path; fixture MP4/AVI under `tests/fixtures/` |
| CAM-03 | Synthetic frame source for automated tests | Upgrade `SyntheticSource` to emit patterned numpy BGR + identity `Frame` |
| CAM-04 | Network/IP cameras (RTSP) | OpenCV URL open first; document latency/drop limits; PyAV optional later |
| CAM-05 | Frame bus keep-latest + drop/FPS metrics | `FrameBus` mailbox depth 1; `frames_dropped`, `capture_fps` counters |
| CAM-06 | Disconnect/reconnect with clear error state | Capture loop status enum + exponential backoff; API + HTML status pill |
| UI-01 | Web dashboard shows live camera video | FastAPI `GET /preview/mjpeg` + static `index.html` `<img>` |
| MODEL-03 | Default bind localhost; remote opt-in | Uvicorn `host=127.0.0.1` default; `--host 0.0.0.0` documented opt-in |
</phase_requirements>

## Summary

Phase 2 proves the realtime skeleton: commodity cameras (USB, file, synthetic, RTSP-best-effort) feed a **keep-latest Frame Bus**, and a **localhost FastAPI** process serves an MJPEG live preview with status/FPS/drops — **no ML**. Phase 1 left `Frame` as identity-only (no numpy) and `CameraSource.read() -> Frame`. The main design move is to introduce a **runtime image container** (`ImageFrame`) without polluting the Pydantic wire contract, evolve the protocol to return it, and run blocking OpenCV I/O on a **dedicated capture thread** while FastAPI’s asyncio loop only reads bus state and streams JPEG.

OpenCV headless is sufficient for USB + file + basic RTSP. Do **not** pull PyAV/GStreamer in Phase 2 unless OpenCV RTSP fails a documented smoke path — stack research already ranks OpenCV first and PyAV as upgrade. Uvicorn’s default bind is already `127.0.0.1` (MODEL-03). Preview transport is MJPEG multipart via `StreamingResponse` into a single static HTML page (UI-SPEC).

**Primary recommendation:** Implement `ImageFrame` + `FrameBus` + OpenCV sources + capture thread + `sentry serve` with FastAPI MJPEG/static UI; keep `Frame` identity schema stable; treat RTSP as OpenCV-first with honest latency-class docs.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| USB / file / RTSP / synthetic capture | API / Backend (capture thread) | — | Blocking OpenCV I/O; never in request handlers |
| Frame identity (`frame_id`, timestamps) | API / Backend | — | Shared schema; set at source + bus ingest |
| Image payload (BGR ndarray) | API / Backend (runtime only) | — | Hot-path arrays; not a wire/Pydantic field |
| Keep-latest Frame Bus + drop metrics | API / Backend | — | Process-local mailbox; single-camera v1 |
| Reconnect / source status | API / Backend | Browser / Client (display) | Status owned by capture loop; UI reads it |
| MJPEG encode + stream | API / Backend (async) | Browser / Client (`<img>`) | Server encodes JPEG from latest bus frame |
| Live preview HTML | CDN / Static (packaged static) | Browser / Client | Served by FastAPI `StaticFiles` / HTMLResponse |
| CLI `sentry serve` | API / Backend | — | Typer entry starts capture + uvicorn |
| Bind address policy (localhost) | API / Backend | — | MODEL-03; no auth in Phase 2 |
| Automated tests (no hardware) | API / Backend | — | Synthetic + file fixtures; TestClient |

## Standard Stack

### Core

| Library | Version (verified 2026-08-07) | Purpose | Why Standard |
|---------|------------------------------|---------|--------------|
| Python | **3.11+** (project requires) | Runtime | Phase 1 lock; Jetson/Pi wheels mature [CITED: STACK.md] |
| **opencv-python-headless** | **4.14.0.94** (latest 4.x; 5.0.0.93 also on PyPI) | USB/file/RTSP capture, `imencode` JPEG | Official headless wheels; no GUI deps [VERIFIED: PyPI] |
| **numpy** | **≥2.0,<2.5** (e.g. **2.4.6**; 2.5.x requires Python ≥3.12) | BGR arrays, synthetic patterns | Required by OpenCV Python bindings [VERIFIED: PyPI] |
| **fastapi** | **0.141.1** | REST + StreamingResponse MJPEG | Project stack; async web [VERIFIED: PyPI] |
| **uvicorn[standard]** | **0.52.1** | ASGI server | Default host `127.0.0.1` [CITED: uvicorn.dev/settings] |
| pydantic | already **≥2.13,<3** | Schemas / status models | Phase 1 dependency |
| typer | already **≥0.27** | `sentry serve` CLI | Phase 1 CLI |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **httpx** | **0.28.1** | ASGI TestClient + integration tests | pytest against FastAPI app [VERIFIED: PyPI] |
| **python-multipart** | **0.0.32** | FastAPI form/multipart support | Prefer transitively; pin if forms added [VERIFIED: PyPI] |
| **pillow** | **12.3.0** | Optional image helpers | **Not required** if `cv2.imencode` used [VERIFIED: PyPI] |
| **av** (PyAV) | **18.0.0** | Advanced RTSP demux | **Defer** unless OpenCV RTSP inadequate [VERIFIED: PyPI] |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| OpenCV RTSP | PyAV / GStreamer | Better reliability/latency control; heavier install & DX cost — Phase 2 upgrade path only |
| MJPEG | WebSocket JPEG frames | Slightly more client JS; same encode cost — MJPEG wins for zero-build HTML |
| MJPEG | WebRTC (aiortc) | Lower lag; ICE/codec complexity — deferred per CONTEXT |
| Capture thread | Pure asyncio `run_in_executor` only | Works but bus ownership still needs a producer loop; dedicated thread is clearer |
| Vite/React preview | Static HTML | Phase 2 UI-SPEC allows static; React is Phase 5–6 overlay surface |
| numpy on Pydantic `Frame` | Separate `ImageFrame` | Avoids `extra=forbid` / serialization / optional-dep breakage — **recommended** |

**Installation (Phase 2 deps to add to `pyproject.toml`):**

```bash
# Prefer uv (project standard)
uv add "opencv-python-headless>=4.10,<6" "numpy>=2.0,<2.5" "fastapi>=0.141,<1" "uvicorn[standard]>=0.52,<1"
uv add --dev "httpx>=0.28"
```

**Pin guidance:**
- Prefer **OpenCV 4.14.x** for Phase 2 stability (5.0.0.93 is new as of 2026-07; API still VideoCapture-compatible, but edge/Jetson ecosystems often lag on major bumps). Allow `<6` so 5.x installs if needed. [ASSUMED: Jetson/OpenCV 5 maturity not re-validated this session]
- Cap **numpy &lt;2.5** so Python 3.11 remains installable (numpy 2.5.1 requires ≥3.12). [VERIFIED: PyPI]

## Package Legitimacy Audit

> slopcheck was **not available** in this environment. Packages below are long-standing ecosystem libraries confirmed on PyPI with official docs/source. Planner may treat them as approved installs; if project policy requires slopcheck, re-run before merge.

| Package | Registry | Age (approx) | Source Repo | slopcheck | Disposition |
|---------|----------|--------------|-------------|-----------|-------------|
| opencv-python-headless | PyPI | ~8 yrs (first 2018) | github.com/opencv/opencv-python | N/A | Approved |
| numpy | PyPI | ~20 yrs | github.com/numpy/numpy | N/A | Approved |
| fastapi | PyPI | ~7 yrs | github.com/fastapi/fastapi | N/A | Approved |
| uvicorn | PyPI | ~9 yrs | github.com/Kludex/uvicorn | N/A | Approved |
| httpx | PyPI | ~6 yrs | github.com/encode/httpx | N/A | Approved |
| python-multipart | PyPI | ~13 yrs | github.com/Kludex/python-multipart | N/A | Approved (optional pin) |
| pillow | PyPI | ~16 yrs | github.com/python-pillow/Pillow | N/A | Optional — not required |
| av (PyAV) | PyPI | mature | PyAV project | N/A | **Not installed in Phase 2** |

**Packages removed due to slopcheck [SLOP]:** none  
**Packages flagged [SUS]:** none  
**Deferred install:** `av` (PyAV) — only if RTSP path fails OpenCV acceptance criteria.

## Architecture Patterns

### System Architecture Diagram

```
┌──────────────────┐
│ CameraSource     │  open/read/close (blocking)
│ USB | File |     │
│ Synthetic | RTSP │
└────────┬─────────┘
         │ ImageFrame { Frame identity + image_bgr }
         ▼
┌──────────────────┐     status: streaming|reconnecting|error
│ Capture Loop     │──── metrics: capture_fps, frames_dropped
│ (daemon thread)  │
└────────┬─────────┘
         │ publish keep-latest (overwrite slot)
         ▼
┌──────────────────┐
│ FrameBus         │  depth=1 mailbox + Lock
│ get_latest()     │  frame_id monotonic (source-owned or bus-owned)
└────────┬─────────┘
         │ non-blocking read
         ▼
┌──────────────────┐     ┌─────────────────────────────┐
│ FastAPI (asyncio)│────▶│ Browser                     │
│ GET /            │ HTML│  status pill + FPS/drops    │
│ GET /preview/mjpeg ───▶│  <img src="/.../mjpeg">      │
│ GET /api/status  │ JSON│                             │
└──────────────────┘     └─────────────────────────────┘
         host default: 127.0.0.1 (MODEL-03)
```

**Rules (from ARCHITECTURE.md — enforce in plan):**
1. Sources → Frame Bus only (never wire models/UI to `VideoCapture` directly).
2. UI is a pure subscriber; never backpressure capture.
3. Workers (Phase 3+) read bus; they do not open cameras.

### Recommended Project Structure

```
src/sentry_ai/
├── schemas/
│   └── frame.py              # KEEP identity-only Frame (Phase 1)
├── capture/                  # NEW — runtime frame types + loop
│   ├── __init__.py
│   ├── image_frame.py        # ImageFrame dataclass
│   ├── status.py             # SourceStatus enum + metrics snapshot
│   └── loop.py               # CaptureLoop thread + reconnect
├── bus/                      # NEW
│   ├── __init__.py
│   └── frame_bus.py          # FrameBus keep-latest
├── sources/                  # NEW — real implementations
│   ├── __init__.py
│   ├── opencv_source.py      # USB index | file path | RTSP URL
│   ├── synthetic.py          # patterned BGR synthetic (moves/upgrade from builtins)
│   └── errors.py             # SourceError, SourceDisconnected
├── api/                      # NEW
│   ├── __init__.py
│   ├── app.py                # create_app(bus, loop) factory
│   ├── routes_preview.py     # /preview/mjpeg, /api/status, /
│   └── deps.py               # app state holders
├── ui/
│   └── static/
│       └── index.html        # Live Preview (UI-SPEC)
├── plugins/
│   ├── protocols.py          # EVOLVE CameraSource.read() -> ImageFrame
│   ├── builtins.py           # re-export or thin wrappers
│   └── registry.py           # register usb/file/rtsp/synthetic entry points
└── cli.py                    # add `serve` command

tests/
├── fixtures/
│   └── sample_clip.mp4       # short generated or committed clip
├── test_sources_synthetic.py
├── test_sources_file.py
├── test_frame_bus.py
├── test_capture_loop_reconnect.py
├── test_api_preview.py
└── test_cli_serve.py
```

**Align with ARCHITECTURE.md logical layout** (`sources/`, `bus/`, `api/`, `ui/`) while keeping Phase 1 modules (`schemas/`, `plugins/`, `config/`) intact.

### Pattern 1: Runtime ImageFrame (do not stuff numpy into Pydantic Frame)

**What:** Keep `Frame` as identity/wire metadata. Add a process-local container for pixels.

**When to use:** Always on the hot path (capture → bus → preview → future workers).

**Example:**

```python
# Recommended internal type (not a Pydantic model)
from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from sentry_ai.schemas.frame import Frame

@dataclass(slots=True)
class ImageFrame:
    """Hot-path frame: schema identity + BGR uint8 image."""

    meta: Frame
    image_bgr: np.ndarray  # HxWx3 uint8, contiguous preferred

    @property
    def frame_id(self) -> int:
        return self.meta.frame_id

    @property
    def camera_id(self) -> str:
        return self.meta.camera_id
```

**Why not `image_jpeg: bytes` on `Frame`:** Preview needs JPEG, but Phase 3+ workers need BGR arrays. Encoding on every capture for bus storage wastes CPU; encode at the MJPEG edge. JPEG-on-Frame also bloats the identity contract and forces optional fields through `extra="forbid"` evolution carefully.

**Why not numpy field on Pydantic Frame:** Phase 1 intentionally avoided numpy deps; `model_dump`/JSON paths break; `extra="forbid"` tests must stay green for identity-only construction.

### Pattern 2: Keep-latest FrameBus

**What:** Single-slot mailbox with lock; publish overwrites; get returns latest or None.

**When to use:** Capture → any consumer (preview now; workers later).

```python
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field

from sentry_ai.capture.image_frame import ImageFrame

@dataclass
class BusMetrics:
    frames_published: int = 0
    frames_dropped: int = 0  # overwrites of unread frames
    last_publish_t: float | None = None
    capture_fps: float = 0.0

class FrameBus:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._latest: ImageFrame | None = None
        self._metrics = BusMetrics()
        self._fps_window_t0 = time.monotonic()
        self._fps_count = 0

    def publish(self, frame: ImageFrame) -> None:
        with self._lock:
            if self._latest is not None:
                # Keep-latest: previous unread frame is dropped
                self._metrics.frames_dropped += 1
            self._latest = frame
            self._metrics.frames_published += 1
            self._metrics.last_publish_t = time.time()
            self._fps_count += 1
            now = time.monotonic()
            dt = now - self._fps_window_t0
            if dt >= 1.0:
                self._metrics.capture_fps = self._fps_count / dt
                self._fps_count = 0
                self._fps_window_t0 = now

    def get_latest(self) -> ImageFrame | None:
        with self._lock:
            return self._latest

    def metrics_snapshot(self) -> BusMetrics:
        with self._lock:
            return BusMetrics(**self._metrics.__dict__)
```

**Drop semantics note:** Count a drop when a publish overwrites a frame that no consumer has “claimed,” **or** simpler and acceptable for Phase 2: count every overwrite (publish while slot occupied). Document the definition in `/api/status`. Prefer **overwrite-count** for simplicity — it matches “never process backlog.”

### Pattern 3: Capture thread + reconnect

**What:** Daemon thread calls `source.read()` in a loop, publishes to bus, handles failures with backoff without freezing UI status.

**When to use:** Always for live serve; tests can drive bus without the thread.

```python
# Pseudocode — reconnect policy (recommended defaults)
# initial_backoff=0.25s, max_backoff=5.0s, factor=2.0
# on read failure / empty frame:
#   set status=RECONNECTING, clear or freeze last frame policy = KEEP_LAST_WITH_STALE_FLAG
#   close source, sleep backoff, open source, reset backoff on success
# on open failure:
#   status=ERROR until first successful open, then RECONNECTING
```

**OpenCV open patterns** [CITED: docs.opencv.org VideoCapture tutorial]:

```python
import cv2

# USB UVC
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # reduce driver queue latency when supported

# File
cap = cv2.VideoCapture("/path/to/clip.mp4")

# RTSP / IP (URL scheme is camera-specific)
cap = cv2.VideoCapture("rtsp://user:pass@host:554/stream")

if not cap.isOpened():
    raise RuntimeError("cannot open source")

ok, bgr = cap.read()
if not ok or bgr is None:
    # disconnect / EOF
    ...
```

### Pattern 4: FastAPI MJPEG + static HTML

**What:** `StreamingResponse` yields multipart JPEG parts; page uses `<img src="//preview/mjpeg">`.

```python
# Source: FastAPI StreamingResponse docs
# https://fastapi.tiangolo.com/advanced/custom-response/
import asyncio
import cv2
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse

BOUNDARY = "frame"

async def mjpeg_generator(bus, jpeg_quality: int = 80):
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
                    b"--" + BOUNDARY.encode() + b"\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + chunk + b"\r\n"
                )
        await asyncio.sleep(0.033)  # ~30 FPS cap for UI path; independent of capture

@app.get("/preview/mjpeg")
async def preview_mjpeg():
    return StreamingResponse(
        mjpeg_generator(bus),
        media_type=f"multipart/x-mixed-replace; boundary={BOUNDARY}",
    )
```

**Bind defaults (MODEL-03):**

```python
# Uvicorn default host is already 127.0.0.1 [CITED: uvicorn.dev/settings]
uvicorn.run(app, host="127.0.0.1", port=8000)
# Opt-in LAN: host="0.0.0.0" via CLI flag --host, document privacy warning
```

### Pattern 5: CLI one-command path

**Recommended command name:** `sentry serve` (not `preview` alone — serve implies API+UI; aligns with future headless `serve --no-ui` in Phase 7).

```bash
# Synthetic (CI / default smoke path)
uv run sentry serve --source synthetic --port 8000

# USB
uv run sentry serve --source usb --device 0

# File
uv run sentry serve --source file --path tests/fixtures/sample_clip.mp4

# RTSP
uv run sentry serve --source rtsp --url "rtsp://..."

# Remote bind (opt-in)
uv run sentry serve --source synthetic --host 0.0.0.0  # warn in help text
```

### Anti-Patterns to Avoid

- **OpenCV capture inside FastAPI request handlers:** Blocks event loop; multi-consumer breaks.
- **Unbounded `queue.Queue` of frames:** Latency spiral (PITFALLS + ARCHITECTURE).
- **Putting numpy on Pydantic `Frame`:** Breaks Phase 1 identity tests / deps boundary.
- **Default `--host 0.0.0.0`:** Camera stream LAN exposure without auth (PITFALLS security).
- **Vite/React mandatory for Phase 2:** Scope creep; UI-SPEC allows static HTML.
- **WebRTC in Phase 2:** Deferred.
- **Processing every frame “to be safe”:** Violates keep-latest.
- **Silent freeze on disconnect:** Must surface RECONNECTING/ERROR (CAM-06).
- **Calling file EOF a permanent ERROR without policy:** File source should loop (dev) or stop cleanly with status — **recommend loop=True for serve demos**, stop with ERROR for one-shot tools.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Camera I/O | Custom V4L2 ctypes | OpenCV `VideoCapture` | Backend matrix (AVFoundation/V4L2/MSMF/FFmpeg) already solved |
| JPEG encode | Manual DCT | `cv2.imencode(".jpg", ...)` | Fast, zero extra deps |
| HTTP streaming | Raw sockets | FastAPI `StreamingResponse` | Cancellation, headers, ASGI integration |
| ASGI server | Custom | Uvicorn | Defaults + websockets later |
| Config validation | ad-hoc dicts | Existing Pydantic `SentryConfig` + CLI options | Phase 1 already has profiles |
| Plugin discovery | import-all hacks | Existing registry + entry points | FOUND-04 contract |
| Low-latency buffer trim | Busy-loop double read only | `CAP_PROP_BUFFERSIZE=1` + keep-latest bus | Driver + app-level both needed |

**Key insight:** Phase 2 complexity is **concurrency and failure modes**, not algorithms. Prefer boring OpenCV + a 20-line mailbox over a custom media stack.

## Common Pitfalls

### Pitfall 1: Unbounded capture queues
**What goes wrong:** Latency grows; robot/UI act on ancient frames.  
**Why:** “Don’t drop frames” instinct.  
**How to avoid:** Mailbox depth 1; metrics for drops.  
**Warning signs:** Memory climb; `t_capture` age ≫ frame period.

### Pitfall 2: OpenCV buffer backlog (USB)
**What goes wrong:** Even with keep-latest app queue, driver holds 4–10 frames → 100–300 ms lag.  
**Why:** Default capture buffers.  
**How to avoid:** `CAP_PROP_BUFFERSIZE=1` where supported; optional grab/retrieve double-read on reconnect.  
**Warning signs:** Preview “feels delayed” while FPS looks fine.

### Pitfall 3: RTSP treated as USB-class latency
**What goes wrong:** Makers expect 30 ms; IP cameras add 100–500 ms + GOP delay.  
**Why:** H.264 buffering, Wi-Fi, OpenCV FFmpeg defaults.  
**How to avoid:** Label source latency class in status/docs (`usb` | `file` | `rtsp_lan` | `rtsp_wifi`); document known limits for CAM-04.  
**Warning signs:** Frozen last keyframe on Wi-Fi drop without ERROR state.

### Pitfall 4: Blocking OpenCV on asyncio loop
**What goes wrong:** All HTTP freezes during `read()`.  
**Why:** Putting capture in async def without a thread/executor.  
**How to avoid:** Dedicated capture thread; async only polls bus.  
**Warning signs:** `/api/status` hangs under load.

### Pitfall 5: Default bind `0.0.0.0`
**What goes wrong:** Household camera exposed on LAN; later port-forwarded.  
**Why:** Copy-paste uvicorn tutorials.  
**How to avoid:** Hard-default `127.0.0.1`; require explicit `--host` for remote; README warning.  
**Warning signs:** Docs show `0.0.0.0` as first example.

### Pitfall 6: Protocol break without test updates
**What goes wrong:** Phase 1 tests expect `read() -> Frame`.  
**Why:** Image payload needs a different return type.  
**How to avoid:** Evolve Protocol deliberately; update registry/synthetic tests in same plan wave.  
**Warning signs:** `isinstance(frame, Frame)` fails after ImageFrame wrap.

### Pitfall 7: File source ends mid-demo
**What goes wrong:** Preview goes black at EOF; looks like a crash.  
**Why:** `ret=False` at end of file.  
**How to avoid:** `loop=True` default for file source in `serve`; expose `--no-loop` for one-shot.  
**Warning signs:** Drops spike once then permanent ERROR.

### Pitfall 8: MJPEG without sleep/await
**What goes wrong:** Generator spins CPU; cancellation broken.  
**Why:** Tight loop with no `await`.  
**How to avoid:** `await asyncio.sleep(...)`; follow FastAPI stream cancellation notes.  
**Warning signs:** 100% CPU with one browser tab.

## Code Examples

### Synthetic source (CAM-03)

```python
import time
import numpy as np
from sentry_ai.schemas.frame import Frame
from sentry_ai.capture.image_frame import ImageFrame

class SyntheticSource:
    name = "synthetic"

    def __init__(self, camera_id: str = "synthetic0", width: int = 640, height: int = 480, fps: float = 30.0):
        self.camera_id = camera_id
        self.width = width
        self.height = height
        self.fps = fps
        self._next_id = 0
        self._open = False

    def open(self) -> None:
        self._open = True
        self._next_id = 0

    def read(self) -> ImageFrame:
        if not self._open:
            raise RuntimeError("not open")
        # Moving bar / frame_id watermark — deterministic for tests
        img = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        x = (self._next_id * 8) % self.width
        img[:, x : min(x + 16, self.width)] = (0, 255, 0)
        now = time.time()
        meta = Frame(
            frame_id=self._next_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=self.width,
            height=self.height,
        )
        self._next_id += 1
        if self.fps > 0:
            time.sleep(1.0 / self.fps)
        return ImageFrame(meta=meta, image_bgr=img)

    def close(self) -> None:
        self._open = False
```

### OpenCV multi-source adapter (CAM-01/02/04)

```python
import time
import cv2
from sentry_ai.schemas.frame import Frame
from sentry_ai.capture.image_frame import ImageFrame

class OpenCVSource:
    """One class for usb index, file path, or RTSP URL."""

    def __init__(
        self,
        target: int | str,
        *,
        camera_id: str,
        name: str = "opencv",
        loop_file: bool = True,
    ) -> None:
        self.target = target
        self.camera_id = camera_id
        self.name = name
        self.loop_file = loop_file
        self._cap: cv2.VideoCapture | None = None
        self._next_id = 0
        self._is_file = isinstance(target, str) and not str(target).startswith(
            ("rtsp://", "rtsps://", "http://", "https://")
        )

    def open(self) -> None:
        self._cap = cv2.VideoCapture(self.target)
        if not self._cap.isOpened():
            raise RuntimeError(f"failed to open source: {self.target!r}")
        # Best-effort low latency (may be ignored by some backends)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self._next_id = 0

    def read(self) -> ImageFrame:
        assert self._cap is not None
        ok, bgr = self._cap.read()
        if not ok or bgr is None:
            if self._is_file and self.loop_file:
                self._cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ok, bgr = self._cap.read()
            if not ok or bgr is None:
                raise SourceDisconnected(f"no frame from {self.target!r}")
        h, w = bgr.shape[:2]
        now = time.time()
        meta = Frame(
            frame_id=self._next_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=w,
            height=h,
        )
        self._next_id += 1
        return ImageFrame(meta=meta, image_bgr=bgr)

    def close(self) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None
```

### Protocol evolution (Phase 1 → Phase 2)

```python
# protocols.py — recommended Phase 2 shape
@runtime_checkable
class CameraSource(Protocol):
    name: str
    def open(self) -> None: ...
    def read(self) -> ImageFrame: ...  # was Frame
    def close(self) -> None: ...
```

**Compatibility strategy:**
- Update Phase 1 tests that assumed `isinstance(..., Frame)` to unwrap `ImageFrame.meta` or assert `ImageFrame`.
- Keep constructing bare `Frame(...)` valid for schema unit tests (no image required).
- Entry points: `synthetic`, `usb`, `file`, `rtsp` (rtsp can share `OpenCVSource` factory).

### Status API shape (CAM-06 + UI-SPEC)

```json
{
  "source": "synthetic",
  "camera_id": "synthetic0",
  "status": "streaming",
  "status_detail": null,
  "frame_id": 128,
  "capture_fps": 29.4,
  "frames_dropped": 3,
  "bind": "127.0.0.1:8000",
  "t_capture": 1720000000.123
}
```

`status` enum: `starting` | `streaming` | `reconnecting` | `error` | `stopped`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Identity-only `Frame` (Phase 1) | `Frame` + runtime `ImageFrame` | Phase 2 | Enables pixels without schema pollution |
| Stub synthetic (no image) | Patterned BGR synthetic | Phase 2 | Real CI preview path |
| No server | FastAPI + Uvicorn localhost | Phase 2 | UI-01 / MODEL-03 |
| OpenCV GUI demos | Headless + browser MJPEG | Ongoing maker stacks | Server-friendly, remote-dev later |
| GStreamer-first robotics | OpenCV first, GStreamer upgrade | STACK research 2026-08-07 | Faster maker DX |

**Deprecated/outdated for this phase:**
- Streamlit/Gradio as product UI — rejected in STACK.
- WebRTC-first preview — deferred.
- Kafka/Redis bus — overkill single process.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | OpenCV 4.14 is safer default than 5.0 for multi-target later | Standard Stack | May need pin tweak; API likely compatible either way |
| A2 | `CAP_PROP_BUFFERSIZE=1` works on most USB backends | Pitfalls / OpenCV | Some backends ignore it — lag remains until double-grab workaround |
| A3 | Overwrite-count is an acceptable drop metric definition | FrameBus | Metric semantics may need rename later (`frames_overwritten`) |
| A4 | File source should loop by default in `serve` | Pitfalls | Demo UX preference; CLI flag covers alternative |
| A5 | JPEG quality 70–85 is fine for Phase 2 preview | MJPEG | Bandwidth/CPU tradeoff only |
| A6 | No auth required on localhost Phase 2 | Security | Acceptable for MODEL-03; LAN opt-in still unauthenticated unless documented |

## Open Questions

1. **Exact drop metric definition**
   - What we know: Keep-latest requires counting lost frames under load.
   - What's unclear: Overwrite count vs “unread overwrite only.”
   - **Recommendation (default):** Count every publish that replaces a non-None slot; expose as `frames_dropped`. Document in API.

2. **Who owns `frame_id` monotonic counter?**
   - What we know: Must be stable and increasing per camera.
   - What's unclear: Source-local vs bus-assigned.
   - **Recommendation:** Source-owned (reset on `open()` is OK); bus does not renumber. Multi-cam later stays namespaced by `camera_id`.

3. **RTSP acceptance bar for CAM-04**
   - What we know: Requirement allows “works or documented known limits.”
   - What's unclear: Whether CI must hit a live RTSP.
   - **Recommendation:** Unit-test URL construction + mock/failure path; manual/doc matrix for real cameras; no live RTSP in CI. Ship OpenCV path; add PyAV only if makers hit hard failures.

4. **Stale frame on disconnect**
   - What we know: UI must not silently look “live forever.”
   - What's unclear: Keep last JPEG with banner vs blank.
   - **Recommendation:** Keep last frame image but force status pill to yellow/red and stop updating FPS; optional overlay text in HTML via status poll (not burned into JPEG in Phase 2).

5. **Config vs CLI for source selection**
   - What we know: `SentryConfig.source.type` exists (`synthetic` default).
   - What's unclear: YAML-only vs CLI flags.
   - **Recommendation:** CLI flags override profile `source.type` for Phase 2 DX; extend `SourceConfig` fields (`device`, `path`, `url`) when convenient.

6. **Port default**
   - **Recommendation:** `8000` (uvicorn default) unless occupied — document `sentry serve --port`.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python 3.11+ | package | ✓ | 3.11.15 (+ system 3.14) | Use 3.11 for project `.venv` |
| uv | install/run | ✓ | 0.11.23 | pip + venv |
| pytest | tests | ✓ | 8.4.2 | — |
| opencv (cv2) | capture | ✗ (not in default env yet) | — | Add dep Phase 2 |
| numpy | arrays | ✓ (system) | 2.4.x range | Pin in project env |
| fastapi | API | ✓ (system 0.135; project will pin 0.141) | upgrade via uv add |
| USB camera | CAM-01 manual | unknown | — | synthetic/file for CI |
| RTSP camera | CAM-04 manual | unknown | — | docs + OpenCV URL path |

**Missing dependencies with no fallback:** none for implementation (synthetic/file cover CI).  
**Missing dependencies with fallback:** real USB/RTSP hardware → synthetic/file + manual checklist.

## Validation Architecture

> `workflow.nyquist_validation` is **true** in `.planning/config.json` — include full test map.

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest (already in dev extras; env has 8.4.2 / project ≥8) |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` testpaths=`tests` |
| Quick run command | `uv run pytest tests/test_frame_bus.py tests/test_sources_synthetic.py -q` |
| Full suite command | `uv run pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|--------------|
| CAM-01 | USB source constructs VideoCapture(index) path (mock cv2) | unit | `pytest tests/test_sources_opencv.py::test_usb_open_uses_index -q` | ❌ Wave 0 |
| CAM-02 | File source reads fixture frames with increasing frame_id | unit | `pytest tests/test_sources_file.py -q` | ❌ Wave 0 |
| CAM-03 | Synthetic yields ImageFrame with HxWx3 uint8 | unit | `pytest tests/test_sources_synthetic.py -q` | ❌ Wave 0 |
| CAM-04 | RTSP target passed to VideoCapture; disconnect raises | unit (mock) | `pytest tests/test_sources_rtsp.py -q` | ❌ Wave 0 |
| CAM-05 | Bus depth-1; drops increment on overwrite; fps computed | unit | `pytest tests/test_frame_bus.py -q` | ❌ Wave 0 |
| CAM-06 | Capture loop sets reconnecting/error; recovers after open works | unit | `pytest tests/test_capture_loop_reconnect.py -q` | ❌ Wave 0 |
| UI-01 | `/preview/mjpeg` returns multipart; `/` serves HTML with img | integration | `pytest tests/test_api_preview.py -q` | ❌ Wave 0 |
| MODEL-03 | Default host is 127.0.0.1 in serve CLI options | unit | `pytest tests/test_cli_serve.py::test_default_host_localhost -q` | ❌ Wave 0 |

### Sampling Rate

- **Per task commit:** quick subset for touched module  
- **Per wave merge:** `uv run pytest -q`  
- **Phase gate:** Full suite green + manual USB check (optional hardware) before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/fixtures/sample_clip.mp4` — short generated clip (script or committed binary; generate in test session with cv2.VideoWriter if preferred)
- [ ] `tests/test_sources_synthetic.py` — CAM-03
- [ ] `tests/test_sources_file.py` — CAM-02
- [ ] `tests/test_sources_opencv.py` — CAM-01 (mock)
- [ ] `tests/test_sources_rtsp.py` — CAM-04 (mock)
- [ ] `tests/test_frame_bus.py` — CAM-05
- [ ] `tests/test_capture_loop_reconnect.py` — CAM-06
- [ ] `tests/test_api_preview.py` — UI-01 (httpx ASGI)
- [ ] `tests/test_cli_serve.py` — MODEL-03 host default + help
- [ ] Update `tests/test_plugins_registry.py` / `test_schemas_frame.py` for protocol evolution (identity Frame stays)
- [ ] Dev deps: ensure `httpx` in `[project.optional-dependencies] dev`
- [ ] Runtime deps: opencv-python-headless, numpy, fastapi, uvicorn[standard]

**Manual-only (document in VALIDATION.md):**
- Plug real USB camera → browser shows motion
- Unplug USB → status yellow/red, no infinite silent freeze; replug recovers
- Optional RTSP against lab camera

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|------------------|
| V2 Authentication | no (localhost Phase 2) | Document auth when leaving localhost (later) |
| V3 Session Management | no | — |
| V4 Access Control | partial | Bind localhost by default; opt-in remote |
| V5 Input Validation | yes | Validate source paths/URLs/device index; reject path traversal if serving files |
| V6 Cryptography | no | No TLS required for localhost; optional later |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LAN exposure of live camera | Information Disclosure | Default `127.0.0.1`; warn on `0.0.0.0` |
| RTSP credentials in CLI/process list | Information Disclosure | Prefer env/config file; document risk of URL passwords |
| Path traversal via `--path` | Tampering | Resolve path; optional allowlist under cwd |
| Resource exhaustion via many MJPEG clients | Denial of Service | Cap UI FPS; keep-latest; optional max clients later |
| Stale “all clear” perception | Spoofing (integrity) | Status + timestamps; Phase 5 TTL — Phase 2: status not green when disconnected |

## What NOT to Build (Phase 2)

| Out of scope | Why |
|--------------|-----|
| Detection / depth / free-space models | Phases 3–5 |
| Overlay canvas, thresholds, stage toggles | Phases 5–6 |
| Full `/v1` PerceptionFrame robot stream | Phase 5 |
| WebRTC / aiortc | Post-v1 if MJPEG lag hurts |
| Vite + React dashboard | Phase 5–6; static HTML enough now |
| Multi-camera fusion | v2; keep `camera_id` only |
| GStreamer graph as default capture | Upgrade path only |
| PyAV as required dependency | Optional RTSP escape hatch |
| Auth tokens / HTTPS | Not required for localhost default |
| Kafka/Redis/ZMQ bus | Single-process mailbox |
| ROS2 bridge | Phase 7 stub |
| Intrinsics calibration UX | Needed before metric free-space, not for preview |
| Recording / video write product features | Not in requirements |
| Electron shell | Browser to localhost |

## Recommended Package Layout (under `src/sentry_ai/`)

See Architecture Patterns → Recommended Project Structure. Summary of **new** top-level packages:

| Package | Responsibility |
|---------|----------------|
| `sentry_ai.capture` | `ImageFrame`, status enums, capture loop/reconnect |
| `sentry_ai.bus` | `FrameBus`, metrics |
| `sentry_ai.sources` | OpenCV + synthetic implementations |
| `sentry_ai.api` | FastAPI app factory + routes |
| `sentry_ai.ui.static` | `index.html` Live Preview |

**Leave in place:** `schemas`, `plugins`, `config`, `backend`, `policy`, `cli`.

## Project Constraints (from CLAUDE.md / project instructions)

No project-root `CLAUDE.md` or `AGENTS.md` was present in the Sentry repo at research time. Applicable constraints come from planning artifacts and Phase 1:

- Package: `sentry-ai` / `sentry_ai` / CLI `sentry`
- Python 3.11+, `uv` + `pyproject.toml`, hatchling wheel
- Perception-only (no motor commands)
- Localhost-first privacy
- Ruff lint config already in `pyproject.toml` — follow it
- pytest under `tests/`
- Do not expand into detection/depth in this phase

## Sources

### Primary (HIGH confidence)

- Phase 1 shipped code: `schemas/frame.py`, `plugins/protocols.py`, `plugins/builtins.py`, `cli.py`, `pyproject.toml`
- `.planning/research/STACK.md`, `ARCHITECTURE.md`, `PITFALLS.md`, `SUMMARY.md`
- `.planning/phases/02-camera-ingest-live-preview/02-CONTEXT.md`, `02-UI-SPEC.md`
- [OpenCV VideoCapture tutorial](https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html) — USB/file capture API
- [OpenCV VideoCapture class](https://docs.opencv.org/4.x/d8/dfe/classcv_1_1VideoCapture.html) — open/read/release, URL streams
- [FastAPI custom responses / StreamingResponse](https://fastapi.tiangolo.com/advanced/custom-response/) — MJPEG stream pattern
- [Uvicorn settings](https://uvicorn.dev/settings/) — default host `127.0.0.1`, port 8000
- PyPI version checks 2026-08-07: opencv-python-headless 4.14.0.94 / 5.0.0.93, numpy 2.4.6 (py3.11) / 2.5.1 (py≥3.12), fastapi 0.141.1, uvicorn 0.52.1, httpx 0.28.1

### Secondary (MEDIUM confidence)

- Stack research RTSP reliability notes (OpenCV flaky → PyAV/GStreamer) — not re-benchmarked this session
- Jetson/OpenCV 5 readiness — assumed lag; prefer 4.14 pin

### Tertiary (LOW confidence)

- Exact per-backend behavior of `CAP_PROP_BUFFERSIZE` on macOS AVFoundation vs Linux V4L2 — validate during implementation

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — PyPI versions verified; aligns with STACK.md
- Architecture: **HIGH** — constrained by ARCHITECTURE.md + Phase 1 contracts + UI-SPEC
- Pitfalls: **HIGH** — from PITFALLS.md + OpenCV/async common failures
- RTSP production hardness: **MEDIUM** — OpenCV-first with documented limits is the deliberate Phase 2 bar

**Research date:** 2026-08-07  
**Valid until:** ~2026-09-07 (re-check FastAPI/OpenCV pins if delayed)

---

## RESEARCH COMPLETE

**Phase:** 2 - Camera Ingest & Live Preview  
**Confidence:** HIGH

### Key Findings
- Introduce **`ImageFrame`** (runtime) rather than putting numpy/JPEG on Pydantic `Frame`; evolve `CameraSource.read() -> ImageFrame`.
- **Capture thread + FrameBus depth-1** is the concurrency model; FastAPI only subscribes.
- **OpenCV headless** covers USB, file, synthetic patterns, and best-effort RTSP; defer PyAV.
- **MJPEG + static HTML** satisfies UI-01 without Vite; Uvicorn default **127.0.0.1** satisfies MODEL-03.
- **CLI: `sentry serve`** with `--source synthetic|usb|file|rtsp` is the one-command path.
- Deps: `opencv-python-headless` (prefer 4.14.x), `numpy>=2,<2.5`, `fastapi` 0.141.x, `uvicorn[standard]` 0.52.x, dev `httpx`.

### File Created
`.planning/phases/02-camera-ingest-live-preview/02-RESEARCH.md`

### Confidence Assessment
| Area | Level | Reason |
|------|-------|--------|
| Standard Stack | HIGH | PyPI + official FastAPI/OpenCV/Uvicorn docs |
| Architecture | HIGH | Locked CONTEXT + ARCHITECTURE + Phase 1 code |
| Pitfalls | HIGH | Project PITFALLS + capture/async known issues |
| RTSP depth | MEDIUM | Documented limits acceptable for CAM-04 |

### Open Questions
Drop metric definition, RTSP CI bar, stale-frame UX — all have recommended defaults above.

### Ready for Planning
Research complete. Planner can create PLAN.md files (02-01 sources, 02-02 bus, 02-03 API/preview).  
**Note:** Per user instruction this research was **not** git-committed.
