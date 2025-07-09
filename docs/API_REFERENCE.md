# xArm Translocation API Documentation

This document provides instructions on how to use the REST API for controlling the xArm robot.

## Running the API Server

### 1. Installation

The API server requires Python 3 and several packages. You can install the dependencies using pip:

```bash
pip install fastapi "uvicorn[standard]" websockets
```

### 2. Starting the Server

To start the API server, run the following command from the root of the project directory:

```bash
python src/xarm_api_server.py
```

The server will start on `http://0.0.0.0:6001`.

## API Endpoints

The API provides several endpoints to control the robot.

---

### System

#### `POST /connect`

Connects to the robot and initializes the controller.

**Request Body:**

```json
{
  "config_path": "users/settings/",
  "gripper_type": "bio",
  "enable_track": true,
  "auto_enable": true,
  "model": null
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/connect -H "Content-Type: application/json" -d '{}'
```

---

#### `POST /disconnect`

Disconnects from the robot.

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/disconnect
```

---

#### `GET /status`

Retrieves the current status of the robot.

**Example:**

```bash
curl http://127.0.0.1:6001/status
```

---

### Movement

#### `POST /move/position`

Moves the robot to a specific Cartesian position.

**Request Body:**

```json
{
  "x": 200,
  "y": 0,
  "z": 150,
  "roll": 180,
  "pitch": 0,
  "yaw": 0,
  "speed": 100,
  "wait": true
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/move/position -H "Content-Type: application/json" -d '{"x": 200, "y": 0, "z": 150}'
```

---

#### `POST /move/joints`

Moves the robot to a specific joint configuration.

**Request Body:**

```json
{
  "angles": [0, 0, 0, 0, 0, 0],
  "speed": 50,
  "wait": true
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/move/joints -H "Content-Type: application/json" -d '{"angles": [30, 30, 0, 0, 0, 0]}'
```

---

#### `POST /move/relative`

Moves the robot relative to its current position.

**Request Body:**

```json
{
  "dx": 10,
  "dy": 10,
  "dz": 0,
  "droll": 0,
  "dpitch": 0,
  "dyaw": 0,
  "speed": 100
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/move/relative -H "Content-Type: application/json" -d '{"dx": 20}'
```

---

#### `POST /move/location`

Moves the robot to a pre-configured named location.

**Request Body:**

```json
{
  "location_name": "home_safe",
  "speed": 100
}
```

---

#### `POST /move/home`

Moves the robot to its home position.

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/move/home
```

---

#### `POST /move/stop`

Stops all robot movement immediately.

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/move/stop
```

---

### Velocity Control

#### `POST /velocity/cartesian`

Sets a continuous Cartesian velocity for the robot's end-effector.

**Request Body:**

```json
{
  "vx": 10,
  "vy": 0,
  "vz": 0,
  "vroll": 0,
  "vpitch": 0,
  "vyaw": 0
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/velocity/cartesian -H "Content-Type: application/json" -d '{"vx": 10}'
```

---

### Gripper Control

#### `POST /gripper/open`

Opens the gripper.

**Request Body:**

```json
{
  "speed": 500,
  "wait": true
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/gripper/open -H "Content-Type: application/json" -d '{}'
```

---

#### `POST /gripper/close`

Closes the gripper.

**Request Body:**

```json
{
  "speed": 500,
  "wait": true
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/gripper/close -H "Content-Type: application/json" -d '{}'
```

---

### Linear Track Control

#### `POST /track/move`

Moves the linear track to a specific position.

**Request Body:**

```json
{
  "position": 100,
  "speed": 100,
  "wait": true
}
```

**Example:**

```bash
curl -X POST http://127.0.0.1:6001/track/move -H "Content-Type: application/json" -d '{"position": 100}'
```

---

#### `GET /track/position`

Gets the current position of the linear track.

**Example:**

```bash
curl http://127.0.0.1:6001/track/position
```

---

## WebSocket Interface

The API provides a WebSocket endpoint for real-time status updates.

### Endpoint: `/ws`

Connect to this endpoint to receive status updates from the robot, such as position, joint angles, and component states.

When a client connects, it will receive an initial status update. The server will then broadcast updates whenever the robot's state changes (e.g., after a move command).

**Example Client (JavaScript):**

```javascript
const ws = new WebSocket("ws://127.0.0.1:6001/ws");

ws.onopen = () => {
  console.log("Connected to xArm WebSocket.");
};

ws.onmessage = (event) => {
  const status = JSON.parse(event.data);
  console.log("Received status update:", status);
};

ws.onclose = () => {
  console.log("Disconnected from WebSocket.");
};

ws.onerror = (error) => {
  console.error("WebSocket error:", error);
};
``` 