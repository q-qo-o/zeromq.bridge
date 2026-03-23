# ZeroMQ Bridge Architecture & Usage Guide

## Overview

The ZeroMQ Bridge provides a centralized context management system for ZeroMQ communication in Isaac Sim. All data flows through a **single unified pair of addresses** (PUB/SUB), with different data types distinguished by topic names.

## Unified Addressing Model (Single Address Pair)

**Key Feature**: All data streams through one address pair:

```
┌─────────────────────────────────────────────────────┐
│ All Publishers                                      │
│ ├─ Clock           ┐                                │
│ ├─ Joint States    ├──→ Single PUB: tcp://*:25556  │
│ ├─ Twist          │                                │
│ └─ Camera Images   ┘                                │
│                                                      │
│ All Subscribers                                     │
│ ├─ Joint States   ┐                                │
│ ├─ Twist          ├──← Single SUB: tcp://127.0.0.1:25557
│ └─ Custom Topics  ┘                                │
└─────────────────────────────────────────────────────┘
```

**Benefits**:
- ✅ Single configuration point (ZmqContext)
- ✅ Easy scaling: add new data types without address management
- ✅ Reduced port usage
- ✅ Simpler ROS2 bridge configuration
- ✅ Automatic socket pooling prevents duplicates

## Architecture

### Key Components

1. **ZmqManager** (Singleton)
   - Manages global ZMQ context
   - Maintains publisher/subscriber socket pools
   - Handles graceful shutdown
   - Supports socket address reuse with proper linger settings

2. **ZmqContext Node** (OmniGraph)
   - Initializes the ZMQ system at the start of your action graph
   - Provides execution flow control
   - Configures linger timeout for graceful socket cleanup

3. **Extension Lifecycle**
   - `on_startup()`: Initializes ZmqManager when extension loads
   - `on_shutdown()`: Cleanly closes all ZMQ sockets when extension unloads

### Key Improvements

✅ **Socket Reuse**: Prevents address binding conflicts by caching publishers/subscribers
✅ **Graceful Shutdown**: Proper linger settings ensure sockets close cleanly
✅ **Centralized Management**: Single ZmqManager instance controls all ZMQ operations  
✅ **Auto-cleanup**: atexit handler ensures cleanup even on unexpected exit
✅ **ROS2 Compatible**: Proper ZMQ configuration for ROS2 bridge communication

## Usage

### 1. Setup Action Graph with ZmqContext

Place **ZmqContext at the start** of your action graph to configure global addresses:

```
[Tick] → [ZmqContext] → [All Other ZMQ Nodes]
         ├─ Publish Address: tcp://*:25556     ← Single address for ALL publishers
         ├─ Subscribe Address: tcp://127.0.0.1:25557 ← Single address for ALL subscribers
         └─ Linger Time: 100ms
```

### 2. Configure Global Addresses (Single Pair)

**ZmqContext Inputs:**
- `pubAddress`: Global publisher address for all data. Default: `tcp://*:25556`
- `subAddress`: Global subscriber address for all data. Default: `tcp://127.0.0.1:25557`
- `lingerMs`: Socket linger time for graceful shutdown. Default: 100ms

All subsequent nodes automatically use these global addresses.

### 3. Connect ZMQ Nodes (No Address Configuration Needed)

Every node only needs **topic name**, addresses are automatic:

```mermaid
graph LR
  A[ZmqContext<br/>tcp://*:25556<br/>tcp://127.0.0.1:25557] --> B[ZmqPublishClock<br/>topic: clock]
  A --> C[ZmqPublishJointState<br/>topic: joint_states]
  A --> D[ZmqPublishTwist<br/>topic: cmd_vel]
  A --> E[ZmqCameraHelper<br/>topic: rgb_image]
  A --> Imu[ZmqImuHelper<br/>topic: imu_data]
  A --> F[ZmqSubscribeJointState<br/>topic: joint_states]
  A --> G[ZmqSubscribeTwist<br/>topic: cmd_vel]
  A --> P[Primitive Nodes<br/>Float/Double/Int]

  B -->|Frame: clock<br/>JSON| H["PUB: tcp://*:25556<br/>All Data Streams"]
  C -->|Frame: joint_states<br/>JSON| H
  D -->|Frame: cmd_vel<br/>JSON| H
  E -->|Frame: rgb_image<br/>Metadata + Bytes| H
  Imu -->|Frame: imu_data<br/>JSON| H
  P -->|Frame: topic<br/>{data: value}| H
  
  H -->|Subscriptions| I["SUB: tcp://127.0.0.1:25557<br/>Topic Filtering"]
  I --> F
  I --> G
```

### 3a. Optional: Override Global Addresses for Specific Nodes

If you need a node to use a different address (advanced use case):

**Example**: Publish camera to a separate high-bandwidth address
```
ZmqCameraHelper node:
├─ pubAddress: tcp://*:6666  (overrides global tcp://*:25556)
├─ topic: rgb_image
└─ Other inputs...
```

