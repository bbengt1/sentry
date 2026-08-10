"""EDGE-DOC-01: Edge serve hub keyword assertions (no hardware)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "edge-serve.md"
README_PATH = REPO_ROOT / "README.md"


def test_edge_serve_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_edge_serve_numbered_export_to_serve_path() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "export" in lowered
    assert "sentry serve" in lowered
    assert "--profile" in text
    assert "onnx" in lowered
    assert "tensorrt" in lowered or ".engine" in text
    assert "--no-ui" in text or "headless" in lowered
    assert "backend_live" in lowered or "backend_requested" in lowered
    assert "fallback" in lowered or "soft" in lowered
    assert "measure" in lowered
    assert "30 fps dual-model" not in lowered


def test_readme_links_edge_serve_doc() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    assert "docs/edge-serve.md" in readme or "edge-serve" in readme
