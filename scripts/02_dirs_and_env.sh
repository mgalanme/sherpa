#!/usr/bin/env bash
# 02_dirs_and_env.sh - Confirms the project layout and creates the working .env from the template.
#                      It never overwrites an existing .env.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST"

mkdir -p scripts/smoke databricks/notebooks data/gpx data/outputs src

if [ -f .env ]; then
  echo ">> .env already exists; leaving it untouched."
else
  if [ -f .env.example ]; then
    cp .env.example .env
    echo ">> Created .env from .env.example."
    echo "   IMPORTANT: open .env and fill in every value before continuing."
  else
    echo ">> .env.example not found in $DEST. Did 00_deploy.sh run correctly?"
    exit 1
  fi
fi

# Quick reminder of the variables that must be set.
echo
echo ">> The following variables must be populated in $DEST/.env :"
grep -E '^[A-Z0-9_]+=' .env.example | cut -d= -f1 | sed 's/^/     - /'
echo
echo ">> When .env is complete, run 03_uv_bootstrap.sh"
