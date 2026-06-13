#!/usr/bin/env bash
# 00_deploy.sh - Deploys the SHERPA setup scripts from the downloads folder to the
#                training destination, creating the project layout if it does not exist.
#
#   Origin      : the folder where this ZIP was extracted (defaults to this script's own dir).
#   Destination : /home/pruebas/formacion/sherpa  (created automatically; it does not exist yet).
#
# Usage:
#   bash 00_deploy.sh                 # uses defaults
#   SHERPA_ORIGIN=/path SHERPA_HOME=/path bash 00_deploy.sh
set -euo pipefail

SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGIN="${SHERPA_ORIGIN:-$SELF_DIR}"
DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"

echo ">> Origin      : $ORIGIN"
echo ">> Destination : $DEST"

mkdir -p "$DEST/scripts/smoke"
mkdir -p "$DEST/databricks/notebooks"
mkdir -p "$DEST/data/gpx" "$DEST/data/outputs"
mkdir -p "$DEST/src"

# Copy scripts and configuration, preserving structure. The application source code
# (src/) is delivered later in a separate App Scripts package.
cp -v "$ORIGIN"/scripts/*.sh                "$DEST/scripts/"        2>/dev/null || true
cp -v "$ORIGIN"/scripts/smoke/*.py          "$DEST/scripts/smoke/"  2>/dev/null || true
cp -v "$ORIGIN"/docker-compose.yml          "$DEST/"                2>/dev/null || true
cp -v "$ORIGIN"/.env.example                "$DEST/"                2>/dev/null || true
cp -v "$ORIGIN"/.gitignore                  "$DEST/"                2>/dev/null || true
cp -v "$ORIGIN"/requirements-*.txt          "$DEST/"                2>/dev/null || true
cp -v "$ORIGIN"/README.md                   "$DEST/"                2>/dev/null || true

chmod +x "$DEST"/scripts/*.sh 2>/dev/null || true

echo ">> Deployment complete. Next steps:"
echo "   1) cd $DEST/scripts"
echo "   2) bash 01_prereqs_check.sh"
echo "   3) Follow the Setup document in order (sections 6 onwards)."
