"""ONL-03 / ONL-04: throttled draft window and draft-only fit/reject."""

from __future__ import annotations

import math

import numpy as np
import pytest

from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.control.online_sampler import (
    ONLINE_MIN_INTERVAL_S,
    ONLINE_WINDOW_N,
    OnlineSampler,
)
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
)
from sentry_ai.schemas.enums import DepthKind


def _params(**overrides: object) -> CalibrationParams:
    data: dict[str, object] = {
        "scale": 4.0,
        "offset": 0.0,
        "sample_count": 2,
        "fingerprint": CalibrationFingerprint(camera_id="cam0"),
    }
    data.update(overrides)
    return CalibrationParams(**data)  # type: ignore[arg-type]


def _map(value: float, *, h: int = 4, w: int = 4) -> np.ndarray:
    return np.full((h, w), value, dtype=np.float32)


def _ready(
    *,
    online: bool = True,
    scale: float = 4.0,
    samples: list[CalibrationSample] | None = None,
) -> CalibrationState:
    state = CalibrationState()
    draft = samples or [
        CalibrationSample(point_uv=(1.0, 1.0), known_meters=2.0, observed_raw=1.0)
    ]
    for sample in draft:
        state.add_draft_sample(sample)
    state.set_draft_params(_params(scale=scale, offset=0.0))
    state.apply()
    if online:
        state.set_online(True)
    return state


def _fill(
    sampler: OnlineSampler,
    depth: np.ndarray,
    *,
    count: int = 8,
    frame_start: int = 1,
    now_start: float = 0.0,
) -> object:
    last = None
    for index in range(count):
        last = sampler.consider(
            depth,
            frame_id=frame_start + index,
            now_s=now_start + float(index),
        )
    return last


def test_sampler_defaults() -> None:
    sampler = OnlineSampler(CalibrationState())
    assert sampler.window_n == 8
    assert sampler.min_interval_s == 1.0
    assert ONLINE_WINDOW_N == 8
    assert ONLINE_MIN_INTERVAL_S == 1.0


def test_consider_while_online_off_writes_nothing() -> None:
    fresh = CalibrationState()
    result = OnlineSampler(fresh).consider(_map(1.0), frame_id=1, now_s=0.0)
    assert result.accepted is False
    assert result.reason == "online_off"
    assert result.fit_ok is None
    snap = fresh.snapshot()
    assert snap.draft_sample_count == 0
    assert fresh.is_applied() is False
    kind, unit = fresh.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.RELATIVE
    assert unit is None

    applied = _ready(online=False, scale=4.0)
    before = applied.snapshot().scale
    off = OnlineSampler(applied).consider(_map(2.0), frame_id=1, now_s=0.0)
    assert off.reason == "online_off"
    assert off.accepted is False
    assert applied.get_draft_samples() == []
    assert applied.snapshot().scale == before
    assert applied.get_consent_anchors()


def test_not_applied_when_online_forced_without_weakening_set_online() -> None:
    """Defensive branch. set_online(True) still refuses an unapplied state."""
    state = CalibrationState()
    with pytest.raises(ValueError, match="online_requires_applied"):
        state.set_online(True)
    state._online_enabled = True  # noqa: SLF001 — not reachable via set_online
    result = OnlineSampler(state).consider(_map(1.0), frame_id=1, now_s=0.0)
    assert result.accepted is False
    assert result.reason == "not_applied"
    assert state.snapshot().draft_sample_count == 0
    assert state.is_applied() is False


def test_no_anchors_after_apply_params() -> None:
    state = CalibrationState()
    state.apply_params(_params())
    state.set_online(True)
    assert state.get_consent_anchors() == ()
    result = OnlineSampler(state).consider(_map(1.0), frame_id=1, now_s=0.0)
    assert result.accepted is False
    assert result.reason == "no_anchors"
    assert state.get_draft_samples() == []
    assert state.snapshot().has_draft_params is False


def test_missing_frame_id_writes_nothing() -> None:
    state = _ready()
    result = OnlineSampler(state).consider(_map(1.0), frame_id=None, now_s=0.0)
    assert result.accepted is False
    assert result.reason == "missing_frame_id"
    assert state.get_draft_samples() == []


def test_same_timestamp_accepts_once() -> None:
    state = _ready()
    sampler = OnlineSampler(state)
    reasons = []
    for frame_id in range(1, 31):
        result = sampler.consider(_map(2.0), frame_id=frame_id, now_s=0.0)
        reasons.append(result.reason)
    assert reasons[0] == "window_short"
    assert reasons[1:] == ["throttled"] * 29
    assert len(state.get_draft_samples()) == 1
    assert state.snapshot().has_draft_params is False


