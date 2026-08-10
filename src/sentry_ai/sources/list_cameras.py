"""Enumerate local camera devices for ``sentry cameras``.

Strategies (combined):

1. **macOS AVFoundation** (preferred names / Continuity): Swift
   ``AVCaptureDevice.DiscoverySession`` including ``continuityCamera``,
   ``external``, ``deskViewCamera``, and built-in wide angle. Falls back to
   ``ffmpeg -f avfoundation -list_devices`` when Swift is unavailable.
2. **OpenCV index probe**: open ``VideoCapture(i[, CAP_AVFOUNDATION])``,
   confirm a frame can be read, report size/FPS.

Continuity Camera only appears in system discovery when the iPhone is nearby
with Continuity Camera available (Bluetooth/Wi‑Fi, same Apple ID, feature on).
OpenCV may still fail to open a Continuity device even when AVFoundation
lists it — we surface the name and a clear note in that case.
"""

from __future__ import annotations

import platform
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class LocalCameraInfo:
    """One local camera entry (OpenCV index and/or AVFoundation identity)."""

    index: int | None
    available: bool
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    backend: str | None = None
    name: str | None = None
    device_type: str | None = None
    unique_id: str | None = None
    error: str | None = None
    notes: tuple[str, ...] = ()


# Embedded Swift: macOS DiscoverySession including Continuity Camera types.
# Compiled once into ~/.cache/sentry-ai/bin/list_av_cameras.
_SWIFT_LIST_CAMERAS = r"""
import AVFoundation
import Foundation

var types: [AVCaptureDevice.DeviceType] = [
    .builtInWideAngleCamera,
    .external,
]
if #available(macOS 13.0, *) {
    types.append(.continuityCamera)
}
if #available(macOS 14.0, *) {
    types.append(.deskViewCamera)
}

let session = AVCaptureDevice.DiscoverySession(
    deviceTypes: types,
    mediaType: .video,
    position: .unspecified
)

for (i, d) in session.devices.enumerated() {
    let name = d.localizedName
        .replacingOccurrences(of: "|", with: "/")
        .replacingOccurrences(of: "\n", with: " ")
    let dtype = d.deviceType.rawValue
        .replacingOccurrences(of: "|", with: "/")
    let uid = d.uniqueID
        .replacingOccurrences(of: "|", with: "/")
    var flags: [String] = []
    if #available(macOS 13.0, *) {
        if d.isContinuityCamera { flags.append("continuity") }
    }
    if #available(macOS 14.0, *) {
        // Desk View / multi-cam related flags if present
    }
    let flagStr = flags.joined(separator: ",")
    print("\(i)|\(name)|\(dtype)|\(uid)|\(flagStr)")
}
"""


def _is_macos() -> bool:
    return platform.system() == "Darwin"


def _cache_bin_dir() -> Path:
    return Path.home() / ".cache" / "sentry-ai" / "bin"


def _swift_binary_path() -> Path:
    return _cache_bin_dir() / "list_av_cameras"


