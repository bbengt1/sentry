"""Unit tests for local camera enumeration (mocked OpenCV)."""

from __future__ import annotations

from typing import Any

from typer.testing import CliRunner

from sentry_ai.cli import app
from sentry_ai.sources.list_cameras import (
    LocalCameraInfo,
    format_camera_list,
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
        # Property ids are opaque to us; map by call order / any prop.
        # Tests inject fixed values; get is called for WIDTH/HEIGHT/FPS/BACKEND.
        # Use a simple queue of values in typical order.
        return {
            # common OpenCV constants (values may vary; fake by counting)
        }.get(prop, 0.0)

    def read(self) -> tuple[bool, Any]:
        if not self._read_ok:
            return False, None
        return True, object()

    def release(self) -> None:
        self.released = True


def _make_cv2(caps_by_index: dict[int, _FakeCap]) -> Any:
    """Build a minimal cv2 stand-in with CAP_PROP_* and VideoCapture."""

    class FakeCv2:
        CAP_PROP_FRAME_WIDTH = 3
        CAP_PROP_FRAME_HEIGHT = 4
        CAP_PROP_FPS = 5
        CAP_PROP_BACKEND = 6

        class videoio_registry:
            @staticmethod
            def getBackendName(backend_id: int) -> str:
                return f"Backend{backend_id}"

        @staticmethod
        def VideoCapture(index: int) -> _FakeCap:
            if index not in caps_by_index:
                cap = _FakeCap(opened=False)
                caps_by_index[index] = cap
                return cap
            return caps_by_index[index]

    # Patch get on each cap to return sensible props
    for cap in caps_by_index.values():
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
    info = probe_camera_index(0, cv2_module=cv2)
    assert info.available is True
    assert info.index == 0
    assert info.width == 1280
    assert info.height == 720
    assert info.fps == 30.0
    assert info.backend == "Backend1"
    assert caps[0].released is True


def test_probe_unavailable_camera() -> None:
    caps: dict[int, _FakeCap] = {1: _FakeCap(opened=False)}
    cv2 = _make_cv2(caps)
    info = probe_camera_index(1, cv2_module=cv2)
    assert info.available is False
    assert info.error is not None
    assert caps[1].released is True


def test_probe_open_but_no_frame() -> None:
    caps: dict[int, _FakeCap] = {
        2: _FakeCap(opened=True, read_ok=False),
    }
    cv2 = _make_cv2(caps)
    info = probe_camera_index(2, cv2_module=cv2)
    assert info.available is False
    assert info.error is not None
    assert "frame" in info.error.lower() or "permission" in info.error.lower()


def test_list_local_cameras_filters_unavailable() -> None:
    caps: dict[int, _FakeCap] = {
        0: _FakeCap(opened=True),
        1: _FakeCap(opened=False),
        2: _FakeCap(opened=True, width=640, height=480),
    }
    # list probes 0..max_index; only put 0 and 2 as open
    cv2 = _make_cv2(caps)

    def video_capture(index: int) -> _FakeCap:
        if index in (0, 2):
            return caps[index]
        cap = _FakeCap(opened=False)
        return cap

    cv2.VideoCapture = staticmethod(video_capture)  # type: ignore[method-assign]
    # re-bind get for open caps
    for idx in (0, 2):
        c = caps[idx]

        def _get(
            prop: int,
            c: _FakeCap = c,
        ) -> float:
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

    found = list_local_cameras(max_index=2, include_unavailable=False, cv2_module=cv2)
    assert [c.index for c in found] == [0, 2]
    assert all(c.available for c in found)


def test_list_local_cameras_include_unavailable() -> None:
    caps: dict[int, _FakeCap] = {
        0: _FakeCap(opened=True),
    }
    cv2 = _make_cv2(caps)

    def video_capture(index: int) -> _FakeCap:
        if index == 0:
            return caps[0]
        return _FakeCap(opened=False)

    cv2.VideoCapture = staticmethod(video_capture)  # type: ignore[method-assign]
    c = caps[0]

    def _get(prop: int) -> float:
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

    found = list_local_cameras(max_index=1, include_unavailable=True, cv2_module=cv2)
    assert len(found) == 2
    assert found[0].available is True
    assert found[1].available is False


def test_format_camera_list_mentions_macos_and_serve() -> None:
    cams = [
        LocalCameraInfo(
            index=0,
            available=True,
            width=1920,
            height=1080,
            fps=30.0,
            backend="AVFOUNDATION",
        ),
        LocalCameraInfo(
            index=1,
            available=True,
            width=1280,
            height=720,
            fps=24.0,
            backend="AVFOUNDATION",
        ),
    ]
    text = format_camera_list(cams, max_index=8)
    assert "INDEX" in text
    assert "0" in text and "1" in text
    assert "Continuity" in text or "macOS" in text
    assert "sentry serve --source usb --device" in text


def test_format_empty_list_gives_tips() -> None:
    text = format_camera_list([], max_index=8)
    assert "none found" in text.lower() or "(none" in text.lower()
    assert "permission" in text.lower() or "Camera" in text


def test_cli_cameras_command_registered() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "cameras" in result.stdout


def test_cli_cameras_help() -> None:
    result = runner.invoke(app, ["cameras", "--help"])
    assert result.exit_code == 0
    assert "max-index" in result.stdout
    assert "device" in result.stdout.lower() or "OpenCV" in result.stdout


def test_cli_cameras_runs_with_mock(monkeypatch: Any) -> None:
    fake = [
        LocalCameraInfo(
            index=0,
            available=True,
            width=640,
            height=480,
            fps=30.0,
            backend="FAKE",
        )
    ]
    monkeypatch.setattr(
        "sentry_ai.sources.list_cameras.list_local_cameras",
        lambda **kwargs: fake,
    )
    result = runner.invoke(app, ["cameras"])
    assert result.exit_code == 0
    assert "640x480" in result.stdout
    assert "usb --device" in result.stdout
