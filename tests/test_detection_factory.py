"""BACK-01 / EDGE-RT-03: build_detection_worker honesty + soft ORT/TRT stubs."""

from __future__ import annotations

import inspect
from typing import Any

import pytest

from sentry_ai.config.load import load_config
from sentry_ai.config.profile_runtime import ProfileRuntime, profile_runtime
from sentry_ai.models.detection import factory as factory_mod
from sentry_ai.models.detection.factory import WorkerBuild, build_detection_worker
from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker
from sentry_ai.schemas.enums import RuntimeProfile


class FakeModel:
    """Minimal injectable model so tests never download weights."""

    def predict(self, **kwargs: Any) -> list[Any]:
        return []


def _rt_for_profile(profile: str) -> ProfileRuntime:
    return profile_runtime(load_config(profile=profile))


def test_desktop_gpu_torch_live() -> None:
    rt = _rt_for_profile("desktop-gpu")
    build = build_detection_worker(rt, conf=0.25, model=FakeModel())
    assert isinstance(build, WorkerBuild)
    assert build.backend_requested == "torch"
    assert build.backend_live == "torch"
    assert build.backend_reason is None
    assert isinstance(build.worker, YoloDetectionWorker)
    assert build.worker.get_conf() == pytest.approx(0.25)


def test_jetson_tensorrt_soft_stub() -> None:
    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_loader_not_implemented"
    assert isinstance(build.worker, YoloDetectionWorker)


def test_cpu_fallback_ort_soft_stub() -> None:
    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "onnxruntime"
    assert build.backend_live == "torch"
    assert build.backend_reason == "ort_loader_not_implemented"
    assert isinstance(build.worker, YoloDetectionWorker)


@pytest.mark.parametrize(
    "profile",
    ["desktop-gpu", "jetson", "cpu-fallback"],
)
def test_backend_live_never_ort_or_trt(profile: str) -> None:
    rt = _rt_for_profile(profile)
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_live not in {"onnxruntime", "tensorrt"}
    assert build.backend_live == "torch"


def test_worker_duck_type_process_conf() -> None:
    rt = _rt_for_profile("desktop-gpu")
    build = build_detection_worker(rt, model=FakeModel())
    w = build.worker
    assert hasattr(w, "process")
    assert callable(w.process)
    assert hasattr(w, "get_conf")
    assert hasattr(w, "set_conf")
    w.set_conf(0.4)
    assert w.get_conf() == pytest.approx(0.4)


def test_unknown_backend_unsupported_reason() -> None:
    rt = ProfileRuntime(
        profile=RuntimeProfile.DESKTOP_GPU,
        detector_weights="yolo26s.pt",
        open_vocab_weights="yoloe-26s-seg.pt",
        depth_model_id="depth-anything/Depth-Anything-V2-Small-hf",
        depth_tier="small",
        preferred_backend="openvino",
        device=None,
        device_id="cpu",
    )
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "openvino"
    assert build.backend_live == "torch"
    assert build.backend_reason == "unsupported_backend"


def test_cpu_preferred_live_torch() -> None:
    rt = ProfileRuntime(
        profile=RuntimeProfile.CPU_FALLBACK,
        detector_weights="yolo26n.pt",
        open_vocab_weights="yoloe-26n-seg.pt",
        depth_model_id="depth-anything/Depth-Anything-V2-Small-hf",
        depth_tier="small",
        preferred_backend="cpu",
        device="cpu",
        device_id="cpu",
    )
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "cpu"
    assert build.backend_live == "torch"
    assert build.backend_reason is None


def test_factory_module_does_not_import_ort_trt() -> None:
    source = inspect.getsource(factory_mod)
    assert "import onnxruntime" not in source
    assert "import tensorrt" not in source
    assert "from onnxruntime" not in source
    assert "from tensorrt" not in source
    # Import graph: module loads without GPU packages
    assert factory_mod.build_detection_worker is build_detection_worker


def test_forwards_weights_and_device() -> None:
    rt = _rt_for_profile("desktop-gpu")
    build = build_detection_worker(rt, model=FakeModel())
    worker = build.worker
    assert isinstance(worker, YoloDetectionWorker)
    assert worker._weights == rt.detector_weights
    assert worker._device_arg == rt.device
