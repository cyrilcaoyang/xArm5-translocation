#!/usr/bin/env python3
"""
FastAPI Server for xArm Translocation Control

This module provides a REST API wrapper around the XArmController class
to enable web-based control and monitoring of xArm robots.
"""

# TODO: planning to implement DI/DO for safety light and additional e-stop

import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, List, Optional, Any
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
import uvicorn

from .xarm_controller import XArmController, SafetyLevel
from .xarm_utils import load_config
from .xarm_controller import ComponentState

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global controller instance
controller: Optional[XArmController] = None

# WebSocket connections for real-time updates
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")

manager = ConnectionManager()

# Pydantic models for request/response
class ConnectionRequest(BaseModel):
    """Request model for establishing a connection to the controller."""
    profile_name: Optional[str] = Field(default=None, description="Name of the connection profile to use.")
    host: Optional[str] = Field(default=None, description="IP address of the robot. Overrides profile.")
    model: Optional[int] = Field(default=None, description="Robot model: 5, 6, 7. Overrides profile.")
    simulation_mode: bool = Field(default=False, description="Enable software simulation mode (no hardware required).")
    safety_level: str = Field(default="MEDIUM", description="Set the safety validation level: LOW, MEDIUM, HIGH.")

    def get_safety_level_enum(self) -> SafetyLevel:
        """Convert string safety level to enum"""
        level_map = {
            "LOW": SafetyLevel.LOW,
            "MEDIUM": SafetyLevel.MEDIUM, 
            "HIGH": SafetyLevel.HIGH
        }
        return level_map.get(self.safety_level.upper(), SafetyLevel.MEDIUM)

class PositionRequest(BaseModel):
    """Request model for Cartesian position movement."""
    x: float = Field(description="X coordinate in mm")
    y: float = Field(description="Y coordinate in mm")
    z: float = Field(description="Z coordinate in mm")
    roll: Optional[float] = Field(default=None, description="Roll angle in degrees")
    pitch: Optional[float] = Field(default=None, description="Pitch angle in degrees")
    yaw: Optional[float] = Field(default=None, description="Yaw angle in degrees")
    speed: Optional[float] = Field(default=None, description="Movement speed (validated by safety level)")
    check_collision: bool = Field(default=True, description="Perform collision checking before movement.")
    wait: bool = Field(default=True, description="Wait for movement to complete.")

class JointRequest(BaseModel):
    """Request model for joint angle movement."""
    angles: List[float] = Field(description="List of joint angles in degrees")
    speed: Optional[float] = Field(default=None, description="Movement speed (validated by safety level)")
    acceleration: Optional[float] = Field(default=None, description="Movement acceleration (validated by safety level)")
    check_collision: bool = Field(default=True, description="Perform collision checking before movement.")
    wait: bool = Field(default=True, description="Wait for movement to complete.")

class RelativeRequest(BaseModel):
    """Request model for relative Cartesian movement."""
    dx: float = Field(default=0, description="Delta X in mm")
    dy: float = Field(default=0, description="Delta Y in mm")
    dz: float = Field(default=0, description="Delta Z in mm")
    droll: float = Field(default=0, description="Delta roll in degrees")
    dpitch: float = Field(default=0, description="Delta pitch in degrees")
    dyaw: float = Field(default=0, description="Delta yaw in degrees")
    speed: Optional[float] = Field(default=None, description="Movement speed (validated by safety level)")
    check_collision: bool = Field(default=True, description="Perform collision checking before movement.")
    wait: bool = Field(default=True, description="Wait for movement to complete.")

class LocationRequest(BaseModel):
    """Request model for moving to a named location."""
    location_name: str = Field(description="Name of the location defined in location_config.yaml")
    speed: Optional[float] = Field(default=None, description="Movement speed (validated by safety level)")
    check_collision: bool = Field(default=True, description="Perform collision checking before movement.")
    wait: bool = Field(default=True, description="Wait for movement to complete.")

class TrackRequest(BaseModel):
    """Request model for linear track movement."""
    position: float = Field(description="Target position for the linear track in mm")
    speed: Optional[float] = Field(default=None, description="Movement speed for the track (validated by safety level)")
    wait: bool = Field(default=True, description="Wait for movement to complete.")

class TrackLocationRequest(BaseModel):
    """Request model for moving linear track to a named location."""
    location_name: str = Field(description="Name of the location from linear_track_config.yaml")
    speed: Optional[float] = Field(default=None, description="Movement speed for the track (validated by safety level)")
    wait: bool = Field(default=True, description="Wait for movement to complete.")