def _ensure_swift_lister(
    *,
    run_subprocess: Any | None = None,
) -> Path | None:
    """Compile embedded Swift helper once; return path or None if unavailable."""
    run = run_subprocess or subprocess.run
    if shutil.which("swift") is None:
        return None

    binary = _swift_binary_path()
    if binary.is_file() and binary.stat().st_size > 0:
        return binary

    binary.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="sentry-av-") as tmp:
            src = Path(tmp) / "list_av_cameras.swift"
            src.write_text(_SWIFT_LIST_CAMERAS, encoding="utf-8")
            # swiftc produces a standalone binary (faster subsequent runs).
            compiler = shutil.which("swiftc") or "swiftc"
            proc = run(
                [compiler, "-O", "-o", str(binary), str(src)],
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
            if proc.returncode != 0 or not binary.is_file():
                # Fallback: interpret with `swift` each time (slow but works).
                return None
            binary.chmod(0o755)
            return binary
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return None


def list_avfoundation_devices_swift(
    *,
    run_subprocess: Any | None = None,
) -> list[dict[str, str]]:
    """List macOS AVFoundation video devices via Swift DiscoverySession."""
    run = run_subprocess or subprocess.run
    devices: list[dict[str, str]] = []

    binary = _ensure_swift_lister(run_subprocess=run)
    try:
        if binary is not None:
            proc = run(
                [str(binary)],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        elif shutil.which("swift") is not None:
            with tempfile.TemporaryDirectory(prefix="sentry-av-") as tmp:
                src = Path(tmp) / "list_av_cameras.swift"
                src.write_text(_SWIFT_LIST_CAMERAS, encoding="utf-8")
                proc = run(
                    ["swift", str(src)],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    check=False,
                )
        else:
            return []
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return []

    if proc.returncode != 0:
        return []

    for line in (proc.stdout or "").splitlines():
        line = line.strip()
        if not line or line.count("|") < 3:
            continue
        parts = line.split("|", 4)
        while len(parts) < 5:
            parts.append("")
        idx_s, name, dtype, uid, flags = parts
        devices.append(
            {
                "av_index": idx_s.strip(),
                "name": name.strip(),
                "device_type": dtype.strip(),
                "unique_id": uid.strip(),
                "flags": flags.strip(),
            }
        )
    return devices


def list_avfoundation_devices_ffmpeg(
    *,
    run_subprocess: Any | None = None,
) -> list[dict[str, str]]:
    """Parse ``ffmpeg -f avfoundation -list_devices`` video device names."""
    run = run_subprocess or subprocess.run
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return []

    try:
        proc = run(
            [
                ffmpeg,
                "-hide_banner",
                "-f",
                "avfoundation",
                "-list_devices",
                "true",
                "-i",
                "",
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return []

    # Device lines go to stderr.
    text = (proc.stderr or "") + "\n" + (proc.stdout or "")
    devices: list[dict[str, str]] = []
    in_video = False
    # Examples:
    # [AVFoundation indev @ 0x…] [0] FaceTime HD Camera
    # [AVFoundation indev @ 0x…] [1] Capture screen 0
    line_re = re.compile(
        r"\[(\d+)\]\s+(.+?)\s*$"
    )
    for raw in text.splitlines():
        line = raw.strip()
        lower = line.lower()
        if "avfoundation video devices" in lower:
            in_video = True
            continue
        if "avfoundation audio devices" in lower:
            in_video = False
            continue
        if not in_video:
            continue
        match = line_re.search(line)
        if not match:
            continue
        idx, name = match.group(1), match.group(2).strip()
        # Skip pure screen captures as cameras (still show with note).
        dtype = "screen" if "capture screen" in name.lower() else "avfoundation"
        devices.append(
            {
                "av_index": idx,
                "name": name,
                "device_type": dtype,
                "unique_id": "",
                "flags": "screen" if dtype == "screen" else "",
            }
        )
    return devices


def list_macos_av_devices(
    *,
    run_subprocess: Any | None = None,
) -> list[dict[str, str]]:
    """Prefer Swift Continuity-aware discovery; fall back to ffmpeg."""
    devices = list_avfoundation_devices_swift(run_subprocess=run_subprocess)
    if devices:
        return devices
    return list_avfoundation_devices_ffmpeg(run_subprocess=run_subprocess)


def _backend_name(cv2: Any, cap: Any) -> str | None:
    """Best-effort OpenCV backend name for an open capture."""
    try:
        backend_id = int(cap.get(cv2.CAP_PROP_BACKEND))
    except Exception:  # noqa: BLE001
        return None
    try:
        name = cv2.videoio_registry.getBackendName(backend_id)
        if name:
            return str(name)
    except Exception:  # noqa: BLE001
        pass
    return str(backend_id) if backend_id >= 0 else None


def _opencv_open_kwargs(cv2: Any) -> dict[str, Any]:
    """Prefer AVFoundation on macOS so indices align with system cameras."""
    if _is_macos() and hasattr(cv2, "CAP_AVFOUNDATION"):
        return {"apiPreference": cv2.CAP_AVFOUNDATION}
    return {}


def probe_camera_index(
    index: int,
    *,
    cv2_module: Any | None = None,
    name: str | None = None,
    device_type: str | None = None,
    unique_id: str | None = None,
    extra_notes: tuple[str, ...] = (),
) -> LocalCameraInfo:
    """Probe a single device index; always release the capture."""
    cv2 = cv2_module
    if cv2 is None:
        import cv2 as cv2_imported

        cv2 = cv2_imported

    open_kw = _opencv_open_kwargs(cv2)
    cap: Any | None = None
    try:
        if open_kw:
            cap = cv2.VideoCapture(index, open_kw["apiPreference"])
        else:
            cap = cv2.VideoCapture(index)
        if cap is None or not cap.isOpened():
            return LocalCameraInfo(
                index=index,
                available=False,
                name=name,
                device_type=device_type,
                unique_id=unique_id,
                error="not opened by OpenCV",
                notes=extra_notes,
            )

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0) or None
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0) or None
        fps_raw = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        fps = fps_raw if fps_raw > 0 else None
        backend = _backend_name(cv2, cap)

        ok, _frame = cap.read()
        if not ok:
            return LocalCameraInfo(
                index=index,
                available=False,
                width=width,
                height=height,
                fps=fps,
                backend=backend,
                name=name,
                device_type=device_type,
                unique_id=unique_id,
                error="opened but failed to read a frame (permission? busy?)",
                notes=extra_notes,
            )

        return LocalCameraInfo(
            index=index,
            available=True,
            width=width,
            height=height,
            fps=fps,
            backend=backend,
            name=name,
            device_type=device_type,
            unique_id=unique_id,
            error=None,
            notes=extra_notes,
        )
    except Exception as exc:  # noqa: BLE001
        return LocalCameraInfo(
            index=index,
            available=False,
            name=name,
            device_type=device_type,
            unique_id=unique_id,
            error=str(exc) or type(exc).__name__,
            notes=extra_notes,
        )
    finally:
        if cap is not None:
            try:
                cap.release()
            except Exception:  # noqa: BLE001
                pass


def _notes_for_av_device(dev: dict[str, str]) -> tuple[str, ...]:
    notes: list[str] = []
    dtype = (dev.get("device_type") or "").lower()
    flags = (dev.get("flags") or "").lower()
    name = (dev.get("name") or "").lower()
    if "continuity" in dtype or "continuity" in flags:
        notes.append("Continuity Camera")
    if "deskview" in dtype or "desk view" in name:
        notes.append("Desk View")
    if "external" in dtype:
        notes.append("external")
    if "screen" in dtype or "capture screen" in name:
        notes.append("screen capture (not a USB camera)")
    if "iphone" in name or "ipad" in name:
        notes.append("iOS device")
    return tuple(notes)


def list_local_cameras(
    *,
    max_index: int = 8,
    include_unavailable: bool = False,
    cv2_module: Any | None = None,
    run_subprocess: Any | None = None,
    use_avfoundation: bool = True,
) -> list[LocalCameraInfo]:
    """List local cameras by merging AVFoundation names with OpenCV probes.

    Parameters
    ----------
    max_index:
        Highest OpenCV index to probe when AVFoundation does not supply a
        richer list (inclusive).
    include_unavailable:
        Include indices/devices OpenCV could not open.
    cv2_module:
        Injectable OpenCV module for tests.
    run_subprocess:
        Injectable ``subprocess.run`` for tests.
    use_avfoundation:
        On macOS, query AVFoundation for names (incl. Continuity).
    """
    if max_index < 0:
        raise ValueError(f"max_index must be >= 0, got {max_index}")

    av_devices: list[dict[str, str]] = []
    if use_avfoundation and _is_macos():
        av_devices = list_macos_av_devices(run_subprocess=run_subprocess)

    # Build name map by av_index (often matches OpenCV CAP_AVFOUNDATION index).
    by_index: dict[int, dict[str, str]] = {}
    for dev in av_devices:
        try:
            idx = int(dev["av_index"])
        except (KeyError, ValueError):
            continue
        by_index[idx] = dev

    # OpenCV on macOS typically only has a small set of streamable indices
    # (often 0–1). Probing 0..8 when AVFoundation lists 3 named devices
    # floods stderr with "out device of bound" noise. Probe only:
    #   - AVFoundation-listed video indices, and
    #   - 0..max_index for unlisted UVC (when no AV list).
    # Skip Desk View / screen captures without opening OpenCV.
    if by_index:
        probe_indices = sorted(by_index.keys())
    else:
        probe_indices = list(range(max_index + 1))

    found: list[LocalCameraInfo] = []

    for index in probe_indices:
        if index > max_index and index not in by_index:
            continue
        dev = by_index.get(index)
        name = dev["name"] if dev else None
        dtype = dev["device_type"] if dev else None
        uid = dev.get("unique_id") if dev else None
        notes = _notes_for_av_device(dev) if dev else ()

        # Screen captures / Desk View are not useful as ``--source usb``.
        notes_joined = " ".join(notes).lower()
        dtype_l = (dtype or "").lower()
        if dev and (
            "screen capture" in notes_joined
            or "deskview" in dtype_l
            or "desk view" in notes_joined
        ):
            found.append(
                LocalCameraInfo(
                    index=index,
                    available=False,
                    name=name,
                    device_type=dtype,
                    unique_id=uid,
                    error="not a USB OpenCV camera (Desk View / screen)",
                    notes=notes + ("not usable with --source usb",),
                )
            )
            continue

        info = probe_camera_index(
            index,
            cv2_module=cv2_module,
            name=name,
            device_type=dtype,
            unique_id=uid,
            extra_notes=notes,
        )

        if info.available:
            found.append(info)
            continue

        if include_unavailable:
            found.append(info)
            continue

        # Always surface AVFoundation-named devices even when OpenCV cannot
        # open them (Continuity often lists before it is fully streamable).
        if dev is not None and name:
            found.append(
                replace(
                    info,
                    notes=info.notes
                    + ("listed by AVFoundation; OpenCV could not open",),
                )
            )

    return found


def format_camera_list(
    cameras: list[LocalCameraInfo],
    *,
    max_index: int,
    av_device_count: int | None = None,
    continuity_hint: bool = True,
) -> str:
    """Human-readable table for CLI output."""
    if av_device_count and av_device_count > 0:
        range_line = (
            f"AVFoundation listed {av_device_count} video device(s); "
            f"OpenCV probed named indices only (use OPEN=yes with serve)"
        )
    else:
        range_line = f"OpenCV probe range: 0..{max_index}"
    lines: list[str] = [
        "Local cameras",
        range_line,
        "",
    ]

    if not cameras:
        lines.append("  (none found)")
        lines.append("")
        lines.extend(_empty_tips(continuity_hint=continuity_hint))
        return "\n".join(lines)

    # Header with NAME for Continuity / FaceTime identification
    lines.append(
        f"  {'IDX':<4} {'OPEN':<5} {'NAME':<28} {'SIZE':<11} "
        f"{'FPS':<6} {'TYPE':<18} NOTES"
    )
    lines.append(
        f"  {'---':<4} {'----':<5} {'----':<28} {'----':<11} "
        f"{'---':<6} {'----':<18} -----"
    )

    has_continuity = False
    for cam in cameras:
        size = (
            f"{cam.width}x{cam.height}"
            if cam.width and cam.height
            else "-"
        )
        fps = f"{cam.fps:.0f}" if cam.fps is not None else "-"
        open_s = "yes" if cam.available else "no"
        name = (cam.name or "(unnamed)")[:28]
        dtype_raw = cam.device_type or ""
        # Shorten AVCaptureDeviceType* for display
        dtype = dtype_raw.replace("AVCaptureDeviceType", "") or "-"
        dtype = dtype[:18]
        notes: list[str] = list(cam.notes)
        if cam.error and not cam.available:
            notes.append(cam.error)
        cont = any("continuity" in n.lower() for n in notes)
        if cont or "continuity" in dtype.lower():
            has_continuity = True
        note = "; ".join(notes)
        idx_s = "-" if cam.index is None else str(cam.index)
        lines.append(
            f"  {idx_s:<4} {open_s:<5} {name:<28} {size:<11} "
            f"{fps:<6} {dtype:<18} {note}"
        )

    lines.append("")
    lines.append("Use with serve:")
    lines.append("  uv run sentry serve --source usb --device <IDX>")
    lines.append("")
    if continuity_hint and _is_macos() and not has_continuity:
        lines.extend(_continuity_missing_tips())
    elif continuity_hint and _is_macos():
        lines.append(
            "Continuity Camera: use the IDX next to the Continuity / iPhone "
            "entry (OPEN=yes required for OpenCV serve)."
        )
        lines.append("")
    lines.append(
        "Note: On macOS, indices may include FaceTime, Continuity Camera "
        "(iPhone), external webcams, and virtual devices."
    )
    return "\n".join(lines)


def _empty_tips(*, continuity_hint: bool) -> list[str]:
    lines = [
        "Tips:",
        "  • Grant Camera permission to Terminal / your IDE "
        "(macOS System Settings → Privacy & Security → Camera).",
        "  • Quit apps that may hold the camera "
        "(Zoom, Meet, Photo Booth, FaceTime).",
        "  • Try: sentry cameras --max-index 12 --all",
    ]
    if continuity_hint and _is_macos():
        lines.extend(_continuity_missing_tips())
    lines.append("Then: uv run sentry serve --source usb --device <IDX>")
    return lines


def _continuity_missing_tips() -> list[str]:
    return [
        "Continuity Camera not listed right now. To make an iPhone appear:",
        "  • iPhone on same Apple ID, Bluetooth + Wi‑Fi on, nearby",
        "  • iOS: Settings → General → AirPlay & Continuity → Continuity Camera on",
        "  • Unlock iPhone; leave Continuity Camera free (not in use elsewhere)",
        "  • macOS Ventura+: Continuity is automatic when the iPhone is available",
        "  • Re-run: uv run sentry cameras",
        "  • If OPEN=no, OpenCV cannot open it yet — try again when active",
        "",
    ]
