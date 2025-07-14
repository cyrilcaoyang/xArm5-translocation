document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, checking elements...');
    console.log('connection-details exists:', !!document.getElementById('connection-details'));
    console.log('status-container exists:', !!document.getElementById('status-container'));
    console.log('status-main exists:', !!document.getElementById('status-main'));
    
    // Create connection-details element if it doesn't exist
    if (!document.getElementById('connection-details')) {
        console.log('Creating missing connection-details element');
        const statusContainer = document.getElementById('status-container');
        const connectionDetails = document.createElement('div');
        connectionDetails.id = 'connection-details';
        connectionDetails.className = 'connection-details';
        statusContainer.appendChild(connectionDetails);
    }
    
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
    async function apiRequest(endpoint, method = 'GET', body = null, skipErrorDisplay = false) {
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
                let errorMessage = errorData.detail || `HTTP error! status: ${response.status}`;
                
                // Simplify connection error messages
                if (endpoint === '/connect' && response.status >= 500) {
                    errorMessage = 'Failed to initialize robot connection.';
                }
                
                throw new Error(errorMessage);
            }
            return response.json();
        } catch (error) {
            console.error(`API request failed: ${error.message}`);
            
            // For connection errors, show error below status (unless skipped)
            if (!skipErrorDisplay) {
                showMessage(error.message, 'error');
            }
            return null;
        }
    }

    // --- Status Fetching ---
    async function fetchAndUpdateStatus() {
        try {
            const statusData = await apiRequest('/status', 'GET', null, true); // Skip error display
            if (statusData) {
                // Transform the /status response to match updateStatusUI format
                const transformedData = {
                    is_alive: statusData.is_alive,
                    connection_details: statusData.connection_details,
                    system_status: { last_error: statusData.last_error || 'None' },
                    component_states: {
                        arm: statusData.arm_state || 'N/A',
                        gripper: statusData.gripper_state || 'N/A', 
                        track: statusData.track_state || 'N/A'
                    },
                    current_position: statusData.current_position,
                    current_joints: statusData.current_joints,
                    track_position: null // Will be fetched separately if needed
                };
                updateStatusUI(transformedData);
            }
        } catch (error) {
            console.error('Failed to fetch status:', error);
            // On error, assume disconnected
            setControlsState(false);
            updateStatusText('Disconnected');
        }
    }

    // --- UI Updates ---
    function updateStatusUI(data) {
        // The `is_alive` flag is now the source of truth from the backend.
        const isConnected = data.is_alive === true;

        // Update connection text and light
        if (isConnected && data.connection_details) {
            updateStatusText('Connected');
            const details = data.connection_details;
            const subtext = `${details.host}:${details.port} (${details.profile_name}${details.simulation_mode ? ' - Simulation' : ''})`;
            showMessage(subtext, 'info');
        } else {
            updateStatusText('Disconnected');
            clearMessage();
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
    
    function updateStatusText(text) {
        const statusText = document.getElementById('status-text');
        const statusLight = document.getElementById('status-light');
        
        statusText.innerHTML = text;
        // Set status light based on connection state
        const lowerText = text.toLowerCase();
        if (lowerText === 'connected') {
            statusLight.className = 'status-light online';
        } else {
            statusLight.className = 'status-light offline';
        }
        // Do not clear error message here; let it persist until next status change
    }

    // --- Message Helpers ---
    function showMessage(msg, type = 'info') {
        const messageDiv = document.getElementById('connection-details');
        if (messageDiv) {
            messageDiv.textContent = msg;
            messageDiv.className = type === 'error' ? 'error-message-error' : 'error-message-info';
        } else {
            console.error('connection-details element not found');
        }
    }
    function clearMessage() {
        const messageDiv = document.getElementById('connection-details');
        if (messageDiv) {
            messageDiv.textContent = '';
            messageDiv.className = '';
        } else {
            console.error('connection-details element not found');
        }
    }

    function setControlsState(enabled) {
        // Enable/disable all control buttons based on connection state
        const controlButtons = [
            disconnectBtn, movePosBtn, moveJointsBtn, moveLocBtn, 
            homeBtn, stopBtn, openGripperBtn, closeGripperBtn, moveTrackLocBtn
        ];
        
        controlButtons.forEach(btn => {
            if (btn) btn.disabled = !enabled;
        });
        
        // Connect button is opposite - enabled when disconnected, disabled when connected
        if (connectBtn) connectBtn.disabled = enabled;
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
            // Only update UI if there's no error currently shown
            const statusText = document.getElementById('status-text');
            if (!statusText.textContent.toLowerCase().includes('error')) {
                setControlsState(false);
                updateStatusText('Disconnected');
            }
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
        
        // Disable connect button during connection attempt
        connectBtn.disabled = true;
        
        const body = {
            profile_name: selectedProfile,
            simulation_mode: simulationModeCheckbox.checked,
            safety_level: safetyLevelSelect.value,
        };

        const response = await apiRequest('/connect', 'POST', body);
        
        if (response && response.message) {
            // Extract connection details from the connect response
            const details = response.connection_details;
            if (details) {
                const connectedText = `${details.host}:${details.port} (${details.profile_name}${details.simulation_mode ? ' - Simulation' : ''})`;
                updateStatusText('Connected');
                showMessage(connectedText, 'info');
            } else {
                updateStatusText('Connected');
                clearMessage();
            }
            
            // Enable controls since connection was successful
            setControlsState(true);
            
            // Start WebSocket for real-time updates
            connectWebSocket();
            
            // Fetch current status to get detailed state info
            setTimeout(() => fetchAndUpdateStatus(), 500);
        } else {
            // Connection failed - re-enable connect button
            connectBtn.disabled = false;
            setControlsState(false);
        }
    });

    disconnectBtn.addEventListener('click', async () => {
        console.log('Disconnect button clicked');
        const response = await apiRequest('/disconnect', 'POST');
        
        // Close WebSocket connection first to prevent it from overriding our status update
        if (socket) socket.close();
        
        // Always update UI state regardless of response (in case of server issues)
        setControlsState(false);  // Disable disconnect and other controls, enable connect
        updateStatusText('Disconnected');
        clearMessage();
        
        if (response && response.message) {
            console.log('Disconnect response:', response.message);
        }
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

    homeBtn.addEventListener('click', () => {
        console.log('Home button clicked');
        apiRequest('/move/home', 'POST');
    });
    stopBtn.addEventListener('click', () => {
        console.log('Stop button clicked');
        apiRequest('/move/stop', 'POST');
    });

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
    
    // Check current connection status on page load (after a short delay)
    setTimeout(() => {
        fetchAndUpdateStatus().catch(() => {
            // If status check fails, assume disconnected (which is the default)
            console.log('Initial status check failed - assuming disconnected state');
        });
    }, 100);
}); 