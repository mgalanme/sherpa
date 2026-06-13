#!/usr/bin/env bash
# 21_seed_stores.sh - Initialises the stores the app relies on: the Qdrant collection and the
#   Neo4j constraints. The gold place vectors are produced by the Databricks notebook 03.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST"
set -a; [ -f .env ] && . ./.env; set +a
export PYTHONPATH=.

echo ">> Ensuring Qdrant collection and Neo4j constraints ..."
.venv-langchain/bin/python - <<'PY'
from src.stores import qdrant_store, neo4j_store
qdrant_store.ensure_collection()
print("  [ OK ] Qdrant collection ready:", qdrant_store.get_settings().qdrant_collection)
neo4j_store.ensure_constraints()
print("  [ OK ] Neo4j constraints ready")
PY

echo ">> Stores initialised. Run the Databricks notebooks (01->02->03) to populate gold and"
echo "   upsert place-fact vectors into Qdrant, then 22_run_local.sh to launch the portal."
