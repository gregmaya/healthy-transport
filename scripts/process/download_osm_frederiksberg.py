"""
Download OSM address nodes for the Frederiksberg portion of the Nørrebro scoring buffer.

Outputs a GeoPackage ready for QGIS inspection — load alongside
data/processed/norrebro_buildings.gpkg (layer 'entrances') to compare
DAR vs OSM address density in the western buffer zone.

The output already uses the entrance schema (entrance_id, positioning_type,
status, geometry) so the same file can be used directly in Step 2 of the
pipeline swap (scripts/process/process_buildings.py).

Outputs:
    data/processed/osm_frederiksberg_addresses.gpkg

Usage:
    python scripts/process/download_osm_frederiksberg.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import osmnx as ox
import pandas as pd
from shapely.geometry import Point

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    MAX_WALK_DISTANCE,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    PROCESSED_DATA_DIR,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Constants ---
# Full buffer bbox (WGS84) — osmnx format: (west, south, east, north)
OSM_BBOX = (12.52, 55.665, 12.585, 55.705)

KVARTERGRAENSER_FILE = (
    PROJECT_ROOT / "data" / "raw" / "demographics" / "copenhagen_kvartergrænser.gpkg"
)
FREDERIKSBERG_KVARTERNR = 147  # integer, confirmed from kvartergrænser inspection

CRS_DENMARK = "EPSG:25832"
OUTPUT_FILE = PROCESSED_DATA_DIR / "osm_frederiksberg_addresses.gpkg"


# --- Steps ---

def download_osm_nodes() -> gpd.GeoDataFrame:
    """Fetch addr:housenumber nodes via osmnx and return as GeoDataFrame (EPSG:25832)."""
    logger.info("Fetching OSM addr:housenumber nodes via osmnx (bbox=%s) ...", OSM_BBOX)
    gdf = ox.features_from_bbox(OSM_BBOX, tags={"addr:housenumber": True})
    # osmnx returns all geometry types; keep Point nodes only
    gdf = gdf[gdf.geometry.geom_type == "Point"].copy()
    logger.info("Downloaded %d address nodes (Points only)", len(gdf))

    # osmnx index is MultiIndex (element_type, osmid) — extract osmid as a column
    gdf = gdf.reset_index()
    # Column name for OSM ID varies by osmnx version; find it
    id_col = next((c for c in gdf.columns if "osmid" in str(c).lower() or c == "id"), None)
    if id_col is None:
        # Fall back to positional index if no osmid column found
        gdf["osm_id"] = range(len(gdf))
        logger.warning("osmid column not found; using positional index as osm_id")
    else:
        gdf = gdf.rename(columns={id_col: "osm_id"})
    gdf = gdf[["osm_id", "geometry"]]
    gdf = gdf.to_crs(CRS_DENMARK)
    logger.info("Reprojected to %s", CRS_DENMARK)
    return gdf


def clip_to_frederiksberg_in_buffer(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Retain only nodes within Frederiksberg municipality ∩ MAX_WALK_DISTANCE buffer."""
    # Frederiksberg polygon
    kvarter = gpd.read_file(KVARTERGRAENSER_FILE).to_crs(CRS_DENMARK)
    fred = kvarter[kvarter["kvarternr"] == FREDERIKSBERG_KVARTERNR]
    if fred.empty:
        raise ValueError(
            f"kvarternr={FREDERIKSBERG_KVARTERNR} not found in {KVARTERGRAENSER_FILE}"
        )
    logger.info("Frederiksberg polygon loaded (%d feature(s))", len(fred))

    # Buffer around Nørrebro boundary
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER).to_crs(
        CRS_DENMARK
    )
    buf_geom = boundary.geometry.union_all().buffer(MAX_WALK_DISTANCE)
    buf_gdf = gpd.GeoDataFrame(geometry=[buf_geom], crs=CRS_DENMARK)

    # Intersection: Frederiksberg clipped to buffer
    target = gpd.overlay(fred[["geometry"]], buf_gdf, how="intersection")
    logger.info(
        "Target zone: Frederiksberg ∩ %dm buffer (%d polygon(s))", MAX_WALK_DISTANCE, len(target)
    )

    before = len(gdf)
    gdf_clip = gdf[gdf.within(target.geometry.union_all())]
    logger.info("Clipped %d → %d nodes (kept inside target zone)", before, len(gdf_clip))
    return gdf_clip


def to_entrance_schema(gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """Convert OSM nodes to the pipeline entrance schema."""
    return gpd.GeoDataFrame(
        {
            "entrance_id": "osm_" + gdf["osm_id"].astype(str),
            "positioning_type": "TK",  # facade-level — closest DAR equivalent
            "status": "8",             # active
        },
        geometry=gdf.geometry.values,
        crs=CRS_DENMARK,
    )


def save(gdf: gpd.GeoDataFrame) -> None:
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
    gdf.to_file(OUTPUT_FILE, driver="GPKG")
    size_kb = OUTPUT_FILE.stat().st_size // 1024
    logger.info("Saved %d features → %s (%d KB)", len(gdf), OUTPUT_FILE, size_kb)


def main():
    logger.info("=" * 60)
    logger.info("DOWNLOAD OSM ADDRESSES — Frederiksberg buffer zone")
    logger.info("=" * 60)

    osm = download_osm_nodes()
    logger.info("Step 1 done: %d nodes downloaded", len(osm))

    osm = clip_to_frederiksberg_in_buffer(osm)
    logger.info("Step 2 done: %d nodes after Frederiksberg clip", len(osm))

    if osm.empty:
        logger.error("No nodes remain after clip — check geometry or bbox")
        sys.exit(1)

    result = to_entrance_schema(osm)
    logger.info("Step 3 done: schema converted")

    save(result)

    logger.info("=" * 60)
    logger.info("SUMMARY")
    logger.info("  Final OSM nodes (Frederiksberg buffer): %d", len(result))
    logger.info("  All entrance_id start with 'osm_'")
    logger.info("  positioning_type: TK  |  status: 8  |  CRS: %s", CRS_DENMARK)
    logger.info("=" * 60)
    logger.info(
        "Open in QGIS: %s", OUTPUT_FILE
    )
    logger.info(
        "Compare with: data/processed/norrebro_buildings.gpkg (layer 'entrances')"
    )


if __name__ == "__main__":
    main()
