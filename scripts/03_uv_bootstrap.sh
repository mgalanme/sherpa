#!/usr/bin/env bash
# 03_uv_bootstrap.sh - Ensures uv is available in user space (no root). Idempotent.
set -euo pipefail

if command -v uv >/dev/null 2>&1; then
  echo ">> uv already present: $(uv --version)"
  exit 0
fi

echo ">> Installing uv in user space (no root required)..."
curl -LsSf https://astral.sh/uv/install.sh | sh

# Make uv available in the current and future shells.
if ! grep -q 'astral/uv' "$HOME/.bashrc" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi
export PATH="$HOME/.local/bin:$PATH"

if command -v uv >/dev/null 2>&1; then
  echo ">> uv installed: $(uv --version)"
  echo "   Open a new shell or run:  source ~/.bashrc"
else
  echo ">> uv was installed but is not on PATH yet. Run: source ~/.bashrc"
fi
