# xArm Docker Simulator

This directory contains tools to set up and manage the UFACTORY xArm Docker simulator for development and testing.

## Overview

The Docker simulator provides a virtual xArm robot environment that allows you to:
- Test robot control code without physical hardware
- Develop and debug applications safely
- Practice robot programming
- Run demos and examples

## Quick Start

### Prerequisites
- Docker installed and running on your system
- Internet connection (for initial setup)

### Basic Usage

1. **Start the simulator:**
   ```bash
   ./docker_setup.sh start
   ```
   This starts an xArm6 simulator by default.

2. **Start with specific arm type:**
   ```bash
   ./docker_setup.sh start 5    # xArm5 (5 joints)
   ./docker_setup.sh start 6    # xArm6 (6 joints) 
   ./docker_setup.sh start 7    # xArm7 (7 joints)
   ```

3. **Check simulator status:**
   ```bash
   ./docker_setup.sh status
   ```

4. **Stop the simulator:**
   ```bash
   ./docker_setup.sh stop
   ```

## Accessing the Simulator

Once running, you can access the simulator:

- **Web UI**: http://localhost:18333
- **SDK Connection**: Use IP address `127.0.0.1` in your Python scripts
- **Default Ports**: 18333, 502-504, 30000-30003

## Example Usage in Code

```python
from xarm.wrapper import XArmAPI

# Connect to simulator
arm = XArmAPI('127.0.0.1')
arm.connect()

# Your robot control code here
arm.set_position([300, 0, 400, 180, 0, 0])

arm.disconnect()
```

## Files

- `docker_setup.sh` - Main setup script for managing the Docker simulator
- `README.md` - This documentation file

## Troubleshooting

- **Docker not found**: Make sure Docker is installed and running
- **Port conflicts**: Stop other services using ports 18333, 502-504, or 30000-30003
- **Connection issues**: Wait 10-15 seconds after starting for the simulator to fully initialize
- **Permission errors**: You may need to run with `sudo` on some systems

## Commands Reference

| Command | Description |
|---------|-------------|
| `start [5\|6\|7]` | Start simulator with specified arm type |
| `stop` | Stop and remove simulator container |
| `status` | Show current simulator status |
| `help` | Show available commands |

For more advanced usage and troubleshooting, refer to the UFACTORY documentation. 