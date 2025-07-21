"""
Docker Simulation Example - Basic Motion and Gripper Control
================================================================

A simple demonstration script for basic robot control using the Docker simulator.
This script demonstrates how to connect to the xArm using a connection profile
from the `xarm_config.yaml` file.

This example will:
1. Connect to the robot using the 'docker_local' profile.
2. Initialize the controller in simulation mode.
3. Perform basic arm and gripper movements.

This example supports any robot model defined in your configuration file.

Prerequisites:
- Docker and Docker Compose must be installed.
- The xArm Docker simulator must be running.
  (Run `docker-compose up` from the project root)
"""
import sys
import os
import time

from core.xarm_controller import XArmController, SafetyLevel

def run_demonstration(controller: XArmController):
    """Runs a sequence of movements to demonstrate controller functionality."""
    try:
        if not controller.is_alive:
            print("❌ Robot is not alive. Aborting demonstration.")
            return

        print("✅ Robot is alive and connected. Starting demonstration...")

        # 1. Home the robot
        print("\nStep 1: Homing the robot...")
        if controller.go_home(wait=True):
            print("   ✅ Robot successfully homed.")
        else:
            print("   ⚠️  Failed to home the robot. It may already be home or in an error state.")
        time.sleep(1)

        # 2. Demonstrate Gripper Control
        print("\nStep 2: Demonstrating Gripper Control...")
        if controller.has_gripper() and controller.is_component_enabled('gripper'):
            print("   Opening gripper...")
            if controller.open_gripper(wait=True):
                print("   ✅ Gripper opened.")
            else:
                print("   ❌ Failed to open gripper.")
            time.sleep(2)

            print("   Closing gripper...")
            if controller.close_gripper(wait=True):
                print("   ✅ Gripper closed.")
            else:
                print("   ❌ Failed to close gripper.")
        else:
            print("   ℹ️  Gripper not available or not enabled, skipping gripper demo.")
        time.sleep(1)

        # 3. Demonstrate Relative Cartesian Movement
        print("\nStep 3: Demonstrating Relative Cartesian Movement...")
        print("   Moving arm 50mm up (relative to base frame)...")
        if controller.move_relative(dz=50):
            print("   ✅ Moved up successfully.")
        else:
            print("   ❌ Failed to move up.")
        time.sleep(2)

        print("   Moving arm 50mm down...")
        if controller.move_relative(dz=-50):
            print("   ✅ Moved down successfully.")
        else:
            print("   ❌ Failed to move down.")
        time.sleep(1)

        # 4. Move to a safe 'stow' position using joint control
        print("\nStep 4: Moving to a stow position via joint control...")
        stow_joints = [0, -45, 0, -90, 0] # A safe position for a 5-axis arm
        if controller.move_joints(stow_joints, wait=True):
            print("   ✅ Moved to stow position.")
        else:
            print("   ❌ Failed to move to stow position.")

    except Exception as e:
        print(f"\n❌ An error occurred during the demonstration: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main function to initialize and run the demo."""
    print("=" * 60)
    print("  xArm Docker Simulation Example")
    print("=" * 60)
    
    controller = None
    try:
        print("Connecting to robot using 'docker_local' profile...")
        
        # Initialize the controller using a profile name.
        # The controller will automatically load settings from xarm_config.yaml.
        # We explicitly disable auto_enable to control initialization manually.
        controller = XArmController(
            profile_name='docker_local',
            simulation_mode=False,
            safety_level=SafetyLevel.LOW, # Use LOW for less restrictive simulation
            auto_enable=False # Prevent initialization within the constructor
        )
        
        # The initialize method handles the connection and setup.
        print("Initializing controller...")
        if not controller.initialize():
            print("🔥 Failed to initialize robot controller. Please ensure the Docker")
            print("   simulator is running and the 'docker_local' profile in")
            print("   `src/settings/xarm_config.yaml` is correct.")
            sys.exit(1)
        
        run_demonstration(controller)

    except Exception as e:
        print(f"🔥 An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        if controller:
            print("\n" + "=" * 60)
            print("🚀 Demonstration finished. Cleaning up...")
            controller.disconnect()
            print("✅ Controller disconnected.")
            print("=" * 60)

if __name__ == "__main__":
    main()
            
            