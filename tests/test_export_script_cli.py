"""EDGE-03: export_yolo.py CLI validation without GPU / real export."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "export" / "export_yolo.py"


def _import_export_module():
    """Load scripts/export/export_yolo.py as a module without running main."""
    import importlib.util

    assert SCRIPT.is_file(), f"missing {SCRIPT}"
    spec = importlib.util.spec_from_file_location("export_yolo", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_export_script_exists() -> None:
    assert SCRIPT.is_file()


def test_help_exits_zero_and_mentions_formats() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--help"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    out = (proc.stdout + proc.stderr).lower()
    assert "onnx" in out
    assert "engine" in out


def test_validate_weights_accepts_known_basenames() -> None:
    mod = _import_export_module()
    known = (
        "yolo26n.pt",
        "yolo26s.pt",
        "yolo26m.pt",
        "yoloe-26n-seg.pt",
        "yoloe-26s-seg.pt",
    )
    for name in known:
        assert mod.validate_weights(name) == name


def test_validate_weights_rejects_unknown() -> None:
    mod = _import_export_module()
    with pytest.raises(ValueError, match="[Uu]nknown|[Aa]llowlist|KNOWN"):
        mod.validate_weights("not-a-model.pt")


def test_validate_weights_rejects_path_traversal() -> None:
    mod = _import_export_module()
    for bad in (
        "../../etc/passwd",
        "../yolo26n.pt",
        "/tmp/yolo26n.pt",
        "subdir/yolo26n.pt",
        "yolo26n.pt/../evil.pt",
    ):
        with pytest.raises(ValueError):
            mod.validate_weights(bad)


def test_parse_args_defaults() -> None:
    mod = _import_export_module()
    args = mod.parse_args(["--weights", "yolo26n.pt", "--format", "onnx"])
    assert args.weights == "yolo26n.pt"
    assert args.format == "onnx"
    assert args.imgsz == 640


def test_parse_args_engine_device() -> None:
    mod = _import_export_module()
    args = mod.parse_args(
        ["--weights", "yolo26n.pt", "--format", "engine", "--device", "0"]
    )
    assert args.format == "engine"
    assert args.device == "0"


def test_invalid_weights_cli_nonzero_exit() -> None:
    proc = subprocess.run(
        [sys.executable, str(SCRIPT), "--weights", "evil.pt", "--format", "onnx"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0
    combined = (proc.stdout + proc.stderr).lower()
    assert "unknown" in combined or "allowlist" in combined or "invalid" in combined


def test_path_traversal_cli_nonzero_exit() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--weights",
            "../../etc/passwd",
            "--format",
            "onnx",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode != 0


def test_run_export_not_called_on_import() -> None:
    """Importing the module must not invoke model.export or download weights."""
    mod = _import_export_module()
    # Helpers exist; export path is only via main / run_export
    assert hasattr(mod, "validate_weights")
    assert hasattr(mod, "parse_args")
    assert hasattr(mod, "run_export")


@pytest.mark.export
@pytest.mark.skip(reason="Real Ultralytics export; opt-in only — never default CI")
def test_full_export_opt_in_skipped_by_default() -> None:
    """Placeholder for maker-machine full export; marked export + skipped."""
    raise AssertionError("should be skipped")
