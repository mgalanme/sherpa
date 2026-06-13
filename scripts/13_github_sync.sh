#!/usr/bin/env bash
# 13_github_sync.sh - Creates or updates the GitHub repository via gh (already installed and
#   authenticated), commits the project and pushes. Accepts an optional commit message.
#
# Usage:
#   bash 13_github_sync.sh                      # default commit message
#   bash 13_github_sync.sh "feat: pilot setup"  # custom commit message
set -euo pipefail

DEST="${SHERPA_HOME:-/home/pruebas/formacion/sherpa}"
cd "$DEST"
set -a; [ -f .env ] && . ./.env; set +a
REPO="${GH_REPO:-mgalanme/sherpa}"
BRANCH="${GH_BRANCH:-main}"
MSG="${1:-chore: SHERPA pilot setup}"

command -v gh >/dev/null 2>&1 || { echo ">> gh not found."; exit 1; }
gh auth status >/dev/null 2>&1 || { echo ">> Not authenticated. Run: gh auth login (use a PAT)"; exit 1; }

# Generate a correct .gitignore only if it is missing (never copy .env content into it).
if [ ! -f .gitignore ]; then
  cat > .gitignore <<'IGN'
.env
.venv-*/
__pycache__/
*.pyc
data/outputs/
data/gpx/*.gpx
.ipynb_checkpoints/
.databricks/
*.log
IGN
  echo ">> Created .gitignore"
fi

# Run ruff only on source directories that actually exist, to avoid spurious failures.
if command -v ruff >/dev/null 2>&1; then
  TARGETS=()
  for d in src scripts; do [ -d "$d" ] && TARGETS+=("$d"); done
  if [ "${#TARGETS[@]}" -gt 0 ]; then
    echo ">> ruff check + format on: ${TARGETS[*]}"
    ruff check "${TARGETS[@]}" || true
    ruff format "${TARGETS[@]}" || true
  fi
fi

if [ ! -d .git ]; then
  git init -q
  git config pull.rebase true
fi

git add -A
git commit -q -m "$MSG" || echo ">> Nothing new to commit."

if gh repo view "$REPO" >/dev/null 2>&1; then
  echo ">> Repository $REPO exists; updating."
  git remote get-url origin >/dev/null 2>&1 || git remote add origin "https://github.com/$REPO.git"
  git branch -M "$BRANCH"
  git pull --rebase origin "$BRANCH" 2>/dev/null || true
  git push -u origin "$BRANCH"
else
  echo ">> Creating public repository $REPO and pushing."
  git branch -M "$BRANCH"
  gh repo create "$REPO" --public --source=. --remote=origin --push
fi

echo ">> Repository ready: https://github.com/$REPO"
