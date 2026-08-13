"""Pure monocular scale/affine fit + reject gates (CAL-01/02).

NumPy only - no FastAPI, no DepthLoop, no CalibrationState mutation.

Phase 14-02 apply formula (document for handoff; not implemented here):
    map_out = scale * map_in + offset
(float32 copy-on-write; not inverse-depth).

Fit-time reject: callers must not stage draft params when ok is False.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import ArrayLike

__all__ = [
    "MAX_SCALE",
    "MIN_SCALE",
    "CalibrationFitResult",
    "fit_affine_lstsq",
    "fit_scale_median",
    "residual_rms_gate",
]

MIN_SCALE = 1e-4
MAX_SCALE = 1e4

_RESIDUAL_FRAC = 0.15
_RESIDUAL_FLOOR_M = 0.05


@dataclass(frozen=True)
class CalibrationFitResult:
    """Outcome of a pure scale/affine fit (never mutates CalibrationState)."""

    ok: bool
    scale: float = 1.0
    offset: float = 0.0
    residual_rms: float | None = None
    sample_count: int = 0
    method: str = "known_distance"
    reason: str | None = None


def residual_rms_gate(rms: float, known_meters: ArrayLike) -> bool:
    """Return True when residual RMS is within the product gate.

    Reject when ``rms > max(0.15 * median(D), 0.05)``.
    """
    d = np.asarray(known_meters, dtype=np.float64).ravel()
    if d.size == 0 or not math.isfinite(float(rms)):
        return False
    threshold = max(_RESIDUAL_FRAC * float(np.median(d)), _RESIDUAL_FLOOR_M)
    return float(rms) <= threshold


def _is_absurd_scale(scale: float) -> bool:
    """True when scale is non-finite or outside open interval (MIN_SCALE, MAX_SCALE)."""
    if not math.isfinite(scale):
        return True
    return scale <= MIN_SCALE or scale >= MAX_SCALE


def _reject(
    *,
    reason: str,
    method: str,
    sample_count: int = 0,
    scale: float = 1.0,
    offset: float = 0.0,
    residual_rms: float | None = None,
) -> CalibrationFitResult:
    return CalibrationFitResult(
        ok=False,
        scale=scale,
        offset=offset,
        residual_rms=residual_rms,
        sample_count=sample_count,
        method=method,
        reason=reason,
    )


def _valid_pairs(
    observed_raw: ArrayLike,
    known_meters: ArrayLike,
) -> tuple[np.ndarray, np.ndarray]:
    """Return finite, strictly positive (observed, known) pairs.

    Raises
    ------
    ValueError
        When array lengths differ after ravel.
    """
    o = np.asarray(observed_raw, dtype=np.float64).ravel()
    k = np.asarray(known_meters, dtype=np.float64).ravel()
    if o.shape != k.shape:
        raise ValueError(
            f"observed_raw and known_meters length mismatch: {o.size} vs {k.size}"
        )
    mask = np.isfinite(o) & np.isfinite(k) & (o > 0.0) & (k > 0.0)
    return o[mask], k[mask]


def _residual_rms(predicted: np.ndarray, known: np.ndarray) -> float:
    err = predicted - known
    return float(np.sqrt(np.mean(err * err)))


def _finalize_fit(
    *,
    scale: float,
    offset: float,
    observed: np.ndarray,
    known: np.ndarray,
    method: str,
) -> CalibrationFitResult:
    """Apply absurd-scale + residual gates; return accept or reject result."""
    n = int(observed.size)
    predicted = scale * observed + offset
    rms = _residual_rms(predicted, known)

    if _is_absurd_scale(scale):
        return _reject(
            reason="absurd_scale",
            method=method,
            sample_count=n,
            scale=float(scale),
            offset=float(offset),
            residual_rms=rms,
        )
    if not residual_rms_gate(rms, known):
        return _reject(
            reason="residual_rms_too_high",
            method=method,
            sample_count=n,
            scale=float(scale),
            offset=float(offset),
            residual_rms=rms,
        )
    return CalibrationFitResult(
        ok=True,
        scale=float(scale),
        offset=float(offset),
        residual_rms=rms,
        sample_count=n,
        method=method,
        reason=None,
    )


def fit_scale_median(
    observed_raw: ArrayLike,
    known_meters: ArrayLike,
    *,
    method: str = "known_distance",
) -> CalibrationFitResult:
    """Scale-only median fit: scale = median(D_i / d_i), offset = 0.

    Non-positive / non-finite pairs are excluded. Fit-time gates reject absurd
    scale and high residual_rms before any draft staging.
    """
    observed, known = _valid_pairs(observed_raw, known_meters)
    if observed.size == 0:
        return _reject(reason="insufficient_valid_samples", method=method)

    ratios = known / observed
    scale = float(np.median(ratios))
    return _finalize_fit(
        scale=scale,
        offset=0.0,
        observed=observed,
        known=known,
        method=method,
    )


def fit_affine_lstsq(
    observed_raw: ArrayLike,
    known_meters: ArrayLike,
    *,
    method: str = "known_distance",
) -> CalibrationFitResult:
    """Affine least-squares fit: known ~= scale * observed + offset (N >= 2).

    Uses ``numpy.linalg.lstsq`` on columns ``[observed, 1]``. Same absurd-scale
    and residual_rms gates as the median path.
    """
    observed, known = _valid_pairs(observed_raw, known_meters)
    if observed.size == 0:
        return _reject(reason="insufficient_valid_samples", method=method)
    if observed.size < 2:
        return _reject(
            reason="affine_requires_n_ge_2",
            method=method,
            sample_count=int(observed.size),
        )

    design = np.column_stack([observed, np.ones_like(observed)])
    sol, _residuals, _rank, _singular = np.linalg.lstsq(design, known, rcond=None)
    scale = float(sol[0])
    offset = float(sol[1])
    return _finalize_fit(
        scale=scale,
        offset=offset,
        observed=observed,
        known=known,
        method=method,
    )
