"""Sentry AI CLI — health and smoke entry points."""

from __future__ import annotations

import typer

from sentry_ai import __version__

app = typer.Typer(
    name="sentry",
    help="Sentry AI — camera-only perception",
    no_args_is_help=True,
)


@app.command()
def health(
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name (config load lands in plan 01-02).",
    ),
) -> None:
    """Print package version, default profile, and ok status."""
    typer.echo(f"sentry-ai {__version__}")
    typer.echo(f"profile: {profile}")
    typer.echo("status: ok")


@app.command()
def smoke(
    frames: int = typer.Option(
        3,
        help="Number of synthetic frames (full validation in plan 01-03).",
    ),
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name (config load lands in plan 01-02).",
    ),
) -> None:
    """Phase 1 skeleton: synthetic smoke validates frames in plan 01-03."""
    typer.echo(
        f"smoke skeleton ok (frames={frames}, profile={profile}); "
        "synthetic Frame/PerceptionFrame validation lands in plan 01-03"
    )


def main() -> None:
    """Console script entry point for `sentry` and `python -m sentry_ai`."""
    app()


if __name__ == "__main__":
    main()
