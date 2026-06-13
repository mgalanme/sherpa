#!/usr/bin/env python3
"""smoke_graph.py - Verifies connectivity to Neo4j (Aura in cloud, or local in development).
Reads NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD from the environment.
Run inside .venv-langchain after sourcing the project .env.
"""

import os
import sys

from neo4j import GraphDatabase

uri = os.environ.get("NEO4J_URI") or os.environ.get(
    "NEO4J_LOCAL_URI", "bolt://localhost:7687"
)
user = os.environ.get("NEO4J_USERNAME", "neo4j")
pwd = os.environ.get("NEO4J_PASSWORD") or os.environ.get("NEO4J_LOCAL_PASSWORD", "")

try:
    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    with driver.session() as session:
        value = session.run("RETURN 1 AS ok").single()["ok"]
        assert value == 1
        try:
            ver = session.run("RETURN apoc.version() AS v").single()["v"]
            print(f"  [ OK ] Neo4j reachable at {uri}; APOC version {ver}")
        except Exception:
            print(
                f"  [ OK ] Neo4j reachable at {uri}; APOC not detected (fine for Aura core checks)"
            )
    driver.close()
except Exception as exc:  # noqa: BLE001
    print(f"  [FAIL] Neo4j check failed: {exc}")
    sys.exit(1)
