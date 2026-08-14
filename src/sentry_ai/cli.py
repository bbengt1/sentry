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
    Use IDX with: sentry serve --source usb --device IDX
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
            # Optional pass-through stubs (no dedicated models).
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
