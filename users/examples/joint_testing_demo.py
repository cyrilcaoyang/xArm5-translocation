#!/usr/bin/env python3
"""
Joint Testing Demonstration Script

This script demonstrates individual joint movement testing for the xArm robot.
It homes the robot to all joints at 0 degrees, then systematically tests each
joint by moving it through a sequence: +2°, 0°, -2°, 0°.

Features:
- Interactive joint testing with user confirmation
- Support for both simulation and real hardware
- Automatic IP address prompting for real hardware
- Safe movement with position verification
- Comprehensive error handling and cleanup

Usage:
    python joint_testing_demo.py --simulate     # Run in simulation mode
    python joint_testing_demo.py --real         # Connect to real robot hardware
    python joint_testing_demo.py --real --host 192.168.1.237  # Specify robot IP

Author: AI Assistant
Created: 2024
"""

import os
import sys
import time
import argparse
import traceback

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.xarm_controller import XArmController


def test_single_joint(controller, joint_id, joint_name, simulate=False):
    """
    Test a single joint through the movement sequence: +2°, 0°, -2°, 0°
    
    Args:
        controller: XArmController instance
        joint_id: Joint index (0-5)
        joint_name: Human-readable joint name
        simulate: If True, simulate the operations without hardware
    
    Returns:
        bool: True if all movements successful, False otherwise
    """
    print(f"\n🔧 Testing {joint_name} (Joint {joint_id + 1}):")
    
    test_angles = [2.0, 0.0, -2.0, 0.0]
    test_descriptions = ["+2 degrees", "back to 0°", "-2 degrees", "back to 0°"]
    
    for i, (angle, description) in enumerate(zip(test_angles, test_descriptions), 1):
        print(f"    Step {i}/4: Moving to {description}")
        
        if simulate:
            print(f"      [SIM] Moving {joint_name} to {angle}°...")
            time.sleep(1.5)  # Simulate movement time
            print(f"      [SIM] ✓ {joint_name} at {angle}°")
        else:
            # Real hardware operations
            print(f"      → Moving {joint_name} to {angle}°...")
            
            if controller.move_single_joint(joint_id, angle, wait=True):
                print(f"      ✓ {joint_name} moved to {angle}°")
                
                # Verify position
                current_joints = controller.get_current_joints()
                if current_joints and len(current_joints) > joint_id:
                    actual_angle = current_joints[joint_id]
                    print(f"      📍 Confirmed position: {actual_angle:.2f}°")
                    
                    # Check if position is close enough (within 0.5 degrees)
                    if abs(actual_angle - angle) > 0.5:
                        print(f"      ⚠️  Position deviation: expected {angle}°, got {actual_angle:.2f}°")
                else:
                    print(f"      ⚠️  Could not verify position")
            else:
                print(f"      ✗ Failed to move {joint_name} to {angle}°")
                return False
        
        # Small pause between movements
        time.sleep(0.5)
    
    return True


def run_interactive_joint_test(controller, simulate_mode=False):
    """
    Run the interactive joint testing sequence for all joints.
    
    Args:
        controller: XArmController instance
        simulate_mode: If True, simulate all movements
    """
    joint_names = [
        "Base Joint (Rotation)",
        "Shoulder Joint", 
        "Elbow Joint",
        "Wrist 1 Joint",
        "Wrist 2 Joint", 
        "Wrist 3 Joint (End Effector)"
    ]
    
    print(f"\n📋 Interactive Joint Testing Sequence:")
    print(f"   Mode: {'SIMULATION' if simulate_mode else 'REAL HARDWARE'}")
    print(f"   Test pattern per joint: +2° → 0° → -2° → 0°")
    print(f"   Total joints to test: {len(joint_names)}")
    print("=" * 70)
    
    successful_tests = 0
    
    for joint_id, joint_name in enumerate(joint_names):
        print(f"\n📍 Joint {joint_id + 1}/{len(joint_names)}: {joint_name}")
        
        # Interactive confirmation for real hardware
        if not simulate_mode:
            try:
                response = input(f"    Press Enter to test {joint_name}, or 's' to skip: ").strip().lower()
                if response == 's':
                    print(f"    ⏭️  Skipped {joint_name}")
                    continue
            except (EOFError, KeyboardInterrupt):
                print(f"    ⏭️  Skipped {joint_name} (no input)")
                continue
        
        # Perform the joint test
        success = test_single_joint(controller, joint_id, joint_name, simulate_mode)
        
        if success:
            successful_tests += 1
            print(f"    ✅ {joint_name} test completed successfully")
        else:
            print(f"    ❌ {joint_name} test failed")
            
            if not simulate_mode:
                try:
                    response = input("    Continue with remaining joints? (y/n): ").strip().lower()
                    if response == 'n':
                        break
                except (EOFError, KeyboardInterrupt):
                    print("    Continuing with remaining joints...")
        
        # Pause between joints
        time.sleep(1)
    
    # Summary
    print(f"\n📊 Test Summary:")
    print(f"   Joints tested: {successful_tests}/{len(joint_names)}")
    if successful_tests == len(joint_names):
        print(f"   🎉 All joints tested successfully!")
    else:
        failed_count = len(joint_names) - successful_tests
        print(f"   ⚠️  {failed_count} joint(s) had issues or were skipped")


