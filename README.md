# xArm Translocation Control

A comprehensive Python package for controlling UFACTORY xArm robotic arms with integrated gripper and linear track support for translocation tasks. This package provides a unified controller optimized for xArm5 robots with extensible multi-model architecture, supporting multiple gripper types and optional linear track functionality.

## ✨ Features

- ** Multi-Model Architecture**: Designed for xArm5, xArm6, xArm7, and xArm850 with extensible model detection (currently optimized for xArm5)
- ** Unified Control**: Single `XArmController` class manages arm, gripper, and linear track
- ** Multiple Gripper Support**: BIO, Standard, RobotIQ grippers, or no gripper
- ** Movement Types**: Joint, Cartesian/linear, relative, named locations, velocity control
- ** State Management**: Comprehensive component state tracking and error handling
- ** Flexible Configuration**: Model-specific configs with auto-enable or manual component control
- ** Safety Features**: Component validation, error history, position caching
- ** Docker Integration**: Simplified simulator setup with containerized UFACTORY Studio
- ** Demo Suite**: Comprehensive examples for all functionality

## 📁 Project Structure

```
xArm5-translocation/
├── src/
│   └── xarm_controller.py          # Main unified controller
├── users/
│   ├── examples/                   # Demo scripts
│   │   ├── demo_5joints.py         # xArm5 joint testing
│   │   ├── demo_gripper.py         # Gripper functionality
│   │   ├── demo_linear_motor.py    # Linear track operations
│   │   └── demo_docker_sim.py      # Docker simulator demo
│   ├── settings/                   # Configuration files
│   │   ├── xarm5_config.yaml       # xArm5 specific config
│   │   ├── bio_gripper_config.yaml # Gripper settings
│   │   ├── linear_track_config.yaml# Track parameters
│   │   └── location_config.yaml    # Named positions
│   ├── docker/                     # Docker simulator tools
│   │   ├── docker_setup.sh         # Simplified setup script
│   │   └── README.md              # Docker documentation
│   └── manuals/                   # Hardware documentation
│       ├── xArm-Developer-Manual-V1.10.0.pdf
│       └── Linear-Motor-V2.0.04.pdf
├── test/                          # Comprehensive test suite
│   ├── test_xarm_controller.py    # Controller unit tests
│   ├── test_docker_integration.py # Docker integration tests
│   └── TESTING.md                 # Testing documentation
├── pyproject.toml                 # Project & testing configuration
└── README.md                      # This file
```

## 🚀 Installation

### Option 1: With Real Hardware

Install the xArm Python SDK in your environment:

```bash
# Clone and install xArm Python SDK
git clone https://github.com/xArm-Developer/xArm-Python-SDK.git
cd xArm-Python-SDK
python setup.py install

# Install this package
cd /path/to/xArm5-translocation
pip install -e .

# Optional: Install with development tools
pip install -e ".[dev]"        # Includes testing + linting tools
pip install -e ".[test]"       # Just testing dependencies
```

### Option 2: With Docker Simulator (No Hardware Required)

Use the simplified Docker setup for development and testing:

```bash
# Navigate to docker directory
cd users/docker

# Start simulator (xArm6 by default)
./docker_setup.sh start

# Or start specific model
./docker_setup.sh start 5    # xArm5
./docker_setup.sh start 7    # xArm7

# Check status
./docker_setup.sh status

# Stop simulator
./docker_setup.sh stop
```

**Simulator Access:**
- Web UI: http://localhost:18333
- SDK Connection: `127.0.0.1`
- Ports: 18333, 502-504, 30000-30003

See `users/docker/README.md` for detailed Docker setup instructions.

## ⚡ Quick Start

### Basic Usage (Auto-Detection)

