#!/usr/bin/env python3
"""
5-Joint Testing Demonstration Script

This script demonstrates joint movement testing for xArm5 robots.
It homes the robot to all joints at 0 degrees, then tests each
of the 5 joints by moving them through: +2°, 0°, -2°, 0°.
Additionally, it tests the gripper with open/close operations.

Usage:
    python demo_5joints.py --simulate     # Run in simulation mode
    python demo_5joints.py --real         # Connect to real robot hardware
"""

import os
import sys
import time
import argparse

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.xarm_controller import XArmController


def test_joint(controller, joint_id, joint_name, simulate=False):
    """Test a single joint through: +2°, 0°, -2°, 0°"""
    print(f"\n🔧 Testing {joint_name} (Joint {joint_id + 1}):")
    
    angles = [2.0, 0.0, -2.0, 0.0]
    descriptions = ["+2°", "0°", "-2°", "0°"]
    
    for angle, desc in zip(angles, descriptions):
        print(f"    Moving to {desc}")
        
        if simulate:
            print(f"      [SIM] Moving to {angle}°...")
            time.sleep(1)
            print(f"      [SIM] ✓ At {angle}°")
        else:
            if controller.move_single_joint(joint_id, angle, wait=True):
                print(f"      ✓ Moved to {angle}°")
            else:
                print(f"      ✗ Failed to move to {angle}°")
                return False
        
        time.sleep(0.5)
    
    return True


def test_gripper(controller, simulate=False):
    """Test gripper open/close"""
    print(f"\n🔧 Testing Gripper:")
    
    if simulate:
        print("    [SIM] Opening gripper...")
        time.sleep(1)
        print("    [SIM] ✓ Opened")
        print("    [SIM] Closing gripper...")
        time.sleep(1)
        print("    [SIM] ✓ Closed")
        return True
    else:
        
        print("    Opening gripper...")
        if not controller.open_gripper():
            print("    ✗ Failed to open")
            return False
        print("    ✓ Opened")
        
        time.sleep(1)
        
        print("    Closing gripper...")
        if not controller.close_gripper():
            print("    ✗ Failed to close")
            return False
        print("    ✓ Closed")

        print("    Opening gripper...")
        if not controller.open_gripper():
            print("    ✗ Failed to open")
            return False
        print("    ✓ Opened")
        
        return True


def run_joint_tests(controller, simulate=False):
    """Run tests for all 5 joints plus gripper"""
    joint_names = [
        "Base Joint",
        "Shoulder Joint", 
        "Elbow Joint",
        "Wrist 1 Joint",
        "Wrist 2 Joint"
    ]
    
    print(f"\n📋 Testing 5 joints + gripper")
    print(f"   Mode: {'SIMULATION' if simulate else 'REAL HARDWARE'}")
    print("=" * 50)
    
    successful = 0
    
    # Test each joint
    for i, name in enumerate(joint_names):
        if test_joint(controller, i, name, simulate):
            successful += 1
            print(f"    ✅ {name} - SUCCESS")
        else:
            print(f"    ❌ {name} - FAILED")
    
    # Test gripper
    gripper_ok = test_gripper(controller, simulate)
    if gripper_ok:
        print(f"    ✅ Gripper - SUCCESS")
        successful += 1
    else:
        print(f"    ❌ Gripper - FAILED")
    
    # Summary
    total = len(joint_names) + 1
    print(f"\n📊 Results: {successful}/{total} components successful")
    
    return successful == total


def main():
    parser = argparse.ArgumentParser(description='5-Joint Testing Demo')
    parser.add_argument('--simulate', action='store_true', help='Simulation mode')
    parser.add_argument('--real', action='store_true', help='Real hardware mode')
    
    args = parser.parse_args()
    
    if args.simulate and args.real:
        print("Error: Cannot specify both --simulate and --real")
        sys.exit(1)
    
    if not args.simulate and not args.real:
        print("Error: Must specify either --simulate or --real")
        sys.exit(1)
    
    simulate = args.simulate
    
    print("=" * 50)
    print("🔧 xArm5 JOINT TESTING DEMO")
    print("=" * 50)
    print(f"Mode: {'SIMULATION' if simulate else 'REAL HARDWARE'}")
    
    if simulate:
        print("\n🔄 Running in SIMULATION mode")
        
        print("\n1. [SIM] Homing to [0, 0, 0, 0, 0]...")
        time.sleep(1)
        print("   [SIM] ✓ Homed")
        
        # Run simulation
        success = run_joint_tests(None, simulate=True)
        
        print("\n2. [SIM] Returning to home...")
        time.sleep(1)
        print("   [SIM] ✓ Home position")
        
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n⚠️ Some tests failed")
            
    else:
        print(f"\n🔗 Connecting to robot...")
        
        try:
            controller = XArmController(
                profile_name='real_hw',  # Use real_hw profile from config (192.168.1.237)
                model=5,  # Force xArm5 model
                gripper_type='bio',
                enable_track=False,
                auto_enable=False
            )
            
            if not controller.initialize():
                print("✗ Failed to initialize")
                sys.exit(1)
                
            print("✓ Connected")
            
            if not controller.is_alive:
                print("✗ Robot not responding")
                sys.exit(1)
            
            print("✓ Robot alive")
            
            # Enable gripper
            print("\n🔧 Enabling gripper...")
            controller.enable_gripper_component()
            print("   ✓ Gripper ready")
            
            # Home to 5 joints (0°)
            print("\n1. Homing to [0, 0, 0, 0, 0]...")
            if controller.move_joints(angles=[0, 0, 0, 0, 0], wait=True):
                print("   ✓ Homed")
            else:
                print("   ✗ Failed to home")
                sys.exit(1)
            
            # Run tests
            print("\n2. Starting joint tests...")
            success = run_joint_tests(controller, simulate=False)
            
            # Return home
            print(f"\n3. Returning to home...")
            if controller.move_joints(angles=[0, 0, 0, 0, 0], wait=True):
                print("   ✓ Home position")
            else:
                print("   ⚠️ Could not return home")
            
            if success:
                print("\n🎉 All tests passed!")
            else:
                print("\n⚠️ Some tests failed")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            print(f"\n4. Cleanup...")
            if 'controller' in locals():
                controller.disconnect()
            print("   ✓ Disconnected")

    print("\n" + "=" * 50)
    print("🏁 TESTING COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main() 
