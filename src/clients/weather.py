"""Weather client: AEMET OpenData (Spain) + Open-Meteo (global + ERA5 baseline).

Sources used:
- AEMET OpenData: official Spanish Met Office, free API key
- Open-Meteo forecast: global 7-day, no key required
- Open-Meteo ERA5: climatological baseline beyond forecast horizon
- Open-Meteo UV index and air quality (Copernicus CAMS) via the forecast endpoint
- Open-Meteo marine API for coastal/kayaking activities
- Open-Elevation for altitude at the start point (affects heat/altitude risk)
"""

from __future__ import annotations

from datetime import date

import requests

from ..config import get_settings
from ..models import GeoPoint, WeatherPanel

_FORECAST_HORIZON_DAYS = 10


def _altitude_m(point: GeoPoint) -> float | None:
    """Open-Elevation: free, no key."""
    try:
        r = requests.get(
            "https://api.open-elevation.com/api/v1/lookup",
            params={"locations": f"{point.lat},{point.lon}"},
            headers={"User-Agent": get_settings().http_user_agent},
            timeout=15,
        )
        r.raise_for_status()
        return r.json()["results"][0]["elevation"]
    except Exception:
        return None


def _open_meteo_forecast(point: GeoPoint, day: date) -> WeatherPanel:
    s = get_settings()
    params = {
        "latitude": point.lat,
        "longitude": point.lon,
        "daily": (
            "temperature_2m_max,temperature_2m_min,precipitation_probability_max,"
            "wind_speed_10m_max,wind_gusts_10m_max,uv_index_max,snowfall_sum,"
            "precipitation_sum,weathercode,sunrise,sunset"
        ),
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
    warnings = []
    sunrise = first("sunrise") or ""
    sunset = first("sunset") or ""
    if sunrise or sunset:
        warnings.append(
            f"Sunrise {sunrise[11:] if sunrise else 'n/a'}, sunset {sunset[11:] if sunset else 'n/a'}"
        )

    # Altitude flag
    alt = _altitude_m(point)
    if alt and alt > 1500:
        warnings.append(
            f"Altitude: {int(alt)} m. Factor in altitude sickness risk and temperature lapse rate."
        )

    return WeatherPanel(
        summary="Open-Meteo 7-day forecast",
        temp_min_c=first("temperature_2m_min"),
        temp_max_c=first("temperature_2m_max"),
        wind_kmh=first("wind_speed_10m_max"),
        gust_kmh=first("wind_gusts_10m_max"),
        rain_prob_pct=first("precipitation_probability_max"),
        snow=bool(snowfall and snowfall > 0),
        uv_index=first("uv_index_max"),
        is_forecast=True,
        warnings=warnings,
        source="open-meteo (forecast)",
    )


def _open_meteo_climatology(point: GeoPoint, day: date) -> WeatherPanel:
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
            "Date is beyond the reliable 7-day forecast horizon; this is a seasonal baseline. Re-check nearer the date."
        ],
    )


def _aemet_forecast(point: GeoPoint, day: date, api_key: str) -> WeatherPanel | None:
    """AEMET OpenData forecast for Spain. Returns None on any failure so callers can fall back."""
    try:
        s = get_settings()
        # Step 1: get the nearest municipality forecast URL
        r = requests.get(
            f"https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/{day.isoformat()}/latlon/{point.lat},{point.lon}",
            headers={"api_key": api_key, "User-Agent": s.http_user_agent},
            timeout=20,
        )
        if not r.ok:
            return None
        data_url = r.json().get("datos")
        if not data_url:
            return None
        data = requests.get(
            data_url, headers={"User-Agent": s.http_user_agent}, timeout=20
        ).json()
        pred = data[0]["prediccion"]["dia"][0]
        tmax = pred.get("temperatura", {}).get("maxima")
        tmin = pred.get("temperatura", {}).get("minima")
        wind_kmh = None
        winds = pred.get("viento", [])
        if winds:
            wind_kmh = max((w.get("velocidad", 0) for w in winds), default=None)
        prob_rain = pred.get("probPrecipitacion", [{}])[0].get("value")
        snow = any(p.get("value", 0) > 0 for p in pred.get("probNieve", []))
        return WeatherPanel(
            summary="AEMET official Spanish forecast",
            temp_min_c=float(tmin) if tmin is not None else None,
            temp_max_c=float(tmax) if tmax is not None else None,
            wind_kmh=float(wind_kmh) if wind_kmh else None,
            rain_prob_pct=float(prob_rain) if prob_rain is not None else None,
            snow=snow,
            is_forecast=True,
            source="AEMET OpenData",
        )
    except Exception:
        return None


def get_weather(point: GeoPoint, day: date) -> WeatherPanel:
    s = get_settings()
    days_ahead = (day - date.today()).days
    try:
        # Try AEMET first for Spain (lat 27–44 N, lon -18–5 E)
        if (
            s.aemet_api_key
            and 27 <= point.lat <= 44
            and -18 <= point.lon <= 5
            and 0 <= days_ahead <= 6
        ):
            aemet = _aemet_forecast(point, day, s.aemet_api_key)
            if aemet:
                return aemet
        if 0 <= days_ahead <= _FORECAST_HORIZON_DAYS:
            return _open_meteo_forecast(point, day)
        return _open_meteo_climatology(point, day)
    except Exception as exc:
        return WeatherPanel(summary=f"Weather unavailable: {exc}", source="none")
