"""Safe detector artifact path resolution for ORT/TRT (BACK-04).

Pure pathlib/os only — no ultralytics, torch, onnxruntime, or tensorrt.
Resolves existing ``.onnx`` / ``.engine`` candidates under allowlisted roots.
Never invents a path; never accepts path traversal outside roots.
"""

from __future__ import annotations

from pathlib import Path

ALLOWED_DETECTOR_STEMS: frozenset[str] = frozenset({"yolo26n", "yolo26s", "yolo26m"})
ALLOWED_ARTIFACT_SUFFIXES: frozenset[str] = frozenset({".onnx", ".engine"})

__all__ = [
    "ALLOWED_ARTIFACT_SUFFIXES",
    "ALLOWED_DETECTOR_STEMS",
    "resolve_detector_artifact",
    "stem_from_detector_weights",
]


def stem_from_detector_weights(detector_weights: str) -> str:
    """Map detector weight basename to allowlisted artifact stem.

    ``yolo26n.pt`` → ``yolo26n``. Raises ``ValueError`` for unknown stems.
    """
    name = Path(str(detector_weights).strip()).name
    if name.endswith(".pt"):
        stem = name[: -len(".pt")]
    else:
        stem = Path(name).stem
    if stem not in ALLOWED_DETECTOR_STEMS:
        raise ValueError(
            f"unknown detector stem {stem!r}: must be in ALLOWED_DETECTOR_STEMS "
            f"({', '.join(sorted(ALLOWED_DETECTOR_STEMS))})"
        )
    return stem


def _suffix_for_backend(preferred_backend: str) -> str | None:
    """Return expected artifact suffix for ORT/TRT backends, else None."""
    b = str(preferred_backend).strip().lower()
    if b.startswith("backendname."):
        b = b.split(".", 1)[1].lower()
    if b == "onnxruntime":
        return ".onnx"
    if b == "tensorrt":
        return ".engine"
    return None


def _allowlisted_roots(
    *,
    weights_dir: Path | None,
    cwd: Path | None,
    artifact_root: Path | None,
) -> list[Path]:
    roots: list[Path] = []
    for candidate in (weights_dir, artifact_root, cwd):
        if candidate is None:
            continue
        try:
            roots.append(Path(candidate).expanduser().resolve())
        except OSError:
            continue
    return roots


def _is_under_any_root(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            if path == root or path.is_relative_to(root):
                return True
        except (ValueError, OSError):
            continue
    return False


def _validate_explicit_or_env(
    raw: str | Path,
    *,
    expected_suffix: str,
    stem: str,
    roots: list[Path],
) -> Path:
    """Resolve explicit/env path; raise ValueError (path_rejected) if invalid."""
    if not roots:
        raise ValueError(
            "path_rejected: no allowlisted roots configured for artifact path"
        )
    try:
        resolved = Path(raw).expanduser().resolve()
    except (OSError, RuntimeError) as exc:
        raise ValueError(f"path_rejected: cannot resolve artifact path {raw!r}") from exc

    if not _is_under_any_root(resolved, roots):
        raise ValueError(
            f"path_rejected: artifact path outside allowlist: {resolved}"
        )

    suffix = resolved.suffix.lower()
    if suffix not in ALLOWED_ARTIFACT_SUFFIXES:
        raise ValueError(
            f"path_rejected: artifact suffix {suffix!r} not allowlisted "
            f"(expected one of {sorted(ALLOWED_ARTIFACT_SUFFIXES)})"
        )
    if suffix != expected_suffix:
        raise ValueError(
            f"path_rejected: artifact suffix {suffix!r} does not match "
            f"backend expected {expected_suffix!r}"
        )
    # Stem of the file must be an allowlisted detector stem (may differ from
    # detector_weights stem when env overrides to another known model).
    file_stem = resolved.stem
    if file_stem not in ALLOWED_DETECTOR_STEMS:
        raise ValueError(
            f"path_rejected: unknown artifact stem {file_stem!r} "
            f"(allowed: {', '.join(sorted(ALLOWED_DETECTOR_STEMS))})"
        )
    # stem param kept for API symmetry / future strict matching
    _ = stem
    if not resolved.is_file():
        raise ValueError(f"path_rejected: artifact is not a file: {resolved}")
    return resolved


def resolve_detector_artifact(
    *,
    preferred_backend: str,
    detector_weights: str,
    explicit: str | Path | None = None,
    env_value: str | None = None,
    weights_dir: Path | str | None = None,
    cwd: Path | str | None = None,
    artifact_root: Path | str | None = None,
) -> Path | None:
    """Return an existing allowlisted ``.onnx``/``.engine`` path, or ``None``.

    Resolution order (ORT/TRT backends only):

    1. ``explicit`` argument
    2. ``env_value`` (caller may pass ``SENTRY_DETECTOR_ONNX`` / ``ENGINE``)
    3. ``{weights_dir}/{stem}{suffix}`` when the file exists
    4. ``{cwd}/{stem}{suffix}`` when the file exists

    For ``torch`` / ``cpu`` / unknown backends, returns ``None`` unless
    ``explicit`` or ``env_value`` is set (still validated against allowlist).

    Explicit/env paths outside allowlisted roots raise ``ValueError``
    (reason code ``path_rejected`` for factory honesty). Cache/CWD misses
    return ``None`` without inventing a path.
    """
    expected = _suffix_for_backend(preferred_backend)

    # Torch/cpu: skip scan unless operator provided an explicit/env path.
    # If they did, we still need a suffix — infer from backend or from path.
    if expected is None:
        if explicit is None and not (env_value and str(env_value).strip()):
            return None
        # Allow explicit resolution only when suffix can be inferred from path
        # later; for torch, treat as no default artifact role.
        # Prefer rejecting wrong usage by requiring ORT/TRT backend for scan.
        # If explicit provided under torch, still try to validate as .onnx/.engine
        # with suffix taken from the path itself after resolve — but without a
        # backend match we cannot soft-accept. Return None for pure torch.
        return None

    stem = stem_from_detector_weights(detector_weights)

    wd = Path(weights_dir) if weights_dir is not None else None
    cw = Path(cwd) if cwd is not None else Path.cwd()
    ar = Path(artifact_root) if artifact_root is not None else None
    roots = _allowlisted_roots(weights_dir=wd, cwd=cw, artifact_root=ar)

    # 1. Explicit
    if explicit is not None and str(explicit).strip():
        return _validate_explicit_or_env(
            explicit, expected_suffix=expected, stem=stem, roots=roots
        )

    # 2. Env
    if env_value is not None and str(env_value).strip():
        return _validate_explicit_or_env(
            env_value, expected_suffix=expected, stem=stem, roots=roots
        )

    # 3. weights_dir / {stem}{suffix}
    if wd is not None:
        candidate = (wd / f"{stem}{expected}").expanduser().resolve()
        if candidate.is_file() and _is_under_any_root(candidate, roots):
            if candidate.stem in ALLOWED_DETECTOR_STEMS:
                return candidate

    # 4. cwd / {stem}{suffix}
    if cw is not None:
        candidate = (cw / f"{stem}{expected}").expanduser().resolve()
        if candidate.is_file() and _is_under_any_root(candidate, roots):
            if candidate.stem in ALLOWED_DETECTOR_STEMS:
                return candidate

    return None
