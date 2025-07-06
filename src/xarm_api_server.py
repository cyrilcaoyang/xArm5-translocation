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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from xarm_controller import XArmController

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
    config_path: str = Field(default='users/settings/', description="Path to configuration files")
    gripper_type: str = Field(default='bio', description="Type of gripper: bio, standard, robotiq, or none")
    enable_track: bool = Field(default=True, description="Enable linear track functionality")
    auto_enable: bool = Field(default=True, description="Auto-enable components during initialization")
    model: Optional[int] = Field(default=None, description="Robot model: 5, 6, 7, or 850")

class PositionRequest(BaseModel):
    x: float = Field(description="X coordinate")
    y: float = Field(description="Y coordinate") 
    z: float = Field(description="Z coordinate")
    roll: Optional[float] = Field(default=None, description="Roll angle")
    pitch: Optional[float] = Field(default=None, description="Pitch angle")
    yaw: Optional[float] = Field(default=None, description="Yaw angle")
    speed: Optional[float] = Field(default=None, description="Movement speed")
    wait: bool = Field(default=True, description="Wait for movement completion")

class JointRequest(BaseModel):
    angles: List[float] = Field(description="Joint angles in degrees")
    speed: Optional[float] = Field(default=None, description="Movement speed")
    acceleration: Optional[float] = Field(default=None, description="Movement acceleration")
    wait: bool = Field(default=True, description="Wait for movement completion")

class RelativeRequest(BaseModel):
    dx: float = Field(default=0, description="Delta X")
    dy: float = Field(default=0, description="Delta Y")
    dz: float = Field(default=0, description="Delta Z")
    droll: float = Field(default=0, description="Delta roll")
    dpitch: float = Field(default=0, description="Delta pitch")
    dyaw: float = Field(default=0, description="Delta yaw")
    speed: Optional[float] = Field(default=None, description="Movement speed")

class LocationRequest(BaseModel):
    location_name: str = Field(description="Named location from config")
    speed: Optional[float] = Field(default=None, description="Movement speed")

class TrackRequest(BaseModel):
    position: float = Field(description="Linear track position")
    speed: Optional[float] = Field(default=None, description="Movement speed")
    wait: bool = Field(default=True, description="Wait for movement completion")

class GripperRequest(BaseModel):
    speed: Optional[float] = Field(default=None, description="Gripper speed")
    wait: bool = Field(default=True, description="Wait for operation completion")

class VelocityRequest(BaseModel):
    vx: float = Field(default=0, description="Velocity in X direction")
    vy: float = Field(default=0, description="Velocity in Y direction")
    vz: float = Field(default=0, description="Velocity in Z direction")
    vroll: float = Field(default=0, description="Angular velocity around X axis")
    vpitch: float = Field(default=0, description="Angular velocity around Y axis")
    vyaw: float = Field(default=0, description="Angular velocity around Z axis")

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
            status = {
                "type": "status_update",
                "data": {
                    "system_status": controller.get_system_status(),
                    "component_states": controller.get_component_states(),
                    "current_position": controller.get_current_position(),
                    "current_joints": controller.get_current_joints(),
                    "track_position": controller.get_track_position() if controller.has_track() else None,
                    "timestamp": datetime.now().isoformat()
                }
            }
            await manager.broadcast(json.dumps(status))
        except Exception as e:
            logger.error(f"Error broadcasting status: {e}")

# API Routes

@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "xArm Translocation API",
        "version": "1.0.0",
        "status": "running",
        "connected": controller is not None and controller.is_alive
    }

@app.post("/connect")
async def connect_robot(request: ConnectionRequest):
    """Connect to the robot"""
    global controller
    
    try:
        # Create controller instance
        controller = XArmController(
            config_path=request.config_path,
            gripper_type=request.gripper_type,
            enable_track=request.enable_track,
            auto_enable=request.auto_enable,
            model=request.model
        )
        
        # Initialize connection
        if controller.initialize():
            await broadcast_status_update()
            return {
                "message": "Successfully connected to robot",
                "model": controller.model_name,
                "num_joints": controller.num_joints,
                "gripper_type": controller.gripper_type,
                "has_track": controller.has_track(),
                "component_states": controller.get_component_states()
            }
        else:
            controller = None
            raise HTTPException(status_code=500, detail="Failed to initialize robot connection")
            
    except Exception as e:
        controller = None
        logger.error(f"Connection failed: {e}")
        raise HTTPException(status_code=500, detail=f"Connection failed: {str(e)}")