class GripperRequest(BaseModel):
    """Request model for gripper operations."""
    speed: Optional[float] = Field(default=None, description="Gripper speed (1-5000)")
    wait: bool = Field(default=True, description="Wait for operation to complete.")

class VelocityRequest(BaseModel):
    """Request model for Cartesian velocity control."""
    vx: float = Field(default=0, description="Velocity in X direction (mm/s)")
    vy: float = Field(default=0, description="Velocity in Y direction (mm/s)")
    vz: float = Field(default=0, description="Velocity in Z direction (mm/s)")
    vroll: float = Field(default=0, description="Angular velocity around X axis (deg/s)")
    vpitch: float = Field(default=0, description="Angular velocity around Y axis (deg/s)")
    vyaw: float = Field(default=0, description="Angular velocity around Z axis (deg/s)")

class ComponentRequest(BaseModel):
    """Request model for enabling/disabling a component."""
    component: str = Field(description="Component to manage ('gripper' or 'track')")

# Application lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting xArm API Server")
    yield
    # Shutdown
    global controller
    if controller:
        logger.info("Disconnecting from robot...")
        controller.disconnect()
    logger.info("xArm API Server shutdown complete")

# Create FastAPI app
app = FastAPI(
    title="xArm Translocation API",
    description="REST API for controlling xArm robots with gripper and linear track support",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static files directory
app.mount("/web", StaticFiles(directory="src/web"), name="web")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper functions
def get_controller() -> XArmController:
    """Get the global controller instance"""
    global controller
    if not controller:
        raise HTTPException(status_code=400, detail="Robot not connected. Please connect first.")
    return controller

def create_error_response(message: str, status_code: int = 500) -> JSONResponse:
    """Create standardized error response"""
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "timestamp": datetime.now().isoformat()}
    )

async def broadcast_status_update():
    """Broadcast status update to all connected WebSocket clients"""
    global controller
    if controller:
        try:
            # More detailed status
            is_connected = controller.is_alive and controller.arm.connected if hasattr(controller, 'arm') and controller.arm else False
            
            # Standardize connection details
            connection_details = None
            if is_connected:
                connection_details = {
                    "host": controller.host,
                    "port": controller.xarm_config.get('port', 18333),
                    "profile_name": getattr(controller, 'profile_name', 'unknown'),
                    "simulation_mode": controller.simulation_mode
                }
            
            system_status = controller.get_system_status()
            
            status_info = {
                "connection_status": "Connected" if is_connected else "Disconnected",
                "connection_details": connection_details,
                "system_status": system_status,
                "is_alive": controller.is_alive,
                "component_states": controller.get_component_states(),
                "current_position": controller.get_current_position(),
                "current_joints": controller.get_current_joints(),
                "track_position": controller.get_track_position() if controller.has_track() else None,
                "timestamp": datetime.now().isoformat()
            }
            status = {
                "type": "status_update",
                "data": status_info
            }
            await manager.broadcast(json.dumps(status))
        except Exception as e:
            logger.error(f"Error broadcasting status: {e}")

# API Routes

@app.get("/")
async def read_root():
    """Serve the main dashboard page."""
    return FileResponse('src/web/index.html')

@app.get("/api")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "xArm Translocation API",
        "version": "1.0.0",
        "status": "running",
        "connected": controller is not None and controller.is_alive
    }

@app.get("/api/configurations")
async def get_configurations():
    """Scan and return available connection profiles from the main config file."""
    config_path = os.path.join('src', 'settings', 'xarm_config.yaml')
    try:
        full_config = load_config(config_path)
        profiles = full_config.get('profiles', {})
        return sorted(list(profiles.keys()))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Main xarm_config.yaml not found.")
    except Exception as e:
        logger.error(f"Failed to read profiles from xarm_config.yaml: {e}")
        raise HTTPException(status_code=500, detail="Failed to read profiles.")


