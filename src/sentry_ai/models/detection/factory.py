"""Serve-time fixed-class detection worker factory.

Covers BACK-01, EDGE-RT-02, ORT-01, TRT-01, BACK-03.

Branches on ``ProfileRuntime.preferred_backend``. Torch path is fully live via
``YoloDetectionWorker``. Phase 9: preferred ``onnxruntime`` is live when an
allowlisted ``.onnx`` artifact resolves and ``onnxruntime`` is importable;
otherwise soft-falls to a torch worker with a stable reason code (default) or
strict-fails with ``worker=None`` when ``fallback_to_torch`` is false. Phase 10:
preferred ``tensorrt`` is live when an allowlisted ``.engine`` artifact resolves
and system/JetPack ``tensorrt`` is importable; otherwise soft/strict miss with
``trt_artifact_missing`` / ``trt_dep_missing`` / ``path_rejected``.

Does not import ``onnxruntime`` or ``tensorrt`` at module level — dep probe uses
``importlib.util.find_spec`` only. Never triggers Ultralytics auto-pip TRT install.
"""

from __future__ import annotations

import importlib.util
import logging
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

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class WorkerBuild:
    """Detection worker plus honest preferred-vs-live backend identity."""

    worker: Any | None  # ModelWorker duck-type, or None on strict miss
    backend_requested: str
    backend_live: str | None
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


def _miss(
    rt: ProfileRuntime,
    *,
    requested: str,
    reason: str,
    conf: float,
    model: Any | None,
    fallback_to_torch: bool,
) -> WorkerBuild:
    """Soft torch fallback or strict fail-closed miss (BACK-03)."""
    if fallback_to_torch:
        return WorkerBuild(
            worker=_torch_worker(rt, conf=conf, model=model),
            backend_requested=requested,
            backend_live="torch",
            backend_reason=reason,
        )
    # Strict: never silent torch under preferred ORT/TRT
    return WorkerBuild(
        worker=None,
        backend_requested=requested,
        backend_live=None,
        backend_reason=reason,
    )


def _log_reason_once(build: WorkerBuild, *, fallback_to_torch: bool) -> None:
    """Emit structured soft/strict reason log once per construct call."""
    if build.backend_reason is None:
        return
    if fallback_to_torch:
        logger.warning(
            "detection backend soft-fallback: requested=%s live=%s reason=%s",
            build.backend_requested,
            build.backend_live,
            build.backend_reason,
        )
    else:
        logger.error(
            "detection backend strict-fail: requested=%s live=%s reason=%s",
            build.backend_requested,
            build.backend_live,
            build.backend_reason,
        )


def build_detection_worker(
    rt: ProfileRuntime,
    *,
    conf: float = 0.25,
    model: Any | None = None,
) -> WorkerBuild:
    """Construct fixed-class detector from profile runtime.

    Phase 9: torch/cpu fully live; onnxruntime live when allowlisted ``.onnx``
    resolves and onnxruntime is available; otherwise soft-fall to torch with a
    stable reason (default) or strict fail-closed when
    ``rt.fallback_to_torch`` is false. Phase 10: tensorrt live when allowlisted
    ``.engine`` resolves and system tensorrt is available; otherwise soft/strict
    miss with ``trt_artifact_missing`` / ``trt_dep_missing`` / ``path_rejected``.
    ``backend_live=onnxruntime`` only when the worker is constructed with the
    resolved ``.onnx`` weights path; ``backend_live=tensorrt`` only with the
    resolved ``.engine`` weights path.
    """
    requested = normalize_backend(rt.preferred_backend)
    fallback_to_torch = bool(getattr(rt, "fallback_to_torch", True))

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
            build = _miss(
                rt,
                requested="onnxruntime",
                reason=reject,
                conf=conf,
                model=model,
                fallback_to_torch=fallback_to_torch,
            )
            _log_reason_once(build, fallback_to_torch=fallback_to_torch)
            return build
        if path is None:
            build = _miss(
                rt,
                requested="onnxruntime",
                reason="ort_artifact_missing",
                conf=conf,
                model=model,
                fallback_to_torch=fallback_to_torch,
            )
            _log_reason_once(build, fallback_to_torch=fallback_to_torch)
            return build
        if not _onnxruntime_available():
            build = _miss(
                rt,
                requested="onnxruntime",
                reason="ort_dep_missing",
                conf=conf,
                model=model,
                fallback_to_torch=fallback_to_torch,
            )
            _log_reason_once(build, fallback_to_torch=fallback_to_torch)
            return build
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
            build = _miss(
                rt,
                requested="tensorrt",
                reason=reject,
                conf=conf,
                model=model,
                fallback_to_torch=fallback_to_torch,
            )
            _log_reason_once(build, fallback_to_torch=fallback_to_torch)
            return build
        if path is None:
            build = _miss(
                rt,
                requested="tensorrt",
                reason="trt_artifact_missing",
                conf=conf,
                model=model,
                fallback_to_torch=fallback_to_torch,
            )
            _log_reason_once(build, fallback_to_torch=fallback_to_torch)
            return build
        if not _tensorrt_available():
            build = _miss(
                rt,
                requested="tensorrt",
                reason="trt_dep_missing",
                conf=conf,
                model=model,
                fallback_to_torch=fallback_to_torch,
            )
            _log_reason_once(build, fallback_to_torch=fallback_to_torch)
            return build
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

    # openvino / unknown → soft torch or strict None + unsupported_backend
    build = _miss(
        rt,
        requested=requested,
        reason="unsupported_backend",
        conf=conf,
        model=model,
        fallback_to_torch=fallback_to_torch,
    )
    _log_reason_once(build, fallback_to_torch=fallback_to_torch)
    return build
