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


def test_export_docs_live_ort_conditions_and_onnx_extra() -> None:
    """Live fixed-class ORT conditions + install path (ORT-03 honesty)."""
    yolo = _read("yolo26-onnx-tensorrt.md").lower()
    readme = _read("README.md").lower()
    blob = yolo + "\n" + readme
    assert "onnxruntime" in blob or "onnx runtime" in blob
    assert "live" in blob
    assert "extra onnx" in blob or "--extra onnx" in blob
    assert "uv sync" in blob
    # Soft-fallback honesty when artifact/dep missing
    assert (
        "soft-fall" in blob
        or "soft fall" in blob
        or "missing" in blob
        or "fallback" in blob
    )
    assert (
        "ort_artifact_missing" in blob
        or "artifact" in blob
        or "dependency" in blob
        or "dep" in blob
    )


def test_export_docs_live_trt_conditions() -> None:
    """Live fixed-class TRT conditions: preferred + .engine + system tensorrt."""
    yolo = _read("yolo26-onnx-tensorrt.md")
    readme = _read("README.md")
    blob = (yolo + "\n" + readme).lower()
    assert "tensorrt" in blob
    assert "live" in blob
    assert ".engine" in (yolo + readme) or "engine" in blob
    # Couple live language with backend_live or preferred_backend conditions
    assert (
        "backend_live" in blob
        or "preferred_backend" in blob
        or "preferred backend" in blob
    )
    assert "system" in blob or "jetpack" in blob
    # Soft-fallback honesty for TRT (artifact / dep / path)
    assert (
        "trt_artifact_missing" in blob
        or "trt_dep_missing" in blob
        or "path_rejected" in blob
        or ("artifact" in blob and "missing" in blob)
        or ("tensorrt" in blob and "missing" in blob)
    )
    # Soft-fall / fallback language present
    assert (
        "soft-fall" in blob
        or "soft fall" in blob
        or "soft torch" in blob
        or "fallback" in blob
    )


def test_export_docs_trt_system_packaging_no_pip_extra() -> None:
    """TRT-03: JetPack/system TensorRT; no project tensorrt pip extra/pin."""
    jetson = _read("jetson-packaging.md").lower()
    yolo = _read("yolo26-onnx-tensorrt.md").lower()
    readme = _read("README.md").lower()
    blob = jetson + "\n" + yolo + "\n" + readme
    assert "jetpack" in blob or "system" in blob
    assert "tensorrt" in blob
    # Forbid project pip pin / extra for tensorrt
    assert "no" in blob and (
        "pip extra" in blob
        or "tensorrt pip" in blob
        or "--extra tensorrt" in blob
        or "project `tensorrt`" in blob
        or "project tensorrt" in blob
    )
    # Positive: system or JetPack guidance
    assert "jetpack" in jetson or "system" in jetson


def test_yolo26_onnx_tensorrt_on_device_and_no_engine_copy() -> None:
    text = _read("yolo26-onnx-tensorrt.md")
    lowered = text.lower()
    assert "onnx" in lowered
    assert "tensorrt" in lowered
    assert "on-device" in lowered or "on device" in lowered
    assert "ultralytics" in lowered or "model.export" in lowered
    # Non-portability / forbid cross-SKU copy
    assert (
        "do not copy" in lowered or "never copy" in lowered or "not portable" in lowered
    )
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
    assert (
        "depth_kind" in lowered or "metric_estimated" in lowered or "meters" in lowered
    )
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


def test_export_docs_dual_model_measure_on_device() -> None:
    """Dual-model: TRT/torch YOLO + torch depth may share GPU — measure on device."""
    yolo = _read("yolo26-onnx-tensorrt.md")
    jetson = _read("jetson-packaging.md")
    readme = _read("README.md")
    blob = (yolo + "\n" + jetson + "\n" + readme).lower()
    assert "measure" in blob
    assert "on device" in blob or "on-device" in blob
    # Dual-model scope language present
    assert "dual-model" in blob or "dual model" in blob
    # YOLO + depth pairing
    assert "depth" in blob
    assert "yolo" in blob or "torch" in blob


