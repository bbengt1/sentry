"""Unit tests for local camera enumeration (mocked OpenCV / AVFoundation)."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from sentry_ai.cli import app
from sentry_ai.sources.list_cameras import (
    LocalCameraInfo,
    format_camera_list,
    list_avfoundation_devices_ffmpeg,
    list_local_cameras,
    probe_camera_index,
)

runner = CliRunner()


class _FakeCap:
    def __init__(
        self,
        *,
        opened: bool,
        width: float = 640,
        height: float = 480,
        fps: float = 30.0,
        backend: float = 0,
        read_ok: bool = True,
    ) -> None:
        self._opened = opened
        self._width = width
        self._height = height
        self._fps = fps
        self._backend = backend
        self._read_ok = read_ok
        self.released = False

    def isOpened(self) -> bool:
        return self._opened

    def get(self, prop: int) -> float:
        return 0.0

    def read(self) -> tuple[bool, Any]:
        if not self._read_ok:
            return False, None
        return True, object()

    def release(self) -> None:
        self.released = True


def _make_cv2(caps_by_index: dict[int, _FakeCap]) -> Any:
    class FakeCv2:
        CAP_PROP_FRAME_WIDTH = 3
        CAP_PROP_FRAME_HEIGHT = 4
        CAP_PROP_FPS = 5
        CAP_PROP_BACKEND = 6
        CAP_AVFOUNDATION = 1200

        class videoio_registry:
            @staticmethod
            def getBackendName(backend_id: int) -> str:
                return f"Backend{backend_id}"

        @staticmethod
        def VideoCapture(index: int, *args: Any) -> _FakeCap:
            if index not in caps_by_index:
                cap = _FakeCap(opened=False)
                caps_by_index[index] = cap
                return cap
            return caps_by_index[index]

    for cap in list(caps_by_index.values()):

        def _get(
            prop: int,
            c: _FakeCap = cap,
            fc: type[FakeCv2] = FakeCv2,
        ) -> float:
            if prop == fc.CAP_PROP_FRAME_WIDTH:
                return c._width
            if prop == fc.CAP_PROP_FRAME_HEIGHT:
                return c._height
            if prop == fc.CAP_PROP_FPS:
                return c._fps
            if prop == fc.CAP_PROP_BACKEND:
                return c._backend
            return 0.0

        cap.get = _get  # type: ignore[method-assign]

    return FakeCv2()


def test_probe_available_camera() -> None:
    caps: dict[int, _FakeCap] = {
        0: _FakeCap(opened=True, width=1280, height=720, fps=30.0, backend=1),
    }
    cv2 = _make_cv2(caps)
    info = probe_camera_index(0, cv2_module=cv2, name="FaceTime")
    assert info.available is True
    assert info.name == "FaceTime"
    assert info.width == 1280
    assert caps[0].released is True


def test_probe_unavailable_camera() -> None:
    caps: dict[int, _FakeCap] = {1: _FakeCap(opened=False)}
    cv2 = _make_cv2(caps)
    info = probe_camera_index(1, cv2_module=cv2)
    assert info.available is False
    assert info.error is not None


def test_list_merges_avfoundation_names(monkeypatch: Any) -> None:
    caps: dict[int, _FakeCap] = {
        0: _FakeCap(opened=True, width=1920, height=1080),
        1: _FakeCap(opened=False),
    }
    cv2 = _make_cv2(caps)

    def video_capture(index: int, *args: Any) -> _FakeCap:
        if index in caps:
            return caps[index]
        return _FakeCap(opened=False)

    cv2.VideoCapture = staticmethod(video_capture)  # type: ignore[method-assign]
    for _idx, c in caps.items():

        def _get(prop: int, c: _FakeCap = c, cv2: Any = cv2) -> float:
            if prop == cv2.CAP_PROP_FRAME_WIDTH:
                return c._width
            if prop == cv2.CAP_PROP_FRAME_HEIGHT:
                return c._height
            if prop == cv2.CAP_PROP_FPS:
                return c._fps
            if prop == cv2.CAP_PROP_BACKEND:
                return c._backend
            return 0.0

        c.get = _get  # type: ignore[method-assign]

    monkeypatch.setattr(
        "sentry_ai.sources.list_cameras._is_macos",
        lambda: True,
    )
    monkeypatch.setattr(
        "sentry_ai.sources.list_cameras.list_macos_av_devices",
        lambda **kwargs: [
            {
                "av_index": "0",
                "name": "FaceTime HD Camera",
                "device_type": "AVCaptureDeviceTypeBuiltInWideAngleCamera",
                "unique_id": "uid0",
                "flags": "",
            },
            {
                "av_index": "1",
                "name": "Brent's iPhone",
                "device_type": "AVCaptureDeviceTypeContinuityCamera",
                "unique_id": "uid1",
                "flags": "continuity",
            },
        ],
    )

    found = list_local_cameras(
        max_index=1,
        include_unavailable=False,
        cv2_module=cv2,
        use_avfoundation=True,
    )
    assert len(found) == 2
    assert found[0].name == "FaceTime HD Camera"
    assert found[0].available is True
    # Continuity listed by AV even though OpenCV open failed
    assert found[1].name == "Brent's iPhone"
    assert found[1].available is False
    assert any("Continuity" in n for n in found[1].notes)


def test_ffmpeg_parser_extracts_video_devices() -> None:
    ffmpeg_stderr = """
