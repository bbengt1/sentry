# Development

## Prerequisites

- Python **3.11+**
- [uv](https://docs.astral.sh/uv/)
- Git

## Setup

```bash
git clone https://github.com/bbengt1/sentry.git
cd sentry
uv sync --extra dev
# Optional ML:
uv sync --extra dev --extra detect --extra depth
```

## Tests

```bash
# Full suite
uv run pytest -q

# Lint
uv run ruff check src tests

# Smoke (no server)
uv run sentry smoke
uv run sentry health
```

CI-oriented tests **mock** YOLO/DAV2 and do not download weights by default.
Real-weight visual checks are optional operator UAT.

## Layout

```
src/sentry_ai/     # Library + CLI
tests/             # pytest
docs/              # User and integrator docs
scripts/export/    # Offline export helpers (not importable runtime)
.planning/         # GSD roadmap/archive (optional for end users)
```

## Coding conventions

- **Perception-only:** no motor/control API fields  
- **Depth honesty:** relative never labeled as meters; `metric_estimated` ≠
  calibrated; `metric_calibrated` + m only when applied+valid
  ([calibration.md](calibration.md))  
- **Workers:** never open cameras; consume `ImageFrame` only  
- **Keep-latest:** FrameBus and PerceptionStore drop-old under load  
- **Extras:** optional `detect` / `depth` — core must import without torch  

## Adding a camera source

1. Implement `CameraSource` protocol  
2. Register via entry point `sentry_ai.sources`  
3. Wire CLI serve if it should appear as `--source`  

## Adding a sink / extension

See `src/sentry_ai/plugins/` and `src/sentry_ai/extensions/`.  
ROS2 bridge is a **stub** (`NotImplementedError`); voice is a no-op sink.

## Docs

Index: [README.md](README.md). Prefer honesty language (no FPS guarantees
without measurement; no FSD claims). Operator calibration:
[calibration.md](calibration.md).

## License

Application code: **Apache-2.0** (`LICENSE`).  
Models: [THIRD_PARTY_MODELS.md](../THIRD_PARTY_MODELS.md) (YOLO/YOLOE AGPL).
