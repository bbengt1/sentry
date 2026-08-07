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
uv run sentry smoke
```

`sentry smoke` builds synthetic camera Frames, wraps each as a `PerceptionFrame`,
validates the schema contracts, and exits 0 — **no camera, no GPU, no cloud API keys**.

Also available:

```bash
uv run sentry health
python -m sentry_ai health
python -m sentry_ai smoke
```

`sentry health` prints version, runtime profile, registered plugins
(sources / workers / sinks), and `schema_version`.

## Phase 1 scope

Phase 1 ships **contracts and stubs**:

- Installable package + Typer CLI (`health`, `smoke`)
- Shared `Frame` / `PerceptionFrame` schemas with honest `DepthKind`
- Runtime profiles: `desktop-gpu`, `jetson`, `cpu-fallback`
- Plugin registry stubs (`synthetic` source, `noop` worker, `null` sink)
- InferenceBackend + `NullBackend` stubs (no torch)
- Model license documentation in [`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md)

No real camera capture, model inference, or web UI yet.

## Model licenses

Default depth weights are **Depth Anything V2 Small (Apache-2.0)**. AGPL and
CC-BY-NC weights are **non-default**. See [`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md).

Core path is **local OSS only** (`allow_cloud: false` by default).

## License

Application code is licensed under [Apache-2.0](LICENSE). Third-party model
weight licenses are documented separately in
[`THIRD_PARTY_MODELS.md`](THIRD_PARTY_MODELS.md).
