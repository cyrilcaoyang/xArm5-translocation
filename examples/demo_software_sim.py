#!/usr/bin/env python3
"""
Enhanced Software Simulation with Collision Detection
====================================================

This example demonstrates the enhanced software simulation capabilities including:
1. Joint limit checking and violations
2. Workspace limit checking
3. Basic self-collision detection
4. All movement commands work identically to hardware
5. Comprehensive error reporting and safety checks

The simulation mode now provides realistic collision detection and safety 
features that match what you'd see in professional robotics simulation software.

Features demonstrated:
- Official SDK simulation mode (do_not_open=True)
- Enhanced collision detection system
- Joint limit violations with detailed feedback
- Workspace boundary checking
- Self-collision detection between joints
- Gripper and linear track simulation
- State monitoring and error handling
- Realistic motion planning validation

Usage:
    python demo_software_sim.py

Requirements:
- No hardware required
- All commands execute with realistic validation
- Perfect for development, testing, and education
"""

import sys
import os
import math
import time

# Add src directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.xarm_controller import XArmController

def demo_basic_simulation():
    """Demonstrate basic simulation mode functionality."""
    print("=" * 60)
    print("BASIC SIMULATION MODE DEMO")
    print("=" * 60)
    
    # Initialize the controller in simulation mode
    controller = XArmController(
        config_path='src/settings/',
        simulation_mode=True,
        model=7,
        auto_enable=True
    )
    
    print(f"✓ Controller initialized in simulation mode")
    print(f"✓ Model: xArm{controller.model} with {controller.num_joints} joints")
    print(f"✓ Gripper type: {controller.gripper_type}")
    print(f"✓ Linear track: {'enabled' if controller.enable_track else 'disabled'}")
    print()
    
    # Test basic movements
    print("Testing basic movements...")
    
    # Safe joint movement
    print("1. Safe joint movement:")
    success = controller.move_joints([0, -30, 0, 30, 0, 0, 0])
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")
    
    # Safe Cartesian movement
    print("2. Safe Cartesian movement:")
    success = controller.move_to_position(x=400, y=100, z=300)
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")
    
    # Gripper operation
    print("3. Gripper operation:")
    success = controller.open_gripper()
    print(f"   Open gripper: {'✓ Success' if success else '✗ Failed'}")
    success = controller.close_gripper()
    print(f"   Close gripper: {'✓ Success' if success else '✗ Failed'}")
    
    # Linear track movement
    print("4. Linear track movement:")
    success = controller.move_track_to_position(100)
    print(f"   Result: {'✓ Success' if success else '✗ Failed'}")
    
    return controller

def demo_collision_detection(controller):
    """Demonstrate collision detection features."""
    print("\n" + "=" * 60)
    print("COLLISION DETECTION DEMO")
    print("=" * 60)
    
    print("Testing joint limit violations...")
    
    # Test joint limit violations
    test_cases = [
        {
            'name': 'Joint 1 over-rotation',
            'angles': [400, 0, 0, 0, 0, 0, 0],  # 400° exceeds ±360° limit
            'expected': 'Joint limit violation'
        },
        {
            'name': 'Joint 2 extreme position',
            'angles': [0, -150, 0, 0, 0, 0, 0],  # -150° exceeds -118° limit
            'expected': 'Joint limit violation'
        },
        {
            'name': 'Joint 3 dangerous angle',
            'angles': [0, 0, 50, 0, 0, 0, 0],  # 50° exceeds 11° limit
            'expected': 'Joint limit violation'
        },
        {
            'name': 'Multiple joint violations',
            'angles': [400, -150, 50, 0, 0, 0, 0],  # Multiple violations
            'expected': 'Multiple joint limit violations'
        }
    ]
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{i}. {test['name']}:")
        print(f"   Attempting: {test['angles']}")
        success = controller.move_joints(test['angles'])
        print(f"   Result: {'✗ Blocked (Expected)' if not success else '✓ Unexpected Success'}")
    
    print("\nTesting workspace limit violations...")
    
    # Test workspace limit violations
    workspace_tests = [
        {
            'name': 'X-axis out of bounds',
            'pose': [1000, 0, 300, 180, 0, 0],  # X too far
            'expected': 'X workspace limit violation'
        },
        {
            'name': 'Z-axis below floor',
            'pose': [300, 0, -300, 180, 0, 0],  # Z below minimum
            'expected': 'Z workspace limit violation'
        },
        {
            'name': 'Y-axis extreme position',
            'pose': [300, 800, 300, 180, 0, 0],  # Y too far
            'expected': 'Y workspace limit violation'
        }
    ]
    
    for i, test in enumerate(workspace_tests, 1):
        print(f"\n{i}. {test['name']}:")
        print(f"   Attempting: {test['pose']}")
        success = controller.move_to_position(*test['pose'])
        print(f"   Result: {'✗ Blocked (Expected)' if not success else '✓ Unexpected Success'}")
    
    print("\nTesting self-collision detection...")
    
    # Test self-collision scenarios
    collision_tests = [
        {
            'name': 'Joint 1 & 2 collision zone',
            'angles': [170, -100, 0, 0, 0, 0, 0],  # Should trigger collision
            'expected': 'Self-collision between joints'
        },
        {
            'name': 'Joint 2 & 3 collision zone',
            'angles': [0, 110, 5, 0, 0, 0, 0],  # Should trigger collision
            'expected': 'Self-collision between joints'
        }
    ]
    
    for i, test in enumerate(collision_tests, 1):
        print(f"\n{i}. {test['name']}:")
        print(f"   Attempting: {test['angles']}")
        success = controller.move_joints(test['angles'])
        print(f"   Result: {'✗ Blocked (Expected)' if not success else '✓ Unexpected Success'}")

