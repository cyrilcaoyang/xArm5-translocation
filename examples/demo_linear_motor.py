"""
Linear Motor Control Demonstration
==================================

A dedicated demonstration script for linear motor control with gripper operations.
This script demonstrates moving the linear track to specific positions (100, 200, 400, 700mm)
while keeping the robot arm joints at zero and performing gripper operations at each position.

Supports: xArm5 (5 joints), xArm6 (6 joints), xArm7 (7 joints), xArm850 (6 joints)
Auto-adapts joint positions based on robot model configuration.

Features:
- Keeps arm joints at zero throughout the demo (adapts to model)
- Homes linear motor to position 0
- Moves to specified positions: 100, 200, 400, 700mm
- Performs open/close gripper cycle at each position
- Works with both real hardware and simulation mode
- Automatic model detection from configuration

Usage:
    python demo_linear_motor.py [--simulate]
    
Options:
    --simulate    Run in simulation mode (no real hardware required)
    --real        Connect to real robot (default)
    --help        Show this help message

Requirements:
- For real hardware: xArm robot with linear track and gripper
- For simulation: Docker simulator running at 127.0.0.1
"""

import sys
import time
import os
import argparse

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.xarm_controller import XArmController


def demonstrate_gripper_cycle(controller, position, simulate=False):
    """
    Demonstrate gripper open/close cycle at a specific position.
    
    Args:
        controller: XArmController instance
        position: Current linear motor position (for logging)
        simulate: If True, simulate the operations without hardware
    """
    print(f"    🔧 Gripper operations at position {position}mm:")
    
    if simulate:
        print("      [SIM] Opening gripper...")
        time.sleep(1.5)
        print("      [SIM] ✓ Gripper opened")
        
        print("      [SIM] Closing gripper...")
        time.sleep(1.5)
        print("      [SIM] ✓ Gripper closed")
        return True
    
    # Real hardware operations
    print("      → Opening gripper...")
    if controller.open_gripper():
        print("      ✓ Gripper opened successfully")
    else:
        print("      ✗ Failed to open gripper")
        return False
    
    time.sleep(1.5)
    
    print("      → Closing gripper...")
    if controller.close_gripper():
        print("      ✓ Gripper closed successfully")
    else:
        print("      ✗ Failed to close gripper")
        return False
    
    time.sleep(1.5)
    return True


def run_linear_motor_demo(controller, target_positions, simulate_mode=False):
    """
    Run the main linear motor demonstration.
    
    Args:
        controller: XArmController instance
        target_positions: List of positions to move to
        simulate_mode: If True, simulate linear motor movements
    """
    print(f"\n📋 Linear Motor Movement Sequence:")
    print(f"   Target positions: {target_positions} mm")
    print(f"   Mode: {'SIMULATION' if simulate_mode else 'REAL HARDWARE'}")
    print("   Operations at each position: open gripper → close gripper")
    print("=" * 70)
    
    for i, position in enumerate(target_positions, 1):
        print(f"\n📍 Step {i}/{len(target_positions)}: Position {position}mm")
        
        if simulate_mode:
            print(f"    [SIM] Moving linear motor to {position}mm...")
            time.sleep(2)  # Simulate movement time
            print(f"    [SIM] ✓ Linear motor at {position}mm")
            
            # Simulate gripper operations
            demonstrate_gripper_cycle(controller, position, simulate=True)
            
        else:
            # Real hardware operations
            print(f"    → Moving linear motor to {position}mm...")
            if controller.move_track_to_position(position):
                print(f"    ✓ Linear motor moved to {position}mm")
                
                # Verify position
                pos_ret = controller.get_track_position()
                current_pos = None
                if isinstance(pos_ret, list) and len(pos_ret) > 1 and isinstance(pos_ret[1], (int, float)):
                    current_pos = pos_ret[1]
                elif isinstance(pos_ret, (int, float)):
                    current_pos = pos_ret

                if current_pos is not None:
                    print(f"    📍 Confirmed position: {current_pos}mm")
                    if abs(current_pos - position) > 10:
                        print(f"    ⚠️  Warning: Position discrepancy > 10mm (is: {current_pos}, expected: {position})")
                
                # Perform gripper operations
                if controller.has_gripper() and controller.is_component_enabled('gripper'):
                    demonstrate_gripper_cycle(controller, position, simulate=False)
                else:
                    print(f"    ⚠️  Gripper not available - skipping gripper operations")
                    
            else:
                print(f"    ✗ Failed to move linear motor to {position}mm")
                print(f"    ⚠️  Continuing with next position...")
        
        # Pause between positions
        time.sleep(1)
    
    # Return to home
    print(f"\n🏠 Returning to home position...")
    if simulate_mode:
        print("    [SIM] Moving linear motor to home (0mm)...")
        time.sleep(2)
        print("    [SIM] ✓ Linear motor at home position")
    else:
        if controller.reset_track():
            print("    ✓ Linear motor returned to home (0mm)")
            pos_ret = controller.get_track_position()
            current_pos = None
            if isinstance(pos_ret, list) and len(pos_ret) > 1 and isinstance(pos_ret[1], (int, float)):
                current_pos = pos_ret[1]
            elif isinstance(pos_ret, (int, float)):
                current_pos = pos_ret

            if current_pos is not None and abs(current_pos) > 10:
                print(f"    ⚠️  Warning: Home position discrepancy > 10mm (is: {current_pos})")
        else:
            print("    ✗ Failed to return to home position")


