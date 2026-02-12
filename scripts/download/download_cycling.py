"""
Download Copenhagen cycling infrastructure from Copenhagen Municipality WFS.

Downloads three citywide layers (no clipping):
- cykelsti: Physical cycle paths with type classification and width
- cykeldata: Broader cycling network (paths, supercykelstier, green routes, etc.)
- cykelstativ: Bike parking points with capacity

Source: Copenhagen Municipality WFS (https://wfs-kbhkort.kk.dk/k101/ows)
No authentication required.

Outputs:
    data/raw/cycling/kk_cykelsti.gpkg
    data/raw/cycling/kk_cykeldata.gpkg
    data/raw/cycling/kk_cykelstativ.gpkg

Usage:
    python scripts/download_cycling.py
"""

import logging
import sys
import tempfile
from pathlib import Path

import geopandas as gpd
import requests

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    CRS_DENMARK,
    CYCLING_RAW_DIR,
    KK_CYCLING_LAYERS,
    KK_WFS_URL,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def download_wfs_layer(layer_name: str, type_name: str) -> gpd.GeoDataFrame:
    """Download a WFS layer from Copenhagen Municipality as GeoDataFrame."""
    params = {
        "service": "WFS",
        "version": "1.0.0",
        "request": "GetFeature",
        "typeName": type_name,
        "outputFormat": "json",
        "SRSNAME": "EPSG:4326",
    }

    logger.info("Downloading %s (%s)...", layer_name, type_name)
    response = requests.get(KK_WFS_URL, params=params, timeout=120)
    response.raise_for_status()

    # Write to temp file and read with geopandas
    with tempfile.NamedTemporaryFile(suffix=".geojson", delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        gdf = gpd.read_file(tmp_path)
    finally:
        Path(tmp_path).unlink()

    logger.info("  Downloaded %d features", len(gdf))
    return gdf


def log_distribution(gdf: gpd.GeoDataFrame, column: str, label: str):
    """Log value distribution for a column."""
    if column not in gdf.columns:
        return
    logger.info("  %s distribution:", label)
    for val, count in gdf[column].value_counts().items():
        logger.info("    %s: %d", val, count)


def main():
    logger.info("=" * 60)
    logger.info("COPENHAGEN CYCLING INFRASTRUCTURE DOWNLOAD")
    logger.info("=" * 60)

    CYCLING_RAW_DIR.mkdir(parents=True, exist_ok=True)

    for layer_name, type_name in KK_CYCLING_LAYERS.items():
        logger.info("-" * 60)

        gdf = download_wfs_layer(layer_name, type_name)

        if gdf.empty:
            logger.warning("  No features returned for %s", layer_name)
            continue

        # Reproject to Danish CRS
        gdf = gdf.to_crs(CRS_DENMARK)
        logger.info("  Reprojected to %s", CRS_DENMARK)

        # Log type distributions
        if layer_name == "cykelsti":
            log_distribution(gdf, "beskrivelse", "sti_type")
        elif layer_name == "cykeldata":
            log_distribution(gdf, "kategori", "kategori")

        # Save
        output_path = CYCLING_RAW_DIR / f"kk_{layer_name}.gpkg"
        gdf.to_file(output_path, driver="GPKG")
        size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info("  Saved: %s (%.1f MB, %d features)", output_path, size_mb, len(gdf))

    # Summary
    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)
    for layer_name in KK_CYCLING_LAYERS:
        path = CYCLING_RAW_DIR / f"kk_{layer_name}.gpkg"
        if path.exists():
            size_mb = path.stat().st_size / (1024 * 1024)
            logger.info("  %s (%.1f MB)", path, size_mb)
        else:
            logger.info("  %s — not created", path)


if __name__ == "__main__":
    main()