def test_frame_id_must_strictly_increase() -> None:
    state = _ready()
    sampler = OnlineSampler(state)
    first = sampler.consider(_map(2.0), frame_id=5, now_s=0.0)
    assert first.accepted is True
    stalled = sampler.consider(_map(2.0), frame_id=5, now_s=10.0)
    assert stalled.accepted is False
    assert stalled.reason == "frame_not_advanced"
    older = sampler.consider(_map(2.0), frame_id=4, now_s=11.0)
    assert older.reason == "frame_not_advanced"
    assert len(state.get_draft_samples()) == 1


def test_partial_window_is_draft_samples_only() -> None:
    state = _ready(scale=4.0)
    sampler = OnlineSampler(state)
    for index, now_s in enumerate((0.0, 1.0, 2.0)):
        result = sampler.consider(_map(2.0), frame_id=index + 1, now_s=now_s)
        assert result.accepted is True
        assert result.reason == "window_short"
        assert result.fit_ok is None
        assert len(state.get_draft_samples()) == index + 1
    snap = state.snapshot()
    assert snap.has_draft_params is False
    assert snap.scale == 4.0
    assert snap.online_status == "online_draft"
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"
    samples = state.get_draft_samples()
    assert [sample.frame_id for sample in samples] == [1, 2, 3]
    assert all(sample.note == "online" for sample in samples)
    assert all(sample.observed_raw == 2.0 for sample in samples)


def test_eighth_accept_stays_window_short_without_fit() -> None:
    state = _ready(scale=4.0)
    sampler = OnlineSampler(state)
    last = None
    for index in range(8):
        last = sampler.consider(
            _map(2.0), frame_id=index + 1, now_s=float(index)
        )
    assert last is not None
    assert last.accepted is True
    assert last.reason == "window_short"
    assert last.fit_ok is None
    snap = state.snapshot()
    assert snap.has_draft_params is False
    assert snap.scale == 4.0
    assert snap.online_status == "online_draft"
    assert len(state.get_draft_samples()) == 8


def test_map_space_applied_stores_pre_apply_raw() -> None:
    state = _ready(scale=4.0)
    sampler = OnlineSampler(state)
    result = sampler.consider(_map(8.0), frame_id=1, now_s=0.0, map_space="applied")
    assert result.reason == "window_short"
    samples = state.get_draft_samples()
    assert len(samples) == 1
    assert samples[0].observed_raw == 2.0


def test_map_space_raw_does_not_invert() -> None:
    state = _ready(scale=4.0)
    sampler = OnlineSampler(state)
    result = sampler.consider(_map(8.0), frame_id=1, now_s=0.0, map_space="raw")
    assert result.reason == "window_short"
    samples = state.get_draft_samples()
    assert len(samples) == 1
    assert samples[0].observed_raw == 8.0


def test_bbox_anchor_uses_positive_finite_median() -> None:
    state = _ready(
        samples=[
            CalibrationSample(
                bbox_xyxy=(0.0, 0.0, 1.0, 1.0),
                known_meters=3.0,
                observed_raw=1.0,
            )
        ]
    )
    depth = _map(3.0)
    depth[0, 0] = np.nan
    depth[0, 1] = -1.0
    result = OnlineSampler(state).consider(depth, frame_id=1, now_s=0.0)
    assert result.reason == "window_short"
    samples = state.get_draft_samples()
    assert len(samples) == 1
    assert samples[0].bbox_xyxy == (0.0, 0.0, 1.0, 1.0)
    assert samples[0].point_uv is None
    assert samples[0].observed_raw == 3.0
    assert samples[0].note == "online"


def test_empty_roi_is_not_counted() -> None:
    state = _ready(
        samples=[
            CalibrationSample(point_uv=(0.0, 0.0), known_meters=2.0, observed_raw=1.0),
            CalibrationSample(point_uv=(1.0, 0.0), known_meters=4.0, observed_raw=1.0),
        ]
    )
    sampler = OnlineSampler(state)
    good = _map(2.0)
    first = sampler.consider(good, frame_id=1, now_s=0.0)
    assert first.accepted is True
    assert len(state.get_draft_samples()) == 2

    bad = _map(2.0)
    bad[0, 1] = np.nan
    missed = sampler.consider(bad, frame_id=2, now_s=1.0)
    assert missed.accepted is False
    assert missed.reason == "empty_roi"
    assert len(state.get_draft_samples()) == 2

    retry = sampler.consider(good, frame_id=2, now_s=2.0)
    assert retry.accepted is True
    assert len(state.get_draft_samples()) == 4


def test_nonfinite_anchor_pixel_is_empty_roi() -> None:
    state = _ready()
    depth = _map(2.0)
    depth[1, 1] = math.nan
    result = OnlineSampler(state).consider(depth, frame_id=1, now_s=0.0)
    assert result.accepted is False
    assert result.reason == "empty_roi"
    assert state.get_draft_samples() == []


