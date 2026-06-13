#!/usr/bin/env bash
# 20_deploy_app.sh - Deploys the SHERPA application code from the downloads folder into the
#   existing project at /home/pruebas/formacion/sherpa. Run after the Setup package is in place.
#
#   Origin      : the folder where this app ZIP was extracted (defaults to this script's parent).
#   Destination : /home/pruebas/formacion/sherpa
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGIN="${SHERPA_APP_ORIGIN:-$(dirname "$SELF_DIR")}"
DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"

echo ">> Origin      : $ORIGIN"
echo ">> Destination : $DEST"

mkdir -p "$DEST/src/clients" "$DEST/src/stores" "$DEST/src/agents" "$DEST/src/portal"
mkdir -p "$DEST/databricks/notebooks" "$DEST/prompts" "$DEST/solace" "$DEST/.streamlit"
mkdir -p "$DEST/data/gpx" "$DEST/data/outputs"

cp -rv "$ORIGIN"/src/*                       "$DEST/src/"                   2>/dev/null || true
cp -rv "$ORIGIN"/databricks/notebooks/*      "$DEST/databricks/notebooks/" 2>/dev/null || true
cp -rv "$ORIGIN"/prompts/*                   "$DEST/prompts/"              2>/dev/null || true
cp -rv "$ORIGIN"/solace/*                    "$DEST/solace/"               2>/dev/null || true
cp -v  "$ORIGIN"/.streamlit/secrets.toml.example "$DEST/.streamlit/"       2>/dev/null || true
cp -v  "$ORIGIN"/scripts/2*.sh               "$DEST/scripts/"              2>/dev/null || true
cp -v  "$ORIGIN"/README_APP.md               "$DEST/"                      2>/dev/null || true

chmod +x "$DEST"/scripts/*.sh 2>/dev/null || true

echo ">> Application code deployed. Next:"
echo "   1) Configure Databricks notebooks (databricks/notebooks) and run 01 -> 02 -> 03 to seed gold and Qdrant."
echo "   2) bash scripts/21_seed_stores.sh   (creates Qdrant collection and Neo4j constraints)"
echo "   3) bash scripts/22_run_local.sh     (local mesh + Streamlit) or deploy to Streamlit Cloud."
