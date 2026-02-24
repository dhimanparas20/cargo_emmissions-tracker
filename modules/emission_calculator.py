"""
Carbon Emission Calculation Module

This module calculates carbon emissions for cargo transportation based on:
- Distance (km)
- Weight (kg)
- Transport mode (land, sea, air)

Emission Factors (kg CO2 per ton-km):
- Land (Truck): 0.062 kg CO2 / ton-km
- Sea (Container ship): 0.016 kg CO2 / ton-km
- Air (Cargo aircraft): 0.602 kg CO2 / ton-km

Sources:
- Based on typical industry averages and EPA/IEA emission factors
- These are simplified factors for demonstration purposes
"""

from enum import Enum
from typing import Dict, Tuple, List
from dataclasses import dataclass
from modules.logger import get_logger

logger = get_logger("EMISSION_CALCULATOR")


class TransportMode(str, Enum):
    """Transport modes for cargo shipment."""

    LAND = "land"
    SEA = "sea"
    AIR = "air"


# Emission factors in kg CO2 per ton-kilometer
# Sources: Based on typical industry averages
EMISSION_FACTORS = {
    TransportMode.LAND: 0.062,  # Truck transportation
    TransportMode.SEA: 0.016,  # Container ship
    TransportMode.AIR: 0.602,  # Cargo aircraft
}

# Average speeds for different modes (km/h) - for time estimation
AVERAGE_SPEEDS = {
    TransportMode.LAND: 60,  # Truck average speed
    TransportMode.SEA: 25,  # Container ship average speed
    TransportMode.AIR: 800,  # Cargo aircraft average speed
}

# Cost factors (relative cost per km)
COST_FACTORS = {
    TransportMode.LAND: 1.0,  # Baseline
    TransportMode.SEA: 0.3,  # Cheapest
    TransportMode.AIR: 8.0,  # Most expensive
}


@dataclass
class EmissionResult:
    """Result of emission calculation."""

    transport_mode: TransportMode
    distance_km: float
    weight_kg: float
    emissions_kg_co2: float
    emissions_tons_co2: float
    estimated_time_hours: float
    estimated_cost_relative: float


def calculate_emissions(
    distance_km: float, weight_kg: float, transport_mode: TransportMode
) -> EmissionResult:
    """
    Calculate carbon emissions for cargo transportation.

    Formula: emissions = distance (km) × weight (tons) × emission_factor (kg CO2/ton-km)

    Args:
        distance_km: Distance in kilometers
        weight_kg: Weight of cargo in kilograms
        transport_mode: Mode of transportation (land, sea, air)

    Returns:
        EmissionResult: Complete emission calculation result
    """
    # Convert weight from kg to tons
    weight_tons = weight_kg / 1000

    # Get emission factor for the transport mode
    emission_factor = EMISSION_FACTORS.get(
        transport_mode, EMISSION_FACTORS[TransportMode.LAND]
    )

    # Calculate emissions in kg CO2
    emissions_kg = distance_km * weight_tons * emission_factor

    # Convert to tons CO2
    emissions_tons = emissions_kg / 1000

    # Estimate time based on average speed
    avg_speed = AVERAGE_SPEEDS.get(transport_mode, 60)
    estimated_time = distance_km / avg_speed if avg_speed > 0 else 0

    # Calculate relative cost
    cost_factor = COST_FACTORS.get(transport_mode, 1.0)
    estimated_cost = distance_km * cost_factor

    result = EmissionResult(
        transport_mode=transport_mode,
        distance_km=distance_km,
        weight_kg=weight_kg,
        emissions_kg_co2=round(emissions_kg, 2),
        emissions_tons_co2=round(emissions_tons, 4),
        estimated_time_hours=round(estimated_time, 1),
        estimated_cost_relative=round(estimated_cost, 2),
    )

    logger.info(
        f"Calculated emissions for {transport_mode.value}: "
        f"{distance_km}km, {weight_kg}kg = {emissions_kg:.2f} kg CO2"
    )

    return result


def calculate_emissions_for_all_modes(
    distance_km: float, weight_kg: float
) -> Dict[TransportMode, EmissionResult]:
    """
    Calculate emissions for all transport modes.

    Args:
        distance_km: Distance in kilometers
        weight_kg: Weight of cargo in kilograms

    Returns:
        Dict[TransportMode, EmissionResult]: Emissions for all modes
    """
    results = {}
    for mode in TransportMode:
        results[mode] = calculate_emissions(distance_km, weight_kg, mode)
    return results


def get_most_efficient_mode(
    distance_km: float, weight_kg: float
) -> Tuple[TransportMode, EmissionResult]:
    """
    Determine the most carbon-efficient transport mode.

    Args:
        distance_km: Distance in kilometers
        weight_kg: Weight of cargo in kilograms

    Returns:
        Tuple[TransportMode, EmissionResult]: Most efficient mode and its result
    """
    all_emissions = calculate_emissions_for_all_modes(distance_km, weight_kg)

    # Find mode with lowest emissions
    most_efficient = min(all_emissions.items(), key=lambda x: x[1].emissions_kg_co2)

    logger.info(
        f"Most efficient mode for {distance_km}km, {weight_kg}kg: "
        f"{most_efficient[0].value} ({most_efficient[1].emissions_kg_co2:.2f} kg CO2)"
    )

    return most_efficient


def get_emission_factor_info() -> Dict[str, Dict[str, float]]:
    """
    Get information about emission factors used.

    Returns:
        Dict with emission factors, speeds, and cost factors
    """
    return {
        "emission_factors_kg_co2_per_ton_km": {
            mode.value: factor for mode, factor in EMISSION_FACTORS.items()
        },
        "average_speeds_km_per_hour": {
            mode.value: speed for mode, speed in AVERAGE_SPEEDS.items()
        },
        "cost_factors_relative": {
            mode.value: cost for mode, cost in COST_FACTORS.items()
        },
    }
