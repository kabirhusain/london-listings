#!/usr/bin/env bash
# Assemble the GitHub Pages site around listings.json and status.json.
#
#   scripts/20261122_build_site.sh site
#
# SITE_DIR must already contain listings.json and status.json (from a collector
# run, or downloaded from the live site). Adds:
#   status.html          venue-health table
#   data/soon.json       website feed, next ~2 weeks
#   data/later.json      website feed, the rest
#   index.html, assets/  the London Calling website (built from web/)
#   .nojekyll
# Both publish workflows call this, so the site is always built the same way.
set -euo pipefail

site="$(realpath "${1:-site}")"
repo="$(cd "$(dirname "$0")/.." && pwd)"
python="${PYTHON:-python}"

"$python" "$repo/scripts/20261024_make_index.py" "$site"
"$python" "$repo/scripts/20261122_make_web_feed.py" "$site"

(cd "$repo/web" && npm ci --no-audit --no-fund && npm run build)
cp -r "$repo/web/dist/." "$site/"
touch "$site/.nojekyll"

echo "Site assembled in $site"
