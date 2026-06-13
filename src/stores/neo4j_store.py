"""Neo4j graph store for relationships among places, tracks, points of interest and species.

Lessons applied: enhanced_schema is set off when using the LangChain Neo4jGraph wrapper, and
APOC is required (available on Aura core and in the local Docker image).
"""

from __future__ import annotations

from functools import lru_cache

from neo4j import GraphDatabase

from ..config import get_settings


@lru_cache(maxsize=1)
def driver():
    s = get_settings()
    return GraphDatabase.driver(s.neo4j_uri, auth=(s.neo4j_username, s.neo4j_password))


def ensure_constraints() -> None:
    with driver().session() as session:
        session.run(
            "CREATE CONSTRAINT place_name IF NOT EXISTS FOR (p:Place) REQUIRE p.name IS UNIQUE"
        )
        session.run(
            "CREATE CONSTRAINT poi_name IF NOT EXISTS FOR (p:POI) REQUIRE p.name IS UNIQUE"
        )


def link_place_pois(place: str, pois: list[str], species: list[str]) -> None:
    with driver().session() as session:
        session.run("MERGE (p:Place {name:$place})", place=place)
        for poi in pois:
            session.run(
                "MERGE (p:Place {name:$place}) MERGE (q:POI {name:$poi}) MERGE (p)-[:HAS_POI]->(q)",
                place=place,
                poi=poi,
            )
        for sp in species:
            session.run(
                "MERGE (p:Place {name:$place}) MERGE (s:Species {name:$sp}) MERGE (p)-[:OBSERVED]->(s)",
                place=place,
                sp=sp,
            )


def related_pois(place: str, limit: int = 10) -> list[str]:
    with driver().session() as session:
        rows = session.run(
            "MATCH (p:Place {name:$place})-[:HAS_POI]->(q:POI) RETURN q.name AS name LIMIT $limit",
            place=place,
            limit=limit,
        )
        return [r["name"] for r in rows]
