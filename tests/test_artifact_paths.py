"""BACK-04: resolve_detector_artifact allowlist + path safety (no network)."""

from __future__ import annotations

import pytest

from sentry_ai.config.artifact_paths import (
    ALLOWED_ARTIFACT_SUFFIXES,
    ALLOWED_DETECTOR_STEMS,
    resolve_detector_artifact,
)


def test_allowed_stems_and_suffixes() -> None:
    assert ALLOWED_DETECTOR_STEMS == frozenset({"yolo26n", "yolo26s", "yolo26m"})
    assert ALLOWED_ARTIFACT_SUFFIXES == frozenset({".onnx", ".engine"})


def test_resolve_onnx_under_weights_dir(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    artifact = weights_dir / "yolo26n.onnx"
    artifact.write_bytes(b"fake-onnx")

    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        weights_dir=weights_dir,
        cwd=tmp_path / "empty_cwd",
    )
    assert got == artifact.resolve()


def test_resolve_engine_under_weights_dir(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    artifact = weights_dir / "yolo26n.engine"
    artifact.write_bytes(b"fake-engine")

    got = resolve_detector_artifact(
        preferred_backend="tensorrt",
        detector_weights="yolo26n.pt",
        weights_dir=weights_dir,
        cwd=tmp_path / "empty_cwd",
    )
    assert got == artifact.resolve()


def test_env_override_under_allowlisted_root_wins(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    cache_artifact = weights_dir / "yolo26n.onnx"
    cache_artifact.write_bytes(b"cache")
    env_artifact = weights_dir / "yolo26s.onnx"
    env_artifact.write_bytes(b"env")

    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        env_value=str(env_artifact),
        weights_dir=weights_dir,
        cwd=tmp_path,
    )
    assert got == env_artifact.resolve()


def test_cwd_basename_candidate(tmp_path) -> None:
    cwd = tmp_path / "work"
    cwd.mkdir()
    artifact = cwd / "yolo26n.onnx"
    artifact.write_bytes(b"cwd-onnx")

    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        weights_dir=tmp_path / "missing_weights",
        cwd=cwd,
    )
    assert got == artifact.resolve()


def test_missing_returns_none(tmp_path) -> None:
    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        weights_dir=tmp_path / "weights",
        cwd=tmp_path,
    )
    assert got is None


def test_torch_backend_skips_scan_without_explicit(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    (weights_dir / "yolo26n.onnx").write_bytes(b"x")

    got = resolve_detector_artifact(
        preferred_backend="torch",
        detector_weights="yolo26n.pt",
        weights_dir=weights_dir,
        cwd=tmp_path,
    )
    assert got is None


def test_reject_path_traversal_explicit(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    with pytest.raises(ValueError, match="path_rejected|allowlist|outside"):
        resolve_detector_artifact(
            preferred_backend="onnxruntime",
            detector_weights="yolo26n.pt",
            explicit="../../etc/passwd",
            weights_dir=weights_dir,
            cwd=tmp_path,
        )


def test_reject_absolute_outside_roots(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    outside = tmp_path.parent / "outside_yolo26n.onnx"
    # Use a path that resolve() keeps outside allowlisted roots.
    outside_path = tmp_path / ".." / "not_allowlisted_yolo26n.onnx"
    # Create a real file outside weights_dir and cwd after resolve
    real_outside = (tmp_path / "outside_root")
    real_outside.mkdir()
    evil = real_outside / "yolo26n.onnx"
    evil.write_bytes(b"evil")

    with pytest.raises(ValueError, match="path_rejected|allowlist|outside"):
        resolve_detector_artifact(
            preferred_backend="onnxruntime",
            detector_weights="yolo26n.pt",
            explicit=str(evil),
            weights_dir=weights_dir,
            cwd=tmp_path / "cwd",
        )


def test_reject_wrong_suffix_for_backend(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    engine = weights_dir / "yolo26n.engine"
    engine.write_bytes(b"engine")

    # onnxruntime must not return .engine from cache/cwd scan
    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        weights_dir=weights_dir,
        cwd=tmp_path,
    )
    assert got is None

    with pytest.raises(ValueError, match="path_rejected|suffix|allowlist"):
        resolve_detector_artifact(
            preferred_backend="onnxruntime",
            detector_weights="yolo26n.pt",
            explicit=str(engine),
            weights_dir=weights_dir,
            cwd=tmp_path,
        )


def test_reject_unknown_stem(tmp_path) -> None:
    weights_dir = tmp_path / "weights"
    weights_dir.mkdir()
    evil = weights_dir / "evil.onnx"
    evil.write_bytes(b"x")

    with pytest.raises(ValueError, match="stem|unknown|allowlist"):
        resolve_detector_artifact(
            preferred_backend="onnxruntime",
            detector_weights="evil.pt",
            weights_dir=weights_dir,
            cwd=tmp_path,
        )


def test_reject_nested_subdir_basename_only_policy(tmp_path) -> None:
    """Cache/CWD scan is basename-only; nested subdir is not auto-discovered."""
    weights_dir = tmp_path / "weights"
    sub = weights_dir / "subdir"
    sub.mkdir(parents=True)
    nested = sub / "yolo26n.onnx"
    nested.write_bytes(b"nested")

    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        weights_dir=weights_dir,
        cwd=tmp_path,
    )
    assert got is None


def test_explicit_under_artifact_root_allowed(tmp_path) -> None:
    artifact_root = tmp_path / "artifacts"
    artifact_root.mkdir()
    artifact = artifact_root / "yolo26n.onnx"
    artifact.write_bytes(b"ok")

    got = resolve_detector_artifact(
        preferred_backend="onnxruntime",
        detector_weights="yolo26n.pt",
        explicit=str(artifact),
        weights_dir=tmp_path / "weights",
        cwd=tmp_path / "cwd",
        artifact_root=artifact_root,
    )
    assert got == artifact.resolve()
