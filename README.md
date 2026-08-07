# Sentry AI

Camera-only perception for maker robotics — depth awareness, obstacle signals, and object recognition as a **perception stream only** (no motor commands).

## Naming

| Surface | Name |
|---------|------|
| PyPI / distribution | **`sentry-ai`** |
| Python import | **`sentry_ai`** |
| CLI | **`sentry`** |

This project is **not** the [getsentry](https://sentry.io) error-tracking product. The PyPI package `sentry` is unrelated; install and import **`sentry-ai`** / **`sentry_ai`**.

## Requirements

- Python 3.11+
- [`uv`](https://docs.astral.sh/uv/)

## One-command local start

```bash
uv sync --extra dev
uv run sentry serve --source synthetic
```

Then open **`http://127.0.0.1:8000/`** for the Live Preview (MJPEG + status).

Default bind is **localhost only** (`127.0.0.1`). Binding a remote interface is an
**explicit opt-in** and exposes the live camera stream **without authentication**:

```bash
# Privacy risk — LAN exposure, no auth:
uv run sentry serve --source synthetic --host 0.0.0.0
```

### Other sources

```bash
# USB UVC camera
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

## License

Application code is licensed under [Apache-2.0](LICENSE). Third-party model
weight licenses are documented separately in
[`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md).
