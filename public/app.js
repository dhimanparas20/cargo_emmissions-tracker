/**
 * Cargo Emissions Tracker - Frontend JavaScript
 * Handles authentication, route calculation, map visualization, and search history
 */

// API Base URL
const API_BASE_URL = window.location.origin;

// Global variables
let map = null;
let shortestRouteLayer = null;
let efficientRouteLayer = null;
let isLoginMode = true;
let authToken = localStorage.getItem('authToken');

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    initMap();
    setupEventListeners();
    checkAuthStatus();
});

// Initialize Leaflet Map
function initMap() {
    map = L.map('map').setView([20.5937, 78.9629], 4); // Center on India
    
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);
}

// Setup Event Listeners
function setupEventListeners() {
    // Auth form
    document.getElementById('authForm').addEventListener('submit', handleAuth);
    
    // Auth switch (login/register toggle)
    document.getElementById('authSwitch').addEventListener('click', function(e) {
        e.preventDefault();
        toggleAuthMode();
    });
    
    // Route form
    document.getElementById('routeForm').addEventListener('submit', handleRouteCalculation);
}

// Check Authentication Status
function checkAuthStatus() {
    if (authToken) {
        showApp();
        loadSearchHistory();
        updateNavUser();
    } else {
        showAuth();
    }
}

// Toggle between Login and Register modes
function toggleAuthMode() {
    isLoginMode = !isLoginMode;
    
    const title = document.getElementById('authTitle');
    const button = document.getElementById('authButton');
    const switchText = document.getElementById('authSwitchText');
    const switchLink = document.getElementById('authSwitch');
    const nameField = document.getElementById('nameField');
    
    if (isLoginMode) {
        title.textContent = 'Login';
        button.textContent = 'Login';
        switchText.textContent = "Don't have an account?";
        switchLink.textContent = 'Register';
        nameField.style.display = 'none';
    } else {
        title.textContent = 'Register';
        button.textContent = 'Register';
        switchText.textContent = 'Already have an account?';
        switchLink.textContent = 'Login';
        nameField.style.display = 'block';
    }
    
    // Clear error
    document.getElementById('authError').classList.add('hidden');
}

// Validate password strength
function validatePassword(password) {
    const errors = [];
    
    if (password.length < 8) {
        errors.push("At least 8 characters");
    }
    if (!/[A-Z]/.test(password)) {
        errors.push("One uppercase letter");
    }
    if (!/[a-z]/.test(password)) {
        errors.push("One lowercase letter");
    }
    if (!/\d/.test(password)) {
        errors.push("One digit");
    }
    if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
        errors.push("One special character");
    }
    
    return {
        isValid: errors.length === 0,
        errors: errors
    };
}

// Handle Authentication (Login/Register)
async function handleAuth(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const fullName = document.getElementById('fullName').value;
    
    const button = document.getElementById('authButton');
    const errorDiv = document.getElementById('authError');
    
    // Validate password for registration
    if (!isLoginMode) {
        const passwordCheck = validatePassword(password);
        if (!passwordCheck.isValid) {
            errorDiv.innerHTML = '<strong>Password requirements:</strong><br>' + 
                passwordCheck.errors.map(e => '• ' + e).join('<br>');
            errorDiv.classList.remove('hidden');
            return;
        }
    }
    
    button.innerHTML = '<span class="loading"></span>';
    button.disabled = true;
    
    try {
        let response;
        
        if (isLoginMode) {
            // Login
            response = await fetch(`${API_BASE_URL}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
        } else {
            // Register
            response = await fetch(`${API_BASE_URL}/auth/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ full_name: fullName, email, password })
            });
        }
        
        const data = await response.json();
        
        if (response.ok) {
            if (isLoginMode && data.token) {
                authToken = data.token;
                localStorage.setItem('authToken', authToken);
                showApp();
                loadSearchHistory();
                updateNavUser();
            } else if (!isLoginMode) {
                showSuccess('Registration successful! Please login.');
                toggleAuthMode();
            }
        } else {
            showAuthError(data.detail || 'Authentication failed');
        }
    } catch (error) {
        showAuthError('Network error. Please try again.');
        console.error('Auth error:', error);
    } finally {
        button.innerHTML = isLoginMode ? 'Login' : 'Register';
        button.disabled = false;
    }
}

