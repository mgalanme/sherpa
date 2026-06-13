"""Activity taxonomy and the deterministic, explainable equipment rules.

This is classical (rules-based) AI: transparent, testable and auditable, which is the right
choice for safety-relevant recommendations. The language model is never used to decide kit.
"""

from __future__ import annotations

from .models import ActivityType, EquipmentChecklist

ACTIVITY_LABELS: dict[ActivityType, str] = {
    ActivityType.CYCLING_ROAD: "Road cycling",
    ActivityType.CYCLING_GRAVEL: "Gravel cycling",
    ActivityType.CYCLING_MTB: "Mountain biking",
    ActivityType.HIKING: "Hiking and trekking",
    ActivityType.TRAIL_RUNNING: "Trail running",
    ActivityType.TENNIS: "Tennis",
    ActivityType.PADEL: "Padel",
    ActivityType.CLIMBING: "Climbing",
    ActivityType.KAYAKING: "Kayaking and paddle",
    ActivityType.CULTURAL: "Cultural outing",
}

_CYCLING = {
    ActivityType.CYCLING_ROAD,
    ActivityType.CYCLING_GRAVEL,
    ActivityType.CYCLING_MTB,
}
_FOOT = {ActivityType.HIKING, ActivityType.TRAIL_RUNNING}
_RACKET = {ActivityType.TENNIS, ActivityType.PADEL}

# Base personal kit per activity family
_BASE_PERSONAL: dict[ActivityType, list[str]] = {
    ActivityType.CYCLING_ROAD: [
        "Helmet",
        "Cycling jersey and shorts",
        "Sunglasses",
        "Gloves",
    ],
    ActivityType.CYCLING_GRAVEL: ["Helmet", "Layered clothing", "Sunglasses", "Gloves"],
    ActivityType.CYCLING_MTB: [
        "Helmet",
        "Protective gloves",
        "Knee protection (optional)",
        "Sunglasses",
    ],
    ActivityType.HIKING: [
        "Hiking boots",
        "Layered clothing",
        "Sun hat",
        "Trekking poles (optional)",
    ],
    ActivityType.TRAIL_RUNNING: [
        "Trail shoes",
        "Breathable layers",
        "Cap",
        "Running vest",
    ],
    ActivityType.TENNIS: ["Court shoes", "Sportswear", "Cap", "Wristbands"],
    ActivityType.PADEL: ["Court shoes", "Sportswear", "Cap", "Wristbands"],
    ActivityType.CLIMBING: ["Helmet", "Harness", "Climbing shoes", "Belay device"],
    ActivityType.KAYAKING: [
        "Buoyancy aid",
        "Quick-dry clothing",
        "Water shoes",
        "Dry bag",
    ],
    ActivityType.CULTURAL: ["Comfortable footwear", "Weather-appropriate clothing"],
}

_ACTIVITY_SPECIFIC: dict[ActivityType, list[str]] = {
    ActivityType.CYCLING_ROAD: [
        "Bike pre-ride check: tyres and pressures, brakes, drivetrain",
        "Spare tube, pump, multitool",
        "Front and rear lights",
    ],
    ActivityType.CYCLING_GRAVEL: [
        "Bike check: tyres, brakes, drivetrain",
        "Tubeless plugs or spare tube, pump, multitool",
        "Lights",
    ],
    ActivityType.CYCLING_MTB: [
        "Bike check: suspension, tyres, brakes",
        "Spare tube, pump, multitool, chain link",
        "Lights",
    ],
    ActivityType.HIKING: [
        "Backpack sized to duration",
        "Navigation (map or GPS)",
        "First-aid kit",
        "Headtorch for late finishes",
    ],
    ActivityType.TRAIL_RUNNING: [
        "Lightweight pack",
        "Navigation",
        "Basic first aid",
        "Whistle",
    ],
    ActivityType.TENNIS: [
        "Racket(s)",
        "Suitable tennis balls",
        "Confirm court booking",
    ],
    ActivityType.PADEL: ["Padel racket(s)", "Padel balls", "Confirm court booking"],
    ActivityType.CLIMBING: [
        "Rope and quickdraws",
        "Guidebook or topo",
        "Partner check protocol",
    ],
    ActivityType.KAYAKING: [
        "Kayak and paddle check",
        "Bilge pump and sponge",
        "Waterproof phone case",
    ],
    ActivityType.CULTURAL: [
        "Tickets or booking",
        "Check opening hours",
        "Plan around closures or events",
    ],
}


def base_checklist(activity: ActivityType) -> EquipmentChecklist:
    return EquipmentChecklist(
        personal=list(_BASE_PERSONAL.get(activity, [])),
        activity_specific=list(_ACTIVITY_SPECIFIC.get(activity, [])),
        nutrition_hydration=[],
    )


def is_cycling(activity: ActivityType) -> bool:
    return activity in _CYCLING


def is_on_foot(activity: ActivityType) -> bool:
    return activity in _FOOT


def is_racket(activity: ActivityType) -> bool:
    return activity in _RACKET
