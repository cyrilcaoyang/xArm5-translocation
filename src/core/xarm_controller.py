import yaml
import time
from enum import Enum
from collections import deque
from xarm.wrapper import XArmAPI
import os
from typing import Dict, List, Optional, Tuple, Any, Callable
import threading

# Import utilities from separate module
from .xarm_utils import (
    SafetyLevel, load_config, get_default_config, validate_target_position,
    validate_joint_angles, validate_track_position, validate_track_speed,
    check_joint_collision_simulation, check_workspace_collision_simulation,
    DEFAULT_PERFORMANCE_THRESHOLDS, DEFAULT_TEMPERATURE_THRESHOLDS,
    DEFAULT_SAFETY_BOUNDARIES, DEFAULT_COLLISION_SENSITIVITY,
    get_safety_speed_limits, apply_movement_parameter_limits, create_default_performance_metrics,
    get_joint_limits_for_model, check_operation_result, validate_and_apply_safety_config
)

class ComponentState(Enum):
    """Enum for component states"""
    UNKNOWN = "unknown"
    DISABLED = "disabled" 
    ENABLING = "enabling"
    ENABLED = "enabled"
    ERROR = "error"
    MAINTENANCE = "maintenance"  # State for maintenance mode

class XArmController:
    """
    xArm controller with intelligent error recovery, improved safety validation,
    better configuration management, state tracking, and performance monitoring.
    """
    def __init__(self, host: Optional[str] = None, config_path: str = 'settings/', 
                 gripper_type: str = 'bio', enable_track: bool = True, 
                 auto_enable: bool = True, model: Optional[int] = None, 
                 simulation_mode: bool = False, safety_level: SafetyLevel = SafetyLevel.MEDIUM):
        """
        Args:
            host (str, optional): The IP address of the xArm. If provided, this
                                overrides any host in the config file. Defaults to None.
            config_path (str): The path to the directory containing configuration files.
            gripper_type (str): Type of gripper ('bio', 'standard', 'robotiq', or 'none')
            enable_track (bool): Whether to enable the linear track
            auto_enable (bool): Whether to automatically enable components during initialization
            model (int): xArm model (5, 6, 7, or 850). If None, will be detected from config
            simulation_mode (bool): Enable simulation mode (no hardware required)
            safety_level (SafetyLevel): Safety level for validation strictness
        """
        # Store simulation mode first
        self.simulation_mode = simulation_mode
        self.safety_level = safety_level
        self.gripper_type = gripper_type
        self.enable_track = enable_track
        self.auto_enable = auto_enable
        
        # Initialize configuration attributes to help linter
        self.xarm_config = {}
        self.gripper_config = {}
        self.track_config = {}
        self.location_config = {}
        self.safety_config = {}
        
        # Configuration loading
        self.config_path = config_path
        self._load_configurations()
        
        # Determine the connection host with clear priority
        # 1. Direct `host` parameter
        # 2. `XARM_HOST_IP` environment variable
        # 3. Host from xarm_config.yaml
        # 4. Default to '127.0.0.1'
        self.host = host or \
                    os.environ.get('XARM_HOST_IP') or \
                    self.xarm_config.get('host', '127.0.0.1')
        
        # Determine model
        self.model = model or self.xarm_config.get('model', 7)
        self.num_joints = self.model if self.model in [5, 6, 7] else 6  # 850 has 6 joints
        
        # Model name for API server
        self.model_name = f"xArm{self.model}"
        
        # Initialize state management
        self._initialize_state_management()
        
        # Initialize safety systems
        self._initialize_safety_systems()
        
        # Initialize error recovery system
        self._initialize_error_recovery()
        
        # Initialize robot arm connection
        if self.simulation_mode:
            # In simulation mode, create a mock arm object
            self.arm = self._create_simulation_arm()
        else:
            # Use official SDK with do_not_open parameter
            self.arm = XArmAPI(self.host, do_not_open=True)
        
        # Movement parameters with validation
        self._setup_movement_parameters()
        
        # Initialize simulation state and collision detection
        if self.simulation_mode:
            self.last_position = [300, 0, 300, 180, 0, 0]
            self.last_joints = [0] * self.num_joints
            self.last_track_position = 0
        
        # Initialize if auto_enable is True
        if auto_enable:
            try:
                self.initialize()
            except Exception as e:
                print(f"Auto-initialization failed: {e}")

    def _load_configurations(self):
        """Load configurations from YAML files with error handling."""
        config_files = {
            'xarm_config': 'xarm_config.yaml',
            'gripper_config': self.gripper_type + '_gripper_config.yaml' if self.gripper_type != 'none' else None,
            'track_config': 'linear_track_config.yaml' if self.enable_track else None,
            'location_config': 'location_config.yaml',
            'safety_config': 'safety.yaml'  # Load from the new safety.yaml
        }
        
        for config_name, file_name in config_files.items():
            if file_name:
                # Use src/settings as the base path
                file_path = os.path.join('src', 'settings', file_name)
                try:
                    setattr(self, config_name, load_config(file_path))
                except FileNotFoundError:
                    print(f"Warning: Config file {file_path} not found, using defaults")
                    setattr(self, config_name, get_default_config(config_name))
            else:
                setattr(self, config_name, {})

    def _initialize_state_management(self):
        """Initialize state management system with callbacks."""
        # Component states
        self.states = {
            'connection': ComponentState.DISABLED,
            'arm': ComponentState.DISABLED,
            'gripper': ComponentState.DISABLED,
            'track': ComponentState.DISABLED
        }
        
        # Error tracking with automatic cleanup
        self.error_history = deque(maxlen=1000)
        self.last_error_code = 0
        self.last_warn_code = 0
        
        # Position tracking with history for analysis
        self.position_history = deque(maxlen=100)
        self.last_position = [300, 0, 300, 180, 0, 0]  # Default position
        self.last_joints = [0] * self.num_joints
        self.last_track_position = 0
        
        # Motion state tracking
        self._motion_in_progress = False
        
        # State tracking
        self.alive = True
        self._ignore_exit_state = False
        
        #Performance tracking system
        self.performance_metrics = create_default_performance_metrics()
        
        self.performance_thresholds = DEFAULT_PERFORMANCE_THRESHOLDS.copy()
        
        # Predictive maintenance monitoring
        self.temperature_history = deque(maxlen=100)
        self.torque_history = deque(maxlen=100)
        self.current_history = deque(maxlen=100)
        
        self.temperature_thresholds = self.safety_config.get('temperature_limits', DEFAULT_TEMPERATURE_THRESHOLDS)
        
        # Real-time monitoring thread
        self._monitoring_thread = None
        self._monitoring_active = False
        
        # Callback system for event-driven programming
        self._callbacks = {
            'state_changed': [],
            'error_occurred': [],
            'motion_complete': [],
            'safety_violation': [],
            'maintenance_alert': []
        }
        
        # Joint limits for different models (degrees)
        self.joint_limits = get_joint_limits_for_model(self.model)

    def _initialize_safety_systems(self):
        """Initialize safety validation systems."""
        # First, validate and clamp the loaded safety config against hardware limits
        self.safety_config = validate_and_apply_safety_config(self.safety_config)

        # Safety boundaries from the now-validated config
        self.safety_boundaries = self.safety_config.get('workspace_limits', DEFAULT_SAFETY_BOUNDARIES)
        
        # Speed limits based on safety level using utility function
        self.max_tcp_speed, self.max_joint_speed = get_safety_speed_limits(
            self.safety_level,
            self.safety_config.get('max_tcp_speed', 1000),
            self.safety_config.get('max_joint_speed', 180)
        )
        
        # Collision detection sensitivity from the now-validated config
        self.collision_sensitivity = self.safety_config.get('collision_sensitivity', DEFAULT_COLLISION_SENSITIVITY)

    def _initialize_error_recovery(self):
        """Initialize intelligent error recovery system."""
        # Error recovery strategies for common error codes
        self.error_recovery_strategies = {
            # Collision errors
            31: self._handle_collision_error,
            # Joint limit errors  
            23: self._handle_joint_limit_error,
            38: self._handle_hard_joint_limit_error,
            # Speed limit errors
            24: self._handle_joint_speed_error,
            60: self._handle_tcp_speed_error,
            # Communication errors
            1: self._handle_communication_error,
            2: self._handle_communication_error,
            # State errors
            4: self._handle_state_error
        }
        
        # Track recovery attempts to prevent infinite loops
        self.recovery_attempts = {}
        self.max_recovery_attempts = 3

    def _setup_movement_parameters(self):
        """Setup and validate movement parameters with safety limits."""
        # Basic movement parameters with validation
        raw_tcp_speed = self.xarm_config.get('tcp_speed', 100)
        raw_tcp_acc = self.xarm_config.get('tcp_acc', 2000)
        raw_angle_speed = self.xarm_config.get('angle_speed', 20)
        raw_angle_acc = self.xarm_config.get('angle_acc', 500)
        
        # Apply safety limits using utility function
        self.tcp_speed, self.tcp_acc, self.angle_speed, self.angle_acc = apply_movement_parameter_limits(
            raw_tcp_speed, raw_tcp_acc, raw_angle_speed, raw_angle_acc,
            self.max_tcp_speed, self.max_joint_speed
        )
        
        # Log if parameters were limited for safety
        if raw_tcp_speed != self.tcp_speed:
            print(f"TCP speed limited from {raw_tcp_speed} to {self.tcp_speed} for safety")
        if raw_angle_speed != self.angle_speed:
            print(f"Joint speed limited from {raw_angle_speed} to {self.angle_speed} for safety")

    def _create_simulation_arm(self):
        """Create a mock arm object for simulation mode."""
        class SimulationArm:
            def __init__(self, controller):
                self.controller = controller
                self.connected = True
                self.error_code = 0
                self.warn_code = 0
                self.state = 0
                self.mode = 0
                
            # Basic connection methods
            def connect(self):
                self.connected = True
                return 0
                
            def disconnect(self):
                self.connected = False
                return 0
            
            # Error and warning management
            def clean_error(self):
                self.error_code = 0
                return 0
                
            def clean_warn(self):
                self.warn_code = 0
                return 0
            
            # Motion enable and state management
            def motion_enable(self, enable=True):
                return 0
                
            def set_mode(self, mode):
                self.mode = mode
                return 0
                
            def set_state(self, state):
                self.state = state
                return 0
            
            # Callback registration (no-op in simulation)
            def register_error_warn_changed_callback(self, callback):
                return 0
                
            def register_state_changed_callback(self, callback):
                return 0
                
            # Position and joint methods
            def get_position(self):
                return [0, self.controller.last_position]
                
            def get_servo_angle(self):
                return [0, self.controller.last_joints]
                
            def set_servo_angle(self, angle, speed=None, mvacc=None, wait=True):
                # Basic collision detection in simulation
                if len(angle) > self.controller.num_joints:
                    return 19  # Invalid parameter
                self.controller.last_joints = angle[:self.controller.num_joints]
                return 0
                
            def set_position(self, x, y, z, roll, pitch, yaw, speed=None, mvacc=None, wait=True, relative=False, motion_type=0):
                # Handle relative movement
                if relative:
                    current = self.controller.last_position
                    x += current[0]
                    y += current[1] 
                    z += current[2]
                    roll += current[3]
                    pitch += current[4]
                    yaw += current[5]
                
                self.controller.last_position = [x, y, z, roll, pitch, yaw]
                return 0
            
            def set_only_check_type(self, check_type):
                """Simulation of collision checking mode."""
                return 0
            
            # Velocity control methods
            def vc_set_cartesian_velocity(self, velocities):
                return 0
                
            def vc_set_joint_velocity(self, velocities):
                return 0
            
            # Emergency stop
            def emergency_stop(self):
                return 0
            
            # Home position
            def move_gohome(self, wait=True):
                self.controller.last_joints = [0] * self.controller.num_joints
                self.controller.last_position = [300, 0, 300, 180, 0, 0]
                return 0
            
            # Bio gripper methods
            def set_bio_gripper_enable(self, enable):
                return 0
                
            def open_bio_gripper(self, speed=None, wait=True):
                return 0
                
            def close_bio_gripper(self, speed=None, wait=True):
                return 0
            
            # Standard gripper methods
            def set_gripper_enable(self, enable):
                return 0
                
            def set_gripper_position(self, pos, speed=None, wait=True):
                return 0
            
            # RobotIQ gripper methods
            def robotiq_reset(self):
                return 0
                
            def robotiq_set_activate(self, activate):
                return 0
                
            def robotiq_set_position(self, position, speed=None, force=None, wait=True):
                return 0
                
            def robotiq_open(self, wait=True):
                return 0
                
            def robotiq_close(self, wait=True):
                return 0
            
            # Linear track methods
            def set_linear_track_enable(self, enable):
                return 0
                
            def set_linear_track_speed(self, speed):
                return 0
                
            def set_linear_track_pos(self, pos, speed=None, wait=True):
                self.controller.last_track_position = pos
                return 0
                
            def get_linear_track_pos(self):
                return [0, self.controller.last_track_position]
                
        return SimulationArm(self)
    
    # =============================================================================
    # PERFORMANCE TRACKING AND MONITORING
    # =============================================================================

    def _start_monitoring_thread(self):
        """Start background monitoring thread for performance tracking."""
        if self.simulation_mode:
            return  # Skip monitoring in simulation mode
            
        self._monitoring_active = True
        self._monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self._monitoring_thread.start()
        print("Performance monitoring thread started")

    def _monitoring_loop(self):
        """Background monitoring loop for predictive maintenance and performance tracking."""
        while self._monitoring_active:
            try:
                self._check_predictive_maintenance()
                self._monitor_performance_metrics()
                self._check_performance_thresholds()
                time.sleep(0.1)  # 10Hz monitoring
            except Exception as e:
                print(f"Monitoring error: {e}")
                time.sleep(1)  # Slower retry on error

    def _check_predictive_maintenance(self):
        """Check for predictive maintenance indicators."""
        if not self.arm or self.simulation_mode:
            return
        
        try:
            # Check temperatures
            temps = getattr(self.arm, 'temperatures', None)
            if temps:
                self.temperature_history.append({
                    'timestamp': time.time(),
                    'temperatures': temps
                })
                
                # Check temperature thresholds
                for i, temp in enumerate(temps):
                    if temp > self.temperature_thresholds['critical']:
                        self._trigger_maintenance_alert('temperature_critical', {
                            'joint': i + 1,
                            'temperature': temp,
                            'threshold': self.temperature_thresholds['critical']
                        })
                    elif temp > self.temperature_thresholds['warning']:
                        self._trigger_maintenance_alert('temperature_warning', {
                            'joint': i + 1,
                            'temperature': temp,
                            'threshold': self.temperature_thresholds['warning']
                        })
            
            # Check joint torques
            torques = getattr(self.arm, 'joints_torque', None)
            if torques:
                self.torque_history.append({
                    'timestamp': time.time(),
                    'torques': torques
                })
                self._analyze_torque_trends()
            
            # Check current consumption
            currents = getattr(self.arm, 'currents', None)
            if currents:
                self.current_history.append({
                    'timestamp': time.time(),
                    'currents': currents
                })
                self._analyze_current_trends()
                
        except Exception as e:
            print(f"Predictive maintenance check error: {e}")

    def _monitor_performance_metrics(self):
        """Monitor and update performance metrics."""
        if not self.arm or self.simulation_mode:
            return
        
        try:
            # Calculate TCP utilization (simplified)
            current_pos = getattr(self.arm, 'position', self.last_position)
            if current_pos and isinstance(current_pos, (list, tuple)) and len(current_pos) >= 3:
                # Simple utilization based on movement
                tcp_util = min(100, abs(sum(current_pos[:3]) / 3000 * 100))
                self.performance_metrics['tcp_utilization'].append(tcp_util)
            
            # Calculate joint utilization
            current_joints = getattr(self.arm, 'angles', self.last_joints)
            if current_joints and isinstance(current_joints, (list, tuple)) and len(current_joints) > 0:
                try:
                    # Safely convert to numeric values
                    numeric_joints = [float(angle) for angle in current_joints if isinstance(angle, (int, float))]
                    if numeric_joints:
                        joint_util = min(100, sum(abs(angle) for angle in numeric_joints) / len(numeric_joints))
                        self.performance_metrics['joint_utilization'].append(joint_util)
                except (ValueError, TypeError):
                    pass  # Skip if conversion fails
            
        except Exception as e:
            print(f"Performance monitoring error: {e}")

    def _check_performance_thresholds(self):
        """Check if performance metrics exceed thresholds."""
        try:
            # Check cycle times
            if self.performance_metrics['cycle_times']:
                avg_cycle_time = sum(self.performance_metrics['cycle_times']) / len(self.performance_metrics['cycle_times'])
                if avg_cycle_time > self.performance_thresholds['max_cycle_time']:
                    self._trigger_maintenance_alert('performance_cycle_time', {
                        'average_cycle_time': avg_cycle_time,
                        'threshold': self.performance_thresholds['max_cycle_time']
                    })
            
            # Check utilization
            if self.performance_metrics['tcp_utilization']:
                avg_tcp_util = sum(self.performance_metrics['tcp_utilization']) / len(self.performance_metrics['tcp_utilization'])
                if avg_tcp_util > self.performance_thresholds['max_utilization']:
                    self._trigger_maintenance_alert('performance_tcp_utilization', {
                        'average_utilization': avg_tcp_util,
                        'threshold': self.performance_thresholds['max_utilization']
                    })
                    
        except Exception as e:
            print(f"Performance threshold check error: {e}")

    def _analyze_torque_trends(self):
        """Analyze torque trends for predictive maintenance."""
        if len(self.torque_history) < 10:
            return
        
        try:
            # Simple trend analysis - could be enhanced with ML
            recent_torques = list(self.torque_history)[-10:]
            
            for joint_idx in range(self.num_joints):
                if joint_idx < len(recent_torques[0]['torques']):
                    torque_values = [entry['torques'][joint_idx] for entry in recent_torques]
                    avg_torque = sum(torque_values) / len(torque_values)
                    
                    # Check for abnormal torque levels (simplified)
                    normal_torque_threshold = 50  # This should be calibrated per joint
                    if avg_torque > normal_torque_threshold:
                        self._trigger_maintenance_alert('torque_high', {
                            'joint': joint_idx + 1,
                            'average_torque': avg_torque,
                            'threshold': normal_torque_threshold
                        })
                        
        except Exception as e:
            print(f"Torque analysis error: {e}")

    def _analyze_current_trends(self):
        """Analyze current consumption trends."""
        if len(self.current_history) < 10:
            return
        
        try:
            recent_currents = list(self.current_history)[-10:]
            
            for joint_idx in range(self.num_joints):
                if joint_idx < len(recent_currents[0]['currents']):
                    current_values = [entry['currents'][joint_idx] for entry in recent_currents]
                    avg_current = sum(current_values) / len(current_values)
                    
                    # Check for abnormal current levels
                    normal_current_threshold = 2.0  # Amperes - should be calibrated
                    if avg_current > normal_current_threshold:
                        self._trigger_maintenance_alert('current_high', {
                            'joint': joint_idx + 1,
                            'average_current': avg_current,
                            'threshold': normal_current_threshold
                        })
                        
        except Exception as e:
            print(f"Current analysis error: {e}")

    def _trigger_maintenance_alert(self, alert_type, data):
        """Trigger maintenance alert."""
        alert = {
            'timestamp': time.time(),
            'type': alert_type,
            'data': data,
            'severity': 'warning' if 'warning' in alert_type else 'critical'
        }
        
        print(f"Maintenance Alert: {alert_type} - {data}")
        
        # Store in error history with maintenance type
        maintenance_error = {
            'timestamp': time.time(),
            'type': 'maintenance',
            'alert_type': alert_type,
            'data': data,
            'severity': alert['severity']
        }
        self.error_history.append(maintenance_error)
        
        # Trigger maintenance callbacks
        for callback in self._callbacks.get('maintenance_alert', []):
            try:
                callback(alert)
            except Exception as e:
                print(f"Maintenance callback error: {e}")

    def stop_monitoring(self):
        """Stop the monitoring thread."""
        if self._monitoring_active:
            self._monitoring_active = False
            if self._monitoring_thread and self._monitoring_thread.is_alive():
                self._monitoring_thread.join(timeout=1)
            print("Performance monitoring stopped")

    # =============================================================================
    # COLLISION DETECTION AND VALIDATION
    # =============================================================================

    def _check_joint_collision(self, angles):
        """Joint collision checking for simulation mode."""
        if self.simulation_mode:
            # Use utility function for simulation collision check
            collision_detected = check_joint_collision_simulation(angles, self.joint_limits)
            if collision_detected:
                print(f"Joint collision detected at angles: {angles}")
            return collision_detected
        else:
            # For hardware, rely on SDK's collision checking
            self.arm.set_only_check_type(1) # Check without moving
            check_code = self.arm.set_servo_angle(angles, speed=self.angle_speed, mvacc=self.angle_acc)
            self.arm.set_only_check_type(0) # Reset to normal mode
            
            if check_code != 0:
                print(f"Joint collision detected: code={check_code}")
                return True
        return False
    
    def _check_workspace_collision(self, pose):
        """Workspace collision checking for simulation mode."""
        if not self.simulation_mode:
            return False
            
        # Check workspace boundaries
        if not self._validate_target_position(pose):
            return True
            
        # Use utility function for collision zone checking
        collision_zones = self.safety_config.get('collision_zones', [])
        collision_detected, zone_name = check_workspace_collision_simulation(pose, collision_zones)
        
        if collision_detected:
            print(f"Collision detected with {zone_name} at position [{pose[0]}, {pose[1]}, {pose[2]}]")
        
        return collision_detected

    def get_performance_metrics(self):
        """Get current performance metrics summary."""
        metrics = {}
        
        for metric_type, data in self.performance_metrics.items():
            if data:
                metrics[metric_type] = {
                    'current': data[-1] if data else 0,
                    'average': sum(data) / len(data),
                    'min': min(data),
                    'max': max(data),
                    'count': len(data)
                }
            else:
                metrics[metric_type] = {
                    'current': 0, 'average': 0, 'min': 0, 'max': 0, 'count': 0
                }
        
        return metrics

    def get_maintenance_status(self):
        """Get predictive maintenance status."""
        status = {
            'temperature': {'status': 'normal', 'alerts': []},
            'torque': {'status': 'normal', 'alerts': []},
            'current': {'status': 'normal', 'alerts': []},
            'overall_health': 'good'
        }
        
        # Check recent maintenance alerts
        recent_alerts = [error for error in list(self.error_history)[-50:] 
                        if error.get('type') == 'maintenance']
        
        for alert in recent_alerts:
            alert_type = alert.get('alert_type', '')
            if 'temperature' in alert_type:
                status['temperature']['alerts'].append(alert)
                if alert.get('severity') == 'critical':
                    status['temperature']['status'] = 'critical'
                elif status['temperature']['status'] == 'normal':
                    status['temperature']['status'] = 'warning'
            elif 'torque' in alert_type:
                status['torque']['alerts'].append(alert)
                if alert.get('severity') == 'critical':
                    status['torque']['status'] = 'critical'
                elif status['torque']['status'] == 'normal':
                    status['torque']['status'] = 'warning'
            elif 'current' in alert_type:
                status['current']['alerts'].append(alert)
                if alert.get('severity') == 'critical':
                    status['current']['status'] = 'critical'
                elif status['current']['status'] == 'normal':
                    status['current']['status'] = 'warning'
        
        # Determine overall health
        if any(comp['status'] == 'critical' for comp in [status['temperature'], status['torque'], status['current']]):
            status['overall_health'] = 'critical'
        elif any(comp['status'] == 'warning' for comp in [status['temperature'], status['torque'], status['current']]):
            status['overall_health'] = 'warning'
        
        return status

    # =============================================================================
    # COLLISION DETECTION AND VALIDATION
    # =============================================================================

    def initialize(self):
        """
        Initializes the robot arm connection and sets the initial state.
        Components are only enabled if auto_enable=True.
        Supports both hardware and simulation modes.
        """
        mode_str = "Simulation" if self.simulation_mode else "Hardware"
        print(f"Initializing Robot Arm ({mode_str})...")
        
        try:
            self.states['connection'] = ComponentState.ENABLING
            
            # Create the XArmAPI connection if not already created
            if self.arm is None:
                if self.simulation_mode:
                    # Use official SDK simulation mode with do_not_open=True
                    self.arm = XArmAPI(self.xarm_config.get('host'), do_not_open=True)
                    print("Created simulation instance (do_not_open=True)")
                else:
                    # Normal hardware connection
                    self.arm = XArmAPI(self.host)
            
            # Connect only if not in simulation mode
            if not self.simulation_mode:
                self.arm.connect()
                
                if not self.arm.connected:
                    self.states['connection'] = ComponentState.ERROR
                    print("Failed to connect to robot arm")
                    return False
            else:
                print("Simulation mode: Skipping hardware connection")
                
            self.states['connection'] = ComponentState.ENABLED
            
            # Clear any existing errors/warnings (skip in simulation)
            if not self.simulation_mode:
                self.arm.clean_warn()
                self.arm.clean_error()
            
            # Enable motion and set modes
            self.states['arm'] = ComponentState.ENABLING
            
            if not self.simulation_mode:
                self.arm.motion_enable(enable=True)
                self.arm.set_mode(0)  # Position control mode
                self.arm.set_state(0)  # Ready state
                time.sleep(1)
                
                # Register callbacks for monitoring
                self.arm.register_error_warn_changed_callback(self._error_warn_callback)
                self.arm.register_state_changed_callback(self._state_changed_callback)
            else:
                print("Simulation mode: Skipping motion enable and callbacks")
            
            self.states['arm'] = ComponentState.ENABLED
            
            # Auto-enable components if requested
            if self.auto_enable:
                if self.gripper_type != 'none':
                    self.enable_gripper_component()
                
                if self.enable_track:
                    self.enable_track_component()
            
            # Start monitoring thread for Phase 2 performance tracking
            if not self.simulation_mode:
                self._start_monitoring_thread()
            
            print(f"{'Simulation' if self.simulation_mode else 'Hardware'} xArm Controller Initialized")
            self._update_positions()
            if self.enable_track:
                self._update_track_position()
            return True
            
        except Exception as e:
            print(f"Failed to initialize robot arm: {e}")
            self.states['arm'] = ComponentState.ERROR
            self.states['connection'] = ComponentState.ERROR
            return False

    def enable_gripper_component(self):
        """Enable the gripper component based on configured type."""
        if self.gripper_type == 'none':
            print("No gripper configured")
            return False
            
        try:
            self.states['gripper'] = ComponentState.ENABLING
            success = False
            
            if self.simulation_mode:
                # In simulation mode, assume gripper is always available
                success = True
                print(f"Simulation mode: {self.gripper_type.title()} gripper enabled (simulated)")
            else:
                if self.gripper_type == 'bio':
                    success = self._enable_bio_gripper_internal()
                elif self.gripper_type == 'standard':
                    success = self._enable_standard_gripper_internal()
                elif self.gripper_type == 'robotiq':
                    success = self._initialize_robotiq_gripper_internal()
            
            if success:
                self.states['gripper'] = ComponentState.ENABLED
                if not self.simulation_mode:
                    print(f"{self.gripper_type.title()} gripper enabled")
            else:
                self.states['gripper'] = ComponentState.ERROR
                print(f"Failed to enable {self.gripper_type} gripper")
                
            return success
            
        except Exception as e:
            self.states['gripper'] = ComponentState.ERROR
            print(f"Error enabling {self.gripper_type} gripper: {e}")
            return False

    def enable_track_component(self):
        """Enable the linear track component."""
        if not self.enable_track:
            print("Linear track disabled")
            return False
            
        try:
            self.states['track'] = ComponentState.ENABLING
            
            if self.simulation_mode:
                # In simulation mode, assume track is always available
                success = True
                print("Simulation mode: Linear track enabled (simulated)")
            else:
                success = self.enable_linear_track()
            
            if success:
                self.states['track'] = ComponentState.ENABLED
                if not self.simulation_mode:
                    print("Linear track enabled")
                    self._update_track_position()
            else:
                self.states['track'] = ComponentState.ERROR
                print("Failed to enable linear track")
                
            return success
            
        except Exception as e:
            self.states['track'] = ComponentState.ERROR
            print(f"Error enabling linear track: {e}")
            return False

    def disable_gripper_component(self):
        """Disable the gripper component."""
        if self.gripper_type == 'none':
            return True
            
        try:
            # Different grippers have different disable methods
            if self.gripper_type == 'bio':
                code = self.arm.set_bio_gripper_enable(False)
            elif self.gripper_type == 'standard':
                code = self.arm.set_gripper_enable(False)
            elif self.gripper_type == 'robotiq':
                code = self.arm.robotiq_set_activate(False)
            
            if code == 0:
                self.states['gripper'] = ComponentState.DISABLED
                print(f"{self.gripper_type.title()} gripper disabled")
                return True
            else:
                self.states['gripper'] = ComponentState.ERROR
                return False
                
        except Exception as e:
            self.states['gripper'] = ComponentState.ERROR
            print(f"Error disabling {self.gripper_type} gripper: {e}")
            return False

    def disable_track_component(self):
        """Disable the linear track component."""
        if not self.enable_track:
            return True
            
        try:
            code = self.arm.set_linear_track_enable(False)
            if code == 0:
                self.states['track'] = ComponentState.DISABLED
                print("Linear track disabled")
                return True
            else:
                self.states['track'] = ComponentState.ERROR
                return False
                
        except Exception as e:
            self.states['track'] = ComponentState.ERROR
            print(f"Error disabling linear track: {e}")
            return False

    def _update_positions(self):
        """Update cached position information."""
        if not self.arm:
            return
            
        try:
            if self.simulation_mode:
                # In simulation mode, use default positions
                self.last_position = [300, 0, 300, 180, 0, 0]  # Default Cartesian position
                self.last_joints = [0] * self.num_joints  # Default joint angles
                return
                
            # Update Cartesian position
            ret = self.arm.get_position()
            if ret[0] == 0:
                self.last_position = ret[1:]
            
            # Update joint angles
            ret = self.arm.get_servo_angle()
            if ret[0] == 0:
                self.last_joints = ret[1]
                
        except Exception as e:
            print(f"Warning: Failed to update positions: {e}")

    def _update_track_position(self):
        """Update cached track position."""
        if not self.arm or not self.enable_track or self.states['track'] != ComponentState.ENABLED:
            return
            
        try:
            ret = self.arm.get_linear_track_pos()
            if ret[0] == 0:
                self.last_track_position = ret[1]
        except Exception as e:
            print(f"Warning: Failed to update track position: {e}")

    def _error_warn_callback(self, data):
        """Callback for error/warning changes with automatic recovery."""
        if data:
            if data.get('error_code', 0) != 0:
                error_code = data['error_code']
                self.last_error_code = error_code
                
                # Log error to history
                error_info = {
                    'timestamp': time.time(),
                    'error_code': error_code,
                    'warn_code': data.get('warn_code', 0)
                }
                self.error_history.append(error_info)
                
                # Trigger error callbacks
                self._trigger_callbacks('error_occurred', error_info)
                
                # Attempt automatic recovery
                recovery_success = self._handle_error_with_recovery(error_code)
                
                if not recovery_success:
                    # If recovery failed, set error state
                    self.alive = False
                    self.states['arm'] = ComponentState.ERROR
                    print(f'Error {error_code} detected, automatic recovery failed')
                else:
                    print(f'Error {error_code} detected and automatically recovered')
            
            if data.get('warn_code', 0) != 0:
                self.last_warn_code = data['warn_code']
                print(f'Warning: {data["warn_code"]}')

    def _state_changed_callback(self, data):
        """Callback for state changes."""
        if not self._ignore_exit_state and data and data['state'] == 4:
            self.alive = False
            self.states['arm'] = ComponentState.ERROR
            # Trigger state change callbacks
            self._trigger_callbacks('state_changed', {
                'old_state': self.states['arm'],
                'new_state': ComponentState.ERROR,
                'reason': 'Emergency state detected'
            })
            print('State 4 detected, stopping operations')

    def unregister_callback(self, event_type: str, callback: Callable):
        """Unregister a callback."""
        if event_type in self._callbacks and callback in self._callbacks[event_type]:
            self._callbacks[event_type].remove(callback)

    def _trigger_callbacks(self, event_type: str, data: Any = None):
        """Trigger all callbacks for a specific event type."""
        for callback in self._callbacks.get(event_type, []):
            try:
                callback(data)
            except Exception as e:
                print(f"Error in callback for {event_type}: {e}")

    def check_code(self, code, operation_name):
        """Check if an operation was successful."""
        if not self.is_alive or code != 0:
            self.alive = False
            state = self.arm.state if self.arm else None
            error = self.arm.error_code if self.arm else None
            return check_operation_result(code, operation_name, state, error, self.simulation_mode)
        return True

    @property
    def is_alive(self):
        """Check if the robot is in a safe operating state."""
        if self.simulation_mode:
            # In simulation mode, always return True if initialized
            return self.alive and self.arm is not None
            
        if self.alive and self.arm and self.arm.connected and self.arm.error_code == 0:
            if self._ignore_exit_state:
                return True
            if self.arm.state == 5:
                cnt = 0
                while self.arm.state == 5 and cnt < 5:
                    cnt += 1
                    time.sleep(0.1)
            return self.arm.state < 4
        return False

    # =============================================================================
    # STATE MONITORING METHODS
    # =============================================================================
    
    def get_system_status(self):
        """Get comprehensive system status."""
        self._update_positions()
        if self.enable_track:
            self._update_track_position()
            
        return {
            'timestamp': time.time(),
            'connection': {
                'connected': self.arm.connected if self.arm else False,
                'state': self.states['connection'].value,
                'alive': self.is_alive
            },
            'arm': {
                'state': self.states['arm'].value,
                'mode': getattr(self.arm, 'mode', None) if self.arm else None,
                'robot_state': getattr(self.arm, 'state', None) if self.arm else None,
                'position': self.last_position,
                'joints': self.last_joints,
                'error_code': self.arm.error_code if self.arm else 0,
                'warn_code': getattr(self.arm, 'warn_code', 0) if self.arm else 0
            },
            'gripper': {
                'type': self.gripper_type,
                'state': self.states['gripper'].value,
                'has_gripper': self.has_gripper()
            },
            'track': {
                'state': self.states['track'].value,
                'has_track': self.has_track(),
                'position': self.last_track_position
            },
            'errors': {
                'last_error': self.last_error_code,
                'last_warning': self.last_warn_code,
                'error_count': len(self.error_history)
            }
        }

    def get_component_states(self):
        """Get just the component states."""
        return {k: v.value for k, v in self.states.items()}

    def is_component_enabled(self, component):
        """Check if a specific component is enabled."""
        return self.states.get(component, ComponentState.UNKNOWN) == ComponentState.ENABLED

    def get_error_history(self, count=10):
        """Get recent error history."""
        return list(self.error_history)[-count:] if self.error_history else []

    def clear_errors(self):
        """
        Clear all robot errors and reset error states.
        This includes clearing xArm SDK errors, warnings, and controller error history.
        """
        if not self.arm:
            print("Cannot clear errors: No arm connection")
            return False
            
        try:
            if self.simulation_mode:
                print("[SIM] Clearing all errors and warnings")
                self.error_history.clear()
                self.last_error_code = 0
                self.last_warn_code = 0
                self.alive = True
                return True
                
            # Clear xArm SDK errors and warnings
            print("Clearing robot errors and warnings...")
            
            # Clear errors and warnings
            error_clear_code = self.arm.clean_error()
            warn_clear_code = self.arm.clean_warn()
            
            # Reset error tracking
            self.error_history.clear()
            self.last_error_code = 0
            self.last_warn_code = 0
            
            # Reset alive state if errors were cleared successfully
            if error_clear_code == 0 and warn_clear_code == 0:
                self.alive = True
                print("✅ All errors and warnings cleared successfully")
                
                # Check if we need to re-enable components
                if self.auto_enable:
                    print("Re-enabling components...")
                    if self.states['arm'] == ComponentState.ERROR:
                        self.states['arm'] = ComponentState.ENABLED
                    if self.has_gripper() and self.states['gripper'] == ComponentState.ERROR:
                        self.enable_gripper_component()
                    if self.has_track() and self.states['track'] == ComponentState.ERROR:
                        self.enable_track_component()
                        
                return True
            else:
                print(f"⚠️ Error clearing partially failed: error_clear={error_clear_code}, warn_clear={warn_clear_code}")
                return False
                
        except Exception as e:
            print(f"❌ Failed to clear errors: {e}")
            return False

    # =============================================================================
    # LINEAR/CARTESIAN MOVEMENTS
    # =============================================================================
    
    def move_to_position(self, x, y, z, roll=None, pitch=None, yaw=None, 
                        speed=None, check_collision=True, motion_type=0, wait=True):
        """
        Move to a Cartesian position with collision checking and intelligent planning.
        
        Args:
            x, y, z: Target position coordinates
            roll, pitch, yaw: Target orientation (defaults: 180, 0, 0)
            speed: Movement speed (default: tcp_speed)
            check_collision: Enable collision detection and validation
            motion_type: Motion planning type (0=default, 1=alternative)
            wait: Wait for movement completion
            
        Returns:
            bool: True if movement successful, False otherwise
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        # Set defaults
        if roll is None: roll = 180
        if pitch is None: pitch = 0
        if yaw is None: yaw = 0
        if speed is None: speed = self.tcp_speed
        
        target_pos = [x, y, z, roll, pitch, yaw]
        
        # Pre-motion validation
        if not self._validate_target_position(target_pos):
                return False
        
        # Collision checking
        if check_collision and not self.simulation_mode:
            # Use SDK's built-in collision checking
            self.arm.set_only_check_type(1)  # Check without moving
            check_code = self.arm.set_position(x, y, z, roll, pitch, yaw, speed=speed)
            self.arm.set_only_check_type(0)  # Reset to normal mode
            
            if check_code != 0:
                error_details = getattr(self.arm, 'only_check_result', None)
                print(f"Motion planning failed: code={check_code}, details={error_details}")
                
                # Try alternative motion planning
                if motion_type == 0:
                    print("Trying alternative motion planning (motion_type=1)")
                    return self.move_to_position(x, y, z, roll, pitch, yaw, 
                                                speed, check_collision, motion_type=1, wait=wait)
                else:
                    print("Alternative motion planning also failed")
                    return False
        
        # Execute the movement with performance tracking
        self._motion_in_progress = True
        start_time = time.time()
        
        try:
            if self.simulation_mode:
                if self._check_workspace_collision(target_pos):
                    return False
                print(f"[SIM] Moved to position {target_pos}")
                self.last_position = target_pos
                success = True
            else:
                code = self.arm.set_position(x, y, z, roll, pitch, yaw, 
                                           speed=speed, wait=wait, motion_type=motion_type)
                success = self.check_code(code, f'move_to_position({x}, {y}, {z})')
            
            # Track performance metrics
            cycle_time = time.time() - start_time
            self.performance_metrics['cycle_times'].append(cycle_time)
            
            # Track command success rate
            self.performance_metrics['command_success_rate'].append(1.0 if success else 0.0)
            
            if success:
                self._update_positions()
                # Calculate and track accuracy error
                if not self.simulation_mode:
                    actual_pos = self.get_current_position()
                    if actual_pos:
                        accuracy_error = ((actual_pos[0] - x)**2 + (actual_pos[1] - y)**2 + (actual_pos[2] - z)**2)**0.5
                        self.performance_metrics['accuracy_errors'].append(accuracy_error)
                
            return success
            
        finally:
            self._motion_in_progress = False

    def move_to_named_location(self, location_name, speed=None):
        """
        Move to a predefined location from the location config.
        Supports both joint-based and Cartesian-based location definitions.
        """
        # Check if locations are defined in config
        if 'locations' not in self.location_config:
            print(f"Error: No 'locations' section found in location config")
            return False
            
        if location_name not in self.location_config['locations']:
            print(f"Error: Location '{location_name}' not found in config")
            return False
            
        location = self.location_config['locations'][location_name]
        
        # Detect format: list = joint angles, dict = Cartesian coordinates
        if isinstance(location, list):
            # Joint-based location (e.g., [0.0, 0.0, 0.0, 0.0, 0.0])
            print(f"Moving to location '{location_name}' using joint angles: {location}")
            return self.move_joints(angles=location, speed=speed)
        elif isinstance(location, dict):
            # Cartesian-based location (e.g., {x: 300, y: 0, z: 300, ...})
            print(f"Moving to location '{location_name}' using Cartesian coordinates")
            return self.move_to_position(
                x=location['x'], y=location['y'], z=location['z'],
                roll=location.get('roll'), pitch=location.get('pitch'), yaw=location.get('yaw'),
                speed=speed
            )
        else:
            print(f"Error: Invalid location format for '{location_name}'. Expected list (joint angles) or dict (Cartesian coordinates)")
            return False

    def move_relative(self, dx=0.0, dy=0.0, dz=0.0, droll=0.0, dpitch=0.0, dyaw=0.0, speed=None):
        """
        Move relative to current position (linear movement).
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        if speed is None:
            speed = self.tcp_speed
            
        code = self.arm.set_position(x=dx, y=dy, z=dz, roll=droll, pitch=dpitch, yaw=dyaw,
                                   speed=speed, relative=True, wait=True)
        success = self.check_code(code, f'move_relative({dx}, {dy}, {dz})')
        if success:
            self._update_positions()
        return success

    # =============================================================================
    # JOINT MOVEMENTS
    # =============================================================================
    
    def move_joints(self, angles, speed=None, acceleration=None, 
                   wait=True, check_collision=True):
        """
        Move individual joints to specified angles with comprehensive safety checking.
        
        Args:
            angles (list): Joint angles in degrees
            speed (float, optional): Joint movement speed (degrees/second)
            acceleration (float, optional): Joint acceleration (degrees/second²)
            wait (bool): Wait for movement completion
            check_collision (bool): Enable collision detection and validation
            
        Returns:
            bool: True if movement successful, False otherwise
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        if speed is None: speed = self.angle_speed
        if acceleration is None: acceleration = self.angle_acc
        
        # Validate joint angles
        if not self._validate_joint_angles(angles):
            return False
        
        # Collision checking
        if check_collision:
            if self.simulation_mode:
                if self._check_joint_collision(angles):
                    return False
            else:
                # Use SDK collision checking for joints
                self.arm.set_only_check_type(1)
                check_code = self.arm.set_servo_angle(angles, speed=speed, mvacc=acceleration)
                self.arm.set_only_check_type(0)
                
                if check_code != 0:
                    print(f"Joint motion planning failed: {check_code}")
                    return False
        
        # Execute movement with performance tracking
        self._motion_in_progress = True
        start_time = time.time()
        
        try:
            if self.simulation_mode:
                print(f"[SIM] Joints moved to {angles}")
                self.last_joints = angles[:self.num_joints]  # Store only valid joints for model
                success = True
            else:
                code = self.arm.set_servo_angle(angles, speed=speed, mvacc=acceleration, wait=wait)
                success = self.check_code(code, f'move_joints({angles})')
            
            # Track performance metrics
            cycle_time = time.time() - start_time
            self.performance_metrics['cycle_times'].append(cycle_time)
            
            # Track command success rate
            self.performance_metrics['command_success_rate'].append(1.0 if success else 0.0)
            
            if success:
                self._update_positions()
                
            return success
            
        finally:
            self._motion_in_progress = False

    def move_single_joint(self, joint_id, angle, speed=None, wait=True):
        """
        Move a single joint while keeping others in place.
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        # Get current joint angles
        ret = self.arm.get_servo_angle()
        if ret[0] != 0:
            print("Failed to get current joint angles")
            return False
            
        # Handle case where ret[1] might be a list or direct value
        current_angles = ret[1] if isinstance(ret[1], list) else list(ret[1:])
        if len(current_angles) <= joint_id:
            print(f"Invalid joint_id {joint_id} for {len(current_angles)} joints")
            return False
            
        current_angles[joint_id] = angle
        
        return self.move_joints(current_angles, speed=speed, wait=wait)

    # =============================================================================
    # VELOCITY CONTROL
    # =============================================================================
    
    def set_cartesian_velocity(self, vx=0.0, vy=0.0, vz=0.0, vroll=0.0, vpitch=0.0, vyaw=0.0):
        """
        Control the robot using Cartesian velocity commands.
        Useful for real-time control or jogging.
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        code = self.arm.vc_set_cartesian_velocity([vx, vy, vz, vroll, vpitch, vyaw])
        return self.check_code(code, f'set_cartesian_velocity')

    def set_joint_velocity(self, velocities):
        """
        Control individual joints using velocity commands.
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        code = self.arm.vc_set_joint_velocity(velocities)
        return self.check_code(code, f'set_joint_velocity')

    def stop_motion(self):
        """Stop all motion immediately."""
        self.arm.emergency_stop()

    # =============================================================================
    # GRIPPER CONTROL - Multiple Types Supported
    # =============================================================================
    
    def has_gripper(self):
        """Check if a gripper is configured."""
        return self.gripper_type != 'none'

    # Universal Gripper Methods
    def open_gripper(self, speed=None, wait=True):
        """Open the gripper (works with any configured gripper type)."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
            
        if self.simulation_mode:
            print(f"[SIM] {self.gripper_type.title()} gripper opened")
            return True
            
        if self.gripper_type == 'bio':
            return self._open_bio_gripper_internal(speed=speed, wait=wait)
        elif self.gripper_type == 'standard':
            max_position = self.gripper_config.get('MAX_POSITION', 850)
            return self._set_gripper_position_internal(max_position, speed=speed, wait=wait)
        elif self.gripper_type == 'robotiq':
            if not self.simulation_mode:
                code = self.arm.robotiq_open(wait=wait)
                return self.check_code(code, 'open_robotiq_gripper')
            return True
        else:
            print("No gripper configured")
            return False

    def close_gripper(self, speed=None, wait=True):
        """Close the gripper (works with any configured gripper type)."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
            
        if self.simulation_mode:
            print(f"[SIM] {self.gripper_type.title()} gripper closed")
            return True
            
        if self.gripper_type == 'bio':
            return self._close_bio_gripper_internal(speed=speed, wait=wait)
        elif self.gripper_type == 'standard':
            return self._set_gripper_position_internal(0, speed=speed, wait=wait)
        elif self.gripper_type == 'robotiq':
            if not self.simulation_mode:
                code = self.arm.robotiq_close(wait=wait)
                return self.check_code(code, 'close_robotiq_gripper')
            return True
        else:
            print("No gripper configured")
            return False

    # =============================================================================
    # LINEAR TRACK CONTROL (Optional)
    # =============================================================================
    
    def has_track(self):
        """Check if linear track is enabled."""
        return self.enable_track

    def enable_linear_track(self):
        """Enable the linear track."""
        if not self.enable_track:
            print("Linear track is disabled")
            return False
        code = self.arm.set_linear_track_enable(True)
        return self.check_code(code, 'enable_linear_track')

    def set_track_speed(self, speed):
        """Set the linear track speed."""
        if not self.is_component_enabled('track'):
            print("Linear track is not enabled")
            return False
        code = self.arm.set_linear_track_speed(speed)
        return self.check_code(code, 'set_linear_track_speed')

    def move_track_to_position(self, position, speed=None, wait=True):
        """Move the linear track to a specific position with validation."""
        if not self.is_component_enabled('track'):
            print("Linear track is not enabled")
            return False

        # Validation
        if not self._validate_track_position(position):
            return False

        if speed is None:
            speed = self.track_config.get('Speed', 200)
        
        # Validate speed
        if not self._validate_track_speed(speed):
            return False
        
        # Performance tracking
        self._motion_in_progress = True
        start_time = time.time()
        
        try:
            if self.simulation_mode:
                print(f"[SIM] Linear track moved to position {position}mm at {speed}mm/s")
                self.last_track_position = position
                success = True
            else:
                code = self.arm.set_linear_track_pos(speed=speed, pos=position, wait=wait)
                success = self.check_code(code, f'move_track_to_position({position})')
            
            # Track performance metrics
            cycle_time = time.time() - start_time
            self.performance_metrics['cycle_times'].append(cycle_time)
            self.performance_metrics['command_success_rate'].append(1.0 if success else 0.0)
            
            if success:
                self._update_track_position()
                # Calculate accuracy for track movement
                if not self.simulation_mode:
                    actual_pos = self.get_track_position()
                    if actual_pos is not None:
                        accuracy_error = abs(actual_pos - position)
                        self.performance_metrics['accuracy_errors'].append(accuracy_error)
                        
            return success
            
        finally:
            self._motion_in_progress = False
    
    def _validate_track_position(self, position):
        """Validation for track position."""
        is_valid, message = validate_track_position(
            position, 
            (0, 700), 
            self.track_config.get('danger_zones', [])
        )
        
        if not is_valid:
            print(f"Error: {message}")
            self._trigger_callbacks('safety_violation', {
                'type': 'track_position',
                'value': position,
                'message': message
            })
            return False
            
        return True
    
    def _validate_track_speed(self, speed):
        """Validation for track speed."""
        is_valid, message = validate_track_speed(speed, (1, 1000))
        
        if not is_valid:
            print(f"Error: {message}")
            self._trigger_callbacks('safety_violation', {
                'type': 'track_speed',
                'value': speed,
                'message': message
            })
            return False
            
        return True

    def reset_track(self):
        """Reset the linear track to home position."""
        if not self.is_component_enabled('track'):
            print("Linear track is not enabled")
            return False
        return self.move_track_to_position(0)

    def get_track_position(self):
        """Get current linear track position."""
        if not self.is_component_enabled('track'):
            print("Linear track is not enabled")
            return None
        
        if self.simulation_mode:
            return getattr(self, 'last_track_position', 0)
            
        ret = self.arm.get_linear_track_pos()
        if ret[0] == 0:
            self.last_track_position = ret[1]
            return ret[1]
        return None

    # =============================================================================
    # UTILITY METHODS
    # =============================================================================

    def get_current_position(self):
        """Get the current Cartesian position."""
        ret = self.arm.get_position()
        if ret[0] == 0:
            # ret[1] should be the position list [x, y, z, roll, pitch, yaw]
            position = ret[1] if len(ret) > 1 else ret[1:]
            self.last_position = position
            return position
        return None

    def get_current_joints(self):
        """Get the current joint angles."""
        ret = self.arm.get_servo_angle()
        if ret[0] == 0:
            # Handle case where ret[1] might be a list or direct value
            joints = ret[1] if isinstance(ret[1], list) else list(ret[1:])
            # Handle case where 7-axis robots return 7 values but we only want first 6
            if isinstance(joints, list) and len(joints) > 6:
                joints = joints[:6]
            self.last_joints = joints
            return joints
        return None

    def go_home(self):
        """Move to the home position using safety features."""
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
        
        # Use movement with home position
        home_joints = [0] * self.num_joints
        return self.move_joints(home_joints, check_collision=True, wait=True)

    def get_named_locations(self):
        """Returns a list of all named locations."""
        if self.location_config and 'locations' in self.location_config:
            return list(self.location_config['locations'].keys())
        return []

    def get_system_info(self):
        """Get information about the configured system."""
        info = {
            'model': self.model,
            'num_joints': self.num_joints,
            'gripper_type': self.gripper_type,
            'has_gripper': self.has_gripper(),
            'has_track': self.has_track(),
            'connected': self.arm.connected if self.arm else False,
            'is_alive': self.is_alive,
            'auto_enable': self.auto_enable,
            'component_states': self.get_component_states()
        }
        return info
    
    def get_model(self):
        """Get the robot model number."""
        return self.model
    
    def get_num_joints(self):
        """Get the number of joints for this robot model."""
        return self.num_joints

    def disconnect(self):
        """Disconnects from the robot arm."""
        print("Disconnecting Robot Arm...")
        self.states['connection'] = ComponentState.DISABLED
        self.states['arm'] = ComponentState.DISABLED
        if self.arm:
            self.arm.disconnect()
        print("Robot Arm Disconnected.")

    # Safety validation
    def _validate_target_position(self, position: List[float]) -> bool:
        """Validate target position against safety boundaries."""
        is_valid, error_msg = validate_target_position(position, self.safety_boundaries)
        if not is_valid:
            self._trigger_callbacks('safety_violation', {'type': 'validation_error', 'message': error_msg})
        return is_valid

    def _validate_joint_angles(self, angles: List[float]) -> bool:
        """Validate joint angles against model-specific limits."""
        is_valid, error_msg = validate_joint_angles(angles, self.joint_limits)
        if not is_valid:
            self._trigger_callbacks('safety_violation', {'type': 'joint_validation_error', 'message': error_msg})
        return is_valid

    # Error recovery methods
    def _handle_error_with_recovery(self, error_code: int) -> bool:
        """Handle errors with intelligent recovery strategies."""
        # Track recovery attempts
        if error_code not in self.recovery_attempts:
            self.recovery_attempts[error_code] = 0
        
        # Check if we've exceeded max recovery attempts
        if self.recovery_attempts[error_code] >= self.max_recovery_attempts:
            print(f"Max recovery attempts ({self.max_recovery_attempts}) exceeded for error {error_code}")
            self._trigger_callbacks('error_occurred', {
                'error_code': error_code,
                'recovery_failed': True,
                'attempts': self.recovery_attempts[error_code]
            })
            return False
        
        # Increment recovery attempts
        self.recovery_attempts[error_code] += 1
        
        # Try recovery strategy if available
        if error_code in self.error_recovery_strategies:
            print(f"Attempting recovery for error {error_code} (attempt {self.recovery_attempts[error_code]})")
            try:
                success = self.error_recovery_strategies[error_code]()
                if success:
                    print(f"Successfully recovered from error {error_code}")
                    # Reset recovery attempts on success
                    self.recovery_attempts[error_code] = 0
                    return True
            except Exception as e:
                print(f"Recovery strategy failed for error {error_code}: {e}")
        
        return False

    def _handle_collision_error(self) -> bool:
        """Handle collision detection errors."""
        print("Handling collision error - stopping motion and clearing error")
        try:
            if self.arm:
                self.arm.emergency_stop()
                time.sleep(0.5)
                self.arm.clean_error()
                self.arm.motion_enable(enable=True)
                return True
        except Exception as e:
            print(f"Failed to handle collision error: {e}")
        return False

    def _handle_joint_limit_error(self) -> bool:
        """Handle joint limit errors."""
        print("Handling joint limit error - moving to safe position")
        try:
            if self.arm:
                self.arm.clean_error()
                # Move to home position as safe recovery
                self.arm.move_gohome(wait=True)
                return True
        except Exception as e:
            print(f"Failed to handle joint limit error: {e}")
        return False

    def _handle_hard_joint_limit_error(self) -> bool:
        """Handle hard joint limit errors."""
        print("Handling hard joint limit error - emergency recovery")
        try:
            if self.arm:
                self.arm.emergency_stop()
                time.sleep(1)
                self.arm.clean_error()
                self.arm.motion_enable(enable=True)
                return True
        except Exception as e:
            print(f"Failed to handle hard joint limit error: {e}")
        return False

    def _handle_joint_speed_error(self) -> bool:
        """Handle joint speed limit errors."""
        print("Handling joint speed error - reducing speed limits")
        try:
            # Reduce speed limits by 20%
            self.angle_speed = int(self.angle_speed * 0.8)
            self.angle_acc = int(self.angle_acc * 0.8)
            print(f"Reduced joint speed to {self.angle_speed}°/s, acceleration to {self.angle_acc}°/s²")
            
            if self.arm:
                self.arm.clean_error()
                return True
        except Exception as e:
            print(f"Failed to handle joint speed error: {e}")
        return False

    def _handle_tcp_speed_error(self) -> bool:
        """Handle TCP speed limit errors."""
        print("Handling TCP speed error - reducing TCP limits")
        try:
            # Reduce TCP speed limits by 20%
            self.tcp_speed = int(self.tcp_speed * 0.8)
            self.tcp_acc = int(self.tcp_acc * 0.8)
            print(f"Reduced TCP speed to {self.tcp_speed}mm/s, acceleration to {self.tcp_acc}mm/s²")
            
            if self.arm:
                self.arm.clean_error()
                return True
        except Exception as e:
            print(f"Failed to handle TCP speed error: {e}")
        return False

    def _handle_communication_error(self) -> bool:
        """Handle communication errors."""
        print("Handling communication error - attempting reconnection")
        try:
            if self.arm and not self.simulation_mode:
                self.arm.disconnect()
                time.sleep(2)
                self.arm.connect()
                return self.arm.connected
        except Exception as e:
            print(f"Failed to handle communication error: {e}")
        return False

    def _handle_state_error(self) -> bool:
        """Handle robot state errors."""
        print("Handling state error - resetting robot state")
        try:
            if self.arm:
                self.arm.clean_error()
                self.arm.clean_warn()
                self.arm.motion_enable(enable=True)
                self.arm.set_mode(0)
                self.arm.set_state(0)
                return True
        except Exception as e:
            print(f"Failed to handle state error: {e}")
        return False

    # Bio Gripper Methods (Internal use - prefer universal methods)
    def _enable_bio_gripper_internal(self):
        """Internal method for enabling bio gripper."""
        if self.gripper_type != 'bio':
            return False
        code = self.arm.set_bio_gripper_enable(True)
        return self.check_code(code, 'enable_bio_gripper')

    def _open_bio_gripper_internal(self, speed=None, wait=True):
        """Internal method for opening bio gripper."""
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 300)
        code = self.arm.open_bio_gripper(speed=speed, wait=wait)
        return self.check_code(code, 'open_bio_gripper')

    def _close_bio_gripper_internal(self, speed=None, wait=True):
        """Internal method for closing bio gripper."""
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 300)
        code = self.arm.close_bio_gripper(speed=speed, wait=wait)
        return self.check_code(code, 'close_bio_gripper')

    # Standard Gripper Methods (Internal use - prefer universal methods)
    def _enable_standard_gripper_internal(self):
        """Internal method for enabling standard gripper."""
        if self.gripper_type != 'standard':
            return False
        code = self.arm.set_gripper_enable(True)
        return self.check_code(code, 'enable_standard_gripper')

    def _set_gripper_position_internal(self, position, speed=None, wait=True):
        """Internal method for setting standard gripper position."""
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 5000)
        code = self.arm.set_gripper_position(position, speed=speed, wait=wait)
        return self.check_code(code, f'set_gripper_position({position})')

    # RobotIQ Gripper Methods (Internal use - prefer universal methods)
    def _initialize_robotiq_gripper_internal(self):
        """Internal method for initializing RobotIQ gripper."""
        if self.gripper_type != 'robotiq':
            return False
        code1 = self.arm.robotiq_reset()
        if not self.check_code(code1, 'robotiq_reset'):
            return False
        time.sleep(1)
        code2 = self.arm.robotiq_set_activate(True)
        return self.check_code(code2, 'robotiq_set_activate')

    def _set_robotiq_position_internal(self, position, speed=None, force=None, wait=True):
        """Internal method for setting RobotIQ gripper position."""
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 255)
        if force is None:
            force = self.gripper_config.get('GRIPPER_FORCE', 255)
        code = self.arm.robotiq_set_position(position, speed=speed, force=force, wait=wait)
        return self.check_code(code, f'set_robotiq_position({position})')

# Example usage:
if __name__ == '__main__':
    print("XArmController with streamlined API!")
    print("=" * 50)
    print("✅ METHODS (Recommended):")
    print("   • move_to_position() - Cartesian movement with collision detection and alternative planning")
    print("   • move_joints() - Joint movement with comprehensive safety validation")
    print("   • open_gripper() / close_gripper() - Universal gripper support")
    print("   • enable_gripper_component() - Component-based gripper control")
    print()
    print("📊 PERFORMANCE TRACKING:")
    print("   • Real-time cycle time monitoring")
    print("   • Position accuracy tracking")
    print("   • Component utilization metrics")
    print("   • Speed limit enforcement")
    print("   • Automatic error recovery")
    print()
    print("Usage Example:")
    print("  # Modern API (recommended):")
    print("  controller = XArmController(auto_enable=True)")
    print("  controller.move_to_position(300, 0, 400)  # With collision detection by default")
    print("  controller.open_gripper()  # Universal gripper support")
    print()
    print("  # Advanced usage:")
    print("  controller.move_to_position(x, y, z, check_collision=True, motion_type=0)")
    print("  controller.move_joints(angles, check_collision=True)")
    