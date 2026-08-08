# ROS2 perception bridge (v1 stub)

**Status:** Importable **NotImplemented** scaffold only (EDGE-04).  
**Not** a production ROS2 package. **No** `rclpy` dependency in Sentry core.

## What ships in v1

```python
from sentry_ai.extensions.ros2.bridge import Ros2PerceptionBridge

bridge = Ros2PerceptionBridge()
assert bridge.name == "ros2_perception"
# bridge.start()  -> NotImplementedError
# bridge.emit(x)  -> NotImplementedError
bridge.close()  # no-op
```

The bridge is **not** auto-registered as a sink (`register_builtins` / health
lists stay free of half-implemented ROS plugins). Optional future entry-point
snippet for integrators:

```toml
# pyproject.toml (your package — not Sentry core default)
[project.entry-points."sentry_ai.sinks"]
ros2-stub = "your_pkg.ros2:Ros2PerceptionBridge"
```

## Intended mapping (future)

Integrators would map Sentry wire JSON (`PerceptionFrame`) to ROS2 messages, e.g.:

| Sentry field | Typical ROS2 direction |
|--------------|------------------------|
| `frame_id`, `camera_id`, `t_capture` | Header / frame_id conventions |
| `detections[]` | `vision_msgs/Detection2DArray` (or custom) |
| `depth` metadata | Custom relative-depth topic (not meters unless calibrated) |
| `free_space` | Custom obstacle cue topic — **not** a safety interlock |
| control fields | **None** — Sentry is perception-only (no `cmd_vel` / motors) |

Always honor `completeness` and `stats.*_stale` on the consumer side.

## Deferred production scope

Not in v1:

- Humble / Jazzy package + `package.xml` / launch files
- Lifecycle node management
- Bag recording
- Multi-camera TF / extrinsic calibration
- Real `rclpy` publishers or QoS tuning

## Non-autonomy

This stub does **not** publish robot control commands. Free-space / obstacle
cues from Sentry are perception signals only — your robot controller owns
e-stop and motion. See [`docs/safety-and-privacy.md`](../../../../docs/safety-and-privacy.md).
