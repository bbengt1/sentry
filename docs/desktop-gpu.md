# Desktop GPU — primary maker path (EDGE-01)

**This is the primary end-to-end path for makers** developing with Sentry AI:
local camera → fixed-class detect + monocular depth + free-space → Live Preview
and/or robot `/v1` consumers.

Other profiles:

| Profile | Role |
|---------|------|
| **`desktop-gpu`** | Primary maker path (this doc) — detector tier `s`, CUDA device policy |
| **`cpu-fallback`** | Default `sentry serve` profile — CI / laptops without GPU |
| **`jetson`** | Edge deploy target — smaller tiers; package via [export recipes](export/README.md) |

Throughput **depends on GPU / thermal / resolution** — Sentry does not publish
guaranteed FPS numbers for dual-model (detect + depth) stacks.

## Prerequisites

- Python **3.11+**
- [`uv`](https://docs.astral.sh/uv/)
- NVIDIA GPU with working CUDA PyTorch **or** Apple MPS / CPU (slower)
- Optional: USB UVC camera (`uv run sentry cameras`)

## Install

```bash
# Full dual-model stack (detect + depth) for desktop development
uv sync --extra dev --extra detect --extra depth
```

- `detect` — Ultralytics YOLO26 fixed-class (+ YOLOE open-vocab) — **AGPL-3.0**
- `depth` — Depth Anything V2 Small via HF Transformers — **Apache-2.0**

License table and commercial notes: [`THIRD_PARTY_MODELS.md`](../THIRD_PARTY_MODELS.md).
Ultralytics/AGPL is **non-default** for commercial redistribution — read it
before shipping products that include those weights.

## Serve (primary command)

```bash
# Opt-in desktop profile (serve default remains cpu-fallback for CI safety)
uv run sentry serve --profile desktop-gpu --source usb --device 0
```

Then open **`http://127.0.0.1:8000/`** for Live Preview (MJPEG + status footer).

Synthetic (no camera) for bring-up:

```bash
uv run sentry serve --profile desktop-gpu --source synthetic
```

### Expected stages

With both extras installed, a healthy desktop session typically runs:

1. **Capture** — USB / file / synthetic / RTSP → Frame Bus  
2. **Fixed-class detect** — YOLO26 (`detector_tier: s` → `yolo26s.pt` on desktop-gpu)  
3. **Monocular depth** — DAV2 Small (relative by default; never labeled as meters)  
4. **Free-space** — CPU Spatial Post from the depth map (ordinal nearness bands)  
5. **Live Preview** — depth blend → free-space overlay → detection boxes  
6. **Robot API** — `GET /v1/snapshot`, `WS /v1/stream` (same `PerceptionFrame`)

Open-vocab (YOLOE) stays **off** by default. On Live Preview, enter prompts and
click **Run** (or enable continuous mode). First Run may download YOLOE weights
(AGPL). See README open-vocab section.

## Model cache

First detect/depth run downloads weights once into the Sentry cache:

| Env / path | Use |
|------------|-----|
| `SENTRY_MODEL_CACHE` | Override root cache directory |
| `~/.cache/sentry-ai/weights` | Default YOLO / YOLOE weights |
| `~/.cache/sentry-ai/hf` (or `$SENTRY_MODEL_CACHE/hf`) | HF DAV2 Small |

Subsequent runs are **offline** when the cache is warm. No cloud inference keys
are required (`allow_cloud: false` remains the default).

## Robot clients (`/v1`)

Live Preview is optional for robot integrators:

```bash
# Headless: perception API without Live Preview HTML
uv run sentry serve --profile desktop-gpu --source usb --device 0 --no-ui
```

```python
import httpx
frame = httpx.get("http://127.0.0.1:8000/v1/snapshot").json()
# Honor completeness + stats.*_stale before acting on free-space cues

from websockets.sync.client import connect
with connect("ws://127.0.0.1:8000/v1/stream") as ws:
    msg = ws.recv()  # JSON PerceptionFrame ~10 Hz keep-latest
```

Default bind is **localhost** (`127.0.0.1`). LAN bind is opt-in and
**unauthenticated** — see [safety and privacy](safety-and-privacy.md).

## Profiles recap

```bash
# Primary maker path (this doc)
uv run sentry serve --profile desktop-gpu --source usb --device 0

# CI / no-GPU default
uv run sentry serve --profile cpu-fallback --source synthetic

# Jetson-class tiers — live TRT when allowlisted .engine + system TensorRT;
# otherwise soft torch + reason. See docs/edge-serve.md and docs/export/.
uv run sentry serve --profile jetson --source usb --device 0
```

Edge export → serve path: [`docs/edge-serve.md`](edge-serve.md).  
Edge export recipes: [`docs/export/README.md`](export/README.md).  
Camera source matrix: [`docs/camera-sources.md`](camera-sources.md).  
Safety / non-autonomy: [`docs/safety-and-privacy.md`](safety-and-privacy.md).

## What this path is not

- Not a measured FPS guarantee  
- Not automatic multi-SKU TensorRT — engines are on-device only  
- Not multi-cam fusion (v1 is single active source; `camera_id` is the extension key)  
- Not robot control — perception stream only  

## Related extension stubs (EDGE-04)

- `Ros2PerceptionBridge` — importable NotImplemented stub (`sentry_ai.extensions.ros2`)  
- `voice-null` sink — no-op plugin entry point (no ASR/TTS)  
- Multi-cam: schema `camera_id` identities only; no fusion product in v1  
