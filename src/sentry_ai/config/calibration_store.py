"""YAML persist of applied CalibrationParams (PER-01 / PER-03).

STACK path: ``SENTRY_CALIBRATION_DIR`` or
``{SENTRY_MODEL_CACHE|default_cache_root()}/calibration/{safe_id}.yaml``.
YAML only — no platformdirs, no profile merge, no JSON.

I/O is ``yaml.safe_load`` / ``yaml.safe_dump`` only (never ``yaml.load``).
Atomic temp+``os.replace``. No depth maps, samples, or freeze pins on disk.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from sentry_ai.models.cache import default_cache_root
from sentry_ai.schemas.calibration import CalibrationFingerprint, CalibrationParams

__all__ = [
    "LoadResult",
    "calibration_path",
    "default_calibration_dir",
    "delete_params",
    "fingerprints_match",
    "load_params",
    "safe_camera_stem",
    "save_params",
]

_SAFE_STEM = re.compile(r"^[A-Za-z0-9._-]+$")
_BANNED_YAML_KEYS = ("depth_map", "samples", "freeze")


@dataclass(frozen=True)
class LoadResult:
    status: Literal["none", "ok", "error"]
    params: CalibrationParams | None = None
    reason: str | None = None


def default_calibration_dir() -> Path:
    """SENTRY_CALIBRATION_DIR or {cache_root}/calibration.

    cache_root = SENTRY_MODEL_CACHE or default_cache_root().
    Does not create the directory (save does).
    """
    env = os.environ.get("SENTRY_CALIBRATION_DIR")
    if env:
        return Path(env)
    cache = os.environ.get("SENTRY_MODEL_CACHE")
    root = Path(cache) if cache else default_cache_root()
    return root / "calibration"


def safe_camera_stem(camera_id: str) -> str:
    """Sanitize to a single path stem. Reject empty, '..', '/', '\\\\'."""
    raw = str(camera_id).strip()
    if not raw:
        raise ValueError("unsafe / empty camera_id stem")
    if raw.startswith("."):
        raise ValueError("unsafe / empty camera_id stem")
    if ".." in raw or "/" in raw or "\\" in raw:
        raise ValueError("unsafe / empty camera_id stem")
    if not _SAFE_STEM.fullmatch(raw):
        raise ValueError("unsafe / empty camera_id stem")
    return raw


def calibration_path(
    camera_id: str,
    *,
    directory: Path | None = None,
    explicit_file: Path | None = None,
) -> Path:
    """explicit_file wins; else directory/default_calibration_dir() / {stem}.yaml."""
    if explicit_file is not None:
        return Path(explicit_file)
    root = Path(directory) if directory is not None else default_calibration_dir()
    return root / f"{safe_camera_stem(camera_id)}.yaml"


def fingerprints_match(
    saved: CalibrationFingerprint,
    live: CalibrationFingerprint,
) -> tuple[bool, str | None]:
    """Return (True, None) or (False, reason_code).

    camera_id always; depth_mode/model_id when saved side non-None;
    width/height only when both sides non-None.
    """
    if saved.camera_id != live.camera_id:
        return False, "camera_id"
    if saved.depth_mode is not None and saved.depth_mode != live.depth_mode:
        return False, "depth_mode"
    if saved.model_id is not None and saved.model_id != live.model_id:
        return False, "model_id"
    width_known = saved.width is not None and live.width is not None
    height_known = saved.height is not None and live.height is not None
    if width_known and saved.width != live.width:
        return False, "resolution"
    if height_known and saved.height != live.height:
        return False, "resolution"
    return True, None


def save_params(params: CalibrationParams, path: Path) -> Path:
    """Atomic temp+os.replace. yaml.safe_dump of params.model_dump.

    Strip any depth_map / samples / freeze keys if present. mkdir parents.
    """
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = params.model_dump(mode="python")
    for key in _BANNED_YAML_KEYS:
        data.pop(key, None)
    tmp = dest.with_name(dest.name + ".tmp")
    try:
        tmp.write_text(
            yaml.safe_dump(data, sort_keys=False),
            encoding="utf-8",
        )
        os.replace(tmp, dest)
    except Exception:
        if tmp.exists():
            tmp.unlink()
        raise
    return dest


def load_params(path: Path) -> LoadResult:
    """missing → status=none; safe_load + model_validate → ok; else error."""
    dest = Path(path)
    if not dest.is_file():
        return LoadResult(status="none")
    try:
        data = yaml.safe_load(dest.read_text(encoding="utf-8"))
    except Exception as exc:
        return LoadResult(status="error", reason=str(exc))
    if not isinstance(data, dict):
        return LoadResult(status="error", reason="not a mapping")
    try:
        params = CalibrationParams.model_validate(data)
    except Exception as exc:
        return LoadResult(status="error", reason=str(exc))
    return LoadResult(status="ok", params=params)


def delete_params(path: Path) -> bool:
    """Unlink if exists. True if a file was removed. Missing is False."""
    dest = Path(path)
    if not dest.is_file():
        return False
    dest.unlink()
    return True
