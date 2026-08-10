"""Serve-time fixed-class detection worker factory.

Covers BACK-01, EDGE-RT-02, ORT-01, TRT-01.

Branches on ``ProfileRuntime.preferred_backend``. Torch path is fully live via
``YoloDetectionWorker``. Phase 9: preferred ``onnxruntime`` is live when an
allowlisted ``.onnx`` artifact resolves and ``onnxruntime`` is importable;
otherwise soft-falls to a torch worker with a stable reason code. Phase 10:
preferred ``tensorrt`` is live when an allowlisted ``.engine`` artifact resolves
and system/JetPack ``tensorrt`` is importable; otherwise soft-falls to torch
with a stable reason (``trt_artifact_missing`` / ``trt_dep_missing`` /
``path_rejected``).

Does not import ``onnxruntime`` or ``tensorrt`` at module level — dep probe uses
``importlib.util.find_spec`` only. Never triggers Ultralytics auto-pip TRT install.
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sentry_ai.config.artifact_paths import resolve_detector_artifact
from sentry_ai.config.profile_runtime import ProfileRuntime
from sentry_ai.models.cache import configure_model_cache
from sentry_ai.models.detection.yolo_worker import YoloDetectionWorker

__all__ = [
    "WorkerBuild",
    "build_detection_worker",
    "normalize_backend",
]


@dataclass(frozen=True)
class WorkerBuild:
    """Detection worker plus honest preferred-vs-live backend identity."""

    worker: Any  # ModelWorker duck-type
    backend_requested: str
    backend_live: str
    backend_reason: str | None = None


def normalize_backend(backend: Any) -> str:
    """Normalize preferred_backend to a lowercase snake-case string.

    Mirrors ``device_for_backend`` hygiene (strip, lower, BackendName.X).
    """
    if backend is None:
        return "torch"
    # Enum with .value
    value = getattr(backend, "value", backend)
    b = str(value).strip().lower()
    if b.startswith("backendname."):
        b = b.split(".", 1)[1].lower()
    return b


def _torch_worker(
    rt: ProfileRuntime,
    *,
    conf: float,
    model: Any | None,
) -> YoloDetectionWorker:
    return YoloDetectionWorker(
        weights=rt.detector_weights,
        conf=conf,
        device=rt.device,
        model=model,
    )


def _onnxruntime_available() -> bool:
    """True when the onnxruntime package is importable (no hard import)."""
    return importlib.util.find_spec("onnxruntime") is not None


def _tensorrt_available() -> bool:
    """True when the system tensorrt package is importable (no hard import)."""
    return importlib.util.find_spec("tensorrt") is not None


def _try_resolve_artifact(
    rt: ProfileRuntime,
    *,
    preferred: str,
) -> tuple[Path | None, str | None]:
    """Resolve ORT/TRT artifact candidate; capture path_rejected without failing.

    Returns (path, None) on success, (None, "path_rejected") when an explicit/env
    path fails the allowlist, or (None, None) when no artifact is found.

    Phase 9 consumes a resolved ``.onnx`` path for the live ORT worker branch.
    Phase 10 consumes a resolved ``.engine`` path for the live TRT worker branch.
    """
    if preferred == "onnxruntime":
        env_value = os.environ.get("SENTRY_DETECTOR_ONNX")
    elif preferred == "tensorrt":
        env_value = os.environ.get("SENTRY_DETECTOR_ENGINE")
    else:
        return None, None

    artifact_root_env = os.environ.get("SENTRY_ARTIFACT_ROOT")
    artifact_root = Path(artifact_root_env) if artifact_root_env else None

    try:
        weights_dir = configure_model_cache()
    except OSError:
        weights_dir = None

    try:
        path = resolve_detector_artifact(
            preferred_backend=preferred,
            detector_weights=rt.detector_weights,
            env_value=env_value,
            weights_dir=weights_dir,
            cwd=Path.cwd(),
            artifact_root=artifact_root,
        )
        return path, None
    except ValueError:
        # Explicit/env path failed allowlist — still soft-stub torch.
        return None, "path_rejected"


def build_detection_worker(
    rt: ProfileRuntime,
    *,
    conf: float = 0.25,
    model: Any | None = None,
) -> WorkerBuild:
    """Construct fixed-class detector from profile runtime.

    Phase 9: torch/cpu fully live; onnxruntime live when allowlisted ``.onnx``
    resolves and onnxruntime is available; otherwise soft-fall to torch with a
    stable reason. Phase 10: tensorrt live when allowlisted ``.engine`` resolves
    and system tensorrt is available; otherwise soft-fall with
    ``trt_artifact_missing`` / ``trt_dep_missing`` / ``path_rejected``.
    ``backend_live=onnxruntime`` only when the worker is constructed with the
    resolved ``.onnx`` weights path; ``backend_live=tensorrt`` only with the
    resolved ``.engine`` weights path.
    """
    requested = normalize_backend(rt.preferred_backend)

    if requested in {"torch", "cpu"}:
        worker = _torch_worker(rt, conf=conf, model=model)
        return WorkerBuild(
            worker=worker,
            backend_requested=requested,
            backend_live="torch",
            backend_reason=None,
        )

    if requested == "onnxruntime":
        path, reject = _try_resolve_artifact(rt, preferred="onnxruntime")
        if reject:
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="onnxruntime",
                backend_live="torch",
                backend_reason=reject,
            )
        if path is None:
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="onnxruntime",
                backend_live="torch",
                backend_reason="ort_artifact_missing",
            )
        if not _onnxruntime_available():
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="onnxruntime",
                backend_live="torch",
                backend_reason="ort_dep_missing",
            )
        # Live ORT: Ultralytics-native YOLO("*.onnx") via same worker class.
        ort_worker = YoloDetectionWorker(
            weights=str(path),
            conf=conf,
            device=rt.device,
            model=model,
        )
        return WorkerBuild(
            worker=ort_worker,
            backend_requested="onnxruntime",
            backend_live="onnxruntime",
            backend_reason=None,
        )

    if requested == "tensorrt":
        path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
        if reject:
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="tensorrt",
                backend_live="torch",
                backend_reason=reject,
            )
        if path is None:
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="tensorrt",
                backend_live="torch",
                backend_reason="trt_artifact_missing",
            )
        if not _tensorrt_available():
            return WorkerBuild(
                worker=_torch_worker(rt, conf=conf, model=model),
                backend_requested="tensorrt",
                backend_live="torch",
                backend_reason="trt_dep_missing",
            )
        # Live TRT: Ultralytics-native YOLO("*.engine") via same worker class.
        trt_worker = YoloDetectionWorker(
            weights=str(path),
            conf=conf,
            device=rt.device,
            model=model,
        )
        return WorkerBuild(
            worker=trt_worker,
            backend_requested="tensorrt",
            backend_live="tensorrt",
            backend_reason=None,
        )

    # openvino / unknown → torch + unsupported_backend
    return WorkerBuild(
        worker=_torch_worker(rt, conf=conf, model=model),
        backend_requested=requested,
        backend_live="torch",
        backend_reason="unsupported_backend",
    )