But most use cases will just use the global addresses.

## Data Message Format

All data uses **topic-based routing** through the unified address pair:

```
┌─ Message Frame Structure ─┐
├─ Frame 0: Topic Name     │ ← Identifies data type
│  Examples:               │   - "clock"
│                          │   - "joint_states"
│                          │   - "cmd_vel"
│                          │   - "rgb_image"
├─ Frame 1: Payload        │ ← JSON for most data
│  (JSON or Metadata)      │   (Metadata for images)
├─ Frame 2: (Optional)     │ ← Raw bytes for images
│  Binary Data             │
└────────────────────────┘
```

**Examples**:

Clock message:
```
[0] "clock"
[1] {"sec": 123, "nanosec": 456000000}
```

Joint State message:
```
[0] "joint_states"
[1] {"name": ["j1", "j2"], "position": [0.1, 0.2], "velocity": [0.0, 0.0]}
```

Camera message (PNG):
```
[0] "rgb_image"
[1] {"width": 1280, "height": 720, "channels": 4, "encoding": "png", ...}
[2] [PNG encoded bytes...]
```

## Troubleshooting

### "Address in use" Error (tcp://*:25556)

**Root Cause**: Previous Isaac Sim session didn't properly clean up ZMQ sockets.

**Solutions**:
1. **Restart Isaac Sim** (cleanest option)
2. **Wait 60-90 seconds** (OS releases TIME_WAIT sockets after linger timeout)
3. **Use different port**: Change publish address to `tcp://*:25557` in ZmqContext
4. **Increase linger time**: Set `lingerMs` to 200-500 for more graceful shutdown

### Slow ROS2 Communication

**Check**:
```bash
# Verify ports are listening
netstat -an | grep 25556
netstat -an | grep 25557

# Check ROS2 node communication
ros2 topic list
ros2 topic echo /robot/joint_states
```

**Solutions**:
- Ensure ZmqContext runs before other ZMQ nodes
- Check network firewall settings
- Verify ROS2 middleware configuration (DDS_DOMAIN_ID, RMW_IMPLEMENTATION)

## Configuration Reference

### ZmqManager.initialize(linger_ms)

```python
mgr = ZmqManager.get_instance()
mgr.initialize(linger_ms=100)  # 100ms graceful socket shutdown
```

**Linger Time Recommendations**:
- `0ms`: Immediate close (may lose messages)
- `50-100ms`: Normal operation (default)
- `200-500ms`: Slow networks or many pending messages
- `1000ms+`: Very reliable but slower shutdown

### Socket Pooling

Sockets are cached by address:
```python
# First call creates new publisher
pub1 = mgr.get_publisher("tcp://*:25556")

# Subsequent calls reuse the same socket
pub2 = mgr.get_publisher("tcp://*:25556")  
# pub1 is pub2 == True
```

### Manual Cleanup

If needed (advanced):
```python
mgr = ZmqManager.get_instance()
mgr.clear()          # Close all sockets, keep context
mgr.shutdown()       # Full cleanup, terminate context
```

## Best Practices

1. ✅ Always use **ZmqContext at the start** of action graph to set global addresses
2. ✅ Only configure **one address pair** in ZmqContext (all data shares them)
3. ✅ Specify **topic names** in individual nodes for data type identification
4. ✅ Leave node `pubAddress`/`subAddress` inputs **empty** to use global settings
5. ✅ Let auto-shutdown handle cleanup (don't manually call shutdown)
6. ✅ Monitor /World/ActionGraph execution for errors
7. ❌ Don't override node addresses unless you have a specific reason
8. ❌ Don't manually create/close ZMQ sockets (use ZmqManager)

## Integration with ROS2

Example action graph for unified ROS2 bridge:

```
[Tick] 
↓
[ZmqContext] ← Configure ONCE: tcp://*:25556 (PUB) and tcp://127.0.0.1:25557 (SUB)
├→ execOut/execIn
[ZmqPublishClock] (topic: clock) ──┐
├→ execOut/execIn                    │
[ZmqPublishJointState] (topic: joint_states) ──┤ All flow through
├→ execOut/execIn                    │ same PUB address
[ZmqPublishTwist] (topic: cmd_vel) ──┘
├→ execOut/execIn
[ZmqSubscribeJointState] (topic: joint_states) ──┐
├→ execOut/execIn                    │
[ZmqSubscribeTwist] (topic: cmd_vel) ──┘ All from same SUB address
```

On remote ROS2 machine:
```bash
# Single bridge command for all topics
ros2 bridge zmq --pub-address tcp://isaac-sim-ip:25556 --sub-address tcp://127.0.0.1:25557
```

No need to configure separate addresses for each ROS2 topic!

## References

- [ZeroMQ Documentation](https://zguide.zeromq.org/)
- [Isaac Sim OmniGraph](https://docs.omniverse.nvidia.com/app_isaacsim/)
- [ROS2 ZMQ Bridge](https://github.com/osrf/rmw_zenoh)