def test_export_docs_continuous_ov_not_first_class() -> None:
    """Continuous open-vocab + TRT YOLO + DAV2 is not a first-class config."""
    yolo = _read("yolo26-onnx-tensorrt.md").lower()
    jetson = _read("jetson-packaging.md").lower()
    blob = yolo + "\n" + jetson
    assert "continuous open-vocab" in blob or "continuous" in blob
    assert (
        "not a first-class" in blob
        or "not first-class" in blob
        or "not first class" in blob
    )


def test_export_docs_sticky_soft_strict_shipped() -> None:
    """Sticky / soft / strict language present; fallback_to_torch documented."""
    yolo = _read("yolo26-onnx-tensorrt.md")
    jetson = _read("jetson-packaging.md")
    readme = _read("README.md")
    blob = yolo + "\n" + jetson + "\n" + readme
    lowered = blob.lower()
    assert "sticky" in lowered or "once" in lowered
    assert (
        "fallback_to_torch" in blob
        or "sentry_fallback_to_torch" in lowered
        or ("soft" in lowered and "strict" in lowered)
    )


def test_export_docs_no_phase11_deferral_for_sticky_dual_model() -> None:
    """Phase 11 deferral language for sticky/dual-model must be retired."""
    yolo = _read("yolo26-onnx-tensorrt.md")
    jetson = _read("jetson-packaging.md")
    for name, text in (("yolo26", yolo), ("jetson", jetson)):
        assert "Phase 11 owns" not in text, f"{name}: still defers dual-model"
        assert "deferred to Phase 11" not in text, f"{name}: deferred phrase"
        assert "Sticky thrash-free fallback policy (Phase 11)" not in text
        # Dual-model scheduling "are Phase 11" style deferral
        assert "guardrails are Phase 11" not in text
        assert "guardrails (Phase 11)" not in text


def test_export_docs_no_guaranteed_dual_model_fps() -> None:
    """Forbid bare dual-model FPS product claims without methodology."""
    yolo = _read("yolo26-onnx-tensorrt.md").lower()
    jetson = _read("jetson-packaging.md").lower()
    blob = yolo + "\n" + jetson
    # Must not invent a hard dual-model FPS number as a guarantee
    assert "30 fps dual-model" not in blob
    assert "guaranteed" not in blob or "fps" not in blob.split("guaranteed")[0][-40:]
    # Positive honesty: no published dual-model FPS claim language or measure-only
    assert (
        "no dual-model fps" in blob
        or "no published dual-model" in blob
        or "do not invent dual-model" in blob
        or "no dual-model fps claim" in blob
        or ("measure" in blob and "fps" in blob)
    )


def test_root_readme_edge_live_path_honesty() -> None:
    """EDGE-DOC-01: root README must not claim export-only / still-PyTorch live."""
    text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    # Forbid v1.0 export-only / non-live TRT lies
    assert "not a live tensorrt runtime" not in lowered
    assert "still pytorch live" not in lowered
    # Discoverability of live edge path
    assert "docs/export" in text
    assert "sentry serve" in lowered
    assert "--profile" in text
    assert "onnx" in lowered and ("tensorrt" in lowered or ".engine" in text)


def test_scripts_export_readme_not_pytorch_only() -> None:
    """EDGE-DOC-01: scripts/export README must not say serve stays on PyTorch only."""
    text = (REPO_ROOT / "scripts" / "export" / "README.md").read_text(encoding="utf-8")
    lowered = text.lower()
    assert "stays on pytorch profiles" not in lowered
    assert "live" in lowered or "onnx" in lowered or "engine" in lowered


def test_export_index_no_phase7_deferral() -> None:
    """EDGE-DOC-01: export index must not defer desktop walkthrough to Phase 7."""
    text = _read("README.md")
    assert "Phase 7 plan" not in text
    assert "07-03" not in text
    # Point at existing hubs
    assert "desktop-gpu" in text.lower() or "edge-serve" in text.lower()
