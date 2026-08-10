"""ORT-03: optional onnx extra pin and packaging hygiene."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"


def _optional_deps() -> dict[str, list[str]]:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["optional-dependencies"]


def test_onnx_extra_exists_with_locked_pin() -> None:
    extras = _optional_deps()
    assert "onnx" in extras
    body = extras["onnx"]
    assert len(body) >= 1
    pin = " ".join(body)
    assert "onnxruntime>=1.20" in pin
    assert "<1.29" in pin
    # Single-pin form matching RESEARCH lock
    assert any(
        re.fullmatch(r"onnxruntime>=1\.20,<1\.29", item.strip()) for item in body
    )


def test_no_tensorrt_optional_extra() -> None:
    extras = _optional_deps()
    assert "tensorrt" not in extras
    # No tensorrt package listed under any extra name
    for name, deps in extras.items():
        joined = " ".join(deps).lower()
        assert "tensorrt" not in joined, f"tensorrt appears under extra {name!r}"


def test_onnx_extra_does_not_pin_gpu_ort() -> None:
    extras = _optional_deps()
    body = " ".join(extras["onnx"]).lower()
    assert "onnxruntime-gpu" not in body


def test_pyproject_text_documents_onnx_install() -> None:
    text = PYPROJECT.read_text(encoding="utf-8")
    assert "onnxruntime>=1.20,<1.29" in text
    assert "--extra onnx" in text or "extra onnx" in text


def test_wheel_force_include_has_no_engines_or_onnx() -> None:
    """Wheel force-include ships profiles + UI static only — never model artifacts."""
    text = PYPROJECT.read_text(encoding="utf-8")
    assert 'packages = ["src/sentry_ai"]' in text or "packages = [" in text
    assert "src/sentry_ai/config/profiles" in text
    assert "src/sentry_ai/ui/static" in text
    data = tomllib.loads(text)
    force = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("force-include", {})
    )
    assert force, "expected hatch wheel force-include for profiles + UI static"
    for src, dst in force.items():
        assert not str(src).endswith((".engine", ".onnx", ".pt")), src
        assert not str(dst).endswith((".engine", ".onnx", ".pt")), dst
    joined_src = " ".join(str(s) for s in force)
    assert "profiles" in joined_src
    assert "static" in joined_src or "ui" in joined_src
