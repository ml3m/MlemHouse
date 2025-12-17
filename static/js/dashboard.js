/**
 * EcoHub IoT Dashboard - Real-time Device Management
 * Professional JavaScript Implementation
 */

// ============================================================================
// Global State
// ============================================================================

const state = {
    devices: {},
    metrics: {},
    alerts: [],
    ws: null,
    connected: false,
    charts: {},
    chartData: {
        energy: [],
        temperature: [],
        timestamps: []
    },
    currentFilter: 'all',
    startTime: Date.now()
};

// Device type icons (emoji placeholders - replace with actual images)
const DEVICE_ICONS = {
    BULB: '💡',           // Replace: /static/img/bulb.png
    THERMOSTAT: '🌡️',     // Replace: /static/img/thermostat.png
    CAMERA: '📷',         // Replace: /static/img/camera.png
    WATER_METER: '💧'     // Replace: /static/img/water_meter.png
};

// Room icons
const ROOM_ICONS = {
    'Living Room': '🛋️',
    'Bedroom': '🛏️',
    'Kitchen': '🍳',
    'Bathroom': '🚿',
    'Entrance': '🚪',
    'Backyard': '🌳',
    'Garage': '🚗',
    'Garden': '🌻',
    'Office': '💼',
    'Utility Room': '🔧'
};

// Issue display names
const ISSUE_NAMES = {
    'high_temp': 'High Temperature',
    'low_temp': 'Low Temperature',
    'high_humidity': 'High Humidity',
    'low_battery': 'Low Battery',
    'critical_battery': 'Critical Battery',
    'connection_lost': 'Connection Lost',
    'weak_signal': 'Weak Signal',
    'firmware_update': 'Firmware Update Available',
    'sensor_malfunction': 'Sensor Malfunction',
    'storage_full': 'Storage Full',
    'motion_alert': 'Motion Detected',
    'bulb_flickering': 'Bulb Flickering',
    'unresponsive': 'Device Unresponsive',
    'overload': 'Overload Warning',
    // Water-related issues
    'leak_detected': '🚨 Leak Detected!',
    'high_flow': 'High Water Flow',
    'abnormal_usage': 'Abnormal Water Usage'
};

// ============================================================================
// WebSocket Connection
// ============================================================================

