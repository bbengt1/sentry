"""Sentry AI CLI — health and synthetic smoke entry points.

Smoke validates synthetic ImageFrame → PerceptionFrame paths without
hardware cameras, torch, or cloud API keys (MODEL-01 / FOUND-05).
"""

from __future__ import annotations

import sys

import typer
from pydantic import ValidationError

from sentry_ai import __version__
from sentry_ai.config.load import load_config
from sentry_ai.plugins.builtins import NoopWorker, NullSink, SyntheticSource
from sentry_ai.plugins.registry import PluginRegistry, register_builtins
from sentry_ai.schemas.perception import Completeness, PerceptionFrame

app = typer.Typer(
    name="sentry",
    help="Sentry AI — camera-only perception",
    no_args_is_help=True,
)


def _build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtins(registry)
    registry.discover()
    return registry


@app.command()
def health(
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name.",
    ),
) -> None:
    """Print package version, profile, plugins, and ok status."""
    registry = _build_registry()
    sources = ", ".join(registry.list_sources()) or "(none)"
    workers = ", ".join(registry.list_workers()) or "(none)"
    sinks = ", ".join(registry.list_sinks()) or "(none)"

    typer.echo(f"sentry-ai {__version__}")
    typer.echo(f"profile: {profile}")
    typer.echo("schema_version: 1")
    typer.echo(f"sources: {sources}")
    typer.echo(f"workers: {workers}")
    typer.echo(f"sinks: {sinks}")
    typer.echo("status: ok")


@app.command()
def smoke(
    frames: int = typer.Option(
        3,
        help="Number of synthetic frames to validate.",
        min=1,
    ),
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name.",
    ),
) -> None:
    """Build synthetic ImageFrames, wrap as PerceptionFrames, validate, exit 0.

    Local OSS path only — loads profile, asserts allow_cloud is false, never
    calls cloud APIs or loads ML weights.
    """
    try:
        cfg = load_config(profile=profile)
    except (ValueError, FileNotFoundError, ValidationError) as exc:
        typer.echo(f"smoke failed: config error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if cfg.models.allow_cloud:
        typer.echo(
            "smoke failed: allow_cloud is true; default path must stay local OSS",
            err=True,
        )
        raise typer.Exit(code=1)

    source = SyntheticSource(camera_id="synthetic0", fps=0.0)
    worker = NoopWorker()
    sink = NullSink()
    validated = 0

    source.open()
    try:
        for _ in range(frames):
            image = source.read()
            # Optional pass-through stubs (no models).
            _ = worker.process(image)
            meta = image.meta

            try:
                perception = PerceptionFrame.model_validate(
                    {
                        "schema_version": 1,
                        "frame_id": meta.frame_id,
                        "camera_id": meta.camera_id,
                        "t_capture": meta.t_capture,
                        "t_publish": meta.t_ingest,
                        "completeness": Completeness(
                            depth=False,
                            detections=False,
                            free_space=False,
                        ).model_dump(),
                    }
                )
            except ValidationError as exc:
                typer.echo(f"smoke failed: PerceptionFrame invalid: {exc}", err=True)
                raise typer.Exit(code=1) from exc

            sink.emit(perception)
            validated += 1
    finally:
        source.close()
        sink.close()

    typer.echo(
        f"smoke ok: validated {validated} synthetic PerceptionFrame(s) "
        f"(profile={profile}, allow_cloud={cfg.models.allow_cloud})"
    )


def main() -> None:
    """Console script entry point for `sentry` and `python -m sentry_ai`."""
    # Ensure non-zero exit propagates when invoked as a script.
    try:
        app()
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
        sys.exit(code)


if __name__ == "__main__":
    main()
