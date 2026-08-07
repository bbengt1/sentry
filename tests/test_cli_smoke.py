"""FOUND-01: CLI health and smoke entry points."""

from __future__ import annotations

from typer.testing import CliRunner

from sentry_ai import __version__
from sentry_ai.cli import app

runner = CliRunner()


def test_health_exits_zero_and_prints_version() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert __version__ in result.stdout
    assert "0.1.0" in result.stdout
    assert "ok" in result.stdout.lower()


def test_smoke_exits_zero() -> None:
    result = runner.invoke(app, ["smoke"])
    assert result.exit_code == 0
    assert "smoke" in result.stdout.lower()


def test_health_default_profile_string() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "cpu-fallback" in result.stdout
