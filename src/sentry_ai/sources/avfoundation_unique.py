"""macOS capture by AVFoundation uniqueID (true Continuity identity).

OpenCV/FFmpeg device *indices* can open FaceTime while UI labels say Continuity.
Swift ``AVCaptureDevice(uniqueID:)`` opens the exact Continuity device identity
from ``sentry cameras`` (flag ``continuity`` + unique_id).

Helper is compiled once to ``~/.cache/sentry-ai/bin/capture_av_device``.
"""

from __future__ import annotations

import logging
import shutil
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from sentry_ai.capture.image_frame import ImageFrame
from sentry_ai.schemas.frame import Frame
from sentry_ai.sources.errors import SourceDisconnected, SourceError

logger = logging.getLogger(__name__)

__all__ = [
    "AvFoundationUniqueSource",
    "ensure_capture_av_binary",
]

# Length-prefixed JPEG frames on stdout (4-byte big-endian length + payload).
# Info.plist (embedded via -sectcreate) opts into Continuity Camera device type.
_SWIFT_CAPTURE = r"""
import AVFoundation
import CoreImage
import CoreMedia
import CoreVideo
import Foundation
import ImageIO
import UniformTypeIdentifiers

final class Recorder: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let context = CIContext(options: nil)
    let lock = NSLock()
    var lastPTS: TimeInterval = 0
    let minInterval: TimeInterval = 1.0 / 24.0
    var writing = false

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        // Serialize rate-limit + write under one lock so length-prefixed JPEGs
        // never interleave (stdout desync → huge invalid lengths).
        lock.lock()
        let now = CFAbsoluteTimeGetCurrent()
        if writing || (now - lastPTS) < minInterval {
            lock.unlock()
            return
        }
        writing = true
        lastPTS = now
        lock.unlock()
        defer {
            lock.lock()
            writing = false
            lock.unlock()
        }

        guard let pb = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        let ci = CIImage(cvPixelBuffer: pb)
        guard let cg = context.createCGImage(ci, from: ci.extent) else { return }

        let data = NSMutableData()
        guard let dest = CGImageDestinationCreateWithData(
            data, UTType.jpeg.identifier as CFString, 1, nil
        ) else { return }
        let props: [CFString: Any] = [
            kCGImageDestinationLossyCompressionQuality: 0.8
        ]
        CGImageDestinationAddImage(dest, cg, props as CFDictionary)
        guard CGImageDestinationFinalize(dest) else { return }

        var be = UInt32(data.count).bigEndian
        let header = Data(bytes: &be, count: 4)
        // Single write reduces partial-frame risk on the pipe.
        var packet = Data()
        packet.append(header)
        packet.append(data as Data)
        FileHandle.standardOutput.write(packet)
    }
}

func fail(_ msg: String) -> Never {
    fputs(msg + "\n", stderr)
    exit(1)
}

guard CommandLine.arguments.count >= 2 else {
    fail("usage: capture_av_device <uniqueID>")
}
let uid = CommandLine.arguments[1]

guard let device = AVCaptureDevice(uniqueID: uid) else {
    fail("AVCaptureDevice not found for uniqueID")
}

// Hint system preference so Continuity is treated as the active camera.
if #available(macOS 13.0, *) {
    AVCaptureDevice.userPreferredCamera = device
}

let session = AVCaptureSession()
session.beginConfiguration()
// .high lets Continuity pick a working format; fixed presets can black-screen.
session.sessionPreset = .high

let input: AVCaptureDeviceInput
do {
    input = try AVCaptureDeviceInput(device: device)
} catch {
    fail("input error: \(error)")
}
guard session.canAddInput(input) else { fail("cannot add input") }
session.addInput(input)

let output = AVCaptureVideoDataOutput()
output.alwaysDiscardsLateVideoFrames = true
output.videoSettings = [
    kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA
]
let recorder = Recorder()
let queue = DispatchQueue(label: "sentry.av.capture")
output.setSampleBufferDelegate(recorder, queue: queue)
guard session.canAddOutput(output) else { fail("cannot add output") }
session.addOutput(output)
session.commitConfiguration()

session.startRunning()
var contFlag = false
if #available(macOS 13.0, *) {
    contFlag = device.isContinuityCamera
}
fputs(
  "capture_av_device: started name=\(device.localizedName) "
  + "continuity=\(contFlag) suspended=\(device.isSuspended) "
  + "connected=\(device.isConnected) uid=\(device.uniqueID)\n",
  stderr
)

// Keep process alive
RunLoop.main.run()
"""

