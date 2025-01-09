#    This code demonstrate the workflow of picking up an HPLC tray from a location
#    and moving it to one of the positions on the Jubilee platform

# Author: Yang Cao <yangcyril.cao@utoronto.ca>

# Based on xArm-Python-SDK: https://github.com/xArm-Developer/xArm-Python-SDK
#   1. git clone git@github.com:xArm-Developer/xArm-Python-SDK.git
#   2. cd xArm-Python-SDK
#   3. python setup.py install

import sys
import math
import time
import queue
import datetime
import random
import traceback
import threading
from xarm import version
from xarm.wrapper import XArmAPI


class RobotMain(object):
    """Robot Main Class"""
    def __init__(self, robot, **kwargs):
        self.alive = True
        self._arm = robot
        self._ignore_exit_state = False
        self._tcp_speed = 100
        self._tcp_acc = 2000
        self._angle_speed = 20
        self._angle_acc = 500
        self._vars = {}
        self._funcs = {}
        self._robot_init()

    # Robot init
    def _robot_init(self):
        self._arm.clean_warn()
        self._arm.clean_error()
        self._arm.motion_enable(True)
        self._arm.set_mode(0)
        self._arm.set_state(0)
        time.sleep(1)
        self._arm.register_error_warn_changed_callback(self._error_warn_changed_callback)
        self._arm.register_state_changed_callback(self._state_changed_callback)

    # Register error/warn changed callback
    def _error_warn_changed_callback(self, data):
        if data and data['error_code'] != 0:
            self.alive = False
            self.pprint('err={}, quit'.format(data['error_code']))
            self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)

    # Register state changed callback
    def _state_changed_callback(self, data):
        if not self._ignore_exit_state and data and data['state'] == 4:
            self.alive = False
            self.pprint('state=4, quit')
            self._arm.release_state_changed_callback(self._state_changed_callback)

    def _check_code(self, code, label):
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

    # Robot Main Run
    def run(self):
        try:
            # Joint Motion
            for i in range(int(1)):
                if not self.is_alive:
                    break
                t1 = time.monotonic()
                code = self._arm.set_bio_gripper_enable(True)
                if not self._check_code(code, 'set_bio_gripper_enable'):
                    return
                code = self._arm.open_bio_gripper(speed=300, wait=True)
                if not self._check_code(code, 'open_bio_gripper'):
                    return
                code = self._arm.close_bio_gripper(speed=300, wait=True)
                if not self._check_code(code, 'close_bio_gripper'):
                    return
                self._angle_speed = 40
                self._angle_acc = 200
                code = self._arm.set_servo_angle(angle=[0.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[90.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[90.0, 0.0, 0.0, 0.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[100.0, 0.0, 0.0, 0.0, 10.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.open_bio_gripper(speed=300, wait=True)
                if not self._check_code(code, 'open_bio_gripper'):
                    return
                code = self._arm.set_servo_angle(angle=[95.8, 15.9, -28.8, 12.9, 6.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.close_bio_gripper(speed=300, wait=True)
                if not self._check_code(code, 'close_bio_gripper'):
                    return
                code = self._arm.set_servo_angle(angle=[95.7, 6.6, -27.8, 21.1, 6.1], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[90.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[0.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[-90.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[-107.3, -54.1, -2.2, 56.2, -17.3], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[-98.2, 1.7, -44.6, 42.8, -8.3], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[-98.2, 4.7, -43.5, 38.7, -8.3], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.open_bio_gripper(speed=300, wait=True)
                if not self._check_code(code, 'open_bio_gripper'):
                    return
                code = self._arm.set_servo_angle(angle=[-98.2, 1.7, -44.6, 42.8, -8.3], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.close_bio_gripper(speed=300, wait=True)
                if not self._check_code(code, 'close_bio_gripper'):
                    return
                code = self._arm.set_servo_angle(angle=[-107.3, -54.1, -2.2, 56.2, -17.3], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[-90.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                code = self._arm.set_servo_angle(angle=[0.0, -60.0, 0.0, 60.0, 0.0], speed=self._angle_speed, mvacc=self._angle_acc, wait=True, radius=-1.0)
                if not self._check_code(code, 'set_servo_angle'):
                    return
                interval = time.monotonic() - t1
                if interval < 0.01:
                    time.sleep(0.01 - interval)
        except Exception as e:
            self.pprint('MainException: {}'.format(e))
        finally:
            self.alive = False
            self._arm.release_error_warn_changed_callback(self._error_warn_changed_callback)
            self._arm.release_state_changed_callback(self._state_changed_callback)


if __name__ == '__main__':
    RobotMain.pprint('xArm-Python-SDK Version:{}'.format(version.__version__))
    arm = XArmAPI('192.168.1.212', baud_checkset=False)
    robot_main = RobotMain(arm)
    robot_main.run()