@app.post("/disconnect")
async def disconnect_robot():
    """Disconnect from the robot"""
    global controller
    
    if controller:
        try:
            controller.disconnect()
            controller = None
            await broadcast_status_update()
            return {"message": "Successfully disconnected from robot"}
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")
            raise HTTPException(status_code=500, detail=f"Disconnect failed: {str(e)}")
    else:
        return {"message": "Robot not connected"}

@app.get("/status")
async def get_status():
    """Get current robot status"""
    ctrl = get_controller()
    
    try:
        return {
            "system_status": ctrl.get_system_status(),
            "component_states": ctrl.get_component_states(),
            "current_position": ctrl.get_current_position(),
            "current_joints": ctrl.get_current_joints(),
            "track_position": ctrl.get_track_position() if ctrl.has_track() else None,
            "model": ctrl.model_name,
            "num_joints": ctrl.num_joints,
            "gripper_type": ctrl.gripper_type,
            "has_track": ctrl.has_track(),
            "has_gripper": ctrl.has_gripper(),
            "error_history": ctrl.get_error_history(5),
            "is_alive": ctrl.is_alive,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting status: {str(e)}")

@app.post("/move/position")
async def move_to_position(request: PositionRequest, background_tasks: BackgroundTasks):
    """Move robot to specified Cartesian position"""
    ctrl = get_controller()
    
    try:
        result = ctrl.move_to_position(
            x=request.x,
            y=request.y,
            z=request.z,
            roll=request.roll,
            pitch=request.pitch,
            yaw=request.yaw,
            speed=request.speed,
            wait=request.wait
        )
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Movement completed successfully",
                "position": {"x": request.x, "y": request.y, "z": request.z},
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Movement failed")
            
    except Exception as e:
        logger.error(f"Movement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Movement failed: {str(e)}")

@app.post("/move/joints")
async def move_joints(request: JointRequest, background_tasks: BackgroundTasks):
    """Move robot joints to specified angles"""
    ctrl = get_controller()
    
    try:
        # Validate joint count
        if len(request.angles) != ctrl.num_joints:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid joint count. Expected {ctrl.num_joints}, got {len(request.angles)}"
            )
        
        result = ctrl.move_joints(
            angles=request.angles,
            speed=request.speed,
            acceleration=request.acceleration,
            wait=request.wait
        )
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Joint movement completed successfully",
                "angles": request.angles,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Joint movement failed")
            
    except Exception as e:
        logger.error(f"Joint movement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Joint movement failed: {str(e)}")

@app.post("/move/relative")
async def move_relative(request: RelativeRequest, background_tasks: BackgroundTasks):
    """Move robot relative to current position"""
    ctrl = get_controller()
    
    try:
        result = ctrl.move_relative(
            dx=request.dx,
            dy=request.dy,
            dz=request.dz,
            droll=request.droll,
            dpitch=request.dpitch,
            dyaw=request.dyaw,
            speed=request.speed
        )
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Relative movement completed successfully",
                "delta": {
                    "dx": request.dx, "dy": request.dy, "dz": request.dz,
                    "droll": request.droll, "dpitch": request.dpitch, "dyaw": request.dyaw
                },
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Relative movement failed")
            
    except Exception as e:
        logger.error(f"Relative movement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Relative movement failed: {str(e)}")

