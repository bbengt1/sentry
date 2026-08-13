"""CAL-01 / CAL-02: pure scale/affine fit + fit-time reject gates."""

from __future__ import annotations

import inspect
import math

import numpy as np
import pytest

import sentry_ai.spatial.calibration as calib_mod
from sentry_ai.spatial.calibration import (
    MAX_SCALE,
    MIN_SCALE,
    CalibrationFitResult,
    fit_affine_lstsq,
    fit_scale_median,
    known_height_to_distance_m,
    residual_rms_gate,
)


def test_fit_scale_median_recovers_known_scale() -> None:
    rng = np.random.default_rng(0)
    true_scale = 2.5
    observed = rng.uniform(0.5, 3.0, size=5)
    known = true_scale * observed
    result = fit_scale_median(observed, known)
    assert result.ok is True
    assert result.reason is None
    assert result.scale == pytest.approx(true_scale, rel=1e-6)
    assert result.offset == 0.0
    assert result.sample_count == 5
    assert result.residual_rms is not None
    assert result.residual_rms == pytest.approx(0.0, abs=1e-9)
    assert result.method == "known_distance"


def test_fit_scale_median_method_passthrough() -> None:
    observed = np.array([1.0, 2.0, 3.0])
    known = 4.0 * observed
    result = fit_scale_median(observed, known, method="known_height")
    assert result.ok
    assert result.method == "known_height"


def test_fit_scale_median_ignores_non_positive_and_non_finite() -> None:
    observed = np.array([1.0, -2.0, 0.0, np.nan, np.inf, 2.0])
    known = np.array([2.0, 4.0, 1.0, 3.0, 5.0, 4.0])
    result = fit_scale_median(observed, known)
    assert result.ok is True
    assert result.sample_count == 2  # (1,2) and (2,4)
    assert result.scale == pytest.approx(2.0, rel=1e-6)


def test_fit_scale_median_negative_observed_never_contributes() -> None:
    # Only negative / zero observations -> no valid pairs
    observed = np.array([-1.0, -2.0, 0.0])
    known = np.array([2.0, 4.0, 1.0])
    result = fit_scale_median(observed, known)
    assert result.ok is False
    assert result.reason == "insufficient_valid_samples"


def test_fit_scale_median_empty_rejects() -> None:
    result = fit_scale_median([], [])
    assert result.ok is False
    assert result.reason == "insufficient_valid_samples"
    assert result.sample_count == 0


def test_fit_scale_median_all_invalid_rejects() -> None:
    observed = np.array([np.nan, -1.0, 0.0])
    known = np.array([1.0, 2.0, 3.0])
    result = fit_scale_median(observed, known)
    assert result.ok is False
    assert result.reason == "insufficient_valid_samples"


def test_fit_scale_median_length_mismatch_raises() -> None:
    with pytest.raises(ValueError, match="length mismatch"):
        fit_scale_median([1.0, 2.0], [1.0])


def test_fit_scale_median_absurd_scale_too_small() -> None:
    # known << observed -> tiny scale
    observed = np.array([1.0, 2.0, 3.0])
    known = np.array([1e-8, 2e-8, 3e-8])
    result = fit_scale_median(observed, known)
    assert result.ok is False
    assert result.reason == "absurd_scale"
    assert result.scale <= MIN_SCALE


def test_fit_scale_median_absurd_scale_too_large() -> None:
    observed = np.array([1.0, 2.0, 3.0])
    known = np.array([1e5, 2e5, 3e5])
    result = fit_scale_median(observed, known)
    assert result.ok is False
    assert result.reason == "absurd_scale"
    assert result.scale >= MAX_SCALE


def test_fit_scale_median_residual_rms_too_high() -> None:
    # Median ratio is stable, but residuals are large vs median(D).
    # ratios: 1/1=1, 10/1=10, 1/1=1 -> median=1; predictions 1,1,1 vs known 1,10,1
    observed = np.array([1.0, 1.0, 1.0])
    known = np.array([1.0, 10.0, 1.0])
    result = fit_scale_median(observed, known)
    assert result.ok is False
    assert result.reason == "residual_rms_too_high"
    assert result.scale == pytest.approx(1.0, rel=1e-9)
    assert result.residual_rms is not None
    assert result.residual_rms > max(0.15 * float(np.median(known)), 0.05)


