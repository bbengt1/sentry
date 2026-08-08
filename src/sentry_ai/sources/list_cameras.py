"""Enumerate local OpenCV camera device indices.

Probes integer ``VideoCapture`` indices only (USB UVC, built-in FaceTime,
Continuity Camera / virtual devices on macOS, etc.). Does not list RTSP URLs
or file paths.

Opens each index briefly, reads properties, then releases — never leaves
captures open.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LocalCameraInfo:
    """One probed local capture index."""

    index: int
    available: bool
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    backend: str | None = None
    error: str | None = None


def _backend_name(cv2: Any, cap: Any) -> str | None:
    """Best-effort OpenCV backend name for an open capture."""
    try:
        backend_id = int(cap.get(cv2.CAP_PROP_BACKEND))
    except Exception:  # noqa: BLE001 — property may not exist
        return None
    try:
        # OpenCV 4.5+: maps backend id → string when available
        name = cv2.videoio_registry.getBackendName(backend_id)
        if name:
            return str(name)
    except Exception:  # noqa: BLE001
        pass
    return str(backend_id) if backend_id >= 0 else None


def probe_camera_index(index: int, *, cv2_module: Any | None = None) -> LocalCameraInfo:
    """Probe a single device index; always release the capture."""
    cv2 = cv2_module
    if cv2 is None:
        import cv2 as cv2_imported

        cv2 = cv2_imported

    cap: Any | None = None
    try:
        cap = cv2.VideoCapture(index)
        if cap is None or not cap.isOpened():
            return LocalCameraInfo(
                index=index,
                available=False,
                error="not opened",
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
        fps_raw = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        fps = fps_raw if fps_raw > 0 else None
        backend = _backend_name(cv2, cap)

        # Optional: grab one frame to confirm the device actually streams.
        # Some virtual devices open but fail on first read until permission.
        ok, _frame = cap.read()
        if not ok:
            return LocalCameraInfo(
                index=index,
                available=False,
                width=width,
                height=height,
                fps=fps,
                backend=backend,
                error="opened but failed to read a frame (permission? busy?)",
            )

        return LocalCameraInfo(
            index=index,
            available=True,
            width=width,
            height=height,
            fps=fps,
            backend=backend,
            error=None,
        )
    except Exception as exc:  # noqa: BLE001 — surface probe failures cleanly
        return LocalCameraInfo(
            index=index,
            available=False,
            error=str(exc) or type(exc).__name__,
        )
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:  # noqa: BLE001
                pass


def list_local_cameras(
    *,
    max_index: int = 8,
    include_unavailable: bool = False,
    cv2_module: Any | None = None,
) -> list[LocalCameraInfo]:
    """Probe indices ``0..max_index`` inclusive.

    Parameters
    ----------
    max_index:
        Highest device index to try (inclusive). Default 8 covers typical
        multi-device Mac setups (built-in + Continuity + extras).
    include_unavailable:
        If True, also return indices that failed to open (useful for debugging).
    cv2_module:
        Optional OpenCV module inject for tests.
    """
    if max_index < 0:
        raise ValueError(f"max_index must be >= 0, got {max_index}")

    found: list[LocalCameraInfo] = []
    for index in range(max_index + 1):
        info = probe_camera_index(index, cv2_module=cv2_module)
        if info.available or include_unavailable:
            found.append(info)
    return found


def format_camera_list(
    cameras: list[LocalCameraInfo],
    *,
    max_index: int,
) -> str:
    """Human-readable table for CLI output."""
    lines: list[str] = [
        "Local cameras (OpenCV device indices)",
        f"Probed indices 0..{max_index}",
        "",
    ]

    available = [c for c in cameras if c.available]
    if not available and not cameras:
        lines.append("  (none found)")
        lines.append("")
        lines.append("Tips:")
        lines.append(
            "  • Grant Camera permission to Terminal / your IDE "
            "(macOS System Settings)."
        )
        lines.append(
            "  • Quit apps that may hold the camera "
            "(Zoom, Meet, Photo Booth)."
        )
        lines.append("  • Try a higher range: sentry cameras --max-index 12")
        lines.append(
            "  • On macOS, Continuity Camera (iPhone) may appear "
            "as an extra index."
        )
        lines.append("")
        lines.append("Then: uv run sentry serve --source usb --device <INDEX>")
        return "\n".join(lines)

    # Header
    lines.append(
        f"  {'INDEX':<6} {'OPEN':<5} {'SIZE':<12} {'FPS':<8} {'BACKEND':<14} NOTES"
    )
    lines.append(
        f"  {'-----':<6} {'----':<5} {'----':<12} {'---':<8} {'-------':<14} -----"
    )

    for cam in cameras:
        size = (
            f"{cam.width}x{cam.height}"
            if cam.width and cam.height
            else "-"
        )
        fps = f"{cam.fps:.1f}" if cam.fps is not None else "-"
        backend = (cam.backend or "-")[:14]
        open_s = "yes" if cam.available else "no"
        notes: list[str] = []
        if not cam.available and cam.error:
            notes.append(cam.error)
        # Soft hint for multi-device Macs — not proven per index.
        if cam.available and cam.index > 0:
            notes.append("may be Continuity / virtual device on macOS")
        note = "; ".join(notes)
        lines.append(
            f"  {cam.index:<6} {open_s:<5} {size:<12} {fps:<8} {backend:<14} {note}"
        )

    lines.append("")
    lines.append("Use with serve:")
    lines.append("  uv run sentry serve --source usb --device <INDEX>")
    lines.append("")
    lines.append(
        "Note: On macOS, device indices often include FaceTime, Continuity Camera "
        "(iPhone), and other virtual cameras — not only physical USB webcams."
    )
    return "\n".join(lines)
