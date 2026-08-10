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
    let minInterval: TimeInterval = 1.0 / 30.0
    var writing = false

    func captureOutput(
        _ output: AVCaptureOutput,
        didOutput sampleBuffer: CMSampleBuffer,
        from connection: AVCaptureConnection
    ) {
        let now = CFAbsoluteTimeGetCurrent()
        if now - lastPTS < minInterval { return }
        lastPTS = now

        lock.lock()
        if writing {
            lock.unlock()
            return
        }
        writing = true
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
        FileHandle.standardOutput.write(header)
        FileHandle.standardOutput.write(data as Data)
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

let session = AVCaptureSession()
session.beginConfiguration()
session.sessionPreset = .hd1280x720

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
  + "continuity=\(contFlag) uid=\(device.uniqueID)\n",
  stderr
)

// Keep process alive
RunLoop.main.run()
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
    version = "2"
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


class AvFoundationUniqueSource:
    """Stream frames from a macOS camera opened by AVFoundation uniqueID."""

    name: str = "usb"

    def __init__(
        self,
        unique_id: str,
        *,
        camera_id: str = "usb0",
        device_label: str | None = None,
    ) -> None:
        if not unique_id or not str(unique_id).strip():
            raise ValueError("unique_id is required")
        self.unique_id = str(unique_id).strip()
        self.camera_id = camera_id
        self.device_label = device_label
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

        # Brief wait for first frame (Continuity wake).
        deadline = time.time() + 10.0
        last_err = "no frames"
        while time.time() < deadline:
            try:
                frame = self.read()
                mean = float(np.mean(frame.image_bgr))
                if mean >= 1.0:
                    self._next_frame_id = 0
                    logger.info(
                        "AVFoundation uniqueID warm-up ok mean=%.1f label=%s",
                        mean,
                        self.device_label,
                    )
                    return
                last_err = f"black frame mean={mean:.1f}"
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
