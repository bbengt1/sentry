"""Serve-time fixed-class detection worker factory (BACK-01, EDGE-RT-02).

Branches on ``ProfileRuntime.preferred_backend``. Torch path is fully live via
``YoloDetectionWorker``. ORT/TRT branches are soft-stubs in Phase 8: they still
construct a torch worker and report ``backend_live=torch`` with a stable reason
code — never claim live ORT/TRT.

Does not import ``onnxruntime`` or ``tensorrt`` at module level.
"""

from __future__ import annotations

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


def _try_resolve_artifact(
    rt: ProfileRuntime,
    *,
    preferred: str,
) -> tuple[Path | None, str | None]:
    """Resolve ORT/TRT artifact candidate; capture path_rejected without failing.

    Returns (path_or_none, reason_override_or_none). Artifact presence does not
    flip ``backend_live`` in Phase 8 — recorded for future loaders only.
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

    Phase 8: torch/cpu fully live; onnxruntime/tensorrt soft-stub to torch with
    stable reason codes. Never sets ``backend_live`` to onnxruntime or tensorrt.
    """
    requested = normalize_backend(rt.preferred_backend)
    worker = _torch_worker(rt, conf=conf, model=model)

    if requested in {"torch", "cpu"}:
        return WorkerBuild(
            worker=worker,
            backend_requested=requested,
            backend_live="torch",
            backend_reason=None,
        )

    if requested == "onnxruntime":
        _path, reject = _try_resolve_artifact(rt, preferred="onnxruntime")
        reason = reject or "ort_loader_not_implemented"
        return WorkerBuild(
            worker=worker,
            backend_requested="onnxruntime",
            backend_live="torch",
            backend_reason=reason,
        )

    if requested == "tensorrt":
        _path, reject = _try_resolve_artifact(rt, preferred="tensorrt")
        reason = reject or "trt_loader_not_implemented"
        return WorkerBuild(
            worker=worker,
            backend_requested="tensorrt",
            backend_live="torch",
            backend_reason=reason,
        )

    # openvino / unknown → torch + unsupported_backend
    return WorkerBuild(
        worker=worker,
        backend_requested=requested,
        backend_live="torch",
        backend_reason="unsupported_backend",
    )
