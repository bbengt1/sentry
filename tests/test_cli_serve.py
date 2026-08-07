"""MODEL-03: sentry serve CLI defaults and registration."""

from __future__ import annotations

import inspect

from typer.testing import CliRunner

from sentry_ai import cli as cli_mod
from sentry_ai.cli import _build_serve_source, app
from sentry_ai.sources.opencv_source import FileSource, RtspSource, UsbSource
from sentry_ai.sources.synthetic import SyntheticSource

runner = CliRunner()


def test_serve_help_shows_localhost_default() -> None:
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    out = result.stdout
    assert "127.0.0.1" in out
    # Privacy opt-in language for non-localhost binds
    assert "0.0.0.0" in out or "LAN" in out or "auth" in out.lower()


def test_serve_command_registered() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "serve" in result.stdout


def test_serve_host_option_default_is_loopback() -> None:
    """Inspect Typer option default without binding a server."""
    result = runner.invoke(app, ["serve", "--help"])
    assert result.exit_code == 0
    # Typer help format: --host TEXT  [default: 127.0.0.1]
    assert "127.0.0.1" in result.stdout
    lower = result.stdout.lower()
    assert "default" in lower


def test_build_serve_source_synthetic() -> None:
    src = _build_serve_source(
        source="synthetic",
        device=0,
        path=None,
        url=None,
        camera_id=None,
    )
    assert isinstance(src, SyntheticSource)
    assert src.name == "synthetic"


def test_build_serve_source_usb() -> None:
    src = _build_serve_source(
        source="usb",
        device=1,
        path=None,
        url=None,
        camera_id=None,
    )
    assert isinstance(src, UsbSource)
    assert src.target == 1


def test_build_serve_source_file_requires_path() -> None:
    result = runner.invoke(app, ["serve", "--source", "file"])
    assert result.exit_code == 1
    assert "path" in (result.stderr + result.stdout).lower()


def test_build_serve_source_rtsp_requires_url() -> None:
    result = runner.invoke(app, ["serve", "--source", "rtsp"])
    assert result.exit_code == 1
    assert "url" in (result.stderr + result.stdout).lower()


def test_build_serve_source_file_and_rtsp() -> None:
    file_src = _build_serve_source(
        source="file",
        device=0,
        path="/tmp/clip.mp4",
        url=None,
        camera_id="f0",
    )
    assert isinstance(file_src, FileSource)
    assert file_src.target == "/tmp/clip.mp4"

    rtsp_src = _build_serve_source(
        source="rtsp",
        device=0,
        path=None,
        url="rtsp://example.invalid/s",
        camera_id="r0",
    )
    assert isinstance(rtsp_src, RtspSource)
    assert rtsp_src.target == "rtsp://example.invalid/s"


def test_health_lists_rtsp_source() -> None:
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "rtsp" in result.stdout


def test_serve_source_wires_detection_loop_lifecycle() -> None:
    """serve constructs PerceptionStore + DetectionLoop when available."""
    source = inspect.getsource(cli_mod.serve)
    assert "PerceptionStore" in source
    assert "DetectionLoop" in source
    assert "create_app" in source
    assert "perception_store" in source
    assert "detection_worker" in source
    # Graceful degrade path when detect extra missing
    assert "uv sync --extra detect" in source or "detect extra" in source.lower()
    # Stop detection before capture in finally
    assert "det_loop" in source


def test_serve_does_not_import_torch_at_module_level() -> None:
    """Bare smoke path: cli module must not hard-import torch."""
    source = inspect.getsource(cli_mod)
    # Top of module / unconditional imports should not pull torch.
    assert "import torch" not in source.split("def serve")[0]
