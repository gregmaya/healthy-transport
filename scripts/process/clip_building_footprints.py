"""
Clip INSPIRE Building Footprints to Nørrebro + 1,000m Buffer

Reads the full INSPIRE building footprints dataset (~2.6 GB), clips to a 1,000m
buffer around the Nørrebro boundary using a bbox mask for fast I/O followed by an
intersects filter for precision, and saves the result as a GeoPackage.

The 1,000m buffer (SCORING_BUFFER_M) ensures that buildings just outside the district
boundary contribute to health-benefit scores for near-boundary bus-route segments,
correcting the edge-truncation artifact in catchment calculations.

Usage:
    python scripts/clip_building_footprints.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
from shapely import box

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    BUILDING_FOOTPRINTS_OUTPUT,
    INSPIRE_BUILDINGS_FILE,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    SCORING_BUFFER_M,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=" * 60)
    logger.info("CLIP INSPIRE BUILDING FOOTPRINTS TO NØRREBRO + %dm BUFFER", SCORING_BUFFER_M)
    logger.info("=" * 60)

    # 1. Load boundary and create buffered version for edge-effect correction
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info("Loaded boundary: CRS %s", boundary.crs)

    buffered_boundary = boundary.buffer(SCORING_BUFFER_M).union_all()
    logger.info("Buffered boundary by %dm", SCORING_BUFFER_M)

    # 2. Create bounding box from buffered boundary for fast spatial filtering on read
    buffered_bounds = gpd.GeoSeries([buffered_boundary], crs=boundary.crs).total_bounds
    bbox = box(buffered_bounds[0], buffered_bounds[1], buffered_bounds[2], buffered_bounds[3])
    logger.info("Bounding box (buffered): %s", buffered_bounds)

    # 3. Read INSPIRE buildings masked to bbox (avoids loading full 2.6 GB)
    logger.info("Reading INSPIRE buildings within buffered bbox...")
    buildings = gpd.read_file(INSPIRE_BUILDINGS_FILE, mask=bbox)
    logger.info("Loaded %d buildings within buffered bbox", len(buildings))

    # 4. Filter to buildings that intersect the buffered boundary
    buildings_clipped = buildings[buildings.intersects(buffered_boundary)]
    logger.info(
        "Clipped to %d buildings within %dm buffer of boundary",
        len(buildings_clipped), SCORING_BUFFER_M,
    )

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
