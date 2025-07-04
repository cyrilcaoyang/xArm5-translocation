#!/usr/bin/env python3
"""
Simple Gripper Test Script

This script connects to the xArm robot and tests the gripper (end effector)
open and close functionality.

Usage:
    python gripper_test.py --real --host 192.168.1.237
"""

import os
import sys
import time
import argparse

# Add the project root directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from src.xarm_controller import XArmController


def test_gripper(controller):
    """
    Test gripper open and close functionality.
    
    Args:
        controller: XArmController instance
    
    Returns:
        bool: True if test successful, False otherwise
    """
    print("\n🔧 Testing Gripper (End Effector):")
    
    # Check if gripper is available
    if not controller.has_gripper():
        print("   ❌ No gripper detected")
        return False
    
    if not controller.is_component_enabled('gripper'):
        print("   🔄 Enabling gripper...")
        if not controller.enable_gripper_component():
            print("   ❌ Failed to enable gripper")
            return False
        print("   ✅ Gripper enabled")
    
    try:
        # Test 1: Open gripper
        print("\n   Test 1: Opening gripper...")
        if controller.open_gripper(wait=True):
            print("   ✅ Gripper opened successfully")
        else:
            print("   ❌ Failed to open gripper")
            return False
        
        time.sleep(2)  # Wait to observe the action
        
        # Test 2: Close gripper
        print("\n   Test 2: Closing gripper...")
        if controller.close_gripper(wait=True):
            print("   ✅ Gripper closed successfully")
        else:
            print("   ❌ Failed to close gripper")
            return False
        
        time.sleep(2)  # Wait to observe the action
        
        # Test 3: Open again
        print("\n   Test 3: Opening gripper again...")
        if controller.open_gripper(wait=True):
            print("   ✅ Gripper opened successfully")
        else:
            print("   ❌ Failed to open gripper")
            return False
        
        print("\n   🎉 All gripper tests passed!")
        return True
        
    except Exception as e:
        print(f"   ❌ Error during gripper test: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description='Simple Gripper Test')
    parser.add_argument('--real', action='store_true', required=True,
                       help='Connect to real robot hardware')
    parser.add_argument('--host', default='192.168.1.237',
                       help='Robot IP address (default: 192.168.1.237)')
    
    args = parser.parse_args()
    robot_host = args.host
    
    print("=" * 50)
    print("🤖 GRIPPER TEST")
    print("=" * 50)
    print(f"Robot IP: {robot_host}")
    print("=" * 50)
    
    try:
        # Create XArmController
        print(f"\n🔗 Connecting to robot at {robot_host}")
        controller = XArmController(
            config_path='users/settings/',
            gripper_type='bio',
            enable_track=False,  # Not needed for gripper test
            auto_enable=False
        )
        
        # Set up the robot connection
        from xarm.wrapper import XArmAPI
        controller.arm = XArmAPI(robot_host)
        
        # Initialize
        if not controller.initialize():
            print("❌ Failed to initialize robot controller")
            sys.exit(1)
            
        print("✅ Robot controller initialized")
        
        # Check if robot is alive
        if not controller.is_alive:
            print("❌ Robot is not responding")
            sys.exit(1)
        
        print("✅ Robot is alive and responding")
        
        # Run gripper test
        success = test_gripper(controller)
        
        if success:
            print("\n🎉 Gripper test completed successfully!")
        else:
            print("\n❌ Gripper test failed")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        print(f"\n🔄 Cleanup:")
        print("   Disconnecting from robot...")
        try:
            controller.disconnect()
            print("   ✅ Disconnected successfully")
        except:
            print("   ⚠️  Disconnect may have failed")

    print("\n" + "=" * 50)
    print("🏁 GRIPPER TEST COMPLETE")
    print("=" * 50)


if __name__ == "__main__":
    main() 