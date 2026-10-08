"""ONL-05 / ONL-09: gated online auto-commit, strict horizon, deadband (21-01)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import pytest

import sentry_ai.control.online_sampler as online_sampler_mod
from sentry_ai.control.calibration_state import CalibrationState
from sentry_ai.control.online_sampler import (
    ONLINE_COMMIT_DEADBAND,
    OnlineSampler,
    horizon_median_m,
    within_deadband,
)
from sentry_ai.schemas.calibration import (
    CalibrationFingerprint,
    CalibrationParams,
    CalibrationSample,
)
from sentry_ai.schemas.enums import DepthKind
from sentry_ai.spatial.calibration import CalibrationFitResult


def _fp(camera_id: str = "cam0", **extra: Any) -> CalibrationFingerprint:
    return CalibrationFingerprint(camera_id=camera_id, **extra)


LIVE = _fp(width=4, height=4)


def _map(value: float, *, h: int = 4, w: int = 4) -> np.ndarray:
    return np.full((h, w), value, dtype=np.float32)


def _ready(
    *,
    scale: float,
    known: float | list[float] = 2.0,
    fingerprint: CalibrationFingerprint | None = None,
) -> CalibrationState:
    """Applied (wizard apply) + online, with one anchor per known distance."""
    state = CalibrationState()
    knowns = known if isinstance(known, list) else [known]
    for index, meters in enumerate(knowns):
        state.add_draft_sample(
            CalibrationSample(
                point_uv=(float(index), 1.0), known_meters=meters, observed_raw=1.0
            )
        )
    state.set_draft_params(
        CalibrationParams(
            scale=scale,
            offset=0.0,
            sample_count=len(knowns),
            fingerprint=fingerprint or _fp(),
        )
    )
    state.apply()
    state.set_online(True)
    return state


def _fill(
    sampler: OnlineSampler,
    depth: np.ndarray,
    *,
    count: int = 8,
    frame_start: int = 1,
    now_start: float = 0.0,
    live: CalibrationFingerprint | None = LIVE,
) -> Any:
    last = None
    for index in range(count):
        last = sampler.consider(
            depth,
            frame_id=frame_start + index,
            now_s=now_start + float(index),
            live_fingerprint=live,
        )
    return last


class _Spy:
    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> None:
        self.calls += 1


# --- success ---------------------------------------------------------------


def test_success_commits_via_apply_params_and_resets_once() -> None:
    state = _ready(scale=1.5, known=2.0)
    before = state.get_applied_params()
    spy = _Spy()
    sampler = OnlineSampler(state, auto_commit=True, on_auto_commit=spy)
    seventh = _fill(sampler, _map(1.0), count=7)
    assert seventh.reason == "window_short"
    assert spy.calls == 0
    last = sampler.consider(_map(1.0), frame_id=8, now_s=7.0, live_fingerprint=LIVE)
    assert last.accepted is True
    assert last.reason == "committed"
    assert last.fit_ok is True
    applied = state.get_applied_params()
    assert applied is not None and applied is not before
    assert applied.scale == pytest.approx(2.0)
    assert applied.offset == 0.0
    assert applied.fingerprint.camera_id == "cam0"
    snap = state.snapshot()
    assert snap.online_status == "auto_committed"
    assert snap.has_draft_params is False
    assert snap.scale == pytest.approx(2.0)
    assert state.get_draft_samples() == []
    assert state.is_online() is True
    assert state.get_consent_anchors()
    assert spy.calls == 1
    kind, unit = state.promote_kind_unit(DepthKind.RELATIVE, None)
    assert kind == DepthKind.METRIC_CALIBRATED and unit == "m"
    # Window was cleared: the next accept starts a fresh window.
    nxt = sampler.consider(_map(1.0), frame_id=9, now_s=8.0, live_fingerprint=LIVE)
    assert nxt.reason == "window_short"
    assert spy.calls == 1


def test_commit_from_prior_rejected_sets_auto_committed() -> None:
    state = _ready(scale=1.5, known=2.0)
    state.set_online_status("rejected")
    last = _fill(OnlineSampler(state, auto_commit=True), _map(1.0))
    assert last.reason == "committed"
    assert state.snapshot().online_status == "auto_committed"


def test_callback_error_does_not_undo_commit() -> None:
    state = _ready(scale=1.5, known=2.0)

    def _boom() -> None:
        raise RuntimeError("reset failed")

    sampler = OnlineSampler(state, auto_commit=True, on_auto_commit=_boom)
    last = _fill(sampler, _map(1.0))
    assert last.reason == "committed"
    applied = state.get_applied_params()
    assert applied is not None and applied.scale == pytest.approx(2.0)
    assert state.snapshot().online_status == "auto_committed"


# --- refusals --------------------------------------------------------------


def _assert_refused(
    state: CalibrationState, before: CalibrationParams | None, spy: _Spy
) -> None:
    assert state.get_applied_params() is before
    snap = state.snapshot()
    assert snap.online_status == "rejected"
    assert snap.has_draft_params is False
    assert state.is_online() is True
    assert spy.calls == 0


def test_fit_rejected_sets_rejected_and_keeps_applied() -> None:
    state = _ready(scale=3.0, known=[1.0, 10.0])
    before = state.get_applied_params()
    spy = _Spy()
    last = _fill(OnlineSampler(state, auto_commit=True, on_auto_commit=spy), _map(2.0))
    assert last.reason == "fit_rejected"
    assert last.fit_ok is False
    _assert_refused(state, before, spy)
    assert state.snapshot().draft_sample_count > 0


def test_horizon_refused_in_range_scale_1000() -> None:
    state = _ready(scale=2.0, known=1000.0)
    before = state.get_applied_params()
    spy = _Spy()
    last = _fill(OnlineSampler(state, auto_commit=True, on_auto_commit=spy), _map(1.0))
    assert last.reason == "horizon_refused"
    assert last.fit_ok is True
    _assert_refused(state, before, spy)


def test_horizon_boundary_exactly_3m_is_refused() -> None:
    state = _ready(scale=1.5, known=3.0)
    before = state.get_applied_params()
    spy = _Spy()
    last = _fill(OnlineSampler(state, auto_commit=True, on_auto_commit=spy), _map(1.0))
    assert last.reason == "horizon_refused"
    _assert_refused(state, before, spy)


def test_horizon_just_under_3m_commits() -> None:
    state = _ready(scale=1.5, known=2.99)
    last = _fill(OnlineSampler(state, auto_commit=True), _map(1.0))
    assert last.reason == "committed"
    assert state.get_applied_params().scale == pytest.approx(2.99)  # type: ignore[union-attr]


def test_strict_deep_scene_refused_even_when_equal_to_applied() -> None:
    """Consented scale already puts the median at 4 m; strict rule still refuses.

    The candidate equals the applied scale, so this also proves the horizon
    gate runs before the deadband.
    """
    state = _ready(scale=2.0, known=4.0)
    before = state.get_applied_params()
    spy = _Spy()
    last = _fill(OnlineSampler(state, auto_commit=True, on_auto_commit=spy), _map(2.0))
    assert last.reason == "horizon_refused"
    assert last.reason != "within_deadband"
    _assert_refused(state, before, spy)


def test_fingerprint_unavailable_refused() -> None:
    state = _ready(scale=1.5, known=2.0)
    before = state.get_applied_params()
    spy = _Spy()
    sampler = OnlineSampler(state, auto_commit=True, on_auto_commit=spy)
    last = _fill(sampler, _map(1.0), live=None)
    assert last.reason == "fingerprint_unavailable"
    _assert_refused(state, before, spy)


def test_fingerprint_camera_mismatch_refused() -> None:
    state = _ready(scale=1.5, known=2.0)
    before = state.get_applied_params()
    spy = _Spy()
    sampler = OnlineSampler(state, auto_commit=True, on_auto_commit=spy)
    last = _fill(sampler, _map(1.0), live=_fp("cam1", width=4, height=4))
    assert last.reason == "fingerprint_mismatch"
    _assert_refused(state, before, spy)


def test_fingerprint_resolution_mismatch_refused() -> None:
    state = _ready(scale=1.5, known=2.0, fingerprint=_fp(width=4, height=4))
    before = state.get_applied_params()
    spy = _Spy()
    sampler = OnlineSampler(state, auto_commit=True, on_auto_commit=spy)
    last = _fill(sampler, _map(1.0), live=_fp(width=8, height=4))
    assert last.reason == "fingerprint_mismatch"
    _assert_refused(state, before, spy)


def test_offset_lock_gate_refuses_nonzero_offset() -> None:
    state = _ready(scale=1.5, known=2.0)
    applied = state.get_applied_params()
    assert applied is not None
    sampler = OnlineSampler(state, auto_commit=True)
    candidate = CalibrationParams(
        scale=2.0,
        offset=0.5,
        sample_count=8,
        residual_rms=0.0,
        fingerprint=applied.fingerprint.model_copy(),
    )
    result = CalibrationFitResult(
        ok=True, scale=2.0, offset=0.5, residual_rms=0.0, sample_count=8
    )
    reason = sampler._commit_gate(  # noqa: SLF001
        candidate, result, LIVE, _map(1.0)
    )
    assert reason == "offset_not_zero"
    zero = candidate.model_copy(update={"offset": 0.0})
    ok_result = CalibrationFitResult(
        ok=True, scale=2.0, offset=0.0, residual_rms=0.0, sample_count=8
    )
    assert sampler._commit_gate(zero, ok_result, LIVE, _map(1.0)) is None  # noqa: SLF001


def test_clear_racing_commit_wins(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _ready(scale=1.5, known=2.0)
    spy = _Spy()

    def _clear_then_match(_saved: object, _live: object) -> tuple[bool, None]:
        state.clear_applied()
        return True, None

    monkeypatch.setattr(online_sampler_mod, "fingerprints_match", _clear_then_match)
    last = _fill(OnlineSampler(state, auto_commit=True, on_auto_commit=spy), _map(1.0))
    assert last.reason == "commit_stale"
    assert state.is_applied() is False
    assert state.snapshot().online_status == "online_off"
    assert spy.calls == 0


# --- deadband --------------------------------------------------------------


def test_deadband_constant_and_boundary() -> None:
    assert ONLINE_COMMIT_DEADBAND == 0.01
    assert within_deadband(100.5, 100.0) is True
    assert within_deadband(99.5, 100.0) is True
    assert within_deadband(100.0, 100.0) is True
    # Exactly 1% is outside the band and commits.
    assert within_deadband(101.0, 100.0) is False
    assert within_deadband(99.0, 100.0) is False
    assert within_deadband(101.5, 100.0) is False


@pytest.mark.parametrize("prior", ["online_draft", "rejected"])
def test_deadband_half_percent_skips(
    prior: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    state = _ready(scale=2.0, known=2.01)
    if prior == "rejected":
        state.set_online_status("rejected")
    before = state.get_applied_params()
    spy = _Spy()
    calls: list[object] = []
    real = state.apply_params

    def _spy_apply_params(*args: object, **kwargs: object) -> object:
        calls.append((args, kwargs))
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(state, "apply_params", _spy_apply_params)
    sampler = OnlineSampler(state, auto_commit=True, on_auto_commit=spy)
    last = _fill(sampler, _map(1.0))
    assert last.accepted is True
    assert last.reason == "within_deadband"
    assert last.fit_ok is True
    assert calls == []
    assert spy.calls == 0
    assert state.get_applied_params() is before
    snap = state.snapshot()
    assert snap.has_draft_params is False
    assert snap.online_status == prior
    assert snap.draft_sample_count == 8
    # Window kept: the ninth accept refits the sliding window.
    ninth = sampler.consider(_map(1.0), frame_id=9, now_s=8.0, live_fingerprint=LIVE)
    assert ninth.reason == "within_deadband"
    assert calls == []


def test_deadband_one_and_a_half_percent_commits() -> None:
    state = _ready(scale=2.0, known=2.03)
    spy = _Spy()
    last = _fill(OnlineSampler(state, auto_commit=True, on_auto_commit=spy), _map(1.0))
    assert last.reason == "committed"
    assert spy.calls == 1
    assert state.get_applied_params().scale == pytest.approx(2.03)  # type: ignore[union-attr]


# --- horizon helper --------------------------------------------------------


def test_horizon_median_m_helper() -> None:
    assert horizon_median_m(np.full((2, 2), np.nan), 2.0, 0.0) is None
    assert horizon_median_m(np.zeros((2, 2)), 2.0, 0.0) is None
    assert horizon_median_m(np.full((2, 2), -1.0), 2.0, 0.0) is None
    arr = np.array([[1.0, np.nan], [np.inf, 0.0], [-3.0, 3.0]])
    # Valid pixels are 1.0 and 3.0 -> median 2.0.
    assert horizon_median_m(arr, 2.0, 0.0) == pytest.approx(4.0)
    assert horizon_median_m(arr, 1.0, 0.5) == pytest.approx(2.5)


def test_horizon_threshold_imported_not_copied() -> None:
    import inspect

    from sentry_ai.spatial.free_space import DEFAULT_METRIC_MID_CUT_M

    assert online_sampler_mod.DEFAULT_METRIC_MID_CUT_M is DEFAULT_METRIC_MID_CUT_M
    assert "3.0" not in inspect.getsource(online_sampler_mod)


# --- honesty / boundaries --------------------------------------------------


def test_auto_commit_never_calls_apply_or_apply_map(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = _ready(scale=1.5, known=2.0)
    seen: list[object] = []
    real = state.apply_params

    def _boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("sampler must not call apply/apply_map")

    def _guarded(params: CalibrationParams, **kwargs: object) -> object:
        seen.append(kwargs.get("expect_applied"))
        return real(params, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(state, "apply", _boom)
    monkeypatch.setattr(state, "apply_map", _boom)
    monkeypatch.setattr(state, "apply_params", _guarded)
    last = _fill(OnlineSampler(state, auto_commit=True), _map(1.0))
    assert last.reason == "committed"
    assert len(seen) == 1 and seen[0] is not None


def test_auto_commit_writes_no_yaml(tmp_path) -> None:
    path = tmp_path / "calibration.yaml"
    payload = b"scale: 1\n"
    path.write_bytes(payload)
    state = _ready(scale=1.5, known=2.0)
    state.set_persist_status("applied")
    persist_before = state.get_persist_status()
    last = _fill(OnlineSampler(state, auto_commit=True), _map(1.0))
    assert last.reason == "committed"
    assert path.read_bytes() == payload
    assert list(tmp_path.iterdir()) == [path]
    assert state.get_persist_status() == persist_before


def test_default_sampler_is_draft_only() -> None:
    """auto_commit defaults to False: Phase 20 draft-only contract."""
    state = _ready(scale=1.5, known=2.0)
    before = state.get_applied_params()
    sampler = OnlineSampler(state)
    last = _fill(sampler, _map(1.0))
    assert last.reason == "draft_staged"
    assert state.get_applied_params() is before
    assert state.snapshot().online_status == "online_draft"


def test_wizard_apply_has_no_horizon_gate() -> None:
    state = _ready(scale=2.0, known=2.0)
    state.set_online_status("rejected")
    state.add_draft_sample(
        CalibrationSample(point_uv=(1.0, 1.0), known_meters=1000.0, observed_raw=1.0)
    )
    state.set_draft_params(
        CalibrationParams(scale=1000.0, offset=0.0, sample_count=1, fingerprint=_fp())
    )
    state.apply()
    applied = state.get_applied_params()
    assert applied is not None and applied.scale == 1000.0
    assert state.snapshot().online_status == "rejected"
    assert math.isfinite(applied.scale)
