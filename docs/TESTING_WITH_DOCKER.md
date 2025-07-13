# Testing with Docker and the UFACTORY Simulator

This document provides comprehensive instructions for running integration tests against the official UFACTORY xArm simulator using Docker. You can choose to run the simulator either locally on your development machine or on a remote Linux server.

The UFACTORY simulator provides a realistic testing environment without requiring physical hardware, making it ideal for development, CI/CD pipelines, and automated testing.

---

## Option 1: Local Docker Testing

This approach runs the Docker simulator directly on your local development machine. This is the simplest setup and works well for development and debugging.

### Prerequisites

- Docker installed and running on your local machine
- Python 3.8+ with the project dependencies installed

### Setup Steps

1. **Pull the Docker Image**
   ```bash
   docker pull danielwang123321/uf-ubuntu-docker
   ```

2. **Start the Simulator Container**
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

3. **Initialize the xArm Firmware**
   Choose your robot model and start the firmware:
   ```bash
   # For xArm 5
   docker exec uf_software /xarm_scripts/xarm_start.sh 5 5
   
   # For xArm 6
   docker exec uf_software /xarm_scripts/xarm_start.sh 6 6
   
   # For xArm 7
   docker exec uf_software /xarm_scripts/xarm_start.sh 7 7
   ```
   
   Wait 10-15 seconds for the firmware to fully initialize.

4. **Run Your Tests**
   The simulator is now accessible at `localhost`. Run your integration tests:
   ```bash
   # Run all integration tests
   pytest test/ -m integration -v
   
   # Run specific test file
   pytest test/test_docker_integration.py -v
   ```

5. **Using the Automated Script**
   Alternatively, you can use the provided test script that handles the entire workflow:
   ```bash
   python test/test_with_docker.py --arm-type 6
   ```

### Web Interface

The simulator also provides a web interface accessible at:
- **Web UI**: http://localhost:18333

---

## Option 2: Remote Docker Testing

This approach runs the simulator on a remote Linux server (e.g., accessed via Tailscale) while you develop and test from your local machine. This is ideal for teams, CI/CD systems, or when you want to keep your local environment clean.

### Prerequisites

- A remote Linux server with Docker installed
- Network access to the remote server (e.g., via Tailscale, VPN, or direct network access)
- Python 3.8+ with project dependencies installed locally

### Part A: On Your Remote Linux Server

These steps are performed once on your remote server:

1. **Pull the Docker Image**
   ```bash
   docker pull danielwang123321/uf-ubuntu-docker
   ```

2. **Start the Simulator Container**
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

3. **Initialize the xArm Firmware**
   ```bash
   # Choose your robot model (5, 6, or 7)
   docker exec uf_software /xarm_scripts/xarm_start.sh 6 6
   ```
   
   Wait 10-15 seconds for initialization. Your remote server is now running the simulator.

### Part B: On Your Local Development Machine

1. **Install Dependencies Locally**
   ```bash
   # Create and activate a virtual environment
   python -m venv .venv
   
   # On Windows
   .venv\Scripts\activate
   
   # On macOS/Linux
   source .venv/bin/activate
   
   # Install dependencies
   pip install -e .[dev]
   ```

2. **Test Connection with a Script**
   Create a test script to verify connectivity:
   ```python
   # test_remote_connection.py
   from src.core.xarm_controller import XArmController
   
   # Replace with your server's IP address
   REMOTE_IP = "100.64.254.xxx"  # Your Tailscale IP
   
   controller = XArmController(host=REMOTE_IP)
   
   if controller.initialize():
       print("✅ Successfully connected to remote xArm simulator!")
       print(f"Robot model: {controller.get_model()}")
       print(f"Status: {controller.get_system_status()}")
       controller.disconnect()
   else:
       print("❌ Failed to connect to remote xArm simulator.")
   ```

3. **Run Integration Tests Against Remote Simulator**
   Set the remote IP and run your tests:
   
   **Windows (Command Prompt):**
   ```cmd
   set XARM_HOST_IP=100.64.254.xxx
   pytest test/ -m integration -v
   ```
   
   **Windows (PowerShell):**
   ```powershell
   $env:XARM_HOST_IP="100.64.254.xxx"
   pytest test/ -m integration -v
   ```
   
   **macOS/Linux:**
   ```bash
   export XARM_HOST_IP=100.64.254.xxx
   pytest test/ -m integration -v
   ```

### Remote Web Interface

When using a remote server, the web interface is accessible at:
- **Web UI**: http://YOUR_SERVER_IP:18333

---

## Cleaning Up

### Local Docker
```bash
docker stop uf_software
docker rm uf_software
```

### Remote Docker
On your remote server:
```bash
docker stop uf_software
docker rm uf_software
```

---

## Troubleshooting

### Connection Issues
- **Local**: Ensure Docker is running and ports aren't blocked by firewall
- **Remote**: Verify network connectivity and that ports 18333, 502-504, and 30000-30003 are accessible

### Simulator Not Responding
- Wait longer for firmware initialization (up to 30 seconds)
- Check container logs: `docker logs uf_software`
- Restart the firmware: `docker exec uf_software /xarm_scripts/xarm_start.sh 6 6`

### Test Failures
- Verify the simulator is running: `docker ps`
- Check if the correct robot model is configured in your tests
- Ensure the `XARM_HOST_IP` environment variable is set correctly for remote testing

---

## Advanced Usage

### Running Specific Test Suites
```bash
# Run only unit tests (no Docker required)
python test/test_with_docker.py --unit-only

# Run only Docker integration tests
python test/test_with_docker.py --docker-only

# Start container and leave it running for manual testing
python test/test_with_docker.py --start-container --no-cleanup
```

### Multiple Robot Models
You can test different robot models by changing the firmware initialization:
```bash
# Test with different models
docker exec uf_software /xarm_scripts/xarm_start.sh 5 5  # xArm 5
docker exec uf_software /xarm_scripts/xarm_start.sh 6 6  # xArm 6
docker exec uf_software /xarm_scripts/xarm_start.sh 7 7  # xArm 7
```

This comprehensive Docker testing setup provides a robust foundation for developing and testing xArm applications in a controlled, repeatable environment. 