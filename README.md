# Sentry AI

Camera-only perception for maker robotics — depth awareness, obstacle signals, and object recognition as a **perception stream only** (no motor commands).

**Release:** [v0.1.0](https://github.com/bbengt1/sentry/releases/tag/v0.1.0) · **Docs hub:** [`docs/README.md`](docs/README.md) · **Changelog:** [`CHANGELOG.md`](CHANGELOG.md)

## Naming

| Surface | Name |
|---------|------|
| PyPI / distribution | **`sentry-ai`** |
| Python import | **`sentry_ai`** |
| CLI | **`sentry`** |

This project is **not** the [getsentry](https://sentry.io) error-tracking product. The PyPI package `sentry` is unrelated; install and import **`sentry-ai`** / **`sentry_ai`**.

## Documentation

| Guide | Description |
|-------|-------------|
| [docs/README.md](docs/README.md) | **Documentation index** |
| [docs/desktop-gpu.md](docs/desktop-gpu.md) | Primary end-to-end maker path |
| [docs/architecture.md](docs/architecture.md) | Pipeline spine and boundaries |
| [docs/api-reference.md](docs/api-reference.md) | HTTP / WebSocket API |
| [docs/cli.md](docs/cli.md) | CLI commands |
| [docs/configuration.md](docs/configuration.md) | Profiles, env, model cache |
| [docs/perception-frame.md](docs/perception-frame.md) | Robot wire contract |
| [docs/camera-sources.md](docs/camera-sources.md) | USB / RTSP / file matrix |
| [docs/safety-and-privacy.md](docs/safety-and-privacy.md) | Non-autonomy and privacy |
| [docs/export/](docs/export/) | ONNX / TensorRT export recipes |
| [docs/development.md](docs/development.md) | Contributing and tests |
| [THIRD_PARTY_MODELS.md](THIRD_PARTY_MODELS.md) | Model licenses |

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)

## Primary maker path (desktop GPU)

For full dual-model development (detect + depth + free-space + Live Preview),
follow **[`docs/desktop-gpu.md`](docs/desktop-gpu.md)** — the primary end-to-end
maker path:

```bash
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --profile desktop-gpu --source usb --device 0
```

Then open **`http://127.0.0.1:8000/`**. Safety / privacy / non-autonomy:
[`docs/safety-and-privacy.md`](docs/safety-and-privacy.md).

## One-command local start (CPU / CI)

```bash
uv sync --extra dev
uv run sentry serve --source synthetic
```

Default runtime profile is **`cpu-fallback`** (safe without a GPU). Then open
**`http://127.0.0.1:8000/`** for the Live Preview (MJPEG + status).

Default bind is **localhost only** (`127.0.0.1`). Binding a remote interface is an
**explicit opt-in** and exposes the live camera stream **without authentication**:

```bash
# Privacy risk — LAN exposure, no auth:
uv run sentry serve --source synthetic --host 0.0.0.0
```

### Runtime profiles

| Profile | Typical use | Select |
|---------|-------------|--------|
| `desktop-gpu` | **Primary maker path** — full pipeline on GPU | `--profile desktop-gpu` |
| `jetson` | Jetson-class edge tiers (still PyTorch live) | `--profile jetson` |
| `cpu-fallback` | Default — CI / no-GPU | `--profile cpu-fallback` (or omit) |

### Headless (API without Live Preview HTML)

```bash
uv run sentry serve --no-ui --source synthetic
# Perception APIs remain: /v1/snapshot, /v1/stream, /api/*
```

Headless does **not** add authentication — see
[`docs/safety-and-privacy.md`](docs/safety-and-privacy.md).
### Other sources

```bash
# USB UVC camera
# List OpenCV camera indices (USB / FaceTime / Continuity Camera on macOS)
uv run sentry cameras

uv run sentry serve --source usb --device 0

# Local video file (loops by default)
uv run sentry serve --source file --path tests/fixtures/sample_clip.mp4

# Network / IP camera (OpenCV best-effort — see docs)
uv run sentry serve --source rtsp --url "rtsp://camera.local/stream"
```

Camera source matrix, RTSP known limits, and manual checks:
[`docs/camera-sources.md`](docs/camera-sources.md).

### Smoke / health (no server)

```bash
uv run sentry smoke
uv run sentry health
python -m sentry_ai health
python -m sentry_ai smoke
```

`sentry smoke` builds synthetic camera frames, wraps each as a `PerceptionFrame`,
validates the schema contracts, and exits 0 — **no camera, no GPU, no cloud API keys**.

`sentry health` prints version, runtime profile, registered plugins
(sources / workers / sinks), and `schema_version`.

## Optional detection (Phase 3)

Fixed-class object detection (YOLO26 via Ultralytics) is an **optional extra** —
core install and unit tests do not require torch:

```bash
# Dev + detection stack
uv sync --extra dev --extra detect

# Synthetic serve with boxes on Live Preview
uv run sentry serve --source synthetic
```

Open **`http://127.0.0.1:8000/`** — MJPEG shows server-drawn boxes; footer
shows detection count, det latency, and a confidence threshold control.

Without the detect extra, `sentry serve` still starts capture + Live Preview
and logs a clear install hint (`uv sync --extra detect`).

### Detection API

| Endpoint | Purpose |
|----------|---------|
| `GET /api/snapshot` | Latest `PerceptionFrame` JSON (same detections as MJPEG overlay) |
| `GET /api/detection/config` | Current conf (+ weights/device when available) |
| `PATCH /api/detection/config` | Runtime conf update: `{"conf": 0.4}` without restart |
| `GET /api/status` | Capture + optional det metrics (`detections_count`, `det_latency_ms`, `det_conf`, …) |

### Model cache

On first detection run, weights download once into the Sentry model cache
(`SENTRY_MODEL_CACHE` or `~/.cache/sentry-ai/weights`). Subsequent runs are
offline. Profile `detector_tier` maps to YOLO26 weights (`n`/`s`/`m`).

Ultralytics/YOLO26 is **AGPL-3.0** — see
[`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md) before commercial use.

## Optional open-vocab detection (Phase 6)

Text-prompt open-vocabulary detection (YOLOE via the same `detect` extra)
runs as a **secondary** path alongside fixed-class YOLO. Default mode is
**off** — it does not block fixed-class, depth, or capture.

```bash
# Same detect extra as fixed-class YOLO
uv sync --extra dev --extra detect
uv run sentry serve --source synthetic
```

On Live Preview (`http://127.0.0.1:8000/`):

1. Enter comma-separated prompts (e.g. `person, red cup, toolbox`)
2. Click **Run** for a one-shot on-demand pass
3. Optionally enable **continuous (lower rate)** (`every_n=3`)

Open-vocab boxes are **magenta** (`ov:` label prefix); fixed-class stay cyan.
Results appear on MJPEG and `/v1/snapshot` / `/v1/stream` with
`Detection.source = "open_vocab"`.

| Endpoint | Purpose |
|----------|---------|
| `GET /api/open-vocab/config` | Mode, classes, conf, every_n |
| `PATCH /api/open-vocab/config` | Update prompt/mode/conf/every_n (no inference) |
| `POST /api/open-vocab/run` | Arm one-shot on-demand run (process on loop thread) |

First open-vocab Run may download YOLOE weights (`yoloe-26s-seg.pt`) into
`SENTRY_MODEL_CACHE` — **AGPL-3.0** Ultralytics; see
[`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md). Unit tests mock YOLOE and
never download weights.

Prompt limits: ≤32 classes, ≤64 characters each (422 on violation).

## Optional monocular depth (Phase 4)

Depth Anything V2 **Small** (Apache-2.0) runs locally via Hugging Face
Transformers. Core install and unit tests do **not** require torch:

```bash
# Dev + depth stack
uv sync --extra dev --extra depth

# Both detection and depth
uv sync --extra dev --extra detect --extra depth

# Synthetic serve with TURBO depth colormap on Live Preview
uv run sentry serve --source synthetic
```

Default mode is **relative** depth (`DepthKind.relative`) — **never** labeled
as meters. Optional metric indoor/outdoor Small heads are labeled
`metric_estimated` with `unit="m"`. Base/Large NC weights are never default.

Without the depth extra, `sentry serve` still starts capture + Live Preview
and logs a clear install hint (`uv sync --extra depth`).

On first depth run, HF weights download once into
`SENTRY_MODEL_CACHE/hf` (or `~/.cache/sentry-ai/hf`). Subsequent runs are
offline. Unit tests inject fake models and never hit the HF hub.

### Depth API / status

| Endpoint | Purpose |
|----------|---------|
| `GET /api/snapshot` | `PerceptionFrame` with optional `depth` (`DepthPayload`: kind, unit, width, height) + completeness; **no** full depth map arrays |
| `GET /api/depth/config` | Current `depth_mode` (+ model id/device when available) |
| `PATCH /api/depth/config` | Runtime mode: `{"depth_mode":"relative"\|"metric_indoor"\|"metric_outdoor"}` |
| `GET /api/status` | Capture + optional depth metrics (`depth_kind`, `depth_latency_ms`, `depth_fps`, `depth_frame_id`, …) |
| Live Preview MJPEG | Server-side OpenCV `COLORMAP_TURBO` blend from the same PerceptionStore product |

Honesty rules: relative products omit unit / never claim meters; metric modes
show `metric_estimated` + `m`. Status/UI footer show depth kind + latency.

## Free-space & unified stream (Phase 5)

Near-field free-space / obstacle cues are derived on CPU from the in-process
depth map (**Spatial Post** — no second neural net, no new install extra).
`sentry serve` always starts `FreeSpaceLoop` when a `PerceptionStore` exists;
it idles until depth products appear.

### Versioned perception API (`/v1`)

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/snapshot` | Point-in-time merged `PerceptionFrame` (detections + depth metadata + free_space) |
| `WS /v1/stream` | Keep-latest JSON `PerceptionFrame` at ~10 Hz (no per-client queue) |
| `GET /api/snapshot` | **Alias** of `GET /v1/snapshot` (same assembler; back-compat) |
| `GET /api/status` | Capture + det/depth/**free_space** metrics for Live Preview footer |
| Live Preview MJPEG | Draw order: depth blend → free-space mask → detection boxes (same store) |

Wire free-space shape (`FreeSpacePayload`):

- `method`: `near_field_bands`
- `depth_kind` + `units` (v1 always **ordinal** — not calibrated meters)
- `obstacle_count`, `obstacles[]` (bbox + nearness + band), optional `bands`
- **Not** on the wire: full `free_mask` / `occupied_mask` / `depth_map` arrays

Every frame includes `completeness` and `stats` ages / stale flags
(`free_space_age_ms`, `free_space_stale`, `products_stale`, stage FPS/drops).
**Consumers must honor stale/TTL** — this is a perception stream, **not a
safety interlock**. Invalidated products must not be treated as live.

### Perception-only boundary (API-05)

Envelopes never include motor, velocity, path-plan, or autonomy-clearance
fields (`cmd`, `cmd_vel`, `twist`, `path_plan`, and related control keys).
Live Preview copy is limited to obstacles / free-space / incomplete / STALE.

### Robot client sketch (optional)

```python
# Point-in-time
import httpx
frame = httpx.get("http://127.0.0.1:8000/v1/snapshot").json()

# Streaming (~10 Hz keep-latest)
from websockets.sync.client import connect
with connect("ws://127.0.0.1:8000/v1/stream") as ws:
    msg = ws.recv()  # JSON PerceptionFrame; check stats.*_stale
```

Install remains **core** + optional `detect` / `depth` extras. Free-space needs
no new package — only a depth product for the loop to consume.

## Export (ONNX / TensorRT)

Offline edge packaging recipes — **not** a live TensorRT runtime in Sentry v1.
Live `sentry serve` stays on **PyTorch** profiles (`desktop-gpu`, `jetson`,
`cpu-fallback`). Build TensorRT engines **on-device**; never copy `.engine`
across JetPack SKUs.

```bash
uv sync --extra detect
uv run python scripts/export/export_yolo.py --weights yolo26n.pt --format onnx
```

Full honesty notes (Jetson packaging, YOLOE experimental export, depth
feasibility, AGPL): [`docs/export/README.md`](docs/export/README.md).

## Safety, privacy, and non-autonomy

Sentry is **perception-only** — no motor / `cmd_vel` / path-plan fields on the
wire. Free-space is **not a safety interlock** (honor STALE / incomplete).
Default bind is localhost; LAN is unauthenticated opt-in; `allow_cloud: false`.

Canonical page: [`docs/safety-and-privacy.md`](docs/safety-and-privacy.md).  
Primary GPU path: [`docs/desktop-gpu.md`](docs/desktop-gpu.md).

## Extension stubs (post-v1 hooks)

v1 leaves clean extension points without shipping full products:

| Stub | What it is |
|------|------------|
| Multi-cam `camera_id` | Schema identity key (cam0 vs cam1); **single active source** in v1 — no fusion |
| ROS2 bridge | Importable `Ros2PerceptionBridge` raises `NotImplementedError` (no `rclpy`) |
| Voice | `voice-null` no-op sink (no ASR/TTS) |

```python
from sentry_ai.extensions.ros2.bridge import Ros2PerceptionBridge
```

## Phase 5 scope

- FreeSpaceLoop Spatial Post (near-field bands) + FreeSpaceProduct in store
- `assemble_perception_frame` single merge path for REST + WS
- `GET /v1/snapshot` + `WS /v1/stream` + `/api/snapshot` alias
- MJPEG free-space overlay + status free_space metrics + STALE/incomplete UI
- API-05 perception-only denylist on wire envelopes
- No new ML packages

## Phase 4 scope

- Depth Anything V2 Small worker (HF Transformers) + DepthLoop on FrameBus
- PerceptionStore DepthProduct (keep-latest, dual with detections)
- Honest `DepthKind` / unit from configured mode; relative never meters
- Server-side TURBO colormap on MJPEG; snapshot metadata + stats only
- Live Preview depth kind badge + depth latency; optional depth_mode PATCH
- HF cache under `SENTRY_MODEL_CACHE/hf`
- `sentry serve` starts DepthLoop when depth extra available

## Phase 3 scope

- Fixed-class YOLO26 worker + DetectionLoop on FrameBus
- Keep-latest PerceptionStore (single truth for UI/API)
- Server-side OpenCV overlays on MJPEG
- `GET /api/snapshot` + runtime conf PATCH
- Live Preview conf slider + det telemetry

## Phase 2 scope

Phase 2 ships the **camera ingest + live preview** vertical slice:

- USB / file / synthetic / RTSP (OpenCV) sources → keep-latest Frame Bus
- Capture thread with reconnect status
- FastAPI localhost Live Preview (`GET /`, `/preview/mjpeg`, `/api/status`)
- CLI `sentry serve` (default host `127.0.0.1`)

## Phase 1 scope (still present)

- Installable package + Typer CLI (`health`, `smoke`, `serve`)
- Shared `Frame` / `PerceptionFrame` schemas with honest `DepthKind`
- Runtime profiles: `desktop-gpu`, `jetson`, `cpu-fallback`
- Plugin registry (`synthetic`, `usb`, `file`, `rtsp`, `noop`, `null`)
- InferenceBackend + `NullBackend` stubs (no torch)
- Model license documentation in [`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md)

## Model licenses

Default depth weights are **Depth Anything V2 Small (Apache-2.0)**. AGPL and
CC-BY-NC weights are **non-default**. See [`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md).

Core path is **local OSS only** (`allow_cloud: false` by default).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [docs/development.md](docs/development.md).

## License

Application code is licensed under [Apache-2.0](LICENSE). Third-party model
weight licenses are documented separately in
[`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md).
