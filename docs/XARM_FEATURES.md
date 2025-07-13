# xArm Controller Features Documentation

## 🚀 Recent Improvements (January 2025)

**BREAKING CHANGES**: The controller has been streamlined with enhanced methods replacing basic ones:

### ✅ Enhanced Methods Now Default
- **`move_to_position()`** → Now uses collision detection and alternative planning automatically
- **`move_joints()`** → Now uses comprehensive safety validation by default
- **`go_home()`** → Now uses enhanced joint movement with collision checking

### 🎯 Universal Methods
All components now use universal methods that automatically work with your configured hardware:
```python
# Universal gripper control (works with bio, standard, or robotiq grippers)
controller.open_gripper()               # Opens any configured gripper
controller.close_gripper()              # Closes any configured gripper  
controller.enable_gripper_component()   # Enables any gripper type

# Enhanced movement with automatic collision detection and safety
controller.move_to_position(x, y, z)    # Now enhanced with collision detection
```

---

## Overview

This documentation compares **Simulation Mode** vs **Real Robot Mode** in the xArm Controller, lists supported features, and identifies upgrade opportunities from basic to advanced methods.

## Table of Contents

1. [Simulation Mode vs Real Robot Mode](#simulation-mode-vs-real-robot-mode)
2. [Feature Support Matrix](#feature-support-matrix)
3. [Method Upgrade Opportunities](#method-upgrade-opportunities)
4. [Use Cases and Examples](#use-cases-and-examples)
5. [xArm Python SDK Advanced Features](#xarm-python-sdk-advanced-features)

---

## Simulation Mode vs Real Robot Mode

### Simulation Mode (`simulation_mode=True`)

**Purpose**: Software testing, development, and debugging without physical hardware

**Key Characteristics**:
- ✅ **Mock Hardware**: Creates `SimulationArm` object with simulated responses
- ✅ **Instant Responses**: All operations return success codes immediately
- ✅ **No Hardware Required**: No physical connection needed
- ✅ **Safe Testing**: Perfect for algorithm development and testing
- ✅ **Collision Simulation**: Basic workspace and joint limit checking
- ✅ **State Tracking**: Maintains position, joint angles, and component states
- ❌ **No Real Feedback**: No actual sensor data or force feedback
- ❌ **No Monitoring**: Performance tracking and predictive maintenance disabled
- ❌ **Limited Physics**: Simplified collision detection

**Initialization**:
```python
controller = XArmController(
    simulation_mode=True,
    gripper_type='bio',
    enable_track=True,
    auto_enable=True
)
```

**Supported Operations**:
- ✅ All movement commands (simulated)
- ✅ Gripper control (simulated)
- ✅ Linear track control (simulated)
- ✅ State management
- ✅ Configuration loading
- ✅ Error clearing
- ❌ Hardware monitoring
- ❌ Force/torque sensing
- ❌ Predictive maintenance

---

### Real Robot Mode (`simulation_mode=False`)

**Purpose**: Production control of physical xArm hardware

**Key Characteristics**:
- ✅ **Hardware Connection**: Real TCP/IP connection to xArm controller
- ✅ **Real Sensor Data**: Actual position, torque, temperature feedback
- ✅ **Safety Systems**: Hardware-level collision detection and limits
- ✅ **Force Control**: 6-axis force/torque sensor support (if equipped)
- ✅ **Monitoring**: Real-time performance and predictive maintenance
- ✅ **Callbacks**: Hardware state change notifications
- ⚠️ **Requires Hardware**: Physical xArm must be connected and powered
- ⚠️ **Safety Critical**: Improper use can cause damage or injury

**Initialization**:
```python
controller = XArmController(
    simulation_mode=False,
    gripper_type='bio',
    enable_track=True,
    auto_enable=True,
    safety_level=SafetyLevel.MEDIUM
)
```

**Supported Operations**:
- ✅ All movement commands (real hardware)
- ✅ Hardware gripper control
- ✅ Linear track control
- ✅ Real-time monitoring
- ✅ Force/torque sensing
- ✅ Predictive maintenance
- ✅ Error recovery
- ✅ Safety validation

---

## Feature Support Matrix

| Feature | Simulation Mode | Real Robot Mode | Notes |
|---------|-----------------|-----------------|-------|
| **Movement Control** | | | |
| Basic positioning | ✅ | ✅ | `move_to_position()` |
| Joint control | ✅ | ✅ | `move_joints()` |
| Collision checking | ⚠️ Basic | ✅ Hardware | SDK collision detection |
| Motion planning | ❌ | ✅ | Multiple motion types |
| Velocity control | ✅ | ✅ | Cartesian/joint velocity |
| **Safety Systems** | | | |
| Workspace limits | ✅ | ✅ | Configurable boundaries |
| Joint limits | ✅ | ✅ | Model-specific limits |
| Speed limits | ✅ | ✅ | Safety level based |
| Emergency stop | ✅ | ✅ | `emergency_stop()` |
| **Gripper Control** | | | |
| Bio gripper | ✅ | ✅ | Open/close operations |
| Standard gripper | ✅ | ✅ | Position control |
| RobotIQ gripper | ✅ | ✅ | Advanced features |
| Universal methods | ✅ | ✅ | `open_gripper()`, `close_gripper()` |
| **Linear Track** | | | |
| Position control | ✅ | ✅ | `move_track_to_position()` |
| Speed control | ✅ | ✅ | Configurable speeds |
| Safety validation | ✅ | ✅ | Position/speed limits |
| **Monitoring** | | | |
| Performance tracking | ❌ | ✅ | Cycle times, accuracy |
| Predictive maintenance | ❌ | ✅ | Temperature, torque monitoring |
| Error history | ✅ | ✅ | Automatic cleanup |
| State callbacks | ❌ | ✅ | Hardware state changes |
| **Force Control** | | | |
| Force/torque sensing | ❌ | ✅ | 6-axis sensor |
| Impedance control | ❌ | ✅ | Compliant motion |
| Force thresholds | ❌ | ✅ | Collision detection |
| **Configuration** | | | |
| YAML config loading | ✅ | ✅ | All configuration files |
| Named locations | ✅ | ✅ | Predefined positions |
| Multi-model support | ✅ | ✅ | xArm5/6/7/850 |

---

## Method Upgrade Opportunities

### Quick Reference Table

| Current Method | Enhanced Method | Key Improvements | Availability |
|----------------|-----------------|------------------|--------------|
| `move_to_position()` | *Built-in advanced features* | ✅ Collision checking<br>✅ Motion planning alternatives<br>✅ Performance tracking | Both modes |
| `move_joints()` | *Built-in advanced features* | ✅ Joint angle validation<br>✅ Collision detection<br>✅ Performance metrics | Both modes |
| `move_track_to_position()` | *Enhanced version built-in* | ✅ Position/speed validation<br>✅ Danger zone checking<br>✅ Performance tracking | Both modes |
| Universal gripper methods | `open_gripper()`, `close_gripper()` | ✅ Works with any gripper type<br>✅ Automatic type detection | Both modes |
| `get_system_status()` | `get_comprehensive_status()` | ✅ Performance metrics<br>✅ Maintenance alerts<br>✅ Detailed monitoring | Real robot only |
| `clear_errors()` | *Automatic recovery* | ✅ Intelligent error strategies<br>✅ Callback notifications<br>✅ Recovery attempt limiting | Real robot only |
| Manual error checking | `register_callback()` | ✅ Event-driven error handling<br>✅ Automatic notifications<br>✅ Custom error handlers | Real robot only |

### 1. Movement Control Upgrades

#### Basic → Enhanced Movement
```python
# Basic method
controller.move_to_position(x, y, z, roll, pitch, yaw)

# Advanced method (available in both modes)
controller.move_to_position(
    x, y, z, roll, pitch, yaw,
    check_collision=True,
    motion_type=0,  # Try alternative planning if fails
    speed=100
)
```

#### Basic → Enhanced Joint Movement
```python
# Basic method
controller.move_joints(angles, speed, acceleration)

# Enhanced method (available in both modes)
controller.move_joints(
    angles,
    speed=None,
    acceleration=None,
    check_collision=True,
    wait=True
)
```

### 2. Gripper Control Upgrades

#### Universal Gripper Control
```python
# Universal methods work with any gripper type (bio, standard, robotiq)
controller.open_gripper()   # Opens any configured gripper
controller.close_gripper()  # Closes any configured gripper
controller.enable_gripper_component()  # Enables any gripper type

# Automatically detects and uses the correct gripper type based on configuration
```

### 3. Monitoring Upgrades

#### Basic Status → Comprehensive Status
```python
# Basic status
status = controller.get_system_status()

# Comprehensive status (real robot mode only)
status = controller.get_comprehensive_status()  # Includes performance metrics
maintenance = controller.get_maintenance_status()  # Predictive maintenance
```

### 4. Error Handling Upgrades

#### Manual → Automatic Recovery
```python
# Manual error handling
if controller.last_error_code != 0:
    controller.clear_errors()

# Automatic recovery (built-in)
# Errors are automatically detected and recovery attempted
# Register callbacks for notifications
def error_handler(error_info):
    print(f"Error {error_info['error_code']} automatically handled")

controller.register_callback('error_occurred', error_handler)
```

### 5. Safety Upgrades

#### Basic → Advanced Validation
```python
# Basic movement (minimal validation)
controller.move_to_position(x, y, z)

# Advanced validation (comprehensive safety checks)
controller.move_to_position(
    x, y, z,
    check_collision=True,      # Pre-motion collision check
    motion_type=0,            # Try alternative planning
    speed=100                 # Validated against safety limits
)
```

---

## Use Cases and Examples

### Development and Testing (Simulation Mode)

```python
# Development environment
controller = XArmController(
    simulation_mode=True,
    gripper_type='bio',
    enable_track=True,
    auto_enable=True,
    safety_level=SafetyLevel.LOW  # Faster development
)

# Safe algorithm testing
for position in test_positions:
    success = controller.move_to_position(*position)
    print(f"Position {position}: {'SUCCESS' if success else 'FAILED'}")

# No hardware required - perfect for CI/CD testing
```

### Production Control (Real Robot Mode)

```python
# Production environment
controller = XArmController(
    simulation_mode=False,
    gripper_type='bio',
    enable_track=True,
    auto_enable=True,
    safety_level=SafetyLevel.HIGH  # Maximum safety
)

# Real hardware operations with monitoring
controller.register_callback('maintenance_alert', handle_maintenance)
controller.register_callback('error_occurred', handle_errors)

# Production workflow with comprehensive monitoring
for task in production_tasks:
    success = controller.move_to_position(*task.position)
    if success:
        controller.open_gripper()
        # ... perform task
        controller.close_gripper()
    
    # Monitor performance
    metrics = controller.get_performance_metrics()
    if metrics['cycle_times']['average'] > 5.0:
        print("WARNING: Performance degradation detected")
```

### Predictive Maintenance (Real Robot Mode Only)

```python
# Monitor robot health
def check_robot_health():
    maintenance_status = controller.get_maintenance_status()
    
    if maintenance_status['overall_health'] == 'critical':
        print("🚨 CRITICAL: Robot requires immediate maintenance")
        return False
    elif maintenance_status['overall_health'] == 'warning':
        print("⚠️ WARNING: Schedule maintenance soon")
    
    return True

# Register maintenance alerts
def maintenance_alert_handler(alert):
    print(f"Maintenance Alert: {alert['type']} - {alert['data']}")
    if alert['severity'] == 'critical':
        controller.emergency_stop()

controller.register_callback('maintenance_alert', maintenance_alert_handler)
```

---

## xArm Python SDK Advanced Features

### Available in xArm Python SDK

The controller utilizes these advanced xArm Python SDK features:

#### 1. Collision Detection
```python
# Pre-motion collision checking
arm.set_only_check_type(1)  # Check without moving
result = arm.set_position(x, y, z, roll, pitch, yaw)
arm.set_only_check_type(0)  # Reset to normal mode
```

#### 2. Motion Planning
```python
# Multiple motion types for path planning
arm.set_position(x, y, z, roll, pitch, yaw, motion_type=0)  # Default
arm.set_position(x, y, z, roll, pitch, yaw, motion_type=1)  # Alternative
```

#### 3. Force/Torque Control
```python
# 6-axis force/torque sensor (if equipped)
arm.ft_sensor_enable(True)
force_data = arm.get_ft_sensor_data()
arm.ft_sensor_app_set(1)  # Impedance control mode
```

#### 4. Advanced Parameters
```python
# Jerk control for smooth motion
arm.set_tcp_jerk(jerk_value)
arm.set_joint_jerk(jerk_value)

# Comprehensive limit checking
arm = XArmAPI(
    port=ip,
    check_tcp_limit=True,
    check_joint_limit=True,
    check_cmdnum_limit=True,
    check_is_ready=True
)
```

#### 5. Comprehensive Callbacks
```python
# Register multiple callback types
arm.register_report_callback(callback)
arm.register_error_warn_changed_callback(callback)
arm.register_state_changed_callback(callback)
arm.register_temperature_changed_callback(callback)
arm.register_feedback_callback(callback)
```

#### 6. Real-time Monitoring
```python
# Access real-time robot data
temperatures = arm.temperatures
joint_torques = arm.joints_torque
currents = arm.currents
voltages = arm.voltages
```

#### 7. Multiple Gripper Support
```python
# Bio gripper
arm.set_bio_gripper_enable(True)
arm.open_bio_gripper()

# Standard gripper
arm.set_gripper_enable(True)
arm.set_gripper_position(850)

# RobotIQ gripper
arm.robotiq_reset()
arm.robotiq_set_activate(True)
arm.robotiq_set_position(255)
```

#### 8. Advanced Motion Features
```python
# Trajectory recording and playback
arm.start_record_trajectory()
arm.stop_record_trajectory()
arm.playback_trajectory(times=1, wait=True)

# Online trajectory planning
arm.set_servo_cartesian(x, y, z, roll, pitch, yaw)
arm.set_servo_j(angles)

# Circular motion
arm.move_circle(pose1, pose2, percent=100, speed=100)
```

#### 9. Safety and Limit Control
```python
# Collision sensitivity
arm.set_collision_sensitivity(sensitivity)

# Reduced mode (safety boundaries)
arm.set_reduced_mode(True)
arm.set_reduced_tcp_boundary([x_min, x_max, y_min, y_max, z_min, z_max])

# Fence mode (virtual boundaries)
arm.set_fence_mode(True)
arm.set_fence_tcp_boundary([x_min, x_max, y_min, y_max, z_min, z_max])
```

#### 10. GPIO and Modbus Control
```python
# Tool GPIO
arm.get_tgpio_digital(ionum)
arm.set_tgpio_digital(ionum, value)
arm.get_tgpio_analog(ionum)

# Controller GPIO
arm.get_cgpio_digital(ionum)
arm.set_cgpio_digital(ionum, value)
arm.get_cgpio_analog(ionum)
arm.set_cgpio_analog(ionum, value)

# Modbus TCP
arm.getset_tgpio_modbus_data(datas, min_res_len=0)
```

#### 11. System Configuration
```python
# TCP load and offset
arm.set_tcp_load(weight, center_of_gravity)
arm.set_tcp_offset(offset)

# Gravity direction
arm.set_gravity_direction(direction)

# Self-collision detection
arm.set_self_collision_detection(True)

# Collision tool model
arm.set_collision_tool_model(tool_type)
```

### Potential Future Enhancements

Based on available xArm Python SDK features, the controller could be enhanced with:

1. **Trajectory Control**: Recording and playback of complex movements
2. **Servo Control**: Real-time position control for smooth operations
3. **Circular Motion**: Built-in circular interpolation for arc movements
4. **Boundary Control**: Virtual safety boundaries and reduced mode
5. **GPIO Integration**: Digital and analog I/O control for external devices
6. **Modbus Support**: Industrial communication protocol support
7. **Advanced Safety**: Tool models, self-collision detection, teach sensitivity
8. **Load Compensation**: Automatic payload compensation
9. **Gravity Compensation**: Orientation-based gravity adjustment
10. **Multi-axis Coordination**: Synchronized multi-robot control

---

## Recommendations

### For Development:
1. ✅ Use **Simulation Mode** for algorithm development and testing
2. ✅ Use **Advanced Methods** (`move_to_position`, `move_joints`) for better safety
3. ✅ Use **Universal Gripper Methods** for gripper type independence
4. ✅ Test with different safety levels to understand behavior

### For Production:
1. ✅ Use **Real Robot Mode** with appropriate safety level
2. ✅ Implement **Predictive Maintenance** monitoring
3. ✅ Register **Error Callbacks** for automatic recovery
4. ✅ Use **Force Control** if equipped with 6-axis sensor
5. ✅ Monitor **Performance Metrics** for optimization

### For Migration:
1. ✅ Replace basic gripper methods with universal methods for flexibility
2. ✅ Use `move_joints` with `check_collision=True` for comprehensive validation
3. ✅ Use `move_to_position` (automatically uses collision detection)
4. ✅ Implement callback-based error handling instead of polling
5. ✅ Add performance monitoring for production systems

---

## Version Information

- **Controller Version**: Enhanced with Phase 2 Performance Tracking
- **SDK Compatibility**: xArm Python SDK v1.16.0+
- **Supported Models**: xArm5, xArm6, xArm7, xArm850
- **Python Version**: 3.8+

---

*This documentation is current as of January 2025. For the latest updates, refer to the xArm Python SDK documentation and release notes.* 