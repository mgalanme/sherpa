#!/usr/bin/env bash
# 08_ollama_models.sh - Pulls the local sovereign fallback model used in development.
#   The deployed demo uses Groq; Ollama is local-only because Streamlit Cloud cannot
#   reach a local Ollama server.
set -euo pipefail

MODEL="${OLLAMA_MODEL:-qwen2.5:3b}"

if ! command -v ollama >/dev/null 2>&1; then
  echo ">> Ollama is not installed. Install it, then re-run this script."
  exit 1
fi

echo ">> Pulling local model: $MODEL"
echo "   Note: qwen2.5:3b is used because it supports function calling; llama3 does not."
ollama pull "$MODEL"

echo ">> Available models:"
ollama list

echo
echo ">> Embeddings are produced in-process with nomic-ai/nomic-embed-text-v1 (768 dims),"
echo "   so no embedding model is pulled here."
echo ">> Next, run 09_cloud_accounts_check.sh"
