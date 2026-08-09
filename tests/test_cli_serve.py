"""MODEL-03: sentry serve CLI defaults and registration."""

from __future__ import annotations

import inspect

from typer.testing import CliRunner

from sentry_ai import cli as cli_mod
from sentry_ai.cli import _build_serve_source, app
from sentry_ai.sources.opencv_source import FileSource, RtspSource, UsbSource
from sentry_ai.sources.synthetic import SyntheticSource
from tests.cli_helpers import cli_help_output

runner = CliRunner()


def test_serve_help_shows_localhost_default() -> None:
    out = cli_help_output(app, "serve", "--help")
    assert "127.0.0.1" in out
    # Privacy opt-in language for non-localhost binds
    assert "0.0.0.0" in out or "LAN" in out or "auth" in out.lower()


def test_serve_command_registered() -> None:
    out = cli_help_output(app, "--help")
    assert "serve" in out


def test_serve_host_option_default_is_loopback() -> None:
    """Inspect Typer option default without binding a server."""
    out = cli_help_output(app, "serve", "--help")
    # Typer help format: --host TEXT  [default: 127.0.0.1]
    assert "127.0.0.1" in out
    lower = out.lower()
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


def test_serve_uses_graceful_shutdown_timeout() -> None:
    """Ctrl+C must not hang forever on open MJPEG connections."""
    source = inspect.getsource(cli_mod.serve)
    assert "timeout_graceful_shutdown" in source
    assert "shutdown_flag" in source
    assert "_signal_shutdown" in source
    assert "handle_exit" in source


def test_serve_source_wires_depth_loop_lifecycle() -> None:
    """serve constructs DepthLoop when depth extra available; degrades otherwise."""
    source = inspect.getsource(cli_mod.serve)
    assert "DepthLoop" in source
    assert "DepthAnythingWorker" in source
    assert "depth_worker" in source
    assert "depth_loop" in source
    assert "depth_loop.start()" in source
    assert "depth_loop.stop()" in source
    # Graceful degrade path when depth extra missing
    assert "uv sync --extra depth" in source or "depth extra" in source.lower()
    # Stop depth before bare capture loop.stop() in finally
    depth_stop = source.index("depth_loop.stop()")
    bare_stop = None
    for line in source.splitlines():
        if line.strip() == "loop.stop()":
            bare_stop = source.index(line)
            break
    assert bare_stop is not None
    assert depth_stop < bare_stop
    # Enabled banner for relative DAV2 Small
    assert "DAV2" in source or "relative" in source


def test_serve_source_wires_free_space_loop_lifecycle() -> None:
    """serve always constructs FreeSpaceLoop (CPU Spatial Post; no ML extra)."""
    source = inspect.getsource(cli_mod.serve)
    assert "FreeSpaceLoop" in source
    assert "free_space_loop" in source
    assert "free_space_loop.start()" in source
    assert "free_space_loop.stop()" in source
    # Always-on banner — no ImportError / extra gate for free-space
    assert "near-field bands" in source.lower() or "free-space: enabled" in source
    # No ML extra install hint for free-space (CPU Spatial Post only)
    assert "uv sync --extra free" not in source
    # Start free_space after depth start (when depth present); stop free_space
    # before depth stop.
    free_start = source.index("free_space_loop.start()")
    free_stop = source.index("free_space_loop.stop()")
    depth_start = source.index("depth_loop.start()")
    depth_stop = source.index("depth_loop.stop()")
    bare_stop = None
    for line in source.splitlines():
        if line.strip() == "loop.stop()":
            bare_stop = source.index(line)
            break
    assert bare_stop is not None
    assert depth_start < free_start
    assert free_stop < depth_stop < bare_stop


