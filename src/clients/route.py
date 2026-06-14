"""Route client: GPX parsing (primary) and OpenRouteService (fallback).

Key addition: gpx_endpoints() extracts the start and end coordinates directly from a
GPX file so the portal can auto-fill the activity start/end fields.

No Wikiloc integration: Wikiloc has no public API.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import requests

from ..config import get_settings
from ..models import ActivityType, GeoPoint, RouteInfo

_ORS_PROFILE = {
    ActivityType.CYCLING_ROAD: "cycling-road",
    ActivityType.CYCLING_GRAVEL: "cycling-regular",
    ActivityType.CYCLING_MTB: "cycling-mountain",
    ActivityType.HIKING: "foot-hiking",
    ActivityType.TRAIL_RUNNING: "foot-hiking",
    ActivityType.CULTURAL: "foot-walking",
}


@dataclass
class GpxSummary:
    distance_km: float
    ascent_m: float
    descent_m: float
    is_loop: bool
    track_points: int
    start: GeoPoint
    end: GeoPoint
    start_label: str = ""
    end_label: str = ""


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


def _reverse_geocode(point: GeoPoint) -> str:
    """Return a human-readable label from Nominatim, or empty string on failure."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": point.lat, "lon": point.lon, "format": "json", "zoom": 14},
            headers={"User-Agent": get_settings().http_user_agent},
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        addr = data.get("address", {})
        # prefer a named place, trail or road over a long address
        name = (
            data.get("name")
            or addr.get("tourism")
            or addr.get("leisure")
            or addr.get("natural")
            or addr.get("road")
            or addr.get("hamlet")
            or addr.get("village")
            or addr.get("town")
            or addr.get("city")
            or ""
        )
        return name
    except Exception:
        return ""


def parse_gpx(path: str) -> GpxSummary:
    """Parse a GPX file and return a full summary including start/end points with labels."""
    import gpxpy

    with open(path, "r", encoding="utf-8") as fh:
        gpx = gpxpy.parse(fh)

    distance = gpx.length_3d() or gpx.length_2d() or 0.0
    ascent, descent = gpx.get_uphill_downhill()
    points = sum(len(seg.points) for trk in gpx.tracks for seg in trk.segments)

    first_pt = gpx.tracks[0].segments[0].points[0]
    last_pt = gpx.tracks[-1].segments[-1].points[-1]
    start = GeoPoint(lat=first_pt.latitude, lon=first_pt.longitude)
    end = GeoPoint(lat=last_pt.latitude, lon=last_pt.longitude)
    is_loop = _haversine_km(start, end) < 0.3

    start_label = _reverse_geocode(start)
    end_label = _reverse_geocode(end) if not is_loop else start_label

    start.label = start_label
    end.label = end_label if not is_loop else start_label

    return GpxSummary(
        distance_km=round(distance / 1000.0, 2),
        ascent_m=round(ascent, 0),
        descent_m=round(descent, 0),
        is_loop=is_loop,
        track_points=points,
        start=start,
        end=end,
        start_label=start_label,
        end_label=end_label if not is_loop else start_label,
    )


def gpx_endpoints(path: str) -> tuple[GeoPoint, GeoPoint] | None:
    """Extract start and end GeoPoints from a GPX file. Returns None on failure."""
    try:
        summary = parse_gpx(path)
        return summary.start, summary.end
    except Exception:
        return None


def from_gpx(path: str) -> RouteInfo:
    summary = parse_gpx(path)
    return RouteInfo(
        distance_km=summary.distance_km,
        ascent_m=summary.ascent_m,
        descent_m=summary.descent_m,
        is_loop=summary.is_loop,
        source="user_gpx",
        track_points=summary.track_points,
        meeting_points=[summary.start_label or "Start", summary.end_label or "End"],
    )


def from_openrouteservice(
    activity: ActivityType, start: GeoPoint, end: GeoPoint
) -> RouteInfo:
    s = get_settings()
    profile = _ORS_PROFILE.get(activity, "foot-hiking")
    if not s.ors_api_key:
        dist = _haversine_km(start, end)
        return RouteInfo(
            distance_km=round(dist, 2),
            source="straight-line-estimate",
            is_loop=_haversine_km(start, end) < 0.3,
        )
    try:
        r = requests.post(
            f"https://api.openrouteservice.org/v2/directions/{profile}/geojson",
            headers={
                "Authorization": s.ors_api_key,
                "Content-Type": "application/json",
                "User-Agent": s.http_user_agent,
            },
            json={
                "coordinates": [[start.lon, start.lat], [end.lon, end.lat]],
                "elevation": True,
            },
            timeout=40,
        )
        r.raise_for_status()
        feat = r.json()["features"][0]
        summary = feat["properties"]["summary"]
        ascent = feat["properties"].get("ascent", 0.0)
        descent = feat["properties"].get("descent", 0.0)
        coords = feat["geometry"]["coordinates"]
        return RouteInfo(
            distance_km=round(summary.get("distance", 0) / 1000.0, 2),
            ascent_m=round(ascent, 0),
            descent_m=round(descent, 0),
            is_loop=_haversine_km(start, end) < 0.3,
            source="openrouteservice",
            track_points=len(coords),
        )
    except Exception as exc:
        dist = _haversine_km(start, end)
        return RouteInfo(
            distance_km=round(dist, 2), source=f"estimate (ORS error: {exc})"
        )


def resolve_route(
    activity: ActivityType, start: GeoPoint, end: GeoPoint, gpx_path: str | None
) -> RouteInfo:
    if gpx_path:
        try:
            return from_gpx(gpx_path)
        except Exception:
            pass
    return from_openrouteservice(activity, start, end)