def verify_home_position(controller, simulate=False):
    """
    Verify that all joints are at home position (0 degrees).
    
    Args:
        controller: XArmController instance
        simulate: If True, simulate the verification
    
    Returns:
        bool: True if at home position, False otherwise
    """
    if simulate:
        print("    [SIM] ✓ All joints confirmed at home position [0, 0, 0, 0, 0, 0]")
        return True
    
    current_joints = controller.get_current_joints()
    if current_joints:
        print(f"    📍 Current joints: {[round(j, 2) for j in current_joints]}")
        
        # Check if all joints are close to zero (within 0.5 degrees)
        if all(abs(joint) < 0.5 for joint in current_joints):
            print("    ✓ All joints confirmed at home position")
            return True
        else:
            print("    ⚠️  Some joints are not at home position")
            return False
    else:
        print("    ⚠️  Could not read current joint positions")
        return False


def main():
    parser = argparse.ArgumentParser(description='Interactive Joint Testing Demonstration')
    parser.add_argument('--simulate', action='store_true', 
                       help='Run in simulation mode (no hardware required)')
    parser.add_argument('--real', action='store_true', 
                       help='Connect to real robot hardware')
    parser.add_argument('--host', default='127.0.0.1',
                       help='Robot IP address (default: 127.0.0.1 for simulator)')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.simulate and args.real:
        print("Error: Cannot specify both --simulate and --real")
        sys.exit(1)
    
    if not args.simulate and not args.real:
        print("Error: Must specify either --simulate or --real")
        sys.exit(1)
    
    simulate_mode = args.simulate
    robot_host = args.host
    
    # If running in real mode and using default host, prompt for robot IP
    if args.real and robot_host == '127.0.0.1':
        print("\n🤖 Real Hardware Mode Selected")
        try:
            robot_host = input("Enter robot IP address (default: 192.168.1.237): ").strip()
            if not robot_host:
                robot_host = '192.168.1.237'
            print(f"Using robot IP: {robot_host}")
        except (EOFError, KeyboardInterrupt):
            print("No input provided. Using default: 192.168.1.237")
            robot_host = '192.168.1.237'
    
    print("=" * 70)
    print("🔧 INTERACTIVE JOINT TESTING DEMONSTRATION")
    print("=" * 70)
    print(f"Mode: {'SIMULATION' if simulate_mode else 'REAL HARDWARE'}")
    print(f"Host: {robot_host}")
    print("Test Pattern: Home → +2° → 0° → -2° → 0° (per joint)")
    print("=" * 70)
    
    if simulate_mode:
        # Pure simulation mode - no hardware connection needed
        print("\n🔄 Running in SIMULATION mode")
        print("   No hardware connection required")
        
        # Create a mock controller for simulation
        controller = None
        
        print("\n1. [SIM] Initializing robot controller...")
        print("   [SIM] ✓ Controller initialized")
        
        print("\n2. [SIM] Homing robot - moving all joints to 0°...")
        print("   [SIM] ✓ All joints moved to [0, 0, 0, 0, 0, 0]")
        verify_home_position(controller, simulate=True)
        
        # Run simulation
        run_interactive_joint_test(controller, simulate_mode=True)
        
        print("\n3. [SIM] Final homing - returning all joints to 0°...")
        print("   [SIM] ✓ All joints returned to home position")
        
        print("\n4. [SIM] Final status:")
        print("   [SIM] ✓ All joint tests completed successfully")
        print("   [SIM] ✓ Simulation demonstrates expected real hardware behavior")
        
    else:
        # Real hardware mode
        print(f"\n🔗 Connecting to robot at {robot_host}")
        
        try:
            # Create XArmController
            controller = XArmController(
                config_path='users/settings/',
                gripper_type='bio',
                enable_track=False,  # Not needed for joint testing
                auto_enable=False
            )
            
            # Set up the robot connection based on host
            if robot_host == '127.0.0.1':
                # Docker simulator - need special handling
                from xarm.wrapper import XArmAPI
                controller.arm = XArmAPI(robot_host, check_joint_limit=False)
            else:
                # Real hardware - create XArmAPI with the specified host
                from xarm.wrapper import XArmAPI
                controller.arm = XArmAPI(robot_host)
            
            # Initialize
            if not controller.initialize():
                print("✗ Failed to initialize robot controller")
                sys.exit(1)
                
            print("✓ Robot controller initialized")
            
        except Exception as e:
            print(f"✗ Failed to connect to robot: {e}")
            sys.exit(1)
        
        try:
            # Check if robot is alive
            if not controller.is_alive:
                print("✗ Robot is not responding")
                sys.exit(1)
            
            print("✓ Robot is alive and responding")
            
            # Initial homing
            print("\n1. Homing robot - moving all joints to 0°...")
            if controller.move_joints(angles=[0, 0, 0, 0, 0, 0], wait=True):
                print("   ✓ All joints moved to [0, 0, 0, 0, 0, 0]")
                verify_home_position(controller, simulate=False)
            else:
                print("   ✗ Failed to move joints to home position")
                sys.exit(1)
            
            # Interactive confirmation to start testing
            print(f"\n2. Ready to start interactive joint testing...")
            try:
                input("   Press Enter to begin joint testing (Ctrl+C to cancel): ")
            except (EOFError, KeyboardInterrupt):
                print("   Testing cancelled by user")
                sys.exit(0)
            
            # Run the joint testing
            run_interactive_joint_test(controller, simulate_mode=False)
            
            # Final homing
            print(f"\n3. Final homing - returning all joints to 0°...")
            if controller.move_joints(angles=[0, 0, 0, 0, 0, 0], wait=True):
                print("   ✓ All joints returned to home position")
                verify_home_position(controller, simulate=False)
            else:
                print("   ⚠️  Could not return to home position")
            
            print("   ✅ Interactive joint testing completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error during joint testing: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            print(f"\n4. Cleanup:")
            print("   Disconnecting from robot...")
            controller.disconnect()
            print("   ✓ Disconnected successfully")

    print("\n" + "=" * 70)
    print("🏁 JOINT TESTING COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main() 