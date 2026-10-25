#!/usr/bin/env bash
# Collect the venues that block GitHub's servers, on this machine, and push the
# result to local/listings.json. The push re-runs the GitHub Action, which uses
# this data for those venues (see --local in .github/workflows/publish-listings.yml).
#
# Venues to run here are listed, one slug per line, in local/20261024_venues.txt.
# Scheduled by scripts/20261024_install_timer.sh (see the README).
set -euo pipefail
cd "$(dirname "$0")/.."

# Python environment: override with LISTINGS_PYTHON=/path/to/python if needed.
if [[ -z "${LISTINGS_PYTHON:-}" ]]; then
  export PATH="$HOME/Apps/miniconda3/bin:$PATH"
  # shellcheck disable=SC1091
  source activate jupy
  LISTINGS_PYTHON=python
fi

mapfile -t VENUES < <(grep -Ev '^\s*(#|$)' local/20261024_venues.txt || true)
if [[ ${#VENUES[@]} -eq 0 ]]; then
  echo "No venues in local/20261024_venues.txt; nothing to do."
  exit 0
fi

git pull --rebase --quiet
args=()
for v in "${VENUES[@]}"; do args+=(--venue "$v"); done
"$LISTINGS_PYTHON" -m listings collect "${args[@]}" --manual-dir /nonexistent -o local/listings.json

git add local/listings.json
if git diff --cached --quiet; then
  echo "No changes."
else
  git commit --quiet -m "Local run: ${VENUES[*]}"
  git push --quiet
  echo "Pushed local/listings.json (${VENUES[*]})."
fi
