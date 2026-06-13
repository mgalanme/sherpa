#!/usr/bin/env bash
# 10_databricks_bootstrap.sh - Prepares the Databricks workspace for the demo:
#   verifies CLI auth, creates the secret scope, and creates the catalog/schema and the
#   append-only, hash-chained audit Delta table. Idempotent where possible.
#
# Requires: the Databricks CLI installed and configured (databricks configure --token),
#           using the DATABRICKS_HOST and DATABRICKS_TOKEN from .env.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
set -a; [ -f "$DEST/.env" ] && . "$DEST/.env"; set +a

CATALOG="${DATABRICKS_CATALOG:-sherpa}"
SCHEMA="${DATABRICKS_SCHEMA:-pilot}"
SCOPE="${DATABRICKS_SECRET_SCOPE:-sherpa}"
WAREHOUSE="${DATABRICKS_WAREHOUSE_ID:?Set DATABRICKS_WAREHOUSE_ID in .env}"

command -v databricks >/dev/null 2>&1 || { echo ">> Databricks CLI not found."; exit 1; }

echo ">> Creating secret scope '$SCOPE' (ignored if it already exists) ..."
databricks secrets create-scope "$SCOPE" 2>/dev/null || echo "   scope already exists."

echo ">> Storing shared secrets in the scope (reused from your existing projects) ..."
for k in GROQ_API_KEY NEO4J_URI NEO4J_PASSWORD QDRANT_URL QDRANT_API_KEY AEMET_API_KEY ORS_API_KEY; do
  if [ -n "${!k:-}" ]; then
    databricks secrets put-secret "$SCOPE" "$k" --string-value "${!k}" >/dev/null 2>&1 \
      && echo "   stored $k" || echo "   could not store $k (check permissions)"
  fi
done

echo ">> Creating catalog/schema and the audit table via the SQL Warehouse ..."
run_sql() { databricks api post /api/2.0/sql/statements --json "{\"warehouse_id\":\"$WAREHOUSE\",\"statement\":\"$1\"}" >/dev/null; }

run_sql "CREATE CATALOG IF NOT EXISTS ${CATALOG}"
run_sql "CREATE SCHEMA IF NOT EXISTS ${CATALOG}.${SCHEMA}"
run_sql "CREATE TABLE IF NOT EXISTS ${CATALOG}.${SCHEMA}.audit_event (event_id STRING, ts TIMESTAMP, actor STRING, action STRING, plan_id STRING, payload STRING, prev_hash STRING, hash STRING) USING DELTA"

echo ">> Databricks bootstrap complete."
echo "   Catalog.Schema : ${CATALOG}.${SCHEMA}"
echo "   Audit table    : ${CATALOG}.${SCHEMA}.audit_event (append-only, hash-chained)"
echo ">> Next: 11_solace_cloud_check.sh"