[AVFoundation indev @ 0x1] AVFoundation video devices:
[AVFoundation indev @ 0x1] [0] FaceTime HD Camera
[AVFoundation indev @ 0x1] [1] Capture screen 0
[AVFoundation indev @ 0x1] AVFoundation audio devices:
[AVFoundation indev @ 0x1] [0] MacBook Pro Microphone
"""

    def fake_run(*args: Any, **kwargs: Any) -> Any:
        return type(
            "P",
            (),
            {
                "returncode": 1,
                "stdout": "",
                "stderr": ffmpeg_stderr,
            },
        )()

    # Force ffmpeg path
    import sentry_ai.sources.list_cameras as mod

    orig = mod.shutil.which

    def which(name: str) -> str | None:
        if name == "ffmpeg":
            return "/usr/bin/ffmpeg"
        return orig(name)

    mod.shutil.which = which  # type: ignore[method-assign]
    try:
        devices = list_avfoundation_devices_ffmpeg(run_subprocess=fake_run)
    finally:
        mod.shutil.which = orig  # type: ignore[method-assign]

    assert len(devices) == 2
    assert devices[0]["name"] == "FaceTime HD Camera"
    assert devices[1]["flags"] == "screen"


def test_format_camera_list_shows_name_and_continuity_tips() -> None:
    cams = [
        LocalCameraInfo(
            index=0,
            available=True,
            width=1920,
            height=1080,
            fps=30.0,
            name="FaceTime HD Camera",
            device_type="BuiltInWideAngleCamera",
        ),
    ]
    text = format_camera_list(cams, max_index=8, continuity_hint=True)
    assert "FaceTime HD Camera" in text
    assert "Continuity Camera not listed" in text or "Continuity" in text
    assert "serve --source usb --device" in text


def test_format_with_continuity_device() -> None:
    cams = [
        LocalCameraInfo(
            index=1,
            available=True,
            name="iPhone",
            notes=("Continuity Camera",),
            device_type="ContinuityCamera",
        ),
    ]
    text = format_camera_list(cams, max_index=8, continuity_hint=True)
    assert "iPhone" in text
    assert "Continuity Camera not listed" not in text


def test_cli_cameras_command_registered() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "cameras" in result.stdout


def test_cli_cameras_help() -> None:
    result = runner.invoke(app, ["cameras", "--help"])
    assert result.exit_code == 0
    assert "max-index" in result.stdout
    assert "avfoundation" in result.stdout.lower() or "Continuity" in result.stdout


def test_cli_cameras_runs_with_mock(monkeypatch: Any) -> None:
    fake = [
        LocalCameraInfo(
            index=0,
            available=True,
            width=640,
            height=480,
            fps=30.0,
            name="FakeCam",
            backend="FAKE",
        )
    ]
    monkeypatch.setattr(
        "sentry_ai.sources.list_cameras.list_local_cameras",
        lambda **kwargs: fake,
    )
    monkeypatch.setattr(
        "sentry_ai.sources.list_cameras.list_macos_av_devices",
        lambda **kwargs: [],
    )
    result = runner.invoke(app, ["cameras"])
    assert result.exit_code == 0
    assert "FakeCam" in result.stdout or "640x480" in result.stdout
