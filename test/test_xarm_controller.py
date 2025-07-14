"""
Tests for XArmController class.

This test suite covers the comprehensive features of the enhanced XArmController
including simulation mode, safety systems, performance monitoring, error recovery,
and the new streamlined API.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Ensure src is in the python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from core.xarm_controller import XArmController, ComponentState
from core.xarm_utils import SafetyLevel


@pytest.fixture
def simulation_controller(test_config_path):
    """Create a simulation mode controller for testing without hardware."""
    return XArmController(
        config_path=test_config_path,
        simulation_mode=True,
        auto_enable=False,
        gripper_type='bio',
        enable_track=True
    )


@pytest.fixture
def hardware_controller(test_config_path):
    """Create a hardware mode controller for testing with mocks."""
    return XArmController(
        config_path=test_config_path,
        simulation_mode=False,
        auto_enable=False,
        gripper_type='bio',
        enable_track=True
    )


class TestXArmControllerInitialization:
    """Test XArmController initialization and configuration."""

    def test_simulation_mode_creation(self, simulation_controller):
        """Test creating controller in simulation mode."""
        controller = simulation_controller
        assert controller.simulation_mode is True
        assert controller.arm is not None
        assert controller.gripper_type == 'bio'
        assert controller.enable_track is True

    def test_hardware_mode_creation(self, hardware_controller):
        """Test creating controller in hardware mode."""
        controller = hardware_controller
        assert controller.simulation_mode is False
        assert controller.arm is not None
        assert controller.gripper_type == 'bio'
        assert controller.enable_track is True

    def test_auto_enable_functionality(self, test_config_path):
        """Test auto_enable functionality."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            auto_enable=True
        )
        # In simulation mode, auto_enable should work
        assert controller.get_component_states()['connection'] == 'enabled'

    def test_config_loading(self, simulation_controller):
        """Test configuration loading."""
        controller = simulation_controller
        # Check that configs are loaded (even if defaults)
        assert hasattr(controller, 'xarm_config')
        assert hasattr(controller, 'gripper_config')
        assert hasattr(controller, 'track_config')
        assert hasattr(controller, 'location_config')

    def test_safety_level_configuration(self, test_config_path):
        """Test safety level configuration."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            safety_level=SafetyLevel.HIGH
        )
        assert controller.safety_level == SafetyLevel.HIGH

    def test_model_detection(self, simulation_controller):
        """Test model detection and joint count."""
        controller = simulation_controller
        assert controller.model in [5, 6, 7, 850]
        assert controller.num_joints > 0


class TestSimulationMode:
    """Test simulation mode specific functionality."""

    def test_simulation_initialization(self, simulation_controller):
        """Test simulation mode initialization."""
        controller = simulation_controller
        success = controller.initialize()
        assert success is True
        assert controller.states['connection'] == ComponentState.ENABLED

    def test_simulation_arm_methods(self, simulation_controller):
        """Test simulation arm methods are available."""
        controller = simulation_controller
        controller.initialize()
        
        # Test that simulation arm methods exist
        assert hasattr(controller.arm, 'connect')
        assert hasattr(controller.arm, 'get_position')
        assert hasattr(controller.arm, 'get_servo_angle')
        assert hasattr(controller.arm, 'set_servo_angle')

    def test_simulation_movement(self, simulation_controller):
        """Test movement in simulation mode."""
        controller = simulation_controller
        controller.initialize()
        
        # Test joint movement
        success = controller.move_joints([0, 0, 0, 0, 0, 0, 0], speed=50)
        assert success is True

    def test_simulation_gripper_control(self, simulation_controller):
        """Test gripper control in simulation mode."""
        controller = simulation_controller
        controller.initialize()
        controller.enable_gripper_component()
        
        success = controller.open_gripper()
        assert success is True
        
        success = controller.close_gripper()
        assert success is True

    def test_simulation_track_control(self, simulation_controller):
        """Test track control in simulation mode."""
        controller = simulation_controller
        controller.initialize()
        controller.enable_track_component()
        
        success = controller.move_track_to_position(100)
        assert success is True


class TestHardwareMode:
    """Test hardware mode functionality with mocks."""

    def test_hardware_initialization_success(self, initialized_controller):
        """Test successful hardware initialization."""
        controller = initialized_controller
        assert controller.states['connection'] == ComponentState.ENABLED
        assert controller.is_alive is True

    def test_hardware_initialization_failure(self, hardware_controller):
        """Test hardware initialization failure handling."""
        # Mock arm to simulate connection failure
        with patch.object(hardware_controller.arm, 'connect', return_value=1):
            success = hardware_controller.initialize()
            assert success is False

    def test_hardware_disconnect(self, initialized_controller):
        """Test hardware disconnection."""
        controller = initialized_controller
        controller.disconnect()
        assert controller.states['connection'] == ComponentState.DISABLED


class TestComponentManagement:
    """Test component enable/disable functionality."""

    def test_enable_gripper_component(self, initialized_controller):
        """Test enabling gripper component."""
        controller = initialized_controller
        success = controller.enable_gripper_component()
        assert success is True
        assert controller.states['gripper'] == ComponentState.ENABLED

    def test_enable_track_component(self, initialized_controller):
        """Test enabling track component."""
        controller = initialized_controller
        success = controller.enable_track_component()
        assert success is True
        assert controller.states['track'] == ComponentState.ENABLED

    def test_disable_gripper_component(self, initialized_controller):
        """Test disabling gripper component."""
        controller = initialized_controller
        controller.enable_gripper_component()
        success = controller.disable_gripper_component()
        assert success is True
        assert controller.states['gripper'] == ComponentState.DISABLED

    def test_disable_track_component(self, initialized_controller):
        """Test disabling track component."""
        controller = initialized_controller
        controller.enable_track_component()
        success = controller.disable_track_component()
        assert success is True
        assert controller.states['track'] == ComponentState.DISABLED

    def test_component_state_checking(self, initialized_controller):
        """Test component state checking methods."""
        controller = initialized_controller
        
        # Test component state retrieval
        states = controller.get_component_states()
        assert isinstance(states, dict)
        assert 'connection' in states
        assert 'arm' in states
        assert 'gripper' in states
        assert 'track' in states


class TestEnhancedMovementMethods:
    """Test enhanced movement methods with safety features."""

    def test_move_to_position_with_collision_detection(self, initialized_controller):
        """Test move_to_position with collision detection."""
        controller = initialized_controller
        
        success = controller.move_to_position(
            x=300, y=0, z=300, 
            roll=180, pitch=0, yaw=0,
            check_collision=True
        )
        assert success is True

    def test_move_joints_with_safety_validation(self, simulation_controller):
        """Test move_joints with safety validation."""
        controller = simulation_controller
        controller.initialize()
        
        # Test valid joint angles
        success = controller.move_joints([0, 0, 0, 0, 0, 0, 0], check_collision=True)
        assert success is True

    def test_move_to_named_location(self, simulation_controller):
        """Test move_to_named_location method."""
        controller = simulation_controller
        controller.initialize()
        
        # Test with an actual location from the config
        success = controller.move_to_named_location('ROBOT_HOME')
        assert success is True

    def test_move_relative(self, initialized_controller):
        """Test relative movement."""
        controller = initialized_controller
        
        success = controller.move_relative(dx=10, dy=0, dz=0)
        assert success is True

    def test_move_single_joint(self, initialized_controller):
        """Test single joint movement."""
        controller = initialized_controller
        
        success = controller.move_single_joint(joint_id=0, angle=10)
        assert success is True

    def test_go_home_enhanced(self, initialized_controller):
        """Test enhanced go_home method."""
        controller = initialized_controller
        
        success = controller.go_home()
        assert success is True

    def test_velocity_control(self, initialized_controller):
        """Test velocity control methods."""
        controller = initialized_controller
        
        # Test Cartesian velocity
        success = controller.set_cartesian_velocity(vx=10, vy=0, vz=0)
        assert success is True
        
        # Test joint velocity
        success = controller.set_joint_velocity([10, 0, 0, 0, 0, 0, 0])
        assert success is True

    def test_stop_motion(self, initialized_controller):
        """Test emergency stop functionality."""
        controller = initialized_controller
        
        success = controller.stop_motion()
        assert success is True


class TestUniversalGripperControl:
    """Test universal gripper control system."""

    def test_bio_gripper_control(self, initialized_controller):
        """Test bio gripper control."""
        controller = initialized_controller
        controller.enable_gripper_component()
        
        success = controller.open_gripper()
        assert success is True
        
        success = controller.close_gripper()
        assert success is True

    def test_standard_gripper_control(self, test_config_path):
        """Test standard gripper control."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            gripper_type='standard'
        )
        controller.initialize()
        controller.enable_gripper_component()
        
        success = controller.open_gripper()
        assert success is True

    def test_robotiq_gripper_control(self, test_config_path):
        """Test Robotiq gripper control."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            gripper_type='robotiq'
        )
        controller.initialize()
        controller.enable_gripper_component()
        
        success = controller.open_gripper()
        assert success is True

    def test_no_gripper_configured(self, test_config_path):
        """Test behavior when no gripper is configured."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            gripper_type='none'
        )
        controller.initialize()
        
        assert controller.has_gripper() is False


