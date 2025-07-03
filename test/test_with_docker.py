#!/usr/bin/env python3
"""
Script to help run Docker integration tests.
"""

import subprocess
import sys
import time
import argparse

def check_docker_running():
    """Check if Docker is running."""
    try:
        result = subprocess.run(['docker', 'ps'], capture_output=True, text=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False

def check_container_running(container_name="uf_software"):
    """Check if the xArm container is running."""
    try:
        result = subprocess.run(['docker', 'ps', '--filter', f'name={container_name}'], 
                              capture_output=True, text=True)
        return container_name in result.stdout
    except FileNotFoundError:
        return False

def start_container():
    """Start the xArm Docker container."""
    print("Starting xArm Docker container...")
    cmd = [
        'docker', 'run', '-d', '--name', 'uf_software',
        '-p', '18333:18333',
        '-p', '502:502',
        '-p', '503:503', 
        '-p', '504:504',
        '-p', '30000:30000',
        '-p', '30001:30001',
        '-p', '30002:30002',
        '-p', '30003:30003',
        'danielwang123321/uf-ubuntu-docker'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Container started successfully")
            return True
        else:
            print(f"❌ Failed to start container: {result.stderr}")
            return False
    except FileNotFoundError:
        print("❌ Docker not found. Please install Docker.")
        return False

def start_xarm_firmware(arm_type="6"):
    """Start xArm firmware inside the container."""
    print(f"Starting xArm {arm_type} firmware...")
    cmd = ['docker', 'exec', 'uf_software', '/xarm_scripts/xarm_start.sh', arm_type, arm_type]
    
    try:
        # Run in background
        subprocess.Popen(cmd)
        print("✅ xArm firmware starting...")
        print("⏳ Waiting 10 seconds for firmware to initialize...")
        time.sleep(10)
        return True
    except FileNotFoundError:
        print("❌ Failed to start firmware")
        return False

def test_connection():
    """Test connection to the simulator."""
    print("Testing connection to simulator...")
    
    try:
        sys.path.append('src')
        from xarm.wrapper import XArmAPI
        
        arm = XArmAPI('127.0.0.1', check_joint_limit=False)
        arm.connect()
        
        if arm.connected:
            print("✅ Successfully connected to simulator")
            arm.disconnect()
            return True
        else:
            print("❌ Failed to connect to simulator")
            return False
            
    except Exception as e:
        print(f"❌ Connection test failed: {e}")
        return False

def run_unit_tests():
    """Run unit tests."""
    print("\n🧪 Running unit tests...")
    cmd = ['python', '-m', 'pytest', 'test/test_xarm_controller.py', '-v', '--tb=short']
    result = subprocess.run(cmd)
    return result.returncode == 0

def run_docker_tests():
    """Run Docker integration tests."""
    print("\n🐳 Running Docker integration tests...")
    cmd = ['python', '-m', 'pytest', 'tests/test_docker_integration.py', '-v', '--tb=short', '-m', 'integration']
    result = subprocess.run(cmd)
    return result.returncode == 0

def cleanup_container():
    """Clean up Docker container."""
    print("\n🧹 Cleaning up Docker container...")
    subprocess.run(['docker', 'stop', 'uf_software'], capture_output=True)
    subprocess.run(['docker', 'rm', 'uf_software'], capture_output=True)
    print("✅ Container cleaned up")

def main():
    parser = argparse.ArgumentParser(description='Run xArm tests with Docker simulator')
    parser.add_argument('--arm-type', default='6', choices=['5', '6', '7'], 
                       help='xArm type (5, 6, or 7)')
    parser.add_argument('--unit-only', action='store_true', 
                       help='Run only unit tests (no Docker required)')
    parser.add_argument('--docker-only', action='store_true',
                       help='Run only Docker integration tests')
    parser.add_argument('--no-cleanup', action='store_true',
                       help='Don\'t clean up Docker container after tests')
    parser.add_argument('--start-container', action='store_true',
                       help='Start Docker container and firmware, then exit')
    
    args = parser.parse_args()
    
    # Unit tests only
    if args.unit_only:
        success = run_unit_tests()
        sys.exit(0 if success else 1)
    
    # Check Docker availability
    if not check_docker_running():
        print("❌ Docker is not running. Please start Docker.")
        sys.exit(1)
    
    container_was_running = check_container_running()
    
    try:
        # Start container if needed
        if not container_was_running:
            if not start_container():
                sys.exit(1)
            
            if not start_xarm_firmware(args.arm_type):
                sys.exit(1)
        else:
            print("✅ Container already running")
        
        # Just start container and exit
        if args.start_container:
            print("🎯 Container and firmware started. Ready for testing!")
            print("Web UI available at: http://localhost:18333")
            print("Run tests with: python test/test_with_docker.py --docker-only")
            return
        
        # Test connection
        if not test_connection():
            print("❌ Cannot connect to simulator. Check if firmware is running.")
            if not container_was_running:
                cleanup_container()
            sys.exit(1)
        
        # Run tests
        success = True
        
        if not args.docker_only:
            success &= run_unit_tests()
        
        success &= run_docker_tests()
        
        if success:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed!")
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        success = False
    
    finally:
        # Cleanup if we started the container
        if not container_was_running and not args.no_cleanup:
            cleanup_container()
    
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main() 