"""
Pytest configuration and fixtures for xarm-translocation tests.
"""

import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add src to path to allow imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.xarm_controller import XArmController, ComponentState


@pytest.fixture
def mock_xarm_api():
    """Create a mock XArmAPI for testing."""
    mock_arm = Mock()
    
    # Mock basic properties
    mock_arm.connected = True
    mock_arm.state = 0
    mock_arm.mode = 0
    mock_arm.error_code = 0
    mock_arm.warn_code = 0
    
    # Mock position and joint methods
    # These will be dynamically adjusted in the `initialized_controller` fixture
    mock_arm.get_position.return_value = (0, [300, 0, 300, 180, 0, 0])
    mock_arm.get_servo_angle.return_value = (0, [0, 0, 0, 0, 0, 0])
    
    # Mock movement methods
    mock_arm.set_servo_angle.return_value = 0
    mock_arm.set_position.return_value = 0
    mock_arm.move_gohome.return_value = 0
    
    # Mock connection and control methods
    mock_arm.connect.return_value = 0
    mock_arm.disconnect.return_value = 0
    mock_arm.clean_warn.return_value = 0
    mock_arm.clean_error.return_value = 0
    mock_arm.motion_enable.return_value = 0
    mock_arm.set_mode.return_value = 0
    mock_arm.set_state.return_value = 0
    mock_arm.emergency_stop.return_value = 0
    mock_arm.register_error_warn_changed_callback.return_value = 0
    mock_arm.register_state_changed_callback.return_value = 0
    
    # Mock gripper methods
    mock_arm.set_bio_gripper_enable.return_value = 0
    mock_arm.open_bio_gripper.return_value = 0
    mock_arm.close_bio_gripper.return_value = 0
    mock_arm.set_gripper_enable.return_value = 0
    mock_arm.set_gripper_position.return_value = 0
    mock_arm.robotiq_reset.return_value = 0
    mock_arm.robotiq_set_activate.return_value = 0
    mock_arm.robotiq_set_position.return_value = 0
    mock_arm.robotiq_open.return_value = 0
    mock_arm.robotiq_close.return_value = 0
    
    # Mock linear track methods - return proper codes, not tuples
    mock_arm.set_linear_track_enable.return_value = 0
    mock_arm.set_linear_track_speed.return_value = 0
    mock_arm.set_linear_track_pos.return_value = 0
    mock_arm.get_linear_track_pos.return_value = (0, 0)
    
    # Mock velocity control methods
    mock_arm.vc_set_cartesian_velocity.return_value = 0
    mock_arm.vc_set_joint_velocity.return_value = 0
    mock_arm.set_only_check_type.return_value = 0

    # Add attributes for predictive maintenance
    mock_arm.temperatures = [30.0] * 8
    mock_arm.joints_torque = [0.0] * 8
    mock_arm.currents = [0.0] * 8
    
    return mock_arm


@pytest.fixture
def test_config_path(tmp_path):
    """Create temporary config files for testing."""
    config_dir = tmp_path / "test_settings"
    config_dir.mkdir()
    
    # Create test configuration files
    xarm_config = {
        'host': '127.0.0.1',
        'port': 502,
        'Tcp_Speed': 100,
        'Tcp_Acc': 2000,
        'Angle_Speed': 20,
        'Angle_Acc': 500
    }
    
    bio_gripper_config = {
        'GRIPPER_SPEED': 300
    }
    
    location_config = {
        'home': {'x': 300, 'y': 0, 'z': 300, 'roll': 180, 'pitch': 0, 'yaw': 0},
        'pickup': {'x': 400, 'y': 100, 'z': 200, 'roll': 180, 'pitch': 0, 'yaw': 0}
    }
    
    track_config = {
        'Speed': 200,
        'Acc': 1000
    }
    
    import yaml
    
    with open(config_dir / "xarm_config.yaml", 'w') as f:
        yaml.dump(xarm_config, f)
    
    with open(config_dir / "bio_gripper_config.yaml", 'w') as f:
        yaml.dump(bio_gripper_config, f)
        
    with open(config_dir / "location_config.yaml", 'w') as f:
        yaml.dump(location_config, f)
        
    with open(config_dir / "linear_track_config.yaml", 'w') as f:
        yaml.dump(track_config, f)
    
    return str(config_dir) + "/"


@pytest.fixture
def controller_no_auto_enable(test_config_path):
    """Create XArmController with auto_enable=False for testing."""
    return XArmController(
        config_path=test_config_path,
        gripper_type='bio',
        enable_track=True,
        auto_enable=False
    )


@pytest.fixture
def controller_auto_enable(test_config_path):
    """Create XArmController with auto_enable=True for testing."""
    return XArmController(
        config_path=test_config_path,
        gripper_type='bio',
        enable_track=True,
        auto_enable=True
    )


@pytest.fixture
def initialized_controller(test_config_path, mock_xarm_api, monkeypatch):
    """Create an initialized controller with a mocked arm instance."""

    # This fixture is critical. It patches the XArmAPI class so that any
    # instance created will be our mock instance. This prevents any test
    # from accidentally trying to connect to a real robot.
    
    # We patch the class constructor to always return our mock.
    monkeypatch.setattr('core.xarm_controller.XArmAPI', lambda *args, **kwargs: mock_xarm_api)
    
    # Create the controller AFTER the patch is applied.
    # auto_enable=False is important for manual initialization
    controller = XArmController(
        config_path=test_config_path,
        gripper_type='bio',
        enable_track=True,
        auto_enable=False  # We initialize it manually here
    )

    # Dynamically set the mock's joint count based on the controller's model
    mock_xarm_api.get_servo_angle.return_value = (0, [0] * controller.num_joints)
    mock_xarm_api.temperatures = [30.0] * controller.num_joints
    mock_xarm_api.joints_torque = [0.0] * controller.num_joints
    mock_xarm_api.currents = [0.0] * controller.num_joints

    # Now, we can safely initialize the controller.
    success = controller.initialize()
    
    # We must assert success here, as any test using this fixture depends on it.
    assert success, "Mocked controller initialization failed. This is a fixture error."
    
    return controller 