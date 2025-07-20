#!/usr/bin/env python3
"""
Force Torque Sensor Demo Script

This script demonstrates the three main functionalities of the 6-axis force torque sensor:
1. Safety monitoring - Alert when force/torque exceeds thresholds
2. Linear movement until force threshold - For button pressing, drawer pulling
3. Joint movement until torque threshold - For joint-specific operations

Usage:
    python demo_force_torque.py --real
    python demo_force_torque.py --simulation
"""

import os
import sys
import time
import argparse
import threading

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.xarm_controller import XArmController


def demo_safety_monitoring(controller):
    """Demo 1: Safety monitoring with alerts."""
    print("\n🔒 Demo 1: Safety Monitoring")
    print("=" * 50)
    
    if not controller.has_force_torque_sensor():
        print("❌ Force torque sensor not available")
        return False
    
    print("Enabling force torque sensor...")
    if not controller.enable_force_torque_sensor():
        print("❌ Failed to enable force torque sensor")
        return False
    
    print("Calibrating sensor...")
    if not controller.calibrate_force_torque_sensor():
        print("❌ Failed to calibrate sensor")
        return False
    
    print("✅ Safety monitoring active!")
    print("📊 Monitoring force/torque for 30 seconds...")
    print("💡 Try applying force to the end effector to trigger alerts")
    
    # Monitor for 30 seconds
    start_time = time.time()
    while time.time() - start_time < 30:
        # Check for safety violations
        if controller.check_force_torque_safety():
            print("🚨 Safety violation detected!")
        
        # Display current readings
        data = controller.get_force_torque_data()
        if data:
            print(f"📈 Current readings: F[{data[0]:6.2f}, {data[1]:6.2f}, {data[2]:6.2f}] "
                  f"T[{data[3]:6.2f}, {data[4]:6.2f}, {data[5]:6.2f}]")
        
        time.sleep(1)
    
    print("✅ Safety monitoring demo completed")
    return True


def demo_linear_force_movement(controller):
    """Demo 2: Linear movement until force threshold."""
    print("\n🔧 Demo 2: Linear Force-Controlled Movement")
    print("=" * 50)
    
    if not controller.is_component_enabled('force_torque'):
        print("❌ Force torque sensor must be enabled")
        return False
    
    print("This demo will move the robot downward until it detects resistance")
    print("💡 Place your hand or an object under the end effector")
    
    input("Press Enter to start downward movement...")
    
    # Move downward until force threshold is reached
    direction = [0, 0, -1]  # Downward direction
    force_threshold = 20.0   # 20 Newtons threshold
    
    print(f"🔄 Moving downward until {force_threshold}N force detected...")
    
    success = controller.move_until_force(
        direction=direction,
        force_threshold=force_threshold,
        speed=50,  # Slow speed for safety
        timeout=30.0
    )
    
    if success:
        print("✅ Force threshold reached! Movement stopped.")
    else:
        print("❌ Movement failed or timed out")
    
    return success


def demo_joint_torque_movement(controller):
    """Demo 3: Joint movement until torque threshold."""
    print("\n⚙️ Demo 3: Joint Torque-Controlled Movement")
    print("=" * 50)
    
    if not controller.is_component_enabled('force_torque'):
        print("❌ Force torque sensor must be enabled")
        return False
    
    # Get current joint angles
    current_joints = controller.get_current_joints()
    if current_joints is None:
        print("❌ Failed to get current joint angles")
        return False
    
    print(f"Current joint angles: {[f'{j:.1f}°' for j in current_joints]}")
    
    # Choose joint 5 (wrist joint) for demo
    joint_id = 5
    if joint_id > controller.get_num_joints():
        print(f"❌ Joint {joint_id} not available on this robot")
        return False
    
    current_angle = current_joints[joint_id - 1]
    target_angle = current_angle + 30  # Move 30 degrees
    
    print(f"🔄 Moving joint {joint_id} from {current_angle:.1f}° to {target_angle:.1f}°")
    print("💡 Try resisting the movement to trigger torque threshold")
    
    input("Press Enter to start joint movement...")
    
    success = controller.move_joint_until_torque(
        joint_id=joint_id,
        target_angle=target_angle,
        torque_threshold=2.0,  # 2 Nm threshold
        speed=10,  # Slow speed for safety
        timeout=30.0
    )
    
    if success:
        print("✅ Torque threshold reached or target angle achieved!")
    else:
        print("❌ Joint movement failed or timed out")
    
    return success


