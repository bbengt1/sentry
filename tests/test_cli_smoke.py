"""FOUND-01 / FOUND-05: CLI health and full synthetic smoke."""

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


def test_health_default_profile_string() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "cpu-fallback" in result.stdout


def test_health_lists_plugins() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "synthetic" in out
    assert "noop" in out
    assert "null" in out
    assert "schema_version" in out or "schema-version" in out or "schema version" in out


def test_smoke_exits_zero() -> None:
    result = runner.invoke(app, ["smoke"])
    assert result.exit_code == 0
    assert "smoke" in result.stdout.lower()


def test_smoke_validates_synthetic_frames() -> None:
    result = runner.invoke(app, ["smoke", "--frames", "5"])
    assert result.exit_code == 0
    out = result.stdout.lower()
    assert "5" in result.stdout or "frames" in out
    # Should mention perception / validated path
    assert "perception" in out or "validated" in out or "ok" in out


def test_smoke_rejects_cloud_if_forced() -> None:
    """Smoke must load profile with allow_cloud false and not require keys."""
    result = runner.invoke(app, ["smoke", "--profile", "cpu-fallback"])
    assert result.exit_code == 0
    # No cloud key errors
    assert "api key" not in result.stdout.lower()
    assert "api_key" not in result.stdout.lower()
