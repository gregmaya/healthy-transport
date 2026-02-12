"""
Clip INSPIRE Building Footprints to Nørrebro Boundary

Reads the full INSPIRE building footprints dataset (~2.6 GB), clips to the
Nørrebro boundary using a bbox mask for fast I/O followed by an intersects
filter for precision, and saves the result as a GeoPackage.

Usage:
    python scripts/clip_building_footprints.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
from shapely import box

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    BUILDING_FOOTPRINTS_OUTPUT,
    INSPIRE_BUILDINGS_FILE,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("CLIP INSPIRE BUILDING FOOTPRINTS TO NØRREBRO")
    logger.info("=" * 60)

    # 1. Load boundary
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info("Loaded boundary: CRS %s", boundary.crs)

    # 2. Create bounding box for fast spatial filtering on read
    bounds = boundary.total_bounds
    bbox = box(bounds[0], bounds[1], bounds[2], bounds[3])
    logger.info("Bounding box: %s", bounds)

    # 3. Read INSPIRE buildings masked to bbox (avoids loading full 2.6 GB)
    logger.info("Reading INSPIRE buildings within bbox...")
    buildings = gpd.read_file(INSPIRE_BUILDINGS_FILE, mask=bbox)
    logger.info("Loaded %d buildings within bbox", len(buildings))

    # 4. Filter to buildings that intersect the actual boundary
    buildings_clipped = buildings[buildings.intersects(boundary.unary_union)]
    logger.info("Clipped to %d buildings within boundary", len(buildings_clipped))

    # 5. Save
    BUILDING_FOOTPRINTS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    buildings_clipped.to_file(BUILDING_FOOTPRINTS_OUTPUT, driver="GPKG")
    size_mb = BUILDING_FOOTPRINTS_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info("Saved: %s (%.1f MB)", BUILDING_FOOTPRINTS_OUTPUT, size_mb)

    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
