#!/usr/bin/env bash
# 99_teardown.sh - Stops the local containers and background processes to free resources
#   at the end of a session. Data volumes are preserved unless you opt to remove them.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST/scripts"

echo ">> Stopping local containers (volumes are preserved) ..."
docker compose --env-file "$DEST/.env" down || true

echo ">> To also DELETE local container data:"
echo "   docker compose --env-file $DEST/.env down -v"

# Stop typical background processes if they were launched for the demo.
pkill -f "streamlit run" 2>/dev/null && echo ">> Streamlit stopped." || true
pkill -f "solace-agent-mesh" 2>/dev/null && echo ">> Mesh runtime stopped." || true
pkill -f "uvicorn" 2>/dev/null && echo ">> uvicorn stopped." || true

echo ">> Resources released."
