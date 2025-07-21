# PyxArm - xArm Robot Control Package

A comprehensive Python package for controlling UFACTORY xArm robotic arms with integrated gripper, linear track, and force torque sensor support. Features unified control, multiple simulation modes, and a professional three-stage testing strategy.

## ✨ Key Features

- **Multi-Model Support**: xArm5, xArm6, xArm7, and xArm850 with auto-detection
- **Unified Control**: Single controller for arm, gripper, linear track, and force torque sensor
- **Multiple Simulation Modes**: Software simulation with collision detection + Docker simulation with 3D physics
- **Professional Testing Strategy**: Three-stage methodology from simulation to production
- **REST API**: FastAPI server for web-based control and monitoring
- **Flexible Configuration**: Model-specific configs with component auto-enable
- **6-Axis Force Torque Sensor**: Safety monitoring, force-controlled movement, and torque-controlled joint operations

## 🚀 Quick Start

### Installation
```bash
# Prepare and activate your python enviroment, and install PyxArm in editable mode
pip install -e .

# Or, install PyxArm in development mode with pytests
pip install -e ".[dev]"
```

### Basic Usage
```python
from src.core.xarm_controller import XArmController

# Auto-detect and connect
controller = XArmController(
    gripper_type='bio',
    enable_track=True,
    auto_enable=True
)

if controller.initialize():
    # Move robot
    controller.move_to_position(x=300, y=0, z=300)
    controller.open_gripper()
    controller.disconnect()
```

### Simulation Modes
```bash
# Run software simulation
python src/examples/demo_software_sim.py

# Run Docker simulation (after starting container, in this case "5" for xArm5)
src/docker/docker_setup.sh start 5
python src/examples/demo_docker_sim.py

# Run force torque sensor demo
python src/examples/demo_force_torque.py --simulation
```

For detailed instructions on simulation and hardware setup, see the [Simulation README](src/docs/PYXARM_TESTING.md).

### Web Interface & API Server
```bash
# Start web interface and API server
pyxarm web

# Or specify custom host/port
pyxarm web --host 0.0.0.0 --port 8000

# Alternative method (without installing package)
python -m src.cli.main web
```

**Access Points:**
- 🌐 **Web UI**: http://localhost:6001/web/
- 📖 **API Docs**: http://localhost:6001/docs  
- 📡 **API Server**: http://localhost:6001

## 💻 Command Line Interface

PyxArm includes a convenient command-line interface:

```bash
# Show help
pyxarm --help

# Start web interface
pyxarm web

# Start on custom host/port
pyxarm web --host 127.0.0.1 --port 8080

# Show version
pyxarm --version
```

## 🎯 Three-Stage Testing Strategy

1. **Software Simulation** → Logic validation, error handling, collision detection
2. **Docker Simulation** → Physics validation, 3D visualization, realistic dynamics  
3. **Real Hardware** → Production validation, safety systems, performance optimization

## 📚 Documentation

For detailed guides on specific topics, please see the project root:

-   **[Features Overview](./src/docs/PYXARM_FEATURES.md)**: A high-level overview of the controller's features.
-   **[API Reference](./src/docs/PYXARM_API.md)**: Detailed documentation of the `XArmController` methods and parameters.
-   **[Simulation & Testing Guide](./src/docs/PYXARM_TESTING.md)**: A comprehensive guide to simulation modes and the project's testing strategy.

## 🔧 Advanced Features

- **Multi-gripper support**: BIO, Standard, RobotIQ, or none
- **Named locations**: Predefined positions with easy recall
- **Real-time monitoring**: WebSocket updates and status tracking
- **Error handling**: Comprehensive error history and recovery
- **Remote deployment**: Docker containers on web servers
- **Configuration**: All settings are now in `src/settings/`. Modify the `.yaml` files to match your hardware.
- **Examples**: Run demo scripts in `src/examples/` to see different functionalities.
- **API Server**: Start the web server with `pyxarm web` or `uvicorn src.core.xarm_api_server:app --reload`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass: `pytest`
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Create GitHub issues for bugs and feature requests
- **Documentation**: Check root directory for comprehensive guides
- **Examples**: Run demo scripts in `src/examples/`
- **CLI**: Use `pyxarm --help` for command-line interface
- **API**: Access interactive docs at `http://localhost:6001/docs`

---

**Get started in minutes with our three-stage testing strategy - from safe simulation to production deployment!**
