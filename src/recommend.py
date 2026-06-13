"""Classical recommendation engine: deterministic, explainable rules over the activity type,
route metrics and weather. Produces an equipment checklist and risk flags with rationale.

This layer is intentionally not driven by the language model, so that safety-relevant advice
is reproducible and auditable.
"""

from __future__ import annotations

from datetime import datetime

from .catalog import base_checklist, is_cycling, is_on_foot
from .models import (
    ActivityInputs,
    EquipmentChecklist,
    Recommendation,
    RiskFlag,
    RouteInfo,
    WeatherPanel,
)


def _duration_hours(inp: ActivityInputs) -> float:
    start = datetime.combine(inp.activity_date, inp.start_time)
    end = datetime.combine(inp.activity_date, inp.end_time)
    hours = (end - start).total_seconds() / 3600.0
    return hours if hours > 0 else 1.0


def recommend(
    inp: ActivityInputs, route: RouteInfo, weather: WeatherPanel
) -> Recommendation:
    checklist: EquipmentChecklist = base_checklist(inp.activity_type)
    flags: list[RiskFlag] = []
    rationale: list[str] = []

    hours = _duration_hours(inp)
    temp_max = weather.temp_max_c if weather.temp_max_c is not None else 18.0
    temp_min = weather.temp_min_c if weather.temp_min_c is not None else 10.0
    wind = weather.wind_kmh or 0.0
    rain = weather.rain_prob_pct or 0.0

    # Hydration and nutrition scaled by duration and heat
    water_litres = round(0.5 * hours + (0.3 if temp_max >= 28 else 0.0), 1)
    checklist.nutrition_hydration.append(f"Water: about {water_litres} litres")
    if hours >= 3:
        checklist.nutrition_hydration.append(
            "Food for a long outing (energy bars, fruit, sandwiches)"
        )
    rationale.append(
        f"Duration estimated at {hours:.1f} hours; water scaled accordingly."
    )

    # Heat
    if temp_max >= 30:
        flags.append(
            RiskFlag(
                level="warning",
                message=f"High heat expected (up to {temp_max:.0f} C). Start early, carry extra water, plan shade.",
            )
        )
        checklist.personal.append("Extra sun protection and electrolytes")
    elif temp_max >= 26:
        flags.append(
            RiskFlag(
                level="caution", message=f"Warm conditions (up to {temp_max:.0f} C)."
            )
        )

    # Cold
    if temp_min <= 3:
        flags.append(
            RiskFlag(
                level="caution",
                message=f"Cold start expected ({temp_min:.0f} C). Pack warm layers.",
            )
        )
        checklist.personal.append("Warm layers and gloves")

    # Rain and snow
    if rain >= 50:
        flags.append(
            RiskFlag(
                level="caution",
                message=f"Rain likely ({rain:.0f}% chance). Pack waterproofs.",
            )
        )
        checklist.personal.append("Waterproof jacket")
    if weather.snow:
        flags.append(
            RiskFlag(
                level="warning",
                message="Snow indicated. Reassess suitability and traction.",
            )
        )

    # Wind, relevant to cycling and exposed routes
    if wind >= 40 and is_cycling(inp.activity_type):
        flags.append(
            RiskFlag(
                level="warning",
                message=f"Strong wind ({wind:.0f} km/h). Crosswinds can be hazardous on a bike.",
            )
        )
    elif wind >= 50:
        flags.append(
            RiskFlag(
                level="caution",
                message=f"Strong wind ({wind:.0f} km/h) on an exposed route.",
            )
        )

    # Distance and elevation for foot and cycling activities
    if route.distance_km:
        rationale.append(
            f"Route distance {route.distance_km} km, ascent {route.ascent_m:.0f} m."
        )
        if is_on_foot(inp.activity_type) and route.distance_km >= 18:
            flags.append(
                RiskFlag(
                    level="caution",
                    message="Long route on foot; ensure pacing, food and a turnaround plan.",
                )
            )
        if is_cycling(inp.activity_type) and route.ascent_m >= 1200:
            flags.append(
                RiskFlag(
                    level="caution",
                    message="Significant climbing; check gearing and fuelling.",
                )
            )

    # Combined high-risk pattern
    if temp_max >= 30 and route.distance_km >= 15 and water_litres < 2:
        flags.append(
            RiskFlag(
                level="warning",
                message="Long, hot route with limited planned water. Increase water and add a refill point.",
            )
        )

    # Late finish needs light
    if inp.end_time.hour >= 19 and is_on_foot(inp.activity_type):
        checklist.personal.append("Headtorch for a late finish")

    if not weather.is_forecast:
        flags.append(
            RiskFlag(
                level="info",
                message="Weather is a seasonal baseline, not a forecast. Re-check nearer the date.",
            )
        )

    return Recommendation(checklist=checklist, risk_flags=flags, rationale=rationale)