@app.post("/connect")
async def connect_robot(request: ConnectionRequest, background_tasks: BackgroundTasks):
    """
    Connect to the robot controller.

    This endpoint initializes the `XArmController`, allowing you to choose
    between hardware and simulation modes, and set the initial safety level.
    """
    global controller
    
    if controller and controller.is_alive:
        raise HTTPException(status_code=400, detail="A robot is already connected. Please disconnect first.")

    try:
        # Create and initialize the controller instance
        controller = XArmController(
            profile_name=request.profile_name,
            host=request.host,
            model=request.model,
            simulation_mode=request.simulation_mode,
            safety_level=request.get_safety_level_enum()
        )
        
        if controller.initialize():
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": f"Successfully connected in {'Simulation' if request.simulation_mode else 'Hardware'} mode.",
                "connection_details": {
                    "host": controller.host,
                    "port": controller.xarm_config.get('port', 18333),
                    "profile_name": request.profile_name or 'custom',
                    "simulation_mode": request.simulation_mode
                },
                "model": controller.model_name,
                "num_joints": controller.num_joints,
                "gripper_type": controller.gripper_type if hasattr(controller, 'gripper_type') else 'N/A',
                "has_track": controller.has_track(),
                "component_states": controller.get_component_states(),
                "safety_level": controller.safety_level.name
            }
        else:
            controller = None
            raise HTTPException(status_code=500, detail="Failed to initialize robot connection. Check logs for details.")
            
    except Exception as e:
        controller = None
        logger.error(f"Connection failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during connection: {e}")

@app.post("/disconnect")
async def disconnect_robot():
    """Disconnect from the robot and ensure the state is cleaned up."""
    global controller
    
    connection_info = None
    if controller:
        # Capture connection info before disconnecting
        connection_info = {
            "host": controller.host,
            "port": controller.xarm_config.get('port', 18333),
            "profile_name": getattr(controller, 'profile_name', 'unknown')
        }
    
    message = "Robot was not connected."
    if controller:
        try:
            controller.disconnect()
            message = f"Successfully disconnected from {connection_info['host']}:{connection_info['port']}"
        except Exception as e:
            logger.error(f"Disconnect failed: {e}", exc_info=True)
            # Still proceed to set controller to None
            message = f"Disconnected from {connection_info['host']}:{connection_info['port']} (with errors)"
        finally:
            controller = None
    
    # Broadcast a final disconnected status to all clients to sync the UI
    await manager.broadcast(json.dumps({
        "type": "status_update",
        "data": {
            "connection_status": "Disconnected",
            "connection_details": None,
            "system_status": {"connection": {"alive": False}},
            "is_alive": False,
            "component_states": {
                "arm": "disabled",
                "gripper": "disabled",
                "track": "disabled"
            },
            "current_position": None,
            "current_joints": None,
            "track_position": None
        }
    }))
    
    return {
        "message": message,
        "connection_details": connection_info
    }

@app.get("/status")
async def get_status():
    """Get the current status of the robot and all components."""
    global controller
    
    # Handle disconnected state gracefully
    if not controller:
        return {
            "connection_state": "disconnected",
            "connection_details": None,
            "arm_state": "disabled",
            "gripper_state": "disabled", 
            "track_state": "disabled",
            "is_alive": False,
            "current_position": None,
            "current_joints": None,
            "last_error": None,
        }
    
    # Include connection details if connected
    connection_details = None
    if controller.is_alive:
        connection_details = {
            "host": controller.host,
            "port": controller.xarm_config.get('port', 18333),
            "profile_name": getattr(controller, 'profile_name', 'unknown'),
            "simulation_mode": controller.simulation_mode
        }
    
    return {
        "connection_state": controller.states.get('connection').value if controller.states.get('connection') else "unknown",
        "connection_details": connection_details,
        "arm_state": controller.states.get('arm').value if controller.states.get('arm') else "unknown",
        "gripper_state": controller.states.get('gripper').value if controller.states.get('gripper') else "unknown",
        "track_state": controller.states.get('track').value if controller.states.get('track') else "unknown",
        "is_alive": controller.is_alive,
        "current_position": controller.get_current_position(),
        "current_joints": controller.get_current_joints(),
        "last_error": getattr(controller, 'last_error', None),
    }

@app.get("/status/performance")
async def get_performance_status():
    """Get detailed performance and maintenance status (hardware only)."""
    c = get_controller()
    if c.simulation_mode:
        raise HTTPException(status_code=400, detail="Performance monitoring is not available in simulation mode.")
    return {
        "performance_metrics": c.get_performance_metrics(),
        "maintenance_status": c.get_maintenance_status(),
    }

@app.get("/locations")
async def get_locations():
    """Get all named arm locations from the location config file."""
    try:
        location_config_path = os.path.join('src', 'settings', 'location_config.yaml')
        location_config = load_config(location_config_path)
        locations = list(location_config.get('locations', {}).keys())
        return {"locations": locations}
    except FileNotFoundError:
        logger.warning("location_config.yaml not found, returning empty list for locations.")
        return {"locations": []}
    except Exception as e:
        logger.error(f"Get arm locations failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get arm locations failed: {str(e)}")

