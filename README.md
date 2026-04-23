# ZeroMQ Bridge for Isaac Sim

[中文版说明请见下方 (Chinese Version Below)](#中文说明-chinese-version)

## English Overview

A lightweight, high-performance communication bridge for NVIDIA Isaac Sim based on ZeroMQ (ZMQ). This extension allows seamless data exchange (Publish/Subscribe) between Isaac Sim and external control systems, simulation environments, or custom ROS2 bridge nodes via OmniGraph.

### Core Features

- **OmniGraph Integration**: Provides intuitive visual nodes (`ZmqPublish*`, `ZmqSubscribe*`) in the Action Graph without writing code.
- **Rich Data Types**: Fully supports fundamental types (Float, Double, Int and Arrays), physical states (Twist/CmdVel, JointState, Odometry), and complex sensors (Camera Image, IMU, Depth/Altitude, Nav/GPS).
- **Auto-Subscription Protocol**: Subscribers automatically handshake with external endpoints using the `__zmq_bridge_control__` topic, reducing manual configuration.
- **Safety Mechanisms**: Built-in thread-safe socket management and control signal watchdogs (prevents robot runaway upon network disconnection).

### Installation & Setup

1. Ensure this folder (`zeromq.bridge`) is placed in your Isaac Sim's extension search path (e.g., `extsUser` directory).
2. Launch Isaac Sim.
3. Navigate to **Window > Extensions**.
4. Search for `zmq.bridge` and toggle the switch to enable it.

### Quick Start

1. Open **Window > Visual Scripting > Action Graph**.
2. Create a new Action Graph.
3. Search for nodes under the **ZmqBridge** category.
4. Drag and drop a Publisher or Subscriber node.
5. Configure the **Subscribe/Publish Address** (e.g., `tcp://127.0.0.1:25557`) and **Topic Name** (e.g., `cmd_vel`).
6. Connect the `execIn` pin to a tick stream (like `On Playback Tick`).

---

## 中文说明 (Chinese Version)

基于 ZeroMQ (ZMQ) 为 NVIDIA Isaac Sim 构建的轻量级、高性能通信桥接扩展。该插件使得 Isaac Sim 能够通过 OmniGraph 节点，以发布/订阅（Pub/Sub）模式与外部控制系统、其他仿真环境或自定义的 ROS2 桥接节点进行无缝数据交互。

### 核心特性

- **OmniGraph 深度集成**：在动作图（Action Graph）中提供直观的可视化节点（`ZmqPublish*`, `ZmqSubscribe*`），无需编写代码即可完成通讯链路搭建。
- **丰富的数据类型支持**：全面支持基础类型（Float, Double, Int 及其数组）、物理运动状态（Twist/CmdVel, JointState, Odometry）以及复杂的传感器（相机图像, IMU, 深度计/高度计, Nav导航数据）。
- **自动订阅协议**：订阅者节点会在图引擎执行时，自动通过 `__zmq_bridge_control__` 主题与外部端点握手，极大简化了外部程序的路由配置。
- **安全与稳定性**：内置底层 Socket 线程安全锁，并对控制信号节点加入了看门狗（Watchdog）熔断机制（网络断开或超时会自动归零速度，防止机器人“飞车”）。

### 安装与配置

1. 确保本工程文件夹（`zeromq.bridge`）已放置在 Isaac Sim 的扩展搜索路径下（例如 `extsUser` 目录）。
2. 启动 Isaac Sim。
3. 在顶部菜单栏选择 **Window > Extensions**。
4. 搜索 `zmq.bridge`，点击开启按钮进行加载。

### 快速开始

1. 打开 **Window > Visual Scripting > Action Graph** 节点编辑器。
2. 新建一个 Action Graph。
3. 在左侧节点库的 **ZmqBridge** 目录下找到所需节点。
4. 拖拽发布者（Publisher）或订阅者（Subscriber）节点到画布中。
5. 在属性面板配置 **Subscribe/Publish Address**（如 `tcp://127.0.0.1:25557`）以及对应的 **Topic Name**（如 `cmd_vel`）。
6. 将节点的 `execIn` 引脚连接到时钟触发源（如 `On Playback Tick`）。
