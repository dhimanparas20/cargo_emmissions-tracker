from fastapi import APIRouter, Depends, status, HTTPException
from fastapi.responses import JSONResponse

from models.route_model import (
    RouteRequest,
    RouteResponse,
    CompareRoutesRequest,
    CompareRoutesResponse,
)
from modules.emission_calculator import (
    calculate_emissions,
    get_most_efficient_mode,
    TransportMode,
)
from modules.entity import search_history_db
from modules.jwt_util import require_token
from modules.logger import get_logger
from modules.route_calculator import (
    calculate_shortest_route,
    get_available_transport_modes,
)
from modules.utils import get_timestamp

route_router = APIRouter()
logger = get_logger("ROUTE_ROUTER")


def _route_result_to_response(
    route_result, emission_result, route_type: str
) -> RouteResponse:
    """Convert route and emission results to response model."""
    return RouteResponse(
        origin=route_result.origin.address,
        destination=route_result.destination.address,
        distance_km=route_result.distance_km,
        duration_minutes=route_result.duration_minutes,
        weight_kg=emission_result.weight_kg,
        transport_mode=route_result.transport_mode,
        emissions_kg_co2=emission_result.emissions_kg_co2,
        emissions_tons_co2=emission_result.emissions_tons_co2,
        estimated_time_hours=emission_result.estimated_time_hours,
        geometry=route_result.geometry,
        route_type=route_type,
    )


def _save_search_history(
    user_id: str,
    origin: str,
    destination: str,
    weight_kg: float,
    transport_mode: str,
    distance_km: float,
    emissions_kg_co2: float,
    emissions_tons_co2: float,
    route_type: str,
):
    """Save search to history."""
    try:
        history_entry = {
            "user_id": user_id,
            "origin": origin,
            "destination": destination,
            "weight_kg": weight_kg,
            "transport_mode": transport_mode,
            "distance_km": distance_km,
            "emissions_kg_co2": emissions_kg_co2,
            "emissions_tons_co2": emissions_tons_co2,
            "route_type": route_type,
            "created_at": get_timestamp(),
            "updated_at": get_timestamp(),
        }
        search_history_db.insert(history_entry)
    except Exception as e:
        logger.error(f"Failed to save search history: {e}")


