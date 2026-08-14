"""OPS-03: v0.3 honesty matrix — lock existing synthetic suites in CI.

Documents Phase 13–17 coverage so default ``pytest -q`` keeps fit / apply /
honesty / persist without a room, Jetson, CUDA, or ``--extra depth``.

| Theme             | Files |
|-------------------|-------|
| Fit / reject      | test_calibration_fit.py |
| Apply / state     | test_calibration_state.py, test_depth_loop.py, |
|                   | test_cli_calibration_inject.py |
| Kind/unit honesty | test_calibration_validators.py, |
|                   | test_depth_kind_honesty.py, |
|                   | test_perception_store_depth_honesty.py |
| Free-space meters | test_free_space_bands.py, test_free_space_loop.py, |
|                   | test_assemble_perception_frame.py |
| Persist / serve   | test_calibration_store.py, test_calibration_persist.py, |
|                   | test_api_calibration.py |
| Docs (18-01)      | test_calibration_docs.py |

CI contract is locked here and in ``tests/test_edge_ci_workflow.py``
(EDGE-CI-02). No new product assertions — path existence + ``ci.yml``
static lock only.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CI_YML = REPO_ROOT / ".github" / "workflows" / "ci.yml"

V03_INVENTORY = (
    "tests/test_calibration_fit.py",  # fit / reject
    "tests/test_calibration_state.py",  # apply / draft
    "tests/test_depth_loop.py",  # apply_map + late W×H
    "tests/test_calibration_validators.py",  # kind/unit + FS units
    "tests/test_depth_kind_honesty.py",
    "tests/test_perception_store_depth_honesty.py",
    "tests/test_free_space_bands.py",  # FS-01/02
    "tests/test_free_space_loop.py",  # FS-03
    "tests/test_assemble_perception_frame.py",
    "tests/test_calibration_store.py",  # persist I/O
    "tests/test_calibration_persist.py",  # try_reapply
    "tests/test_api_calibration.py",  # save/clear/cancel
    "tests/test_cli_calibration_inject.py",
    "tests/test_calibration_docs.py",  # 18-01 OPS-02
)


def test_v03_inventory_files_exist() -> None:
    for rel in V03_INVENTORY:
        path = REPO_ROOT / rel
        assert path.is_file(), f"OPS-03 inventory missing {rel}"


def test_v03_ci_stays_dev_extra_only() -> None:
    assert CI_YML.is_file()
    yml = CI_YML.read_text(encoding="utf-8")
    lowered = yml.lower()
    assert "ubuntu-latest" in lowered
    assert "uv sync --extra dev" in yml
    assert "ruff" in lowered
    assert "pytest" in lowered
    assert "sentry health" in yml
    assert "--extra depth" not in yml
    assert "--extra detect" not in yml
    assert "--extra onnx" not in yml
    assert "self-hosted" not in lowered
    assert "tensorrt" not in lowered
    assert "jetson" not in lowered
    assert "cuda" not in lowered
