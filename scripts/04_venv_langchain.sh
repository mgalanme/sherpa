#!/usr/bin/env bash
# 04_venv_langchain.sh - Creates the .venv-langchain environment for the orchestration,
#   data, classical AI and Streamlit application layers, and installs its requirements.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
PY="${SHERPA_PYTHON:-3.12}"
cd "$DEST"
export PATH="$HOME/.local/bin:$PATH"

echo ">> Creating .venv-langchain (Python $PY) ..."
uv venv .venv-langchain --python "$PY"

echo ">> Installing requirements-langchain.txt ..."
uv pip install --python .venv-langchain/bin/python -r requirements-langchain.txt

echo ">> .venv-langchain ready."
echo "   Activate with:  source $DEST/.venv-langchain/bin/activate"
echo "   Always run from project root with PYTHONPATH=. set."
