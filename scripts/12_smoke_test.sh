#!/usr/bin/env bash
# 12_smoke_test.sh - Runs the end-to-end connectivity smoke tests in the correct
#   virtual environments, after sourcing the project .env. Reports a single verdict.
set -uo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST"
set -a; [ -f .env ] && . ./.env; set +a
export PYTHONPATH=.
fail=0

run_in() {  # run_in <venv-dir> <python-file>
  local venv="$1" file="$2"
  if [ -x "$venv/bin/python" ]; then
    "$venv/bin/python" "$file" || fail=$((fail+1))
  else
    echo "  [ERR] Missing $venv (run the matching venv script first)"; fail=$((fail+1))
  fi
}

echo ">> 1/5 Neo4j graph";        run_in .venv-langchain scripts/smoke/smoke_graph.py
echo ">> 2/5 Qdrant vector store"; run_in .venv-langchain scripts/smoke/smoke_vector.py
echo ">> 3/5 LLMs (Groq, Ollama)"; run_in .venv-langchain scripts/smoke/smoke_llm.py
echo ">> 4/5 Databricks SQL";      run_in .venv-langchain scripts/smoke/smoke_databricks.py
echo ">> 5/5 Solace mesh";         run_in .venv-mesh       scripts/smoke/smoke_mesh.py

echo
if [ "$fail" -eq 0 ]; then
  echo "SMOKE TEST OK: the stack is ready for the demo."
else
  echo "SMOKE TEST reported $fail failure(s). See the Troubleshooting appendix of the Setup document."
  exit 1
fi
