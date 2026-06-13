"""In-process embeddings with nomic-ai/nomic-embed-text-v1 (768 dimensions).

The model is loaded lazily and cached. For the cloud app, place-fact embeddings are precomputed
in the Databricks gold pipeline, so at runtime only the short user query is embedded, which is
light enough for the free tier.
"""

from __future__ import annotations

from functools import lru_cache

from .config import get_settings


@lru_cache(maxsize=1)
def _model():
    from sentence_transformers import SentenceTransformer

    s = get_settings()
    # trust_remote_code is required for the nomic model architecture.
    return SentenceTransformer(s.embed_model, trust_remote_code=True)


def embed_query(text: str) -> list[float]:
    """Embed a single short query string. Nomic expects a task prefix for queries."""
    vec = _model().encode([f"search_query: {text}"], normalize_embeddings=True)[0]
    return vec.tolist()


def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed documents (used by the pipeline; not normally called at runtime in the cloud)."""
    prefixed = [f"search_document: {t}" for t in texts]
    vecs = _model().encode(prefixed, normalize_embeddings=True)
    return [v.tolist() for v in vecs]
