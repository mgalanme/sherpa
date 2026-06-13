#!/usr/bin/env python3
"""smoke_vector.py - Verifies connectivity to Qdrant (Cloud in deployment, or local in dev).
Reads QDRANT_URL and QDRANT_API_KEY from the environment.
Run inside .venv-langchain. The client minor version must match the server (pinned in requirements).
"""

import os
import sys

from qdrant_client import QdrantClient

url = os.environ.get("QDRANT_URL") or os.environ.get(
    "QDRANT_LOCAL_URL", "http://localhost:6333"
)
api_key = os.environ.get("QDRANT_API_KEY") or None

try:
    client = QdrantClient(url=url, api_key=api_key, timeout=20)
    cols = client.get_collections()
    names = [c.name for c in cols.collections]
    print(f"  [ OK ] Qdrant reachable at {url}; collections: {names or '(none yet)'}")
    print(
        "         Remember to use query_points() rather than the deprecated search()."
    )
except Exception as exc:  # noqa: BLE001
    print(f"  [FAIL] Qdrant check failed: {exc}")
    sys.exit(1)
