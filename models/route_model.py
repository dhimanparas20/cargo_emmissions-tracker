from typing import Optional
from pydantic import BaseModel, Field
from modules.utils import get_timestamp
from modules.emission_calculator import TransportMode


class RouteRequest(BaseModel):
    """Request model for route calculation."""

    origin: str = Field(..., min_length=2, max_length=200, description="Origin address")
    destination: str = Field(
        ..., min_length=2, max_length=200, description="Destination address"
    )
    weight_kg: float = Field(
        ..., gt=0, le=1000000, description="Cargo weight in kilograms"
    )
    transport_mode: TransportMode = Field(
        default=TransportMode.LAND, description="Transport mode"
    )


class RouteResponse(BaseModel):
    """Response model for route calculation."""

    origin: str
    destination: str
    distance_km: float
    duration_minutes: float
    weight_kg: float
    transport_mode: str
    emissions_kg_co2: float
    emissions_tons_co2: float
    estimated_time_hours: float
    geometry: list  # List of [longitude, latitude] coordinates
    route_type: str  # "shortest" or "efficient"


class CompareRoutesRequest(BaseModel):
    """Request to compare shortest and most efficient routes."""

    origin: str = Field(..., min_length=2, max_length=200)
    destination: str = Field(..., min_length=2, max_length=200)
    weight_kg: float = Field(..., gt=0, le=1000000)


class CompareRoutesResponse(BaseModel):
    """Response with both shortest and most efficient routes."""

    shortest_route: RouteResponse
    most_efficient_route: RouteResponse
    comparison: dict  # Comparison metrics


class SearchHistoryItem(BaseModel):
    """Model for a search history item."""

    id: Optional[str] = None
    user_id: str
    origin: str
    destination: str
    weight_kg: float
    transport_mode: str
    distance_km: float
    emissions_kg_co2: float
    emissions_tons_co2: float
    route_type: str  # "shortest" or "efficient"
    created_at: float = Field(default_factory=lambda: get_timestamp())
    updated_at: float = Field(default_factory=lambda: get_timestamp())


class SearchHistoryCreate(BaseModel):
    """Model for creating search history entry."""

    user_id: str
    origin: str
    destination: str
    weight_kg: float
    transport_mode: str
    distance_km: float
    emissions_kg_co2: float
    emissions_tons_co2: float
    route_type: str


class SearchHistoryFilter(BaseModel):
    """Filter options for search history."""

    transport_mode: Optional[str] = None
    route_type: Optional[str] = None
    start_date: Optional[float] = None
    end_date: Optional[float] = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class PaginatedSearchHistory(BaseModel):
    """Paginated search history response."""

    items: list
    total: int
    limit: int
    offset: int
    has_more: bool
