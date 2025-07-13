document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = 'http://127.0.0.1:6001';
    const WS_BASE_URL = 'ws://127.0.0.1:6001';
    const responseEl = document.getElementById('api-response');

    // --- Helper Functions ---
    async function sendRequest(endpoint, method = 'POST', body = null) {
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (body) {
                options.body = JSON.stringify(body);
            }
            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            const result = await response.json();
            responseEl.textContent = JSON.stringify(result, null, 2);
        } catch (error) {
            responseEl.textContent = `Error: ${error.message}`;
        }
    }
    
    function getInputValue(id, isNumber = true) {
        const value = document.getElementById(id).value;
        return isNumber ? parseFloat(value) : value;
    }

    // --- WebSocket for Real-time Status ---
    function connectWebSocket() {
        const ws = new WebSocket(`${WS_BASE_URL}/ws`);

        ws.onopen = () => {
            console.log('WebSocket connected');
            // Status will be updated by the first message
        };

        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'status_update') {
                updateStatusUI(message.data);
            }
        };

        ws.onclose = () => {
            console.log('WebSocket disconnected');
            document.getElementById('robot-status').textContent = 'Disconnected from Arm';
            document.getElementById('robot-ip').textContent = 'N/A';
            // Optional: try to reconnect
            setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            document.getElementById('robot-status').textContent = 'Error';
        };
    }

    function updateStatusUI(data) {
        // Update connection status and IP
        document.getElementById('robot-status').textContent = data.connection_status || 'N/A';
        document.getElementById('robot-ip').textContent = data.ip_address || 'N/A';

        if (data.current_position) {
            const pos = data.current_position;
            document.getElementById('robot-position').textContent = 
                `[${pos.x.toFixed(2)}, ${pos.y.toFixed(2)}, ${pos.z.toFixed(2)}, ${pos.roll.toFixed(2)}, ${pos.pitch.toFixed(2)}, ${pos.yaw.toFixed(2)}]`;
        }
        if (data.current_joints) {
            const joints = data.current_joints;
            document.getElementById('robot-joints').textContent = 
                `[${joints.map(j => j.toFixed(2)).join(', ')}]`;
        }
        if (data.track_position !== null && data.track_position !== undefined) {
             document.getElementById('track-position').textContent = data.track_position.toFixed(2);
        }
    }

    async function populateLocations() {
        try {
            const response = await fetch(`${API_BASE_URL}/locations`);
            const data = await response.json();
            const select = document.getElementById('location-select');
            select.innerHTML = '<option value="">-- Select Location --</option>'; // Clear existing
            if (data.locations) {
                data.locations.forEach(location => {
                    const option = document.createElement('option');
                    option.value = location;
                    option.textContent = location;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Failed to load locations:', error);
        }
    }


    // --- Event Listeners ---
    document.getElementById('connect-btn').addEventListener('click', () => {
        const connectionData = {
            config_path: 'src/settings/',
            gripper_type: 'bio',
            enable_track: true,
            auto_enable: true,
            model: 5
        };
        sendRequest('/connect', 'POST', connectionData).then(populateLocations);
    });
    document.getElementById('disconnect-btn').addEventListener('click', () => {
        sendRequest('/disconnect');
        document.getElementById('robot-status').textContent = 'Disconnected from Arm';
        document.getElementById('robot-ip').textContent = 'N/A';
    });
    document.getElementById('home-btn').addEventListener('click', () => sendRequest('/move/home'));
    document.getElementById('stop-btn').addEventListener('click', () => sendRequest('/move/stop'));
    document.getElementById('clear-errors-btn').addEventListener('click', () => sendRequest('/clear/errors'));
    document.getElementById('gripper-open-btn').addEventListener('click', () => {
        const body = {};
        const speed = getInputValue('gripper-speed');
        if (speed) body.speed = speed;
        sendRequest('/gripper/open', 'POST', body);
    });
    
    document.getElementById('gripper-close-btn').addEventListener('click', () => {
        const body = {};
        const speed = getInputValue('gripper-speed');
        if (speed) body.speed = speed;
        sendRequest('/gripper/close', 'POST', body);
    });

    document.getElementById('move-pos-btn').addEventListener('click', () => {
        const body = {
            x: getInputValue('pos-x'),
            y: getInputValue('pos-y'),
            z: getInputValue('pos-z'),
            roll: getInputValue('pos-roll'),
            pitch: getInputValue('pos-pitch'),
            yaw: getInputValue('pos-yaw'),
        };
        const speed = getInputValue('pos-speed');
        if (speed) body.speed = speed;
        sendRequest('/move/position', 'POST', body);
    });

    document.getElementById('move-joints-btn').addEventListener('click', () => {
        const angles = [
            getInputValue('j1'), getInputValue('j2'), getInputValue('j3'),
            getInputValue('j4'), getInputValue('j5'), getInputValue('j6')
        ];
        const body = { angles };
        const speed = getInputValue('joints-speed');
        if (speed) body.speed = speed;
        sendRequest('/move/joints', 'POST', body);
    });

    document.getElementById('move-loc-btn').addEventListener('click', () => {
        const location_name = document.getElementById('location-select').value;
        if (location_name) {
            const body = { location_name };
            const speed = getInputValue('location-speed');
            if (speed) body.speed = speed;
            sendRequest('/move/location', 'POST', body);
        } else {
            document.getElementById('api-response').textContent = 'Please select a location.';
        }
    });

    document.getElementById('track-move-btn').addEventListener('click', () => {
        const position = getInputValue('track-pos');
        const body = { position };
        const speed = getInputValue('track-speed');
        if (speed) body.speed = speed;
        sendRequest('/track/move', 'POST', body);
    });

    document.getElementById('track-get-btn').addEventListener('click', async () => {
        await sendRequest('/track/position', 'GET');
    });
    
    // Initial connection
    connectWebSocket();
    populateLocations();
}); 