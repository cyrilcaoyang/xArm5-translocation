"""
Pytest tests for the xArm API server (FastAPI application).
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path to allow imports from core module
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We must import the app after the path is updated
from src.core.xarm_api_server import app, controller as api_controller


@pytest.fixture
def mock_controller():
    """Provides a mocked XArmController instance."""
    mc = MagicMock()
    mc.initialize.return_value = True
    mc.disconnect.return_value = True
    mc.move_to_position.return_value = True
    mc.get_system_status.return_value = {
        'connection': {'connected': True},
        'arm': {'robot_state': 0}
    }
    mc.is_connected.return_value = True
    mc.is_alive = True
    mc.host = '127.0.0.1'
    mc.xarm_config = {'port': 18333}
    return mc


@pytest.fixture
def client(monkeypatch, mock_controller):
    """
    Pytest fixture to create a FastAPI TestClient.
    This fixture also patches the XArmController to prevent real hardware interaction.
    """
    monkeypatch.setattr('src.core.xarm_api_server.controller', mock_controller)
    
    with TestClient(app) as test_client:
        yield test_client


def test_read_root(client):
    """Test the root endpoint to ensure it returns the main page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Robotic Control" in response.text


def test_get_status_not_connected(client, monkeypatch):
    """Test the status endpoint when the controller is not connected."""
    mock_controller = MagicMock()
    mock_controller.is_alive = False
    mock_controller.states = {'connection': 'disabled', 'arm': 'disabled', 'gripper': 'disabled', 'track': 'disabled'}
    mock_controller.get_current_position.return_value = []
    mock_controller.get_current_joints.return_value = []
    mock_controller.last_error = 0
    monkeypatch.setattr('src.core.xarm_api_server.controller', mock_controller)
    
    response = client.get("/status")
    assert response.status_code == 200
    data = response.json()
    assert data['connection_state'] == 'disabled'


def test_connect_success(client, monkeypatch):
    """Test the connect endpoint with successful connection."""
    monkeypatch.setattr('src.core.xarm_api_server.controller', None)

    with patch('src.core.xarm_api_server.XArmController') as MockController:
        mock_instance = MockController.return_value
        mock_instance.initialize.return_value = True
        mock_instance.is_alive = True
        
        response = client.post("/connect", json={"profile_name": "docker_local", "simulation_mode": False})
        assert response.status_code == 200
        assert "Successfully connected" in response.json()['message']

def test_connect_failure(client, monkeypatch):
    """Test the connect endpoint with a failed connection."""
    monkeypatch.setattr('src.core.xarm_api_server.controller', None)

    with patch('src.core.xarm_api_server.XArmController') as MockController:
        mock_instance = MockController.return_value
        mock_instance.initialize.return_value = False
        
        response = client.post("/connect", json={"profile_name": "docker_local", "simulation_mode": False})
        assert response.status_code == 500
        assert "Failed to initialize" in response.json()['detail']

def test_disconnect(client, mock_controller):
    """Test the disconnect endpoint."""
    response = client.post("/disconnect")
    assert response.status_code == 200
    assert "Successfully disconnected" in response.json()['message']
    assert mock_controller.disconnect.called

def test_move_to_position(client, mock_controller):
    """Test the move_to_position endpoint."""
    response = client.post("/move/position", json={"x": 300, "y": 0, "z": 300})
    assert response.status_code == 200
    assert response.json() == {"message": "Move to position command accepted."}
    mock_controller.move_to_position.assert_called_once()

def test_get_configs(client):
    """Test the endpoint for listing available configuration files."""
    response = client.get("/api/configurations")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) 