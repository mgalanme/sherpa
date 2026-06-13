"""Central configuration for SHERPA.

Reads from environment variables. On Streamlit Community Cloud, call
load_streamlit_secrets() at startup to copy st.secrets into the environment so that the
same configuration object works in both the local and the cloud environment.
"""

from __future__ import annotations

import os
from functools import lru_cache

from pydantic import BaseModel


def load_streamlit_secrets() -> None:
    """Copy Streamlit secrets into os.environ if running inside Streamlit Cloud.

    This lets the rest of the codebase read configuration uniformly from the environment.
    """
    try:
        import streamlit as st

        for key, value in st.secrets.items():
            if isinstance(value, (str, int, float, bool)):
                os.environ.setdefault(key, str(value))
            else:
                # Nested sections (tables) are flattened with their own keys.
                for sub_key, sub_value in dict(value).items():
                    os.environ.setdefault(sub_key, str(sub_value))
    except Exception:
        # Not running under Streamlit, or no secrets configured.
        pass


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


class Settings(BaseModel):
    # Deployment
    deploy_env: str = "local"

    # LLMs
    groq_api_key: str = ""
    groq_model_primary: str = "llama-3.3-70b-versatile"
    groq_model_fallback: str = "llama-3.1-8b-instant"
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b"

    # Embeddings
    embed_model: str = "nomic-ai/nomic-embed-text-v1"
    embed_dim: int = 768

    # Neo4j
    neo4j_uri: str = ""
    neo4j_username: str = "neo4j"
    neo4j_password: str = ""
    neo4j_database: str = "neo4j"

    # Qdrant
    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "place_facts"

    # Databricks
    databricks_host: str = ""
    databricks_token: str = ""
    databricks_http_path: str = ""
    databricks_catalog: str = "sherpa"
    databricks_schema: str = "pilot"

    # Solace
    solace_host: str = ""
    solace_vpn: str = ""
    solace_username: str = ""
    solace_password: str = ""
    mesh_enabled: bool = True

    # Open data
    aemet_api_key: str = ""
    ors_api_key: str = ""
    overpass_url: str = "https://overpass-api.de/api/interpreter"
    http_user_agent: str = "SHERPA-pilot/0.1 (contact: your-email@example.com)"

    @property
    def is_cloud(self) -> bool:
        return self.deploy_env.lower() == "cloud"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_streamlit_secrets()
    return Settings(
        deploy_env=_env("DEPLOY_ENV", "local"),
        groq_api_key=_env("GROQ_API_KEY"),
        groq_model_primary=_env("GROQ_MODEL_PRIMARY", "llama-3.3-70b-versatile"),
        groq_model_fallback=_env("GROQ_MODEL_FALLBACK", "llama-3.1-8b-instant"),
        ollama_host=_env("OLLAMA_HOST", "http://localhost:11434"),
        ollama_model=_env("OLLAMA_MODEL", "qwen2.5:3b"),
        embed_model=_env("EMBED_MODEL", "nomic-ai/nomic-embed-text-v1"),
        embed_dim=int(_env("EMBED_DIM", "768")),
        neo4j_uri=_env("NEO4J_URI") or _env("NEO4J_LOCAL_URI", "bolt://localhost:7687"),
        neo4j_username=_env("NEO4J_USERNAME", "neo4j"),
        neo4j_password=_env("NEO4J_PASSWORD") or _env("NEO4J_LOCAL_PASSWORD", ""),
        neo4j_database=_env("NEO4J_DATABASE", "neo4j"),
        qdrant_url=_env("QDRANT_URL")
        or _env("QDRANT_LOCAL_URL", "http://localhost:6333"),
        qdrant_api_key=_env("QDRANT_API_KEY"),
        qdrant_collection=_env("QDRANT_COLLECTION", "place_facts"),
        databricks_host=_env("DATABRICKS_HOST"),
        databricks_token=_env("DATABRICKS_TOKEN"),
        databricks_http_path=_env("DATABRICKS_HTTP_PATH"),
        databricks_catalog=_env("DATABRICKS_CATALOG", "sherpa"),
        databricks_schema=_env("DATABRICKS_SCHEMA", "pilot"),
        solace_host=_env("SOLACE_HOST"),
        solace_vpn=_env("SOLACE_VPN"),
        solace_username=_env("SOLACE_USERNAME"),
        solace_password=_env("SOLACE_PASSWORD"),
        mesh_enabled=_env("MESH_ENABLED", "true").lower() == "true",
        aemet_api_key=_env("AEMET_API_KEY"),
        ors_api_key=_env("ORS_API_KEY"),
        overpass_url=_env("OVERPASS_URL", "https://overpass-api.de/api/interpreter"),
        http_user_agent=_env(
            "HTTP_USER_AGENT", "SHERPA-pilot/0.1 (contact: your-email@example.com)"
        ),
    )
