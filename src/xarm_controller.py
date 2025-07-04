import yaml
import time
import traceback
from enum import Enum
from xarm.wrapper import XArmAPI

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
    def __init__(self, config_path='settings/', gripper_type='bio', enable_track=True, auto_enable=True, model=None):
        """
        Initializes the XArmController.

        Args:
            config_path (str): The path to the directory containing configuration files.
            gripper_type (str): Type of gripper ('bio', 'standard', 'robotiq', or 'none')
            enable_track (bool): Whether to enable linear track functionality
            auto_enable (bool): Whether to automatically enable components during initialize()
            model (int|str): Robot model (5, 6, 7, or '850'). If None, tries to auto-detect.
        """
        # Determine config file to load
        if model is not None:
            config_file = f"xarm{model}_config.yaml"
        else:
            # Try to find any xarm config file and use it
            import glob
            import os
            pattern = os.path.join(config_path, "xarm*_config.yaml")
            config_files = glob.glob(pattern)
            if config_files:
                config_file = os.path.basename(config_files[0])
                print(f"Auto-detected config file: {config_file}")
            else:
                # Fallback to xarm5
                config_file = "xarm5_config.yaml"
                print(f"No config files found, defaulting to: {config_file}")
        
        # Load configurations
        self.xarm_config = self._load_yaml(f"{config_path}{config_file}")
        self.location_config = self._load_yaml(f"{config_path}location_config.yaml")
        
        # Robot model information
        self.model = self.xarm_config.get('model', 5)
        self.num_joints = self.xarm_config.get('num_joints', 5)
        
        # Handle special case for 850 model
        if str(self.model) == '850':
            self.model_name = 'xArm850'
        else:
            self.model_name = f'xArm{self.model}'
            
        print(f"Configured for {self.model_name} with {self.num_joints} joints")
        
        # Gripper configuration - load based on type
        self.gripper_type = gripper_type.lower()
        self.gripper_config = {}
        if self.gripper_type == 'bio':
            self.gripper_config = self._load_yaml(f"{config_path}bio_gripper_config.yaml")
        elif self.gripper_type == 'standard':
            self.gripper_config = self._load_yaml(f"{config_path}gripper_config.yaml")
        elif self.gripper_type == 'robotiq':
            self.gripper_config = self._load_yaml(f"{config_path}robotiq_gripper_config.yaml")
        elif self.gripper_type == 'none':
            print("No gripper configured")
        else:
            print(f"Warning: Unknown gripper type '{gripper_type}'. Supported types: 'bio', 'standard', 'robotiq', 'none'")
        
        # Linear track configuration - only load if enabled
        self.enable_track = enable_track
        self.track_config = {}
        if self.enable_track:
            self.track_config = self._load_yaml(f"{config_path}linear_track_config.yaml")
        else:
            print("Linear track disabled")

        # Auto-enable setting
        self.auto_enable = auto_enable

        # Initialize arm connection (will be created during initialize())
        self.arm = None
        
        # Movement parameters from config
        self.tcp_speed = self.xarm_config.get('Tcp_Speed', 100)
        self.tcp_acc = self.xarm_config.get('Tcp_Acc', 2000)
        self.angle_speed = self.xarm_config.get('Angle_Speed', 20)
        self.angle_acc = self.xarm_config.get('Angle_Acc', 500)
        
        # State tracking
        self.alive = True
        self._ignore_exit_state = False
        
        # Component states
        self.states = {
            'arm': ComponentState.UNKNOWN,
            'gripper': ComponentState.DISABLED if self.gripper_type == 'none' else ComponentState.UNKNOWN,
            'track': ComponentState.DISABLED if not self.enable_track else ComponentState.UNKNOWN,
            'connection': ComponentState.UNKNOWN
        }
        
        # Last known positions
        self.last_position = None
        self.last_joints = None
        self.last_track_position = None
        
        # Error tracking
        self.last_error_code = 0
        self.last_warn_code = 0
        self.error_history = []

    def _load_yaml(self, file_path):
        """Loads a YAML file."""
        try:
            with open(file_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"Warning: Configuration file not found at {file_path}")
            return {}
        except yaml.YAMLError as e:
            print(f"Error parsing YAML file {file_path}: {e}")
            return {}

    def initialize(self):
        """
        Initializes the robot arm connection and sets the initial state.
        Components are only enabled if auto_enable=True.
        """
        print("Initializing Robot Arm...")
        
        try:
            self.states['connection'] = ComponentState.ENABLING
            
            # Create the XArmAPI connection if not already created
            if self.arm is None:
                self.arm = XArmAPI(self.xarm_config.get('host'))
            
            self.arm.connect()
            
            if not self.arm.connected:
                self.states['connection'] = ComponentState.ERROR
                print("Failed to connect to robot arm")
                return False
                
            self.states['connection'] = ComponentState.ENABLED
            
            # Clear any existing errors/warnings
            self.arm.clean_warn()
            self.arm.clean_error()
            
            # Enable motion and set modes
            self.states['arm'] = ComponentState.ENABLING
            self.arm.motion_enable(enable=True)
            self.arm.set_mode(0)  # Position control mode
            self.arm.set_state(0)  # Ready state
            time.sleep(1)
            
            # Register callbacks for monitoring
            self.arm.register_error_warn_changed_callback(self._error_warn_callback)
            self.arm.register_state_changed_callback(self._state_changed_callback)
            
            self.states['arm'] = ComponentState.ENABLED
            
            # Auto-enable components if requested
            if self.auto_enable:
                if self.gripper_type != 'none':
                    self.enable_gripper_component()
                
                if self.enable_track:
                    self.enable_track_component()
            
            print("Robot Arm Initialized.")
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
            
            if self.gripper_type == 'bio':
                success = self.enable_bio_gripper()
            elif self.gripper_type == 'standard':
                success = self.enable_standard_gripper()
            elif self.gripper_type == 'robotiq':
                success = self.initialize_robotiq_gripper()
            
            if success:
                self.states['gripper'] = ComponentState.ENABLED
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
            success = self.enable_linear_track()
            
            if success:
                self.states['track'] = ComponentState.ENABLED
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
            
        # Use current orientation if not specified
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