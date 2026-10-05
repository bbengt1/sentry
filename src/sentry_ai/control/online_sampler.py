"""Throttled draft-only online sampler (ONL-03).

Control plane over CalibrationState. Does not fit, commit meters, or read
PerceptionStore. The depth loop stays the only map-transform site.
"""

from __future__ import annotations

import math
import threading
from collections import deque
from dataclasses import dataclass
from typing import Literal

import numpy as np

from sentry_ai.control.calibration_state import CalibrationState, ConsentAnchor
from sentry_ai.schemas.calibration import CalibrationSample

__all__ = [
    "ONLINE_MIN_INTERVAL_S",
    "ONLINE_WINDOW_N",
    "OnlineSampleResult",
    "OnlineSampler",
]

ONLINE_WINDOW_N = 8
ONLINE_MIN_INTERVAL_S = 1.0


@dataclass(frozen=True)
class OnlineSampleResult:
    """In-process result. Not a REST model and not a snapshot field."""

    accepted: bool
    reason: str
    fit_ok: bool | None = None


class OnlineSampler:
    """Collect consented observations into draft samples. No fit in 20-01."""

    def __init__(
        self,
        state: CalibrationState,
        *,
        window_n: int = ONLINE_WINDOW_N,
        min_interval_s: float = ONLINE_MIN_INTERVAL_S,
    ) -> None:
        self._state = state
        self.window_n = window_n
        self.min_interval_s = min_interval_s
        self._lock = threading.Lock()
        self._window: deque[list[CalibrationSample]] = deque(maxlen=window_n)
        self._last_accept_s: float | None = None
        self._last_frame_id: int | None = None

    def consider(
        self,
        depth_map: np.ndarray | None,
        *,
        frame_id: int | None,
        now_s: float,
        map_space: Literal["raw", "applied"] = "raw",
    ) -> OnlineSampleResult:
        """Accept one frame into the draft window, or explain why not.

        A full window still returns ``window_short``. Fit is 20-02.
        """
        with self._lock:
            if frame_id is None:
                return OnlineSampleResult(accepted=False, reason="missing_frame_id")
            if not self._state.is_online():
                return OnlineSampleResult(accepted=False, reason="online_off")
            if not self._state.is_applied():
                return OnlineSampleResult(accepted=False, reason="not_applied")
            anchors = self._state.get_consent_anchors()
            if not anchors:
                return OnlineSampleResult(accepted=False, reason="no_anchors")
            if (
                self._last_frame_id is not None
                and frame_id <= self._last_frame_id
            ):
                return OnlineSampleResult(
                    accepted=False, reason="frame_not_advanced"
                )
            if (
                self._last_accept_s is not None
                and (float(now_s) - self._last_accept_s) < self.min_interval_s
            ):
                return OnlineSampleResult(accepted=False, reason="throttled")

            raw_map, reject = self._raw_map(depth_map, map_space)
            if reject is not None:
                return reject
            assert raw_map is not None
            observed: list[float] = []
            for anchor in anchors:
                value = _read_positive(raw_map, anchor)
                if value is None:
                    return OnlineSampleResult(accepted=False, reason="empty_roi")
                observed.append(value)

            frame_samples = [
                CalibrationSample(
                    point_uv=anchor.point_uv,
                    bbox_xyxy=anchor.bbox_xyxy,
                    known_meters=anchor.known_meters,
                    observed_raw=value,
                    frame_id=frame_id,
                    note="online",
                )
                for anchor, value in zip(anchors, observed, strict=True)
            ]
            # Cancel clears draft samples. Drop the matching window so the
            # next accept cannot put those frames back.
            if self._window and not self._state.get_draft_samples():
                self._window.clear()
            self._window.append(frame_samples)
            flat = [sample for frame in self._window for sample in frame]
            self._state.replace_draft_samples(flat)
            self._last_accept_s = float(now_s)
            self._last_frame_id = frame_id
            # 20-02 fits once len(self._window) >= self.window_n.
            return OnlineSampleResult(
                accepted=True, reason="window_short", fit_ok=None
            )

    def _raw_map(
        self,
        depth_map: np.ndarray | None,
        map_space: str,
    ) -> tuple[np.ndarray | None, OnlineSampleResult | None]:
        """Return a pre-apply map. Invert only for map_space='applied'."""
        if map_space == "applied":
            params = self._state.get_applied_params()
            if params is None:
                return None, OnlineSampleResult(accepted=False, reason="not_applied")
            scale = float(params.scale)
            offset = float(params.offset)
            # Copied out of the state lock (get_applied_params releases it).
            if (
                not math.isfinite(scale)
                or scale <= 0.0
                or not math.isfinite(offset)
            ):
                return None, OnlineSampleResult(
                    accepted=False, reason="bad_applied_scale"
                )
            if depth_map is None:
                return None, OnlineSampleResult(accepted=False, reason="empty_roi")
            arr = np.asarray(depth_map, dtype=np.float64)
            return (arr - offset) / scale, None
        if depth_map is None:
            return None, OnlineSampleResult(accepted=False, reason="empty_roi")
        return np.asarray(depth_map), None


def _read_positive(arr: np.ndarray, anchor: ConsentAnchor) -> float | None:
    """Point pixel or bbox median. Finite and > 0, same clipping as the wizard."""
    if getattr(arr, "ndim", 0) < 2 or arr.shape[0] < 1 or arr.shape[1] < 1:
        return None
    height, width = int(arr.shape[0]), int(arr.shape[1])
    if anchor.point_uv is not None:
        u, v = anchor.point_uv
        x = int(np.clip(round(float(u)), 0, width - 1))
        y = int(np.clip(round(float(v)), 0, height - 1))
        val = float(arr[y, x])
        if not np.isfinite(val) or val <= 0.0:
            return None
        return val
    if anchor.bbox_xyxy is None:
        return None
    x1, y1, x2, y2 = (float(v) for v in anchor.bbox_xyxy)
    xa = int(np.clip(min(x1, x2), 0, width - 1))
    xb = int(np.clip(max(x1, x2), 0, width - 1))
    ya = int(np.clip(min(y1, y2), 0, height - 1))
    yb = int(np.clip(max(y1, y2), 0, height - 1))
    roi = arr[ya : yb + 1, xa : xb + 1]
    finite = roi[np.isfinite(roi) & (roi > 0.0)]
    if finite.size == 0:
        return None
    return float(np.median(finite))
