"""
Export park polygons to data/web/ for the parks map overlay.

Reads the processed parks layer (77 MultiPolygon features, EPSG:25832),
selects display columns, reprojects to WGS84, and writes a compact GeoJSON.

Output:
    data/web/norrebro_parks.geojson

Usage:
    python scripts/web/export_parks.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import CRS_WGS84, GREENSPACES_OUTPUT, WEB_PARKS_GEOJSON

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

DISPLAY_COLS = ["park_id", "park_name", "park_type", "area_name", "area_m2", "geometry"]


def main() -> None:
    log.info("Loading parks from %s (layer='parks')", GREENSPACES_OUTPUT)
    parks = gpd.read_file(GREENSPACES_OUTPUT, layer="parks")
    log.info("Parks: %d features  CRS: %s", len(parks), parks.crs)

    # Select only the columns needed for display
    missing = [c for c in DISPLAY_COLS if c not in parks.columns and c != "geometry"]
    if missing:
        log.warning("Expected display columns not found: %s", missing)
    keep = [c for c in DISPLAY_COLS if c in parks.columns]
    parks = parks[keep]

    parks = parks.to_crs(CRS_WGS84)

    WEB_PARKS_GEOJSON.parent.mkdir(parents=True, exist_ok=True)
    parks.to_file(WEB_PARKS_GEOJSON, driver="GeoJSON")
    log.info(
        "Exported → %s  (%d features, %.0f KB)",
        WEB_PARKS_GEOJSON,
        len(parks),
        WEB_PARKS_GEOJSON.stat().st_size / 1024,
    )


if __name__ == "__main__":
    main()