class TestLinearTrackControl:
    """Test linear track control functionality."""

    def test_track_movement_with_validation(self, initialized_controller):
        """Test track movement with validation."""
        controller = initialized_controller
        controller.enable_track_component()
        
        success = controller.move_track_to_position(100)
        assert success is True

    def test_track_speed_setting(self, initialized_controller):
        """Test track speed setting."""
        controller = initialized_controller
        controller.enable_track_component()
        
        success = controller.set_track_speed(50)
        assert success is True

    def test_track_reset(self, initialized_controller):
        """Test track reset functionality."""
        controller = initialized_controller
        controller.enable_track_component()
        
        success = controller.reset_track()
        assert success is True

    def test_track_position_retrieval(self, initialized_controller):
        """Test track position retrieval."""
        controller = initialized_controller
        controller.enable_track_component()
        
        position = controller.get_track_position()
        assert position is not None

    def test_track_not_enabled(self, test_config_path):
        """Test behavior when track is not enabled."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            enable_track=False
        )
        controller.initialize()
        
        assert controller.has_track() is False

    def test_track_disabled(self, initialized_controller):
        """Test track disabled state."""
        controller = initialized_controller
        
        success = controller.move_track_to_position(100)
        assert success is False  # Should fail when track is disabled


class TestStateManagementAndMonitoring:
    """Test state management and monitoring features."""

    def test_get_system_status(self, initialized_controller):
        """Test comprehensive system status retrieval."""
        controller = initialized_controller
        
        status = controller.get_system_status()
        assert isinstance(status, dict)
        assert 'timestamp' in status
        assert 'connection' in status
        assert 'arm' in status
        assert 'gripper' in status
        assert 'track' in status
        assert 'errors' in status

    def test_error_tracking(self, initialized_controller):
        """Test error tracking functionality."""
        controller = initialized_controller
        
        # Test error history
        history = controller.get_error_history()
        assert isinstance(history, list)

    def test_warning_tracking(self, initialized_controller):
        """Test warning tracking functionality."""
        controller = initialized_controller
        
        # Test that warnings are tracked
        status = controller.get_system_status()
        assert 'errors' in status
        assert 'last_warning' in status['errors']

    def test_state_changed_callback(self, initialized_controller):
        """Test state change callback system."""
        controller = initialized_controller
        
        callback_called = False
        
        def test_callback(data):
            nonlocal callback_called
            callback_called = True
        
        # Register callback (this would be implemented in the actual system)
        # For now, just test that the callback system exists
        assert hasattr(controller, '_trigger_callbacks')

    def test_is_alive_property(self, initialized_controller):
        """Test is_alive property."""
        controller = initialized_controller
        
        assert hasattr(controller, 'is_alive')
        alive_status = controller.is_alive
        assert isinstance(alive_status, bool)

    def test_get_error_history(self, initialized_controller):
        """Test error history retrieval."""
        controller = initialized_controller
        
        history = controller.get_error_history(count=5)
        assert isinstance(history, list)
        assert len(history) <= 5

    def test_clear_errors(self, initialized_controller):
        """Test error clearing functionality."""
        controller = initialized_controller
        
        # This should not raise an exception
        controller.clear_errors()


class TestPerformanceMonitoring:
    """Test performance monitoring features."""

    def test_performance_metrics_initialization(self, initialized_controller):
        """Test performance metrics initialization."""
        controller = initialized_controller
        
        metrics = controller.get_performance_metrics()
        assert isinstance(metrics, dict)
        # Check for expected metric types
        expected_metrics = ['cycle_times', 'joint_utilization', 'accuracy_errors', 'command_success_rate']
        for metric in expected_metrics:
            assert metric in metrics

    def test_maintenance_status(self, initialized_controller):
        """Test maintenance status retrieval."""
        controller = initialized_controller
        
        status = controller.get_maintenance_status()
        assert isinstance(status, dict)
        assert 'temperature' in status
        assert 'torque' in status
        assert 'current' in status
        assert 'overall_health' in status


class TestUtilityMethods:
    """Test utility methods and information retrieval."""

    def test_get_current_position(self, initialized_controller):
        """Test current position retrieval."""
        controller = initialized_controller
        
        position = controller.get_current_position()
        assert isinstance(position, list)
        assert len(position) == 6  # x, y, z, roll, pitch, yaw

    def test_get_current_joints(self, initialized_controller):
        """Test current joint angles retrieval."""
        controller = initialized_controller
        
        joints = controller.get_current_joints()
        assert isinstance(joints, list)
        assert len(joints) == controller.num_joints

    def test_get_named_locations(self, initialized_controller):
        """Test named locations retrieval."""
        controller = initialized_controller
        
        locations = controller.get_named_locations()
        assert isinstance(locations, list)
        # Check for expected locations from config
        expected_locations = ['ROBOT_HOME', 'ROBOT_HOME_-90', 'Rlw_low', 'Rlw_high']
        for location in expected_locations:
            assert location in locations

    def test_get_system_info(self, initialized_controller):
        """Test system information retrieval."""
        controller = initialized_controller
        
        info = controller.get_system_info()
        assert isinstance(info, dict)
        assert 'model' in info
        assert 'num_joints' in info
        assert 'gripper_type' in info
        assert 'has_gripper' in info
        assert 'has_track' in info
        assert 'connected' in info
        assert 'component_states' in info

    def test_check_code_success(self, initialized_controller):
        """Test check_code method with success code."""
        controller = initialized_controller
        
        result = controller.check_code(0, "test_operation")
        assert result is True

    def test_check_code_failure(self, initialized_controller):
        """Test check_code method with failure code."""
        controller = initialized_controller
        
        result = controller.check_code(1, "test_operation")
        assert result is False

    def test_has_gripper(self, initialized_controller):
        """Test has_gripper method."""
        controller = initialized_controller
        
        result = controller.has_gripper()
        assert isinstance(result, bool)

    def test_has_track(self, initialized_controller):
        """Test has_track method."""
        controller = initialized_controller
        
        result = controller.has_track()
        assert isinstance(result, bool)


class TestSafetyAndValidation:
    """Test safety systems and validation."""

    def test_safety_level_enforcement(self, test_config_path):
        """Test safety level enforcement."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            safety_level=SafetyLevel.HIGH
        )
        controller.initialize()
        
        assert controller.safety_level == SafetyLevel.HIGH

    def test_joint_limit_validation(self, simulation_controller):
        """Test joint limit validation."""
        controller = simulation_controller
        controller.initialize()
        
        # Test with valid joint angles
        success = controller.move_joints([0, 0, 0, 0, 0, 0, 0])
        assert success is True

    def test_workspace_boundary_validation(self, initialized_controller):
        """Test workspace boundary validation."""
        controller = initialized_controller
        
        # Test with valid position
        success = controller.move_to_position(
            x=300, y=0, z=300,
            roll=180, pitch=0, yaw=0
        )
        assert success is True


