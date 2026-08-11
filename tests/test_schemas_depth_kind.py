"""FOUND-03: DepthKind enum and relative-depth honesty rules."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentry_ai.schemas import DepthKind, DepthPayload


def test_depth_kind_members_exact() -> None:
    assert {m.value for m in DepthKind} == {
        "relative",
        "metric_estimated",
        "metric_calibrated",
    }
    assert DepthKind.RELATIVE == "relative"
    assert DepthKind.METRIC_ESTIMATED == "metric_estimated"
    assert DepthKind.METRIC_CALIBRATED == "metric_calibrated"


def test_depth_payload_relative_unit_none_ok() -> None:
    d = DepthPayload(kind=DepthKind.RELATIVE, unit=None)
    assert d.kind == DepthKind.RELATIVE
    assert d.unit is None


def test_depth_payload_relative_unit_m_rejected() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.RELATIVE, unit="m")


def test_depth_payload_metric_estimated_unit_m_ok() -> None:
    d = DepthPayload(kind=DepthKind.METRIC_ESTIMATED, unit="m")
    assert d.kind == DepthKind.METRIC_ESTIMATED
    assert d.unit == "m"


def test_depth_payload_metric_calibrated_unit_m_ok() -> None:
    d = DepthPayload(kind=DepthKind.METRIC_CALIBRATED, unit="m")
    assert d.kind == DepthKind.METRIC_CALIBRATED
    assert d.unit == "m"


def test_depth_payload_metric_calibrated_unit_none_rejected() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.METRIC_CALIBRATED, unit=None)


def test_depth_payload_metric_estimated_unit_none_rejected() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.METRIC_ESTIMATED, unit=None)


def test_depth_payload_has_no_depth_m_field() -> None:
    assert "depth_m" not in DepthPayload.model_fields


def test_depth_payload_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(
            kind=DepthKind.RELATIVE,
            unit=None,
            depth_m=1.5,  # type: ignore[call-arg]
        )
