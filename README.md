# XArm Translocation Control

A Python package for controlling xArm robotic arms with integrated gripper and linear track support for translocation tasks. This package provides a unified controller that supports multiple gripper types and optional linear track functionality.

## Features

- **Unified Control**: Single `XArmController` class manages arm, gripper, and linear track
- **Multiple Gripper Support**: BIO, Standard, RobotIQ grippers, or no gripper
- **Movement Types**: Joint, linear/Cartesian, relative, named locations, velocity control
- **State Management**: Comprehensive component state tracking and error handling
- **Flexible Configuration**: Auto-enable or manual component control
- **Safety Features**: Component validation, error history, position caching

## Installation

### With a real robot

Please install SDK first in your environment from the [xArm-Python-SDK](https://github.com/xArm-Developer/xArm-Python-SDK) repository.

  1. `git clone https://github.com/xArm-Developer/xArm-Python-SDK.git`
  2. `cd xArm-Python-SDK`
  3. `python setup.py install`

### With the simulator (no robot required)

It's possible to use a simulator to run the UFACTORY Studio UI and use Blockly without being connected to a physical xArm. This is based on a docker image.

Reference: [UFACTORY Studio simulation](https://forum.ufactory.cc/t/ufactory-studio-simulation/3719)

#### 1. Pull the docker image

```bash
docker pull danielwang123321/uf-ubuntu-docker
```

#### 2. Create and run the container

The following command includes web simulation and SDK ports.

```bash
docker run -it --name uf_software -p 18333:18333 -p 502:502 -p 503:503 -p 504:504 -p 30000:30000 -p 30001:30001 -p 30002:30002 -p 30003:30003 danielwang123321/uf-ubuntu-docker
```

#### 3. Run the xArm robot firmware and UFACTORY Studio

For example, to start the UFACTORY Studio and firmware of xArm 6, run the following inside the container.

```bash
/xarm_scripts/xarm_start.sh 6 6
```

The arguments `6 6` correspond to xArm 6. Change it according to your robot:
*   `5 5`: xArm 5
*   `6 6`: xArm 6
*   `7 7`: xArm 7
*   `6 9`: Lite 6
*   `6 12`: 850

#### 4. Access the UFACTORY Studio web simulation

Open a web browser and go to `http://127.0.0.1:18333` or `http://localhost:18333`.

If a prompt "Unable to get robot SN…" appears, click "Close" to proceed.

#### 5. Connect to the simulator from your code

To connect to the simulated robot from your Python code, use the IP address `127.0.0.1`.

See the example in `examples/docker_simulation_example.py` for simulator usage.

## Quick Start

### Basic Usage

```python
from src.xarm_controller import XArmController

# Create controller with auto-enable (simplest setup)
controller = XArmController(
    gripper_type='bio',    # 'bio', 'standard', 'robotiq', or 'none'
    enable_track=True,     # Enable linear track
    auto_enable=True       # Auto-enable all components
)

# Initialize and connect
if controller.initialize():
    # Move using joint angles
    controller.move_joints([0, -30, 0, 30, 0, 0])
    
    # Move using Cartesian coordinates (linear movement)
    controller.move_to_position(x=300, y=0, z=300)
    
    # Move relative to current position
    controller.move_relative(dx=50, dz=10)
    
    # Control gripper (works with any configured gripper type)
    controller.open_gripper()
    controller.close_gripper()
    
    # Control linear track
    controller.move_track_to_position(100)
    
    # Disconnect when done
    controller.disconnect()
```

### Advanced Usage with Manual Component Control

```python
from src.xarm_controller import XArmController

# Create controller without auto-enabling components
controller = XArmController(
    gripper_type='bio',
    enable_track=True,
    auto_enable=False  # Manual control
)

# Initialize connection only
controller.initialize()

# Check system status
status = controller.get_system_status()
print(f"Connection: {status['connection']['state']}")

# Enable components when ready
if controller.enable_gripper_component():
    print("Gripper ready")

if controller.enable_track_component():
    print("Track ready")

# Check component states
if controller.is_component_enabled('gripper'):
    controller.close_gripper()

# Get error history if needed
errors = controller.get_error_history()
```

### Named Locations

Configure predefined positions in `settings/location_config.yaml`:

```yaml
home:
  x: 300
  y: 0  
  z: 300
  roll: 180
  pitch: 0
  yaw: 0

pickup_position:
  x: 400
  y: 100
  z: 200
  roll: 180
  pitch: 0
  yaw: 0
```

Then use them in code:

```python
controller.move_to_named_location('home')
controller.move_to_named_location('pickup_position')
```

## Configuration

The controller uses YAML configuration files in the `settings/` directory:

- `xarm_config.yaml` - Robot connection and movement parameters
- `bio_gripper_config.yaml` - BIO gripper settings
- `linear_track_config.yaml` - Linear track parameters  
- `location_config.yaml` - Named positions

## Architecture

The `XArmController` provides a unified interface that replaces the previous separate classes:

- **Previous**: `xArm`, `BioGripper`, `LinearTrack` classes
- **New**: Single `XArmController` with integrated functionality
- **Benefits**: Simplified API, better state management, enhanced safety

## Examples

See `examples/docker_simulation_example.py` for a complete demonstration including:

- Component initialization and status checking
- Joint and Cartesian movements  
- Gripper control
- Linear track operation
- Error handling and disconnection
