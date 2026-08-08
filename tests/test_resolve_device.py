"""resolve_device must not pass invalid CUDA devices to Ultralytics."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sentry_ai.models.device import resolve_device


def test_resolve_device_cpu_explicit() -> None:
    assert resolve_device("cpu") == "cpu"


def test_resolve_device_none_auto_without_torch() -> None:
    with patch.dict("sys.modules", {"torch": None}):
        # Import path uses try/import; force cuda/mps unavailable.
        with (
            patch("sentry_ai.models.device._cuda_available", return_value=False),
            patch("sentry_ai.models.device._mps_available", return_value=False),
        ):
            assert resolve_device(None) == "cpu"
            assert resolve_device("") == "cpu"


def test_resolve_device_cuda_request_falls_back_when_unavailable() -> None:
    with (
        patch("sentry_ai.models.device._cuda_available", return_value=False),
        patch("sentry_ai.models.device._mps_available", return_value=False),
    ):
        assert resolve_device("cuda:0") == "cpu"
        assert resolve_device("cuda") == "cpu"
        assert resolve_device("0") == "cpu"


def test_resolve_device_cuda_request_falls_back_to_mps() -> None:
    with (
        patch("sentry_ai.models.device._cuda_available", return_value=False),
        patch("sentry_ai.models.device._mps_available", return_value=True),
    ):
        assert resolve_device("cuda:0") == "mps"
        assert resolve_device("0") == "mps"


def test_resolve_device_cuda_request_kept_when_available() -> None:
    with patch("sentry_ai.models.device._cuda_available", return_value=True):
        assert resolve_device("cuda:0") == "cuda:0"
        assert resolve_device("cuda:1") == "cuda:1"
        assert resolve_device("0") == "cuda:0"


def test_resolve_device_auto_prefers_cuda_then_mps() -> None:
    with (
        patch("sentry_ai.models.device._cuda_available", return_value=True),
        patch("sentry_ai.models.device._mps_available", return_value=True),
    ):
        assert resolve_device(None) == "cuda"
    with (
        patch("sentry_ai.models.device._cuda_available", return_value=False),
        patch("sentry_ai.models.device._mps_available", return_value=True),
    ):
        assert resolve_device(None) == "mps"


def test_yolo_worker_reexports_shared_resolve_device() -> None:
    from sentry_ai.models.detection.yolo_worker import resolve_device as yolo_rd
    from sentry_ai.models.device import resolve_device as shared

    assert yolo_rd is shared


def test_yolo_worker_uses_fallback_device_on_predict() -> None:
    """Regression: desktop-gpu policy cuda:0 must not crash without CUDA."""
    import numpy as np

    from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker

    calls: list[str] = []

    class FakeModel:
        def predict(self, **kwargs):  # type: ignore[no-untyped-def]
            calls.append(str(kwargs.get("device")))
            return []

    with (
        patch("sentry_ai.models.device._cuda_available", return_value=False),
        patch("sentry_ai.models.device._mps_available", return_value=False),
    ):
        worker = YoloDetectionWorker(
            weights="yolo26n.pt",
            device="cuda:0",
            model=FakeModel(),
        )
        frame = MagicMock()
        frame.image_bgr = np.zeros((32, 32, 3), dtype=np.uint8)
        worker.process(frame)
        assert calls == ["cpu"]
        assert worker._device == "cpu"
