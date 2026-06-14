"""Classical recommendation engine: deterministic, explainable rules.

All user-visible strings are now looked up from i18n.c() so that the checklist,
risk flags and rationale respect the active language.
"""

from __future__ import annotations

from datetime import datetime

from .catalog import base_checklist, is_cycling, is_on_foot
from .i18n import c
from .models import (
    ActivityInputs,
    EquipmentChecklist,
    Recommendation,
    RiskFlag,
    RouteInfo,
    WeatherPanel,
)

# Map the English strings produced by base_checklist() to their i18n keys.
# This allows the catalog to remain a single source of truth for which items
# belong to which activity while i18n handles the display text.
_PERSONAL_KEY_MAP: dict[str, str] = {
    "Helmet": "eq_helmet",
    "Cycling jersey and shorts": "eq_cycling_jersey",
    "Sunglasses": "eq_sunglasses",
    "Gloves": "eq_gloves",
    "Layered clothing": "eq_layered",
    "Protective gloves": "eq_prot_gloves",
    "Knee protection (optional)": "eq_knee_prot",
    "Hiking boots": "eq_hiking_boots",
    "Sun hat": "eq_sun_hat",
    "Trekking poles (optional)": "eq_poles",
    "Trail shoes": "eq_trail_shoes",
    "Breathable layers": "eq_breathable",
    "Cap": "eq_cap",
    "Running vest": "eq_running_vest",
    "Court shoes": "eq_court_shoes",
    "Sportswear": "eq_sportswear",
    "Wristbands": "eq_wristbands",
    "Harness": "eq_harness",
    "Climbing shoes": "eq_climbing_shoes",
    "Belay device": "eq_belay",
    "Buoyancy aid": "eq_buoyancy",
    "Quick-dry clothing": "eq_quickdry",
    "Water shoes": "eq_water_shoes",
    "Dry bag": "eq_dry_bag",
    "Comfortable footwear": "eq_comfortable_shoes",
    "Weather-appropriate clothing": "eq_weather_clothing",
}

_ACTIVITY_KEY_MAP: dict[str, str] = {
    "Bike pre-ride check: tyres and pressures, brakes, drivetrain": "eq_bike_check",
    "Spare tube, pump, multitool": "eq_spare_tube",
    "Front and rear lights": "eq_lights",
    "Tubeless plugs or spare tube, pump, multitool": "eq_tubeless",
    "Lights": "eq_lights",
    "Spare tube, pump, multitool, chain link": "eq_chain_link",
    "Backpack sized to duration": "eq_backpack",
    "Navigation (map or GPS)": "eq_navigation",
    "First-aid kit": "eq_first_aid",
    "Headtorch for late finishes": "eq_headtorch",
    "Navigation": "eq_navigation",
    "Basic first aid": "eq_first_aid",
    "Whistle": "eq_whistle",
    "Lightweight pack": "eq_lightweight_pack",
    "Racket(s)": "eq_racket",
    "Suitable tennis balls": "eq_tennis_balls",
    "Confirm court booking": "eq_court_booking",
    "Padel racket(s)": "eq_padel_racket",
    "Padel balls": "eq_padel_balls",
    "Rope and quickdraws": "eq_rope",
    "Guidebook or topo": "eq_guidebook",
    "Partner check protocol": "eq_partner_check",
    "Kayak and paddle check": "eq_kayak_check",
    "Bilge pump and sponge": "eq_bilge_pump",
    "Waterproof phone case": "eq_waterproof_case",
    "Tickets or booking": "eq_tickets",
    "Check opening hours": "eq_opening_hours",
    "Plan around closures or events": "eq_closures",
}


def _translate_list(items: list[str], key_map: dict[str, str], lang: str) -> list[str]:
    return [c(key_map[item], lang) if item in key_map else item for item in items]


def _duration_hours(inp: ActivityInputs) -> float:
    start = datetime.combine(inp.activity_date, inp.start_time)
    end = datetime.combine(inp.activity_date, inp.end_time)
    hours = (end - start).total_seconds() / 3600.0
    return hours if hours > 0 else 1.0


def recommend(
    inp: ActivityInputs, route: RouteInfo, weather: WeatherPanel, lang: str = "en"
) -> Recommendation:
    base = base_checklist(inp.activity_type)
    personal = _translate_list(base.personal, _PERSONAL_KEY_MAP, lang)
    activity_specific = _translate_list(base.activity_specific, _ACTIVITY_KEY_MAP, lang)
    flags: list[RiskFlag] = []
    rationale: list[str] = []

    hours = _duration_hours(inp)
    temp_max = weather.temp_max_c if weather.temp_max_c is not None else 18.0
    temp_min = weather.temp_min_c if weather.temp_min_c is not None else 10.0
    wind = weather.wind_kmh or 0.0
    rain = weather.rain_prob_pct or 0.0

    water_litres = round(0.5 * hours + (0.3 if temp_max >= 28 else 0.0), 1)
    nutrition: list[str] = [c("eq_water_template", lang, n=water_litres)]
    if hours >= 3:
        nutrition.append(c("eq_food_long", lang))

    if temp_max >= 30:
        flags.append(
            RiskFlag(
                level="warning",
                message=c("risk_heat_warning", lang, t=f"{temp_max:.0f}"),
            )
        )
        personal.append(c("eq_sun_protection", lang))
    elif temp_max >= 26:
        flags.append(
            RiskFlag(
                level="caution",
                message=c("risk_heat_caution", lang, t=f"{temp_max:.0f}"),
            )
        )

    if temp_min <= 3:
        flags.append(
            RiskFlag(level="caution", message=c("risk_cold", lang, t=f"{temp_min:.0f}"))
        )
        personal.append(c("eq_warm_layers", lang))

    if rain >= 50:
        flags.append(
            RiskFlag(level="caution", message=c("risk_rain", lang, p=f"{rain:.0f}"))
        )
        personal.append(c("eq_waterproof", lang))

    if weather.snow:
        flags.append(RiskFlag(level="warning", message=c("risk_snow", lang)))

    if wind >= 40 and is_cycling(inp.activity_type):
        flags.append(
            RiskFlag(
                level="warning", message=c("risk_wind_cycling", lang, w=f"{wind:.0f}")
            )
        )
    elif wind >= 50:
        flags.append(
            RiskFlag(
                level="caution", message=c("risk_wind_exposed", lang, w=f"{wind:.0f}")
            )
        )

    if route.distance_km:
        if is_on_foot(inp.activity_type) and route.distance_km >= 18:
            flags.append(RiskFlag(level="caution", message=c("risk_long_foot", lang)))
        if is_cycling(inp.activity_type) and route.ascent_m >= 1200:
            flags.append(RiskFlag(level="caution", message=c("risk_climbing", lang)))

    if temp_max >= 30 and route.distance_km >= 15 and water_litres < 2:
        flags.append(RiskFlag(level="warning", message=c("risk_hot_long", lang)))

    if inp.end_time.hour >= 19 and is_on_foot(inp.activity_type):
        personal.append(c("eq_headtorch_late", lang))

    if not weather.is_forecast:
        flags.append(RiskFlag(level="info", message=c("risk_no_forecast", lang)))

    checklist = EquipmentChecklist(
        personal=personal,
        activity_specific=activity_specific,
        nutrition_hydration=nutrition,
    )
    return Recommendation(checklist=checklist, risk_flags=flags, rationale=rationale)
