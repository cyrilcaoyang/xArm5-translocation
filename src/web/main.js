document.addEventListener('DOMContentLoaded', () => {
    const API_BASE_URL = `${window.location.protocol}//${window.location.host}`;
    const WS_URL = `ws://${window.location.host}/ws`;

    const connectBtn = document.getElementById('connect-btn');
    const disconnectBtn = document.getElementById('disconnect-btn');
    const configSelect = document.getElementById('config-select');
    const safetyLevelSelect = document.getElementById('safety-level-select');
    const simulationModeCheckbox = document.getElementById('simulation-mode');

    const movePosBtn = document.getElementById('move-pos-btn');
    const moveJointsBtn = document.getElementById('move-joints-btn');
    const moveLocBtn = document.getElementById('move-loc-btn');
    const homeBtn = document.getElementById('home-btn');
    const stopBtn = document.getElementById('stop-btn');

    const openGripperBtn = document.getElementById('open-gripper-btn');
    const closeGripperBtn = document.getElementById('close-gripper-btn');

    const locationSelect = document.getElementById('location-select');
    const trackLocationSelect = document.getElementById('track-location-select');
    const moveTrackLocBtn = document.getElementById('move-track-loc-btn');

    let socket;

    // --- API Helper ---
    async function apiRequest(endpoint, method = 'GET', body = null) {
        try {
            const options = {
                method,
                headers: { 'Content-Type': 'application/json' },
            };
            if (body) {
                options.body = JSON.stringify(body);
            }
            const response = await fetch(`${API_BASE_URL}${endpoint}`, options);
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
            }
            return response.json();
        } catch (error) {
            console.error(`API request failed: ${error.message}`);
            updateStatusText(`Error: ${error.message}`, 'error');
            return null;
        }
    }

    // --- UI Updates ---
    function updateStatusUI(data) {
        // The `is_alive` flag is now the source of truth from the backend.
        const isConnected = data.is_alive === true;

        // Update connection text and light
        if (isConnected && data.connection_details) {
            const details = data.connection_details;
            const subtext = `${details.host}:${details.port} (${details.profile_name}${details.simulation_mode ? ' - Simulation' : ''})`;
            updateStatusText('Connected', subtext);
        } else {
            updateStatusText('Disconnected');
        }
        
        // Update status grid
        const systemStatus = data.system_status || {};
        const componentStates = data.component_states || {};

        document.getElementById('arm-state').textContent = componentStates.arm || 'N/A';
        document.getElementById('gripper-state').textContent = componentStates.gripper || 'N/A';
        document.getElementById('track-state').textContent = componentStates.track || 'N/A';
        document.getElementById('robot-mode').textContent = data.connection_details?.simulation_mode ? 'Simulation' : 'Hardware';

        const formatArray = (arr) => arr ? `[${arr.map(n => n.toFixed(2)).join(', ')}]` : '[...]';
        document.getElementById('current-position').textContent = formatArray(data.current_position);
        document.getElementById('current-joints').textContent = formatArray(data.current_joints);
        document.getElementById('track-position').textContent = data.track_position !== null && data.track_position !== undefined ? data.track_position.toFixed(2) : 'N/A';
        document.getElementById('last-error').textContent = systemStatus.last_error || 'None';
        
        // Set the state of all controls based on the connection status
        setControlsState(isConnected);
    }
    
    function updateStatusText(text, subtext = null) {
        const statusText = document.getElementById('status-text');
        const statusLight = document.getElementById('status-light');
        
        statusText.innerHTML = text;
        if (subtext) {
            statusText.innerHTML += `<br><small>${subtext}</small>`;
        }

        if (text.toLowerCase().includes('connected') || text.toLowerCase().includes('success')) {
            statusLight.className = 'status-light online';
        } else if (text.toLowerCase().includes('error')) {
            statusLight.className = 'status-light error';
        } else {
            statusLight.className = 'status-light offline';
        }
    }

    function setControlsState(enabled) {
        // Enable/disable all control buttons except connect
        const controlButtons = [
            disconnectBtn, movePosBtn, moveJointsBtn, moveLocBtn, 
            homeBtn, stopBtn, openGripperBtn, closeGripperBtn, moveTrackLocBtn
        ];
        
        controlButtons.forEach(btn => {
            if (btn) btn.disabled = !enabled;
        });
        
        // Connect button is opposite - enabled when disconnected
        connectBtn.disabled = enabled;
    }

    // --- WebSocket Handling ---
    function connectWebSocket() {
        if (socket && socket.readyState === WebSocket.OPEN) {
            return;
        }
        socket = new WebSocket(WS_URL);
        socket.onopen = () => console.log('WebSocket connected.');
        socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            if (message.type === 'status_update') {
                updateStatusUI(message.data);
            }
        };
        socket.onclose = () => {
            console.log('WebSocket disconnected.');
            setControlsState(false);
            updateStatusText('Disconnected');
        };
        socket.onerror = (error) => console.error('WebSocket error:', error);
    }

    // --- Initial Data Loading ---
    async function loadInitialData() {
        // Load connection profiles
        const profiles = await apiRequest('/api/configurations');
        if (profiles) {
            configSelect.innerHTML = profiles.map(p => `<option value="${p}">${p.replace(/_/g, ' ').toUpperCase()}</option>`).join('');
        }

        // Load arm locations
        const armLocations = await apiRequest('/locations');
        if (armLocations) {
            locationSelect.innerHTML = armLocations.locations.map(loc => `<option value="${loc}">${loc}</option>`).join('');
        }
        
        // Load track locations
        const trackLocations = await apiRequest('/track/locations');
        if (trackLocations) {
            trackLocationSelect.innerHTML = trackLocations.locations.map(loc => `<option value="${loc}">${loc}</option>`).join('');
        }
    }
    
    // --- Event Listeners ---
    configSelect.addEventListener('change', () => {
        const selectedProfile = configSelect.value;
        // Auto-enable simulation mode for Docker profiles
        if (selectedProfile.includes('docker')) {
            simulationModeCheckbox.checked = true;
        } else {
            simulationModeCheckbox.checked = false;
        }
    });

    connectBtn.addEventListener('click', async () => {
        const selectedProfile = configSelect.value;
        
        const body = {
            profile_name: selectedProfile,
            simulation_mode: simulationModeCheckbox.checked,
            safety_level: safetyLevelSelect.value,
        };

        const response = await apiRequest('/connect', 'POST', body);
        if (response) {
                // The WebSocket will handle the UI update. We just need to connect it.
                connectWebSocket();
        }
    });

    disconnectBtn.addEventListener('click', async () => {
        const response = await apiRequest('/disconnect', 'POST');
        if (response) {
            // The disconnect endpoint now broadcasts a final "disconnected" status.
            // We can rely on the WebSocket `onclose` handler to update the UI.
            updateStatusText(response.message || 'Disconnected');
        }
        if (socket) socket.close();
    });

    movePosBtn.addEventListener('click', () => {
        const body = {
            x: parseFloat(document.getElementById('pos-x').value),
            y: parseFloat(document.getElementById('pos-y').value),
            z: parseFloat(document.getElementById('pos-z').value),
            roll: parseFloat(document.getElementById('pos-roll').value) || null,
            pitch: parseFloat(document.getElementById('pos-pitch').value) || null,
            yaw: parseFloat(document.getElementById('pos-yaw').value) || null,
        };
        apiRequest('/move/position', 'POST', body);
    });

    moveJointsBtn.addEventListener('click', () => {
        const angles = document.getElementById('joint-angles').value.split(',').map(Number);
        apiRequest('/move/joints', 'POST', { angles });
    });
    
    moveLocBtn.addEventListener('click', () => {
        const location_name = locationSelect.value;
        apiRequest('/move/location', 'POST', { location_name });
    });

    homeBtn.addEventListener('click', () => apiRequest('/move/home', 'POST'));
    stopBtn.addEventListener('click', () => apiRequest('/move/stop', 'POST'));

    openGripperBtn.addEventListener('click', () => apiRequest('/gripper/open', 'POST', {}));
    closeGripperBtn.addEventListener('click', () => apiRequest('/gripper/close', 'POST', {}));
    
    moveTrackLocBtn.addEventListener('click', () => {
        const location_name = trackLocationSelect.value;
        apiRequest('/track/move/location', 'POST', { location_name });
    });
    
    // --- Tabs ---
    window.openTab = (evt, tabName) => {
        const tabcontent = document.getElementsByClassName("tab-content");
        for (let i = 0; i < tabcontent.length; i++) {
            tabcontent[i].style.display = "none";
            tabcontent[i].classList.remove("active");
        }
        const tablinks = document.getElementsByClassName("tab-link");
        for (let i = 0; i < tablinks.length; i++) {
            tablinks[i].classList.remove("active");
        }
        document.getElementById(tabName).style.display = "block";
        document.getElementById(tabName).classList.add("active");
        evt.currentTarget.classList.add("active");
    };

    // --- Initialization ---
    setControlsState(false);
    loadInitialData().catch(console.error);
}); 