# Movement endpoints
@app.post("/move/position")
async def move_to_position(request: PositionRequest, background_tasks: BackgroundTasks):
    """Move the robot to a specific Cartesian position."""
    c = get_controller()

    async def move_task():
        success = c.move_to_position(
            x=request.x, y=request.y, z=request.z,
            roll=request.roll, pitch=request.pitch, yaw=request.yaw,
            speed=request.speed,
            check_collision=request.check_collision,
            wait=request.wait
        )
        if not success:
            logger.error("Failed to move to position.")
        await broadcast_status_update()

    background_tasks.add_task(move_task)
    return {"message": "Move to position command accepted."}

@app.post("/move/joints")
async def move_joints(request: JointRequest, background_tasks: BackgroundTasks):
    """Move the robot to a specific joint configuration."""
    c = get_controller()

    async def move_task():
        success = c.move_joints(
            angles=request.angles,
            speed=request.speed,
            acceleration=request.acceleration,
            check_collision=request.check_collision,
            wait=request.wait
        )
        if not success:
            logger.error("Failed to move joints.")
        await broadcast_status_update()
    
    background_tasks.add_task(move_task)
    return {"message": "Move joints command accepted."}

@app.post("/move/relative")
async def move_relative(request: RelativeRequest, background_tasks: BackgroundTasks):
    """Move the robot relative to its current position."""
    c = get_controller()

    async def move_task():
        success = c.move_relative(
            dx=request.dx, dy=request.dy, dz=request.dz,
            droll=request.droll, dpitch=request.dpitch, dyaw=request.dyaw,
            speed=request.speed,
            check_collision=request.check_collision,
            wait=request.wait
        )
        if not success:
            logger.error("Failed to move relative.")
        await broadcast_status_update()

    background_tasks.add_task(move_task)
    return {"message": "Move relative command accepted."}

@app.post("/move/location")
async def move_to_location(request: LocationRequest, background_tasks: BackgroundTasks):
    """Move the robot to a pre-defined named location."""
    c = get_controller()

    async def move_task():
        success = c.move_to_named_location(
            location_name=request.location_name,
            speed=request.speed,
            check_collision=request.check_collision,
            wait=request.wait
        )
        if not success:
            logger.error(f"Failed to move to named location: {request.location_name}")
        await broadcast_status_update()
    
    background_tasks.add_task(move_task)
    return {"message": f"Move to location '{request.location_name}' command accepted."}

@app.post("/move/home")
async def move_home(background_tasks: BackgroundTasks):
    """Move robot to home position"""
    ctrl = get_controller()
    
    try:
        result = ctrl.go_home()
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Successfully moved to home position",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Home movement failed")
            
    except Exception as e:
        logger.error(f"Home movement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Home movement failed: {str(e)}")

@app.post("/move/stop")
async def stop_movement(background_tasks: BackgroundTasks):
    """Stop all robot motion immediately."""
    c = get_controller()

    async def stop_task():
        c.stop_motion()
        logger.info("Stop command issued.")
        await broadcast_status_update()

    background_tasks.add_task(stop_task)
    return {"message": "Stop command accepted."}

@app.post("/clear/errors")
async def clear_errors(background_tasks: BackgroundTasks):
    """Clear all robot errors and warnings"""
    ctrl = get_controller()
    
    try:
        result = ctrl.clear_errors()
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "All errors and warnings cleared successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to clear all errors")
            
    except Exception as e:
        logger.error(f"Clear errors failed: {e}")
        raise HTTPException(status_code=500, detail=f"Clear errors failed: {str(e)}")

@app.post("/component/enable")
async def enable_component(request: ComponentRequest):
    """Enable a specific component (gripper or track)."""
    c = get_controller()
    component = request.component.lower()
    success = False
    if component == 'gripper':
        success = c.enable_gripper_component()
    elif component == 'track':
        success = c.enable_track_component()
    else:
        raise HTTPException(status_code=400, detail="Invalid component specified. Use 'gripper' or 'track'.")
    
    await broadcast_status_update()
    if success:
        return {"message": f"Component '{component}' enabled successfully."}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to enable component '{component}'.")

@app.post("/component/disable")
async def disable_component(request: ComponentRequest):
    """Disable a specific component (gripper or track)."""
    c = get_controller()
    component = request.component.lower()
    success = False
    if component == 'gripper':
        success = c.disable_gripper_component()
    elif component == 'track':
        success = c.disable_track_component()
    else:
        raise HTTPException(status_code=400, detail="Invalid component specified. Use 'gripper' or 'track'.")

    await broadcast_status_update()
    if success:
        return {"message": f"Component '{component}' disabled successfully."}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to disable component '{component}'.")

