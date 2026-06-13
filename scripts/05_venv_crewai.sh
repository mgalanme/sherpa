#!/usr/bin/env bash
# 05_venv_crewai.sh - Creates the .venv-crewai environment for the CrewAI collaborative
#   crews (kept isolated from LangChain to avoid dependency conflicts).
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
PY="${SHERPA_PYTHON:-3.12}"
cd "$DEST"
export PATH="$HOME/.local/bin:$PATH"

echo ">> Creating .venv-crewai (Python $PY) ..."
uv venv .venv-crewai --python "$PY"

echo ">> Installing requirements-crewai.txt ..."
uv pip install --python .venv-crewai/bin/python -r requirements-crewai.txt

echo ">> .venv-crewai ready."
echo "   Reminder: import CrewAI modules in the main thread before spawning worker threads."
