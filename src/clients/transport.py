"""Transport options from departure origin to activity start point.

Notes are now looked up from i18n.c() to respect the active language.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import requests

from ..config import get_settings
from ..i18n import c
from ..models import GeoPoint


@dataclass
class TransportOption:
    mode: str
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
    try:
        url = (
            f"https://router.project-osrm.org/route/v1/driving/"
            f"{origin.lon},{origin.lat};{dest.lon},{dest.lat}?overview=false"
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


def get_transport_options(
    origin: GeoPoint, dest: GeoPoint, lang: str = "en"
) -> list[TransportOption]:
    s = get_settings()
    options: list[TransportOption] = []

    # Car
    if s.ors_api_key:
        dist_km, dur_min = _ors_driving(origin, dest, s.ors_api_key)
    else:
        dist_km, dur_min = _osrm_driving(origin, dest)

    car_summary_tpl = {
        "en": "{d} km, approximately {t} minutes by road.",
        "de": "{d} km, ca. {t} Minuten auf der Straße.",
        "fr": "{d} km, environ {t} minutes par la route.",
        "es": "{d} km, aproximadamente {t} minutos por carretera.",
        "it": "{d} km, circa {t} minuti su strada.",
        "pl": "{d} km, około {t} minut drogą.",
        "ro": "{d} km, aproximativ {t} minute pe șosea.",
        "nl": "{d} km, ongeveer {t} minuten over de weg.",
        "pt": "{d} km, aproximadamente {t} minutos por estrada.",
        "el": "{d} χλμ, περίπου {t} λεπτά οδικώς.",
    }
    car_summary = (car_summary_tpl.get(lang) or car_summary_tpl["en"]).format(
        d=dist_km, t=int(dur_min)
    )
    options.append(
        TransportOption(
            mode="car",
            summary=car_summary,
            distance_km=dist_km,
            duration_min=dur_min,
            notes=[
                c("transport_check_parking", lang),
                c("transport_loop_parking", lang),
            ],
            map_link=_google_maps_link(origin, dest),
        )
    )

    # Public transport
    straight_km = _haversine_km(origin, dest)
    transit_notes = [c("transport_bike_carriage", lang)]
    if straight_km <= 60:
        transit_notes.insert(0, c("transport_cercanias", lang))
    else:
        transit_notes.insert(0, c("transport_intercity", lang))
    options.append(
        TransportOption(
            mode="public_transport",
            summary=c("transport_transit_tap", lang),
            distance_km=round(straight_km, 1),
            notes=transit_notes,
            map_link=_google_maps_link(origin, dest, "transit"),
        )
    )

    # Other
    other_notes: list[str] = []
    if straight_km <= 20 and s.ors_api_key:
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
            cycling_tpl = {
                "en": f"Cycling to the start: {cy_km} km, approximately {int(cy_min)} minutes. This adds {cy_km} km of road cycling before the main activity.",
                "de": f"Radfahren zum Start: {cy_km} km, ca. {int(cy_min)} Minuten. Dies fügt {cy_km} km Straßenradfahren vor der Hauptaktivität hinzu.",
                "fr": f"Aller au départ à vélo : {cy_km} km, environ {int(cy_min)} minutes. Cela ajoute {cy_km} km de cyclisme avant l'activité principale.",
                "es": f"Ir al inicio en bici: {cy_km} km, aprox. {int(cy_min)} minutos. Añade {cy_km} km de ciclismo antes de la actividad.",
                "it": f"In bici fino alla partenza: {cy_km} km, circa {int(cy_min)} minuti. Aggiunge {cy_km} km di ciclismo prima dell'attività.",
                "pl": f"Rowerem do startu: {cy_km} km, ok. {int(cy_min)} minut. Dodaje {cy_km} km jazdy rowerem przed główną aktywnością.",
                "ro": f"Pe bicicletă până la start: {cy_km} km, aproximativ {int(cy_min)} minute. Adaugă {cy_km} km de ciclism înainte de activitate.",
                "nl": f"Fietsen naar het startpunt: {cy_km} km, ongeveer {int(cy_min)} minuten. Dit voegt {cy_km} km fietsen toe vóór de hoofdactiviteit.",
                "pt": f"De bicicleta até ao início: {cy_km} km, aprox. {int(cy_min)} minutos. Acrescenta {cy_km} km de ciclismo antes da atividade.",
                "el": f"Με ποδήλατο έως την εκκίνηση: {cy_km} χλμ, περίπου {int(cy_min)} λεπτά. Προσθέτει {cy_km} χλμ ποδηλασίας πριν την κύρια δραστηριότητα.",
            }
            other_notes.append(cycling_tpl.get(lang) or cycling_tpl["en"])
        except Exception:
            pass
    other_notes.extend([c("transport_carsharing", lang), c("transport_taxi", lang)])
    other_summary_tpl = {
        "en": "Alternative access options.",
        "de": "Alternative Zugangsmöglichkeiten.",
        "fr": "Options d'accès alternatives.",
        "es": "Opciones de acceso alternativas.",
        "it": "Opzioni di accesso alternative.",
        "pl": "Alternatywne opcje dojazdu.",
        "ro": "Opțiuni alternative de acces.",
        "nl": "Alternatieve toegangsopties.",
        "pt": "Opções de acesso alternativas.",
        "el": "Εναλλακτικές επιλογές πρόσβασης.",
    }
    options.append(
        TransportOption(
            mode="other",
            summary=other_summary_tpl.get(lang) or other_summary_tpl["en"],
            distance_km=round(straight_km, 1),
            notes=other_notes,
            map_link=_google_maps_link(origin, dest, "walking"),
        )
    )
    return options
