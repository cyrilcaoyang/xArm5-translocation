# xArm Translocation Control

A comprehensive Python package for controlling UFACTORY xArm robotic arms with integrated gripper and linear track support. Features unified control, multiple simulation modes, and a professional three-stage testing strategy.

## ✨ Key Features

- **Multi-Model Support**: xArm5, xArm6, xArm7, and xArm850 with auto-detection
- **Unified Control**: Single controller for arm, gripper, and linear track
- **Multiple Simulation Modes**: Software simulation with collision detection + Docker simulation with 3D physics
- **Professional Testing Strategy**: Three-stage methodology from simulation to production
- **REST API**: FastAPI server for web-based control and monitoring
- **Flexible Configuration**: Model-specific configs with component auto-enable

## 🚀 Quick Start

### Installation
```bash
# Install dependencies
conda run -n sdl2-robots pip install fastapi uvicorn websockets

# Install xArm Python SDK (for real hardware)
git clone https://github.com/xArm-Developer/xArm-Python-SDK.git
cd xArm-Python-SDK && python setup.py install
```

### Basic Usage
```python
from src.xarm_controller import XArmController

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

# Run Docker simulation (after starting container)
src/docker/docker_setup.sh start 7
python src/examples/demo_docker_sim.py
```

For detailed instructions on simulation and hardware setup, see the [Simulation README](src/settings/README_SIMULATION.md).

### API Server
```bash
# Start REST API server
conda run -n sdl2-robots python src/xarm_api_server.py

# Access API documentation
# http://localhost:6001/docs
```

## 🎯 Three-Stage Testing Strategy

1. **Software Simulation** → Logic validation, error handling, collision detection
2. **Docker Simulation** → Physics validation, 3D visualization, realistic dynamics  
3. **Real Hardware** → Production validation, safety systems, performance optimization

## 📚 Documentation

For detailed guides on specific topics, please see the `docs/` directory:

-   **[Features Overview](./docs/FEATURES.md)**: A high-level overview of the controller's features.
-   **[API Reference](./docs/API_REFERENCE.md)**: Detailed documentation of the `XArmController` methods and parameters.
-   **[Simulation & Testing Guide](./docs/SIMULATION_TESTING.md)**: A comprehensive guide to simulation modes and the project's testing strategy.

## 🔧 Advanced Features

- **Multi-gripper support**: BIO, Standard, RobotIQ, or none
- **Named locations**: Predefined positions with easy recall
- **Real-time monitoring**: WebSocket updates and status tracking
- **Error handling**: Comprehensive error history and recovery
- **Remote deployment**: Docker containers on web servers
- **Configuration**: All settings are now in `src/settings/`. Modify the `.yaml` files to match your hardware.
- **Examples**: Run demo scripts in `src/examples/` to see different functionalities.
- **API Server**: Start the web server with `uvicorn src.xarm_api_server:app --reload`.

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
- **Documentation**: Check `docs/` directory for comprehensive guides
- **Examples**: Run demo scripts in `src/examples/`
- **API**: Access interactive docs at `http://localhost:6001/docs`

---

**Get started in minutes with our three-stage testing strategy - from safe simulation to production deployment!**
