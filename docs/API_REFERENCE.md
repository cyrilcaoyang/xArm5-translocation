# API Reference

This document provides a detailed reference for the xArm-translocation project's RESTful API. 

The API allows for comprehensive control over the xArm robot, its components, and the simulation environment.

Start the server by runing xarm_api_server.py as a module at the project root folder.

```bash
python -m src.core.xarm_api_server
```

The API server runs on `http://127.0.0.1:6001` by default.

---

## Table of Contents

- [Server & Connection](#server--connection-management)
- [Robot Arm Movement](#robot-arm-movement)
- [Components](#components)
  - [Gripper](#gripper)
  - [Linear Track](#linear-track)
- [System & Safety](#system--safety)
- [WebSocket Interface](#websocket-interface)

---

## Server & Connection Management

These endpoints manage the connection to the robot (real or simulated) and provide status information.

### `GET /api/configurations`

Retrieves a list of available connection configuration files from the `src/settings/` directory. These can be used with the `/connect` endpoint.

**Response `200 OK`**

```json
[
  "xarm5_docker_local.yaml",
  "xarm5_docker_server.yaml",
  "xarm5_config.yaml"
]
```

**Example**

```bash
curl -X GET "http://127.0.0.1:6001/api/configurations"
```

### `POST /connect`

Initializes the connection to the xArm controller. This is the first command that must be sent to interact with the robot. The connection can be configured in several ways.

**Request Body**

```json
{
  "host": "string",
  "model": "integer",
  "config_name": "string",
  "simulation_mode": "boolean",
  "safety_level": "string"
}
```

*   `host` (optional): IP address of the robot or simulator.
*   `model` (optional): The xArm model number (e.g., 5, 6, 7).
*   `config_name` (optional): The name of a configuration file (e.g., `"xarm5_docker_local.yaml"`) to load settings from.
*   `simulation_mode` (optional, default: `false`): Set to `true` to use the built-in software simulator without any hardware or Docker.
*   `safety_level` (optional, default: `"medium"`): Sets the initial safety level. Options are `"low"`, `"medium"`, `"high"`.

**Response `200 OK`**

```json
{
  "status": "success",
  "message": "Controller initialized successfully for xArm6 at 127.0.0.1"
}
```

**Examples**

1.  **Connect using a configuration file:**
    ```bash
    curl -X POST "http://127.0.0.1:6001/connect" -H "Content-Type: application/json" -d '{
      "config_name": "xarm5_docker_local.yaml"
    }'
    ```

2.  **Connect to a remote Docker simulator:**
    ```bash
    curl -X POST "http://127.0.0.1:6001/connect" -H "Content-Type: application/json" -d '{
      "host": "100.64.254.50",
      "model": 6
    }'
    ```

3.  **Connect using the built-in software simulation:**
    ```bash
    curl -X POST "http://127.0.0.1:6001/connect" -H "Content-Type: application/json" -d '{
      "model": 7,
      "simulation_mode": true
    }'
    ```

### `POST /disconnect`

Disconnects from the robot and shuts down the controller gracefully.

**Response `200 OK`**
```json
{
  "status": "success",
  "message": "Disconnected from the robot."
}
```

**Example**
```bash
curl -X POST "http://127.0.0.1:6001/disconnect"
```

### `GET /status`

Retrieves the current status of the robot and controller.

**Response `200 OK`**
```json
{
    "connected": true,
    "running": true,
    "error_code": 0,
    "safety_level": "medium",
    "model": 6,
    "components": {
        "gripper": { "connected": true, "enabled": true },
        "linear_track": { "connected": false, "enabled": false }
    }
}
```

**Example**
```bash
curl -X GET "http://127.0.0.1:6001/status"
```

---
## Robot Arm Movement

Endpoints for controlling the physical movement of the xArm.

### `POST /move/cartesian`

Moves the robot's end-effector to a specific Cartesian position (X, Y, Z) and orientation (roll, pitch, yaw).

**Request Body**
```json
{
    "x": "number",
    "y": "number",
    "z": "number",
    "roll": "number",
    "pitch": "number",
    "yaw": "number",
    "speed": "integer",
    "mvacc": "integer"
}
```
*   `speed` (optional, default: 100 mm/s)
*   `mvacc` (optional, default: 1000 mm/s²)

**Response `200 OK`**
```json
{ "status": "success", "message": "Move command sent" }
```

**Example**
```bash
curl -X POST "http://127.0.0.1:6001/move/cartesian" -H "Content-Type: application/json" -d '{
    "x": 300, "y": 0, "z": 250, "roll": 180, "pitch": 0, "yaw": 0
}'
```

### `POST /move/joints`

Moves the robot to a specific pose by setting the angle for each joint.

**Request Body**
```json
{
    "j1": "number",
    "j2": "number",
    "j3": "number",
    "j4": "number",
    "j5": "number",
    "j6": "number",
    "j7": "number",
    "speed": "integer",
    "mvacc": "integer"
}
```
*   Provide angles for the joints available on your model (e.g., `j1` to `j5` for xArm5).
*   `speed` (optional, default: 20 deg/s)
*   `mvacc` (optional, default: 200 deg/s²)

**Response `200 OK`**
```json
{ "status": "success", "message": "Move command sent" }
```

**Example**
```bash
curl -X POST "http://127.0.0.1:6001/move/joints" -H "Content-Type: application/json" -d '{
    "j1": 45, "j2": -30, "j3": 0, "j4": 0, "j5": 30, "j6": 0
}'
```

### `GET /position/cartesian`

Retrieves the current Cartesian position and orientation of the end-effector.

**Response `200 OK`**
```json
{
    "x": 300.1, "y": 0.5, "z": 250.2, "roll": 179.9, "pitch": 0.1, "yaw": -0.2
}
```

**Example**
```bash
curl -X GET "http://127.0.0.1:6001/position/cartesian"
```

### `GET /position/joints`

Retrieves the current angles of all robot joints.

**Response `200 OK`**
```json
{
    "j1": 45.1, "j2": -30.0, "j3": 0.2, "j4": 0.1, "j5": 29.8, "j6": -0.1, "j7": 0.0
}
```

**Example**
```bash
curl -X GET "http://127.0.0.1:6001/position/joints"
```

---
## Components

These endpoints control attached components like the gripper and linear track.

### Gripper

#### `POST /gripper/open`

Opens the gripper.

**Response `200 OK`**
```json
{ "status": "success", "message": "Gripper opened" }
```
**Example**
```bash
curl -X POST "http://127.0.0.1:6001/gripper/open"
```

#### `POST /gripper/close`

Closes the gripper.

**Response `200 OK`**
```json
{ "status": "success", "message": "Gripper closed" }
```
**Example**
```bash
curl -X POST "http://127.0.0.1:6001/gripper/close"
```

#### `GET /gripper/status`

Retrieves the current status of the gripper.

**Response `200 OK`**
```json
{
    "position": 850.0,
    "is_open": true
}
```
*   `position`: Raw position value from the gripper motor.

**Example**
```bash
curl -X GET "http://127.0.0.1:6001/gripper/status"
```

### Linear Track

#### `POST /track/move`

Moves the linear track to an absolute position.

**Request Body**
```json
{
    "position": "number",
    "speed": "integer"
}
```
*   `speed` (optional, default: 100 mm/s)

**Response `200 OK`**
```json
{ "status": "success", "message": "Track move command sent" }
```
**Example**
```bash
curl -X POST "http://127.0.0.1:6001/track/move" -H "Content-Type: application/json" -d '{
    "position": 500
}'
```

#### `POST /track/move/location`

Moves the linear track to a pre-defined named location from `location_config.yaml`.

**Request Body**
```json
{ "location_name": "string" }
```

**Response `200 OK`**
```json
{ "status": "success", "message": "Track moving to location: start" }
```
**Example**
```bash
curl -X POST "http://127.0.0.1:6001/track/move/location" -H "Content-Type: application/json" -d '{
    "location_name": "start"
}'
```

#### `GET /track/status`

Retrieves the current status of the linear track.

**Response `200 OK`**
```json
{ "position": 500.1 }
```
**Example**
```bash
curl -X GET "http://127.0.0.1:6001/track/status"
```

---
## System & Safety

Endpoints for system-level configuration and monitoring.

### `POST /safety/level`

Sets the system's safety level, which can affect speed, acceleration, and collision sensitivity.

**Request Body**
```json
{ "level": "string" }
```
*   `level`: `"low"`, `"medium"`, or `"high"`

**Response `200 OK`**
```json
{ "status": "success", "message": "Safety level set to high" }
```
**Example**
```bash
curl -X POST "http://127.0.0.1:6001/safety/level" -H "Content-Type: application/json" -d '{
    "level": "high"
}'
```

### `GET /performance`

Retrieves performance statistics from the controller, such as API latency and command processing time.

**Response `200 OK`**
```json
{
    "api_latency_ms": 1.5,
    "command_rate_hz": 50.2,
    "cpu_usage_percent": 15.7
}
```
**Example**
```bash
curl -X GET "http://127.0.0.1:6001/performance"
```

---
## WebSocket Interface

A WebSocket is available for receiving real-time status updates from the controller.

### `GET /ws`

Establishes a WebSocket connection. Once connected, the server will push status updates automatically at a regular interval. This is the same data that drives the web UI.

**Connection URL**: `ws://127.0.0.1:6001/ws`

**Example Message (from server)**
```json
{
    "connected": true,
    "running": true,
    "error_code": 0,
    "mode": 0,
    "state": 4,
    "safety_level": "medium",
    "position_cartesian": [300.1, 0.5, 250.2, 179.9, 0.1, -0.2],
    "position_joints": [45.1, -30.0, 0.2, 0.1, 29.8, -0.1, 0.0],
    "components": {
        "gripper": { "connected": true, "position": 850.0 },
        "linear_track": { "connected": true, "position": 500.1 }
    }
}
``` 