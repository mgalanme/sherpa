"""Route client: parses a user-supplied GPX file (the primary pattern, since Wikiloc has no
public API) and, when no GPX is provided, generates a route with OpenRouteService on
OpenStreetMap data.
"""

from __future__ import annotations

import math

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


def _haversine_km(a: GeoPoint, b: GeoPoint) -> float:
    r = 6371.0
    p1, p2 = math.radians(a.lat), math.radians(b.lat)
    dphi = math.radians(b.lat - a.lat)
    dlmb = math.radians(b.lon - a.lon)
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def from_gpx(path: str) -> RouteInfo:
    import gpxpy

    with open(path, "r", encoding="utf-8") as fh:
        gpx = gpxpy.parse(fh)
    distance = gpx.length_3d() or gpx.length_2d() or 0.0
    ascent, descent = gpx.get_uphill_downhill()
    points = sum(len(seg.points) for trk in gpx.tracks for seg in trk.segments)
    is_loop = False
    try:
        first = gpx.tracks[0].segments[0].points[0]
        last = gpx.tracks[-1].segments[-1].points[-1]
        is_loop = (
            _haversine_km(
                GeoPoint(lat=first.latitude, lon=first.longitude),
                GeoPoint(lat=last.latitude, lon=last.longitude),
            )
            < 0.3
        )
    except Exception:
        pass
    return RouteInfo(
        distance_km=round(distance / 1000.0, 2),
        ascent_m=round(ascent, 0),
        descent_m=round(descent, 0),
        is_loop=is_loop,
        source="user_gpx",
        track_points=points,
    )


def from_openrouteservice(
    activity: ActivityType, start: GeoPoint, end: GeoPoint
) -> RouteInfo:
    s = get_settings()
    profile = _ORS_PROFILE.get(activity, "foot-hiking")
    if not s.ors_api_key:
        # Fall back to a straight-line estimate when no key is configured.
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
    except Exception as exc:  # noqa: BLE001
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
