"""EDGE-03: Export docs honesty keyword assertions (no Jetson / no GPU)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
EXPORT_DIR = REPO_ROOT / "docs" / "export"

REQUIRED_DOCS = (
    "README.md",
    "yolo26-onnx-tensorrt.md",
    "yoloe-export.md",
    "depth-anything-v2.md",
    "jetson-packaging.md",
)


def _read(name: str) -> str:
    path = EXPORT_DIR / name
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _all_export_text() -> str:
    return "\n".join(_read(name) for name in REQUIRED_DOCS)


def test_export_docs_exist() -> None:
    for name in REQUIRED_DOCS:
        assert (EXPORT_DIR / name).is_file(), f"missing docs/export/{name}"


def test_export_index_offline_and_pytorch_live() -> None:
    text = _read("README.md")
    lowered = text.lower()
    assert "onnx" in lowered
    assert "tensorrt" in lowered
    assert "offline" in lowered
    assert "pytorch" in lowered
    assert "profile" in lowered


def test_yolo26_onnx_tensorrt_on_device_and_no_engine_copy() -> None:
    text = _read("yolo26-onnx-tensorrt.md")
    lowered = text.lower()
    assert "onnx" in lowered
    assert "tensorrt" in lowered
    assert "on-device" in lowered or "on device" in lowered
    assert "ultralytics" in lowered or "model.export" in lowered
    # Non-portability / forbid cross-SKU copy
    assert "do not copy" in lowered or "never copy" in lowered or "not portable" in lowered
    assert ".engine" in text or "engine" in lowered
    assert "jetpack" in lowered or "sku" in lowered


def test_yoloe_export_experimental_with_pytorch_fallback() -> None:
    text = _read("yoloe-export.md")
    lowered = text.lower()
    assert "yoloe" in lowered
    assert "experimental" in lowered
    assert "pytorch" in lowered
    assert "onnx" in lowered or "export" in lowered
    assert "agpl" in lowered or "third_party" in lowered
    # Supported edge OV path remains PyTorch
    assert "on-demand" in lowered or "open-vocab" in lowered or "open vocab" in lowered


def test_depth_export_feasibility_and_relative_honesty() -> None:
    text = _read("depth-anything-v2.md")
    lowered = text.lower()
    assert "depth anything" in lowered or "depth-anything" in lowered
    assert "huggingface" in lowered or "hf" in lowered or "transformers" in lowered
    assert "small" in lowered
    # Relative vs metric honesty — no silent meters
    assert "relative" in lowered
    assert "depth_kind" in lowered or "metric_estimated" in lowered or "meters" in lowered
    assert "community" in lowered or "onnx" in lowered or "tensorrt" in lowered


def test_jetson_packaging_honesty() -> None:
    text = _read("jetson-packaging.md")
    lowered = text.lower()
    assert "jetson" in lowered or "jetpack" in lowered
    assert "tensorrt" in lowered
    assert "on-device" in lowered or "on device" in lowered
    # Profile jetson = n + DAV2 Small + OV off/on-demand
    assert "yolo" in lowered
    assert "small" in lowered
    assert "on-demand" in lowered or "open-vocab" in lowered or "open vocab" in lowered
    # No prebuilt engines
    assert "prebuilt" in lowered or "do not ship" in lowered or "not ship" in lowered
    # Measure on device; no invented FPS as product claim
    assert "measure" in lowered
    # Pi/CPU lite / best-effort
    assert "lite" in lowered or "best-effort" in lowered or "best effort" in lowered
    # CI does not require Jetson
    assert "ci" in lowered


def test_export_docs_agpl_or_third_party_reference() -> None:
    blob = _all_export_text().lower()
    assert "agpl" in blob or "third_party_models" in blob or "third-party" in blob


def test_export_docs_forbid_cross_device_engine_as_supported() -> None:
    """Negative: docs must not instruct copying engines as a supported path."""
    blob = _all_export_text().lower()
    # Require non-portability language
    assert (
        "do not copy" in blob
        or "never copy" in blob
        or "not portable" in blob
        or "non-portable" in blob
        or "not portab" in blob
    )
    assert "on-device" in blob or "on device" in blob
    # Must not present "copy the .engine to jetson" as recommended without forbid
    # Soft check: if "copy" appears with engine, forbid language should dominate
    assert "prebuilt" in blob or "do not ship" in blob or "not ship" in blob


def test_readme_links_export_docs() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "docs/export" in readme
    lowered = readme.lower()
    assert "export" in lowered
    assert "onnx" in lowered or "tensorrt" in lowered or "edge" in lowered
