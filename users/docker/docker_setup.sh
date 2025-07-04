#!/bin/bash
# Simple xArm Docker Simulator Setup
# ==================================
# 
# Usage:
#   ./docker_setup.sh start [5|6|7]    # Start simulator (default: 6)
#   ./docker_setup.sh stop             # Stop simulator
#   ./docker_setup.sh status           # Check status
#   ./docker_setup.sh help             # Show help

set -e

# Configuration
CONTAINER_NAME="uf_software"
IMAGE_NAME="danielwang123321/uf-ubuntu-docker"
DEFAULT_ARM_TYPE="6"

# Check Docker
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker not found. Please install Docker."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "Error: Docker not running. Please start Docker."
        exit 1
    fi
}

# Check if container exists
container_exists() {
    docker ps -a --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$" 2>/dev/null
}

# Check if container is running
container_running() {
    docker ps --format "{{.Names}}" | grep -q "^${CONTAINER_NAME}$" 2>/dev/null
}

# Start simulator
start_simulator() {
    local arm_type=${1:-$DEFAULT_ARM_TYPE}
    
    # Validate arm type
    if [[ ! "${arm_type}" =~ ^[567]$ ]]; then
        echo "Error: Invalid arm type '${arm_type}'. Use 5, 6, or 7."
        exit 1
    fi
    
    echo "Starting xArm${arm_type} Docker simulator..."
    
    # Remove existing container if needed
    if container_exists; then
        if container_running; then
            echo "Simulator already running."
            return 0
        else
            echo "Removing old container..."
            docker rm "${CONTAINER_NAME}" > /dev/null 2>&1
        fi
    fi
    
    # Pull image if needed
    if ! docker images --format "{{.Repository}}:{{.Tag}}" | grep -q "${IMAGE_NAME}" 2>/dev/null; then
        echo "Downloading Docker image..."
        docker pull "${IMAGE_NAME}"
    fi
    
    # Start container
    echo "Creating container..."
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
    
    # Start firmware
    echo "Starting xArm${arm_type} firmware..."
    sleep 3
    docker exec "${CONTAINER_NAME}" /xarm_scripts/xarm_start.sh "${arm_type}" "${arm_type}" > /dev/null 2>&1 &
    
    echo "Waiting for startup..."
    sleep 8
    
    echo "✓ Simulator ready!"
    echo "Web UI: http://localhost:18333"
    echo "SDK IP: 127.0.0.1"
}

# Stop simulator
stop_simulator() {
    echo "Stopping simulator..."
    
    if container_running; then
        docker stop "${CONTAINER_NAME}" > /dev/null 2>&1
        echo "✓ Container stopped"
    fi
    
    if container_exists; then
        docker rm "${CONTAINER_NAME}" > /dev/null 2>&1
        echo "✓ Container removed"
    else
        echo "No simulator running"
    fi
}

# Show status
show_status() {
    echo "xArm Docker Simulator Status:"
    
    if container_running; then
        echo "✓ Running"
        echo "Web UI: http://localhost:18333"
        echo "SDK IP: 127.0.0.1"
    elif container_exists; then
        echo "⚠ Stopped"
    else
        echo "✗ Not created"
    fi
}

# Show help
show_help() {
    echo "xArm Docker Simulator Setup"
    echo "=========================="
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start [5|6|7]  Start simulator (default: xArm6)"
    echo "  stop           Stop simulator"
    echo "  status         Show status"
    echo "  help           Show this help"
    echo ""
    echo "Examples:"
    echo "  $0 start       # Start xArm6"
    echo "  $0 start 5     # Start xArm5"
    echo "  $0 stop        # Stop simulator"
}

# Main command handler
main() {
    check_docker
    
    case "${1:-help}" in
        "start")
            start_simulator "${2}"
            ;;
        "stop")
            stop_simulator
            ;;
        "status")
            show_status
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            echo "Error: Unknown command '$1'"
            echo "Use '$0 help' for usage information."
            exit 1
            ;;
    esac
}

main "$@" 