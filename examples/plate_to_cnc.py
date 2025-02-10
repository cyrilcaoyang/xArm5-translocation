import time
from xarm.wrapper import XArmAPI
from src.PyxArm import xArm, BioGripper
from src.PyxArm import load_arm5_config, load_fixed_pos

# Pre-defined joint angles
positions = load_fixed_pos()
robot_home = positions["ROBOT_HOME"]
cnc_home = positions["CNC_HOME"]
cnc_plate_low = positions["CNC_PLATE_LOW"]
cnc_plate_high = positions["CNC_PLATE_HIGH"]


def run_loop(robot, cycles):
    try:
        # Joint Motion
        for i in range(int(cycles)):
            if not robot.is_alive:
                break
            t1 = time.monotonic()

            robot._angle_speed = 50
            robot._angle_acc = 100

            # Initiate robot and gripper, gripper is closed
            gripper = BioGripper(robot)
            gripper.enable()
            gripper.open()
            gripper.close()

            # Move gripper to pick up the plate
            robot.move_joint(robot_home)
            robot.move_joint(cnc_home)
            robot.move_joint(cnc_plate_high)
            gripper.open()
            robot.move_joint(cnc_plate_low)
            gripper.close()
            robot.move_joint(cnc_plate_high)
            time.sleep(3)

            # Put back the plate and return home
            robot.move_joint(cnc_plate_low)
            gripper.open()
            robot.move_joint(cnc_plate_high)
            gripper.close()

            robot.move_joint(cnc_home)
            robot.move_joint(robot_home)

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

    # # Run a workflow:
    # xArm5._angle_speed = 50
    # xArm5._angle_acc = 100
    # gripper = BioGripper(xArm5)

    # xArm5.move_joint(cnc_home)
    # xArm5.move_joint(robot_home)
    # gripper.enable()
    # gripper.open(speed=100)
    # gripper.close(speed=200)

    # Or run cycles of a workflow
    run_loop(xArm5, cycles=2)
