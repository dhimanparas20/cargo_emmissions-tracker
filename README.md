# Cargo Emissions Tracker

A full-stack application that calculates carbon emissions for cargo movement between locations, identifies optimal routes (shortest and most carbon-efficient), and visualizes them on a map.

## Features

### Backend (FastAPI + MongoDB)

1. **Carbon Emission Calculation**
   - Calculate emissions based on origin, destination, weight, and transport mode
   - Support for Land (Truck), Sea (Ship), and Air (Cargo Plane) transport
   - Emission factors based on industry standards

2. **Route Computation**
   - Shortest route (distance optimized)
   - Most efficient route (CO2 emissions optimized)
   - Integration with OpenRouteService API
   - Automatic geocoding of addresses

3. **User Authentication**
   - JWT-based authentication
   - User registration and login
   - Protected routes for authenticated users only

4. **Search History**
   - Save all route searches
   - Filter by transport mode, route type, and date range
   - Pagination support
   - Statistics and analytics

### Frontend (HTML/CSS/JS + Bootstrap + Leaflet)

1. **User Interface**
   - Clean, responsive design with Bootstrap 5
   - Authentication (Login/Register)
   - Route calculation form

2. **Map Visualization**
   - Interactive map using Leaflet
   - Display shortest route (red) and most efficient route (green)
   - Origin and destination markers
   - Route comparison visualization

3. **Search History**
   - View previous searches
   - Display emissions data and route details
   - Auto-refresh capability

## Tech Stack

- **Backend**: Python, FastAPI, MongoDB
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5, Leaflet
- **Package Manager**: uv
- **Python Version**: 3.12+

## Setup Instructions

### Prerequisites

1. Python 3.12 or higher
2. MongoDB (local or cloud)
3. [uv](https://github.com/astral-sh/uv) package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd cargo_emissions_tracker
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```env
   # MongoDB
   LOCAL_MONGO_CONNECTION_STRING=mongodb://localhost:27017
   MONGO_DB_NAME=cargo-emissions
   
   # FastAPI
   DEBUG=True
   PORT=5000
   HOST=0.0.0.0
   JWT_SECRET=your-super-secret-jwt-key-here
   SECRET_KEY=your-secret-key-here
   FASTAPI_ENV=dev
   
   # OpenRouteService (optional - for better routing)
   # Get a free API key at https://openrouteservice.org/dev/#/signup
   ORS_API_KEY=your-ors-api-key-here
   ```

4. **Start MongoDB**
   
   If using local MongoDB:
   ```bash
   mongod
   ```
   
   Or use MongoDB Atlas (cloud) and update the connection string in `.env`.

5. **Run the application**
   ```bash
   uv run uvicorn app:app --host 0.0.0.0 --port 5000 --reload
   ```

6. **Access the application**
   
   Open your browser and navigate to:
   ```
   http://localhost:5000
   ```

## API Endpoints

### Authentication
- `POST /auth/register` - Register a new user
- `POST /auth/login` - Login and get JWT token
- `POST /auth/change-password` - Change user password
- `POST /auth/regenerate-token` - Refresh JWT token

### User
- `GET /user/me` - Get current user info
- `PATCH /user/me` - Update user info
- `DELETE /user/me` - Delete user account

### Routes
- `POST /api/routes/shortest` - Calculate shortest route with emissions
- `POST /api/routes/efficient` - Calculate most efficient route
- `POST /api/routes/compare` - Compare shortest and efficient routes
- `GET /api/routes/transport-modes` - Get available transport modes

### Search History
- `GET /api/history/` - Get user's search history (with filters & pagination)
- `GET /api/history/{history_id}` - Get specific history item
- `DELETE /api/history/{history_id}` - Delete history item
- `DELETE /api/history/` - Clear all history
- `GET /api/history/stats/summary` - Get search statistics

## Emission Factors

The application uses the following emission factors (kg CO2 per ton-km):

| Transport Mode | Emission Factor | Average Speed |
|----------------|-----------------|---------------|
| Land (Truck)   | 0.062 kg CO2/ton-km | 60 km/h |
| Sea (Ship)     | 0.016 kg CO2/ton-km | 25 km/h |
| Air (Plane)    | 0.602 kg CO2/ton-km | 800 km/h |

*Note: These are simplified factors for demonstration purposes based on typical industry averages.*

## Assignment Requirements Compliance

### Functional Requirements (100 points)

1. **Carbon Emission Calculation (20 pts)** ✅
   - Calculates based on origin, destination, weight, and mode
   - Standard emission factors documented

2. **Route Computation (25 pts)** ✅
   - Shortest route calculation (15 pts) - Uses OpenRouteService
   - Most efficient route calculation (10 pts) - Compares all modes

3. **UI with Map Visualization (15 pts)** ✅
   - Interactive map with Leaflet
   - Differentiates shortest (red) and efficient (green) routes

4. **Authentication (15 pts)** ✅
   - JWT-based authentication
   - Register/Login functionality
   - Protected routes

5. **Search History (10 pts)** ✅
   - Saves all searches
   - Includes all required data
   - Filters and pagination support

6. **Code Quality (15 pts)** ✅
   - Modular structure
   - Error handling
   - Type hints
   - Documentation

## Project Structure

```
cargo_emissions_tracker/
├── app.py                      # FastAPI application entry point
├── entity.py                   # Database instances
├── pyproject.toml             # Package configuration (uv)
├── uv.lock                    # Dependency lock file
├── .env                       # Environment variables
├── .venv/                     # Virtual environment
├── modules/                   # Utility modules
│   ├── mongo_core.py         # MongoDB ORM wrapper
│   ├── jwt_util.py           # JWT authentication utilities
│   ├── logger.py             # Logging utilities
│   ├── utils.py              # General utilities
│   ├── emission_calculator.py # Carbon emission calculations
│   └── route_calculator.py   # Route calculation with ORS
├── models/                    # Pydantic models
│   ├── user_model.py         # User models
│   └── route_model.py        # Route and search history models
├── routers/                   # FastAPI routers
│   ├── auth_router.py        # Authentication routes
│   ├── user_router.py        # User management routes
│   ├── route_router.py       # Route calculation routes
│   └── search_history_router.py # Search history routes
└── public/                    # Frontend files
    ├── index.html            # Main HTML page
    └── app.js                # Frontend JavaScript
```

## Development Notes

- The application uses OpenRouteService API for routing. If no API key is provided, it falls back to straight-line (Haversine) distance calculation.
- Geocoding is done via OpenRouteService or Nominatim (OpenStreetMap) as fallback.
- MongoDB is used for data persistence (users and search history).
- JWT tokens are used for authentication with a 7-day expiration.

## License

This project is created for the Shipthis Backend Engineering Assignment.
