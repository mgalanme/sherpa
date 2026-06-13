"""Qdrant vector store for place-fact retrieval.

Lessons applied: the client is pinned to the server minor version (v1.12.4 in requirements)
and retrieval uses query_points(), not the deprecated search().
"""

from __future__ import annotations

from functools import lru_cache

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..config import get_settings


@lru_cache(maxsize=1)
def client() -> QdrantClient:
    s = get_settings()
    return QdrantClient(url=s.qdrant_url, api_key=s.qdrant_api_key or None, timeout=30)


def ensure_collection() -> None:
    s = get_settings()
    c = client()
    existing = {col.name for col in c.get_collections().collections}
    if s.qdrant_collection not in existing:
        c.create_collection(
            collection_name=s.qdrant_collection,
            vectors_config=VectorParams(size=s.embed_dim, distance=Distance.COSINE),
        )


def upsert(points: list[tuple[str, list[float], dict]]) -> None:
    s = get_settings()
    client().upsert(
        collection_name=s.qdrant_collection,
        points=[
            PointStruct(id=pid, vector=vec, payload=payload)
            for pid, vec, payload in points
        ],
    )


def search(query_vector: list[float], limit: int = 5) -> list[dict]:
    s = get_settings()
    # Use query_points, not the deprecated search()
    result = client().query_points(
        collection_name=s.qdrant_collection,
        query=query_vector,
        limit=limit,
        with_payload=True,
    )
    return [pt.payload or {} for pt in result.points]
