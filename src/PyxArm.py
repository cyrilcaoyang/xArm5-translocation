"""
Python code to control the xArm5:
Functions:
    load_arm_config():
    move_joint(angles, robot):

Classes:
    xArm:
    BioGripper:
    LinearTrack:
"""

import time
import traceback
import yaml
from pathlib import Path

Arm_Config_Path = (Path(__file__).resolve().parent.parent / 'settings' / 'xarm_config.yaml')
Gripper_Config_Path = (Path(__file__).resolve().parent.parent / 'settings' / 'bio_gripper_config.yaml')
Location_Config_Path = (Path(__file__).resolve().parent.parent / 'settings' / 'location_config.yaml')
Linear_Track_Config_Path = (Path(__file__).resolve().parent.parent / 'settings' / 'linear_track_config.yaml')


def load_arm_config():
    # Loading the robotic config file
    try:
        with open(Arm_Config_Path, 'r') as file:
            settings = yaml.safe_load(file)
            print("Setting file successfully loaded.")
            return settings
    except FileNotFoundError:
        print("Error: YAML file not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")


def load_linear_track_config():
    # Loading the robotic config file
    try:
        with open(Linear_Track_Config_Path, 'r') as file:
            settings = yaml.safe_load(file)
            print("Setting file successfully loaded.")
            return settings
    except FileNotFoundError:
        print("Error: YAML file not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")


def load_gripper_config():
    # Loading the robotic config file
    try:
        with open(Gripper_Config_Path, 'r') as file:
            settings = yaml.safe_load(file)
            print("Setting file successfully loaded.")
            return settings
    except FileNotFoundError:
        print("Error: YAML file not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")


def load_fixed_pos():
    # Loading the hard-coded positions from a config file
    try:
        with open(Location_Config_Path, 'r') as file:
            settings = yaml.safe_load(file)
            print("Setting file successfully loaded.")
            return settings
    except FileNotFoundError:
        print("Error: YAML file not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")


class xArm(object):
    """xArm Class"""
    def __init__(self, robot, **kwargs):
        self.alive = True
        self._arm = robot
        self._ignore_exit_state = False
        self.robot_init()

        settings = load_arm_config()
        self._host = settings['host']
        self._port = settings['port']
        self._tcp_speed = settings['Tcp_Speed']
        self._tcp_acc = settings['Tcp_Acc']
        self._angle_speed = settings['Angle_Speed']
        self._angle_acc = settings['Angle_Acc']

    # Robot init
    def robot_init(self):
        self._arm.clean_warn()
        self._arm.clean_error()
        self._arm.motion_enable(True)
        self._arm.set_mode(0)
        self._arm.set_state(0)
        time.sleep(1)
        self._arm.register_error_warn_changed_callback(self.error_warn_changed_callback)
        self._arm.register_state_changed_callback(self.state_changed_callback)

    # Register error/warn changed callback
    def error_warn_changed_callback(self, data):
        if data and data['error_code'] != 0:
            self.alive = False
            self.pprint('err={}, quit'.format(data['error_code']))
            self._arm.release_error_warn_changed_callback(self.error_warn_changed_callback)

    # Register state changed callback
    def state_changed_callback(self, data):
        if not self._ignore_exit_state and data and data['state'] == 4:
            self.alive = False
            self.pprint('state=4, quit')
            self._arm.release_state_changed_callback(self.state_changed_callback)

    def check_code(self, code, label):
        if not self.is_alive or code != 0:
            self.alive = False
            ret1 = self._arm.get_state()
            ret2 = self._arm.get_err_warn_code()
            self.pprint('{}, code={}, connected={}, state={}, error={}, ret1={}. ret2={}'.format(label, code, self._arm.connected, self._arm.state, self._arm.error_code, ret1, ret2))
        return self.is_alive

    @staticmethod
    def pprint(*args, **kwargs):
        try:
            stack_tuple = traceback.extract_stack(limit=2)[0]
            print('[{}][{}] {}'.format(time.strftime(
                '%Y-%m-%d %H:%M:%S', time.localtime(time.time())),
                stack_tuple[1], ' '.join(map(str, args)))
            )
        except:
            print(*args, **kwargs)

    @property
    def arm(self):
        return self._arm

    @property
    def is_alive(self):
        if self.alive and self._arm.connected and self._arm.error_code == 0:
            if self._ignore_exit_state:
                return True
            if self._arm.state == 5:
                cnt = 0
                while self._arm.state == 5 and cnt < 5:
                    cnt += 1
                    time.sleep(0.1)
            return self._arm.state < 4
        else:
            return False

    def move_joint(self, angles):
        # Move joints with error checking
        code = self.arm.set_servo_angle(
            angle=angles,
            speed=self._angle_speed,
            mvacc=self._angle_acc,
            wait=True, radius=-1.0
        )
        if not self.check_code(code, 'set_servo_angle'):
            return
        else:
            print(f"Joints moved to {angles}.")


class LinearTrack(object):
    """
    A class to handle the actions of the linear track with code checking
    """
    def __init__(self, track):
        self.track = track
        try:
            settings = load_linear_track_config()
            self.speed = settings["Speed"]
            self.acc = settings["Acc"]
        except (KeyError, FileNotFoundError) as e:
            print(f"Error loading linear track config: {str(e)}")
            self.speed = 200  # Default fallback value
            self.acc = 1000 # Default fallback value

    def enable(self):
        # Enable the linear track with error checking
        code = self.track.arm.set_linear_track_enable(True)
        return self.track.check_code(code, 'set_linear_track_enable')

    def set_speed(self, speed):
        code = self.track.arm.set_linear_track_speed(speed)
        return self.track.check_code(code, 'set_linear_track_speed')

    def move_to(self, position, speed=None, wait=True):
        # Move the linear track with error checking
        if speed is None:
            speed = self.speed
        code = self.track.arm.set_linear_track_pos(speed=speed, pos=position, wait=wait)
        return self.track.check_code(code, 'set_linear_track_pos')

    def reset(self):
        # Reset the linear track to home by moving to position 0
        return self.move_to(0)


class BioGripper(object):
    """
    A class to handle the actions of bio gripper with code checking
    """
    def __init__(self, gripper):
        self.gripper = gripper
        try:
            self.gripper_speed = load_gripper_config()["GRIPPER_SPEED"]
        except (KeyError, FileNotFoundError) as e:
            print(f"Error loading gripper config: {str(e)}")
            self.gripper_speed = 300  # Default fallback value

    def enable(self):
        # Enable the bio gripper with error checking
        code = self.gripper.arm.set_bio_gripper_enable(True)
        return self.gripper.check_code(code, 'set_bio_gripper_enable')

    def open(self, speed=None, wait=True):
        # Open the bio gripper with error checking
        speed = self.gripper_speed
        code = self.gripper.arm.open_bio_gripper(speed=speed, wait=wait)
        return self.gripper.check_code(code, 'open_bio_gripper')

    def close(self, speed=None, wait=True):
        # Close the bio gripper with error checking
        speed = self.gripper_speed
        code = self.gripper.arm.close_bio_gripper(speed=speed, wait=wait)
        return self.gripper.check_code(code, 'close_bio_gripper')


if __name__ == "__main__":
    setting = load_arm_config()
    host = setting['host']
