#!/usr/bin/env bash
# Local dev server — mirrors the GitHub Pages deployment structure.
# Run from project root: bash scripts/dev.sh
set -e

DIST="dist"

echo "Building dev dist..."
rm -rf "$DIST"
mkdir -p "$DIST/data/web"

cp -r web/* "$DIST/"

if ls data/web/*.geojson 1>/dev/null 2>&1; then
  cp data/web/*.geojson "$DIST/data/web/"
  echo "  GeoJSON files copied."
else
  echo "  WARNING: No GeoJSON files found in data/web/"
  echo "  Run the export cells in notebooks/11_candidate_segments.ipynb first."
fi

echo "Serving at http://localhost:8000"
python -m http.server 8000 --directory "$DIST"