function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws`;
    
    state.ws = new WebSocket(wsUrl);
    
    state.ws.onopen = () => {
        console.log('🔌 WebSocket connected');
        state.connected = true;
        updateConnectionStatus(true);
    };
    
    state.ws.onclose = () => {
        console.log('❌ WebSocket disconnected');
        state.connected = false;
        updateConnectionStatus(false);
        // Reconnect after 3 seconds
        setTimeout(connectWebSocket, 3000);
    };
    
    state.ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    state.ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        handleWebSocketMessage(message);
    };
}

function handleWebSocketMessage(message) {
    switch (message.type) {
        case 'initial_state':
            handleInitialState(message.data);
            break;
        case 'device_update':
            handleDeviceUpdate(message.data);
            break;
        case 'metrics_update':
            handleMetricsUpdate(message.data);
            break;
        case 'alert':
            handleNewAlert(message.data);
            break;
        case 'alerts_cleared':
            state.alerts = [];
            renderAlerts();
            updateAlertBadges();
            break;
    }
}

function handleInitialState(data) {
    // Store devices
    data.devices.forEach(device => {
        state.devices[device.device_id] = device;
    });
    
    // Store metrics
    state.metrics = data.metrics;
    
    // Store alerts
    state.alerts = data.alerts || [];
    
    // Render everything
    renderDevicesGrid();
    renderDevicesTable();
    renderMetrics();
    renderAlerts();
    renderRooms();
    updateAlertBadges();
}

function handleDeviceUpdate(device) {
    state.devices[device.device_id] = device;
    
    // Update specific device card
    updateDeviceCard(device);
    
    // Update table row
    updateDeviceTableRow(device);
    
    // Update charts with new data
    addChartDataPoint(device);
}

function handleMetricsUpdate(metrics) {
    state.metrics = metrics;
    renderMetrics();
}

function handleNewAlert(alert) {
    state.alerts.unshift(alert);
    if (state.alerts.length > 50) {
        state.alerts = state.alerts.slice(0, 50);
    }
    
    renderAlerts();
    updateAlertBadges();
    
    // Show toast notification
    showToast(
        alert.severity === 'error' ? 'error' : 'warning',
        `${alert.device_name}`,
        ISSUE_NAMES[alert.issue] || alert.issue
    );
}

// ============================================================================
// UI Updates
// ============================================================================

function updateConnectionStatus(connected) {
    const statusEl = document.querySelector('.ws-status');
    if (statusEl) {
        statusEl.textContent = connected ? '● Connected' : '● Disconnected';
        statusEl.classList.toggle('disconnected', !connected);
    }
}

function renderMetrics() {
    const m = state.metrics;
    
    // Row 1: Overview stats
    document.getElementById('stat-devices').textContent = m.total_devices || '--';
    document.getElementById('stat-online').textContent = m.online_devices || '--';
    document.getElementById('stat-energy').textContent = m.current_power_watts || m.total_energy_watts || '--';
    document.getElementById('stat-lights').textContent = `${m.lights_on || 0}/${m.total_lights || 0}`;
    document.getElementById('stat-temp').textContent = m.average_temperature || '--';
    
    // Heating status
    const heatingEl = document.getElementById('stat-heating');
    if (heatingEl) {
        heatingEl.textContent = m.heating_active ? '🔥 Heating: On' : 'Heating: Off';
        heatingEl.className = m.heating_active ? 'stat-trend up' : 'stat-trend neutral';
    }
    
    // Water stats
    const waterEl = document.getElementById('stat-water');
    if (waterEl) waterEl.textContent = Math.round(m.water_daily_liters || 0);
    
    const flowEl = document.getElementById('stat-flow');
    if (flowEl) {
        if (m.water_flowing) {
            flowEl.innerHTML = `<span class="flow-indicator active"></span> Flow: ${m.current_flow_rate || 0} L/min`;
        } else {
            flowEl.textContent = 'Flow: 0 L/min';
        }
    }
    
    // Row 2: Cost stats (Romanian lei)
    const elecCostEl = document.getElementById('stat-elec-cost');
    if (elecCostEl) elecCostEl.textContent = (m.electricity_cost || 0).toFixed(2);
    
    const elecKwhEl = document.getElementById('stat-elec-kwh');
    if (elecKwhEl) elecKwhEl.textContent = (m.electricity_kwh || 0).toFixed(3);
    
    const gasCostEl = document.getElementById('stat-gas-cost');
    if (gasCostEl) gasCostEl.textContent = (m.gas_cost || 0).toFixed(2);
    
    const gasKwhEl = document.getElementById('stat-gas-kwh');
    if (gasKwhEl) gasKwhEl.textContent = (m.gas_kwh || 0).toFixed(3);
    
    const waterCostEl = document.getElementById('stat-water-cost');
    if (waterCostEl) waterCostEl.textContent = (m.water_cost || 0).toFixed(2);
    
    const waterM3El = document.getElementById('stat-water-m3');
    if (waterM3El) waterM3El.textContent = (m.water_monthly_m3 || 0).toFixed(2);
    
    // Session total cost (current accumulated)
    const sessionTotalEl = document.getElementById('stat-session-total');
    if (sessionTotalEl) sessionTotalEl.textContent = (m.total_cost || 0).toFixed(2);
    
    // Simulated time display
    const simTimeEl = document.getElementById('stat-sim-time');
    if (simTimeEl) {
        const hours = m.simulated_hours || 0;
        if (hours < 1) {
            simTimeEl.textContent = Math.round(hours * 60) + 'm';
        } else if (hours < 24) {
            simTimeEl.textContent = hours.toFixed(1) + 'h';
        } else {
            simTimeEl.textContent = (hours / 24).toFixed(1) + ' days';
        }
    }
    
    // Estimated monthly cost (with reasonable cap display)
    const estMonthlyEl = document.getElementById('stat-est-monthly');
    if (estMonthlyEl) estMonthlyEl.textContent = (m.est_monthly_total || 0).toFixed(0);
    
    // Carbon footprint
    const carbonEl = document.getElementById('stat-carbon');
    if (carbonEl) carbonEl.textContent = (m.carbon_kg || 0).toFixed(2);
    
    // Alerts
    document.getElementById('stat-alerts').textContent = m.active_alerts || 0;
    document.getElementById('stat-issues').textContent = `${m.devices_with_issues || 0} issues detected`;
    
    // Analytics page stats
    const readingsEl = document.getElementById('analytics-readings');
    if (readingsEl) readingsEl.textContent = m.total_readings || 0;
    
    const uptimeEl = document.getElementById('analytics-uptime');
    if (uptimeEl) {
        const uptime = m.uptime_seconds || Math.floor((Date.now() - state.startTime) / 1000);
        const mins = Math.floor(uptime / 60);
        const secs = uptime % 60;
        uptimeEl.textContent = `${mins}m ${secs}s`;
    }
}

function renderDevicesGrid() {
    const grid = document.getElementById('devices-grid');
    if (!grid) return;
    
    const devices = Object.values(state.devices);
    const filtered = state.currentFilter === 'all' 
        ? devices 
        : devices.filter(d => d.device_type === state.currentFilter);
    
    grid.innerHTML = filtered.map(device => createDeviceCard(device)).join('');
}

function createDeviceCard(device) {
    const isOnline = device.is_connected;
    const hasIssue = device.issue && device.issue !== 'none';
    const isError = device.status === 'error';
    
    let statusClass = isOnline ? '' : 'offline';
    if (hasIssue) statusClass = isError ? 'has-error' : 'has-issue';
    
    let dotClass = isOnline ? '' : 'offline';
    if (hasIssue) dotClass = isError ? 'error' : 'warning';
    
    const iconClass = device.device_type.toLowerCase();
    const isOff = device.device_type === 'BULB' && !device.is_on;
    
    let metricsHtml = '';
    let toggleHtml = '';
    
    if (device.device_type === 'BULB') {
        metricsHtml = `
            <div class="device-metric">
                <span class="device-metric-label">Brightness</span>
                <span class="device-metric-value">${device.brightness}%</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Power</span>
                <span class="device-metric-value">${device.power_draw?.toFixed(1) || 0}W</span>
            </div>
        `;
        toggleHtml = `
            <div class="device-toggle ${device.is_on ? 'on' : ''}" onclick="toggleDevice('${device.device_id}', event)">
                ${device.is_on ? '● ON' : '○ OFF'}
            </div>
        `;
    } else if (device.device_type === 'THERMOSTAT') {
        metricsHtml = `
            <div class="device-metric">
                <span class="device-metric-label">Current</span>
                <span class="device-metric-value">${device.current_temp}°C</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Target</span>
                <span class="device-metric-value">${device.target_temp}°C</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Humidity</span>
                <span class="device-metric-value">${device.humidity}%</span>
            </div>
        `;
    } else if (device.device_type === 'CAMERA') {
        metricsHtml = `
            <div class="device-metric">
                <span class="device-metric-label">Battery</span>
                <span class="device-metric-value">${device.battery_level}%</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Storage</span>
                <span class="device-metric-value">${device.storage_percent}%</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Motion</span>
                <span class="device-metric-value">${device.motion_detected ? '🔴 YES' : '⚪ No'}</span>
            </div>
        `;
    } else if (device.device_type === 'WATER_METER') {
        const flowClass = device.is_flowing ? 'active' : '';
        const leakWarning = device.leak_detected ? '<span class="leak-warning">🚨 LEAK!</span>' : '';
        metricsHtml = `
            <div class="device-metric">
                <span class="device-metric-label">Flow</span>
                <span class="device-metric-value flow-indicator ${flowClass}">${device.flow_rate || 0} L/min</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Today</span>
                <span class="device-metric-value">${Math.round(device.daily_usage || 0)} L</span>
            </div>
            <div class="device-metric">
                <span class="device-metric-label">Month</span>
                <span class="device-metric-value">${Math.round(device.monthly_usage || 0)} L</span>
            </div>
            ${leakWarning}
        `;
        if (!device.valve_open) {
            toggleHtml = `<div class="device-toggle" onclick="sendCommand('${device.device_id}', 'open_valve', {}, event)">🔴 Valve Closed - Click to Open</div>`;
        }
    }
    
    return `
        <div class="device-card ${statusClass}" data-device-id="${device.device_id}" onclick="openDeviceModal('${device.device_id}')">
            <div class="device-status-dot ${dotClass}"></div>
            <div class="device-card-header">
                <div class="device-icon ${iconClass} ${isOff ? 'off' : ''}">
                    ${DEVICE_ICONS[device.device_type] || '📱'}
                </div>
                <div class="device-info">
                    <div class="device-name">${device.name}</div>
                    <div class="device-location">${device.location}</div>
                </div>
            </div>
            <div class="device-card-body">
                ${metricsHtml}
                ${toggleHtml}
            </div>
        </div>
    `;
}

function updateDeviceCard(device) {
    const card = document.querySelector(`[data-device-id="${device.device_id}"]`);
    if (card) {
        const newCard = document.createElement('div');
        newCard.innerHTML = createDeviceCard(device);
        card.replaceWith(newCard.firstElementChild);
    }
}

function renderDevicesTable() {
    const tbody = document.getElementById('devices-table-body');
    if (!tbody) return;
    
    const devices = Object.values(state.devices);
    
    tbody.innerHTML = devices.map(device => {
        const statusClass = device.status === 'online' ? 'online' : 
                           device.status === 'warning' ? 'warning' :
                           device.status === 'error' ? 'error' : 'offline';
        
        const signalBars = getSignalBars(device.signal_strength);
        
        let details = '';
        if (device.device_type === 'BULB') {
            details = `${device.is_on ? 'On' : 'Off'} • ${device.brightness}%`;
        } else if (device.device_type === 'THERMOSTAT') {
            details = `${device.current_temp}°C → ${device.target_temp}°C`;
        } else if (device.device_type === 'CAMERA') {
            details = `🔋 ${device.battery_level}%`;
        } else if (device.device_type === 'WATER_METER') {
            details = `${device.is_flowing ? '💧' : '⚪'} ${Math.round(device.daily_usage || 0)}L today`;
        }
        
        return `
            <tr data-device-id="${device.device_id}">
                <td>
                    <div class="table-device">
                        <div class="table-device-icon ${device.device_type.toLowerCase()}">
                            ${DEVICE_ICONS[device.device_type] || '📱'}
                        </div>
                        <div>
                            <div class="table-device-name">${device.name}</div>
                            <div class="table-device-id">${device.device_id}</div>
                        </div>
                    </div>
                </td>
                <td>${device.location}</td>
                <td><span class="status-badge ${statusClass}">${device.status}</span></td>
                <td>
                    <div class="signal-bar">
                        ${signalBars}
                    </div>
                </td>
                <td>${details}</td>
                <td>
                    <div class="table-actions">
                        <button class="table-btn" onclick="openDeviceModal('${device.device_id}')">Control</button>
                    </div>
                </td>
            </tr>
        `;
    }).join('');
}

function updateDeviceTableRow(device) {
    renderDevicesTable(); // Simple refresh for now
}

function getSignalBars(strength) {
    const levels = [25, 50, 75, 100];
    return levels.map((level, i) => 
        `<span class="${strength >= level - 24 ? 'active' : ''}"></span>`
    ).join('');
}

function renderAlerts() {
    const alertsList = document.getElementById('alerts-list');
    const activityList = document.getElementById('activity-list');
    
    if (alertsList) {
        if (state.alerts.length === 0) {
            alertsList.innerHTML = `
                <div class="alerts-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                        <polyline points="22 4 12 14.01 9 11.01"></polyline>
                    </svg>
                    <p>No active alerts</p>
                    <span>All systems operating normally</span>
                </div>
            `;
        } else {
            alertsList.innerHTML = state.alerts.map(alert => `
                <div class="alert-item ${alert.severity}">
                    <div class="alert-icon">⚠️</div>
                    <div class="alert-content">
                        <div class="alert-title">${ISSUE_NAMES[alert.issue] || alert.issue}</div>
                        <div class="alert-description">${alert.device_name} • ${alert.device_type}</div>
                        <div class="alert-time">${formatTime(alert.timestamp)}</div>
                    </div>
                    <button class="alert-dismiss" onclick="dismissAlert('${alert.id}')">
                        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                            <line x1="18" y1="6" x2="6" y2="18"></line>
                            <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                    </button>
                </div>
            `).join('');
        }
    }
    
    if (activityList) {
        if (state.alerts.length === 0) {
            activityList.innerHTML = `
                <div class="activity-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="10"></circle>
                        <polyline points="12 6 12 12 16 14"></polyline>
                    </svg>
                    <span>No recent activity</span>
                </div>
            `;
        } else {
            activityList.innerHTML = state.alerts.slice(0, 10).map(alert => `
                <div class="activity-item ${alert.severity}">
                    <div class="activity-icon">⚠️</div>
                    <div class="activity-content">
                        <div class="activity-title">${ISSUE_NAMES[alert.issue] || alert.issue}</div>
                        <div class="activity-description">${alert.device_name}</div>
                    </div>
                    <div class="activity-time">${formatTimeShort(alert.timestamp)}</div>
                </div>
            `).join('');
        }
    }
}

function updateAlertBadges() {
    const count = state.alerts.length;
    
    const badge = document.getElementById('alert-badge');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline' : 'none';
    }
    
    const notifCount = document.getElementById('notification-count');
    if (notifCount) {
        notifCount.textContent = count;
        notifCount.setAttribute('data-count', count);
    }
}

function renderRooms() {
    const roomsList = document.getElementById('rooms-list');
    const roomsDetailGrid = document.getElementById('rooms-detail-grid');
    
    // Group devices by location
    const rooms = {};
    Object.values(state.devices).forEach(device => {
        if (!rooms[device.location]) {
            rooms[device.location] = [];
        }
        rooms[device.location].push(device);
    });
    
    if (roomsList) {
        roomsList.innerHTML = Object.entries(rooms).map(([name, devices]) => {
            const onlineCount = devices.filter(d => d.is_connected).length;
            return `
                <div class="room-item" onclick="filterByRoom('${name}')">
                    <div class="room-icon">${ROOM_ICONS[name] || '🏠'}</div>
                    <div class="room-info">
                        <div class="room-name">${name}</div>
                        <div class="room-devices">${devices.length} devices</div>
                    </div>
                    <div class="room-status">
                        ${devices.map(d => `<div class="room-status-dot" style="background: ${d.is_connected ? 'var(--success)' : 'var(--text-muted)'}"></div>`).join('')}
                    </div>
                </div>
            `;
        }).join('');
    }
    
    if (roomsDetailGrid) {
        roomsDetailGrid.innerHTML = Object.entries(rooms).map(([name, devices]) => `
            <div class="room-card">
                <div class="room-card-header">
                    <div class="room-card-icon">${ROOM_ICONS[name] || '🏠'}</div>
                    <div>
                        <div class="room-card-title">${name}</div>
                        <div class="room-card-subtitle">${devices.length} devices</div>
                    </div>
                </div>
                <div class="room-card-body">
                    <div class="room-devices-list">
                        ${devices.map(d => createDeviceCard(d)).join('')}
                    </div>
                </div>
            </div>
        `).join('');
    }
}

// ============================================================================
// Charts
// ============================================================================

function initCharts() {
    // Energy Chart
    const energyCtx = document.getElementById('energy-chart')?.getContext('2d');
    if (energyCtx) {
        state.charts.energy = new Chart(energyCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Power (W)',
                    data: [],
                    borderColor: '#f59e0b',
                    backgroundColor: 'rgba(245, 158, 11, 0.1)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: getChartOptions('Power Usage (W)')
        });
    }
    
    // Temperature Chart
    const tempCtx = document.getElementById('temp-chart')?.getContext('2d');
    if (tempCtx) {
        state.charts.temp = new Chart(tempCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Living Room',
                    data: [],
                    borderColor: '#10b981',
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    pointRadius: 0
                }, {
                    label: 'Bedroom',
                    data: [],
                    borderColor: '#3b82f6',
                    backgroundColor: 'transparent',
                    tension: 0.4,
                    pointRadius: 0
                }]
            },
            options: getChartOptions('Temperature (°C)')
        });
    }
    
    // Health Chart (doughnut)
    const healthCtx = document.getElementById('health-chart')?.getContext('2d');
    if (healthCtx) {
        state.charts.health = new Chart(healthCtx, {
            type: 'doughnut',
            data: {
                labels: ['Online', 'Warning', 'Offline'],
                datasets: [{
                    data: [0, 0, 0],
                    backgroundColor: ['#10b981', '#f59e0b', '#6b7280'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { color: '#8b949e' }
                    }
                }
            }
        });
    }
    
    // Battery Chart (bar)
    const batteryCtx = document.getElementById('battery-chart')?.getContext('2d');
    if (batteryCtx) {
        state.charts.battery = new Chart(batteryCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Battery Level',
                    data: [],
                    backgroundColor: [],
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 100,
                        grid: { color: 'rgba(255,255,255,0.05)' },
                        ticks: { color: '#8b949e' }
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: '#8b949e' }
                    }
                },
                plugins: {
                    legend: { display: false }
                }
            }
        });
    }
}

function getChartOptions(title) {
    return {
        responsive: true,
        maintainAspectRatio: false,
        interaction: {
            intersect: false,
            mode: 'index'
        },
        scales: {
            y: {
                beginAtZero: true,
                grid: { color: 'rgba(255,255,255,0.05)' },
                ticks: { color: '#8b949e' }
            },
            x: {
                grid: { display: false },
                ticks: { 
                    color: '#8b949e',
                    maxTicksLimit: 10
                }
            }
        },
        plugins: {
            legend: {
                position: 'top',
                align: 'end',
                labels: { 
                    color: '#8b949e',
                    usePointStyle: true,
                    pointStyle: 'circle'
                }
            }
        }
    };
}

function addChartDataPoint(device) {
    const now = new Date().toLocaleTimeString();
    
    // Energy chart - aggregate all bulbs
    if (state.charts.energy && device.device_type === 'BULB') {
        const totalEnergy = Object.values(state.devices)
            .filter(d => d.device_type === 'BULB')
            .reduce((sum, d) => sum + (d.power_draw || 0), 0);
        
        const chart = state.charts.energy;
        if (chart.data.labels.length > 30) {
            chart.data.labels.shift();
            chart.data.datasets[0].data.shift();
        }
        chart.data.labels.push(now);
        chart.data.datasets[0].data.push(totalEnergy);
        chart.update('none');
    }
    
    // Temperature chart
    if (state.charts.temp && device.device_type === 'THERMOSTAT') {
        const chart = state.charts.temp;
        if (chart.data.labels.length > 30) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(ds => ds.data.shift());
        }
        chart.data.labels.push(now);
        
        // Update the correct dataset based on location
        const datasetIndex = device.location === 'Living Room' ? 0 : 1;
        chart.data.datasets[datasetIndex].data.push(device.current_temp);
        
        // Keep other dataset at same length
        const otherIndex = datasetIndex === 0 ? 1 : 0;
        if (chart.data.datasets[otherIndex].data.length < chart.data.labels.length) {
            const lastVal = chart.data.datasets[otherIndex].data.slice(-1)[0] || 22;
            chart.data.datasets[otherIndex].data.push(lastVal);
        }
        
        chart.update('none');
    }
    
    // Update health chart periodically
    updateHealthChart();
    updateBatteryChart();
}

function updateHealthChart() {
    if (!state.charts.health) return;
    
    const devices = Object.values(state.devices);
    const online = devices.filter(d => d.status === 'online').length;
    const warning = devices.filter(d => d.status === 'warning').length;
    const offline = devices.filter(d => !d.is_connected).length;
    
    state.charts.health.data.datasets[0].data = [online, warning, offline];
    state.charts.health.update('none');
}

function updateBatteryChart() {
    if (!state.charts.battery) return;
    
    const cameras = Object.values(state.devices).filter(d => d.device_type === 'CAMERA');
    
    state.charts.battery.data.labels = cameras.map(c => c.name.replace(' Cam', ''));
    state.charts.battery.data.datasets[0].data = cameras.map(c => c.battery_level);
    state.charts.battery.data.datasets[0].backgroundColor = cameras.map(c => 
        c.battery_level > 50 ? '#10b981' :
        c.battery_level > 20 ? '#f59e0b' : '#ef4444'
    );
    state.charts.battery.update('none');
}

// ============================================================================
// Device Control
// ============================================================================

function openDeviceModal(deviceId) {
    const device = state.devices[deviceId];
    if (!device) return;
    
    const modal = document.getElementById('device-modal');
    const modalName = document.getElementById('modal-device-name');
    const modalBody = document.getElementById('modal-body');
    
    modalName.textContent = device.name;
    
    let controlsHtml = '';
    
    if (device.device_type === 'BULB') {
        controlsHtml = `
            <div class="control-group">
                <label class="control-label">Power</label>
                <div class="control-toggle">
                    <button class="toggle-btn ${device.is_on ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'turn_on')">ON</button>
                    <button class="toggle-btn ${!device.is_on ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'turn_off')">OFF</button>
                </div>
            </div>
            <div class="control-group">
                <label class="control-label">Brightness</label>
                <input type="range" class="control-slider" min="0" max="100" value="${device.brightness}" 
                    onchange="sendCommand('${deviceId}', 'set_brightness', {level: parseInt(this.value)})"
                    oninput="document.getElementById('brightness-value').textContent = this.value + '%'">
                <div class="control-value" id="brightness-value">${device.brightness}%</div>
            </div>
        `;
    } else if (device.device_type === 'THERMOSTAT') {
        controlsHtml = `
            <div class="control-group">
                <label class="control-label">Current Temperature</label>
                <div class="control-value">${device.current_temp}°C</div>
            </div>
            <div class="control-group">
                <label class="control-label">Target Temperature</label>
                <input type="range" class="control-slider" min="16" max="30" step="0.5" value="${device.target_temp}"
                    onchange="sendCommand('${deviceId}', 'set_target', {temp: parseFloat(this.value)})"
                    oninput="document.getElementById('target-value').textContent = this.value + '°C'">
                <div class="control-value" id="target-value">${device.target_temp}°C</div>
            </div>
            <div class="control-group">
                <label class="control-label">Mode</label>
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'heat')">🔥 Heat</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'cool')">❄️ Cool</button>
                </div>
            </div>
            <div class="control-group">
                <label class="control-label">Humidity: ${device.humidity}%</label>
            </div>
        `;
    } else if (device.device_type === 'CAMERA') {
        controlsHtml = `
            <div class="control-group">
                <label class="control-label">Battery Level</label>
                <div class="control-value">${device.battery_level}%</div>
            </div>
            <div class="control-group">
                <label class="control-label">Storage Used</label>
                <div class="control-value">${device.storage_percent}%</div>
            </div>
            <div class="control-group">
                <label class="control-label">Actions</label>
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'snapshot')">📸 Snapshot</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'arm')">🔒 Arm</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'disarm')">🔓 Disarm</button>
                </div>
            </div>
            <div class="control-group">
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'charge')">🔌 Start Charging</button>
                    <button class="toggle-btn danger" onclick="sendCommand('${deviceId}', 'clear_storage')">🗑️ Clear Storage</button>
                </div>
            </div>
        `;
    } else if (device.device_type === 'WATER_METER') {
        const valveStatus = device.valve_open ? '🟢 Open' : '🔴 Closed';
        const leakAlert = device.leak_detected ? '<div class="control-group"><div class="leak-warning">🚨 LEAK DETECTED!</div></div>' : '';
        controlsHtml = `
            ${leakAlert}
            <div class="control-group">
                <label class="control-label">Flow Rate</label>
                <div class="control-value">${device.flow_rate || 0} L/min</div>
            </div>
            <div class="control-group">
                <label class="control-label">Today's Usage</label>
                <div class="control-value">${Math.round(device.daily_usage || 0)} liters</div>
            </div>
            <div class="control-group">
                <label class="control-label">Monthly Usage</label>
                <div class="control-value">${Math.round(device.monthly_usage || 0)} L (${((device.monthly_usage || 0) / 1000).toFixed(2)} m³)</div>
            </div>
            <div class="control-group">
                <label class="control-label">Pressure</label>
                <div class="control-value">${device.pressure_bar || 0} bar</div>
            </div>
            <div class="control-group">
                <label class="control-label">Valve Status: ${valveStatus}</label>
                <div class="control-toggle">
                    <button class="toggle-btn ${device.valve_open ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'open_valve')">Open Valve</button>
                    <button class="toggle-btn danger ${!device.valve_open ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'close_valve')">Close Valve</button>
                </div>
            </div>
            <div class="control-group">
                <label class="control-label">Reset Counters</label>
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'reset_daily')">Reset Daily</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'reset_monthly')">Reset Monthly</button>
                </div>
            </div>
            ${device.leak_detected ? `
            <div class="control-group">
                <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'ack_leak')">✓ Acknowledge Leak (After Inspection)</button>
            </div>
            ` : ''}
        `;
    }
    
    modalBody.innerHTML = controlsHtml;
    modal.classList.add('active');
}

function closeModal() {
    document.getElementById('device-modal').classList.remove('active');
}

function sendCommand(deviceId, command, params = {}) {
    if (state.ws && state.connected) {
        state.ws.send(JSON.stringify({
            type: 'command',
            device_id: deviceId,
            command: command,
            params: params
        }));
        
        showToast('success', 'Command Sent', `${command} sent to device`);
    }
}

function toggleDevice(deviceId, event) {
    event.stopPropagation();
    const device = state.devices[deviceId];
    if (device) {
        sendCommand(deviceId, device.is_on ? 'turn_off' : 'turn_on');
    }
}

// ============================================================================
// Utility Functions
// ============================================================================

function filterDevices(type) {
    state.currentFilter = type;
    renderDevicesGrid();
    
    // Update active button
    document.querySelectorAll('.card-actions .btn-sm').forEach(btn => {
        btn.classList.toggle('active', btn.textContent.toLowerCase().includes(type.toLowerCase()) || 
            (type === 'all' && btn.textContent === 'All'));
    });
}

function filterByRoom(roomName) {
    // Switch to devices view and filter
    switchView('devices');
    // Could implement room filtering in table
}

async function dismissAlert(alertId) {
    try {
        await fetch(`/api/alerts/${alertId}`, { method: 'DELETE' });
        state.alerts = state.alerts.filter(a => a.id !== alertId);
        renderAlerts();
        updateAlertBadges();
    } catch (err) {
        console.error('Failed to dismiss alert:', err);
    }
}

async function clearAlerts() {
    try {
        await fetch('/api/alerts', { method: 'DELETE' });
        state.alerts = [];
        renderAlerts();
        updateAlertBadges();
        showToast('success', 'Alerts Cleared', 'All alerts have been dismissed');
    } catch (err) {
        console.error('Failed to clear alerts:', err);
    }
}

// Toast rate limiting
const toastState = {
    lastToast: {},  // Track last toast time by type+title
    maxToasts: 3,   // Maximum toasts on screen
    cooldown: 5000  // Minimum ms between same toast type
};

function showToast(type, title, message, options = {}) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    
    // Rate limiting - prevent spam of same toast
    const toastKey = `${type}-${title}`;
    const now = Date.now();
    const lastTime = toastState.lastToast[toastKey] || 0;
    
    if (now - lastTime < toastState.cooldown && !options.force) {
        return; // Skip this toast, too soon
    }
    toastState.lastToast[toastKey] = now;
    
    // Limit max toasts on screen
    const existingToasts = container.querySelectorAll('.toast');
    if (existingToasts.length >= toastState.maxToasts) {
        // Remove oldest toast(s) to make room
        const toRemove = existingToasts.length - toastState.maxToasts + 1;
        for (let i = 0; i < toRemove; i++) {
            existingToasts[i].remove();
        }
    }
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <div class="toast-icon">
            ${type === 'success' ? '✓' : type === 'warning' ? '⚠' : '✕'}
        </div>
        <div class="toast-content">
            <div class="toast-title">${title}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    container.appendChild(toast);
    
    // Auto-remove after duration (shorter for warnings)
    const duration = type === 'warning' ? 3000 : 4000;
    setTimeout(() => {
        if (toast.parentElement) toast.remove();
    }, duration);
}

function formatTime(isoString) {
    const date = new Date(isoString);
    return date.toLocaleString();
}

function formatTimeShort(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = (now - date) / 1000;
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function updateClock() {
    const now = new Date();
    document.getElementById('current-time').textContent = now.toLocaleTimeString();
    document.getElementById('current-date').textContent = now.toLocaleDateString('en-US', {
        weekday: 'short',
        month: 'short',
        day: 'numeric',
        year: 'numeric'
    });
}

function switchView(viewId) {
    // Update nav
    document.querySelectorAll('.nav-item').forEach(item => {
        item.classList.toggle('active', item.dataset.view === viewId);
    });
    
    // Update views
    document.querySelectorAll('.view').forEach(view => {
        view.classList.toggle('active', view.id === `view-${viewId}`);
    });
    
    // Update page title
    const titles = {
        dashboard: 'Dashboard',
        devices: 'Devices',
        analytics: 'Analytics',
        alerts: 'Alert Center',
        rooms: 'Rooms',
        settings: 'Settings'
    };
    document.querySelector('.page-title').textContent = titles[viewId] || 'Dashboard';
    
    // Load settings when switching to settings view
    if (viewId === 'settings') {
        loadSettings();
    }
}

// ============================================================================
// Initialization
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Connect WebSocket
    connectWebSocket();
    
    // Initialize charts
    initCharts();
    
    // Start clock
    updateClock();
    setInterval(updateClock, 1000);
    
    // Update uptime counter
    setInterval(() => {
        const uptimeEl = document.getElementById('analytics-uptime');
        if (uptimeEl) {
            const uptime = Math.floor((Date.now() - state.startTime) / 1000);
            const mins = Math.floor(uptime / 60);
            const secs = uptime % 60;
            uptimeEl.textContent = `${mins}m ${secs}s`;
        }
    }, 1000);
    
    // Navigation
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const viewId = item.dataset.view;
            if (viewId) switchView(viewId);
        });
    });
    
    // Refresh button
    document.getElementById('refresh-btn')?.addEventListener('click', () => {
        location.reload();
    });
    
    // Close modal on escape
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeModal();
    });
    
    // Device search
    document.getElementById('device-search')?.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase();
        document.querySelectorAll('#devices-table-body tr').forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(query) ? '' : 'none';
        });
    });
});

// ============================================================================
// Add Device Functions
// ============================================================================

function openAddDeviceModal() {
    document.getElementById('add-device-modal').classList.add('active');
    document.getElementById('add-device-form').reset();
    document.getElementById('device-specific-fields').innerHTML = '';
}

function closeAddDeviceModal() {
    document.getElementById('add-device-modal').classList.remove('active');
}

function updateDeviceForm() {
    const deviceType = document.getElementById('new-device-type').value;
    const fieldsContainer = document.getElementById('device-specific-fields');
    
    let fieldsHtml = '';
    
    switch (deviceType) {
        case 'BULB':
            fieldsHtml = `
                <div class="form-group">
                    <label class="form-label">Initial Brightness</label>
                    <input type="range" id="new-brightness" class="control-slider" min="0" max="100" value="100"
                        oninput="document.getElementById('brightness-display').textContent = this.value + '%'">
                    <div class="control-value" id="brightness-display">100%</div>
                </div>
                <div class="form-group">
                    <label class="form-label">Initial State</label>
                    <select id="new-is-on" class="form-select">
                        <option value="false">Off</option>
                        <option value="true">On</option>
                    </select>
                </div>
            `;
            break;
        case 'THERMOSTAT':
            fieldsHtml = `
                <div class="form-group">
                    <label class="form-label">Target Temperature (°C)</label>
                    <input type="number" id="new-target-temp" class="form-input" value="22" min="10" max="35" step="0.5">
                </div>
            `;
            break;
        case 'CAMERA':
            fieldsHtml = `
                <div class="form-group">
                    <label class="form-label">Initial Battery Level (%)</label>
                    <input type="number" id="new-battery" class="form-input" value="100" min="0" max="100">
                </div>
            `;
            break;
        case 'WATER_METER':
            fieldsHtml = `
                <div class="form-group">
                    <label class="form-label">Water Source</label>
                    <select id="new-water-source" class="form-select">
                        <option value="main">Main Supply</option>
                        <option value="bathroom">Bathroom</option>
                        <option value="kitchen">Kitchen</option>
                        <option value="garden">Garden/Irrigation</option>
                    </select>
                </div>
            `;
            break;
    }
    
    fieldsContainer.innerHTML = fieldsHtml;
}

async function submitNewDevice(event) {
    event.preventDefault();
    
    const deviceType = document.getElementById('new-device-type').value;
    const deviceId = document.getElementById('new-device-id').value.trim();
    const name = document.getElementById('new-device-name').value.trim();
    const location = document.getElementById('new-device-location').value;
    
    if (!deviceType || !deviceId || !name || !location) {
        showToast('error', 'Error', 'Please fill in all required fields');
        return;
    }
    
    // Build properties based on device type
    const properties = {};
    
    switch (deviceType) {
        case 'BULB':
            properties.brightness = parseInt(document.getElementById('new-brightness')?.value || 100);
            properties.is_on = document.getElementById('new-is-on')?.value === 'true';
            break;
        case 'THERMOSTAT':
            properties.target_temp = parseFloat(document.getElementById('new-target-temp')?.value || 22);
            break;
        case 'CAMERA':
            properties.battery_level = parseInt(document.getElementById('new-battery')?.value || 100);
            break;
        case 'WATER_METER':
            properties.water_source = document.getElementById('new-water-source')?.value || 'main';
            break;
    }
    
    try {
        const response = await fetch('/api/devices', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                device_id: deviceId,
                device_type: deviceType,
                name: name,
                location: location,
                properties: properties
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to create device');
        }
        
        const result = await response.json();
        
        // Add to local state
        state.devices[result.device.device_id] = result.device;
        
        // Refresh UI
        renderDevicesGrid();
        renderDevicesTable();
        renderRooms();
        
        closeAddDeviceModal();
        showToast('success', 'Device Added', `${name} has been added successfully`);
        
    } catch (error) {
        showToast('error', 'Error', error.message);
    }
}

async function deleteDevice(deviceId) {
    if (!confirm('Are you sure you want to delete this device?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/devices/${deviceId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            throw new Error('Failed to delete device');
        }
        
        // Remove from local state
        delete state.devices[deviceId];
        
        // Refresh UI
        renderDevicesGrid();
        renderDevicesTable();
        renderRooms();
        
        closeModal();
        showToast('success', 'Device Deleted', 'Device has been removed');
        
    } catch (error) {
        showToast('error', 'Error', error.message);
    }
}

// Handle device_added WebSocket message
function handleDeviceAdded(device) {
    state.devices[device.device_id] = device;
    renderDevicesGrid();
    renderDevicesTable();
    renderRooms();
}

// Handle device_removed WebSocket message
function handleDeviceRemoved(data) {
    delete state.devices[data.device_id];
    renderDevicesGrid();
    renderDevicesTable();
    renderRooms();
}

// Update WebSocket handler to include new message types
const originalHandleMessage = handleWebSocketMessage;
handleWebSocketMessage = function(message) {
    switch (message.type) {
        case 'device_added':
            handleDeviceAdded(message.data);
            break;
        case 'device_removed':
            handleDeviceRemoved(message.data);
            break;
        default:
            originalHandleMessage(message);
    }
};

// ============================================================================
// Settings & Time Simulation Functions
// ============================================================================

async function toggleExperimental(enabled) {
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ experimental_mode: enabled })
        });
        
        if (response.ok) {
            const card = document.getElementById('time-simulation-card');
            if (card) {
                card.style.display = enabled ? 'block' : 'none';
            }
            showToast('success', 'Settings Updated', enabled ? 'Experimental features enabled' : 'Experimental features disabled');
        }
    } catch (error) {
        showToast('error', 'Error', error.message);
    }
}

async function setTimeMultiplier(multiplier) {
    try {
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ time_multiplier: multiplier })
        });
        
        if (response.ok) {
            // Update button states
            document.querySelectorAll('.time-btn').forEach(btn => {
                btn.classList.toggle('active', parseInt(btn.dataset.multiplier) === multiplier);
            });
            
            const speedEl = document.getElementById('current-speed');
            if (speedEl) speedEl.textContent = multiplier + 'x';
            
            showToast('success', 'Time Speed Changed', `Running at ${multiplier}x speed`);
        }
    } catch (error) {
        showToast('error', 'Error', error.message);
    }
}

async function resetSimulation() {
    if (!confirm('Reset all energy counters and simulated time?')) return;
    
    try {
        const response = await fetch('/api/simulation/reset', { method: 'POST' });
        if (response.ok) {
            showToast('success', 'Simulation Reset', 'All counters have been reset');
        }
    } catch (error) {
        showToast('error', 'Error', error.message);
    }
}

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        const settings = await response.json();
        
        // Update experimental toggle
        const toggle = document.getElementById('experimental-toggle');
        if (toggle) {
            toggle.checked = settings.experimental_mode;
            const card = document.getElementById('time-simulation-card');
            if (card) card.style.display = settings.experimental_mode ? 'block' : 'none';
        }
        
        // Update time multiplier buttons
        document.querySelectorAll('.time-btn').forEach(btn => {
            btn.classList.toggle('active', parseInt(btn.dataset.multiplier) === settings.time_multiplier);
        });
        
        const speedEl = document.getElementById('current-speed');
        if (speedEl) speedEl.textContent = settings.time_multiplier + 'x';
        
    } catch (error) {
        console.error('Failed to load settings:', error);
    }
}

function updateSettingsMetrics(metrics) {
    const elecEl = document.getElementById('settings-elec-kwh');
    if (elecEl) elecEl.textContent = (metrics.electricity_kwh || 0).toFixed(3) + ' kWh';
    
    const gasEl = document.getElementById('settings-gas-kwh');
    if (gasEl) gasEl.textContent = (metrics.gas_kwh || 0).toFixed(3) + ' kWh';
    
    const waterEl = document.getElementById('settings-water-m3');
    if (waterEl) waterEl.textContent = (metrics.water_monthly_m3 || 0).toFixed(2) + ' m³';
    
    const costEl = document.getElementById('settings-total-cost');
    if (costEl) costEl.textContent = (metrics.total_cost || 0).toFixed(2) + ' lei';
    
    const simTimeEl = document.getElementById('simulated-time');
    if (simTimeEl) {
        const hours = metrics.simulated_hours || 0;
        if (hours < 1) {
            simTimeEl.textContent = Math.round(hours * 60) + 'm';
        } else if (hours < 24) {
            simTimeEl.textContent = hours.toFixed(1) + 'h';
        } else {
            simTimeEl.textContent = (hours / 24).toFixed(1) + ' days';
        }
    }
}

// ============================================================================
// Device Configuration Functions
// ============================================================================

async function openDeviceConfig(deviceId) {
    const device = state.devices[deviceId];
    if (!device) return;
    
    try {
        const response = await fetch(`/api/devices/${deviceId}/config`);
        const config = await response.json();
        
        let configHtml = '<div class="config-section"><h4>⚙️ Device Configuration</h4>';
        
        if (device.device_type === 'BULB') {
            configHtml += `
                <div class="config-input-group">
                    <label>Max Power</label>
                    <input type="number" id="config-max-watts" value="${config.max_watts}" min="1" max="${config.configurable_max}" step="1">
                    <span class="unit">W</span>
                </div>
                <div class="config-input-group">
                    <label>Standby Power</label>
                    <input type="number" id="config-standby-watts" value="${config.standby_watts}" min="0" max="5" step="0.1">
                    <span class="unit">W</span>
                </div>
            `;
        } else if (device.device_type === 'THERMOSTAT') {
            configHtml += `
                <div class="config-input-group">
                    <label>Heating Rate</label>
                    <input type="number" id="config-heating-rate" value="${config.heating_kwh_per_degree}" min="0.1" max="5" step="0.1">
                    <span class="unit">kWh/°C/h</span>
                </div>
            `;
        } else if (device.device_type === 'CAMERA') {
            configHtml += `
                <div class="config-input-group">
                    <label>Active Power</label>
                    <input type="number" id="config-active-watts" value="${config.active_watts}" min="1" max="20" step="1">
                    <span class="unit">W</span>
                </div>
                <div class="config-input-group">
                    <label>Recording Power</label>
                    <input type="number" id="config-recording-watts" value="${config.recording_watts}" min="1" max="30" step="1">
                    <span class="unit">W</span>
                </div>
            `;
        }
        
        configHtml += `
            <button class="btn-primary" onclick="saveDeviceConfig('${deviceId}')" style="margin-top: 12px;">Save Configuration</button>
            <button class="btn-danger" onclick="deleteDevice('${deviceId}')" style="margin-left: 8px;">Delete Device</button>
        </div>`;
        
        return configHtml;
    } catch (error) {
        console.error('Failed to load config:', error);
        return '';
    }
}

async function saveDeviceConfig(deviceId) {
    const device = state.devices[deviceId];
    if (!device) return;
    
    const config = {};
    
    if (device.device_type === 'BULB') {
        const maxWatts = document.getElementById('config-max-watts');
        const standbyWatts = document.getElementById('config-standby-watts');
        if (maxWatts) config.max_watts = parseFloat(maxWatts.value);
        if (standbyWatts) config.standby_watts = parseFloat(standbyWatts.value);
    } else if (device.device_type === 'THERMOSTAT') {
        const heatingRate = document.getElementById('config-heating-rate');
        if (heatingRate) config.heating_kwh_per_degree = parseFloat(heatingRate.value);
    } else if (device.device_type === 'CAMERA') {
        const activeWatts = document.getElementById('config-active-watts');
        const recordingWatts = document.getElementById('config-recording-watts');
        if (activeWatts) config.active_watts = parseFloat(activeWatts.value);
        if (recordingWatts) config.recording_watts = parseFloat(recordingWatts.value);
    }
    
    try {
        const response = await fetch(`/api/devices/${deviceId}/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        if (response.ok) {
            showToast('success', 'Configuration Saved', 'Device settings updated');
        }
    } catch (error) {
        showToast('error', 'Error', error.message);
    }
}

