"""Cultural and heritage enrichment.

Sources used:
- Wikipedia geosearch + summaries (CC-BY-SA) for history, landscape and POIs
- Wikidata SPARQL for structured facts (monuments, protected areas, heritage sites)
- OpenStreetMap Nominatim reverse geocode for the administrative context
"""

from __future__ import annotations

import requests

from ..config import get_settings
from ..models import GeoPoint, PlaceFacts

_LANG = "en"
_WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"


def _wikipedia_facts(
    point: GeoPoint, max_articles: int = 5
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Returns (pois, snippets, citations, categories)."""
    s = get_settings()
    headers = {"User-Agent": s.http_user_agent}
    pois, snippets, citations, categories = [], [], [], []
    try:
        geo = requests.get(
            f"https://{_LANG}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{point.lat}|{point.lon}",
                "gsradius": 8000,
                "gslimit": max_articles,
                "format": "json",
            },
            headers=headers,
            timeout=30,
        )
        geo.raise_for_status()
        pages = geo.json().get("query", {}).get("geosearch", [])
    except Exception:
        return pois, snippets, citations, categories

    for page in pages:
        title = page.get("title", "")
        if not title:
            continue
        pois.append(title)
        try:
            summ = requests.get(
                f"https://{_LANG}.wikipedia.org/api/rest_v1/page/summary/{title.replace(' ', '_')}",
                headers=headers,
                timeout=20,
            )
            if summ.ok:
                body = summ.json()
                extract = body.get("extract", "")
                if extract:
                    snippets.append(extract)
                url = body.get("content_urls", {}).get("desktop", {}).get("page", "")
                if url:
                    citations.append(url)
                # collect categories hint from description
                desc = body.get("description", "")
                if desc:
                    categories.append(desc)
        except Exception:
            continue
    return pois, snippets, citations, categories


def _wikidata_heritage(point: GeoPoint, radius_m: int = 8000) -> list[str]:
    """SPARQL query for nearby cultural heritage and natural protected sites."""
    sparql = f"""
    SELECT DISTINCT ?itemLabel WHERE {{
      ?item wdt:P625 ?coord .
      SERVICE wikibase:around {{
        ?item wdt:P625 ?coord .
        bd:serviceParam wikibase:center "Point({point.lon} {point.lat})"^^geo:wktLiteral .
        bd:serviceParam wikibase:radius "{radius_m / 1000}" .
      }}
      ?item wdt:P31 ?type .
      FILTER(?type IN (wd:Q839954, wd:Q747074, wd:Q23442, wd:Q1194038,
                       wd:Q5588651, wd:Q4022, wd:Q179049, wd:Q11292, wd:Q3947))
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en" }}
    }} LIMIT 10
    """
    try:
        r = requests.get(
            _WIKIDATA_ENDPOINT,
            params={"query": sparql, "format": "json"},
            headers={
                "User-Agent": get_settings().http_user_agent,
                "Accept": "application/sparql-results+json",
            },
            timeout=20,
        )
        r.raise_for_status()
        bindings = r.json().get("results", {}).get("bindings", [])
        return [b["itemLabel"]["value"] for b in bindings if b.get("itemLabel")]
    except Exception:
        return []


def _admin_context(point: GeoPoint) -> str:
    """OpenStreetMap Nominatim reverse geocode for municipal/regional context."""
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": point.lat, "lon": point.lon, "format": "json", "zoom": 10},
            headers={"User-Agent": get_settings().http_user_agent},
            timeout=15,
        )
        r.raise_for_status()
        addr = r.json().get("address", {})
        parts = [
            v
            for k, v in addr.items()
            if k in ("municipality", "county", "state", "country") and v
        ]
        return ", ".join(parts)
    except Exception:
        return ""


def place_facts(point: GeoPoint) -> PlaceFacts:
    pois, snippets, citations, categories = _wikipedia_facts(point)
    heritage = _wikidata_heritage(point)
    admin = _admin_context(point)

    facts = PlaceFacts()
    facts.points_of_interest = pois + [h for h in heritage if h not in pois]
    facts.history = " ".join(snippets[:2])
    facts.landscape = snippets[2] if len(snippets) > 2 else ""
    if admin:
        facts.landscape = (admin + ". " + facts.landscape).strip()
    facts.citations = citations
    return facts
