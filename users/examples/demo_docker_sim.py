"""
Docker Simulation Example - Basic Linear Motion and Gripper Control
==================================================================

A simple demonstration script for basic robot control using the Docker simulator.
This example demonstrates:
1. Basic linear/Cartesian arm movements
2. Gripper operations (open/close)
3. Simple joint movements

Supports: xArm5 (5 joints), xArm6 (6 joints), xArm7 (7 joints), xArm850 (6 joints)
Auto-detects robot model from configuration.

For advanced linear motor control, see: demo_linear_motor.py

Please run the docker simulator first and start the xArm firmware inside the container.
Refer to the README.md for instructions.
"""

import sys
import time
import os

# Add the src directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.xarm_controller import XArmController


if __name__ == "__main__":
    print("=" * 60)
    print("Docker Simulation Example - Basic Linear Motion & Gripper")
    print("=" * 60)
    print("Connecting to xArm simulator at 127.0.0.1")
    
    try:
        # Create XArmController for Docker simulator
        controller = XArmController(
            config_path='settings/',
            gripper_type='bio', 
            enable_track=True,
            auto_enable=False
        )
        
        # Override for Docker simulator compatibility
        from xarm.wrapper import XArmAPI
        controller.arm = XArmAPI('127.0.0.1', check_joint_limit=False)
        
        # Initialize the controller
        if not controller.initialize():
            print("Failed to initialize robot controller. Exiting.")
            sys.exit(1)
            
    except Exception as e:
        print(f"Failed to connect to the robot: {e}")
        sys.exit(1)

    try:
        if not controller.is_alive:
            print("Robot is not alive. Exiting.")
            sys.exit(1)

        print("✓ Robot is alive. Starting basic demonstration.")

        # Enable gripper
        print("\n1. Enabling gripper...")
        if controller.enable_gripper_component():
            print("   ✓ Gripper enabled")
        else:
            print("   ⚠️  Gripper not available in simulator")

        # Set arm to home position
        print("\n2. Moving arm to home position...")
        current_joints = controller.get_current_joints()
        if current_joints:
            print(f"   Current joints: {current_joints}")
        
        # Get current position
        current_pos = controller.get_current_position()
        if current_pos:
            print(f"   Current position: {current_pos}")

        # Demonstrate gripper control
        print("\n3. Demonstrating gripper control...")
        if controller.has_gripper() and controller.is_component_enabled('gripper'):
            print("   Opening gripper...")
            if controller.open_gripper():
                print("   ✓ Gripper opened")
            else:
                print("   ✗ Failed to open gripper")
            
            time.sleep(2)
            
            print("   Closing gripper...")
            if controller.close_gripper():
                print("   ✓ Gripper closed")
            else:
                print("   ✗ Failed to close gripper")
        else:
            print("   ⚠️  Gripper not available - skipping gripper demo")

        # Demonstrate basic linear motion
        print("\n4. Demonstrating basic linear motion...")
        print("   Note: Some movements may fail in Docker simulator due to state constraints")
        
        # Try relative movement
        print("   Attempting small relative movement...")
        if controller.move_relative(dz=10):
            print("   ✓ Moved 10mm up in Z")
            time.sleep(1)
            
            if controller.move_relative(dz=-10):
                print("   ✓ Moved back to original Z position")
            else:
                print("   ⚠️  Could not return to original Z position")
        else:
            print("   ⚠️  Relative movement not available in simulator")

        # Final status
        print("\n5. Final status check...")
        final_pos = controller.get_current_position()
        final_joints = controller.get_current_joints()
        
        if final_pos:
            print(f"   Final position: {final_pos}")
        if final_joints:
            print(f"   Final joints: {final_joints}")
        
        print("   ✅ Basic demonstration completed")

    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print(f"\n6. Cleanup:")
        print("   Disconnecting from robot...")
        controller.disconnect()
        print("   ✓ Disconnected successfully")
        print("=" * 60)
        print("For advanced linear motor control, run:")
        print("  python examples/linear_motor_demo.py --help")
        print("=" * 60)
            
            