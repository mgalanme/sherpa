"""Intake helpers: geocoding via OpenStreetMap Nominatim, and a language-model parser that
turns a free-text description into structured inputs. The language model only structures input;
it does not make safety decisions.
"""

from __future__ import annotations

import json
from datetime import date, time

import requests

from .config import get_settings
from .llm import complete
from .models import ActivityInputs, ActivityType, GeoPoint

_NOMINATIM = "https://nominatim.openstreetmap.org/search"


def geocode(query: str) -> GeoPoint:
    s = get_settings()
    try:
        r = requests.get(
            _NOMINATIM,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": s.http_user_agent},
            timeout=20,
        )
        r.raise_for_status()
        data = r.json()
        if data:
            return GeoPoint(
                lat=float(data[0]["lat"]), lon=float(data[0]["lon"]), label=query
            )
    except Exception:
        pass
    return GeoPoint(lat=0.0, lon=0.0, label=query)


_PARSE_SYSTEM = (
    "Extract outing planning fields from the user's text and reply with ONLY a JSON object, no "
    "prose, with keys: activity_type (one of cycling_road, cycling_gravel, cycling_mtb, hiking, "
    "trail_running, tennis, padel, climbing, kayaking, cultural), departure_origin, "
    "activity_start, activity_end (free-text place names), activity_date (YYYY-MM-DD), "
    "start_time (HH:MM), end_time (HH:MM), other_characteristics. Use empty strings if unknown."
)


def parse_freetext(text: str) -> dict:
    raw = complete(text, system=_PARSE_SYSTEM, max_tokens=400, temperature=0.0)
    raw = (
        raw.strip()
        .removeprefix("```json")
        .removeprefix("```")
        .removesuffix("```")
        .strip()
    )
    try:
        return json.loads(raw)
    except Exception:
        return {}


def build_inputs(parsed: dict, gpx_path: str | None = None) -> ActivityInputs:
    """Build a validated ActivityInputs, geocoding the place names."""
    activity = parsed.get("activity_type", "hiking")
    try:
        activity_enum = ActivityType(activity)
    except ValueError:
        activity_enum = ActivityType.HIKING
    return ActivityInputs(
        activity_type=activity_enum,
        departure_origin=geocode(parsed.get("departure_origin", "")),
        activity_start=geocode(parsed.get("activity_start", "")),
        activity_end=geocode(parsed.get("activity_end", "")),
        activity_date=date.fromisoformat(
            parsed.get("activity_date") or date.today().isoformat()
        ),
        start_time=time.fromisoformat((parsed.get("start_time") or "09:00")),
        end_time=time.fromisoformat((parsed.get("end_time") or "14:00")),
        other_characteristics=parsed.get("other_characteristics", ""),
        gpx_path=gpx_path,
    )
