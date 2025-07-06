import yaml
import time
import traceback
from enum import Enum
from xarm.wrapper import XArmAPI
import math
import os

class ComponentState(Enum):
    """Enum for component states"""
    UNKNOWN = "unknown"
    DISABLED = "disabled" 
    ENABLING = "enabling"
    ENABLED = "enabled"
    ERROR = "error"

class XArmController:
    """
    A controller class to manage and abstract interactions with the xArm,
    including optional gripper and linear track. This enhanced version supports
    multiple gripper types, handles optional components gracefully, and provides
    comprehensive state tracking.
    """
    def __init__(self, config_path='settings/', gripper_type='bio', enable_track=True, auto_enable=True, model=None, simulation_mode=False):
        """
        Initializes the XArmController.

        Args:
            config_path (str): The path to the directory containing configuration files.
            gripper_type (str): Type of gripper ('bio', 'standard', 'robotiq', or 'none')
            enable_track (bool): Whether to enable the linear track
            auto_enable (bool): Whether to automatically enable components during initialization
            model (int): xArm model (5, 6, 7, or 850). If None, will be detected from config
            simulation_mode (bool): Enable simulation mode (no hardware required)
        """
        # Store simulation mode first
        self.simulation_mode = simulation_mode
        
        # Load configurations
        self.config_path = config_path
        self.xarm_config = self.load_config(os.path.join(config_path, 'xarm_config.yaml'))
        self.gripper_config = self.load_config(os.path.join(config_path, 'bio_gripper_config.yaml'))
        self.track_config = self.load_config(os.path.join(config_path, 'linear_track_config.yaml'))
        
        # Component settings
        self.gripper_type = gripper_type
        self.enable_track = enable_track
        self.auto_enable = auto_enable
        
        # Determine model
        self.model = model or self.xarm_config.get('model', 7)
        self.num_joints = self.model if self.model in [5, 6, 7] else 6  # 850 has 6 joints
        
        # Initialize robot arm connection
        if self.simulation_mode:
            # In simulation mode, create a mock arm object
            self.arm = self._create_simulation_arm()
        else:
            # Use official SDK with do_not_open parameter
            self.arm = XArmAPI(self.xarm_config.get('host'), do_not_open=True)
        
        # Movement parameters
        self.tcp_speed = self.xarm_config.get('tcp_speed', 100)
        self.tcp_acc = self.xarm_config.get('tcp_acc', 2000)
        self.angle_speed = self.xarm_config.get('angle_speed', 20)
        self.angle_acc = self.xarm_config.get('angle_acc', 500)
        
        # Component states using enum
        self.states = {
            'connection': ComponentState.DISABLED,
            'arm': ComponentState.DISABLED,
            'gripper': ComponentState.DISABLED,
            'track': ComponentState.DISABLED
        }
        
        # Position tracking
        self.last_position = [300, 0, 300, 180, 0, 0]  # Default position
        self.last_joints = [0] * self.num_joints
        self.last_track_position = 0
        
        # Error tracking
        self.error_history = []
        
        # State tracking
        self.alive = True
        self._ignore_exit_state = False
        
        # Initialize simulation state and collision detection
        if self.simulation_mode:
            self.last_position = [300, 0, 300, 180, 0, 0]
            self.last_joints = [0] * self.num_joints
            self.last_track_position = 0
            self._init_collision_detection()
        
        # Initialize if auto_enable is True
        if auto_enable:
            self.initialize()

    def _create_simulation_arm(self):
        """Create a mock arm object for simulation mode."""
        class SimulationArm:
            def __init__(self, controller):
                self.controller = controller
                self.connected = True
                self.error_code = 0
                self.state = 0
                
            def connect(self):
                self.connected = True
                return 0
                
            def disconnect(self):
                self.connected = False
                return 0
                
            def get_position(self):
                return [0, self.controller.last_position]
                
            def get_servo_angle(self):
                return [0, self.controller.last_joints]
                
            def set_servo_angle(self, angle, speed=None, mvacc=None, wait=True):
                # Basic collision detection in simulation
                if self.controller._check_joint_collision(angle):
                    return 19  # Joint limit error code
                self.controller.last_joints = angle[:]
                return 0
                
            def set_position(self, x, y, z, roll, pitch, yaw, speed=None, mvacc=None, wait=True):
                # Basic workspace limit checking
                if self.controller._check_workspace_collision([x, y, z, roll, pitch, yaw]):
                    return 11  # TCP limit error code
                self.controller.last_position = [x, y, z, roll, pitch, yaw]
                return 0
                
            def set_gripper_position(self, pos, wait=True):
                return 0
                
            def set_linear_track_pos(self, pos, speed=None, wait=True):
                self.controller.last_track_position = pos
                return 0
                
            def get_linear_track_pos(self):
                return [0, self.controller.last_track_position]
                
        return SimulationArm(self)
    
    def _init_collision_detection(self):
        """Initialize collision detection parameters for simulation."""
        # Joint limits for different models (degrees)
        self.joint_limits = {
            5: [(-360, 360), (-118, 120), (-225, 11), (-360, 360), (-97, 180)],
            6: [(-360, 360), (-118, 120), (-225, 11), (-360, 360), (-97, 180), (-360, 360)],
            7: [(-360, 360), (-118, 120), (-225, 11), (-360, 360), (-97, 180), (-360, 360), (-360, 360)],
            850: [(-360, 360), (-118, 120), (-225, 11), (-360, 360), (-97, 180), (-360, 360)]
        }
        
        # Workspace limits (mm, degrees)
        self.workspace_limits = {
            'x': (-700, 700),
            'y': (-700, 700), 
            'z': (-200, 700),
            'roll': (-180, 180),
            'pitch': (-180, 180),
            'yaw': (-180, 180)
        }
        
        # Basic self-collision zones (simplified)
        self.collision_zones = [
            # Joint 1 and Joint 2 collision zone
            {'joints': [0, 1], 'condition': lambda j: abs(j[0]) > 160 and j[1] < -90},
            # Joint 2 and Joint 3 collision zone  
            {'joints': [1, 2], 'condition': lambda j: j[1] > 100 and j[2] > 0},
            # Add more collision zones as needed
        ]
    
    def _check_joint_collision(self, joint_angles):
        """Check for joint limit violations and self-collisions in simulation."""
        if not self.simulation_mode:
            return False
            
        # Assume angles are already in degrees for simulation
        angles = joint_angles[:self.num_joints]  # Only check valid joints for this model
        
        # Check joint limits
        limits = self.joint_limits.get(self.model, self.joint_limits[7])
        for i, (angle, (min_limit, max_limit)) in enumerate(zip(angles, limits)):
            if angle < min_limit or angle > max_limit:
                print(f"Joint {i+1} limit exceeded: {angle}° (limits: {min_limit}° to {max_limit}°)")
                return True
        
        # Check basic self-collision zones
        for zone in self.collision_zones:
            if all(i < len(angles) for i in zone['joints']):  # Ensure all joints exist
                joint_subset = [angles[i] for i in zone['joints']]
                if zone['condition'](joint_subset):
                    joint_names = [f"Joint {i+1}" for i in zone['joints']]
                    print(f"Self-collision detected between {' and '.join(joint_names)}")
                    return True
                
        return False
    
    def _check_workspace_collision(self, pose):
        """Check for workspace limit violations in simulation."""
        if not self.simulation_mode:
            return False
            
        x, y, z, roll, pitch, yaw = pose
        
        # Check workspace limits
        if not (self.workspace_limits['x'][0] <= x <= self.workspace_limits['x'][1]):
            print(f"X workspace limit exceeded: {x}mm (limits: {self.workspace_limits['x']})")
            return True
        if not (self.workspace_limits['y'][0] <= y <= self.workspace_limits['y'][1]):
            print(f"Y workspace limit exceeded: {y}mm (limits: {self.workspace_limits['y']})")
            return True
        if not (self.workspace_limits['z'][0] <= z <= self.workspace_limits['z'][1]):
            print(f"Z workspace limit exceeded: {z}mm (limits: {self.workspace_limits['z']})")
            return True
            
        # Check orientation limits
        if not (self.workspace_limits['roll'][0] <= roll <= self.workspace_limits['roll'][1]):
            print(f"Roll limit exceeded: {roll}° (limits: {self.workspace_limits['roll']})")
            return True
        if not (self.workspace_limits['pitch'][0] <= pitch <= self.workspace_limits['pitch'][1]):
            print(f"Pitch limit exceeded: {pitch}° (limits: {self.workspace_limits['pitch']})")
            return True
        if not (self.workspace_limits['yaw'][0] <= yaw <= self.workspace_limits['yaw'][1]):
            print(f"Yaw limit exceeded: {yaw}° (limits: {self.workspace_limits['yaw']})")
            return True
            
        return False

    def load_config(self, file_path):
        """Load YAML configuration file."""
        try:
            with open(file_path, 'r') as file:
                return yaml.safe_load(file)
        except FileNotFoundError:
            print(f"Warning: Config file {file_path} not found, using defaults")
            return {}
        except Exception as e:
            print(f"Error loading config {file_path}: {e}")
            return {}

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
                    self.arm = XArmAPI(self.xarm_config.get('host'))
            
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
            
            print(f"Robot Arm Initialized ({mode_str}).")
            self._update_positions()
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
                    success = self.enable_bio_gripper()
                elif self.gripper_type == 'standard':
                    success = self.enable_standard_gripper()
                elif self.gripper_type == 'robotiq':
                    success = self.initialize_robotiq_gripper()
            
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
        """Callback for error/warning changes."""
        if data:
            if data.get('error_code', 0) != 0:
                self.last_error_code = data['error_code']
                self.alive = False
                self.states['arm'] = ComponentState.ERROR
                error_info = {
                    'timestamp': time.time(),
                    'error_code': data['error_code'],
                    'warn_code': data.get('warn_code', 0)
                }
                self.error_history.append(error_info)
                print(f'Error detected: {data["error_code"]}, stopping operations')
            
            if data.get('warn_code', 0) != 0:
                self.last_warn_code = data['warn_code']
                print(f'Warning: {data["warn_code"]}')

    def _state_changed_callback(self, data):
        """Callback for state changes."""
        if not self._ignore_exit_state and data and data['state'] == 4:
            self.alive = False
            self.states['arm'] = ComponentState.ERROR
            print('State 4 detected, stopping operations')

    def check_code(self, code, operation_name):
        """Check if an operation was successful."""
        if not self.is_alive or code != 0:
            self.alive = False
            state = self.arm.state if self.arm else 'N/A'
            error = self.arm.error_code if self.arm else 'N/A'
            print(f'{operation_name} failed: code={code}, state={state}, error={error}')
            return False
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
        return self.error_history[-count:] if self.error_history else []

    # =============================================================================
    # LINEAR/CARTESIAN MOVEMENTS
    # =============================================================================
    
    def move_to_position(self, x, y, z, roll=None, pitch=None, yaw=None, speed=None, wait=True):
        """
        Move to a Cartesian position (linear movement).
        This is different from joint movement - the end effector moves in a straight line.
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        if speed is None:
            speed = self.tcp_speed
        
        # Set default orientation if not specified
        if roll is None:
            roll = 180
        if pitch is None:
            pitch = 0
        if yaw is None:
            yaw = 0
            
        if self.simulation_mode:
            # In simulation mode, use enhanced collision detection
            if self._check_workspace_collision([x, y, z, roll, pitch, yaw]):
                return False
            print(f"[SIM] Moved to position [{x}, {y}, {z}, {roll}, {pitch}, {yaw}]")
            self.last_position = [x, y, z, roll, pitch, yaw]
            return True
            
        # Use current orientation if not specified (hardware mode only)
        if any(angle is None for angle in [roll, pitch, yaw]):
            current_pos = self.arm.get_position()
            if current_pos[0] == 0:  # Success
                position = current_pos[1] if len(current_pos) > 1 else current_pos[1:]
                if len(position) >= 6:
                    x_curr, y_curr, z_curr, roll_curr, pitch_curr, yaw_curr = position[:6]
                    roll = roll if roll is not None else roll_curr
                    pitch = pitch if pitch is not None else pitch_curr
                    yaw = yaw if yaw is not None else yaw_curr
        
        code = self.arm.set_position(x=x, y=y, z=z, roll=roll, pitch=pitch, yaw=yaw, 
                                   speed=speed, wait=wait)
        success = self.check_code(code, f'move_to_position({x}, {y}, {z})')
        if success:
            self._update_positions()
        return success

    def move_to_named_location(self, location_name, speed=None):
        """
        Move to a predefined location from the location config.
        This uses linear movement.
        """
        if location_name not in self.location_config:
            print(f"Error: Location '{location_name}' not found in config")
            return False
            
        location = self.location_config[location_name]
        return self.move_to_position(
            x=location['x'], y=location['y'], z=location['z'],
            roll=location.get('roll'), pitch=location.get('pitch'), yaw=location.get('yaw'),
            speed=speed
        )

    def move_relative(self, dx=0, dy=0, dz=0, droll=0, dpitch=0, dyaw=0, speed=None):
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
    
    def move_joints(self, angles, speed=None, acceleration=None, wait=True):
        """
        Move individual joints to specified angles.
        Enhanced joint movement with comprehensive error checking and state management.
        """
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
            
        if speed is None:
            speed = self.angle_speed
        if acceleration is None:
            acceleration = self.angle_acc
        
        if self.simulation_mode:
            # In simulation mode, use enhanced collision detection
            if self._check_joint_collision(angles):
                return False
            print(f"[SIM] Joints moved to {angles}")
            self.last_joints = angles[:self.num_joints]  # Store only valid joints for model
            return True
            
        code = self.arm.set_servo_angle(
            angle=angles,
            speed=speed,
            mvacc=acceleration,
            wait=wait
        )
        
        success = self.check_code(code, f'move_joints({angles})')
        if success:
            print(f"Joints moved to {angles}")
            self._update_positions()
        return success

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
            
        current_angles = ret[1]
        current_angles[joint_id] = angle
        
        return self.move_joints(current_angles, speed=speed, wait=wait)

    # =============================================================================
    # VELOCITY CONTROL
    # =============================================================================
    
    def set_cartesian_velocity(self, vx=0, vy=0, vz=0, vroll=0, vpitch=0, vyaw=0):
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

    # BIO Gripper Methods
    def enable_bio_gripper(self):
        """Enable the bio gripper."""
        if self.gripper_type != 'bio':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'bio'")
            return False
        code = self.arm.set_bio_gripper_enable(True)
        return self.check_code(code, 'enable_bio_gripper')

    def open_bio_gripper(self, speed=None, wait=True):
        """Open the bio gripper."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
        if self.gripper_type != 'bio':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'bio'")
            return False
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 300)
        code = self.arm.open_bio_gripper(speed=speed, wait=wait)
        return self.check_code(code, 'open_bio_gripper')

    def close_bio_gripper(self, speed=None, wait=True):
        """Close the bio gripper."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
        if self.gripper_type != 'bio':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'bio'")
            return False
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 300)
        code = self.arm.close_bio_gripper(speed=speed, wait=wait)
        return self.check_code(code, 'close_bio_gripper')

    # Standard Gripper Methods
    def enable_standard_gripper(self):
        """Enable the standard gripper."""
        if self.gripper_type != 'standard':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'standard'")
            return False
        code = self.arm.set_gripper_enable(True)
        return self.check_code(code, 'enable_standard_gripper')

    def set_gripper_position(self, position, speed=None, wait=True):
        """Set standard gripper position (0-850, where 0 is closed)."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
        if self.gripper_type != 'standard':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'standard'")
            return False
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 5000)
        code = self.arm.set_gripper_position(position, speed=speed, wait=wait)
        return self.check_code(code, f'set_gripper_position({position})')

    def open_standard_gripper(self, speed=None, wait=True):
        """Open the standard gripper."""
        max_position = self.gripper_config.get('MAX_POSITION', 850)
        return self.set_gripper_position(max_position, speed=speed, wait=wait)

    def close_standard_gripper(self, speed=None, wait=True):
        """Close the standard gripper."""
        return self.set_gripper_position(0, speed=speed, wait=wait)

    # RobotIQ Gripper Methods
    def initialize_robotiq_gripper(self):
        """Initialize the RobotIQ gripper."""
        if self.gripper_type != 'robotiq':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'robotiq'")
            return False
        code1 = self.arm.robotiq_reset()
        if not self.check_code(code1, 'robotiq_reset'):
            return False
        time.sleep(1)
        code2 = self.arm.robotiq_set_activate(True)
        return self.check_code(code2, 'robotiq_set_activate')

    def set_robotiq_position(self, position, speed=None, force=None, wait=True):
        """Set RobotIQ gripper position (0-255, where 0 is open, 255 is closed)."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
        if self.gripper_type != 'robotiq':
            print(f"Warning: Current gripper type is '{self.gripper_type}', not 'robotiq'")
            return False
        if speed is None:
            speed = self.gripper_config.get('GRIPPER_SPEED', 255)
        if force is None:
            force = self.gripper_config.get('GRIPPER_FORCE', 255)
        code = self.arm.robotiq_set_position(position, speed=speed, force=force, wait=wait)
        return self.check_code(code, f'set_robotiq_position({position})')

    def open_robotiq_gripper(self, wait=True):
        """Open the RobotIQ gripper."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
        code = self.arm.robotiq_open(wait=wait)
        return self.check_code(code, 'open_robotiq_gripper')

    def close_robotiq_gripper(self, wait=True):
        """Close the RobotIQ gripper."""
        if not self.is_component_enabled('gripper'):
            print("Gripper is not enabled")
            return False
        code = self.arm.robotiq_close(wait=wait)
        return self.check_code(code, 'close_robotiq_gripper')

    # Universal Gripper Methods
    def open_gripper(self, speed=None, wait=True):
        """Open the gripper (works with any configured gripper type)."""
        if self.simulation_mode:
            print(f"[SIM] {self.gripper_type.title()} gripper opened")
            return True
            
        if self.gripper_type == 'bio':
            return self.open_bio_gripper(speed=speed, wait=wait)
        elif self.gripper_type == 'standard':
            return self.open_standard_gripper(speed=speed, wait=wait)
        elif self.gripper_type == 'robotiq':
            return self.open_robotiq_gripper(wait=wait)
        else:
            print("No gripper configured")
            return False

    def close_gripper(self, speed=None, wait=True):
        """Close the gripper (works with any configured gripper type)."""
        if self.simulation_mode:
            print(f"[SIM] {self.gripper_type.title()} gripper closed")
            return True
            
        if self.gripper_type == 'bio':
            return self.close_bio_gripper(speed=speed, wait=wait)
        elif self.gripper_type == 'standard':
            return self.close_standard_gripper(speed=speed, wait=wait)
        elif self.gripper_type == 'robotiq':
            return self.close_robotiq_gripper(wait=wait)
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
        """Move the linear track to a specific position."""
        if not self.is_component_enabled('track'):
            print("Linear track is not enabled")
            return False
        if speed is None:
            speed = self.track_config.get('Speed', 200)
        
        if self.simulation_mode:
            print(f"[SIM] Linear track moved to position {position}mm")
            self.last_track_position = position
            return True
            
        code = self.arm.set_linear_track_pos(speed=speed, pos=position, wait=wait)
        success = self.check_code(code, f'move_track_to_position({position})')
        if success:
            self._update_track_position()
        return success

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
    
    @staticmethod
    def pprint(*args, **kwargs):
        """Pretty print with timestamp and caller info for debugging."""
        try:
            stack_tuple = traceback.extract_stack(limit=2)[0]
            print('[{}][{}] {}'.format(time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                stack_tuple[1], ' '.join(map(str, args)))
            )
        except:
            print(*args, **kwargs)

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
            joints = ret[1]
            # Handle case where 7-axis robots return 7 values but we only want first 6
            if len(joints) > 6:
                joints = joints[:6]
            self.last_joints = joints
            return joints
        return None

    def go_home(self):
        """Move to the home position."""
        if not self.is_component_enabled('arm'):
            print("Arm is not enabled")
            return False
        code = self.arm.move_gohome(wait=True)
        success = self.check_code(code, 'go_home')
        if success:
            self._update_positions()
        return success

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

