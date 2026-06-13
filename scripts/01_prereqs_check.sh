#!/usr/bin/env bash
# 01_prereqs_check.sh - Verifies that every local prerequisite is present before setup.
#                       Reports clearly and does not assume anything is installed.
set -uo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
miss=0

check() {  # check <command> <human name> <hint>
  if command -v "$1" >/dev/null 2>&1; then
    printf "  [ OK ] %-16s %s\n" "$2" "$($1 --version 2>&1 | head -n1)"
  else
    printf "  [MISS] %-16s -> %s\n" "$2" "$3"
    miss=$((miss+1))
  fi
}

echo ">> Local prerequisite check for SHERPA"
echo "   (Linux Mint, user pruebas, no sudo; root is available via su when strictly needed)"
echo

check docker      "Docker"      "Install Docker Engine; ensure your user is in the 'docker' group (root via su)."
check uv          "uv"          "Will be installed user-space by 03_uv_bootstrap.sh."
check python3     "Python"      "Install Python 3.11 or 3.12 (uv can also manage interpreters)."
check gh          "GitHub CLI"  "Already expected to be installed and authenticated (gh auth login)."
check git         "git"         "Install git."
check ollama      "Ollama"      "Install Ollama for the local sovereign fallback model."
check curl        "curl"        "Install curl."
check jq          "jq"          "Install jq (used by the cloud-connectivity checks)."
check databricks  "Databricks"  "Install the Databricks CLI (used by 10_databricks_bootstrap.sh)."

echo
if command -v docker >/dev/null 2>&1; then
  if docker info >/dev/null 2>&1; then echo "  [ OK ] Docker daemon is reachable.";
  else echo "  [WARN] Docker is installed but the daemon is not reachable for this user."; miss=$((miss+1)); fi
fi

echo
if [ "$miss" -eq 0 ]; then
  echo ">> All prerequisites satisfied. Proceed with 02_dirs_and_env.sh"
else
  echo ">> $miss item(s) need attention. Resolve them, then re-run this script."
  exit 1
fi
