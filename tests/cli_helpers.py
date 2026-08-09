"""CLI help helpers for Typer/Rich under narrow CI TTYs."""

from __future__ import annotations

import os
import re
from typing import Any

# Rich reads COLUMNS for help table layout; force a usable width in CI.
CLI_TEST_ENV: dict[str, str] = {
    "COLUMNS": "120",
    "NO_COLOR": "1",
    "TERM": "dumb",
    "FORCE_COLOR": "0",
}

# Also set process env early for any code that inspects it at import.
os.environ.update(CLI_TEST_ENV)


def strip_ansi(text: str) -> str:
    """Remove ANSI escape codes for stable CLI help assertions."""
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def cli_help_output(app: Any, *args: str) -> str:
    """Invoke ``app`` with args and return plain-text help/stdout."""
    from typer.testing import CliRunner

    result = CliRunner().invoke(app, list(args), env=CLI_TEST_ENV)
    assert result.exit_code == 0, (result.stdout or "") + (result.stderr or "")
    return strip_ansi(result.stdout or "")