```python
from src.xarm_controller import XArmController

# Auto-detect robot model and enable all components
controller = XArmController(
    gripper_type='bio',    # 'bio', 'standard', 'robotiq', or 'none'
    enable_track=True,     # Enable linear track
    auto_enable=True       # Auto-enable all components
)

# Initialize and connect
if controller.initialize():
    print(f"Connected to {controller.model_name} with {controller.num_joints} joints")
    
    # Move using joint angles (adapts to robot model)
    angles = [0] * controller.num_joints  # Zero position for any model
    controller.move_joints(angles)
    
    # Move using Cartesian coordinates
    controller.move_to_position(x=300, y=0, z=300)
    
    # Control gripper
    controller.open_gripper()
    controller.close_gripper()
    
    controller.disconnect()
```

### Specific Model Usage

```python
# Force specific model (loads corresponding config file)
controller = XArmController(
    model=5,              # Loads xarm5_config.yaml
    gripper_type='bio',
    auto_enable=True
)

# Or for xArm850
controller = XArmController(
    model='850',          # Loads xarm850_config.yaml
    gripper_type='bio'
)
```

### Simulator Usage

```python
# Connect to Docker simulator
controller = XArmController(
    config_path='users/settings/',
    model=6               # Match your started simulator
)

# Initialize for simulator (IP: 127.0.0.1 from config)
controller.initialize()

# Run your code - works identically to real hardware
controller.move_joints([0, -30, 0, 30, 0, 0])
```

## 🎯 Demo Scripts

Comprehensive examples in `users/examples/`:

### 1. 5-Joint Testing (`demo_5joints.py`)
```bash
# Test all 5 joints on xArm5
python demo_5joints.py --simulate    # Simulation mode
python demo_5joints.py --real        # Real hardware
```

### 2. Gripper Testing (`demo_gripper.py`)
```bash
# Test gripper functionality
python demo_gripper.py --simulate
python demo_gripper.py --real
```

### 3. Linear Motor Demo (`demo_linear_motor.py`)
```bash
# Test linear track with adaptive joint positioning
python demo_linear_motor.py --simulate
python demo_linear_motor.py --real
```

### 4. Docker Simulator (`demo_docker_sim.py`)
```bash
# Complete simulator demonstration
python demo_docker_sim.py
```

All demos support both simulation and real hardware modes. The `demo_5joints.py` script is specifically optimized for xArm5 robots and has been thoroughly tested.

## ⚙️ Configuration

### Model-Specific Configurations

The controller supports multiple robot models. Currently available configuration:

- `xarm5_config.yaml` - xArm5 (5 joints) - Available
- Additional model configs can be created following the same pattern

Example configuration structure:
```yaml
# Robot model configuration
model: 5              # Robot model number
num_joints: 5         # Number of joints

# Network configuration  
host: '192.168.1.237' # Robot IP address
port: 18333
Tcp_Speed: 100
Tcp_Acc: 2000
Angle_Speed: 20
Angle_Acc: 500
```

### Component Configurations

- `bio_gripper_config.yaml` - BIO gripper settings
- `linear_track_config.yaml` - Linear track parameters
- `location_config.yaml` - Named positions

### Named Locations

Define reusable positions in `location_config.yaml`:

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

Usage:
```python
controller.move_to_named_location('home')
controller.move_to_named_location('pickup_position')
```

## 🧪 Testing

Comprehensive test suite with Docker integration:

```bash
# Run all tests (uses pyproject.toml configuration)
pytest

# Run specific test categories  
pytest test/test_xarm_controller.py      # Unit tests
pytest test/test_docker_integration.py   # Docker integration
pytest test/test_with_docker.py          # Docker functionality

# Run with different markers
pytest -m "not integration"             # Skip integration tests
pytest -m "not docker"                  # Skip Docker tests
pytest -m "not slow"                    # Skip slow tests

# Run with coverage
pytest --cov-report=html

# Install test dependencies
pip install -e ".[test]"                # Just testing
pip install -e ".[dev]"                 # Development tools
```

**Note**: Pytest configuration is in `pyproject.toml` with comprehensive markers and coverage settings.

See `test/TESTING.md` for detailed testing documentation.

## 🏗️ Architecture

### Unified Controller Design

The `XArmController` replaces multiple separate classes with a single, integrated interface:

**Previous Architecture:**
- Separate `xArm`, `BioGripper`, `LinearTrack` classes
- Manual coordination between components
- Model-specific implementations

