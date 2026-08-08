"""Thread-safe pipeline stage flags + free-space cutoffs (UI-03/UI-04).

Cold-path control plane only — no FastAPI imports, no inference.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

from sentry_ai.spatial.free_space import DEFAULT_MID_CUT, DEFAULT_NEAR_CUT

__all__ = ["PipelineState"]


def _validate_cut(name: str, value: float) -> float:
    v = float(value)
    if not 0.0 <= v <= 1.0:
        raise ValueError(f"{name} must be in [0, 1], got {value!r}")
    return v


@dataclass
class PipelineState:
    """Thread-safe stage enable flags and free-space near/mid cutoffs."""

    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)
    detection_enabled: bool = True
    depth_enabled: bool = True
    free_space_enabled: bool = True
    near_cut: float = DEFAULT_NEAR_CUT
    mid_cut: float = DEFAULT_MID_CUT

    def snapshot(self) -> dict[str, Any]:
        """Return a full isolated copy of current pipeline config."""
        with self._lock:
            return {
                "detection_enabled": self.detection_enabled,
                "depth_enabled": self.depth_enabled,
                "free_space_enabled": self.free_space_enabled,
                "near_cut": self.near_cut,
                "mid_cut": self.mid_cut,
            }

    def update(self, **kwargs: Any) -> dict[str, Any]:
        """Merge partial fields under lock; return full snapshot.

        Raises
        ------
        ValueError
            Unknown keys, non-bool flags, cuts outside [0, 1], or
            effective ``near_cut <= mid_cut``.
        """
        allowed = {
            "detection_enabled",
            "depth_enabled",
            "free_space_enabled",
            "near_cut",
            "mid_cut",
        }
        unknown = set(kwargs) - allowed
        if unknown:
            raise ValueError(f"unknown pipeline fields: {sorted(unknown)}")

        with self._lock:
            det = self.detection_enabled
            dep = self.depth_enabled
            fs = self.free_space_enabled
            near = self.near_cut
            mid = self.mid_cut

            if "detection_enabled" in kwargs:
                if not isinstance(kwargs["detection_enabled"], bool):
                    raise ValueError("detection_enabled must be bool")
                det = kwargs["detection_enabled"]
            if "depth_enabled" in kwargs:
                if not isinstance(kwargs["depth_enabled"], bool):
                    raise ValueError("depth_enabled must be bool")
                dep = kwargs["depth_enabled"]
            if "free_space_enabled" in kwargs:
                if not isinstance(kwargs["free_space_enabled"], bool):
                    raise ValueError("free_space_enabled must be bool")
                fs = kwargs["free_space_enabled"]
            if "near_cut" in kwargs:
                near = _validate_cut("near_cut", kwargs["near_cut"])
            if "mid_cut" in kwargs:
                mid = _validate_cut("mid_cut", kwargs["mid_cut"])

            if near <= mid:
                raise ValueError(
                    f"near_cut must be > mid_cut (got near_cut={near}, mid_cut={mid})"
                )

            self.detection_enabled = det
            self.depth_enabled = dep
            self.free_space_enabled = fs
            self.near_cut = near
            self.mid_cut = mid

            return {
                "detection_enabled": self.detection_enabled,
                "depth_enabled": self.depth_enabled,
                "free_space_enabled": self.free_space_enabled,
                "near_cut": self.near_cut,
                "mid_cut": self.mid_cut,
            }
