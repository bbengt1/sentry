"""Shared inference device selection with availability checks.

Profile policy may request CUDA (desktop-gpu / jetson), but many maker
machines — especially macOS — have no CUDA. Workers must fall back to
MPS or CPU rather than pass an invalid Ultralytics device string every frame.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

__all__ = ["resolve_device"]


def _cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except ImportError:
        return False


def _mps_available() -> bool:
    try:
        import torch

        mps = getattr(getattr(torch, "backends", None), "mps", None)
        return bool(mps is not None and getattr(mps, "is_available", lambda: False)())
    except ImportError:
        return False


def _auto_device() -> str:
    if _cuda_available():
        return "cuda"
    if _mps_available():
        return "mps"
    return "cpu"


def _is_cuda_request(device: str) -> bool:
    """True for cuda, cuda:N, or bare GPU index strings Ultralytics accepts."""
    r = device.strip().lower()
    if r == "cuda" or r.startswith("cuda:"):
        return True
    # Bare digit index (e.g. "0") is treated as CUDA by Ultralytics.
    if r.isdigit():
        return True
    return False


def resolve_device(device: str | None = None) -> str:
    """Pick a live inference device that is actually available.

    - ``None`` / empty → auto: cuda > mps > cpu
    - ``cpu`` → always ``cpu``
    - CUDA-like requests when CUDA is unavailable → mps if present, else cpu
      (with a one-line warning)
    - ``mps`` when MPS unavailable → auto (or cpu)
    - Other explicit strings pass through unchanged
    """
    if device is None or not str(device).strip():
        return _auto_device()

    requested = str(device).strip()
    r = requested.lower()

    if r == "cpu":
        return "cpu"

    if _is_cuda_request(requested):
        if _cuda_available():
            # Normalize bare index for consistency with profile policy.
            if r.isdigit():
                return f"cuda:{r}"
            return requested
        fallback = "mps" if _mps_available() else "cpu"
        logger.warning(
            "Requested CUDA device %r but CUDA is unavailable "
            "(torch.cuda.is_available() is False); falling back to %r. "
            "Use --profile cpu-fallback or a machine with CUDA for the "
            "requested device policy.",
            requested,
            fallback,
        )
        return fallback

    if r == "mps":
        if _mps_available():
            return "mps"
        fallback = _auto_device()
        if fallback != "mps":
            logger.warning(
                "Requested MPS device but MPS is unavailable; falling back to %r",
                fallback,
            )
        return fallback

    return requested
