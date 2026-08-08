"""Importable ROS2 perception bridge stub (EDGE-04).

Not a production ROS2 node. Does **not** depend on ``rclpy``.
``start()`` / ``emit()`` raise :class:`NotImplementedError` so integrators
discover the extension point without implying a working publisher.

See ``sentry_ai/extensions/ros2/README.md`` for message-mapping notes and
deferred production scope (Humble/Jazzy package, lifecycle, bags).

Threat mitigations (T-07-20 / T-07-24): no cmd_vel / motor fields; no rclpy.
"""

from __future__ import annotations

__all__ = ["Ros2PerceptionBridge"]

_STUB_MSG = (
    "ROS2 bridge is a v1 extension stub (NotImplemented). "
    "See sentry_ai.extensions.ros2 README for integrator notes."
)


class Ros2PerceptionBridge:
    """Stub sink-like bridge. Not a production ROS2 node (EDGE-04).

    Intentionally not auto-registered in the plugin registry so
    ``sentry health`` sinks stay clean. Integrators may wire an optional
    entry point (see package README).
    """

    name: str = "ros2_perception"

    def start(self) -> None:
        """Would create ROS2 node / publishers in a future production package."""
        raise NotImplementedError(_STUB_MSG)

    def emit(self, item: object) -> None:
        """Would publish PerceptionFrame-derived messages; not implemented in v1."""
        _ = item
        raise NotImplementedError(_STUB_MSG)

    def close(self) -> None:
        """No-op cleanup (safe if start never succeeded)."""
        return None
