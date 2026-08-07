"""FOUND-05: THIRD_PARTY_MODELS.md license documentation."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DOC_PATH = REPO_ROOT / "THIRD_PARTY_MODELS.md"


def test_third_party_models_doc_exists() -> None:
    assert DOC_PATH.is_file(), f"missing {DOC_PATH}"


def test_doc_documents_apache_default_small_depth() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "Apache-2.0" in text
    assert "Small" in text
    assert "Depth Anything V2" in text or "Depth Anything" in text
    # Default Yes for commercially friendly small depth
    assert "Yes" in text


def test_doc_mentions_agpl_and_nc_as_non_default() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    assert "AGPL" in text
    assert "CC-BY-NC" in text or "NC" in text
    # Non-default markers present
    assert "No" in text or "non-default" in text.lower() or "research" in text.lower()


def test_doc_policy_local_oss_no_cloud_keys() -> None:
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "local" in lowered
    assert "allow_cloud" in lowered or "cloud" in lowered


def test_doc_yolo_phase3_active_agpl_and_cache() -> None:
    """Phase 3: YOLO row is active + AGPL + offline cache wording (MODEL-02)."""
    text = DOC_PATH.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "yolo26" in lowered or "yolo" in lowered
    assert "agpl" in lowered
    assert "phase 3" in lowered
    assert "planned phase 3" not in lowered  # no longer "Planned Phase 3" only
    assert "sentry_model_cache" in lowered or "sentry-ai/weights" in lowered
    assert "offline" in lowered
    assert "cache" in lowered
