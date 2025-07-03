"""
Tests for XArmController class.
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

from xarm_controller import XArmController, ComponentState


class TestXArmControllerInitialization:
    """Test XArmController initialization and configuration."""
    
    def test_controller_creation_no_auto_enable(self, controller_no_auto_enable):
        """Test creating controller without auto-enable."""
        controller = controller_no_auto_enable
        
        assert controller.gripper_type == 'bio'
        assert controller.enable_track is True
        assert controller.auto_enable is False
        assert controller.arm is None  # Not connected yet
        assert controller.alive is True
        
        # Check initial states
        states = controller.get_component_states()
        assert states['connection'] == 'unknown'
        assert states['arm'] == 'unknown'
        assert states['gripper'] == 'unknown'
        assert states['track'] == 'unknown'
    
    def test_controller_creation_auto_enable(self, controller_auto_enable):
        """Test creating controller with auto-enable."""
        controller = controller_auto_enable
        
        assert controller.auto_enable is True
    
    def test_controller_creation_different_grippers(self, test_config_path):
        """Test creating controller with different gripper types."""
        # Test standard gripper
        controller_std = XArmController(
            config_path=test_config_path,
            gripper_type='standard',
            enable_track=False
        )
        assert controller_std.gripper_type == 'standard'
        assert controller_std.enable_track is False
        
        # Test no gripper
        controller_none = XArmController(
            config_path=test_config_path,
            gripper_type='none',
            enable_track=True
        )
        assert controller_none.gripper_type == 'none'
        assert controller_none.get_component_states()['gripper'] == 'disabled'
    
    def test_config_loading(self, controller_no_auto_enable):
        """Test configuration loading."""
        controller = controller_no_auto_enable
        
        assert controller.xarm_config['host'] == '127.0.0.1'
        assert controller.tcp_speed == 100
        assert controller.angle_speed == 20
        assert 'home' in controller.location_config
        assert controller.gripper_config['GRIPPER_SPEED'] == 300


class TestXArmControllerConnection:
    """Test connection and initialization."""
    
    def test_initialize_success(self, controller_no_auto_enable, mock_xarm_api, monkeypatch):
        """Test successful initialization."""
        # Mock XArmAPI constructor
        def mock_constructor(*args, **kwargs):
            mock_xarm_api.connected = True
            return mock_xarm_api
        
        monkeypatch.setattr('xarm_controller.XArmAPI', mock_constructor)
        
        success = controller_no_auto_enable.initialize()
        
        assert success is True
        assert controller_no_auto_enable.arm is not None
        assert controller_no_auto_enable.get_component_states()['connection'] == 'enabled'
        assert controller_no_auto_enable.get_component_states()['arm'] == 'enabled'
    
    def test_initialize_failure(self, controller_no_auto_enable, mock_xarm_api, monkeypatch):
        """Test initialization failure."""
        # Mock XArmAPI constructor
        def mock_constructor(*args, **kwargs):
            mock_xarm_api.connected = False
            return mock_xarm_api
        
        monkeypatch.setattr('xarm_controller.XArmAPI', mock_constructor)
        
        success = controller_no_auto_enable.initialize()
        
        assert success is False
        assert controller_no_auto_enable.get_component_states()['connection'] == 'error'
    
    def test_disconnect(self, initialized_controller):
        """Test disconnection."""
        controller = initialized_controller
        
        controller.disconnect()
        
        assert controller.get_component_states()['connection'] == 'disabled'
        assert controller.get_component_states()['arm'] == 'disabled'


class TestComponentManagement:
    """Test component enable/disable functionality."""
    
    def test_enable_gripper_component(self, initialized_controller):
        """Test enabling gripper component."""
        controller = initialized_controller
        
        success = controller.enable_gripper_component()
        
        assert success is True
        assert controller.get_component_states()['gripper'] == 'enabled'
        assert controller.arm.set_bio_gripper_enable.called
    
    def test_enable_track_component(self, initialized_controller):
        """Test enabling track component."""
        controller = initialized_controller
        
        success = controller.enable_track_component()
        
        assert success is True
        assert controller.get_component_states()['track'] == 'enabled'
        assert controller.arm.set_linear_track_enable.called
    
    def test_disable_gripper_component(self, initialized_controller):
        """Test disabling gripper component."""
        controller = initialized_controller
        
        # First enable it
        controller.enable_gripper_component()
        
        # Then disable it
        success = controller.disable_gripper_component()
        
        assert success is True
        assert controller.get_component_states()['gripper'] == 'disabled'
    
    def test_disable_track_component(self, initialized_controller):
        """Test disabling track component."""
        controller = initialized_controller
        
        # First enable it
        controller.enable_track_component()
        
        # Then disable it
        success = controller.disable_track_component()
        
        assert success is True
        assert controller.get_component_states()['track'] == 'disabled'
    
    def test_component_state_checking(self, initialized_controller):
        """Test component state checking."""
        controller = initialized_controller
        
        # Initially not enabled
        assert not controller.is_component_enabled('gripper')
        assert not controller.is_component_enabled('track')
        
        # Enable components
        controller.enable_gripper_component()
        controller.enable_track_component()
        
        assert controller.is_component_enabled('gripper')
        assert controller.is_component_enabled('track')


class TestMovementMethods:
    """Test robot movement functionality."""
    
    def test_move_joints(self, initialized_controller):
        """Test joint movement."""
        controller = initialized_controller
        
        angles = [0, -30, 0, 30, 0, 0]
        success = controller.move_joints(angles)
        
        assert success is True
        controller.arm.set_servo_angle.assert_called()
    
    def test_move_joints_arm_not_enabled(self, controller_no_auto_enable):
        """Test joint movement when arm not enabled."""
        controller = controller_no_auto_enable
        
        success = controller.move_joints([0, 0, 0, 0, 0, 0])
        
        assert success is False
    
    def test_move_to_position(self, initialized_controller):
        """Test Cartesian position movement."""
        controller = initialized_controller
        
        success = controller.move_to_position(x=300, y=0, z=300)
        
        assert success is True
        controller.arm.set_position.assert_called()
    
    def test_move_relative(self, initialized_controller):
        """Test relative movement."""
        controller = initialized_controller
        
        success = controller.move_relative(dx=50, dz=10)
        
        assert success is True
        controller.arm.set_position.assert_called_with(
            x=50, y=0, z=10, roll=0, pitch=0, yaw=0,
            speed=100, relative=True, wait=True
        )
    
    def test_move_to_named_location(self, initialized_controller):
        """Test movement to named location."""
        controller = initialized_controller
        
        success = controller.move_to_named_location('home')
        
        assert success is True
        controller.arm.set_position.assert_called()
    
    def test_move_to_invalid_location(self, initialized_controller):
        """Test movement to invalid named location."""
        controller = initialized_controller
        
        success = controller.move_to_named_location('invalid_location')
        
        assert success is False
    
    def test_move_single_joint(self, initialized_controller):
        """Test single joint movement."""
        controller = initialized_controller
        
        success = controller.move_single_joint(joint_id=1, angle=45)
        
        assert success is True
        controller.arm.set_servo_angle.assert_called()
    
    def test_go_home(self, initialized_controller):
        """Test go home movement."""
        controller = initialized_controller
        
        success = controller.go_home()
        
        assert success is True
        controller.arm.move_gohome.assert_called()
    
    def test_velocity_control(self, initialized_controller):
        """Test velocity control methods."""
        controller = initialized_controller
        
        # Test Cartesian velocity
        success = controller.set_cartesian_velocity(vx=10, vy=0, vz=5)
        assert success is True
        controller.arm.vc_set_cartesian_velocity.assert_called()
        
        # Test joint velocity
        success = controller.set_joint_velocity([10, 0, 0, 0, 0, 0])
        assert success is True
        controller.arm.vc_set_joint_velocity.assert_called()


class TestGripperControl:
    """Test gripper control functionality."""
    
    def test_bio_gripper_control(self, initialized_controller):
        """Test BIO gripper control."""
        controller = initialized_controller
        controller.enable_gripper_component()
        
        # Test open
        success = controller.open_bio_gripper()
        assert success is True
        controller.arm.open_bio_gripper.assert_called()
        
        # Test close
        success = controller.close_bio_gripper()
        assert success is True
        controller.arm.close_bio_gripper.assert_called()
    
    def test_universal_gripper_methods(self, initialized_controller):
        """Test universal gripper methods."""
        controller = initialized_controller
        controller.enable_gripper_component()
        
        # Test universal open/close (should route to BIO gripper)
        success = controller.open_gripper()
        assert success is True
        controller.arm.open_bio_gripper.assert_called()
        
        success = controller.close_gripper()
        assert success is True
        controller.arm.close_bio_gripper.assert_called()
    
    def test_gripper_not_enabled(self, initialized_controller):
        """Test gripper control when not enabled."""
        controller = initialized_controller
        
        success = controller.open_gripper()
        assert success is False
    
    def test_no_gripper_configured(self, test_config_path, monkeypatch):
        """Test controller with no gripper."""
        controller = XArmController(
            config_path=test_config_path,
            gripper_type='none',
            auto_enable=False
        )
        
        success = controller.open_gripper()
        assert success is False
        
        assert not controller.has_gripper()


class TestLinearTrackControl:
    """Test linear track control functionality."""
    
    def test_track_movement(self, initialized_controller):
        """Test track movement."""
        controller = initialized_controller
        controller.enable_track_component()
        
        success = controller.move_track_to_position(100)
        
        assert success is True
        controller.arm.set_linear_track_pos.assert_called()
    
    def test_track_reset(self, initialized_controller):
        """Test track reset."""
        controller = initialized_controller
        controller.enable_track_component()
        
        success = controller.reset_track()
        
        assert success is True
        controller.arm.set_linear_track_pos.assert_called_with(speed=200, pos=0, wait=True)
    
    def test_track_speed_setting(self, initialized_controller):
        """Test track speed setting."""
        controller = initialized_controller
        controller.enable_track_component()
        
        success = controller.set_track_speed(150)
        
        assert success is True
        controller.arm.set_linear_track_speed.assert_called_with(150)
    
    def test_track_not_enabled(self, initialized_controller):
        """Test track control when not enabled."""
        controller = initialized_controller
        
        success = controller.move_track_to_position(100)
        assert success is False
    
    def test_track_disabled(self, test_config_path):
        """Test controller with track disabled."""
        controller = XArmController(
            config_path=test_config_path,
            gripper_type='bio',
            enable_track=False,
            auto_enable=False
        )
        
        assert not controller.has_track()
        success = controller.move_track_to_position(100)
        assert success is False


class TestStateManagement:
    """Test state management and monitoring."""
    
    def test_get_system_status(self, initialized_controller):
        """Test system status retrieval."""
        controller = initialized_controller
        
        status = controller.get_system_status()
        
        assert 'timestamp' in status
        assert 'connection' in status
        assert 'arm' in status
        assert 'gripper' in status
        assert 'track' in status
        assert 'errors' in status
        
        assert status['connection']['connected'] is True
        assert status['arm']['state'] == 'enabled'
    
    def test_error_tracking(self, initialized_controller):
        """Test error tracking functionality."""
        controller = initialized_controller
        
        # Simulate error callback
        error_data = {'error_code': 5, 'warn_code': 0}
        controller._error_warn_callback(error_data)
        
        assert controller.last_error_code == 5
        assert not controller.alive
        assert len(controller.error_history) == 1
        assert controller.get_component_states()['arm'] == 'error'
    
    def test_warning_tracking(self, initialized_controller):
        """Test warning tracking."""
        controller = initialized_controller
        
        # Simulate warning callback
        warn_data = {'error_code': 0, 'warn_code': 3}
        controller._error_warn_callback(warn_data)
        
        assert controller.last_warn_code == 3
        assert controller.alive  # Should still be alive for warnings
    
    def test_state_changed_callback(self, initialized_controller):
        """Test state change callback."""
        controller = initialized_controller
        
        # Simulate state 4 (exit state)
        state_data = {'state': 4}
        controller._state_changed_callback(state_data)
        
        assert not controller.alive
        assert controller.get_component_states()['arm'] == 'error'
    
    def test_is_alive_property(self, initialized_controller):
        """Test is_alive property."""
        controller = initialized_controller
        
        # Initially should be alive
        assert controller.is_alive
        
        # Simulate error
        controller.alive = False
        assert not controller.is_alive
    
    def test_get_error_history(self, initialized_controller):
        """Test error history retrieval."""
        controller = initialized_controller
        
        # Add some errors
        for i in range(5):
            error_data = {'error_code': i+1, 'warn_code': 0}
            controller._error_warn_callback(error_data)
        
        history = controller.get_error_history(count=3)
        assert len(history) == 3
        assert history[-1]['error_code'] == 5  # Most recent error


class TestUtilityMethods:
    """Test utility and helper methods."""
    
    def test_get_current_position(self, initialized_controller):
        """Test getting current position."""
        controller = initialized_controller
        
        position = controller.get_current_position()
        
        assert position is not None
        assert len(position) == 6  # [x, y, z, roll, pitch, yaw]
        controller.arm.get_position.assert_called()
    
    def test_get_current_joints(self, initialized_controller):
        """Test getting current joint angles."""
        controller = initialized_controller
        
        joints = controller.get_current_joints()
        
        assert joints is not None
        assert len(joints) == 6
        controller.arm.get_servo_angle.assert_called()
    
    def test_get_track_position(self, initialized_controller):
        """Test getting track position."""
        controller = initialized_controller
        controller.enable_track_component()
        
        position = controller.get_track_position()
        
        assert position is not None
        controller.arm.get_linear_track_pos.assert_called()
    
    def test_check_code_success(self, initialized_controller):
        """Test successful code checking."""
        controller = initialized_controller
        
        result = controller.check_code(0, 'test_operation')
        
        assert result is True
    
    def test_check_code_failure(self, initialized_controller):
        """Test failed code checking."""
        controller = initialized_controller
        
        result = controller.check_code(1, 'test_operation')
        
        assert result is False
        assert not controller.alive
    
    def test_pprint_method(self):
        """Test pretty print method."""
        # This is a static method, so we can test it directly
        with patch('builtins.print') as mock_print:
            XArmController.pprint("Test message")
            mock_print.assert_called()
    
    def test_has_gripper(self, test_config_path):
        """Test has_gripper method."""
        # With gripper
        controller_with = XArmController(
            config_path=test_config_path,
            gripper_type='bio'
        )
        assert controller_with.has_gripper()
        
        # Without gripper
        controller_without = XArmController(
            config_path=test_config_path,
            gripper_type='none'
        )
        assert not controller_without.has_gripper()
    
    def test_has_track(self, test_config_path):
        """Test has_track method."""
        # With track
        controller_with = XArmController(
            config_path=test_config_path,
            enable_track=True
        )
        assert controller_with.has_track()
        
        # Without track
        controller_without = XArmController(
            config_path=test_config_path,
            enable_track=False
        )
        assert not controller_without.has_track()


class TestErrorHandling:
    """Test error handling and edge cases."""
    
    def test_missing_config_files(self, tmp_path):
        """Test handling of missing configuration files."""
        # Create controller with path to non-existent configs
        controller = XArmController(
            config_path=str(tmp_path) + "/nonexistent/",
            gripper_type='bio',
            enable_track=True
        )
        
        # Should handle missing configs gracefully
        assert controller.xarm_config == {}
        assert controller.gripper_config == {}
    
    def test_invalid_gripper_type(self, test_config_path):
        """Test handling of invalid gripper type."""
        with patch('builtins.print') as mock_print:
            controller = XArmController(
                config_path=test_config_path,
                gripper_type='invalid_type'
            )
            
            # Should print warning
            mock_print.assert_called()
    
    def test_arm_none_operations(self, controller_no_auto_enable):
        """Test operations when arm is None."""
        controller = controller_no_auto_enable
        
        # These should all handle None arm gracefully
        assert not controller.is_alive
        
        status = controller.get_system_status()
        assert status['connection']['connected'] is False
        
        controller.disconnect()  # Should not crash
    
    def test_position_updates_with_none_arm(self, controller_no_auto_enable):
        """Test position updates when arm is None."""
        controller = controller_no_auto_enable
        
        # Should not crash
        controller._update_positions()
        controller._update_track_position()
        
        assert controller.last_position is None
        assert controller.last_joints is None 