**Current Architecture:**
- Single `XArmController` with integrated functionality
- Automatic model detection and adaptation
- Unified state management and error handling
- Component-agnostic API

### Multi-Model Support

```python
# Controller designed to support multiple models with identical API
# Currently optimized for xArm5, extensible to other models
controller = XArmController(model=5)  # xArm5 with 5 joints
controller.move_joints([0] * controller.num_joints)  # Adapts to model's joint count
```

### Component States

The controller tracks states for all components:
- `UNKNOWN` - Not yet initialized
- `ENABLING` - Currently being enabled
- `ENABLED` - Ready for use
- `DISABLED` - Intentionally disabled
- `ERROR` - Error state

## 🔧 Advanced Usage

### Manual Component Control

```python
# Disable auto-enable for manual control
controller = XArmController(auto_enable=False)
controller.initialize()  # Only connects, doesn't enable components

# Check status before enabling
status = controller.get_system_status()
print(f"Connection: {status['connection']['state']}")

# Enable components when ready
if controller.enable_gripper_component():
    print("Gripper ready")

if controller.enable_track_component():
    print("Linear track ready")

# Check individual component states
if controller.is_component_enabled('gripper'):
    controller.close_gripper()
```

### Error Handling and Monitoring

```python
# Get comprehensive system status
status = controller.get_system_status()
print(f"Arm: {status['arm']['state']}")
print(f"Gripper: {status['gripper']['state']}")
print(f"Track: {status['track']['state']}")

# Monitor error history
errors = controller.get_error_history(count=5)
for error in errors:
    print(f"Error {error['code']}: {error['message']}")

# Check if robot is responsive
if controller.is_alive:
    print("Robot is responding")
```

### Velocity Control

```python
# Set Cartesian velocities (mm/s, deg/s)
controller.set_cartesian_velocity(vx=50, vy=0, vz=10)

# Set joint velocities (deg/s)
joint_velocities = [10, 0, 0, 0, 0, 0]  # Move only first joint
controller.set_joint_velocity(joint_velocities)

# Stop all motion
controller.stop_motion()
```

## 🐳 Docker Integration

The package includes simplified Docker tools for running UFACTORY Studio simulator:

### Quick Docker Setup

```bash
cd users/docker
./docker_setup.sh start 6    # Start xArm6 simulator
```

### Docker Commands

| Command | Description |
|---------|-------------|
| `start [5\|6\|7]` | Start simulator with specified model |
| `stop` | Stop and remove simulator |
| `status` | Show simulator status |
| `help` | Show available commands |

### Docker Development Workflow

1. **Start simulator**: `./docker_setup.sh start 6`
2. **Develop code**: Use `127.0.0.1` as robot IP
3. **Test with demo**: `python demo_docker_sim.py`
4. **Stop when done**: `./docker_setup.sh stop`

## 📖 Examples and Demos

| Demo | Purpose | Models | Features |
|------|---------|--------|----------|
| `demo_5joints.py` | xArm5 joint testing | xArm5 | Individual joint movements, gripper |
| `demo_gripper.py` | Gripper functionality | xArm5+ | Open/close operations, error handling |
| `demo_linear_motor.py` | Linear track demo | xArm5+ | Track movement, adaptive positioning |
| `demo_docker_sim.py` | Simulator demo | xArm5+ | Complete Docker workflow |

All demos support both `--simulate` and `--real` modes.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check `users/manuals/` for hardware documentation
- **Docker Issues**: See `users/docker/README.md`
- **Testing**: Refer to `test/TESTING.md`
- **Examples**: Run demos in `users/examples/`

## 🔄 Version History

- **v0.2.0**: Enhanced project structure, consolidated pytest config in pyproject.toml, improved dependencies, comprehensive testing framework
- **v0.1.0**: Multi-model support, Docker integration, comprehensive demos  
- **v0.0.1**: Initial unified controller implementation

---

For detailed API documentation and advanced usage examples, explore the demo scripts in `users/examples/`.
