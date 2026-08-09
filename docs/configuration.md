# Configuration

## Runtime profiles

Built-in YAML profiles ship in the package:

`src/sentry_ai/config/profiles/{desktop-gpu,jetson,cpu-fallback}.yaml`

| Profile | Detector tier | Preferred backend | Typical device id | Role |
|---------|---------------|-------------------|-------------------|------|
| `desktop-gpu` | `s` | `torch` | `cuda:0` | Primary maker path |
| `jetson` | `n` | `tensorrt` | `0` → cuda policy | Edge tiers / export target |
| `cpu-fallback` | `n` | `onnxruntime` | `cpu` | Default serve / CI |

Select with:

```bash
uv run sentry serve --profile desktop-gpu ...
# or
export SENTRY_PROFILE=desktop-gpu
```

Serve **defaults to `cpu-fallback`** (safe without GPU). There is **no**
automatic switch to `desktop-gpu` when CUDA is detected.

### What profiles apply at serve

| Field | Effect |
|-------|--------|
| `models.detector_tier` | YOLO26 weight (`n`/`s`/`m` → `yolo26*.pt`) |
| open-vocab tier | Derived from detector tier (`yoloe-26n-seg` / `yoloe-26s-seg`) |
| `models.depth_tier` | `small` only (Base/Large NC rejected) |
| `device.preferred_backend` + `device_id` | Device policy for workers |
| `models.allow_cloud` | Must stay `false` on default path |

`preferred_backend: tensorrt` does **not** enable live TensorRT inference.
Live path is still PyTorch (CUDA if available). See [architecture.md](architecture.md).

### Device fallback

`resolve_device` validates availability:

- CUDA request without CUDA → **MPS** (Apple) or **CPU**  
- Logged once; frames continue  

## Environment variables

| Variable | Purpose |
|----------|---------|
| `SENTRY_PROFILE` | Default profile when CLI omits `--profile` |
| `SENTRY_MODEL_CACHE` | Root for weight/HF caches (default `~/.cache/sentry-ai`) |

### Model cache layout

| Path | Content |
|------|---------|
| `$SENTRY_MODEL_CACHE/weights` | Ultralytics `.pt` (YOLO / YOLOE) |
| `$SENTRY_MODEL_CACHE/hf` | Hugging Face home for DAV2 Small |

First run may download weights; later runs work offline if cache is intact.

## Optional user config file

`load_config` merge order:

1. Built-in profile YAML  
2. Optional user file (when supported by CLI/env — see `load.py`)  
3. Environment overrides (`SENTRY_PROFILE`)  

`SentryConfig` is Pydantic with `extra=forbid` on config trees.

## Pipeline runtime (live, not YAML)

Stage enables and free-space cuts live in `PipelineState` and
`PATCH /api/pipeline/config` — they do not require process restart.

Detection conf: `PATCH /api/detection/config`.  
Depth mode: `PATCH /api/depth/config`.

## Privacy defaults

| Setting | Default |
|---------|---------|
| Bind host | `127.0.0.1` |
| `allow_cloud` | `false` |
| Auth on LAN | **None** — never expose `--host 0.0.0.0` without understanding risk |

Details: [safety-and-privacy.md](safety-and-privacy.md).
