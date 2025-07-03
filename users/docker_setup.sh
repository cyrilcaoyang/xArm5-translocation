#!/bin/bash
# xArm Docker Simulator Setup Script
# =====================================
# 
# This script sets up the UFACTORY xArm Docker simulator for development and testing.
# 
# Features:
# - Automatically pulls the official UFACTORY Docker image
# - Creates and configures the container with all necessary ports
# - Starts the xArm firmware for the specified robot type
# - Provides status checking and cleanup options
# 
# Usage:
#   ./docker_setup.sh start [5|6|7]    # Start simulator (default: 6)
#   ./docker_setup.sh stop             # Stop and remove container
#   ./docker_setup.sh status           # Check container status
#   ./docker_setup.sh restart [5|6|7]  # Restart with specified arm type
#   ./docker_setup.sh logs             # Show container logs
#   ./docker_setup.sh shell            # Access container shell
# 
# Requirements:
# - Docker installed and running
# - Internet connection for initial image download

set -e  # Exit on any error

# Configuration
CONTAINER_NAME="uf_software"
IMAGE_NAME="danielwang123321/uf-ubuntu-docker"
DEFAULT_ARM_TYPE="6"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check if Docker is available and running
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Check if container exists
container_exists() {
    docker ps -a --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Check if container is running
container_running() {
    docker ps --format "table {{.Names}}" | grep -q "^${CONTAINER_NAME}$"
}

# Pull the Docker image
pull_image() {
    log_info "Checking for xArm Docker image..."
    
    if docker images --format "table {{.Repository}}:{{.Tag}}" | grep -q "${IMAGE_NAME}"; then
        log_success "xArm Docker image already exists"
    else
        log_info "Pulling xArm Docker image (this may take a few minutes)..."
        docker pull "${IMAGE_NAME}"
        log_success "xArm Docker image pulled successfully"
    fi
}

# Start the container
start_container() {
    local arm_type=${1:-$DEFAULT_ARM_TYPE}
    
    log_info "Starting xArm Docker simulator..."
    
    # Check if container already exists
    if container_exists; then
        if container_running; then
            log_warning "Container is already running"
            return 0
        else
            log_info "Removing existing stopped container..."
            docker rm "${CONTAINER_NAME}" > /dev/null
        fi
    fi
    
    # Pull image if needed
    pull_image
    
    # Start container with all necessary ports
    log_info "Creating and starting container..."
    docker run -d --name "${CONTAINER_NAME}" \
        -p 18333:18333 \
        -p 502:502 \
        -p 503:503 \
        -p 504:504 \
        -p 30000:30000 \
        -p 30001:30001 \
        -p 30002:30002 \
        -p 30003:30003 \
        "${IMAGE_NAME}" > /dev/null
    
    log_success "Container started successfully"
    
    # Start xArm firmware
    start_firmware "${arm_type}"
}

# Start xArm firmware inside container
start_firmware() {
    local arm_type=${1:-$DEFAULT_ARM_TYPE}
    
    # Validate arm type
    if [[ ! "${arm_type}" =~ ^[567]$ ]]; then
        log_error "Invalid arm type: ${arm_type}. Must be 5, 6, or 7"
        exit 1
    fi
    
    log_info "Starting xArm ${arm_type} firmware..."
    
    # Wait for container to be ready
    sleep 2
    
    # Start firmware (runs in background inside container)
    docker exec "${CONTAINER_NAME}" /xarm_scripts/xarm_start.sh "${arm_type}" "${arm_type}" > /dev/null 2>&1 &
    
    log_success "xArm ${arm_type} firmware starting..."
    log_info "Waiting 10 seconds for firmware to initialize..."
    
    # Show progress
    for i in {1..10}; do
        echo -n "."
        sleep 1
    done
    echo ""
    
    log_success "xArm simulator ready!"
    log_info "Web UI available at: http://localhost:18333"
    log_info "SDK connection: 127.0.0.1"
}

# Stop and remove container
stop_container() {
    log_info "Stopping xArm Docker simulator..."
    
    if container_running; then
        docker stop "${CONTAINER_NAME}" > /dev/null
        log_success "Container stopped"
    else
        log_warning "Container is not running"
    fi
    
    if container_exists; then
        docker rm "${CONTAINER_NAME}" > /dev/null
        log_success "Container removed"
    fi
}

# Show container status
show_status() {
    log_info "xArm Docker Simulator Status:"
    echo ""
    
    if container_exists; then
        if container_running; then
            log_success "Container is running"
            echo ""
            echo "Container details:"
            docker ps --filter "name=${CONTAINER_NAME}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            echo ""
            log_info "Web UI: http://localhost:18333"
            log_info "SDK Connection: 127.0.0.1"
        else
            log_warning "Container exists but is not running"
            echo "Use './docker_setup.sh start' to start it"
        fi
    else
        log_warning "Container does not exist"
        echo "Use './docker_setup.sh start' to create and start it"
    fi
}

# Show container logs
show_logs() {
    if container_exists; then
        log_info "Container logs (last 50 lines):"
        echo ""
        docker logs --tail 50 "${CONTAINER_NAME}"
    else
        log_error "Container does not exist"
    fi
}

# Access container shell
access_shell() {
    if container_running; then
        log_info "Accessing container shell..."
        docker exec -it "${CONTAINER_NAME}" /bin/bash
    else
        log_error "Container is not running"
        echo "Use './docker_setup.sh start' to start it first"
    fi
}

# Test connection to simulator
test_connection() {
    log_info "Testing connection to simulator..."
    
    # Create a simple Python test script
    cat > /tmp/test_xarm_connection.py << 'EOF'
import sys
sys.path.append('/path/to/xarm/sdk')  # Adjust as needed

try:
    from xarm.wrapper import XArmAPI
    
    arm = XArmAPI('127.0.0.1', check_joint_limit=False)
    arm.connect()
    
    if arm.connected:
        print("✅ Successfully connected to simulator")
        print(f"Robot info: {arm.get_version()}")
        arm.disconnect()
        sys.exit(0)
    else:
        print("❌ Failed to connect to simulator")
        sys.exit(1)
        
except Exception as e:
    print(f"❌ Connection test failed: {e}")
    sys.exit(1)
EOF
    
    # Run the test (requires xarm-python-sdk)
    if python /tmp/test_xarm_connection.py 2>/dev/null; then
        log_success "Connection test passed"
    else
        log_warning "Connection test failed - make sure xArm SDK is installed and firmware is running"
    fi
    
    # Cleanup
    rm -f /tmp/test_xarm_connection.py
}

# Show usage information
show_usage() {
    echo "xArm Docker Simulator Setup Script"
    echo "=================================="
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start [5|6|7]     Start simulator with specified arm type (default: 6)"
    echo "  stop              Stop and remove container"
    echo "  restart [5|6|7]   Restart simulator with specified arm type"
    echo "  status            Show container status"
    echo "  logs              Show container logs"
    echo "  shell             Access container shell"
    echo "  test              Test connection to simulator"
    echo "  help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start          # Start xArm 6 simulator"
    echo "  $0 start 7        # Start xArm 7 simulator"
    echo "  $0 restart 5      # Restart with xArm 5"
    echo "  $0 status         # Check if running"
    echo "  $0 stop           # Stop simulator"
    echo ""
    echo "Ports exposed:"
    echo "  18333  - Web UI (http://localhost:18333)"
    echo "  502-504, 30000-30003 - xArm communication ports"
}

# Main command handling
main() {
    check_docker
    
    case "${1:-help}" in
        "start")
            start_container "${2}"
            ;;
        "stop")
            stop_container
            ;;
        "restart")
            stop_container
            sleep 2
            start_container "${2}"
            ;;
        "status")
            show_status
            ;;
        "logs")
            show_logs
            ;;
        "shell")
            access_shell
            ;;
        "test")
            test_connection
            ;;
        "help"|"--help"|"-h")
            show_usage
            ;;
        *)
            log_error "Unknown command: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@" 