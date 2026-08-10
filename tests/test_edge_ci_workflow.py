"""EDGE-CI-02: Default GitHub Actions stays Jetson/GPU-free.

Static locks on `.github/workflows/ci.yml` and artifact gitignore hygiene so
contributors never need Jetson hardware or TensorRT GPU in default CI.

EDGE-CI-01 (backend selection / missing-artifact honesty / factory wiring)
lives in existing mock suites — do not re-implement here:

- desktop-gpu default → live=torch, reason=None
  (tests/test_detection_factory.py)
- jetson no artifact (soft) → live=torch, trt_artifact_missing
  (tests/test_detection_factory.py)
- cpu-fallback no artifact (soft) → live=torch, ort_artifact_missing
  (tests/test_detection_factory.py)
- ORT live mock → artifact + dep → live=onnxruntime
  (tests/test_detection_factory.py)
- TRT live mock → artifact + dep → live=tensorrt
  (tests/test_detection_factory.py)
- strict miss → worker=None, live=None, same reason codes
  (tests/test_detection_factory.py)
- sticky → factory once at serve; not in DetectionLoop
  (factory + serve call-site tests)
- status honesty pass-through → backend_live / backend_reason
  (tests/test_backend_honesty_status.py)
- artifact allowlist → path rejection reasons
  (tests/test_artifact_paths.py)
- ORT/TRT parity mocks → Detection contract without real engines
  (tests/test_ort_parity.py, tests/test_trt_parity.py)
- EDGE-RT-04 torch-only → torch path without GPU extras
  (tests/test_edge_rt04_torch_only.py)
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"
GITIGNORE = REPO_ROOT / ".gitignore"


def test_default_gha_no_jetson_or_tensorrt_gpu() -> None:
    assert CI_YML.is_file()
    yml = CI_YML.read_text(encoding="utf-8")
    lowered = yml.lower()
    assert "ubuntu-latest" in lowered
    assert "self-hosted" not in lowered
    assert "tensorrt" not in lowered
    assert "jetson" not in lowered
    # Install path must not require GPU / ML extras for default suite
    assert "uv sync --extra dev" in yml
    assert "--extra detect" not in yml
    assert "--extra onnx" not in yml
    assert "--extra depth" not in yml
    # Smoke steps present (current workflow contract)
    assert "ruff check" in yml or "ruff" in lowered
    assert "pytest" in lowered
    assert "sentry health" in yml


def test_ci_single_job_no_gpu_labels() -> None:
    yml = CI_YML.read_text(encoding="utf-8")
    lowered = yml.lower()
    # No CUDA / GPU runner labels
    assert "cuda" not in lowered
    assert "gpu" not in lowered
    assert "runs-on:" in lowered


def test_gitignore_ignores_engine_and_onnx() -> None:
    text = GITIGNORE.read_text(encoding="utf-8")
    assert "*.engine" in text
    assert "*.onnx" in text
    assert "*.pt" in text
