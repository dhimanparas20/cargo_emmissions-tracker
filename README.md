# Cargo Emissions Tracker API

A FastAPI-based REST API for calculating carbon emissions and optimal routes for cargo transportation.

## Features

- **Carbon Emission Calculation** - Calculate CO2 emissions based on distance, weight, and transport mode (land, sea, air)
- **Route Calculation** - Find shortest and most efficient routes between locations
- **User Authentication** - JWT-based auth with registration, login, and token invalidation
- **Search History** - Save and retrieve past route searches with filtering and pagination

## Tech Stack

- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Authentication**: JWT (PyJWT)
- **API Integration**: OpenRouteService (with Nominatim fallback)

## Prerequisites

- Python 3.10+
- MongoDB (local or Docker)
- OpenRouteService API key (optional, for better geocoding)

## Installation

1. **Clone the repository**
   ```bash
   cd cargo_emmissions-tracker
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file:
   ```env
   MONGO_CONNECTION_STRING=mongodb://localhost:27017
   MONGO_DB_NAME=cargo-emissions
   JWT_SECRET=your-secret-key
   JWT_EXPIRY_DAYS=7
   ORS_API_KEY=your-openrouteservice-api-key
   DEBUG=True
   ```

4. **Start MongoDB**
   ```bash
   docker compose up -d
   ```

5. **Run the server**
   ```bash
   uv run fastapi dev app.py --port 5000

   or

   uv run uvicorn app:app --port 5000
   ```

## API Endpoints

### Authentication (`/auth`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/register` | Register a new user |
| POST | `/auth/login` | Login and get JWT token |
| POST | `/auth/logout` | Invalidate current token |
| POST | `/auth/change-password` | Change user password |

### User (`/user`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/user/me` | Get current user profile |
| PUT | `/user/update` | Update user profile |

### Routes (`/api/routes`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/routes/shortest` | Calculate shortest route |
| POST | `/api/routes/efficient` | Calculate most emissions-efficient route |
| POST | `/api/routes/compare` | Compare shortest vs efficient routes |

### Search History (`/api/history`)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/history` | Get user's search history |
| DELETE | `/api/history/{id}` | Delete a history entry |

## Emission Factors

| Transport Mode | kg CO2 per ton-km | Avg Speed (km/h) |
|---------------|-------------------|------------------|
| Land (Truck) | 0.062 | 60 |
| Sea (Ship) | 0.016 | 25 |
| Air (Cargo) | 0.602 | 800 |

## Example Usage

### Register User
```bash
curl -X POST http://localhost:5001/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "John Doe",
    "email": "john@example.com",
    "password": "SecurePass123!"
  }'
```

### Calculate Shortest Route
```bash
curl -X POST http://localhost:5001/api/routes/shortest \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "London, UK",
    "destination": "Paris, France",
    "weight_kg": 1000,
    "transport_mode": "land"
  }'
```

## Project Structure

```
├── app.py                  # Main FastAPI application
├── compose.yml             # Docker Compose for MongoDB
├── models/
│   ├── user_model.py       # Pydantic models for users
│   └── route_model.py      # Pydantic models for routes
├── modules/
│   ├── mongo_core.py       # MongoDB utility class
│   ├── jwt_util.py         # JWT authentication utilities
│   ├── emission_calculator.py  # CO2 emission calculations
│   ├── route_calculator.py     # Route calculation logic
│   ├── entity.py           # Database collection instances
│   ├── logger.py           # Logging configuration
│   └── utils.py            # Utility functions
└── routers/
    ├── auth_router.py      # Authentication endpoints
    ├── user_router.py      # User management endpoints
    ├── route_router.py     # Route calculation endpoints
    └── search_history_router.py  # History endpoints
```

## License

MIT
