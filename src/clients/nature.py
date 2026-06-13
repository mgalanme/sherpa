"""Biodiversity client using GBIF occurrence records to suggest likely flora and fauna near
the route. Open data with a citation requirement.
"""

from __future__ import annotations

import requests

from ..config import get_settings
from ..models import GeoPoint


def likely_species(
    point: GeoPoint, radius_deg: float = 0.1, limit: int = 40
) -> list[str]:
    s = get_settings()
    params = {
        "decimalLatitude": f"{point.lat - radius_deg},{point.lat + radius_deg}",
        "decimalLongitude": f"{point.lon - radius_deg},{point.lon + radius_deg}",
        "limit": limit,
        "hasCoordinate": "true",
    }
    try:
        r = requests.get(
            "https://api.gbif.org/v1/occurrence/search",
            params=params,
            headers={"User-Agent": s.http_user_agent},
            timeout=30,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception:
        return []

    names: list[str] = []
    seen = set()
    for occ in results:
        name = occ.get("species") or occ.get("scientificName")
        if name and name not in seen:
            seen.add(name)
            names.append(name)
        if len(names) >= 12:
            break
    return names
