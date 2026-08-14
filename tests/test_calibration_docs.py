"""OPS-02: Calibration operator hub keyword assertions (no hardware)."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

HUB_PATHS = (
    "docs/calibration.md",
    "docs/perception-frame.md",
    "docs/safety-and-privacy.md",
    "README.md",
    "docs/README.md",
    "docs/api-reference.md",
    "docs/cli.md",
    "docs/configuration.md",
    "docs/architecture.md",
    "docs/desktop-gpu.md",
)

CALIBRATION_DOC = REPO_ROOT / "docs" / "calibration.md"

_STALE_PHRASES = (
    "always ordinal",
    "v1 always ordinal",
    "precise meters",
    "precise metres",
    "precise metre",
    "no distance_m",
)


def _plain(text: str) -> str:
    """Lowercase and strip markdown emphasis/code so stale phrases match."""
    return text.lower().replace("*", "").replace("`", "")


def _hub_texts() -> dict[str, str]:
    texts: dict[str, str] = {}
    for rel in HUB_PATHS:
        path = REPO_ROOT / rel
        assert path.is_file(), f"missing hub {path}"
        texts[rel] = path.read_text(encoding="utf-8")
    return texts


def test_calibration_doc_exists() -> None:
    assert CALIBRATION_DOC.is_file(), f"missing {CALIBRATION_DOC}"


def test_calibration_hub_wizard_and_honesty() -> None:
    text = CALIBRATION_DOC.read_text(encoding="utf-8")
    lowered = text.lower()
    assert "wizard" in lowered
    assert "apply" in lowered
    assert "cancel" in lowered
    assert "clear" in lowered
    assert "metric_calibrated" in lowered
    assert "monocular" in lowered
    assert (
        "vehicle-grade" in lowered
        or "not vehicle-grade" in lowered
        or "approximate" in lowered
    )
    assert "none" in lowered or "applied" in lowered
    assert "ignored_mismatch" in lowered or "fingerprint" in lowered
    assert "~/.config" not in text
    assert "always ordinal" not in _plain(text)
    assert "precise meters" not in lowered
    assert "precise metres" not in lowered


def test_calibration_hub_persist_stack_path() -> None:
    text = CALIBRATION_DOC.read_text(encoding="utf-8")
    assert "SENTRY_MODEL_CACHE" in text or "calibration/" in text
    assert "SENTRY_CALIBRATION_DIR" in text or "--calibration-file" in text
    assert "yaml" in text.lower()


def test_hubs_forbid_stale_always_ordinal_and_overclaim() -> None:
    for path, text in _hub_texts().items():
        plain = _plain(text)
        for phrase in _STALE_PHRASES:
            assert phrase not in plain, f"{path} contains stale phrase {phrase!r}"
        assert "full self-driving" not in plain, f"{path}: FSD claim"
        assert "fsd-capable" not in plain, f"{path}: fsd-capable claim"
        if "autonomous vehicle" in plain:
            idx = plain.find("autonomous vehicle")
            window = plain[max(0, idx - 40) : idx + 40]
            assert "not" in window, f"{path}: autonomous vehicle as claim"


def test_readme_and_docs_index_link_calibration_hub() -> None:
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    docs_index = (REPO_ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "calibration.md" in readme
    assert "calibration.md" in docs_index
