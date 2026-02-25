from typing import Optional

from bson import ObjectId
from fastapi import APIRouter, Depends, status, HTTPException, Query
from fastapi.responses import JSONResponse

from models.route_model import PaginatedSearchHistory
from modules.entity import search_history_db
from modules.jwt_util import require_token
from modules.logger import get_logger

search_history_router = APIRouter()
logger = get_logger("SEARCH_HISTORY_ROUTER")


def parse_date(date_str: Optional[str]) -> Optional[float]:
    """Parse date string to timestamp."""
    if not date_str:
        return None
    try:
        from datetime import datetime

        dt = datetime.strptime(date_str, "%Y-%m-%d")
        return dt.timestamp()
    except:
        return None


@search_history_router.get(
    "/",
    response_model=PaginatedSearchHistory,
    summary="Get search history",
    description="Get paginated search history for the authenticated user with optional filters.",
    response_class=JSONResponse,
)
async def get_search_history(
    transport_mode: Optional[str] = Query(None, description="Filter by transport mode"),
    route_type: Optional[str] = Query(
        None, description="Filter by route type (shortest/efficient/comparison)"
    ),
    start_date: Optional[str] = Query(
        None, description="Filter by start date (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="Filter by end date (YYYY-MM-DD)"
    ),
    limit: int = Query(20, ge=1, le=100, description="Number of items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    user=Depends(require_token),
):
    """
    Get search history for the authenticated user.

    Supports filtering by transport mode, route type, and date range.
    Results are paginated.
    """
    try:
        user_id = user.get("id")

        # Build filter
        filter_query = {"user_id": user_id}

        if transport_mode:
            filter_query["transport_mode"] = transport_mode

        if route_type:
            filter_query["route_type"] = route_type

        # Date range filter
        if start_date or end_date:
            date_filter = {}
            start_ts = parse_date(start_date) if start_date else None
            end_ts = parse_date(end_date) if end_date else None
            if start_ts:
                date_filter["$gte"] = start_ts
            if end_ts:
                date_filter["$lte"] = end_ts
            if date_filter:
                filter_query["created_at"] = date_filter

        # Get total count
        total = search_history_db.count(filter_query)

        # Get paginated results
        results = search_history_db.filter(
            filter=filter_query,
            show_id=True,
            sort=[("created_at", -1)],  # Descending (newest first)
            limit=limit,
            skip=offset,
        )

        return JSONResponse(
            {
                "items": results,
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + limit) < total,
            }
        )

    except Exception as e:
        logger.error(f"Error fetching search history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@search_history_router.get(
    "/{history_id}",
    summary="Get search history item",
    description="Get a specific search history item by ID.",
    response_class=JSONResponse,
)
async def get_search_history_item(history_id: str, user=Depends(require_token)):
    """Get a specific search history item."""
    try:
        user_id = user.get("id")

        # Get item
        item = search_history_db.get_by_id(_id=history_id)

        if not item:
            raise HTTPException(status_code=404, detail="Search history item not found")

        # Check ownership
        if item.get("user_id") != user_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to view this item"
            )

        return JSONResponse(item)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching search history item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@search_history_router.delete(
    "/{history_id}",
    summary="Delete search history item",
    description="Delete a specific search history item.",
    response_class=JSONResponse,
)
async def delete_search_history_item(history_id: str, user=Depends(require_token)):
    """Delete a specific search history item."""
    try:
        user_id = user.get("id")

        # Convert string ID to ObjectId
        try:
            obj_id = ObjectId(history_id)
        except:
            raise HTTPException(status_code=400, detail="Invalid history ID format")

        # Get item to check ownership
        item = search_history_db.get_by_id(_id=obj_id)

        if not item:
            raise HTTPException(status_code=404, detail="Search history item not found")

        # Check ownership
        if item.get("user_id") != user_id:
            raise HTTPException(
                status_code=403, detail="Not authorized to delete this item"
            )

        # Delete item
        success = search_history_db.delete_one(filter={"_id": obj_id})

        if success:
            return JSONResponse(
                {"msg": "Search history item deleted successfully", "id": history_id}
            )
        else:
            raise HTTPException(status_code=400, detail="Failed to delete item")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting search history item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@search_history_router.delete(
    "/",
    summary="Clear search history",
    description="Clear all search history for the authenticated user.",
    response_class=JSONResponse,
)
async def clear_search_history(user=Depends(require_token)):
    """Clear all search history for the authenticated user."""
    try:
        user_id = user.get("id")

        # Delete all items for user
        result = search_history_db.delete(filter={"user_id": user_id})

        return JSONResponse(
            {"msg": "Search history cleared successfully", "deleted_count": result}
        )

    except Exception as e:
        logger.error(f"Error clearing search history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@search_history_router.get(
    "/stats/summary",
    summary="Get search statistics",
    description="Get summary statistics of user's search history.",
    response_class=JSONResponse,
)
async def get_search_stats(user=Depends(require_token)):
    """Get search statistics for the authenticated user."""
    try:
        user_id = user.get("id")

        # Get all user searches
        results = search_history_db.filter(filter={"user_id": user_id}, limit=10000)

        if not results:
            return JSONResponse(
                {
                    "total_searches": 0,
                    "total_emissions_kg": 0,
                    "avg_distance_km": 0,
                    "most_used_mode": None,
                    "most_common_route": None,
                }
            )

        # Calculate statistics
        total_searches = len(results)
        total_emissions = sum(item.get("emissions_kg_co2", 0) for item in results)
        avg_distance = (
            sum(item.get("distance_km", 0) for item in results) / total_searches
        )

        # Most used transport mode
        mode_counts = {}
        for item in results:
            mode = item.get("transport_mode", "unknown")
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
        most_used_mode = (
            max(mode_counts.items(), key=lambda x: x[1])[0] if mode_counts else None
        )

        # Most common route
        route_counts = {}
        for item in results:
            route_key = f"{item.get('origin')} -> {item.get('destination')}"
            route_counts[route_key] = route_counts.get(route_key, 0) + 1
        most_common_route = (
            max(route_counts.items(), key=lambda x: x[1])[0] if route_counts else None
        )

        return JSONResponse(
            {
                "total_searches": total_searches,
                "total_emissions_kg_co2": round(total_emissions, 2),
                "avg_distance_km": round(avg_distance, 2),
                "most_used_mode": most_used_mode,
                "most_common_route": most_common_route,
            }
        )

    except Exception as e:
        logger.error(f"Error calculating search stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
