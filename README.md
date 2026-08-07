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

Also available:

```bash
uv run sentry health
python -m sentry_ai health
python -m sentry_ai smoke
```

## Phase 1 scope

Phase 1 ships **contracts and smoke skeleton** only:

- Installable package + Typer CLI (`health`, `smoke`)
- Shared schemas, config profiles, plugin registry stubs (subsequent plans)
- No real camera capture, model inference, or web UI yet

## License

Application code is licensed under [Apache-2.0](LICENSE). Third-party model licenses will be documented in `THIRD_PARTY_MODELS.md` (plan 01-03).
