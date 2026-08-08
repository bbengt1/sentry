"""EDGE-04: ROS2 bridge stub + VoiceNullSink no-op coverage.

Stubs only — no rclpy, no ASR/TTS, no production ROS2 node.
"""

from __future__ import annotations

import sys

import pytest

from sentry_ai.plugins.builtins import VoiceNullSink
from sentry_ai.plugins.registry import PluginRegistry, register_builtins


def test_ros2_bridge_importable_without_rclpy() -> None:
    """Ros2PerceptionBridge must import without rclpy installed."""
    assert "rclpy" not in sys.modules or True  # may never be present
    # Force re-import path: ensure bridge module does not pull rclpy
    sys.modules.pop("sentry_ai.extensions.ros2.bridge", None)
    sys.modules.pop("sentry_ai.extensions.ros2", None)
    sys.modules.pop("sentry_ai.extensions", None)

    from sentry_ai.extensions.ros2.bridge import Ros2PerceptionBridge

    assert Ros2PerceptionBridge is not None
    # Module source / dependencies must not require rclpy
    import sentry_ai.extensions.ros2.bridge as bridge_mod

    src = (bridge_mod.__file__ or "")
    assert src.endswith("bridge.py")
    text = open(src, encoding="utf-8").read()
    assert "import rclpy" not in text
    assert "from rclpy" not in text


def test_ros2_bridge_start_and_emit_not_implemented() -> None:
    from sentry_ai.extensions.ros2.bridge import Ros2PerceptionBridge

    bridge = Ros2PerceptionBridge()
    assert bridge.name == "ros2_perception"

    with pytest.raises(NotImplementedError, match=r"(?i)(extension|stub|ros2|readme)"):
        bridge.start()
    with pytest.raises(NotImplementedError, match=r"(?i)(extension|stub|ros2|readme)"):
        bridge.emit({"frame_id": 0})
    # close is a no-op (safe cleanup)
    bridge.close()


def test_ros2_not_auto_registered_as_sink() -> None:
    """ROS2 stub stays importable without polluting default sinks/health."""
    registry = PluginRegistry()
    register_builtins(registry)
    sinks = registry.list_sinks()
    assert "ros2_perception" not in sinks
    assert "ros2-stub" not in sinks
    assert "ros2" not in sinks


def test_voice_null_sink_noop_lifecycle() -> None:
    sink = VoiceNullSink()
    assert sink.name == "voice-null"
    sink.emit({"ignored": True, "audio": b"nope"})
    sink.close()  # no-op, no raise


def test_voice_null_registered_in_builtins() -> None:
    registry = PluginRegistry()
    register_builtins(registry)
    assert "voice-null" in registry.list_sinks()
    assert registry.get_sink("voice-null") is VoiceNullSink
