"""EDGE-RT-04: depth and open-vocab stay PyTorch-only (no factory ORT/TRT).

Static source inspection only — no GPU, weight download, or Jetson.
"""

from __future__ import annotations

import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CLI_PATH = REPO_ROOT / "src" / "sentry_ai" / "cli.py"
DEPTH_WORKER_PATH = (
    REPO_ROOT / "src" / "sentry_ai" / "models" / "depth" / "worker.py"
)
YOLOE_WORKER_PATH = (
    REPO_ROOT
    / "src"
    / "sentry_ai"
    / "models"
    / "detection"
    / "yoloe_worker.py"
)
OPEN_VOCAB_LOOP_PATH = (
    REPO_ROOT
    / "src"
    / "sentry_ai"
    / "models"
    / "detection"
    / "open_vocab_loop.py"
)


def _read(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def test_cli_serve_constructs_depth_and_ov_workers_separately() -> None:
    """Serve builds DepthAnythingWorker + YoloeOpenVocabWorker outside factory."""
    src = _read(CLI_PATH)
    assert "DepthAnythingWorker" in src
    assert "YoloeOpenVocabWorker" in src
    assert "build_detection_worker" in src
    # Depth and OV constructors are present as dedicated call sites.
    assert "depth_worker = DepthAnythingWorker(" in src
    assert "ov_worker = YoloeOpenVocabWorker(" in src
    # Open-vocab weights come from profile runtime (.pt path), not factory.
    assert "weights=rt.open_vocab_weights" in src
    # Depth uses torch/HF path markers (model_id / device from rt).
    assert "model_id=rt.depth_model_id" in src


def test_cli_serve_factory_only_for_fixed_class_detection() -> None:
    """build_detection_worker is for fixed-class YOLO only — not depth/OV."""
    src = _read(CLI_PATH)
    # Single factory call site for fixed-class detection.
    factory_calls = [
        line
        for line in src.splitlines()
        if "build_detection_worker(" in line and not line.strip().startswith("#")
    ]
    assert len(factory_calls) == 1, factory_calls
    # Depth block does not route through factory.
    depth_block_start = src.index("from sentry_ai.models.depth.worker import")
    depth_block = src[depth_block_start : depth_block_start + 1200]
    assert "build_detection_worker" not in depth_block
    assert "DepthAnythingWorker(" in depth_block
    # OV construction is not a factory call.
    ov_start = src.index("ov_worker = YoloeOpenVocabWorker(")
    ov_snippet = src[ov_start : ov_start + 200]
    assert "build_detection_worker" not in ov_snippet


def test_depth_worker_no_ort_trt_backend_claims() -> None:
    """Depth worker module does not claim backend_live onnxruntime/tensorrt."""
    src = _read(DEPTH_WORKER_PATH)
    lowered = src.lower()
    # No factory preferred_backend loader branch for depth.
    assert "preferred_backend" not in src
    assert "backend_live" not in src
    assert "build_detection_worker" not in src
    assert "resolve_detector_artifact" not in src
    # No live ORT/TRT claim vocabulary for depth stage.
    assert "onnxruntime" not in lowered
    assert "tensorrt" not in lowered
    # Torch/HF path markers remain.
    assert "DepthAnythingWorker" in src
    assert "transformers" in lowered or "huggingface" in lowered or "hf" in lowered


def test_yoloe_worker_pt_weights_not_factory() -> None:
    """Open-vocab worker loads via YOLOE / weights string — not factory artifacts."""
    src = _read(YOLOE_WORKER_PATH)
    assert "YoloeOpenVocabWorker" in src
    assert "YOLOE" in src
    assert "weights" in src
    assert ".pt" in src
    # Not detection-factory artifact resolution.
    assert "resolve_detector_artifact" not in src
    assert "preferred_backend" not in src
    assert "build_detection_worker" not in src
    assert "backend_live" not in src


def test_open_vocab_loop_default_mode_off() -> None:
    """OpenVocabLoop default mode remains off (not continuous dual-model)."""
    src = _read(OPEN_VOCAB_LOOP_PATH)
    assert 'mode: Mode = "off"' in src or 'mode: Mode = "off"' in src.replace(
        " ", ""
    )
    # Soft: inspect signature default if importable without extras.
    from sentry_ai.models.detection.open_vocab_loop import OpenVocabLoop

    sig = inspect.signature(OpenVocabLoop.__init__)
    mode_param = sig.parameters.get("mode")
    assert mode_param is not None
    assert mode_param.default == "off"
