#!/usr/bin/env bash
# 06_venv_mesh.sh - Creates the .venv-mesh environment for Solace Agent Mesh and its
#   event-driven runtime, isolated from the other environments because it pulls in the
#   Solace AI Connector and the Google Agent Development Kit.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
PY="${SHERPA_PYTHON:-3.12}"
cd "$DEST"
export PATH="$HOME/.local/bin:$PATH"

echo ">> Creating .venv-mesh (Python $PY) ..."
uv venv .venv-mesh --python "$PY"

echo ">> Installing requirements-mesh.txt ..."
uv pip install --python .venv-mesh/bin/python -r requirements-mesh.txt

echo ">> .venv-mesh ready."
echo "   This environment runs the local mesh against the Solace PubSub+ broker (Docker),"
echo "   and the same code connects to Solace Cloud for the deployed demo via the .env values."