@app.post("/velocity/cartesian")
async def set_cartesian_velocity(request: VelocityRequest):
    """Set the Cartesian velocity of the robot arm."""
    c = get_controller()
    velocities = [request.vx, request.vy, request.vz, request.vroll, request.vpitch, request.vyaw]
    
    if not c.set_cartesian_velocity(velocities):
        raise HTTPException(status_code=500, detail="Failed to set Cartesian velocity.")
    
    return {"message": "Cartesian velocity set successfully."}

# Gripper endpoints
@app.post("/gripper/open")
async def open_gripper(request: GripperRequest, background_tasks: BackgroundTasks):
    """Open the attached gripper."""
    c = get_controller()

    async def gripper_task():
        success = c.open_gripper(speed=request.speed, wait=request.wait)
        if not success:
            logger.error("Failed to open gripper.")
        await broadcast_status_update()

    background_tasks.add_task(gripper_task)
    return {"message": "Open gripper command accepted."}

@app.post("/gripper/close")
async def close_gripper(request: GripperRequest, background_tasks: BackgroundTasks):
    """Close the attached gripper."""
    c = get_controller()

    async def gripper_task():
        success = c.close_gripper(speed=request.speed, wait=request.wait)
        if not success:
            logger.error("Failed to close gripper.")
        await broadcast_status_update()
    
    background_tasks.add_task(gripper_task)
    return {"message": "Close gripper command accepted."}

# Linear track endpoints
@app.post("/track/move")
async def move_track(request: TrackRequest, background_tasks: BackgroundTasks):
    """Move the linear track to a specific position."""
    c = get_controller()

    async def track_task():
        success = c.move_track_to_position(position=request.position, speed=request.speed, wait=request.wait)
        if not success:
            logger.error("Failed to move linear track.")
        await broadcast_status_update()

    background_tasks.add_task(track_task)
    return {"message": "Move track command accepted."}

@app.post("/track/move/location")
async def move_track_to_location(request: TrackLocationRequest, background_tasks: BackgroundTasks):
    """Move the linear track to a pre-configured named location."""
    c = get_controller()

    async def track_task():
        success = c.move_track_to_named_location(
            location_name=request.location_name,
            speed=request.speed,
            wait=request.wait
        )
        if not success:
            logger.error(f"Failed to move track to named location: {request.location_name}")
        await broadcast_status_update()

    background_tasks.add_task(track_task)
    return {"message": f"Move track to location '{request.location_name}' command accepted."}

@app.get("/track/position")
async def get_track_position():
    """Get current linear track position"""
    c = get_controller()
    
    if not c.has_track():
        raise HTTPException(status_code=400, detail="Linear track is not enabled.")
    return {"position": c.get_track_position()}

@app.get("/track/locations")
async def get_track_locations():
    """Get a list of all available named locations for the linear track from its config file."""
    try:
        track_config_path = os.path.join('src', 'settings', 'linear_track_config.yaml')
        track_config = load_config(track_config_path)
        locations = list(track_config.get('locations', {}).keys())
        return {"locations": locations}
    except FileNotFoundError:
        logger.warning("linear_track_config.yaml not found, returning empty list for track locations.")
        return {"locations": []}
    except Exception as e:
        logger.error(f"Get track locations failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get track locations failed: {str(e)}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates"""
    await manager.connect(websocket)
    try:
        # Send initial status on connect
        await broadcast_status_update()
        while True:
            # Keep connection alive, listen for messages if needed
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Development server
if __name__ == "__main__":
    # Get host and port from environment variables or use defaults
    host = os.environ.get("XARM_API_HOST", "0.0.0.0")
    port = int(os.environ.get("XARM_API_PORT", 6001))
    
    logger.info(f"Starting server on {host}:{port}")
    
    # Example of how to connect automatically on startup (optional)
    # This can be useful for development or dedicated server setups
    # Note: In a real production scenario, you might want to handle
    # connection via API calls for better control.
    
    # async def startup_connect():
    #     global controller
    #     logger.info("Attempting to auto-connect on startup...")
    #     try:
    #         controller = XArmController(auto_enable=True)
    #         if not controller.initialize():
    #             logger.error("Auto-connect failed during initialization.")
    #             controller = None
    #         else:
    #             logger.info("Auto-connect successful.")
    #     except Exception as e:
    #         logger.error(f"Auto-connect failed with exception: {e}")
    #         controller = None

    # app.add_event_handler("startup", startup_connect)
    
    uvicorn.run(app, host=host, port=port) 