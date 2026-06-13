#!/usr/bin/env bash
# 22_run_local.sh - Runs the SHERPA portal locally. The local Solace PubSub+ broker carries
#   the mesh events; set SHERPA_MESH_TARGET=local in the environment to use it, or leave the
#   cloud broker configured to exercise Solace Cloud.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST"
set -a; [ -f .env ] && . ./.env; set +a
export PYTHONPATH=.

echo ">> Launching Streamlit portal at http://localhost:8501 (Ctrl+C to stop) ..."
.venv-langchain/bin/streamlit run src/portal/app.py
