"""Safety / privacy / non-autonomy documentation content tests (EDGE-01 cross-cut)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "docs" / "safety-and-privacy.md"
README_PATH = REPO_ROOT / "README.md"


def test_safety_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_safety_doc_non_autonomy_and_privacy() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "perception-only" in lowered or "perception only" in lowered
    assert "localhost" in lowered
    assert "safety interlock" in lowered or "not a safety" in lowered
    # Non-autonomy positioning
    assert (
        "not autonom" in lowered
        or "non-autonom" in lowered
        or "autonomous" in lowered
    )
    assert "cmd_vel" in lowered or "motor" in lowered or "path_plan" in lowered
    assert "allow_cloud" in lowered or "cloud" in lowered
    assert "e-stop" in lowered or "estop" in lowered or "emergency" in lowered
    # Free-space honesty
    assert "free-space" in lowered or "free space" in lowered
    assert "stale" in lowered
    # Headless ≠ auth
    assert "headless" in lowered or "--no-ui" in text
    # LAN unauthenticated risk
    assert (
        "unauth" in lowered
        or "no auth" in lowered
        or "without authentication" in lowered
    )


def test_readme_links_safety_doc() -> None:
    readme = README_PATH.read_text(encoding="utf-8")
    assert "docs/safety-and-privacy.md" in readme