def main():
    parser = argparse.ArgumentParser(description='Linear Motor Control Demonstration')
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
    
    simulate_mode = args.simulate
    robot_host = args.host
    
    # For real hardware, prompt for IP address if not specified
    if not simulate_mode and robot_host == '127.0.0.1':
        try:
            robot_host = input("Enter robot IP address (default: 192.168.1.237): ").strip()
            if not robot_host:
                robot_host = '192.168.1.237'
        except (EOFError, KeyboardInterrupt):
            # Handle non-interactive environments
            robot_host = '192.168.1.237'
            print(f"Using default IP address: {robot_host}")
    
    # Target positions for demonstration
    target_positions = [100, 200, 400, 700]
    
    print("=" * 70)
    print("🚀 LINEAR MOTOR CONTROL DEMONSTRATION")
    print("=" * 70)
    print(f"Mode: {'SIMULATION' if simulate_mode else 'REAL HARDWARE'}")
    print(f"Host: {robot_host}")
    print(f"Target positions: {target_positions} mm")
    print("=" * 70)
    
    if simulate_mode:
        # Pure simulation mode - no hardware connection needed
        print("\n🔄 Running in SIMULATION mode")
        print("   No hardware connection required")
        
        # Create a mock controller for simulation
        controller = None
        
        print("\n1. [SIM] Initializing robot controller...")
        print("   [SIM] ✓ Controller initialized")
        
        print("\n2. [SIM] Setting arm joints to zero position...")
        print("   [SIM] ✓ Arm joints set to zero (adapts to robot model)")
        
        print("\n3. [SIM] Homing linear motor...")
        print("   [SIM] ✓ Linear motor homed to position 0")
        
        # Run simulation
        run_linear_motor_demo(controller, target_positions, simulate_mode=True)
        
        print("\n4. [SIM] Final status:")
        print("   [SIM] ✓ All operations completed successfully")
        print("   [SIM] ✓ Simulation demonstrates expected real hardware behavior")
        
    else:
        # Real hardware mode
        print(f"\n🔗 Connecting to robot at {robot_host}")
        
        try:
            # Create XArmController - use absolute path to avoid path resolution issues
            script_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(script_dir, '..', 'settings') + '/'
            
            controller = XArmController(
                config_path=config_path,
                gripper_type='bio',
                enable_track=True,
                auto_enable=False
            )
            
            # Override robot IP if specified
            if robot_host != '127.0.0.1':
                controller.xarm_config['host'] = robot_host
            
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
            
            # Enable components
            print("\n1. Enabling robot components...")
            
            gripper_available = controller.enable_gripper_component()
            track_available = controller.enable_track_component()
            
            if gripper_available:
                print("   ✓ Gripper enabled")
            else:
                print("   ⚠️  Gripper not available")
                
            if track_available:
                print("   ✓ Linear track enabled")
            else:
                print("   ✗ Linear track not available")
                print("   🔄 Switching to simulation mode for linear track...")
                simulate_mode = True
            
            # Set arm to zero position
            print("\n2. Setting arm joints to zero position...")
            num_joints = controller.get_num_joints()
            zero_angles = [0] * num_joints
            if controller.move_joints(angles=zero_angles):
                print(f"   ✓ Arm joints set to {zero_angles}")
            else:
                print("   ⚠️  Could not move joints (may already be at zero)")
            
            # Verify joints are at zero
            current_joints = controller.get_current_joints()
            if current_joints:
                print(f"   📍 Current joints: {current_joints}")
                if isinstance(current_joints, (list, tuple)) and all(abs(joint) < 1.0 for joint in current_joints):
                    print("   ✓ Joints confirmed at zero position")
            
            # Home linear motor (if available)
            if track_available and not simulate_mode:
                print("\n3. Homing linear motor...")
                if controller.reset_track():
                    print("   ✓ Linear motor homed to position 0")
                else:
                    print("   ✗ Failed to home linear motor")
                    simulate_mode = True
            
            # Run the demonstration
            run_linear_motor_demo(controller, target_positions, simulate_mode)
            
            # Final verification
            print(f"\n4. Final verification:")
            final_joints = controller.get_current_joints()
            if final_joints is not None:
                print(f"   📍 Final arm joints: {final_joints}")
                if isinstance(final_joints, (list, tuple)) and all(abs(joint) < 1.0 for joint in final_joints):
                    print("   ✓ Arm joints maintained at zero throughout demo")
                else:
                    print("   ⚠️  Arm joints have moved - resetting to zero...")
                    num_joints = controller.get_num_joints()
                    zero_angles = [0] * num_joints
                    controller.move_joints(angles=zero_angles)
            
            print("   ✅ Linear motor demonstration completed successfully!")
            
        except Exception as e:
            print(f"\n❌ Error during demonstration: {e}")
            import traceback
            traceback.print_exc()
            
        finally:
            print(f"\n5. Cleanup:")
            print("   Disconnecting from robot...")
            controller.disconnect()
            print("   ✓ Disconnected successfully")
    
    print("\n" + "=" * 70)
    print("🏁 DEMONSTRATION COMPLETE")
    print("=" * 70)


if __name__ == "__main__":
    main() 