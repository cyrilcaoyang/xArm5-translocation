# Testing Guide

This guide provides a comprehensive overview of the three-stage testing strategy for the xArm-translocation project, designed to ensure robust, safe, and reliable robot applications. The strategy progresses from pure software simulation to a full physics simulation, and finally to real hardware validation.

## Three-Stage Testing Strategy

The project's testing methodology is broken down into three distinct stages:

1.  **Stage 1: Software Simulation**: Ideal for initial development, logic validation, and continuous integration. It is fast, lightweight, and carries zero risk to physical hardware.
2.  **Stage 2: Docker-Based Simulation**: Uses a full-fledged physics simulator for realistic dynamics, precise collision detection, and visual verification.
3.  **Stage 3: Real Hardware Testing**: The final validation stage on the physical xArm robot to test performance, safety, and integration in a real-world environment.

---

### Comparison of Simulation Modes

| Feature                 | Stage 1: Software Simulation | Stage 2: Docker Simulation |
| ----------------------- | ---------------------------- | -------------------------- |
| **Hardware Required**   | ❌ No                        | ❌ No                      |
| **Setup Complexity**    | 🟢 Simple                    | 🟡 Moderate                |
| **Physics Engine**      | ❌ No physics                | ✅ Full physics            |
| **Collision Detection** | ✅ Logic-based               | ✅ Physics-based           |
| **Visual Interface**    | ❌ Console only              | ✅ 3D Web UI               |
| **Resource Usage**      | 🟢 Minimal                   | 🟡 High CPU/GPU            |
| **Use Case**            | Logic & algorithm validation | Realistic motion testing   |

---

## Stage 1: Software Simulation (Built-in)

The controller has a built-in simulation mode that does not require Docker or any external dependencies. It works by mocking the robot's hardware interface, allowing you to test your code's logic, parameter validation, and error handling.

This mode includes **logic-based collision detection**:
*   **Joint Limits**: Prevents movements that would exceed the specific model's joint angle limits.
*   **Workspace Boundaries**: Enforces Cartesian workspace limits to prevent the arm from trying to move outside its reachable area.

### How to Use

To activate the built-in simulation mode, simply instantiate the `XArmController` with the `simulation_mode=True` parameter.

```python
from src.core.xarm_controller import XArmController

# Enable software simulation mode
controller = XArmController(
    model=6,
    simulation_mode=True
)

# Initialize the controller (no hardware connection is made)
if controller.initialize():
    print("Software simulation initialized successfully.")
    # All controller commands can be used here
    controller.move_to_position(x=300, y=0, z=300)
    controller.disconnect()
```

### When to Use

*   Initial algorithm development and logic testing.
*   Running unit tests in a Continuous Integration (CI/CD) pipeline.
*   Quickly testing error handling and state management without hardware.

---

## Stage 2: Docker-Based Simulation

For higher-fidelity testing, this project supports the official UFACTORY xArm simulator, which runs in a Docker container. This provides a realistic physics environment, a 3D web interface, and accurate collision detection based on the robot's 3D model. The controller connects to this simulator via a network socket, just as it would with a real robot.

### How to Use

#### Step 1: Start the Docker Container

Run the following command in your terminal to download the image and start the container. This only needs to be done once.

```bash
docker run -d --name uf_software \
    -p 18333:18333 \
    -p 502:502 \
    -p 503:503 \
    -p 504:504 \
    -p 30000:30000 \
    -p 30001:30001 \
    -p 30002:30002 \
    -p 30003:30003 \
    danielwang123321/uf-ubuntu-docker
```
*Note: This Docker image is a community-provided one. Please check the official UFACTORY website or GitHub for the latest recommended image.*

You can check if the container is running with `docker ps`.

#### Step 2: Start the xArm Firmware

Once the container is running, start the firmware simulation inside it. The command below is for an **xArm6**. Replace `6` with `5` or `7` for other models.

```bash
docker exec uf_software /xarm_scripts/xarm_start.sh 6 6
```

The simulator is now running and will be accessible to your controller at `127.0.0.1`.

#### Step 3: Connect from your Code

Your controller will connect to the simulator automatically if the `host` in your `xarm_config.yaml` is set to `127.0.0.1` (which is the default). Ensure `simulation_mode` is `False`.

```python
from src.core.xarm_controller import XArmController

# Connect to the Docker simulator (ensure model matches the simulator)
controller = XArmController(model=6)

# Initialize the controller (connects to 127.0.0.1)
if controller.initialize():
    print("Connected to Docker simulator successfully.")
    controller.move_to_position(x=300, y=0, z=300)
    controller.disconnect()
```

#### Step 4: (Optional) Access the Web UI

You can view a 3D visualization of the robot by navigating to **[http://localhost:18333](http://localhost:18333)** in your browser.

#### Step 5: Stopping the Simulator

To stop and remove the container when you are finished, run:

```bash
docker stop uf_software
docker rm uf_software
```

### When to Use

*   Verifying complex trajectories in a realistic environment.
*   Testing for subtle collisions that logic-based checks might miss.
*   Visualizing robot motion for debugging or demonstrations.

### Connecting to a Remote Simulator (e.g., via VPN/Tailscale)

You can run the Docker simulator on a separate, more powerful machine and connect to it over a secure network. The process is nearly identical to connecting to a local simulator.

**On the Remote Server (e.g., IP `100.64.254.50`):**
1.  Start the Docker container and firmware as described above. The `-p` flags will expose the simulator's ports to the server's Tailscale network interface.
2.  Ensure your client machine can ping the server's Tailscale IP.

**On the Client Machine:**
Simply specify the server's Tailscale IP address as the `host` when connecting.

**Example (Using the API):**
```bash
curl -X POST "http://127.0.0.1:6001/connect" -H "Content-Type: application/json" -d '{
  "host": "100.64.254.50",
  "model": 6
}'
```

**Example (Directly in Python):**
```python
controller = XArmController(
    host='100.64.254.50',
    model=6
)
controller.initialize()
```

---

## Stage 3: Real Hardware Testing

The final stage is to validate your code on a physical xArm. At this stage, your code's logic and motion paths should already be well-tested from the simulation stages. Testing on hardware is focused on verifying real-world performance, sensor integration, and safety.

### How to Use

1.  Ensure the robot is powered on and connected to the network.
2.  Update your `xarm_config.yaml` or pass the robot's IP address directly to the controller.
3.  Run your code. **Always be prepared to trigger the emergency stop.**

```python
from src.core.xarm_controller import XArmController

# Connect to the real robot
controller = XArmController(
    host='192.168.1.XXX', # Replace with your robot's IP
    model=6
)

if controller.initialize():
    # Run pre-validated, safe movements first
    # ...
    controller.disconnect()
```

### Safety First

*   Always have the emergency stop button within reach.
*   Start with slow speeds and simple, non-obstructed movements.
*   Define and test safety boundaries and collision sensitivity settings before running complex routines. 