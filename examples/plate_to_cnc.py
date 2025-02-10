import time
from xarm.wrapper import XArmAPI
from src.PyxArm import load_arm5_config, xArm, move_joint

# Pre-defined joint angles
HOME = [0.0, -60.0, 0.0, 60.0, 0.0]
CNC = [30.7, 48.4, -103.3, 54.8, -59.2]
CNC_plate_low = [30.7, 51.8, -103.3, 51.4, -59.3]
CNC_plate_high = [30.7, 48.4, -103.3, 54.8, -59.2]


def run(robot):
    try:
        # Joint Motion
        for i in range(int(1)):
            if not robot.is_alive:
                break
            t1 = time.monotonic()

            code = robot.arm.set_bio_gripper_enable(True)
            if not robot.check_code(code, 'set_bio_gripper_enable'):
                return
            code = robot.arm.open_bio_gripper(speed=300, wait=True)
            if not robot.check_code(code, 'open_bio_gripper'):
                return
            code = robot.arm.close_bio_gripper(speed=300, wait=True)
            if not robot.check_code(code, 'close_bio_gripper'):
                return
            robot._angle_speed = 50
            robot._angle_acc = 100

            move_joint(HOME, robot)
            move_joint(CNC, robot)
            code = robot.arm.open_bio_gripper(speed=300, wait=True)
            if not robot.check_code(code, 'open_bio_gripper'):
                return
            move_joint(CNC_plate_low, robot)
            code = robot.arm.close_bio_gripper(speed=300, wait=True)
            if not robot.check_code(code, 'close_bio_gripper'):
                return
            move_joint(CNC_plate_high, robot)
            time.sleep(3)
            move_joint(CNC_plate_low, robot)
            code = robot.arm.open_bio_gripper(speed=300, wait=True)
            if not robot.check_code(code, 'open_bio_gripper'):
                return
            move_joint(CNC, robot)
            code = robot.arm.close_bio_gripper(speed=300, wait=True)
            if not robot.check_code(code, 'close_bio_gripper'):
                return
            move_joint(HOME, robot)

            interval = time.monotonic() - t1
            if interval < 0.01:
                time.sleep(0.01 - interval)

    except Exception as e:
        robot.pprint('MainException: {}'.format(e))
    finally:
        robot.alive = False
        robot.arm.release_error_warn_changed_callback(robot.error_warn_changed_callback)
        robot.arm.release_state_changed_callback(robot.state_changed_callback)


if __name__ == '__main__':
    setting = load_arm5_config()
    host = setting['host']

    # Instantiating the robot
    arm = XArmAPI(host, baud_checkset=False)
    xArm5 = xArm(arm)

    run(xArm5)
