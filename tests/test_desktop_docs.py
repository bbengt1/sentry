"""EDGE-01: Desktop GPU primary path documentation content tests."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "desktop-gpu.md"
README_PATH = REPO_ROOT / "README.md"


def test_desktop_gpu_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_desktop_doc_covers_primary_maker_path() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "desktop-gpu" in lowered
    assert "primary" in lowered
    assert "detect" in lowered
    assert "depth" in lowered
    assert "--profile desktop-gpu" in text or "profile desktop-gpu" in lowered
    assert "uv sync" in lowered
    assert "sentry serve" in lowered
    assert "127.0.0.1:8000" in text or "http://127.0.0.1:8000" in text
    assert "sentry_model_cache" in lowered or "~/.cache/sentry-ai" in lowered
    assert "third_party" in lowered or "agpl" in lowered
    assert "/v1/snapshot" in text
    assert "/v1/stream" in text
    # Honest FPS — no invented numbers required; allow "depends on"
    assert "depends on" in lowered or "gpu" in lowered
    # Profiles context
    assert "cpu-fallback" in lowered
    assert "jetson" in lowered or "export" in lowered
    # Headless pointer
    assert "--no-ui" in text or "headless" in lowered
    # Open-vocab optional
    assert "open-vocab" in lowered or "open vocab" in lowered or "yoloe" in lowered


def test_readme_links_desktop_gpu_doc() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    assert "docs/desktop-gpu.md" in readme
    assert "desktop-gpu" in readme.lower()
