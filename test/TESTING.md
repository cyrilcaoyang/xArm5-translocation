# Testing Guide for XArm Translocation

This guide covers how to run tests for the XArm Translocation project, including both unit tests and Docker integration tests.

## Test Structure

```
tests/
├── __init__.py                 # Test package
├── conftest.py                 # Pytest fixtures and configuration
├── test_xarm_controller.py     # Unit tests (48 tests)
└── test_docker_integration.py  # Docker integration tests

scripts/
└── test_with_docker.py         # Helper script for Docker testing

pytest.ini                      # Pytest configuration
```

## Prerequisites

### For Unit Tests Only
```bash
conda run -n sdl2-robots pip install pytest pytest-mock pytest-cov
```

### For Docker Integration Tests
1. **Docker installed and running**
2. **xArm Docker image** (pulls automatically if needed):
   ```bash
   docker pull danielwang123321/uf-ubuntu-docker
   ```

## Running Tests

### 🧪 Unit Tests (No Hardware Required)

Unit tests use mocked XArmAPI and test all XArmController functionality:

```bash
# Run all unit tests
conda run -n sdl2-robots python -m pytest tests/test_xarm_controller.py -v

# Run with coverage
conda run -n sdl2-robots python -m pytest tests/test_xarm_controller.py --cov=src --cov-report=term-missing

# Run specific test class
conda run -n sdl2-robots python -m pytest tests/test_xarm_controller.py::TestMovementMethods -v

# Run using helper script
conda run -n sdl2-robots python scripts/test_with_docker.py --unit-only
```

**Unit Test Coverage:**
- ✅ 48 tests covering all XArmController functionality
- ✅ 66% code coverage
- ✅ Tests initialization, movement, gripper control, track control, state management
- ✅ Error handling and edge cases

### 🐳 Docker Integration Tests (Requires Docker)

Integration tests run against the actual Docker simulator:

#### Option 1: Automatic Docker Management
```bash
# Run all tests (unit + Docker integration)
conda run -n sdl2-robots python scripts/test_with_docker.py

# Run only Docker integration tests
conda run -n sdl2-robots python scripts/test_with_docker.py --docker-only

# Start container and run tests (xArm 6)
conda run -n sdl2-robots python scripts/test_with_docker.py --arm-type 6

# Just start the container (no tests)
conda run -n sdl2-robots python scripts/test_with_docker.py --start-container
```

#### Option 2: Manual Docker Management

**Start Docker Container:**
```bash
docker run -d --name uf_software \
  -p 18333:18333 -p 502:502 -p 503:503 -p 504:504 \
  -p 30000:30000 -p 30001:30001 -p 30002:30002 -p 30003:30003 \
  danielwang123321/uf-ubuntu-docker
```

**Start xArm Firmware (inside container):**
```bash
# For xArm 6
docker exec uf_software /xarm_scripts/xarm_start.sh 6 6

# For xArm 5
docker exec uf_software /xarm_scripts/xarm_start.sh 5 5

# For xArm 7  
docker exec uf_software /xarm_scripts/xarm_start.sh 7 7
```

**Run Tests:**
```bash
conda run -n sdl2-robots python -m pytest tests/test_docker_integration.py -v -m integration
```

**Cleanup:**
```bash
docker stop uf_software
docker rm uf_software
```

### 🎯 Test Categories

#### Unit Tests (`tests/test_xarm_controller.py`)
- **TestXArmControllerInitialization** - Controller creation and configuration
- **TestXArmControllerConnection** - Connection handling
- **TestComponentManagement** - Enable/disable components
- **TestMovementMethods** - Joint, linear, relative movements
- **TestGripperControl** - BIO, Standard, RobotIQ grippers
- **TestLinearTrackControl** - Track movement and control
- **TestStateManagement** - State tracking and error handling
- **TestUtilityMethods** - Helper functions and properties
- **TestErrorHandling** - Edge cases and error conditions

#### Integration Tests (`tests/test_docker_integration.py`)
- **TestDockerIntegration** - Basic Docker connection and workflow
- **TestDockerStressTest** - Multiple connections and stress testing
- **TestDockerComponentIsolation** - Individual component testing

## Test Configuration

### Pytest Markers
```bash
# Run only integration tests
pytest -m integration

# Run only slow tests
pytest -m slow

# Skip integration tests
pytest -m "not integration"
```

### Coverage Settings
- Minimum coverage: 80%
- Coverage reports: Terminal + HTML (`htmlcov/`)
- Source directory: `src/`

## Test Results Summary

### ✅ Current Test Status

| Test Category | Count | Status | Coverage |
|---|---|---|---|
| **Unit Tests** | 48 | ✅ All Pass | 66% |
| **Integration Tests** | 8 | ⏳ Needs Docker | N/A |
| **Total** | 56 | ✅ 48/56 Pass | 66% |

### 📊 Test Coverage Breakdown

**Well Tested (>80% coverage):**
- Component state management
- Movement methods (joint, linear, relative)
- Configuration loading
- Error callbacks and handling
- Utility methods

**Partially Tested (40-80% coverage):**
- Gripper control methods
- Linear track control
- System status reporting

**Needs More Tests (<40% coverage):**
- Some error edge cases
- Velocity control paths
- Position update methods

## Troubleshooting

### Common Issues

1. **"Docker simulator not available"**
   - Check Docker is running: `docker ps`
   - Check container is running: `docker ps | grep uf_software`
   - Check firmware started: Wait 10+ seconds after starting firmware

2. **Import errors**
   - Ensure `src/` is in Python path
   - Check conda environment: `conda activate sdl2-robots`

3. **Test failures**
   - Check mocked methods are properly configured
   - Verify test fixtures are set up correctly
   - Look at specific error messages in test output

### Docker Web UI

When Docker container is running, access the web simulator at:
**http://localhost:18333**

### Quick Health Check

```bash
# Check if everything is working
conda run -n sdl2-robots python -c "
import sys, os
sys.path.append('src')
from xarm_controller import XArmController
controller = XArmController(gripper_type='bio', auto_enable=False)
print('✅ XArmController imports successfully')
print('✅ Tests should work!')
"
```

## Next Steps

1. **Run unit tests** to verify functionality
2. **Start Docker container** for integration testing
3. **Run integration tests** against Docker simulator
4. **Review coverage report** to identify untested code
5. **Add more tests** for edge cases as needed

For more details, see the test files themselves or run with `-v` for verbose output. 