def test_serve_source_wires_pipeline_state() -> None:
    """serve constructs PipelineState and injects loops into create_app (UI-03)."""
    source = inspect.getsource(cli_mod.serve)
    assert "PipelineState" in source
    assert "pipeline_state" in source
    assert "detection_loop" in source
    assert "depth_loop" in source
    assert "free_space_loop" in source
    # Stage toggles must not stop CaptureLoop — no stop()/start() for enable.
    # create_app receives pipeline_state and loop refs.
    assert "pipeline_state=pipeline_state" in source
    assert "detection_loop=det_loop" in source
    assert "depth_loop=depth_loop" in source
    assert "free_space_loop=free_space_loop" in source


def test_serve_does_not_import_torch_at_module_level() -> None:
    """Bare smoke path: cli module must not hard-import torch."""
    source = inspect.getsource(cli_mod)
    # Top of module / unconditional imports should not pull torch.
    assert "import torch" not in source.split("def serve")[0]
    assert "import transformers" not in source.split("def serve")[0]


def test_serve_source_wires_open_vocab_loop_lifecycle() -> None:
    """serve constructs OpenVocabLoop when detect extra available; default off."""
    source = inspect.getsource(cli_mod.serve)
    assert "OpenVocabLoop" in source
    assert "YoloeOpenVocabWorker" in source
    assert "open_vocab_worker" in source
    assert "open_vocab_loop" in source
    assert "ov_loop.start()" in source
    assert "ov_loop.stop()" in source
    # Default mode off (not continuous by default)
    assert "mode off" in source.lower() or "default mode off" in source.lower()
    # Start after free_space; stop before free_space stop
    free_start = source.index("free_space_loop.start()")
    ov_start = source.index("ov_loop.start()")
    ov_stop = source.index("ov_loop.stop()")
    free_stop = source.index("free_space_loop.stop()")
    assert free_start < ov_start
    assert ov_stop < free_stop
    # Injected into create_app
    assert "open_vocab_worker=ov_worker" in source
    assert "open_vocab_loop=ov_loop" in source


def test_serve_applies_profile_runtime() -> None:
    """EDGE-02 / EDGE-RT-02: serve uses factory + profile_runtime for workers."""
    source = inspect.getsource(cli_mod.serve)
    assert "profile_runtime" in source
    assert "tier_to_open_vocab_weight" in source
    # Fixed-class detection via factory (not inline YoloDetectionWorker)
    assert "build_detection_worker" in source
    assert "DetectionLoop" in source
    assert "backend_requested" in source
    assert "backend_live" in source
    assert "backend_reason" in source
    # Open-vocab / depth still take profile weights + device directly
    assert "rt.open_vocab_weights" in source
    assert "rt.depth_model_id" in source
    assert "device=rt.device" in source
    assert "probe_device" in source
    # Banner honesty fields (full BACK-02 rewrite lands in 08-02)
    assert "preferred_backend" in source
    assert "tensorrt" in source
    assert "onnxruntime" in source
    # No hard-coded fixed-class YoloDetectionWorker construction in serve
    assert "YoloDetectionWorker(" not in source


def test_serve_profile_default_is_cpu_fallback() -> None:
    """Serve default profile remains cpu-fallback (no CUDA auto-switch)."""
    out = cli_help_output(app, "serve", "--help")
    assert "cpu-fallback" in out
    lower = out.lower()
    assert "model tier" in lower or "device policy" in lower or "profile" in lower


def test_serve_help_shows_no_ui() -> None:
    """EDGE-05: serve --help documents --no-ui headless flag."""
    out = cli_help_output(app, "serve", "--help")
    assert "--no-ui" in out
    lower = out.lower()
    assert "headless" in lower or "live preview" in lower or "ui" in lower


def test_serve_source_wires_headless_no_ui() -> None:
    """EDGE-05: serve passes serve_ui=not no_ui into create_app."""
    source = inspect.getsource(cli_mod.serve)
    assert "no_ui" in source
    assert "serve_ui" in source
    assert "serve_ui=not no_ui" in source
    assert "headless" in source.lower()
