#!/usr/bin/env bash
# 09_cloud_accounts_check.sh - Confirms that the cloud credentials are present in .env and
#   performs light HTTP connectivity checks where an endpoint allows it. Driver-level checks
#   (Neo4j, Qdrant, Solace) are performed by 12_smoke_test.sh.
set -uo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
set -a; [ -f "$DEST/.env" ] && . "$DEST/.env"; set +a
fail=0

req() {  # req VAR_NAME
  if [ -z "${!1:-}" ]; then echo "  [MISS] $1 is empty in .env"; fail=$((fail+1));
  else echo "  [ OK ] $1 is set"; fi
}

http() {  # http <label> <curl args...>
  local label="$1"; shift
  local code
  code="$(curl -s -o /dev/null -w '%{http_code}' "$@" || echo 000)"
  if [ "$code" = "200" ] || [ "$code" = "201" ]; then echo "  [ OK ] $label reachable (HTTP $code)";
  else echo "  [WARN] $label returned HTTP $code (check key or endpoint)"; fail=$((fail+1)); fi
}

echo ">> Required cloud variables"
for v in GROQ_API_KEY NEO4J_URI NEO4J_PASSWORD QDRANT_URL QDRANT_API_KEY \
         DATABRICKS_HOST DATABRICKS_TOKEN DATABRICKS_HTTP_PATH \
         SOLACE_HOST SOLACE_VPN SOLACE_USERNAME SOLACE_PASSWORD \
         LANGCHAIN_API_KEY AEMET_API_KEY ORS_API_KEY; do
  req "$v"
done

echo
echo ">> Light connectivity checks"
[ -n "${GROQ_API_KEY:-}" ] && http "Groq API" -H "Authorization: Bearer ${GROQ_API_KEY}" https://api.groq.com/openai/v1/models
[ -n "${QDRANT_URL:-}" ] && http "Qdrant Cloud" -H "api-key: ${QDRANT_API_KEY:-}" "${QDRANT_URL%/}/collections"
[ -n "${DATABRICKS_HOST:-}" ] && http "Databricks" -H "Authorization: Bearer ${DATABRICKS_TOKEN:-}" "${DATABRICKS_HOST%/}/api/2.0/clusters/list"
[ -n "${LANGCHAIN_API_KEY:-}" ] && http "LangSmith" -H "x-api-key: ${LANGCHAIN_API_KEY}" https://api.smith.langchain.com/info
[ -n "${AEMET_API_KEY:-}" ] && http "AEMET OpenData" "https://opendata.aemet.es/opendata/api/prediccion/especifica/municipio/diaria/28079?api_key=${AEMET_API_KEY}"

echo
if [ "$fail" -eq 0 ]; then echo ">> Cloud accounts look good. Next: 10_databricks_bootstrap.sh";
else echo ">> $fail issue(s) detected. Fix .env values or endpoints, then re-run."; exit 1; fi