# Example usage:
if __name__ == '__main__':
    # Examples of different configurations
    
    # Configuration 1: Auto-enable everything
    # controller = XArmController(gripper_type='bio', enable_track=True, auto_enable=True)
    # controller.initialize()  # Will automatically enable gripper and track
    
    # Configuration 2: Manual enabling
    # controller = XArmController(gripper_type='bio', enable_track=True, auto_enable=False)
    # controller.initialize()  # Only connects and enables arm
    # controller.enable_gripper_component()  # Manually enable gripper when ready
    # controller.enable_track_component()    # Manually enable track when ready
    
    # Configuration 3: Check states
    # status = controller.get_system_status()
    # print("System Status:", status)
    
    print("Enhanced XArmController with state tracking and manual component control!")
    print("Key features:")
    print("1. Comprehensive state tracking for all components")
    print("2. Separate instantiation from enabling (auto_enable parameter)")
    print("3. Manual enable/disable of individual components")
    print("4. Error history tracking")
    print("5. Cached position information")
    print("6. Component state checking before operations")
    print()
    print("Usage:")
    print("  # Auto-enable components:")
    print("  controller = XArmController(auto_enable=True)")
    print("  controller.initialize()")
    print()
    print("  # Manual component control:")
    print("  controller = XArmController(auto_enable=False)")
    print("  controller.initialize()  # Only arm connection")
    print("  controller.enable_gripper_component()  # Enable when ready")
    print("  controller.enable_track_component()    # Enable when ready") 