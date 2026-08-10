"""Sentry AI CLI — health, cameras, synthetic smoke, and localhost serve.

Smoke validates synthetic ImageFrame → PerceptionFrame paths without
hardware cameras, torch, or cloud API keys (MODEL-01 / FOUND-05).

``sentry cameras`` lists local OpenCV device indices (USB / built-in /
Continuity Camera on macOS).

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
    device: int | str,
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
        from sentry_ai.sources.list_cameras import (
            _is_continuity_camera,
            resolve_usb_device,
        )
        from sentry_ai.sources.opencv_source import UsbSource

        try:
            idx, info = resolve_usb_device(device)
        except ValueError as exc:
            typer.echo(f"serve failed: {exc}", err=True)
            raise typer.Exit(code=1) from exc
        label = (info.name if info and info.name else None) or f"index {idx}"
        typer.echo(f"usb camera: IDX {idx} — {label}")
        if info is not None and info.notes:
            notes = "; ".join(info.notes)
            if notes:
                typer.echo(f"usb notes: {notes}")

        # Continuity: open ONLY by AVFoundation uniqueID.
        # OpenCV / FFmpeg *indices* labeled Continuity almost always deliver
        # FaceTime (laptop) content — verified hist-corr ~0.97 vs FaceTime.
        # Never fall back to index capture for Continuity devices.
        is_cont = info is not None and _is_continuity_camera(info)
        sel = str(device).strip().lower()
        explicit_cont = sel in {"continuity", "iphone", "ipad", "ios"}
        if explicit_cont:
            is_cont = True

        if is_cont:
            uid = (info.unique_id if info is not None else None) or ""
            if not uid.strip():
                typer.echo(
                    "serve failed: Continuity Camera has no AVFoundation "
                    "uniqueID. Re-run: uv run sentry cameras  (needs Swift "
                    "DiscoverySession; xcode-select --install). "
                    "Do not use OpenCV/FFmpeg indices — they bind FaceTime.",
                    err=True,
                )
                raise typer.Exit(code=1)
            from sentry_ai.sources.avfoundation_unique import (
                AvFoundationUniqueSource,
            )

            typer.echo(
                "usb backend: AVFoundation uniqueID "
                f"(true Continuity identity: {uid[:18]}…)"
            )
            typer.echo(
                "Continuity: stream must be non-black from the iPhone. "
                "macOS may still light the laptop LED for privacy — confirm "
                "the Continuity Camera UI on the phone and that Live Preview "
                "moves when you move the phone (not the laptop)."
            )
            return AvFoundationUniqueSource(
                unique_id=uid,
                camera_id=camera_id or f"usb{idx}",
                device_label=info.name if info else label,
                require_non_black=True,
            )

        # Non-Continuity USB: prefer FFmpeg by name when available (macOS),
        # else OpenCV index. (Never use this path for Continuity — see above.)
        import platform as _platform

        if _platform.system() == "Darwin":
            try:
                from sentry_ai.sources.ffmpeg_avfoundation import (
                    FfmpegAvFoundationSource,
                    ffmpeg_available,
                    list_ffmpeg_av_video_devices,
                    match_ffmpeg_device_index,
                )

                if ffmpeg_available():
                    ff_devs = list_ffmpeg_av_video_devices()
                    preferred = info.name if info else None
                    matched = match_ffmpeg_device_index(
                        preferred,
                        prefer_continuity=False,
                        devices=ff_devs,
                    )
                    if matched is None and ff_devs:
                        for fi, fn in ff_devs:
                            if fi == idx:
                                matched = (fi, fn)
                                break
                    if matched is not None:
                        ff_idx, ff_name = matched
                        typer.echo(
                            f"usb backend: ffmpeg avfoundation "
                            f"IDX {ff_idx} — {ff_name}"
                        )
                        return FfmpegAvFoundationSource(
                            device_index=ff_idx,
                            camera_id=camera_id or f"usb{ff_idx}",
                            device_label=ff_name,
                        )
            except Exception as exc:  # noqa: BLE001
                typer.echo(
                    f"usb note: ffmpeg path failed ({exc}); using OpenCV",
                    err=True,
                )

        typer.echo("usb backend: opencv VideoCapture")
        return UsbSource(
            device=idx,
            camera_id=camera_id or f"usb{idx}",
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


@app.command("cameras")
def cameras(
    max_index: int = typer.Option(
        8,
        "--max-index",
        min=0,
        help="Highest OpenCV device index to probe (inclusive). Default 8.",
    ),
    all_indices: bool = typer.Option(
        False,
        "--all",
        help="Also show indices that failed to open (debug).",
    ),
    no_avfoundation: bool = typer.Option(
        False,
        "--no-avfoundation",
        help="Skip macOS AVFoundation name discovery (OpenCV indices only).",
    ),
) -> None:
    """List local cameras (OpenCV indices + macOS AVFoundation names).

    On macOS, uses AVFoundation DiscoverySession so Continuity Camera /
    iPhone entries appear with names when the system exposes them.
    Use IDX with: sentry serve --source usb --device <IDX>
    """
    import platform

    from sentry_ai.sources.list_cameras import (
        format_camera_list,
        list_local_cameras,
        list_macos_av_devices,
    )

    use_av = not no_avfoundation and platform.system() == "Darwin"
    av_count = 0
    if use_av:
        try:
            av_count = len(list_macos_av_devices())
        except Exception:  # noqa: BLE001
            av_count = 0

    try:
        found = list_local_cameras(
            max_index=max_index,
            include_unavailable=all_indices,
            use_avfoundation=use_av,
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(f"cameras failed: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    # Effective probe ceiling after AV expansion
    probed = max_index
    if found:
        idxs = [c.index for c in found if c.index is not None]
        if idxs:
            probed = max(probed, max(idxs))

    typer.echo(
        format_camera_list(
            found,
            max_index=probed,
            av_device_count=av_count if use_av else None,
        )
    )


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
    device: str = typer.Option(
        "auto",
        help=(
            "USB camera for --source usb: OpenCV index (e.g. 1), "
            "'auto' (prefer Continuity OPEN=yes), 'continuity', "
            "or a name substring. List with: sentry cameras"
        ),
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
        help=(
            "Runtime profile name (selects model tiers and device policy; "
            "default cpu-fallback — use desktop-gpu for CUDA)."
        ),
    ),
    camera_id: str | None = typer.Option(
        None,
        help="Optional camera_id override for Frame identity.",
    ),
    no_ui: bool = typer.Option(
        False,
        "--no-ui",
        help="Serve perception API without Live Preview HTML (EDGE-05).",
    ),
) -> None:
    """Start capture + localhost Live Preview (MJPEG + status).

    Default bind is 127.0.0.1 (not 0.0.0.0). Open
    http://127.0.0.1:8000/ in a browser when using defaults.
    Use --no-ui for headless API-only deploy (EDGE-05).
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
    from sentry_ai.backend.protocols import probe_device
    from sentry_ai.bus.frame_bus import FrameBus
    from sentry_ai.capture.loop import CaptureLoop
    from sentry_ai.config.profile_runtime import profile_runtime
    from sentry_ai.state.perception_store import PerceptionStore

    rt = profile_runtime(cfg)
    probe = probe_device(cfg.profile)

    src = _build_serve_source(
        source=source,
        device=device,
        path=path,
        url=url,
        camera_id=camera_id,
    )
    # Continuity: fail fast on black uniqueID stream before loading ML weights.
    if getattr(src, "require_non_black", False):
        try:
            src.open()
            src.close()
        except Exception as exc:  # noqa: BLE001
            typer.echo(f"serve failed: Continuity capture: {exc}", err=True)
            raise typer.Exit(code=1) from exc

    bus = FrameBus()
    loop = CaptureLoop(src, bus)
    store = PerceptionStore()
    bind = f"{host}:{port}"

    # Optional fixed-class detection (requires `uv sync --extra detect`).
    # Factory/workers import without ultralytics; probe the dep *before* starting
    # loops so missing extras do not spam every frame with ImportError.
    # backend_* locals from WorkerBuild feed banner + create_app (BACK-02).
    worker: Any | None = None
    det_loop: Any | None = None
    ov_worker: Any | None = None
    ov_loop: Any | None = None
    backend_requested: str | None = None
    backend_live: str | None = None
    backend_reason: str | None = None
    try:
        import importlib.util

        from sentry_ai.models.cache import (
            configure_model_cache,
            tier_to_open_vocab_weight,
            tier_to_weight,
        )
        from sentry_ai.models.detection.factory import build_detection_worker
        from sentry_ai.models.detection.loop import DetectionLoop
        from sentry_ai.models.detection.open_vocab_loop import OpenVocabLoop
        from sentry_ai.models.detection.yoloe_worker import YoloeOpenVocabWorker

        if importlib.util.find_spec("ultralytics") is None:
            raise ImportError(
                "ultralytics is required for detection. "
                "Install the detect extra: uv sync --extra detect"
            )

        configure_model_cache()
        # Profile-driven weights + device (EDGE-02); keep tier helpers in scope
        # so inspect-source tests and callers can see the wiring.
        _ = tier_to_weight
        _ = tier_to_open_vocab_weight
        # Factory selects loader branch from preferred_backend (EDGE-RT-02).
        build = build_detection_worker(rt, conf=0.25)
        worker = build.worker
        backend_requested = build.backend_requested
        backend_live = build.backend_live
        backend_reason = build.backend_reason
        det_loop = DetectionLoop(bus, worker, store)
        # Open-vocab twin (same detect extra); default mode off.
        ov_worker = YoloeOpenVocabWorker(
            weights=rt.open_vocab_weights,
            conf=0.25,
            device=rt.device,
        )
        ov_loop = OpenVocabLoop(bus, ov_worker, store)  # mode=off default
    except ImportError as exc:
        typer.echo(
            "detection disabled: detect extra not installed "
            f"({exc}). Install with: uv sync --extra detect",
            err=True,
        )
        worker = None
        det_loop = None
        ov_worker = None
        ov_loop = None
        backend_requested = None
        backend_live = None
        backend_reason = None

    # Optional monocular depth (requires `uv sync --extra depth`).
    # Modules import without transformers; probe the dep *before* starting the
    # loop so missing extras do not spam every frame with ImportError.
    depth_worker: Any | None = None
    depth_loop: Any | None = None
    try:
        import importlib.util

        from sentry_ai.models.cache import configure_model_cache
        from sentry_ai.models.depth.loop import DepthLoop
        from sentry_ai.models.depth.worker import DepthAnythingWorker

        if importlib.util.find_spec("transformers") is None:
            raise ImportError(
                "transformers is required for DepthAnythingWorker. "
                "Install the depth extra: uv sync --extra depth"
            )
        if importlib.util.find_spec("torch") is None:
            raise ImportError(
                "torch is required for DepthAnythingWorker. "
                "Install the depth extra: uv sync --extra depth"
            )

        configure_model_cache()  # HF_HOME under SENTRY_MODEL_CACHE
        depth_worker = DepthAnythingWorker(
            depth_mode="relative",
            model_id=rt.depth_model_id,
            device=rt.device,
        )
        depth_loop = DepthLoop(bus, depth_worker, store)
    except ImportError as exc:
        typer.echo(
            "depth disabled: depth extra not installed "
            f"({exc}). Install with: uv sync --extra depth",
            err=True,
        )
        depth_worker = None
        depth_loop = None

    # Free-space Spatial Post always runs when store exists (CPU; no ML extra).
    # Idles until a good depth product appears — no ImportError gate.
    from sentry_ai.control.pipeline_state import PipelineState
    from sentry_ai.spatial.loop import FreeSpaceLoop

    free_space_loop = FreeSpaceLoop(store)
    pipeline_state = PipelineState()

    app_asgi = create_app(
        bus=bus,
        capture_loop=loop,
        bind=bind,
        perception_store=store,
        detection_worker=worker,
        depth_worker=depth_worker,
        pipeline_state=pipeline_state,
        detection_loop=det_loop,
        depth_loop=depth_loop,
        free_space_loop=free_space_loop,
        open_vocab_worker=ov_worker,
        open_vocab_loop=ov_loop,
        backend_requested=backend_requested,
        backend_live=backend_live,
        backend_reason=backend_reason,
        serve_ui=not no_ui,
    )

    device_display = rt.device if rt.device is not None else "auto"
    typer.echo(f"sentry-ai {__version__} serve")
    typer.echo(f"profile: {rt.profile.value}")
    typer.echo(f"detector: {rt.detector_weights}")
    typer.echo(f"open-vocab: {rt.open_vocab_weights} (mode off by default)")
    typer.echo(f"depth: {rt.depth_model_id} (tier={rt.depth_tier})")
    typer.echo(f"preferred_backend: {rt.preferred_backend}")
    typer.echo(f"device: {device_display}")
    typer.echo(
        f"probe: available={probe.available} "
        f"backend={probe.backend} device_id={probe.device_id}"
    )
    # BACK-02: structured honesty fields from factory (sole author of live).
    if backend_requested is not None:
        typer.echo(f"backend_requested: {backend_requested}")
    if backend_live is not None:
        typer.echo(f"backend_live: {backend_live}")
    if backend_reason is not None:
        typer.echo(f"backend_reason: {backend_reason}", err=True)
    typer.echo(f"source: {src.name} camera_id={getattr(src, 'camera_id', src.name)}")
    if no_ui:
        typer.echo(f"bind: http://{bind}/  (headless API)")
    else:
        typer.echo(f"bind: http://{bind}/  (Live Preview)")
    if det_loop is not None:
        typer.echo("detection: enabled (fixed-class YOLO)")
    else:
        typer.echo("detection: disabled (capture-only preview)")
    if depth_loop is not None:
        typer.echo("depth: enabled (DAV2 Small relative)")
    else:
        typer.echo("depth: disabled (install: uv sync --extra depth)")
    typer.echo("free-space: enabled (near-field bands Spatial Post)")
    if ov_loop is not None:
        typer.echo("open-vocab: available (YOLOE; default mode off)")
    else:
        typer.echo("open-vocab: disabled (install: uv sync --extra detect)")
    if host not in ("127.0.0.1", "localhost", "::1"):
        typer.echo(
            "warning: non-localhost bind exposes the live camera stream "
            "without authentication",
            err=True,
        )

    # Start order: capture → det → depth → free_space → open_vocab; stop reverse.
    loop.start()
    if det_loop is not None:
        det_loop.start()
    if depth_loop is not None:
        depth_loop.start()
    free_space_loop.start()
    if ov_loop is not None:
        ov_loop.start()  # thread alive; mode=off sleeps

    def _signal_shutdown() -> None:
        """Wake MJPEG/WS generators immediately (before connection drain)."""
        flag = getattr(app_asgi.state, "shutdown_flag", None)
        if flag is not None:
            flag.set()

    def _stop_workers() -> None:
        _signal_shutdown()
        if ov_loop is not None:
            ov_loop.stop()
        free_space_loop.stop()
        if depth_loop is not None:
            depth_loop.stop()
        if det_loop is not None:
            det_loop.stop()
        loop.stop()

    try:
        import uvicorn

        # Lifespan sets shutdown_flag only *after* connections close — too late
        # for open MJPEG. handle_exit sets the flag on the first Ctrl+C so
        # generators exit during the graceful drain window.
        config = uvicorn.Config(
            app_asgi,
            host=host,
            port=port,
            log_level="info",
            timeout_graceful_shutdown=1,
        )
        server = uvicorn.Server(config)
        _orig_handle_exit = server.handle_exit

        def _handle_exit(sig: int, frame: Any) -> None:  # noqa: ANN401
            _signal_shutdown()
            _orig_handle_exit(sig, frame)

        server.handle_exit = _handle_exit  # type: ignore[method-assign]
        try:
            server.run()
        except KeyboardInterrupt:
            # Race with uvicorn signal handling; keep output quiet.
            pass
    finally:
        _stop_workers()
        typer.echo("sentry serve: stopped")


def main() -> None:
    """Console script entry point for `sentry` and `python -m sentry_ai`."""
    # Ensure non-zero exit propagates when invoked as a script.
    try:
        app()
    except KeyboardInterrupt:
        # Top-level guard so Typer/uvicorn races don't dump a full traceback.
        typer.echo("interrupted", err=True)
        sys.exit(130)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else (1 if exc.code else 0)
        sys.exit(code)


if __name__ == "__main__":
    main()
