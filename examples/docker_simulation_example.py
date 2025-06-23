"""
An example script to demonstrate the control of xArm, linear track, and biogripper
through the docker simulator.

Please run the docker simulator first and start the xArm firmware inside the container.
Refer to the README.md for instructions.
"""

import sys
import time
import os
from xarm.wrapper import XArmAPI

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.PyxArm import xArm, BioGripper, LinearTrack


if __name__ == "__main__":
    # --- Connect to the xArm Simulator ---
    # Use '127.0.0.1' for the docker simulator
    # `check_joint_limit=False` is recommended for the simulator
    print("Connecting to xArm simulator at 127.0.0.1")
    try:
        arm = XArmAPI('127.0.0.1', check_joint_limit=False)
    except Exception as e:
        print(f"Failed to connect to the robot: {e}")
        sys.exit(1)

    # --- Instantiate control classes ---
    robot = xArm(arm)
    track = LinearTrack(robot)
    gripper = BioGripper(robot)

    # --- Main control loop ---
    try:
        if not robot.is_alive:
            print("Robot is not alive. Exiting.")
            sys.exit(1)

        print("Robot is alive. Starting demonstration.")

        # 1. Enable all components
        print("\nEnabling Robot, Gripper, and Linear Track...")
        gripper.enable()
        track.enable()
        time.sleep(1)

        # 2. Homing and initial positioning
        print("\nMoving arm to home position...")
        robot.move_joint(angles=[0, 0, 0, 0, 0, 0])
        print("Resetting linear track...")
        track.reset()
        time.sleep(2)

        # 3. Demonstrate Gripper
        print("\nDemonstrating gripper control...")
        print("Opening gripper...")
        gripper.open()
        time.sleep(2)
        print("Closing gripper...")
        gripper.close()
        time.sleep(2)

        # 4. Demonstrate Linear Track
        print("\nDemonstrating linear track movement...")
        print("Moving track to position 200...")
        track.move_to(200)
        time.sleep(3)
        print("Moving track to position 50...")
        track.move_to(50)
        time.sleep(3)

        # 5. Demonstrate Arm Movement
        print("\nDemonstrating arm joint movement...")
        print("Moving to joint configuration 1...")
        robot.move_joint(angles=[90, 0, 0, 0, 0, 0])
        time.sleep(2)
        print("Moving to joint configuration 2...")
        robot.move_joint(angles=[0, 30, 0, 30, 0, 0])
        time.sleep(2)

        # 6. Return to home position
        print("\nReturning to home position...")
        robot.move_joint(angles=[0, 0, 0, 0, 0, 0])
        track.reset()
        print("Demonstration finished successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        # --- Disconnect from the robot ---
        print("\nDisconnecting from the robot.")
        if arm.connected:
            arm.disconnect() 
            
            