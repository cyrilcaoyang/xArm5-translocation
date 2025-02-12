import time
from xarm.wrapper import XArmAPI
from src.PyxArm import xArm, BioGripper
from src.PyxArm import load_arm5_config, load_fixed_pos

# Pre-defined joint angles
positions = load_fixed_pos()
robot_home = positions["ROBOT_HOME"]
cnc_plate_low = positions["CNC_PLATE_LOW"]
cnc_plate_high = positions["CNC_PLATE_HIGH"]
table_plate_low = positions["TABLE_PLATE_LOW"]
table_plate_high = positions["TABLE_PLATE_HIGH"]
table_1dram_a1_low = positions["TABLE_1DRAM_A1_LOW"]
table_1dram_a1_high = positions["TABLE_1DRAM_A1_HIGH"]


def run_loop(robot, cycles):
    try:
        # Joint Motion
        for i in range(int(cycles)):
            if not robot.is_alive:
                break
            t1 = time.monotonic()

            robot._angle_speed = 50
            robot._angle_acc = 50

            # Initiate robot and gripper, gripper is closed
            gripper = BioGripper(robot)
            gripper.enable()
            gripper.open()

            # Move gripper to pick up the plate from CNC
            gripper.close()
            robot.move_joint(robot_home)
            robot.move_joint(cnc_plate_high)
            gripper.open()
            robot.move_joint(cnc_plate_low)
            gripper.close()
            robot.move_joint(cnc_plate_high)

            # Put plate on the table and return home
            xArm5.move_joint(table_plate_high)
            xArm5.move_joint(table_plate_low)
            gripper.open()
            xArm5.move_joint(table_plate_high)
            gripper.close()
            xArm5.move_joint(robot_home)

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
    # gripper.enable()
    # gripper.open()
    # xArm5.move_joint(robot_home)
    # gripper.close()
    #
    # xArm5.move_joint(table_plate_high)
    # xArm5.move_joint(table_1dram_a1_high)
    # gripper.open()
    # xArm5.move_joint(table_1dram_a1_low)
    # gripper.close()
    # xArm5.move_joint(table_1dram_a1_high)
    # xArm5.move_joint(table_1dram_a1_low)
    # gripper.open()
    # xArm5.move_joint(table_1dram_a1_high)
    # gripper.close()
    # xArm5.move_joint(robot_home)

    # Or run cycles of a workflow
    run_loop(xArm5, cycles=1)
