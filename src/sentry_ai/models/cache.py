"""Sentry-owned model weight cache (MODEL-02).

Pure path helpers always work without ultralytics. ``configure_model_cache``
optionally updates Ultralytics ``settings`` when the detect extra is installed.
"""

from __future__ import annotations

import os
from pathlib import Path

# Known YOLO26 weight filenames only (T-03-01). No arbitrary paths in v1.
KNOWN_WEIGHTS: frozenset[str] = frozenset(
    {
        "yolo26n.pt",
        "yolo26s.pt",
        "yolo26m.pt",
    }
)

_TIER_TO_WEIGHT: dict[str, str] = {
    "n": "yolo26n.pt",
    "s": "yolo26s.pt",
    "m": "yolo26m.pt",
}

DEFAULT_WEIGHT = "yolo26n.pt"

__all__ = [
    "KNOWN_WEIGHTS",
    "configure_model_cache",
    "default_cache_root",
    "tier_to_weight",
]


def default_cache_root() -> Path:
    """Return default Sentry model cache root (``~/.cache/sentry-ai``)."""
    return Path.home() / ".cache" / "sentry-ai"


def tier_to_weight(tier: str | None) -> str:
    """Map detector tier (n/s/m) to a known YOLO26 weight filename.

    Unknown or missing tiers default to ``yolo26n.pt`` (edge/CPU default).
    """
    if tier is None:
        return DEFAULT_WEIGHT
    key = str(tier).strip().lower()
    return _TIER_TO_WEIGHT.get(key, DEFAULT_WEIGHT)


def configure_model_cache(cache_root: Path | None = None) -> Path:
    """Point Ultralytics weights_dir + HF_HOME at a Sentry-owned cache.

    Resolution order for cache root:
      1. ``cache_root`` argument
      2. ``SENTRY_MODEL_CACHE`` environment variable
      3. ``~/.cache/sentry-ai``

    Always creates ``weights/`` and ``hf/`` under the root. Setdefaults
    ``YOLO_CONFIG_DIR``, ``HF_HOME``, and ``HUGGINGFACE_HUB_CACHE``.
    When ultralytics is importable, updates ``settings`` with
    ``weights_dir`` and ``sync=False``. When not installed, path setup
    still succeeds so non-detect / non-depth installs work.

    Returns ``weights_dir`` for YOLO callers (backward compatible).
    """
    if cache_root is not None:
        root = Path(cache_root)
    else:
        env = os.environ.get("SENTRY_MODEL_CACHE")
        root = Path(env) if env else default_cache_root()

    weights_dir = root / "weights"
    weights_dir.mkdir(parents=True, exist_ok=True)

    hf_home = root / "hf"
    hf_home.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("HF_HOME", str(hf_home))
    os.environ.setdefault("HUGGINGFACE_HUB_CACHE", str(hf_home / "hub"))

    os.environ.setdefault("YOLO_CONFIG_DIR", str(root / "ultralytics"))

    try:
        from ultralytics import settings  # type: ignore[import-untyped]
    except ImportError:
        # Detect extra not installed — path helpers remain usable.
        return weights_dir

    settings.update({"weights_dir": str(weights_dir), "sync": False})
    return weights_dir
