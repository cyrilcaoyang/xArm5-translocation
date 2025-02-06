import time
import traceback
import yaml
from pathlib import Path

Config_Path = (
    Path(__file__).resolve().parent.parent
    / 'settings' / 'xarm5_config.yaml'
)


def load_arm_config():
    # Loading the robotic config file
    try:
        with open(Config_Path, 'r') as file:
            settings = yaml.safe_load(file)
            print("Setting file loaded.")
            return settings
    except FileNotFoundError:
        print("Error: YAML file not found.")
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}")


class RobotMain(object):
    """Robot Main Class"""
    def __init__(self, robot, **kwargs):
        self.alive = True
        self._arm = robot
        self._ignore_exit_state = False
        self._vars = {}
        self._funcs = {}
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
        self._arm.register_state_changed_callback(self._state_changed_callback)

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
            print('[{}][{}] {}'.format(time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time())), stack_tuple[1], ' '.join(map(str, args))))
        except:
            print(*args, **kwargs)

    @property
    def arm(self):
        return self._arm

    @property
    def VARS(self):
        return self._vars

    @property
    def FUNCS(self):
        return self._funcs

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


if __name__ == "__main__":
    setting = load_arm_config()
