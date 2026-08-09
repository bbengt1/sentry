# Contributing

Thanks for interest in Sentry AI.

## How to contribute

1. Open an issue for large design changes before a big PR.  
2. Fork and branch from `main`.  
3. Keep PRs focused; match existing style (`ruff`).  
4. Add or update tests for behavior changes.  
5. Run:

```bash
uv sync --extra dev
uv run ruff check src tests
uv run pytest -q
```

## Design non-negotiables

- **Perception only** — no robot control / motor APIs  
- **Depth honesty** — relative depth is never meters  
- **Local OSS default** — no mandatory cloud inference  
- **Localhost default** — document any remote bind risk  

See [docs/development.md](docs/development.md) and
[docs/safety-and-privacy.md](docs/safety-and-privacy.md).

## License

By contributing, you agree that contributions are licensed under the project
**Apache-2.0** license unless stated otherwise. Do not add GPL/AGPL **application**
code without discussion. Model weights used by optional extras may carry
different licenses (see `THIRD_PARTY_MODELS.md`).