class TestErrorHandling:
    """Test error handling and recovery."""

    def test_missing_config_files(self, tmp_path):
        """Test behavior with missing config files."""
        # Create controller with non-existent config path
        controller = XArmController(
            config_path=str(tmp_path / "nonexistent"),
            simulation_mode=True
        )
        
        # Should still initialize with defaults
        assert controller.xarm_config is not None

    def test_invalid_gripper_type(self, test_config_path):
        """Test behavior with invalid gripper type."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            gripper_type='invalid'
        )
        
        # Should still initialize
        assert controller.gripper_type == 'invalid'

    def test_arm_none_operations(self, test_config_path):
        """Test operations when arm is None."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True
        )
        
        # Temporarily set arm to None
        original_arm = controller.arm
        controller.arm = None
        
        # Operations should handle None gracefully
        status = controller.get_system_status()
        assert status is not None
        
        # Restore arm
        controller.arm = original_arm

    def test_position_updates_with_none_arm(self, test_config_path):
        """Test position updates when arm is None."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True
        )
        
        # Temporarily set arm to None
        original_arm = controller.arm
        controller.arm = None
        
        # Should not crash
        controller._update_positions()
        
        # Restore arm
        controller.arm = original_arm


class TestConfigurationManagement:
    """Test configuration management features."""

    def test_host_priority_resolution(self, test_config_path):
        """Test host resolution priority."""
        # Test direct host parameter takes priority
        controller = XArmController(
            host='192.168.1.100',
            config_path=test_config_path,
            simulation_mode=True
        )
        
        assert controller.host == '192.168.1.100'

    def test_model_configuration(self, test_config_path):
        """Test model configuration."""
        controller = XArmController(
            config_path=test_config_path,
            simulation_mode=True,
            model=6
        )
        
        assert controller.model == 6
        assert controller.num_joints == 6

    def test_safety_config_loading(self, initialized_controller):
        """Test safety configuration loading."""
        controller = initialized_controller
        
        # Should have safety config loaded
        assert hasattr(controller, 'safety_config')


class TestBackwardCompatibility:
    """Test backward compatibility features."""

    def test_legacy_method_compatibility(self, initialized_controller):
        """Test that legacy methods still work."""
        controller = initialized_controller
        
        # Test legacy method names if they exist
        if hasattr(controller, 'get_model'):
            model = controller.get_model()
            assert isinstance(model, int)
        
        if hasattr(controller, 'get_num_joints'):
            joints = controller.get_num_joints()
            assert isinstance(joints, int) 