def test_clear_draft_drops_window_not_anchors() -> None:
    state = _ready(scale=4.0)
    sampler = OnlineSampler(state)
    sampler.consider(_map(2.0), frame_id=1, now_s=0.0)
    sampler.consider(_map(2.0), frame_id=2, now_s=1.0)
    anchors = state.get_consent_anchors()
    snap = state.clear_draft()
    assert snap.draft_sample_count == 0
    assert state.get_draft_samples() == []
    assert state.get_consent_anchors() == anchors
    assert state.is_applied() is True
    assert state.is_online() is True
    assert state.snapshot().scale == 4.0
    again = sampler.consider(_map(2.0), frame_id=3, now_s=2.0)
    assert again.accepted is True
    assert len(state.get_draft_samples()) == 1
    assert state.get_draft_samples()[0].frame_id == 3


def test_disable_online_keeps_applied_anchors_and_draft() -> None:
    state = _ready(scale=4.0)
    sampler = OnlineSampler(state)
    sampler.consider(_map(2.0), frame_id=1, now_s=0.0)
    sampler.consider(_map(2.0), frame_id=2, now_s=1.0)
    anchors = state.get_consent_anchors()
    samples = list(state.get_draft_samples())
    snap = state.set_online(False)
    assert snap.online is False
    assert snap.online_status == "online_off"
    assert state.is_applied() is True
    assert state.snapshot().scale == 4.0
    assert state.get_consent_anchors() == anchors
    assert state.get_draft_samples() == samples
    nxt = sampler.consider(_map(2.0), frame_id=3, now_s=2.0)
    assert nxt.accepted is False
    assert nxt.reason == "online_off"
    assert state.get_draft_samples() == samples
    assert state.snapshot().scale == 4.0


def test_consider_does_not_call_apply_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _ready()
    sampler = OnlineSampler(state)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("sampler must not commit or map-apply")

    monkeypatch.setattr(state, "apply", _boom)
    monkeypatch.setattr(state, "apply_params", _boom)
    monkeypatch.setattr(state, "apply_map", _boom)
    result = sampler.consider(_map(2.0), frame_id=1, now_s=0.0)
    assert result.accepted is True
    assert result.reason == "window_short"
    assert state.snapshot().scale == 4.0
    assert state.snapshot().has_draft_params is False


def test_consider_does_not_touch_yaml(tmp_path) -> None:
    path = tmp_path / "calibration.yaml"
    payload = b"scale: 1\n"
    path.write_bytes(payload)
    state = _ready()
    OnlineSampler(state).consider(_map(2.0), frame_id=1, now_s=0.0)
    assert path.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [path]


def test_draft_staged_consistent_window() -> None:
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(point_uv=(1.0, 1.0), known_meters=4.0, observed_raw=1.0)
        ],
    )
    sampler = OnlineSampler(state)
    seventh = _fill(sampler, _map(2.0), count=7)
    assert seventh is not None
    assert seventh.reason == "window_short"
    assert seventh.fit_ok is None
    assert state.snapshot().has_draft_params is False
    last = sampler.consider(_map(2.0), frame_id=8, now_s=7.0)
    assert last is not None
    assert last.accepted is True
    assert last.reason == "draft_staged"
    assert last.fit_ok is True
    snap = state.snapshot()
    assert snap.has_draft_params is True
    assert snap.scale == 2.0
    assert snap.online_status == "online_draft"
    assert snap.online_status not in {"auto_committed", "rejected"}
    assert state.is_online() is True
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 2.0
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED
    assert unit == "m"
    kind_again, unit_again = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind_again == kind
    assert unit_again == unit
    draft = state._draft_params  # noqa: SLF001
    assert draft is not None
    assert draft.scale == pytest.approx(2.0)
    assert draft.offset == pytest.approx(0.0)
    assert draft.method == "known_distance"
    assert draft.fingerprint.camera_id == applied.fingerprint.camera_id
    assert len(state.get_draft_samples()) == 8


def test_fit_rejected_residual_leaves_applied_scale() -> None:
    state = _ready(
        scale=3.0,
        samples=[
            CalibrationSample(point_uv=(0.0, 0.0), known_meters=1.0, observed_raw=1.0),
            CalibrationSample(point_uv=(1.0, 0.0), known_meters=10.0, observed_raw=1.0),
        ],
    )
    last = _fill(OnlineSampler(state), _map(2.0))
    assert last is not None
    assert last.accepted is True
    assert last.reason == "fit_rejected"
    assert last.fit_ok is False
    snap = state.snapshot()
    assert snap.has_draft_params is False
    assert snap.draft_sample_count > 0
    assert snap.scale == 3.0
    assert snap.online_status == "online_draft"
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 3.0
    assert state.is_online() is True
    assert state.get_consent_anchors()