def demo_force_torque_data_analysis(controller):
    """Demo 4: Real-time force/torque data analysis."""
    print("\n📊 Demo 4: Force/Torque Data Analysis")
    print("=" * 50)
    
    if not controller.is_component_enabled('force_torque'):
        print("❌ Force torque sensor must be enabled")
        return False
    
    print("📈 Real-time force/torque data analysis for 20 seconds...")
    print("💡 Apply various forces and torques to see the analysis")
    
    start_time = time.time()
    while time.time() - start_time < 20:
        # Get comprehensive data
        data = controller.get_force_torque_data()
        magnitude = controller.get_force_torque_magnitude()
        direction = controller.get_force_torque_direction()
        
        if data and magnitude and direction:
            print(f"\n📊 Force: [{data[0]:6.2f}, {data[1]:6.2f}, {data[2]:6.2f}] N "
                  f"(mag: {magnitude['force_magnitude']:6.2f} N)")
            print(f"📊 Torque: [{data[3]:6.2f}, {data[4]:6.2f}, {data[5]:6.2f}] Nm "
                  f"(mag: {magnitude['torque_magnitude']:6.2f} Nm)")
            
            if direction['force_direction']:
                print(f"🧭 Force direction: [{direction['force_direction'][0]:.2f}, "
                      f"{direction['force_direction'][1]:.2f}, {direction['force_direction'][2]:.2f}]")
            
            if direction['torque_direction']:
                print(f"🧭 Torque direction: [{direction['torque_direction'][0]:.2f}, "
                      f"{direction['torque_direction'][1]:.2f}, {direction['torque_direction'][2]:.2f}]")
        
        time.sleep(2)
    
    print("✅ Data analysis demo completed")
    return True


def main():
    parser = argparse.ArgumentParser(description="Force Torque Sensor Demo")
    parser.add_argument("--real", action="store_true", help="Use real hardware")
    parser.add_argument("--simulation", action="store_true", help="Use simulation mode")
    parser.add_argument("--demo", choices=["1", "2", "3", "4", "all"], default="all",
                       help="Which demo to run (1=safety, 2=linear, 3=joint, 4=analysis, all=all)")
    
    args = parser.parse_args()
    
    # Determine mode
    if args.real and args.simulation:
        print("❌ Cannot use both --real and --simulation")
        return
    
    simulation_mode = args.simulation or not args.real
    
    print("🤖 xArm Force Torque Sensor Demo")
    print("=" * 50)
    print(f"Mode: {'Simulation' if simulation_mode else 'Real Hardware'}")
    print(f"Demo: {args.demo}")
    
    # Initialize controller
    try:
        controller = XArmController(
            simulation_mode=simulation_mode,
            auto_enable=True
        )
        
        if not controller.initialize():
            print("❌ Failed to initialize controller")
            return
        
        print("✅ Controller initialized successfully")
        
        # Run selected demos
        demos = []
        if args.demo == "1" or args.demo == "all":
            demos.append(("Safety Monitoring", demo_safety_monitoring))
        if args.demo == "2" or args.demo == "all":
            demos.append(("Linear Force Movement", demo_linear_force_movement))
        if args.demo == "3" or args.demo == "all":
            demos.append(("Joint Torque Movement", demo_joint_torque_movement))
        if args.demo == "4" or args.demo == "all":
            demos.append(("Data Analysis", demo_force_torque_data_analysis))
        
        for demo_name, demo_func in demos:
            print(f"\n🎯 Running {demo_name} Demo...")
            try:
                success = demo_func(controller)
                if success:
                    print(f"✅ {demo_name} demo completed successfully")
                else:
                    print(f"❌ {demo_name} demo failed")
            except KeyboardInterrupt:
                print(f"\n⏹️ {demo_name} demo interrupted by user")
                break
            except Exception as e:
                print(f"❌ {demo_name} demo failed with error: {e}")
        
        print("\n🎉 All demos completed!")
        
    except KeyboardInterrupt:
        print("\n⏹️ Demo interrupted by user")
    except Exception as e:
        print(f"❌ Demo failed with error: {e}")
    finally:
        if 'controller' in locals():
            controller.disconnect()
            print("🔌 Controller disconnected")


if __name__ == "__main__":
    main() 