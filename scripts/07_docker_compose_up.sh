#!/usr/bin/env bash
# 07_docker_compose_up.sh - Starts the local development containers (Solace, Qdrant, Neo4j).
#   Required only for local development; the deployed demo uses the cloud equivalents.
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST/scripts"

if [ ! -f "$DEST/.env" ]; then
  echo ">> $DEST/.env not found. Run 02_dirs_and_env.sh and complete it first."
  exit 1
fi

echo ">> Starting local containers ..."
docker compose --env-file "$DEST/.env" up -d

echo ">> Waiting for services to become healthy (this can take a minute for Solace) ..."
sleep 20
docker compose --env-file "$DEST/.env" ps

echo
echo ">> Local endpoints:"
echo "   Solace manager : http://localhost:8080   (admin / value of SOLACE_LOCAL_PASSWORD)"
echo "   Qdrant         : http://localhost:6333/dashboard"
echo "   Neo4j browser  : http://localhost:7474   (neo4j / value of NEO4J_LOCAL_PASSWORD)"
echo
echo ">> When ready, run 08_ollama_models.sh"
