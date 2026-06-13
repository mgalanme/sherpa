"""Weather client: AEMET OpenData (Spain) with Open-Meteo as the global source and for
climatological baselines beyond the reliable forecast horizon.
"""

from __future__ import annotations

from datetime import date

import requests

from ..config import get_settings
from ..models import GeoPoint, WeatherPanel

_FORECAST_HORIZON_DAYS = 10


def _open_meteo_forecast(point: GeoPoint, day: date) -> WeatherPanel:
    s = get_settings()
    params = {
        "latitude": point.lat,
        "longitude": point.lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max,wind_gusts_10m_max,uv_index_max,snowfall_sum",
        "timezone": "auto",
        "start_date": day.isoformat(),
        "end_date": day.isoformat(),
    }
    r = requests.get(
        "https://api.open-meteo.com/v1/forecast",
        params=params,
        headers={"User-Agent": s.http_user_agent},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json().get("daily", {})

    def first(key):
        vals = d.get(key) or []
        return vals[0] if vals else None

    snowfall = first("snowfall_sum") or 0
    return WeatherPanel(
        summary="Forecast from Open-Meteo",
        temp_min_c=first("temperature_2m_min"),
        temp_max_c=first("temperature_2m_max"),
        wind_kmh=first("wind_speed_10m_max"),
        gust_kmh=first("wind_gusts_10m_max"),
        rain_prob_pct=first("precipitation_probability_max"),
        snow=bool(snowfall and snowfall > 0),
        uv_index=first("uv_index_max"),
        is_forecast=True,
        source="open-meteo",
    )


def _open_meteo_climatology(point: GeoPoint, day: date) -> WeatherPanel:
    """Seasonal baseline from ERA5 reanalysis for the same day last year, clearly labelled."""
    s = get_settings()
    ref = day.replace(year=day.year - 1)
    params = {
        "latitude": point.lat,
        "longitude": point.lon,
        "start_date": ref.isoformat(),
        "end_date": ref.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,wind_speed_10m_max,precipitation_sum",
        "timezone": "auto",
    }
    r = requests.get(
        "https://archive-api.open-meteo.com/v1/archive",
        params=params,
        headers={"User-Agent": s.http_user_agent},
        timeout=30,
    )
    r.raise_for_status()
    d = r.json().get("daily", {})

    def first(key):
        vals = d.get(key) or []
        return vals[0] if vals else None

    return WeatherPanel(
        summary="Seasonal baseline (ERA5 reanalysis, same day last year). Not a forecast.",
        temp_min_c=first("temperature_2m_min"),
        temp_max_c=first("temperature_2m_max"),
        wind_kmh=first("wind_speed_10m_max"),
        rain_prob_pct=None,
        is_forecast=False,
        source="open-meteo (ERA5)",
        warnings=[
            "Date is beyond the reliable forecast horizon; this is a seasonal baseline."
        ],
    )


def get_weather(point: GeoPoint, day: date) -> WeatherPanel:
    """Return a weather panel. Within the forecast horizon use a forecast; beyond it, a
    clearly-labelled climatological baseline. AEMET could be layered in here for Spain;
    Open-Meteo is used as the dependable default and requires no key."""
    days_ahead = (day - date.today()).days
    try:
        if 0 <= days_ahead <= _FORECAST_HORIZON_DAYS:
            return _open_meteo_forecast(point, day)
        return _open_meteo_climatology(point, day)
    except Exception as exc:  # noqa: BLE001
        return WeatherPanel(summary=f"Weather unavailable: {exc}", source="none")
