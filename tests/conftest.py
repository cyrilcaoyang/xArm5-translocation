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
    """Mock XArmAPI for testing without hardware."""
    mock_arm = Mock()
    mock_arm.connected = False
    mock_arm.error_code = 0
    mock_arm.warn_code = 0
    mock_arm.state = 0
    mock_arm.mode = 0
    
    # Mock connection methods
    mock_arm.connect.return_value = None
    mock_arm.disconnect.return_value = None
    
    # Mock movement methods
    mock_arm.set_servo_angle.return_value = 0
    mock_arm.set_position.return_value = 0
    mock_arm.move_gohome.return_value = 0
    mock_arm.vc_set_cartesian_velocity.return_value = 0
    mock_arm.vc_set_joint_velocity.return_value = 0
    
    # Mock position methods
    mock_arm.get_position.return_value = [0, [300, 0, 300, 180, 0, 0]]
    mock_arm.get_servo_angle.return_value = [0, [0, 0, 0, 0, 0, 0]]
    
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
    
    # Mock linear track methods
    mock_arm.set_linear_track_enable.return_value = 0
    mock_arm.set_linear_track_speed.return_value = 0
    mock_arm.set_linear_track_pos.return_value = 0
    mock_arm.get_linear_track_pos.return_value = [0, 0]
    
    # Mock state management methods
    mock_arm.clean_warn.return_value = None
    mock_arm.clean_error.return_value = None
    mock_arm.motion_enable.return_value = None
    mock_arm.set_mode.return_value = None
    mock_arm.set_state.return_value = None
    mock_arm.emergency_stop.return_value = None
    mock_arm.register_error_warn_changed_callback.return_value = None
    mock_arm.register_state_changed_callback.return_value = None
    
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
def initialized_controller(controller_no_auto_enable, mock_xarm_api, monkeypatch):
    """Create an initialized controller with mocked arm."""
    # Mock XArmAPI constructor to return our mock
    def mock_xarm_api_constructor(*args, **kwargs):
        mock_xarm_api.connected = True
        return mock_xarm_api
    
    monkeypatch.setattr('core.xarm_controller.XArmAPI', mock_xarm_api_constructor)
    
    # Initialize the controller
    success = controller_no_auto_enable.initialize()
    assert success, "Controller initialization should succeed"
    
    return controller_no_auto_enable 