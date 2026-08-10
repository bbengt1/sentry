# Sentry AI documentation

Camera-only perception for maker robotics — **local OSS models**, Live Preview,
and a versioned perception stream for robots. **No motor commands.**

## Start here

| Doc | When to read it |
|-----|-----------------|
| [../README.md](../README.md) | Install, quick start, feature overview |
| [desktop-gpu.md](desktop-gpu.md) | **Primary maker path** — full detect + depth pipeline |
| [safety-and-privacy.md](safety-and-privacy.md) | Non-autonomy, free-space honesty, localhost / LAN risk |
| [architecture.md](architecture.md) | Pipeline spine, processes, design boundaries |
| [api-reference.md](api-reference.md) | HTTP / WebSocket endpoints |
| [cli.md](cli.md) | `sentry` commands and flags |
| [configuration.md](configuration.md) | Profiles, env vars, model cache |
| [perception-frame.md](perception-frame.md) | `PerceptionFrame` wire contract |
| [camera-sources.md](camera-sources.md) | USB / file / RTSP / synthetic matrix |
| [development.md](development.md) | Contributing, tests, package layout |
| [edge-serve.md](edge-serve.md) | Export → artifact → `sentry serve` edge path (ORT/TRT) |
| [export/README.md](export/README.md) | ONNX / TensorRT export recipes (edge packaging) |
| [../THIRD_PARTY_MODELS.md](../THIRD_PARTY_MODELS.md) | Model licenses (AGPL YOLO, Apache DAV2 Small) |

## Product thesis (one paragraph)

Sentry AI turns a single off-the-shelf camera into a **perception stream**:
relative monocular depth, free-space / obstacle cues, fixed-class detections,
and optional open-vocabulary prompts. Developers use the **Live Preview**;
robots consume **`/v1/snapshot`** and **`WS /v1/stream`**. Control, e-stop,
and navigation stay with the robot integrator.

## Versioning

| Artifact | Version |
|----------|---------|
| Python package (`pyproject.toml`) | **0.1.0** |
| GitHub release | **v0.1.0** |
| Planning milestone (GSD) | v0.2 Edge Runtime (package may still be 0.1.0) |

Package **0.1.0** is the first public software release of the v1.0 MVP slice.
Planning milestone **v0.2** adds live ORT/TRT edge paths without a package
version bump until a release cut.

## Quick links

```bash
# Primary path
uv sync --extra dev --extra detect --extra depth
uv run sentry serve --profile desktop-gpu --source usb --device 0
# → http://127.0.0.1:8000/

# Headless robots
uv run sentry serve --no-ui --source usb --device 0
# → GET /v1/snapshot  ·  WS /v1/stream
```
