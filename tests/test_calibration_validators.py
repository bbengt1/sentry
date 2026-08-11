"""CAL-04 / CAL-05: kind↔unit honesty, free-space units, promote_kind_unit."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from sentry_ai.schemas.enums import DepthKind
from sentry_ai.schemas.perception import DepthPayload, FreeSpacePayload
from sentry_ai.schemas.validators import (
    assert_depth_kind_unit,
    assert_free_space_units,
    promote_kind_unit,
    relative_depth_forbids_unit,
)


# --- assert_depth_kind_unit -------------------------------------------------


def test_assert_depth_kind_unit_relative_none_ok() -> None:
    assert_depth_kind_unit(DepthKind.RELATIVE, None)


def test_assert_depth_kind_unit_relative_m_raises() -> None:
    with pytest.raises(ValueError, match=r"relative|meters|unit"):
        assert_depth_kind_unit(DepthKind.RELATIVE, "m")


def test_assert_depth_kind_unit_metric_estimated_m_ok() -> None:
    assert_depth_kind_unit(DepthKind.METRIC_ESTIMATED, "m")


def test_assert_depth_kind_unit_metric_estimated_none_raises() -> None:
    with pytest.raises(ValueError, match=r"metric_estimated|unit"):
        assert_depth_kind_unit(DepthKind.METRIC_ESTIMATED, None)


def test_assert_depth_kind_unit_metric_calibrated_m_ok() -> None:
    assert_depth_kind_unit(DepthKind.METRIC_CALIBRATED, "m")


def test_assert_depth_kind_unit_metric_calibrated_none_raises() -> None:
    with pytest.raises(ValueError, match=r"CAL-04|meters|metric_calibrated"):
        assert_depth_kind_unit(DepthKind.METRIC_CALIBRATED, None)


# --- DepthPayload mirrors pure assert ---------------------------------------


def test_depth_payload_relative_m_validation_error() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.RELATIVE, unit="m")


def test_depth_payload_metric_estimated_none_validation_error() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.METRIC_ESTIMATED, unit=None)


def test_depth_payload_metric_calibrated_none_validation_error() -> None:
    with pytest.raises(ValidationError):
        DepthPayload(kind=DepthKind.METRIC_CALIBRATED, unit=None)


def test_depth_payload_honest_pairs_ok() -> None:
    assert DepthPayload(kind=DepthKind.RELATIVE, unit=None).unit is None
    assert DepthPayload(kind=DepthKind.METRIC_ESTIMATED, unit="m").unit == "m"
    assert DepthPayload(kind=DepthKind.METRIC_CALIBRATED, unit="m").unit == "m"


# --- assert_free_space_units ------------------------------------------------


def test_assert_free_space_units_relative_ordinal_ok() -> None:
    assert_free_space_units(DepthKind.RELATIVE, "ordinal")


def test_assert_free_space_units_relative_m_raises() -> None:
    with pytest.raises(ValueError, match=r"free-space|metric_calibrated|units"):
        assert_free_space_units(DepthKind.RELATIVE, "m")


def test_assert_free_space_units_metric_estimated_m_raises() -> None:
    with pytest.raises(ValueError, match=r"free-space|metric_calibrated|units"):
        assert_free_space_units(DepthKind.METRIC_ESTIMATED, "m")


def test_assert_free_space_units_metric_estimated_ordinal_ok() -> None:
    assert_free_space_units(DepthKind.METRIC_ESTIMATED, "ordinal")


def test_assert_free_space_units_metric_calibrated_m_ok() -> None:
    assert_free_space_units(DepthKind.METRIC_CALIBRATED, "m")


def test_assert_free_space_units_metric_calibrated_ordinal_ok() -> None:
    assert_free_space_units(DepthKind.METRIC_CALIBRATED, "ordinal")


# --- FreeSpacePayload wire matrix -------------------------------------------


def test_free_space_payload_relative_m_rejected() -> None:
    with pytest.raises(ValidationError):
        FreeSpacePayload(depth_kind=DepthKind.RELATIVE, units="m")


def test_free_space_payload_metric_estimated_m_rejected() -> None:
    with pytest.raises(ValidationError):
        FreeSpacePayload(depth_kind=DepthKind.METRIC_ESTIMATED, units="m")


def test_free_space_payload_metric_estimated_ordinal_ok() -> None:
    p = FreeSpacePayload(depth_kind=DepthKind.METRIC_ESTIMATED, units="ordinal")
    assert p.units == "ordinal"


def test_free_space_payload_metric_calibrated_m_ok() -> None:
    p = FreeSpacePayload(depth_kind=DepthKind.METRIC_CALIBRATED, units="m")
    assert p.units == "m"


def test_free_space_payload_metric_calibrated_ordinal_ok() -> None:
    p = FreeSpacePayload(depth_kind=DepthKind.METRIC_CALIBRATED, units="ordinal")
    assert p.units == "ordinal"


def test_free_space_payload_relative_ordinal_ok() -> None:
    p = FreeSpacePayload(depth_kind=DepthKind.RELATIVE, units="ordinal")
    assert p.units == "ordinal"


# --- promote_kind_unit ------------------------------------------------------


@pytest.mark.parametrize(
    "base_kind,base_unit",
    [
        (DepthKind.RELATIVE, None),
        (DepthKind.METRIC_ESTIMATED, "m"),
        (DepthKind.METRIC_CALIBRATED, "m"),
    ],
)
def test_promote_kind_unit_not_applied_returns_base(
    base_kind: DepthKind, base_unit: str | None
) -> None:
    assert promote_kind_unit(
        base_kind, base_unit, applied=False, valid=True
    ) == (base_kind, base_unit)
    assert promote_kind_unit(
        base_kind, base_unit, applied=False, valid=False
    ) == (base_kind, base_unit)


@pytest.mark.parametrize(
    "base_kind,base_unit",
    [
        (DepthKind.RELATIVE, None),
        (DepthKind.METRIC_ESTIMATED, "m"),
        (DepthKind.METRIC_CALIBRATED, "m"),
    ],
)
def test_promote_kind_unit_applied_invalid_returns_base(
    base_kind: DepthKind, base_unit: str | None
) -> None:
    assert promote_kind_unit(
        base_kind, base_unit, applied=True, valid=False
    ) == (base_kind, base_unit)


@pytest.mark.parametrize(
    "base_kind,base_unit",
    [
        (DepthKind.RELATIVE, None),
        (DepthKind.METRIC_ESTIMATED, "m"),
        (DepthKind.METRIC_CALIBRATED, "m"),
    ],
)
def test_promote_kind_unit_applied_valid_promotes(
    base_kind: DepthKind, base_unit: str | None
) -> None:
    assert promote_kind_unit(
        base_kind, base_unit, applied=True, valid=True
    ) == (DepthKind.METRIC_CALIBRATED, "m")


# --- relative_depth_forbids_unit compatibility ------------------------------


def test_relative_depth_forbids_unit_still_importable() -> None:
    relative_depth_forbids_unit(DepthKind.RELATIVE, None)
    with pytest.raises(ValueError, match=r"relative|meters|unit"):
        relative_depth_forbids_unit(DepthKind.RELATIVE, "m")
