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
# Software simulation (instant, collision detection)
python users/examples/demo_software_sim.py

# Docker simulation (3D physics, visual)
users/docker_setup.sh start 7
python users/examples/demo_docker_sim.py
```

### API Server
```bash
# Start REST API server
conda run -n sdl2-robots python src/xarm_api_server.py

# Access API documentation
# http://localhost:6001/docs
```

## �� Project Structure

```
xarm-translocation/
├── src/
│   ├── xarm_controller.py          # Main unified controller
│   └── xarm_api_server.py          # FastAPI REST server
├── users/
│   ├── examples/                   # Demo scripts
│   │   ├── demo_software_sim.py    # Software simulation
│   │   └── demo_docker_sim.py      # Docker simulation
│   ├── settings/                   # Configuration files
│   └── docker_setup.sh             # Docker simulator setup
└── docs/                          # Comprehensive documentation
```

## 🎯 Three-Stage Testing Strategy

1. **Software Simulation** → Logic validation, error handling, collision detection
2. **Docker Simulation** → Physics validation, 3D visualization, realistic dynamics  
3. **Real Hardware** → Production validation, safety systems, performance optimization

## 📚 Documentation

- **[API_REFERENCE.md](docs/API_REFERENCE.md)** - FastAPI server endpoints and usage

## 🔧 Advanced Features

- **Multi-gripper support**: BIO, Standard, RobotIQ, or none
- **Named locations**: Predefined positions with easy recall
- **Real-time monitoring**: WebSocket updates and status tracking
- **Error handling**: Comprehensive error history and recovery
- **Remote deployment**: Docker containers on web servers

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
- **Examples**: Run demo scripts in `users/examples/`
- **API**: Access interactive docs at `http://localhost:6001/docs`

---

**Get started in minutes with our three-stage testing strategy - from safe simulation to production deployment!**
