"""Geography and access client using the OpenStreetMap Overpass API.

It surfaces access tags, barriers and nearby points of interest around the route, and is
explicit about uncertainty: it reports what it finds and never asserts a closure it cannot
verify from an authoritative source.
"""

from __future__ import annotations

import requests

from ..config import get_settings
from ..models import AccessNote, GeoPoint


def access_notes(point: GeoPoint, radius_m: int = 1500) -> list[AccessNote]:
    s = get_settings()
    query = f"""
    [out:json][timeout:25];
    (
      node(around:{radius_m},{point.lat},{point.lon})["access"];
      way(around:{radius_m},{point.lat},{point.lon})["access"];
      node(around:{radius_m},{point.lat},{point.lon})["barrier"];
    );
    out tags 30;
    """
    try:
        r = requests.post(
            s.overpass_url,
            data={"data": query},
            headers={"User-Agent": s.http_user_agent},
            timeout=40,
        )
        r.raise_for_status()
        elements = r.json().get("elements", [])
    except Exception as exc:  # noqa: BLE001
        return [
            AccessNote(
                note=f"Access data unavailable: {exc}",
                certainty="uncertain",
                source="overpass",
            )
        ]

    notes: list[AccessNote] = []
    seen = set()
    for el in elements:
        tags = el.get("tags", {})
        access = tags.get("access")
        barrier = tags.get("barrier")
        if access and access in {"private", "no", "permit"}:
            key = ("access", access)
            if key not in seen:
                seen.add(key)
                notes.append(
                    AccessNote(
                        note=f"Some segment is tagged access={access}; verify before relying on it.",
                        certainty="likely",
                        source="OpenStreetMap",
                    )
                )
        if barrier and barrier in {"gate", "lift_gate", "bollard"}:
            key = ("barrier", barrier)
            if key not in seen:
                seen.add(key)
                notes.append(
                    AccessNote(
                        note=f"A {barrier} is mapped near the route.",
                        certainty="likely",
                        source="OpenStreetMap",
                    )
                )

    if not notes:
        notes.append(
            AccessNote(
                note="No access restrictions found in OpenStreetMap near the start.",
                certainty="uncertain",
                source="OpenStreetMap",
            )
        )
    return notes
