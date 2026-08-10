"""Factory honesty tests: live ORT/TRT + soft-fallback reason matrix."""

from __future__ import annotations

import inspect
from pathlib import Path
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
    """Default jetson without fixture artifact soft-falls (not live TRT)."""
    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_artifact_missing"
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".pt")


def test_cpu_fallback_ort_soft_stub_artifact_missing() -> None:
    """Default cpu-fallback without fixture artifact soft-falls (not live ORT)."""
    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_requested == "onnxruntime"
    assert build.backend_live == "torch"
    assert build.backend_reason == "ort_artifact_missing"
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".pt")


@pytest.mark.parametrize(
    "profile",
    ["desktop-gpu", "jetson", "cpu-fallback"],
)
def test_backend_live_not_ort_or_trt_without_fixtures(profile: str) -> None:
    """Without live fixtures, backend_live stays torch for default profiles."""
    rt = _rt_for_profile(profile)
    build = build_detection_worker(rt, model=FakeModel())
    assert build.backend_live not in {"onnxruntime", "tensorrt"}
    assert build.backend_live == "torch"


def test_live_ort_success_with_artifact_and_dep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """preferred=onnxruntime + resolved .onnx + dep available → live ORT."""
    onnx_path = tmp_path / "yolo26n.onnx"
    onnx_path.write_bytes(b"fake-onnx")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (onnx_path, None),
    )
    monkeypatch.setattr(factory_mod, "_onnxruntime_available", lambda: True)

    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())

    assert build.backend_requested == "onnxruntime"
    assert build.backend_live == "onnxruntime"
    assert build.backend_reason is None
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".onnx")
    assert Path(build.worker._weights) == onnx_path
    # Live ORT must not claim ORT while still holding torch .pt weights
    assert not str(build.worker._weights).endswith(".pt")


def test_live_trt_success_with_artifact_and_dep(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """preferred=tensorrt + resolved .engine + dep available → live TRT (TRT-01)."""
    engine_path = tmp_path / "yolo26n.engine"
    engine_path.write_bytes(b"fake-engine")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (engine_path, None),
    )
    monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: True)

    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())

    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "tensorrt"
    assert build.backend_reason is None
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".engine")
    assert Path(build.worker._weights) == engine_path
    # Live TRT must not claim TRT while still holding torch .pt weights
    assert not str(build.worker._weights).endswith(".pt")


def test_ort_soft_fallback_dep_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Artifact present but onnxruntime not importable → ort_dep_missing."""
    onnx_path = tmp_path / "yolo26n.onnx"
    onnx_path.write_bytes(b"fake-onnx")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (onnx_path, None),
    )
    monkeypatch.setattr(factory_mod, "_onnxruntime_available", lambda: False)

    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())

    assert build.backend_requested == "onnxruntime"
    assert build.backend_live == "torch"
    assert build.backend_reason == "ort_dep_missing"
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".pt")


def test_trt_soft_fallback_dep_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Artifact present but system tensorrt not importable → trt_dep_missing."""
    engine_path = tmp_path / "yolo26n.engine"
    engine_path.write_bytes(b"fake-engine")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (engine_path, None),
    )
    monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: False)

    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())

    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "trt_dep_missing"
    assert isinstance(build.worker, YoloDetectionWorker)
    assert str(build.worker._weights).endswith(".pt")


def test_ort_soft_fallback_path_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """path_rejected on explicit/env path → torch soft-fallback."""
    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (None, "path_rejected"),
    )
    monkeypatch.setattr(factory_mod, "_onnxruntime_available", lambda: True)

    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())

    assert build.backend_requested == "onnxruntime"
    assert build.backend_live == "torch"
    assert build.backend_reason == "path_rejected"
    assert isinstance(build.worker, YoloDetectionWorker)


def test_trt_soft_fallback_path_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """path_rejected on explicit/env TRT path → torch soft-fallback."""
    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (None, "path_rejected"),
    )
    monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: True)

    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())

    assert build.backend_requested == "tensorrt"
    assert build.backend_live == "torch"
    assert build.backend_reason == "path_rejected"
    assert isinstance(build.worker, YoloDetectionWorker)


def test_never_live_ort_with_pt_weights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """backend_live=onnxruntime only when worker weights end with .onnx."""
    onnx_path = tmp_path / "yolo26n.onnx"
    onnx_path.write_bytes(b"fake-onnx")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (onnx_path, None),
    )
    monkeypatch.setattr(factory_mod, "_onnxruntime_available", lambda: True)

    rt = _rt_for_profile("cpu-fallback")
    build = build_detection_worker(rt, model=FakeModel())
    if build.backend_live == "onnxruntime":
        assert str(build.worker._weights).endswith(".onnx")
        assert not str(build.worker._weights).endswith(".pt")


def test_never_live_trt_with_pt_weights(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """backend_live=tensorrt only when worker weights end with .engine."""
    engine_path = tmp_path / "yolo26n.engine"
    engine_path.write_bytes(b"fake-engine")

    monkeypatch.setattr(
        factory_mod,
        "_try_resolve_artifact",
        lambda rt, *, preferred: (engine_path, None),
    )
    monkeypatch.setattr(factory_mod, "_tensorrt_available", lambda: True)

    rt = _rt_for_profile("jetson")
    build = build_detection_worker(rt, model=FakeModel())
    if build.backend_live == "tensorrt":
        assert str(build.worker._weights).endswith(".engine")
        assert not str(build.worker._weights).endswith(".pt")


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
        fallback_to_torch=True,
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
        fallback_to_torch=True,
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


# --- fallback_to_torch config surface (BACK-03) ---


@pytest.mark.parametrize(
    "profile",
    ["desktop-gpu", "jetson", "cpu-fallback"],
)
def test_fallback_to_torch_default_true(profile: str) -> None:
    """Soft is global default including jetson (profile YAML values unchanged)."""
    rt = _rt_for_profile(profile)
    assert rt.fallback_to_torch is True


def test_fallback_to_torch_env_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_FALLBACK_TO_TORCH", "false")
    rt = profile_runtime(load_config(profile="jetson"))
    assert rt.fallback_to_torch is False


def test_fallback_to_torch_env_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SENTRY_FALLBACK_TO_TORCH", "true")
    rt = profile_runtime(load_config(profile="cpu-fallback"))
    assert rt.fallback_to_torch is True
