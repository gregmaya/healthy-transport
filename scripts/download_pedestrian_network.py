"""
Download Pedestrian Network for Nørrebro from OpenStreetMap

Downloads a walkable street network using osmnx, including footways, paths,
pedestrian zones, and all streets accessible to pedestrians. The boundary is
buffered by 800m to capture network segments leading to facilities just outside
the study area.

Outputs:
- GraphML (WGS84) for routing via ox.load_graphml()
- GeoPackage (EPSG:25832) with nodes + edges layers for QGIS

Usage:
    python scripts/download_pedestrian_network.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import osmnx as ox

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    CRS_DENMARK,
    CRS_WGS84,
    NETWORK_BUFFER_M,
    NETWORK_RAW_DIR,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    PEDESTRIAN_NETWORK_GPKG,
    PEDESTRIAN_NETWORK_GRAPHML,
    WALKING_SPEED,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_boundary():
    """Load the Nørrebro boundary in EPSG:25832."""
    if not NORREBRO_BOUNDARY_FILE.exists():
        logger.error("Boundary file not found: %s", NORREBRO_BOUNDARY_FILE)
        sys.exit(1)
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info(
        "Loaded boundary: %d features, %.2f km², CRS %s",
        len(boundary),
        boundary.geometry.area.sum() / 1e6,
        boundary.crs,
    )
    return boundary


def create_buffered_polygon(boundary_gdf, buffer_m):
    """
    Buffer the boundary in EPSG:25832 and return a single polygon in WGS84.

    The buffer ensures we capture network edges just outside the study area,
    which is critical for routing to facilities near the boundary.
    """
    dissolved = boundary_gdf.dissolve()
    buffered = dissolved.geometry.buffer(buffer_m).iloc[0]
    logger.info(
        "Buffered boundary by %dm (area: %.2f km²)",
        buffer_m,
        buffered.area / 1e6,
    )
    # Convert to WGS84 for osmnx
    buffered_gdf = gpd.GeoDataFrame(geometry=[buffered], crs=CRS_DENMARK)
    buffered_wgs84 = buffered_gdf.to_crs(CRS_WGS84)
    return buffered_wgs84.geometry.iloc[0]


def download_pedestrian_graph(polygon_wgs84):
    """
    Download complete street network from OSM using osmnx.

    network_type='all' includes every road and path type (driving, walking,
    cycling). Filtering by mode can be done downstream during analysis.
    truncate_by_edge=True keeps full edges that cross the boundary polygon.
    """
    logger.info("Downloading street network from OSM...")
    G = ox.graph_from_polygon(
        polygon_wgs84,
        network_type="all",
        simplify=True,
        retain_all=False,
        truncate_by_edge=True,
    )
    logger.info(
        "Downloaded graph: %d nodes, %d edges",
        G.number_of_nodes(),
        G.number_of_edges(),
    )
    return G


def add_walking_travel_times(G, walking_speed_mps):
    """
    Add walking travel time (seconds) to each edge.

    Uses a constant walking speed rather than osmnx's add_edge_speeds()
    which is designed for driving (uses maxspeed tags).
    """
    for _, _, data in G.edges(data=True):
        data["travel_time"] = data.get("length", 0) / walking_speed_mps

    logger.info(
        "Added walking travel times at %.1f m/s (%.0f km/h)",
        walking_speed_mps,
        walking_speed_mps * 3.6,
    )
    return G


def save_outputs(G):
    """
    Save the network in two formats:
    1. GraphML (WGS84) - for loading back into NetworkX for routing
    2. GeoPackage (EPSG:25832) - for QGIS visualization
    """
    # Ensure output directories exist
    NETWORK_RAW_DIR.mkdir(parents=True, exist_ok=True)
    PEDESTRIAN_NETWORK_GPKG.parent.mkdir(parents=True, exist_ok=True)

    # 1. Save GraphML in WGS84 (osmnx native format)
    ox.save_graphml(G, filepath=PEDESTRIAN_NETWORK_GRAPHML)
    size_mb = PEDESTRIAN_NETWORK_GRAPHML.stat().st_size / (1024 * 1024)
    logger.info("Saved GraphML: %s (%.1f MB)", PEDESTRIAN_NETWORK_GRAPHML, size_mb)

    # 2. Project to EPSG:25832 and save GeoPackage
    G_projected = ox.project_graph(G, to_crs=CRS_DENMARK)
    ox.save_graph_geopackage(G_projected, filepath=PEDESTRIAN_NETWORK_GPKG, directed=False)
    size_mb = PEDESTRIAN_NETWORK_GPKG.stat().st_size / (1024 * 1024)
    logger.info("Saved GeoPackage: %s (%.1f MB)", PEDESTRIAN_NETWORK_GPKG, size_mb)

    # Log network summary
    nodes_gdf, edges_gdf = ox.graph_to_gdfs(G_projected)
    total_km = edges_gdf["length"].sum() / 1000
    logger.info("Network summary:")
    logger.info("  Nodes: %d", len(nodes_gdf))
    logger.info("  Edges: %d", len(edges_gdf))
    logger.info("  Total length: %.1f km", total_km)
    logger.info("  CRS (GeoPackage): %s", edges_gdf.crs)

    if "highway" in edges_gdf.columns:
        logger.info("  Highway type distribution:")
        highway_series = edges_gdf["highway"].explode()
        for val, count in highway_series.value_counts().head(10).items():
            logger.info("    %s: %d", val, count)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("PEDESTRIAN NETWORK DOWNLOAD FOR NØRREBRO")
    logger.info("=" * 60)

    # 1. Load boundary
    boundary = load_boundary()

    # 2. Create buffered polygon in WGS84
    polygon_wgs84 = create_buffered_polygon(boundary, NETWORK_BUFFER_M)

    # 3. Download pedestrian graph
    G = download_pedestrian_graph(polygon_wgs84)

    # 4. Add walking travel times
    G = add_walking_travel_times(G, WALKING_SPEED)

    # 5. Save outputs
    save_outputs(G)

    logger.info("=" * 60)
    logger.info("DOWNLOAD COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
