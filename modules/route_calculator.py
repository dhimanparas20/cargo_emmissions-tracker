"""
Route Calculation Module

This module provides route calculation using the OpenRouteService API.
OpenRouteService is a free, open-source routing service based on OpenStreetMap.

Features:
- Calculate shortest route (distance optimized)
- Calculate routes for different transport modes
- Get route geometry for map visualization
- Geocode addresses to coordinates

Note: You can get a free API key at https://openrouteservice.org/dev/#/signup
"""

import os
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import requests
from dotenv import load_dotenv

from modules.logger import get_logger

load_dotenv()
logger = get_logger("ROUTE_CALCULATOR")

# OpenRouteService API configuration
ORS_API_KEY = os.getenv("ORS_API_KEY", "")
ORS_BASE_URL = "https://api.openrouteservice.org"

# Transport mode mapping to OpenRouteService profiles
ORS_PROFILES = {
    "land": "driving-car",  # Car/truck routing
    "sea": "driving-car",  # Fallback to land (ORS doesn't support sea)
    "air": "driving-car",  # Fallback to land (ORS doesn't support air)
}

# Default coordinates for fallback (in case geocoding fails)
DEFAULT_COORDS = {
    "london": [-0.1276, 51.5074],
    "new_york": [-74.0060, 40.7128],
    "singapore": [103.8198, 1.3521],
    "mumbai": [72.8777, 19.0760],
}


@dataclass
class RoutePoint:
    """A geographic point with coordinates and address."""

    address: str
    longitude: float
    latitude: float


@dataclass
class RouteSegment:
    """A segment of a route."""

    instruction: str
    distance_meters: float
    duration_seconds: float


@dataclass
class RouteResult:
    """Complete route calculation result."""

    origin: RoutePoint
    destination: RoutePoint
    distance_km: float
    duration_minutes: float
    geometry: List[List[float]]  # List of [longitude, latitude] coordinates
    segments: List[RouteSegment]
    transport_mode: str


