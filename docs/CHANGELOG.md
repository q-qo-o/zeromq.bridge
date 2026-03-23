# Changelog

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Unreleased

### Added

- ZMQ bridge extension with OmniGraph nodes for PUB/SUB transport.
- Joint state publish/subscribe nodes using JSON payloads.
- Twist publish/subscribe nodes compatible with `cmd_vel`.
- Clock publish node with `sec`/`nanosec` payload.
- Camera helper node that publishes image metadata and raw bytes.
- **ZmqImuHelper**: Node for publishing IMU sensor data (acceleration, angular velocity, and orientation).
- **Primitive Types**: Added support for Float, Double, and Int publish/subscribe nodes (`ZmqPublishFloat`, `ZmqSubscribeFloat`, etc.).
- ZMQ manager and extension initialization scaffolding.
- Bilingual docs covering usage, interface, and ROS2 examples.
- **Subscription protocol**: Control topic (`__zmq_bridge_control__`) for Isaac Sim to request ROS2 bridge subscriptions.
- **Auto-subscription**: ZmqSubscribe nodes automatically send subscription requests on first execution.
- Subscription protocol documentation merged into INTERFACE.md.

### Changed

- N/A

### Fixed

- **per_instance_state calling error**: Fixed incorrect `db.per_instance_state()` method calls across all 7 ZMQ nodes (should be property access, not function call).
- **Missing input variables**: Added proper input reading (`topic`, `time_s`) in ZmqPublishClock node.