@app.post("/move/location")
async def move_to_location(request: LocationRequest, background_tasks: BackgroundTasks):
    """Move robot to named location"""
    ctrl = get_controller()
    
    try:
        result = ctrl.move_to_named_location(
            location_name=request.location_name,
            speed=request.speed
        )
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": f"Successfully moved to location '{request.location_name}'",
                "location": request.location_name,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Location movement failed")
            
    except Exception as e:
        logger.error(f"Location movement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Location movement failed: {str(e)}")

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
    """Stop all robot movement"""
    ctrl = get_controller()
    
    try:
        result = ctrl.stop_motion()
        background_tasks.add_task(broadcast_status_update)
        return {
            "message": "Movement stopped successfully",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Stop movement failed: {e}")
        raise HTTPException(status_code=500, detail=f"Stop movement failed: {str(e)}")

@app.post("/velocity/cartesian")
async def set_cartesian_velocity(request: VelocityRequest):
    """Set Cartesian velocity for continuous movement"""
    ctrl = get_controller()
    
    try:
        result = ctrl.set_cartesian_velocity(
            vx=request.vx,
            vy=request.vy,
            vz=request.vz,
            vroll=request.vroll,
            vpitch=request.vpitch,
            vyaw=request.vyaw
        )
        
        return {
            "message": "Cartesian velocity set successfully",
            "velocity": {
                "vx": request.vx, "vy": request.vy, "vz": request.vz,
                "vroll": request.vroll, "vpitch": request.vpitch, "vyaw": request.vyaw
            },
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Set velocity failed: {e}")
        raise HTTPException(status_code=500, detail=f"Set velocity failed: {str(e)}")

# Gripper endpoints
@app.post("/gripper/open")
async def open_gripper(request: GripperRequest, background_tasks: BackgroundTasks):
    """Open the gripper"""
    ctrl = get_controller()
    
    if not ctrl.has_gripper():
        raise HTTPException(status_code=400, detail="No gripper configured")
    
    try:
        result = ctrl.open_gripper(speed=request.speed, wait=request.wait)
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Gripper opened successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to open gripper")
            
    except Exception as e:
        logger.error(f"Open gripper failed: {e}")
        raise HTTPException(status_code=500, detail=f"Open gripper failed: {str(e)}")

@app.post("/gripper/close")
async def close_gripper(request: GripperRequest, background_tasks: BackgroundTasks):
    """Close the gripper"""
    ctrl = get_controller()
    
    if not ctrl.has_gripper():
        raise HTTPException(status_code=400, detail="No gripper configured")
    
    try:
        result = ctrl.close_gripper(speed=request.speed, wait=request.wait)
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Gripper closed successfully",
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to close gripper")
            
    except Exception as e:
        logger.error(f"Close gripper failed: {e}")
        raise HTTPException(status_code=500, detail=f"Close gripper failed: {str(e)}")

# Linear track endpoints
@app.post("/track/move")
async def move_track(request: TrackRequest, background_tasks: BackgroundTasks):
    """Move linear track to position"""
    ctrl = get_controller()
    
    if not ctrl.has_track():
        raise HTTPException(status_code=400, detail="No linear track configured")
    
    try:
        result = ctrl.move_track_to_position(
            position=request.position,
            speed=request.speed,
            wait=request.wait
        )
        
        if result:
            background_tasks.add_task(broadcast_status_update)
            return {
                "message": "Track moved successfully",
                "position": request.position,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to move track")
            
    except Exception as e:
        logger.error(f"Move track failed: {e}")
        raise HTTPException(status_code=500, detail=f"Move track failed: {str(e)}")

@app.get("/track/position")
async def get_track_position():
    """Get current linear track position"""
    ctrl = get_controller()
    
    if not ctrl.has_track():
        raise HTTPException(status_code=400, detail="No linear track configured")
    
    try:
        position = ctrl.get_track_position()
        return {
            "position": position,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Get track position failed: {e}")
        raise HTTPException(status_code=500, detail=f"Get track position failed: {str(e)}")

# WebSocket endpoint for real-time updates
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time status updates"""
    await manager.connect(websocket)
    try:
        # Send initial status
        await broadcast_status_update()
        
        while True:
            # Keep connection alive and listen for client messages
            data = await websocket.receive_text()
            
            # Handle client requests (e.g., status updates)
            if data == "status":
                await broadcast_status_update()
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

# Development server
if __name__ == "__main__":
    uvicorn.run(
        "xarm_api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 