// Show Authentication Error
function showAuthError(message) {
    const errorDiv = document.getElementById('authError');
    errorDiv.textContent = message;
    errorDiv.classList.remove('hidden');
}

// Show Success Message
function showSuccess(message) {
    alert(message); // Simple alert for now
}

// Show App Container
function showApp() {
    document.getElementById('authContainer').classList.add('hidden');
    document.getElementById('appContainer').classList.remove('hidden');
    setTimeout(() => map.invalidateSize(), 100);
}

// Show Auth Container
function showAuth() {
    document.getElementById('appContainer').classList.add('hidden');
    document.getElementById('authContainer').classList.remove('hidden');
}

// Update Navigation User
async function updateNavUser() {
    try {
        const response = await fetch(`${API_BASE_URL}/user/me`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const user = await response.json();
            const navUser = document.getElementById('navUser');
            navUser.innerHTML = `
                <span class="navbar-text me-3">
                    <i class="fas fa-user me-1"></i>${user.full_name}
                </span>
                <button class="btn btn-outline-danger btn-sm" onclick="logout()">
                    <i class="fas fa-sign-out-alt me-1"></i>Logout
                </button>
            `;
        }
    } catch (error) {
        console.error('Error fetching user:', error);
    }
}

// Logout
async function logout() {
    try {
        // Call logout endpoint to invalidate token on server
        await fetch(`${API_BASE_URL}/auth/logout`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
    } catch (error) {
        console.error('Logout error:', error);
    } finally {
        // Clear local storage and redirect to login
        authToken = null;
        localStorage.removeItem('authToken');
        showAuth();
        document.getElementById('navUser').innerHTML = '';
    }
}

// Handle Route Calculation
async function handleRouteCalculation(e) {
    e.preventDefault();
    
    const origin = document.getElementById('origin').value;
    const destination = document.getElementById('destination').value;
    const weight = parseFloat(document.getElementById('weight').value);
    const transportMode = document.getElementById('transportMode').value;
    
    const button = e.target.querySelector('button[type="submit"]');
    const originalText = button.innerHTML;
    button.innerHTML = '<span class="loading"></span> Calculating...';
    button.disabled = true;
    
    try {
        const response = await fetch(`${API_BASE_URL}/api/routes/compare`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                origin,
                destination,
                weight_kg: weight
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data);
            displayRoutesOnMap(data);
            loadSearchHistory(); // Refresh history
        } else {
            alert(data.detail || 'Failed to calculate routes');
        }
    } catch (error) {
        alert('Network error. Please try again.');
        console.error('Route calculation error:', error);
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

// Display Results
function displayResults(data) {
    const resultsCard = document.getElementById('resultsCard');
    const resultsBody = document.getElementById('resultsBody');
    
    const shortest = data.shortest_route;
    const efficient = data.most_efficient_route;
    const comparison = data.comparison;
    
    resultsBody.innerHTML = `
        <div class="row">
            <div class="col-12">
                <div class="stat-card mb-3">
                    <div class="stat-value">
                        <i class="fas fa-leaf me-2"></i>${comparison.emission_savings_percent}%
                    </div>
                    <div class="stat-label">CO2 Emissions Saved</div>
                </div>
            </div>
        </div>
        
        <div class="row">
            <div class="col-6">
                <h6 class="route-line-shortest">
                    <i class="fas fa-route me-1"></i>Shortest Route
                </h6>
                <ul class="list-unstyled small">
                    <li><strong>Mode:</strong> ${shortest.transport_mode}</li>
                    <li><strong>Distance:</strong> ${shortest.distance_km} km</li>
                    <li><strong>Duration:</strong> ${shortest.duration_minutes} min</li>
                    <li><strong>Emissions:</strong> ${shortest.emissions_kg_co2} kg CO2</li>
                </ul>
            </div>
            <div class="col-6">
                <h6 class="route-line-efficient">
                    <i class="fas fa-leaf me-1"></i>Most Efficient
                </h6>
                <ul class="list-unstyled small">
                    <li><strong>Mode:</strong> ${efficient.transport_mode}</li>
                    <li><strong>Distance:</strong> ${efficient.distance_km} km</li>
                    <li><strong>Duration:</strong> ${efficient.duration_minutes} min</li>
                    <li><strong>Emissions:</strong> ${efficient.emissions_kg_co2} kg CO2</li>
                </ul>
            </div>
        </div>
        
        <div class="alert alert-success mt-3 mb-0">
            <small>
                <i class="fas fa-info-circle me-1"></i>
                You can save <strong>${comparison.emission_savings_kg_co2} kg CO2</strong> 
                by choosing the ${efficient.transport_mode} route!
            </small>
        </div>
    `;
    
    resultsCard.classList.remove('hidden');
}

// Display Routes on Map
function displayRoutesOnMap(data) {
    // Clear existing layers
    if (shortestRouteLayer) map.removeLayer(shortestRouteLayer);
    if (efficientRouteLayer) map.removeLayer(efficientRouteLayer);
    
    const shortest = data.shortest_route;
    const efficient = data.most_efficient_route;
    
    // Convert geometry to Leaflet format (swap coordinates)
    const shortestCoords = shortest.geometry.map(coord => [coord[1], coord[0]]);
    const efficientCoords = efficient.geometry.map(coord => [coord[1], coord[0]]);
    
    // Draw shortest route (red)
    shortestRouteLayer = L.polyline(shortestCoords, {
        color: '#e74c3c',
        weight: 4,
        opacity: 0.8,
        dashArray: '10, 10'
    }).addTo(map);
    
    // Draw efficient route (green)
    efficientRouteLayer = L.polyline(efficientCoords, {
        color: '#27ae60',
        weight: 4,
        opacity: 0.8
    }).addTo(map);
    
    // Add markers for origin and destination
    const originCoord = shortestCoords[0];
    const destCoord = shortestCoords[shortestCoords.length - 1];
    
    L.marker(originCoord)
        .addTo(map)
        .bindPopup(`<b>Origin:</b> ${shortest.origin}`)
        .openPopup();
    
    L.marker(destCoord)
        .addTo(map)
        .bindPopup(`<b>Destination:</b> ${shortest.destination}`);
    
    // Fit bounds to show both routes
    const group = new L.featureGroup([shortestRouteLayer, efficientRouteLayer]);
    map.fitBounds(group.getBounds().pad(0.1));
}

// Load Search History
async function loadSearchHistory() {
    try {
        const response = await fetch(`${API_BASE_URL}/api/history/`, {
            headers: { 'Authorization': `Bearer ${authToken}` }
        });
        
        if (response.ok) {
            const data = await response.json();
            displaySearchHistory(data);
        }
    } catch (error) {
        console.error('Error loading history:', error);
    }
}

// Display Search History
function displaySearchHistory(data) {
    const historyBody = document.getElementById('historyBody');
    
    if (!data.items || data.items.length === 0) {
        historyBody.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-history fa-3x mb-3"></i>
                <p>No search history yet</p>
            </div>
        `;
        return;
    }
    
    const historyHTML = data.items.map(item => {
        const date = new Date(item.created_at * 1000).toLocaleString();
        const routeTypeClass = item.route_type === 'efficient' ? 'text-success' : 'text-danger';
        const routeTypeIcon = item.route_type === 'efficient' ? 'fa-leaf' : 'fa-route';
        
        return `
            <div class="history-item">
                <div class="d-flex justify-content-between align-items-start">
                    <div>
                        <h6 class="mb-1">
                            <i class="fas fa-map-marker-alt text-danger me-1"></i>${item.origin}
                            <i class="fas fa-arrow-right mx-2 text-muted"></i>
                            <i class="fas fa-map-marker-alt text-success me-1"></i>${item.destination}
                        </h6>
                        <small class="text-muted">
                            ${date} • ${item.weight_kg} kg • ${item.transport_mode}
                        </small>
                    </div>
                    <span class="badge ${item.route_type === 'efficient' ? 'bg-success' : 'bg-danger'}">
                        <i class="fas ${routeTypeIcon} me-1"></i>${item.route_type}
                    </span>
                </div>
                <div class="row mt-2 text-center">
                    <div class="col-4">
                        <small class="text-muted">Distance</small>
                        <div class="fw-bold">${item.distance_km} km</div>
                    </div>
                    <div class="col-4">
                        <small class="text-muted">Emissions</small>
                        <div class="fw-bold ${routeTypeClass}">${item.emissions_kg_co2} kg CO2</div>
                    </div>
                    <div class="col-4">
                        <small class="text-muted">Tons CO2</small>
                        <div class="fw-bold">${item.emissions_tons_co2}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    historyBody.innerHTML = historyHTML;
}

// Export functions for global access
window.logout = logout;
window.loadSearchHistory = loadSearchHistory;