def geocode_address(address: str) -> Optional[RoutePoint]:
    """
    Geocode an address to get coordinates using OpenRouteService.

    Args:
        address: Address string to geocode

    Returns:
        RoutePoint: Point with coordinates or None if geocoding fails
    """
    try:
        url = f"{ORS_BASE_URL}/geocode/search"
        headers = {"Authorization": ORS_API_KEY, "Accept": "application/json"}
        params = {"api_key": ORS_API_KEY, "text": address, "size": 1}

        # Try ORS geocoding first
        if ORS_API_KEY:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data.get("features"):
                    feature = data["features"][0]
                    coords = feature["geometry"]["coordinates"]
                    return RoutePoint(
                        address=address, longitude=coords[0], latitude=coords[1]
                    )

        # Fallback to Nominatim (OpenStreetMap) if ORS fails or no API key
        fallback_url = "https://nominatim.openstreetmap.org/search"
        fallback_params = {"q": address, "format": "json", "limit": 1}
        headers = {"User-Agent": "CargoEmissionsTracker/1.0"}

        response = requests.get(
            fallback_url, params=fallback_params, headers=headers, timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            if data:
                return RoutePoint(
                    address=address,
                    longitude=float(data[0]["lon"]),
                    latitude=float(data[0]["lat"]),
                )

        logger.warning(f"Geocoding failed for address: {address}")
        return None

    except Exception as e:
        logger.error(f"Error geocoding address '{address}': {e}")
        return None


def calculate_route(
    origin: RoutePoint, destination: RoutePoint, transport_mode: str = "land"
) -> Optional[RouteResult]:
    """
    Calculate route between two points using OpenRouteService.

    Args:
        origin: Starting point
        destination: Ending point
        transport_mode: Mode of transport (land, sea, air)

    Returns:
        RouteResult: Complete route information or None if calculation fails
    """
    try:
        # Map transport mode to ORS profile
        profile = ORS_PROFILES.get(transport_mode, "driving-car")

        url = f"{ORS_BASE_URL}/v2/directions/{profile}"
        headers = {"Authorization": ORS_API_KEY, "Content-Type": "application/json"}

        body = {
            "coordinates": [
                [origin.longitude, origin.latitude],
                [destination.longitude, destination.latitude],
            ],
            "instructions": True,
            "geometry": True,
        }

        # Try ORS API if key is available
        if ORS_API_KEY:
            response = requests.post(url, json=body, headers=headers, timeout=15)

            if response.status_code == 200:
                data = response.json()
                route = data["routes"][0]
                segment = route["segments"][0]

                # Decode geometry (simplified - just use coordinates)
                geometry = route.get("geometry", {}).get("coordinates", [])
                if not geometry:
                    # Create straight line if no geometry available
                    geometry = [
                        [origin.longitude, origin.latitude],
                        [destination.longitude, destination.latitude],
                    ]

                # Parse segments
                segments = []
                for step in segment.get("steps", []):
                    segments.append(
                        RouteSegment(
                            instruction=step.get("instruction", ""),
                            distance_meters=step.get("distance", 0),
                            duration_seconds=step.get("duration", 0),
                        )
                    )

                return RouteResult(
                    origin=origin,
                    destination=destination,
                    distance_km=round(segment["distance"] / 1000, 2),
                    duration_minutes=round(segment["duration"] / 60, 1),
                    geometry=geometry,
                    segments=segments,
                    transport_mode=transport_mode,
                )

        # Fallback: Calculate great circle distance (Haversine formula)
        logger.info(f"Using fallback distance calculation for {transport_mode}")
        return _calculate_fallback_route(origin, destination, transport_mode)

    except Exception as e:
        logger.error(f"Error calculating route: {e}")
        return _calculate_fallback_route(origin, destination, transport_mode)


def _calculate_fallback_route(
    origin: RoutePoint, destination: RoutePoint, transport_mode: str
) -> RouteResult:
    """
    Calculate fallback route using Haversine formula (great circle distance).
    Used when ORS API is unavailable or fails.

    Args:
        origin: Starting point
        destination: Ending point
        transport_mode: Mode of transport

    Returns:
        RouteResult: Calculated route with estimated values
    """
    import math

    # Haversine formula to calculate great circle distance
    R = 6371  # Earth's radius in kilometers

    lat1 = math.radians(origin.latitude)
    lat2 = math.radians(destination.latitude)
    delta_lat = math.radians(destination.latitude - origin.latitude)
    delta_lon = math.radians(destination.longitude - origin.longitude)

    a = math.sin(delta_lat / 2) * math.sin(delta_lat / 2) + math.cos(lat1) * math.cos(
        lat2
    ) * math.sin(delta_lon / 2) * math.sin(delta_lon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance_km = R * c

    # Estimate duration based on transport mode
    speeds = {"land": 60, "sea": 25, "air": 800}
    speed = speeds.get(transport_mode, 60)
    duration_hours = distance_km / speed

    # Create simple straight-line geometry
    geometry = [
        [origin.longitude, origin.latitude],
        [destination.longitude, destination.latitude],
    ]

    return RouteResult(
        origin=origin,
        destination=destination,
        distance_km=round(distance_km, 2),
        duration_minutes=round(duration_hours * 60, 1),
        geometry=geometry,
        segments=[
            RouteSegment(
                instruction=f"Direct route from {origin.address} to {destination.address}",
                distance_meters=distance_km * 1000,
                duration_seconds=duration_hours * 3600,
            )
        ],
        transport_mode=transport_mode,
    )


def calculate_shortest_route(
    origin_address: str, destination_address: str, transport_mode: str = "land"
) -> Optional[RouteResult]:
    """
    Calculate the shortest route between two addresses.

    Args:
        origin_address: Starting address
        destination_address: Destination address
        transport_mode: Mode of transport

    Returns:
        RouteResult: Shortest route or None if calculation fails
    """
    # Geocode addresses
    origin = geocode_address(origin_address)
    destination = geocode_address(destination_address)

    if not origin or not destination:
        logger.error(
            f"Failed to geocode addresses: {origin_address} -> {destination_address}"
        )
        return None

    # Calculate route
    route = calculate_route(origin, destination, transport_mode)

    if route:
        logger.info(
            f"Shortest route calculated: {route.distance_km}km, "
            f"{route.duration_minutes}min via {transport_mode}"
        )

    return route


def get_available_transport_modes() -> List[str]:
    """Get list of available transport modes."""
    return ["land", "sea", "air"]
