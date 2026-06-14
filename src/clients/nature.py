"""Biodiversity client using GBIF + iNaturalist + OpenStreetMap nature areas.

Sources:
- GBIF occurrence records (species sightings, CC-BY)
- iNaturalist observations API (research-grade only, CC-BY-NC)
- OpenStreetMap Overpass: protected areas, nature reserves, national parks via area tags
"""

from __future__ import annotations

import requests

from ..config import get_settings
from ..models import GeoPoint


def _gbif_species(
    point: GeoPoint, radius_deg: float = 0.1, limit: int = 40
) -> list[str]:
    s = get_settings()
    params = {
        "decimalLatitude": f"{point.lat - radius_deg},{point.lat + radius_deg}",
        "decimalLongitude": f"{point.lon - radius_deg},{point.lon + radius_deg}",
        "limit": limit,
        "hasCoordinate": "true",
        "basisOfRecord": "HUMAN_OBSERVATION",
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
    seen: set[str] = set()
    for occ in results:
        name = occ.get("species") or occ.get("scientificName")
        if name and name not in seen:
            seen.add(name)
            names.append(name)
        if len(names) >= 12:
            break
    return names


def _inaturalist_species(point: GeoPoint, radius_km: float = 10) -> list[str]:
    """iNaturalist research-grade observations near the point."""
    try:
        s = get_settings()
        r = requests.get(
            "https://api.inaturalist.org/v1/observations",
            params={
                "lat": point.lat,
                "lng": point.lon,
                "radius": radius_km,
                "quality_grade": "research",
                "per_page": 30,
                "order_by": "votes",
            },
            headers={"User-Agent": s.http_user_agent},
            timeout=20,
        )
        r.raise_for_status()
        results = r.json().get("results", [])
        names: list[str] = []
        seen: set[str] = set()
        for obs in results:
            taxon = obs.get("taxon") or {}
            name = taxon.get("preferred_common_name") or taxon.get("name")
            if name and name not in seen:
                seen.add(name)
                names.append(name)
            if len(names) >= 10:
                break
        return names
    except Exception:
        return []


def _osm_nature_areas(point: GeoPoint, radius_m: int = 8000) -> list[str]:
    """Protected areas, nature reserves and national parks from OpenStreetMap Overpass."""
    s = get_settings()
    query = f"""
    [out:json][timeout:20];
    (
      node(around:{radius_m},{point.lat},{point.lon})["leisure"="nature_reserve"];
      way(around:{radius_m},{point.lat},{point.lon})["leisure"="nature_reserve"];
      relation(around:{radius_m},{point.lat},{point.lon})["boundary"="protected_area"];
      relation(around:{radius_m},{point.lat},{point.lon})["boundary"="national_park"];
    );
    out tags 15;
    """
    try:
        r = requests.post(
            s.overpass_url,
            data={"data": query},
            headers={"User-Agent": s.http_user_agent},
            timeout=30,
        )
        r.raise_for_status()
        elements = r.json().get("elements", [])
        areas: list[str] = []
        seen: set[str] = set()
        for el in elements:
            name = el.get("tags", {}).get("name")
            if name and name not in seen:
                seen.add(name)
                areas.append(name)
        return areas
    except Exception:
        return []


def likely_species(point: GeoPoint) -> list[str]:
    gbif = _gbif_species(point)
    inat = _inaturalist_species(point)
    combined: list[str] = []
    seen: set[str] = set()
    for s in gbif + inat:
        if s not in seen:
            seen.add(s)
            combined.append(s)
        if len(combined) >= 15:
            break
    return combined


def nature_areas(point: GeoPoint) -> list[str]:
    """Returns named protected/nature areas near the point."""
    return _osm_nature_areas(point)