// Update the openDeviceModal to include config section
const originalOpenDeviceModal = openDeviceModal;
openDeviceModal = async function(deviceId) {
    const device = state.devices[deviceId];
    if (!device) return;
    
    const modal = document.getElementById('device-modal');
    const modalName = document.getElementById('modal-device-name');
    const modalBody = document.getElementById('modal-body');
    
    modalName.textContent = device.name;
    
    // Get base controls HTML (from original function logic)
    let controlsHtml = getDeviceControlsHtml(deviceId, device);
    
    // Add configuration section
    const configHtml = await openDeviceConfig(deviceId);
    controlsHtml += configHtml;
    
    modalBody.innerHTML = controlsHtml;
    modal.classList.add('active');
};

function getDeviceControlsHtml(deviceId, device) {
    let controlsHtml = '';
    
    if (device.device_type === 'BULB') {
        controlsHtml = `
            <div class="control-group">
                <label class="control-label">Power</label>
                <div class="control-toggle">
                    <button class="toggle-btn ${device.is_on ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'turn_on')">ON</button>
                    <button class="toggle-btn ${!device.is_on ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'turn_off')">OFF</button>
                </div>
            </div>
            <div class="control-group">
                <label class="control-label">Brightness</label>
                <input type="range" class="control-slider" min="0" max="100" value="${device.brightness}" 
                    onchange="sendCommand('${deviceId}', 'set_brightness', {level: parseInt(this.value)})"
                    oninput="document.getElementById('brightness-value').textContent = this.value + '%'">
                <div class="control-value" id="brightness-value">${device.brightness}%</div>
            </div>
            <div class="control-group">
                <label class="control-label">Current Power Draw: ${device.power_draw || 0}W (max: ${device.max_watts || 10}W)</label>
            </div>
        `;
    } else if (device.device_type === 'THERMOSTAT') {
        controlsHtml = `
            <div class="control-group">
                <label class="control-label">Current Temperature</label>
                <div class="control-value">${device.current_temp}°C</div>
            </div>
            <div class="control-group">
                <label class="control-label">Target Temperature</label>
                <input type="range" class="control-slider" min="16" max="30" step="0.5" value="${device.target_temp}"
                    onchange="sendCommand('${deviceId}', 'set_target', {temp: parseFloat(this.value)})"
                    oninput="document.getElementById('target-value').textContent = this.value + '°C'">
                <div class="control-value" id="target-value">${device.target_temp}°C</div>
            </div>
            <div class="control-group">
                <label class="control-label">Mode</label>
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'heat')">🔥 Heat</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'cool')">❄️ Cool</button>
                </div>
            </div>
            <div class="control-group">
                <label class="control-label">Humidity: ${device.humidity}%</label>
            </div>
        `;
    } else if (device.device_type === 'CAMERA') {
        controlsHtml = `
            <div class="control-group">
                <label class="control-label">Battery Level</label>
                <div class="control-value">${device.battery_level}%</div>
            </div>
            <div class="control-group">
                <label class="control-label">Storage Used</label>
                <div class="control-value">${device.storage_percent}%</div>
            </div>
            <div class="control-group">
                <label class="control-label">Actions</label>
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'snapshot')">📸 Snapshot</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'arm')">🔒 Arm</button>
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'disarm')">🔓 Disarm</button>
                </div>
            </div>
            <div class="control-group">
                <div class="control-toggle">
                    <button class="toggle-btn" onclick="sendCommand('${deviceId}', 'charge')">🔌 Start Charging</button>
                    <button class="toggle-btn danger" onclick="sendCommand('${deviceId}', 'clear_storage')">🗑️ Clear Storage</button>
                </div>
            </div>
        `;
    } else if (device.device_type === 'WATER_METER') {
        const valveStatus = device.valve_open ? '🟢 Open' : '🔴 Closed';
        const leakAlert = device.leak_detected ? '<div class="control-group"><div class="leak-warning">🚨 LEAK DETECTED!</div></div>' : '';
        controlsHtml = `
            ${leakAlert}
            <div class="control-group">
                <label class="control-label">Flow Rate</label>
                <div class="control-value">${device.flow_rate || 0} L/min</div>
            </div>
            <div class="control-group">
                <label class="control-label">Today's Usage</label>
                <div class="control-value">${Math.round(device.daily_usage || 0)} liters</div>
            </div>
            <div class="control-group">
                <label class="control-label">Monthly Usage</label>
                <div class="control-value">${Math.round(device.monthly_usage || 0)} L (${((device.monthly_usage || 0) / 1000).toFixed(2)} m³)</div>
            </div>
            <div class="control-group">
                <label class="control-label">Valve Status: ${valveStatus}</label>
                <div class="control-toggle">
                    <button class="toggle-btn ${device.valve_open ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'open_valve')">Open</button>
                    <button class="toggle-btn danger ${!device.valve_open ? 'active' : ''}" onclick="sendCommand('${deviceId}', 'close_valve')">Close</button>
                </div>
            </div>
        `;
    }
    
    return controlsHtml;
}

// Update the handleMetricsUpdate to also update settings page
const originalRenderMetrics = renderMetrics;
renderMetrics = function() {
    originalRenderMetrics();
    updateSettingsMetrics(state.metrics);
};

// Load settings on page load
document.addEventListener('DOMContentLoaded', () => {
    loadSettings();
});
