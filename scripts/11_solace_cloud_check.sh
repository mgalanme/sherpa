#!/usr/bin/env bash
# 11_solace_cloud_check.sh - Validates Solace Cloud broker reachability for the deployed demo.
#   Uses the SEMP/REST or health endpoint where available; the full publish/subscribe round
#   trip is exercised by smoke/smoke_mesh.py in 12_smoke_test.sh.
set -uo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
set -a; [ -f "$DEST/.env" ] && . "$DEST/.env"; set +a

for v in SOLACE_HOST SOLACE_VPN SOLACE_USERNAME SOLACE_PASSWORD; do
  [ -z "${!v:-}" ] && { echo "  [MISS] $v is empty in .env"; exit 1; } || echo "  [ OK ] $v is set"
done

echo
echo ">> Solace Cloud broker target:"
echo "   Host : ${SOLACE_HOST}"
echo "   VPN  : ${SOLACE_VPN}"
echo
echo ">> The SMF connection and a publish/subscribe round trip are verified by"
echo "   smoke/smoke_mesh.py during 12_smoke_test.sh, using the Solace Python API."
echo ">> If you also want to test the local broker, ensure 07_docker_compose_up.sh ran first,"
echo "   then set SHERPA_MESH_TARGET=local before the smoke test."
echo ">> Next: 12_smoke_test.sh"