def test_fit_rejected_absurd_scale() -> None:
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(
                point_uv=(1.0, 1.0), known_meters=1.0e4, observed_raw=1.0
            )
        ],
    )
    last = _fill(OnlineSampler(state), _map(1.0))
    assert last is not None
    assert last.reason == "fit_rejected"
    assert last.fit_ok is False
    assert state.snapshot().has_draft_params is False
    assert state.snapshot().scale == 2.0
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 2.0
    assert state.snapshot().online_status == "online_draft"
    assert len(state.get_draft_samples()) == 8


def test_in_range_large_scale_does_not_replace_applied() -> None:
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(
                point_uv=(1.0, 1.0), known_meters=1000.0, observed_raw=1.0
            )
        ],
    )
    last = _fill(OnlineSampler(state), _map(1.0))
    assert last is not None
    assert last.reason == "draft_staged"
    assert last.fit_ok is True
    snap = state.snapshot()
    assert snap.has_draft_params is True
    assert snap.scale == 2.0
    applied = state.get_applied_params()
    assert applied is not None
    assert applied.scale == 2.0
    draft = state._draft_params  # noqa: SLF001
    assert draft is not None
    assert draft.scale == pytest.approx(1000.0)
    assert snap.online_status == "online_draft"


def test_fit_rejected_clears_stale_draft_staged() -> None:
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(point_uv=(1.0, 1.0), known_meters=4.0, observed_raw=1.0)
        ],
    )
    sampler = OnlineSampler(state)
    staged = _fill(sampler, _map(2.0))
    assert staged is not None
    assert staged.reason == "draft_staged"
    assert state.snapshot().has_draft_params is True
    last = None
    for index in range(8):
        value = 1.0 if index % 2 == 0 else 50.0
        last = sampler.consider(
            _map(value),
            frame_id=9 + index,
            now_s=8.0 + float(index),
        )
    assert last is not None
    assert last.reason == "fit_rejected"
    assert last.fit_ok is False
    assert state.snapshot().has_draft_params is False
    assert state.snapshot().draft_sample_count == 8
    assert state.snapshot().scale == 2.0
    assert state.get_applied_params() is not None
    assert state.get_applied_params().scale == 2.0  # type: ignore[union-attr]
    assert state.snapshot().online_status == "online_draft"
    assert state.is_online() is True


def test_slide_ninth_frame_stays_draft_staged() -> None:
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(point_uv=(1.0, 1.0), known_meters=4.0, observed_raw=1.0)
        ],
    )
    sampler = OnlineSampler(state)
    _fill(sampler, _map(2.0))
    ninth = sampler.consider(_map(2.0), frame_id=9, now_s=8.0)
    assert ninth.accepted is True
    assert ninth.reason == "draft_staged"
    assert ninth.fit_ok is True
    assert state.snapshot().scale == 2.0
    assert state.get_applied_params() is not None
    assert state.get_applied_params().scale == 2.0  # type: ignore[union-attr]
    assert len(state.get_draft_samples()) == 8
    assert state.get_draft_samples()[0].frame_id == 2
    assert state.get_draft_samples()[-1].frame_id == 9
    assert state.snapshot().online_status == "online_draft"


def test_draft_staged_does_not_call_apply_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(point_uv=(1.0, 1.0), known_meters=4.0, observed_raw=1.0)
        ],
    )
    sampler = OnlineSampler(state)

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("sampler must not commit or map-apply")

    monkeypatch.setattr(state, "apply", _boom)
    monkeypatch.setattr(state, "apply_params", _boom)
    monkeypatch.setattr(state, "apply_map", _boom)
    last = _fill(sampler, _map(2.0))
    assert last is not None
    assert last.reason == "draft_staged"
    assert state.snapshot().scale == 2.0
    assert state.is_applied() is True


def test_draft_staged_yaml_unchanged(tmp_path) -> None:
    path = tmp_path / "calibration.yaml"
    payload = b"scale: 1\n"
    path.write_bytes(payload)
    state = _ready(
        scale=2.0,
        samples=[
            CalibrationSample(point_uv=(1.0, 1.0), known_meters=4.0, observed_raw=1.0)
        ],
    )
    last = _fill(OnlineSampler(state), _map(2.0))
    assert last is not None
    assert last.reason == "draft_staged"
    assert path.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [path]


def test_bad_applied_scale_does_not_sample() -> None:
    state = _ready(scale=4.0)
    params = state.get_applied_params()
    assert params is not None
    params.scale = math.nan
    result = OnlineSampler(state).consider(
        _map(8.0), frame_id=1, now_s=0.0, map_space="applied"
    )
    assert result.accepted is False
    assert result.reason == "bad_applied_scale"
    assert state.get_draft_samples() == []
