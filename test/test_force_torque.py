#!/usr/bin/env python3
"""
Test script for Force Torque Sensor functionality

This script tests the three main functionalities of the 6-axis force torque sensor:
1. Safety monitoring
2. Linear force-controlled movement
3. Joint torque-controlled movement
"""

import os
import sys
import time
import pytest

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.xarm_controller import XArmController


class TestForceTorqueSensor:
    """Test class for force torque sensor functionality."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test environment."""
        self.controller = XArmController(
            simulation_mode=True,  # Use simulation for testing
            auto_enable=True
        )
        self.controller.initialize()
        yield
        self.controller.disconnect()
    
    def test_force_torque_sensor_availability(self):
        """Test that force torque sensor is available."""
        assert self.controller.has_force_torque_sensor() == True
    
    def test_force_torque_sensor_enable_disable(self):
        """Test enabling and disabling force torque sensor."""
        # Test enable
        assert self.controller.enable_force_torque_sensor() == True
        assert self.controller.is_component_enabled('force_torque') == True
        
        # Test disable
        assert self.controller.disable_force_torque_sensor() == True
        assert self.controller.is_component_enabled('force_torque') == False
    
    def test_force_torque_sensor_calibration(self):
        """Test force torque sensor calibration."""
        # Enable sensor first
        self.controller.enable_force_torque_sensor()
        
        # Test calibration
        assert self.controller.calibrate_force_torque_sensor() == True
        assert self.controller.force_torque_calibrated == True
    
    def test_force_torque_data_retrieval(self):
        """Test retrieving force torque data."""
        # Enable and calibrate sensor
        self.controller.enable_force_torque_sensor()
        self.controller.calibrate_force_torque_sensor()
        
        # Test data retrieval
        data = self.controller.get_force_torque_data()
        assert data is not None
        assert len(data) == 6  # [fx, fy, fz, tx, ty, tz]
        assert all(isinstance(x, (int, float)) for x in data)
    
    def test_force_torque_magnitude_calculation(self):
        """Test force/torque magnitude calculation."""
        # Enable sensor
        self.controller.enable_force_torque_sensor()
        
        # Test magnitude calculation
        magnitude = self.controller.get_force_torque_magnitude()
        assert magnitude is not None
        assert 'force_magnitude' in magnitude
        assert 'torque_magnitude' in magnitude
        assert 'total_magnitude' in magnitude
        assert all(isinstance(v, (int, float)) for v in magnitude.values())
    
    def test_force_torque_direction_detection(self):
        """Test force/torque direction detection."""
        # Enable sensor
        self.controller.enable_force_torque_sensor()
        
        # Test direction detection
        direction = self.controller.get_force_torque_direction()
        assert direction is not None
        assert 'force_magnitude' in direction
        assert 'torque_magnitude' in direction
        
        # Direction vectors may be None if below dead zone
        if direction['force_direction'] is not None:
            assert len(direction['force_direction']) == 3
        if direction['torque_direction'] is not None:
            assert len(direction['torque_direction']) == 3
    
    def test_force_torque_safety_check(self):
        """Test force/torque safety checking."""
        # Enable sensor
        self.controller.enable_force_torque_sensor()
        
        # Test safety check (should not trigger in simulation with default thresholds)
        violation = self.controller.check_force_torque_safety()
        assert isinstance(violation, bool)
    
    def test_force_torque_status(self):
        """Test force torque sensor status retrieval."""
        # Enable sensor
        self.controller.enable_force_torque_sensor()
        
        # Test status retrieval
        status = self.controller.get_force_torque_status()
        assert status is not None
        assert 'enabled' in status
        assert 'calibrated' in status
        assert 'last_reading' in status
        assert 'magnitude' in status
        assert 'direction' in status
    
    def test_linear_force_movement_simulation(self):
        """Test linear force-controlled movement in simulation."""
        # Enable sensor
        self.controller.enable_force_torque_sensor()
        
        # Test force-controlled movement (should work in simulation)
        direction = [0, 0, -1]  # Downward direction
        success = self.controller.move_until_force(
            direction=direction,
            force_threshold=10.0,
            speed=50,
            timeout=5.0  # Short timeout for testing
        )
        
        # In simulation, this should complete without hitting threshold
        assert isinstance(success, bool)
    
    def test_joint_torque_movement_simulation(self):
        """Test joint torque-controlled movement in simulation."""
        # Enable sensor
        self.controller.enable_force_torque_sensor()
        
        # Get current joint angles
        current_joints = self.controller.get_current_joints()
        assert current_joints is not None
        
        # Test torque-controlled movement (should work in simulation)
        joint_id = min(5, self.controller.get_num_joints())  # Use available joint
        current_angle = current_joints[joint_id - 1]
        target_angle = current_angle + 10  # Small movement
        
        success = self.controller.move_joint_until_torque(
            joint_id=joint_id,
            target_angle=target_angle,
            torque_threshold=1.0,
            speed=10,
            timeout=5.0  # Short timeout for testing
        )
        
        # In simulation, this should complete without hitting threshold
        assert isinstance(success, bool)


def test_force_torque_config_loading():
    """Test that force torque configuration loads correctly."""
    controller = XArmController(simulation_mode=True)
    
    # Check that config was loaded
    assert hasattr(controller, 'force_torque_config')
    assert isinstance(controller.force_torque_config, dict)
    
    # Check for required config sections
    assert 'safety_thresholds' in controller.force_torque_config
    assert 'operation_thresholds' in controller.force_torque_config
    assert 'calibration' in controller.force_torque_config
    
    controller.disconnect()


def test_force_torque_simulation_mode():
    """Test force torque sensor in simulation mode."""
    controller = XArmController(simulation_mode=True, auto_enable=True)
    controller.initialize()
    
    # Test that sensor works in simulation
    assert controller.has_force_torque_sensor() == True
    assert controller.enable_force_torque_sensor() == True
    assert controller.calibrate_force_torque_sensor() == True
    
    # Test data retrieval in simulation
    data = controller.get_force_torque_data()
    assert data is not None
    assert len(data) == 6
    
    controller.disconnect()


if __name__ == "__main__":
    # Run tests
    print("🧪 Running Force Torque Sensor Tests...")
    
    # Test configuration loading
    print("Testing configuration loading...")
    test_force_torque_config_loading()
    print("✅ Configuration loading test passed")
    
    # Test simulation mode
    print("Testing simulation mode...")
    test_force_torque_simulation_mode()
    print("✅ Simulation mode test passed")
    
    # Test with pytest
    print("Running pytest tests...")
    pytest.main([__file__, "-v"])
    
    print("🎉 All force torque sensor tests completed!") 