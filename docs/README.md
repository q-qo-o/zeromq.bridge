# Usage

### Enable Extension

Open `Window > Extensions`, search for "zmq.bridge", and enable it.

### Quick Start

1. Create an OmniGraph.
2. Add a `ZmqPublish*` or `ZmqSubscribe*` node from the **ZmqBridge** category (e.g., `ZmqPublishFloat`, `ZmqPublishFloatArray`, etc.).
3. Set the `pubAddress` / `subAddress` and `topicName` properties.
4. Connect the `execIn` pin to a tick or action trigger.

### Notes

- **Supported Data Types**: Float(Array), Double(Array), Int(Array), Twist (CmdVel), JointState, Clock, Image, Imu, Nav/GPS, Depth/Altitude, Odometry.
- ZMQ topics are simply strings; keep them consistent with your external communication endpoints (e.g., ROS2).
- Ensure input/output attributes include `description` fields in `.ogn` definitions.
- PUB/SUB pattern is strictly best-effort; avoid any blocking calls in node `compute` methods to prevent freezing the simulation.

### Subscription Protocol

- **Automatic Subscription**: `ZmqSubscribe*` nodes automatically send a subscription request to the external bridge upon their first execution in the graph.
- **Control Topic**: `__zmq_bridge_control__` - Used to inform the external bridge (like ROS2) which topics Isaac Sim needs to listen to.
- **Detailed Documentation**: Please refer to the "Subscription Protocol" section in `INTERFACE.md`.

---

## Documentation

- [INTERFACE.md](INTERFACE.md) - Complete API reference and architecture.
- [CHANGELOG.md](CHANGELOG.md) - Version history.
