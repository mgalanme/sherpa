"""Cultural enrichment client using the Wikipedia REST API (geosearch plus summaries).

Returns grounded snippets with citations so that the narrative step can be anchored to
sources rather than fabricated.
"""

from __future__ import annotations

import requests

from ..config import get_settings
from ..models import GeoPoint, PlaceFacts

_LANG = "en"


def place_facts(point: GeoPoint, max_articles: int = 4) -> PlaceFacts:
    s = get_settings()
    headers = {"User-Agent": s.http_user_agent}
    facts = PlaceFacts()
    try:
        geo = requests.get(
            f"https://{_LANG}.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{point.lat}|{point.lon}",
                "gsradius": 5000,
                "gslimit": max_articles,
                "format": "json",
            },
            headers=headers,
            timeout=30,
        )
        geo.raise_for_status()
        pages = geo.json().get("query", {}).get("geosearch", [])
    except Exception as exc:  # noqa: BLE001
        facts.history = f"(Cultural context unavailable: {exc})"
        return facts

    pois: list[str] = []
    citations: list[str] = []
    snippets: list[str] = []
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
        except Exception:
            continue

    facts.points_of_interest = pois
    facts.history = " ".join(snippets[:2])
    facts.landscape = snippets[2] if len(snippets) > 2 else ""
    facts.citations = citations
    return facts