def test_residual_rms_gate_floor_and_frac() -> None:
    # Small median(D): floor 0.05 dominates
    assert residual_rms_gate(0.04, [0.1, 0.1, 0.1]) is True
    assert residual_rms_gate(0.06, [0.1, 0.1, 0.1]) is False
    # Large median(D): 0.15*median dominates (median=10 -> 1.5)
    assert residual_rms_gate(1.4, [10.0, 10.0, 10.0]) is True
    assert residual_rms_gate(1.6, [10.0, 10.0, 10.0]) is False


def test_fit_affine_lstsq_requires_n_ge_2() -> None:
    result = fit_affine_lstsq([2.0], [5.0])
    assert result.ok is False
    assert result.reason == "affine_requires_n_ge_2"
    assert result.sample_count == 1


def test_fit_affine_lstsq_recovers_scale_and_offset() -> None:
    rng = np.random.default_rng(1)
    true_scale = 1.75
    true_offset = 0.4
    observed = rng.uniform(0.5, 4.0, size=8)
    known = true_scale * observed + true_offset
    # Tiny noise still within residual gate
    known = known + rng.normal(0.0, 1e-4, size=known.shape)
    result = fit_affine_lstsq(observed, known)
    assert result.ok is True
    assert result.reason is None
    assert result.scale == pytest.approx(true_scale, rel=1e-3, abs=1e-3)
    assert result.offset == pytest.approx(true_offset, rel=1e-3, abs=1e-3)
    assert result.sample_count == 8
    assert result.residual_rms is not None
    assert result.residual_rms < 0.05


def test_fit_affine_lstsq_empty_rejects() -> None:
    result = fit_affine_lstsq([], [])
    assert result.ok is False
    assert result.reason == "insufficient_valid_samples"


def test_fit_affine_lstsq_absurd_scale() -> None:
    observed = np.array([1.0, 2.0])
    known = np.array([1e6, 2e6])
    result = fit_affine_lstsq(observed, known)
    assert result.ok is False
    assert result.reason == "absurd_scale"


def test_fit_affine_lstsq_filters_invalid_then_n1() -> None:
    # Two inputs but only one valid after filter -> affine_requires_n_ge_2
    observed = np.array([1.0, -1.0])
    known = np.array([2.0, 3.0])
    result = fit_affine_lstsq(observed, known)
    assert result.ok is False
    assert result.reason == "affine_requires_n_ge_2"
    assert result.sample_count == 1


def test_rejected_fit_not_draft_ready() -> None:
    result = fit_scale_median([], [])
    assert isinstance(result, CalibrationFitResult)
    assert result.ok is False
    assert result.reason is not None


def test_calibration_module_has_no_heavy_imports() -> None:
    source = inspect.getsource(calib_mod)
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped.startswith(("import ", "from ")):
            continue
        lower = stripped.lower()
        assert "fastapi" not in lower
        assert "torch" not in lower
        assert "scipy" not in lower
        assert "calibration_state" not in lower
        assert "sentry_ai.control" not in lower


def test_min_max_scale_constants() -> None:
    assert MIN_SCALE == 1e-4
    assert MAX_SCALE == 1e4
    assert math.isfinite(MIN_SCALE) and math.isfinite(MAX_SCALE)



def test_known_height_to_distance_m_positive() -> None:
    d = known_height_to_distance_m(
        known_height_m=1.7,
        bbox_xyxy=(10.0, 20.0, 50.0, 220.0),  # height_px = 200
        image_width_px=640,
        hfov_deg=70.0,
    )
    assert d > 0.0
    fy = (640.0 / 2.0) / math.tan(math.radians(70.0) / 2.0)
    assert d == pytest.approx((1.7 * fy) / 200.0)


def test_known_height_to_distance_m_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        known_height_to_distance_m(
            known_height_m=0.0,
            bbox_xyxy=(0.0, 0.0, 10.0, 10.0),
            image_width_px=640,
        )
    with pytest.raises(ValueError):
        known_height_to_distance_m(
            known_height_m=1.0,
            bbox_xyxy=(0.0, 10.0, 10.0, 10.0),  # zero height
            image_width_px=640,
        )
    with pytest.raises(ValueError):
        known_height_to_distance_m(
            known_height_m=1.0,
            bbox_xyxy=(0.0, 0.0, 10.0, 10.0),
            image_width_px=0,
        )