@route_router.post(
    "/shortest",
    response_model=RouteResponse,
    summary="Calculate shortest route",
    description="Calculate the shortest route (distance optimized) between two locations with emissions.",
    response_class=JSONResponse,
)
async def calculate_shortest(request: RouteRequest, user=Depends(require_token)):
    """
    Calculate the shortest route between origin and destination.

    Returns route details with emissions calculation.
    """
    try:
        # Calculate route
        route_result = calculate_shortest_route(
            request.origin, request.destination, request.transport_mode.value
        )

        if not route_result:
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate route. Please check the addresses.",
            )

        # Calculate emissions
        emission_result = calculate_emissions(
            route_result.distance_km, request.weight_kg, request.transport_mode
        )

        # Save to history
        _save_search_history(
            user_id=user.get("id"),
            origin=request.origin,
            destination=request.destination,
            weight_kg=request.weight_kg,
            transport_mode=request.transport_mode.value,
            distance_km=route_result.distance_km,
            emissions_kg_co2=emission_result.emissions_kg_co2,
            emissions_tons_co2=emission_result.emissions_tons_co2,
            route_type="shortest",
        )

        response = _route_result_to_response(route_result, emission_result, "shortest")
        return JSONResponse(response.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating shortest route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@route_router.post(
    "/efficient",
    response_model=RouteResponse,
    summary="Calculate most efficient route",
    description="Calculate the most carbon-efficient route between two locations.",
    response_class=JSONResponse,
)
async def calculate_efficient(request: RouteRequest, user=Depends(require_token)):
    """
    Calculate the most carbon-efficient route between origin and destination.

    Returns route details with emissions calculation using the most efficient transport mode.
    """
    try:
        # First get route with the requested mode to get distance
        route_result = calculate_shortest_route(
            request.origin, request.destination, request.transport_mode.value
        )

        if not route_result:
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate route. Please check the addresses.",
            )

        # Find most efficient transport mode
        efficient_mode, efficient_emissions = get_most_efficient_mode(
            route_result.distance_km, request.weight_kg
        )

        # If most efficient mode is different, recalculate route
        if efficient_mode != request.transport_mode:
            route_result = calculate_shortest_route(
                request.origin, request.destination, efficient_mode.value
            )
            if not route_result:
                route_result = calculate_shortest_route(
                    request.origin, request.destination, request.transport_mode.value
                )
            else:
                # Recalculate emissions with the actual efficient route's distance
                efficient_emissions = calculate_emissions(
                    route_result.distance_km, request.weight_kg, efficient_mode
                )

        if not route_result:
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate route. Please check the addresses.",
            )

        # Save to history
        _save_search_history(
            user_id=user.get("id"),
            origin=request.origin,
            destination=request.destination,
            weight_kg=request.weight_kg,
            transport_mode=efficient_mode.value,
            distance_km=route_result.distance_km,
            emissions_kg_co2=efficient_emissions.emissions_kg_co2,
            emissions_tons_co2=efficient_emissions.emissions_tons_co2,
            route_type="efficient",
        )

        response = _route_result_to_response(
            route_result, efficient_emissions, "efficient"
        )
        return JSONResponse(response.model_dump())

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating efficient route: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@route_router.post(
    "/compare",
    response_model=CompareRoutesResponse,
    summary="Compare routes",
    description="Compare shortest and most efficient routes side by side.",
    response_class=JSONResponse,
)
async def compare_routes(request: CompareRoutesRequest, user=Depends(require_token)):
    """
    Compare shortest and most efficient routes.

    Returns both routes with comparison metrics.
    """
    try:
        # Calculate shortest route using requested transport mode (convert enum to string)
        transport_mode_str = request.transport_mode.value
        shortest_route_result = calculate_shortest_route(
            request.origin, request.destination, transport_mode_str
        )

        if not shortest_route_result:
            raise HTTPException(
                status_code=400,
                detail="Failed to calculate route. Please check the addresses.",
            )

        # Calculate emissions for shortest route using requested transport mode
        shortest_emissions = calculate_emissions(
            shortest_route_result.distance_km, request.weight_kg, request.transport_mode
        )

        # Get most efficient mode
        efficient_mode, efficient_emissions = get_most_efficient_mode(
            shortest_route_result.distance_km, request.weight_kg
        )

        # Calculate route for efficient mode only if it's different from shortest
        if efficient_mode != request.transport_mode:
            efficient_route_result = calculate_shortest_route(
                request.origin, request.destination, efficient_mode.value
            )
            if efficient_route_result:
                # Recalculate emissions using the actual efficient route's distance
                efficient_emissions = calculate_emissions(
                    efficient_route_result.distance_km,
                    request.weight_kg,
                    efficient_mode,
                )
            else:
                # Fallback to shortest route result if efficient route fails
                efficient_route_result = shortest_route_result
        else:
            # If efficient mode is same as shortest, use the same result
            efficient_route_result = shortest_route_result

        # Create responses
        shortest_response = _route_result_to_response(
            shortest_route_result, shortest_emissions, "shortest"
        )

        efficient_response = _route_result_to_response(
            efficient_route_result, efficient_emissions, "efficient"
        )

        # Calculate comparison
        emission_savings = (
            shortest_emissions.emissions_kg_co2 - efficient_emissions.emissions_kg_co2
        )
        emission_savings_percent = (
            (emission_savings / shortest_emissions.emissions_kg_co2 * 100)
            if shortest_emissions.emissions_kg_co2 > 0
            else 0
        )

        comparison = {
            "emission_savings_kg_co2": round(emission_savings, 2),
            "emission_savings_percent": round(emission_savings_percent, 1),
            "recommended_mode": efficient_mode.value,
            "distance_difference_km": round(
                efficient_route_result.distance_km - shortest_route_result.distance_km,
                2,
            ),
        }

        # Save ONE record to history with comparison data
        # Store the user's requested transport mode
        _save_search_history(
            user_id=user.get("id"),
            origin=request.origin,
            destination=request.destination,
            weight_kg=request.weight_kg,
            transport_mode=transport_mode_str,  # User's requested mode
            distance_km=shortest_route_result.distance_km,
            emissions_kg_co2=shortest_emissions.emissions_kg_co2,
            emissions_tons_co2=shortest_emissions.emissions_tons_co2,
            route_type="comparison",  # This was a comparison search
        )

        return JSONResponse(
            {
                "shortest_route": shortest_response.model_dump(),
                "most_efficient_route": efficient_response.model_dump(),
                "comparison": comparison,
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing routes: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@route_router.get(
    "/transport-modes",
    summary="Get transport modes",
    description="Get list of available transport modes with emission factors.",
    response_class=JSONResponse,
)
async def get_transport_modes():
    """Get available transport modes and their emission factors."""
    try:
        from modules.emission_calculator import get_emission_factor_info

        modes = get_available_transport_modes()
        factors = get_emission_factor_info()

        return JSONResponse(
            {
                "modes": modes,
                "emission_factors": factors["emission_factors_kg_co2_per_ton_km"],
                "speeds": factors["average_speeds_km_per_hour"],
                "costs": factors["cost_factors_relative"],
            }
        )
    except Exception as e:
        logger.error(f"Error getting transport modes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
