"""Sentry AI CLI — health, cameras, synthetic smoke, and localhost serve.

Smoke validates synthetic ImageFrame → PerceptionFrame paths without
hardware cameras, torch, or cloud API keys (MODEL-01 / FOUND-05).

``sentry cameras`` lists local OpenCV device indices (USB / built-in /
Continuity Camera on macOS).

``sentry serve`` starts capture + FastAPI Live Preview (UI-01 / MODEL-03).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

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
