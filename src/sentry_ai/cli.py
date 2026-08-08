"""Sentry AI CLI — health, synthetic smoke, and localhost serve.

Smoke validates synthetic ImageFrame → PerceptionFrame paths without
hardware cameras, torch, or cloud API keys (MODEL-01 / FOUND-05).

``sentry serve`` starts capture + FastAPI Live Preview (UI-01 / MODEL-03).
"""

from __future__ import annotations

import sys
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


def _build_registry() -> PluginRegistry:
    registry = PluginRegistry()
    register_builtins(registry)
    registry.discover()
    return registry


def _build_serve_source(
    *,
    source: str,
    device: int,
    path: str | None,
    url: str | None,
    camera_id: str | None,
) -> Any:
    """Construct a camera source instance for ``sentry serve``."""
    name = source.strip().lower()
    if name == "synthetic":
        return SyntheticSource(
            camera_id=camera_id or "synthetic0",
            fps=30.0,
        )
    if name == "usb":
        from sentry_ai.sources.opencv_source import UsbSource

        return UsbSource(
            device=device,
            camera_id=camera_id or f"usb{device}",
        )
    if name == "file":
        if not path:
            typer.echo(
                "serve failed: --source file requires --path",
                err=True,
            )
            raise typer.Exit(code=1)
        from sentry_ai.sources.opencv_source import FileSource

        return FileSource(
            path=path,
            camera_id=camera_id or "file0",
            loop_file=True,
        )
    if name == "rtsp":
        if not url:
            typer.echo(
                "serve failed: --source rtsp requires --url",
                err=True,
            )
            raise typer.Exit(code=1)
        from sentry_ai.sources.opencv_source import RtspSource

        return RtspSource(
            url=url,
            camera_id=camera_id or "rtsp0",
            loop_file=False,
        )
    typer.echo(
        f"serve failed: unknown source {source!r} "
        "(expected synthetic|usb|file|rtsp)",
        err=True,
    )
    raise typer.Exit(code=1)


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


@app.command()
def serve(
    source: str = typer.Option(
        "synthetic",
        help="Source plugin: synthetic | usb | file | rtsp.",
    ),
    host: str = typer.Option(
        "127.0.0.1",
        help=(
            "Bind host (default localhost — MODEL-03). "
            "Setting 0.0.0.0 exposes the live camera on the LAN without auth "
            "(opt-in only)."
        ),
    ),
    port: int = typer.Option(
        8000,
        help="Bind port.",
    ),
    device: int = typer.Option(
        0,
        help="USB device index for --source usb.",
    ),
    path: str | None = typer.Option(
        None,
        help="Filesystem path for --source file.",
    ),
    url: str | None = typer.Option(
        None,
        help="RTSP/HTTP URL for --source rtsp.",
    ),
    profile: str = typer.Option(
        "cpu-fallback",
        help="Runtime profile name (loaded for consistency; no ML).",
    ),
    camera_id: str | None = typer.Option(
        None,
        help="Optional camera_id override for Frame identity.",
    ),
) -> None:
    """Start capture + localhost Live Preview (MJPEG + status).

    Default bind is 127.0.0.1 (not 0.0.0.0). Open
    http://127.0.0.1:8000/ in a browser when using defaults.
    """
    # Validate profile early (same local-OSS constraint as smoke).
    try:
        cfg = load_config(profile=profile)
    except (ValueError, FileNotFoundError, ValidationError) as exc:
        typer.echo(f"serve failed: config error: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    if cfg.models.allow_cloud:
        typer.echo(
            "serve failed: allow_cloud is true; default path must stay local OSS",
            err=True,
        )
        raise typer.Exit(code=1)

    from sentry_ai.api.app import create_app
    from sentry_ai.bus.frame_bus import FrameBus
    from sentry_ai.capture.loop import CaptureLoop
    from sentry_ai.state.perception_store import PerceptionStore

    src = _build_serve_source(
        source=source,
        device=device,
        path=path,
        url=url,
        camera_id=camera_id,
    )
    bus = FrameBus()
    loop = CaptureLoop(src, bus)
    store = PerceptionStore()
    bind = f"{host}:{port}"

    # Optional fixed-class detection (requires `uv sync --extra detect`).
    worker: Any | None = None
    det_loop: Any | None = None
    try:
        from sentry_ai.models.cache import configure_model_cache, tier_to_weight
        from sentry_ai.models.detection.loop import DetectionLoop
        from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker

        configure_model_cache()
        weights = tier_to_weight(cfg.models.detector_tier)
        worker = YoloDetectionWorker(weights=weights, conf=0.25)
        det_loop = DetectionLoop(bus, worker, store)
    except ImportError as exc:
        typer.echo(
            "detection disabled: detect extra not installed "
            f"({exc}). Install with: uv sync --extra detect",
            err=True,
        )
        worker = None
        det_loop = None

    # Optional monocular depth (requires `uv sync --extra depth`).
    depth_worker: Any | None = None
    depth_loop: Any | None = None
    try:
        from sentry_ai.models.cache import configure_model_cache
        from sentry_ai.models.depth.loop import DepthLoop
        from sentry_ai.models.depth.worker import DepthAnythingWorker

        configure_model_cache()  # HF_HOME under SENTRY_MODEL_CACHE
        depth_worker = DepthAnythingWorker(depth_mode="relative")
        depth_loop = DepthLoop(bus, depth_worker, store)
    except ImportError as exc:
        typer.echo(
            "depth disabled: depth extra not installed "
            f"({exc}). Install with: uv sync --extra depth",
            err=True,
        )
        depth_worker = None
        depth_loop = None

    app_asgi = create_app(
        bus=bus,
        capture_loop=loop,
        bind=bind,
        perception_store=store,
        detection_worker=worker,
        depth_worker=depth_worker,
    )

    typer.echo(f"sentry-ai {__version__} serve")
    typer.echo(f"source: {src.name} camera_id={getattr(src, 'camera_id', src.name)}")
    typer.echo(f"bind: http://{bind}/  (Live Preview)")
    if det_loop is not None:
        typer.echo("detection: enabled (fixed-class YOLO)")
    else:
        typer.echo("detection: disabled (capture-only preview)")
    if depth_loop is not None:
        typer.echo("depth: enabled (DAV2 Small relative)")
    else:
        typer.echo("depth: disabled (install: uv sync --extra depth)")
    if host not in ("127.0.0.1", "localhost", "::1"):
        typer.echo(
            "warning: non-localhost bind exposes the live camera stream "
            "without authentication",
            err=True,
        )

    # Start order: capture → det → depth; stop reverse.
    loop.start()
    if det_loop is not None:
        det_loop.start()
    if depth_loop is not None:
        depth_loop.start()
    try:
        import uvicorn

        uvicorn.run(app_asgi, host=host, port=port, log_level="info")
    finally:
        if depth_loop is not None:
            depth_loop.stop()
        if det_loop is not None:
            det_loop.stop()
        loop.stop()


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
