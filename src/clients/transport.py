"""Transport options from the departure origin to the activity start point.

Uses open data sources only:
- OpenRouteService for driving distance and time (requires ORS key; falls back to haversine)
- OSRM public demo API for driving as a no-key fallback
- Transitous / transit routing note (no public EU-wide GTFS routing API without key)
- Nominatim to resolve the origin address if still a string

This module never asserts a specific bus line or train number unless it can ground it in data;
it produces a practical structured summary the human can act on.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import requests

from ..config import get_settings
from ..models import GeoPoint


@dataclass
class TransportOption:
    mode: str  # "car" | "public_transport" | "other"
    summary: str
    distance_km: float = 0.0
    duration_min: float = 0.0
    notes: list[str] = field(default_factory=list)
    map_link: str = ""


def _haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    R = 6371.0
    lat1, lat2 = math.radians(a.lat), math.radians(b.lat)
    dlat = math.radians(b.lat - a.lat)
    dlon = math.radians(b.lon - a.lon)
    h = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    )
    return 2 * R * math.asin(math.sqrt(h))


def _osrm_driving(origin: GeoPoint, dest: GeoPoint) -> tuple[float, float]:
    """OSRM public demo API: returns (distance_km, duration_min). No key required."""
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{origin.lon},{origin.lat};{dest.lon},{dest.lat}"
            f"?overview=false"
        )
        r = requests.get(
            url, headers={"User-Agent": get_settings().http_user_agent}, timeout=20
        )
        r.raise_for_status()
        route = r.json()["routes"][0]
        return round(route["distance"] / 1000.0, 1), round(route["duration"] / 60.0, 0)
    except Exception:
        dist = _haversine_km(origin, dest)
        return round(dist, 1), round(dist / 50.0 * 60.0, 0)


def _ors_driving(origin: GeoPoint, dest: GeoPoint, api_key: str) -> tuple[float, float]:
    try:
        r = requests.post(
            "https://api.openrouteservice.org/v2/directions/driving-car/json",
            headers={
                "Authorization": api_key,
                "Content-Type": "application/json",
                "User-Agent": get_settings().http_user_agent,
            },
            json={"coordinates": [[origin.lon, origin.lat], [dest.lon, dest.lat]]},
            timeout=30,
        )
        r.raise_for_status()
        seg = r.json()["routes"][0]["summary"]
        return round(seg["distance"] / 1000.0, 1), round(seg["duration"] / 60.0, 0)
    except Exception:
        return _osrm_driving(origin, dest)


def _google_maps_link(origin: GeoPoint, dest: GeoPoint, mode: str = "driving") -> str:
    return (
        f"https://www.google.com/maps/dir/?api=1"
        f"&origin={origin.lat},{origin.lon}"
        f"&destination={dest.lat},{dest.lon}"
        f"&travelmode={mode}"
    )


def _transit_link(origin: GeoPoint, dest: GeoPoint) -> str:
    return _google_maps_link(origin, dest, mode="transit")


def get_transport_options(origin: GeoPoint, dest: GeoPoint) -> list[TransportOption]:
    """Return car, public transport and other transport options from origin to dest."""
    s = get_settings()
    options: list[TransportOption] = []

    # 1. Car
    if s.ors_api_key:
        dist_km, dur_min = _ors_driving(origin, dest, s.ors_api_key)
    else:
        dist_km, dur_min = _osrm_driving(origin, dest)
    options.append(
        TransportOption(
            mode="car",
            summary=f"{dist_km} km, approximately {int(dur_min)} minutes by road.",
            distance_km=dist_km,
            duration_min=dur_min,
            notes=[
                "Check parking availability at or near the start point before setting off.",
                "If the route is a loop, parking at the start is your return point.",
            ],
            map_link=_google_maps_link(origin, dest),
        )
    )

    # 2. Public transport
    # There is no single open, keyless EU-wide transit routing API; we use the Google Maps
    # transit deep link so the user gets a live, real-time journey plan.
    straight_km = _haversine_km(origin, dest)
    transit_note = "Tap the link below for live transit options (trains, buses, metro) using Google Maps."
    extra_notes = []
    if straight_km <= 60:
        extra_notes.append(
            "The distance is within typical commuter rail range. Look for Cercanías (Spain), S-Bahn (Germany/Austria), RER (France) or equivalent regional rail services."
        )
    else:
        extra_notes.append(
            "The distance may require an inter-city train or bus. Book in advance for better fares."
        )
    extra_notes.append(
        "If carrying a bicycle, confirm bike carriage policy with the operator before travelling."
    )
    options.append(
        TransportOption(
            mode="public_transport",
            summary=transit_note,
            distance_km=round(straight_km, 1),
            notes=extra_notes,
            map_link=_transit_link(origin, dest),
        )
    )

    # 3. Other options
    other_notes = []
    if straight_km <= 20 and s.ors_api_key:
        # Attempt a cycling route to the start
        try:
            r = requests.post(
                "https://api.openrouteservice.org/v2/directions/cycling-regular/json",
                headers={
                    "Authorization": s.ors_api_key,
                    "Content-Type": "application/json",
                    "User-Agent": s.http_user_agent,
                },
                json={"coordinates": [[origin.lon, origin.lat], [dest.lon, dest.lat]]},
                timeout=30,
            )
            r.raise_for_status()
            seg = r.json()["routes"][0]["summary"]
            cy_km = round(seg["distance"] / 1000.0, 1)
            cy_min = round(seg["duration"] / 60.0, 0)
            other_notes.append(
                f"Cycling to the start: {cy_km} km, approximately {int(cy_min)} minutes. This adds {cy_km} km of road cycling before the main activity."
            )
        except Exception:
            other_notes.append(
                f"Cycling to the start is feasible (approx. {round(straight_km, 1)} km straight line). Use a cycling route planner for a safe road route."
            )
    else:
        other_notes.append(
            "Cycling or e-scooter to the start may be an option if you live nearby."
        )

    other_notes.append(
        "Car sharing (BlaBlaCar, Amovens) can be worth checking for popular trailhead areas, especially for weekend outings."
    )
    other_notes.append(
        "Taxi or ride-hailing to the start can be a practical fallback if public transport does not serve the trailhead."
    )
    options.append(
        TransportOption(
            mode="other",
            summary="Alternative access options.",
            distance_km=round(straight_km, 1),
            notes=other_notes,
            map_link=_google_maps_link(origin, dest, "walking"),
        )
    )

    return options