_INFO_PLIST = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleIdentifier</key>
  <string>ai.sentry.capture-av-device</string>
  <key>CFBundleName</key>
  <string>capture_av_device</string>
  <key>NSCameraUsageDescription</key>
  <string>Sentry AI needs camera access for Continuity Camera and USB capture.</string>
  <key>NSCameraUseContinuityCameraDeviceType</key>
  <true/>
</dict>
</plist>
"""


def _cache_bin_dir() -> Path:
    return Path.home() / ".cache" / "sentry-ai" / "bin"


def ensure_capture_av_binary(
    *,
    run_subprocess: Any | None = None,
) -> Path | None:
    """Compile Swift capture helper once; return path or None."""
    run = run_subprocess or subprocess.run
    if shutil.which("swiftc") is None:
        return None
    binary = _cache_bin_dir() / "capture_av_device"
    # Recompile if missing or source marker version changes.
    marker = _cache_bin_dir() / "capture_av_device.version"
    version = "4"  # serialize stdout packets; Continuity Info.plist
    if (
        binary.is_file()
        and binary.stat().st_size > 0
        and marker.is_file()
        and marker.read_text(encoding="utf-8").strip() == version
    ):
        return binary

    binary.parent.mkdir(parents=True, exist_ok=True)
    try:
        with tempfile.TemporaryDirectory(prefix="sentry-avcap-") as tmp:
            src = Path(tmp) / "capture_av_device.swift"
            src.write_text(_SWIFT_CAPTURE, encoding="utf-8")
            plist = Path(tmp) / "Info.plist"
            plist.write_text(_INFO_PLIST, encoding="utf-8")
            proc = run(
                [
                    "swiftc",
                    "-O",
                    "-o",
                    str(binary),
                    str(src),
                    "-framework",
                    "AVFoundation",
                    "-framework",
                    "CoreImage",
                    "-framework",
                    "CoreMedia",
                    "-framework",
                    "CoreVideo",
                    "-framework",
                    "ImageIO",
                    "-framework",
                    "UniformTypeIdentifiers",
                    "-framework",
                    "Foundation",
                    # Embed Info.plist so Continuity Camera device type is allowed.
                    "-Xlinker",
                    "-sectcreate",
                    "-Xlinker",
                    "__TEXT",
                    "-Xlinker",
                    "__info_plist",
                    "-Xlinker",
                    str(plist),
                ],
                capture_output=True,
                text=True,
                timeout=180,
                check=False,
            )
            if proc.returncode != 0 or not binary.is_file():
                logger.warning(
                    "swiftc capture_av_device failed: %s",
                    (proc.stderr or proc.stdout or "")[:500],
                )
                return None
            binary.chmod(0o755)
            marker.write_text(version, encoding="utf-8")
            return binary
    except (OSError, subprocess.SubprocessError, TimeoutError) as exc:
        logger.warning("capture_av_device compile error: %s", exc)
        return None


_CONTINUITY_BLACK_HELP = (
    "Continuity Camera opened by uniqueID but the stream is black "
    "(iPhone listed, not delivering video). OpenCV/FFmpeg indices would "
    "silently show the laptop FaceTime camera — that path is disabled. "
    "Fix Continuity, then retry:\n"
    "  • Unlock iPhone; Settings → General → AirPlay & Continuity → "
    "Continuity Camera ON\n"
    "  • Same Apple ID, Bluetooth + Wi‑Fi, phone near Mac\n"
    "  • Look for Continuity Camera UI on the iPhone lock screen while streaming\n"
    "  • Quit other apps using the camera; try Photo Booth → select iPhone camera\n"
    "  • Optional: plug iPhone in USB and Trust This Computer"
)


class AvFoundationUniqueSource:
    """Stream frames from a macOS camera opened by AVFoundation uniqueID."""

    name: str = "usb"

    def __init__(
        self,
        unique_id: str,
        *,
        camera_id: str = "usb0",
        device_label: str | None = None,
        require_non_black: bool = False,
        warm_up_seconds: float = 12.0,
    ) -> None:
        if not unique_id or not str(unique_id).strip():
            raise ValueError("unique_id is required")
        self.unique_id = str(unique_id).strip()
        self.camera_id = camera_id
        self.device_label = device_label
        self.require_non_black = bool(require_non_black)
        self.warm_up_seconds = float(warm_up_seconds)
        self._proc: subprocess.Popen[bytes] | None = None
        self._next_frame_id = 0
        self._bin: Path | None = None

    def open(self) -> None:
        self._bin = ensure_capture_av_binary()
        if self._bin is None:
            raise SourceError(
                "cannot compile Swift capture_av_device helper "
                "(need Xcode CLT: xcode-select --install)"
            )
        logger.info(
            "Opening AVFoundation uniqueID capture: %s (%s)",
            self.device_label or "camera",
            self.unique_id[:13] + "…",
        )
        try:
            self._proc = subprocess.Popen(
                [str(self._bin), self.unique_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0,
            )
        except OSError as exc:
            raise SourceError(f"failed to start capture_av_device: {exc}") from exc
        if self._proc.stdout is None:
            self.close()
            raise SourceError("capture_av_device stdout missing")

        # Wait for first *real* frame. Continuity often delivers near-black
        # frames (mean ~7–8 with JPEG noise) while iPhone is not streaming —
        # treat those as black. FaceTime desk scenes are typically mean >> 20.
        min_mean = 12.0 if self.require_non_black else 1.0
        deadline = time.time() + max(self.warm_up_seconds, 1.0)
        last_err = "no frames"
        while time.time() < deadline:
            try:
                frame = self.read()
                mean = float(np.mean(frame.image_bgr))
                # Low stddev + low mean = solid black / letterbox noise.
                std = float(np.std(frame.image_bgr))
                if mean >= min_mean and (not self.require_non_black or std >= 5.0):
                    self._next_frame_id = 0
                    logger.info(
                        "AVFoundation uniqueID warm-up ok mean=%.1f std=%.1f label=%s",
                        mean,
                        std,
                        self.device_label,
                    )
                    return
                last_err = f"black/flat frame mean={mean:.1f} std={std:.1f}"
            except SourceDisconnected as exc:
                last_err = str(exc)
                if self._proc.poll() is not None:
                    err = b""
                    if self._proc.stderr is not None:
                        err = self._proc.stderr.read() or b""
                    raise SourceError(
                        f"capture_av_device exited: {err.decode('utf-8', 'replace')}"
                    ) from exc
                time.sleep(0.05)

        if self.require_non_black:
            # Drain stderr for continuity= / suspended= diagnostics.
            extra = ""
            try:
                if self._proc is not None and self._proc.stderr is not None:
                    # Non-blocking-ish: helper writes a single start line.
                    import select

                    if select.select([self._proc.stderr], [], [], 0.05)[0]:
                        extra = (
                            self._proc.stderr.read(800) or b""
                        ).decode("utf-8", "replace")
            except Exception:  # noqa: BLE001
                pass
            self.close()
            detail = f"{_CONTINUITY_BLACK_HELP}\n(last={last_err})"
            if extra.strip():
                detail = f"{detail}\nhelper: {extra.strip()}"
            raise SourceError(detail)

        logger.warning(
            "AVFoundation uniqueID still %s after warm-up; leaving open. "
            "Confirm Continuity on iPhone lock screen is active.",
            last_err,
        )
        self._next_frame_id = 0

    def read(self) -> ImageFrame:
        if self._proc is None or self._proc.stdout is None:
            raise RuntimeError(f"{type(self).__name__} is not open; call open() first")
        header = self._proc.stdout.read(4)
        if header is None or len(header) < 4:
            code = self._proc.poll()
            raise SourceDisconnected(
                f"no frame header from capture_av_device (exit={code})"
            )
        (length,) = struct.unpack(">I", header)
        if length <= 0 or length > 20_000_000:
            raise SourceDisconnected(f"invalid JPEG length {length}")
        data = self._proc.stdout.read(length)
        if data is None or len(data) < length:
            raise SourceDisconnected("short JPEG payload from capture_av_device")
        arr = np.frombuffer(data, dtype=np.uint8)
        bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if bgr is None:
            raise SourceDisconnected("JPEG decode failed from capture_av_device")
        h, w = bgr.shape[:2]
        now = time.time()
        meta = Frame(
            frame_id=self._next_frame_id,
            camera_id=self.camera_id,
            t_capture=now,
            t_ingest=now,
            width=int(w),
            height=int(h),
        )
        self._next_frame_id += 1
        return ImageFrame(meta=meta, image_bgr=bgr)

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        if proc is None:
            return
        try:
            if proc.stdout is not None:
                proc.stdout.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            proc.terminate()
            proc.wait(timeout=2.0)
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except Exception:  # noqa: BLE001
                pass