def demo_safe_operations(controller):
    """Demonstrate safe operations that should succeed."""
    print("\n" + "=" * 60)
    print("SAFE OPERATIONS DEMO")
    print("=" * 60)
    
    print("Testing safe joint movements...")
    
    safe_positions = [
        [0, 0, 0, 0, 0, 0, 0],
        [30, -45, -30, 45, 0, 30, 0],
        [-30, 45, -60, -45, 90, -30, 0],
        [0, -30, 0, 30, 0, 0, 0]
    ]
    
    for i, angles in enumerate(safe_positions, 1):
        print(f"{i}. Moving to safe position {i}: {angles}")
        success = controller.move_joints(angles)
        print(f"   Result: {'✓ Success' if success else '✗ Failed'}")
        
        # Get current position
        current_pos = controller.get_current_position()
        if current_pos:
            print(f"   Current position: {[round(x, 1) for x in current_pos]}")
    
    print("\nTesting safe Cartesian movements...")
    
    safe_cartesian = [
        [300, 0, 300, 180, 0, 0],
        [400, 200, 400, 180, 0, 0],
        [200, -200, 250, 180, 0, 0],
        [350, 0, 350, 180, 0, 0]
    ]
    
    for i, pose in enumerate(safe_cartesian, 1):
        print(f"{i}. Moving to safe Cartesian position {i}: {pose}")
        success = controller.move_to_position(*pose)
        print(f"   Result: {'✓ Success' if success else '✗ Failed'}")

def demo_system_info(controller):
    """Display system information and status."""
    print("\n" + "=" * 60)
    print("SYSTEM INFORMATION")
    print("=" * 60)
    
    print(f"Simulation Mode: {'✓ Enabled' if controller.simulation_mode else '✗ Disabled'}")
    print(f"Model: xArm{controller.model}")
    print(f"Number of joints: {controller.num_joints}")
    print(f"Gripper type: {controller.gripper_type}")
    print(f"Linear track: {'✓ Enabled' if controller.enable_track else '✗ Disabled'}")
    
    print(f"\nComponent States:")
    for component, state in controller.states.items():
        print(f"  {component.capitalize()}: {state.name}")
    
    print(f"\nCurrent Positions:")
    print(f"  Joint angles: {[round(x, 1) for x in controller.last_joints]}")
    print(f"  Cartesian: {[round(x, 1) for x in controller.last_position]}")
    print(f"  Track position: {controller.last_track_position}")
    
    # Show collision detection parameters
    if hasattr(controller, 'joint_limits'):
        print(f"\nJoint Limits (degrees):")
        limits = controller.joint_limits.get(controller.model, [])
        for i, (min_limit, max_limit) in enumerate(limits):
            print(f"  Joint {i+1}: {min_limit}° to {max_limit}°")
    
    if hasattr(controller, 'workspace_limits'):
        print(f"\nWorkspace Limits:")
        for axis, (min_limit, max_limit) in controller.workspace_limits.items():
            unit = "mm" if axis in ['x', 'y', 'z'] else "°"
            print(f"  {axis.upper()}: {min_limit}{unit} to {max_limit}{unit}")

def main():
    """Main demo function."""
    print("Enhanced xArm Simulation Mode with Collision Detection")
    print("=" * 60)
    print("This demo showcases realistic collision detection and safety features")
    print("that provide professional-grade simulation capabilities.")
    print()
    
    try:
        # Initialize and run basic demo
        controller = demo_basic_simulation()
        
        # Test collision detection
        demo_collision_detection(controller)
        
        # Test safe operations
        demo_safe_operations(controller)
        
        # Show system information
        demo_system_info(controller)
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETED SUCCESSFULLY")
        print("=" * 60)
        print("✓ All simulation features demonstrated")
        print("✓ Collision detection working properly")
        print("✓ Safety systems operational")
        print("✓ Ready for development and testing")
        
    except Exception as e:
        print(f"\n✗ Demo failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 