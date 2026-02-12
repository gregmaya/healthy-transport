"""
Process Copenhagen cycling infrastructure into a single GeoPackage.

Combines two layers:
- cykeldata: Broader cycling network (citywide, no clipping)
- cykelstativ: Bike parking points (clipped to 800m buffer around Nørrebro)

Outputs:
    data/processed/norrebro_cycling.gpkg
        Layer 'cykeldata': 3,638 cycling network lines (citywide)
        Layer 'cykelstativ': bike parking points within 800m of Nørrebro

Usage:
    python scripts/process_cycling.py
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
    CYCLING_OUTPUT,
    CYCLING_RAW_DIR,
    MAX_WALK_DISTANCE,
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
    logger.info("PROCESS CYCLING INFRASTRUCTURE")
    logger.info("=" * 60)

    # --- Layer 1: cykeldata (no clipping) ---
    logger.info("-" * 60)
    logger.info("LAYER 1: cykeldata (citywide, no clipping)")
    logger.info("-" * 60)

    cykeldata_path = CYCLING_RAW_DIR / "kk_cykeldata.gpkg"
    cykeldata = gpd.read_file(cykeldata_path)
    logger.info("Loaded %d cycling features from %s", len(cykeldata), cykeldata_path.name)

    CYCLING_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    cykeldata.to_file(CYCLING_OUTPUT, layer="cykeldata", driver="GPKG")
    logger.info("Saved layer 'cykeldata': %d features", len(cykeldata))

    # --- Layer 2: cykelstativ (clipped to 800m buffer) ---
    logger.info("-" * 60)
    logger.info("LAYER 2: cykelstativ (clipped to %dm buffer)", MAX_WALK_DISTANCE)
    logger.info("-" * 60)

    # Load boundary and create buffer
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info("Loaded boundary: CRS %s", boundary.crs)

    buffered = boundary.buffer(MAX_WALK_DISTANCE).union_all()
    bbox = box(*gpd.GeoSeries([buffered], crs=boundary.crs).total_bounds)

    # Read and clip
    cykelstativ_path = CYCLING_RAW_DIR / "kk_cykelstativ.gpkg"
    cykelstativ = gpd.read_file(cykelstativ_path, mask=bbox)
    logger.info("Loaded %d bike parking points within bbox", len(cykelstativ))

    cykelstativ_clipped = cykelstativ[cykelstativ.intersects(buffered)]
    logger.info("Clipped to %d points within %dm buffer", len(cykelstativ_clipped), MAX_WALK_DISTANCE)

    cykelstativ_clipped.to_file(CYCLING_OUTPUT, layer="cykelstativ", driver="GPKG", mode="a")
    logger.info("Saved layer 'cykelstativ': %d features", len(cykelstativ_clipped))

    # --- Summary ---
    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)
    size_mb = CYCLING_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info("Output: %s (%.1f MB)", CYCLING_OUTPUT, size_mb)


if __name__ == "__main__":
    main()
