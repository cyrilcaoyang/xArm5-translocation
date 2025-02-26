import time
from xarm.wrapper import XArmAPI
from src.PyxArm import xArm, BioGripper
from src.PyxArm import load_arm5_config, load_fixed_pos

# Pre-defined joint angles
positions = load_fixed_pos()
robot_home = positions["ROBOT_HOME"]
robot_home_high = positions["ROBOT_HOME_HIGH"]
robot_back_high = positions["ROBOT_BACK_HIGH"]
handshake_back_high = positions["HANDSHAKE_BACK_HIGH"]
handshake_back_low = positions["HANDSHAKE_BACK_LOW"]
cnc_plate_r_low = positions["CNC_PLATE_R_LOW"]
cnc_plate_r_high = positions["CNC_PLATE_R_HIGH"]
table_plate_r_low = positions["TABLE_PLATE_R_LOW"]
table_plate_r_high = positions["TABLE_PLATE_R_HIGH"]
table_plate_r_1dram_a1_low = positions["TABLE_PLATE_R_1DRAM_A1_LOW"]
table_plate_r_1dram_a1_high = positions["TABLE_PLATE_R_1DRAM_A1_HIGH"]


def run_loop(robot, cycles):
    try:
        # Joint Motion
        for i in range(int(cycles)):
            if not robot.is_alive:
                break
            t1 = time.monotonic()

            robot._angle_speed = 50
            robot._angle_acc = 50

            # Arm pick up plate from cnc
            xArm5.move_joint(cnc_plate_r_high)
            gripper.open()
            xArm5.move_joint(cnc_plate_r_low)
            gripper.close()
            xArm5.move_joint(cnc_plate_r_high)

            # Arm place plate to table
            xArm5.move_joint(table_plate_r_high)
            xArm5.move_joint(table_plate_r_low)
            gripper.open()
            xArm5.move_joint(table_plate_r_high)

            # Arm pick up plate from table
            xArm5.move_joint(table_plate_r_high)
            gripper.open()
            xArm5.move_joint(table_plate_r_low)
            gripper.close()
            xArm5.move_joint(table_plate_r_high)

            # Arm place plate on cnc
            xArm5.move_joint(cnc_plate_r_high)
            xArm5.move_joint(cnc_plate_r_low)
            gripper.open()
            xArm5.move_joint(cnc_plate_r_high)

            interval = time.monotonic() - t1
            if interval < 0.01:
                time.sleep(0.01 - interval)

        # Arm go home:
        xArm5.move_joint(robot_home)
        gripper.close()

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

    # Arm and gripper init and go home:
    xArm5._angle_speed = 150
    xArm5._angle_acc = 100
    gripper = BioGripper(xArm5)
    gripper.enable()
    gripper.open()
    xArm5.move_joint(robot_home)
    gripper.close()

    # Option 1. Run cycles of a workflow
    # run_loop(xArm5, cycles=1)

    # Option 2. Runing step by step
    # xArm5.move_joint(table_1dram_high)
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

    # Option 3. Handshake: table r to handshake position
    # Arm pick up plate from table
    xArm5.move_joint(table_plate_r_high)
    gripper.open()
    xArm5.move_joint(table_plate_r_low)
    gripper.close()
    xArm5.move_joint(table_plate_r_high)

    xArm5.move_joint(robot_home)
    xArm5.move_joint(robot_home_high)
    xArm5.move_joint(robot_back_high)
    xArm5.move_joint(handshake_back_high)
    xArm5.move_joint(handshake_back_low)
    gripper.open()

    xArm5.move_joint(handshake_back_high)
    gripper.close()
    xArm5.move_joint(robot_back_high)
    xArm5.move_joint(robot_home_high)
    xArm5.move_joint(robot_home)






