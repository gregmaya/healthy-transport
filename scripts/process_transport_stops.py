"""
Process Transport Stops and Routes from Rejseplanen GTFS Feed

Extracts bus, metro, and train stops/routes from the national GTFS zip,
classifies by transport mode, clips to a 10 km buffer around Nørrebro,
and saves as a two-layer GeoPackage (stops + routes) in EPSG:25832.

Route geometries come from GTFS shapes.txt (actual GPS traces along roads),
not from connecting stop points. Each route × direction gets one LineString.

Early filtering: stops are spatially filtered before joining with the
large stop_times table to minimise memory and processing time.

Outputs:
- data/processed/norrebro_transport_stops.gpkg
  - Layer 'stops': point geometries, one row per (stop, mode) pair
  - Layer 'routes': line geometries from shapes.txt, one row per (route, direction)

Usage:
    python scripts/process_transport_stops.py
"""

import logging
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    CRS_DENMARK,
    CRS_WGS84,
    GTFS_ROUTE_TYPES,
    GTFS_ZIP_FILE,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    TRANSPORT_BUFFER_M,
    TRANSPORT_STOPS_OUTPUT,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: read a CSV from inside the GTFS zip
# ---------------------------------------------------------------------------


def read_gtfs_table(zf, filename, usecols=None, dtype=None):
    """Read a CSV file from inside the GTFS zip archive."""
    with zf.open(filename) as f:
        df = pd.read_csv(BytesIO(f.read()), usecols=usecols, dtype=dtype)
    logger.info("  %s: %d rows", filename, len(df))
    return df


# ---------------------------------------------------------------------------
# Functions
# ---------------------------------------------------------------------------


def load_buffered_boundary():
    """Load Nørrebro boundary and buffer by TRANSPORT_BUFFER_M in EPSG:25832."""
    if not NORREBRO_BOUNDARY_FILE.exists():
        logger.error("Boundary file not found: %s", NORREBRO_BOUNDARY_FILE)
        sys.exit(1)

    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info("Loaded boundary: CRS %s", boundary.crs)

    dissolved = boundary.dissolve()
    buffered_geom = dissolved.geometry.buffer(TRANSPORT_BUFFER_M).iloc[0]
    buffered_gdf = gpd.GeoDataFrame(geometry=[buffered_geom], crs=CRS_DENMARK)

    logger.info(
        "Buffered boundary by %d m (area: %.1f km²)",
        TRANSPORT_BUFFER_M,
        buffered_geom.area / 1e6,
    )
    return buffered_gdf


def load_and_filter_stops(zf, buffered_boundary):
    """
    Load stops from GTFS, reproject to EPSG:25832, and filter to boundary.

    This is done first so we can use the filtered stop_ids to reduce the
    size of stop_times before joining.
    """
    stops_df = read_gtfs_table(
        zf,
        "stops.txt",
        usecols=["stop_id", "stop_name", "stop_lat", "stop_lon",
                 "location_type", "parent_station"],
        dtype={"stop_id": str, "parent_station": str},
    )

    # Create geometry and reproject to EPSG:25832 immediately
    geometry = [Point(lon, lat) for lon, lat in zip(stops_df["stop_lon"], stops_df["stop_lat"])]
    stops_gdf = gpd.GeoDataFrame(stops_df, geometry=geometry, crs=CRS_WGS84)
    stops_gdf = stops_gdf.to_crs(CRS_DENMARK)
    stops_gdf = stops_gdf.drop(columns=["stop_lat", "stop_lon"])

    logger.info("All stops (national): %d", len(stops_gdf))

    # Fast bbox filter, then precise boundary filter
    bbox = buffered_boundary.total_bounds  # (minx, miny, maxx, maxy)
    stops_gdf = stops_gdf.cx[bbox[0]:bbox[2], bbox[1]:bbox[3]]
    boundary_geom = buffered_boundary.geometry.iloc[0]
    stops_gdf = stops_gdf[stops_gdf.intersects(boundary_geom)].copy()

    logger.info("Stops within 10 km buffer: %d", len(stops_gdf))
    return stops_gdf


def classify_route_type(route_type):
    """Map a GTFS route_type to our transport mode categories."""
    for mode, type_codes in GTFS_ROUTE_TYPES.items():
        if route_type in type_codes:
            return mode
    return None


def build_stop_mode_mapping(zf, filtered_stop_ids):
    """
    Determine which transport modes serve each stop.

    Joins routes → trips → stop_times, filtered to our spatial subset.
    Returns a DataFrame with columns: stop_id, transport_mode.
    """
    # Read routes and trips (small files, load fully)
    routes_df = read_gtfs_table(
        zf, "routes.txt",
        usecols=["route_id", "route_type", "route_short_name"],
        dtype={"route_id": str},
    )
    trips_df = read_gtfs_table(
        zf, "trips.txt",
        usecols=["trip_id", "route_id", "direction_id", "shape_id"],
        dtype={"trip_id": str, "route_id": str, "shape_id": str},
    )

    # Read stop_times — largest file, filter to our stop_ids immediately
    stop_times_df = read_gtfs_table(
        zf, "stop_times.txt",
        usecols=["trip_id", "stop_id", "stop_sequence"],
        dtype={"trip_id": str, "stop_id": str},
    )
    original_count = len(stop_times_df)
    stop_times_df = stop_times_df[stop_times_df["stop_id"].isin(filtered_stop_ids)]
    logger.info(
        "Filtered stop_times: %d → %d rows (%.1f%% reduction)",
        original_count, len(stop_times_df),
        (1 - len(stop_times_df) / original_count) * 100 if original_count > 0 else 0,
    )

    # Classify routes by transport mode
    routes_df["transport_mode"] = routes_df["route_type"].apply(classify_route_type)
    routes_df = routes_df.dropna(subset=["transport_mode"])
    logger.info("Routes by mode: %s", routes_df["transport_mode"].value_counts().to_dict())

    # Join: routes → trips → stop_times
    trips_with_mode = trips_df.merge(
        routes_df[["route_id", "transport_mode", "route_short_name"]],
        on="route_id",
        how="inner",
    )
    stop_modes = stop_times_df.merge(
        trips_with_mode[["trip_id", "transport_mode"]],
        on="trip_id",
        how="inner",
    )

    # Unique (stop_id, transport_mode) pairs
    stop_mode_pairs = stop_modes[["stop_id", "transport_mode"]].drop_duplicates()
    logger.info("Unique (stop, mode) pairs: %d", len(stop_mode_pairs))

    return stop_mode_pairs, routes_df, trips_with_mode, stop_times_df


def build_stops_layer(stops_gdf, stop_mode_pairs):
    """
    Build the stops layer: one row per (stop, mode) pair.

    Handles parent/child stations: keeps parent stations (location_type=1)
    and standalone stops (location_type=0 or NaN). Child stops
    (location_type=0 with a parent_station) are rolled up to their parent.
    """
    # Roll up child stops to parent stations where applicable
    has_parent = stops_gdf["parent_station"].notna() & (stops_gdf["parent_station"] != "")
    child_to_parent = dict(zip(
        stops_gdf.loc[has_parent, "stop_id"],
        stops_gdf.loc[has_parent, "parent_station"],
    ))

    if child_to_parent:
        logger.info("Rolling up %d child stops to parent stations", len(child_to_parent))
        stop_mode_pairs = stop_mode_pairs.copy()
        stop_mode_pairs["stop_id"] = stop_mode_pairs["stop_id"].replace(child_to_parent)
        stop_mode_pairs = stop_mode_pairs.drop_duplicates()

    # Join mode information to stop geometries
    result = stops_gdf.merge(stop_mode_pairs, on="stop_id", how="inner")

    # Drop parent/child metadata columns
    result = result.drop(columns=["location_type", "parent_station"], errors="ignore")

    logger.info("Stops layer: %d features", len(result))
    logger.info("  By mode: %s", result["transport_mode"].value_counts().to_dict())
    return result


def build_shapes_lookup(zf, buffered_boundary):
    """
    Build a dictionary of shape_id → LineString from GTFS shapes.txt.

    Reads shape points, converts to EPSG:25832, builds LineStrings,
    and keeps only shapes that intersect the buffered boundary.
    """
    shapes_df = read_gtfs_table(
        zf, "shapes.txt",
        usecols=["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
        dtype={"shape_id": str},
    )
    shapes_df = shapes_df.sort_values(["shape_id", "shape_pt_sequence"])

    # Build LineStrings per shape_id (in WGS84 first)
    shape_lines = {}
    for shape_id, group in shapes_df.groupby("shape_id"):
        coords = list(zip(group["shape_pt_lon"], group["shape_pt_lat"]))
        if len(coords) >= 2:
            shape_lines[shape_id] = LineString(coords)

    logger.info("Built %d shape geometries from shapes.txt", len(shape_lines))

    # Convert to GeoDataFrame, reproject to EPSG:25832, then filter to boundary
    shapes_gdf = gpd.GeoDataFrame(
        {"shape_id": list(shape_lines.keys())},
        geometry=list(shape_lines.values()),
        crs=CRS_WGS84,
    )
    shapes_gdf = shapes_gdf.to_crs(CRS_DENMARK)

    boundary_geom = buffered_boundary.geometry.iloc[0]
    shapes_gdf = shapes_gdf[shapes_gdf.intersects(boundary_geom)].copy()
    logger.info("Shapes within 10 km buffer: %d", len(shapes_gdf))

    return dict(zip(shapes_gdf["shape_id"], shapes_gdf.geometry))


def build_routes_layer(routes_df, trips_with_mode, shape_lookup):
    """
    Build the routes layer: one line per (route, direction).

    Uses actual GPS traces from GTFS shapes.txt rather than connecting
    stop points. Each route × direction is linked to a shape_id via trips.
    """
    # Pick one representative trip per (route_id, direction_id)
    # Prefer trips that have a shape_id
    trips_with_shape = trips_with_mode[
        trips_with_mode["shape_id"].notna() & (trips_with_mode["shape_id"] != "")
    ].copy()

    representative_trips = (
        trips_with_shape
        .sort_values("trip_id")
        .groupby(["route_id", "direction_id"], as_index=False)
        .first()
    )
    logger.info("Representative trips (route × direction): %d", len(representative_trips))

    # Match each representative trip to its shape geometry
    route_lines = []
    missing_shapes = 0
    for _, trip_row in representative_trips.iterrows():
        shape_id = trip_row.get("shape_id")
        geom = shape_lookup.get(str(shape_id)) if pd.notna(shape_id) else None

        if geom is not None:
            route_lines.append({
                "route_id": trip_row["route_id"],
                "route_short_name": trip_row.get("route_short_name", ""),
                "transport_mode": trip_row["transport_mode"],
                "direction_id": trip_row["direction_id"],
                "geometry": geom,
            })
        else:
            missing_shapes += 1

    if missing_shapes:
        logger.info("Skipped %d route×direction pairs with no shape in buffer", missing_shapes)

    routes_gdf = gpd.GeoDataFrame(route_lines, crs=CRS_DENMARK)
    logger.info("Routes layer: %d features", len(routes_gdf))
    logger.info("  By mode: %s", routes_gdf["transport_mode"].value_counts().to_dict())
    return routes_gdf


def save_output(stops_gdf, routes_gdf):
    """Save both layers to a single GeoPackage."""
    TRANSPORT_STOPS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    stops_gdf.to_file(TRANSPORT_STOPS_OUTPUT, layer="stops", driver="GPKG")
    routes_gdf.to_file(TRANSPORT_STOPS_OUTPUT, layer="routes", driver="GPKG", mode="a")

    size_mb = TRANSPORT_STOPS_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info("Saved: %s (%.1f MB)", TRANSPORT_STOPS_OUTPUT, size_mb)
    logger.info("  Layers: stops (%d features), routes (%d features)",
                len(stops_gdf), len(routes_gdf))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("PROCESS TRANSPORT STOPS FOR NØRREBRO")
    logger.info("=" * 60)

    # 0. Check GTFS zip exists
    if not GTFS_ZIP_FILE.exists():
        logger.error("GTFS zip not found: %s", GTFS_ZIP_FILE)
        logger.error("Run scripts/download_gtfs.py first.")
        sys.exit(1)

    # 1. Load buffered boundary
    buffered_boundary = load_buffered_boundary()

    with zipfile.ZipFile(GTFS_ZIP_FILE, "r") as zf:
        logger.info("Opened GTFS zip: %s", GTFS_ZIP_FILE)
        logger.info("Contents: %s", [f.filename for f in zf.filelist])

        # 2. Load stops and filter spatially (early filtering)
        stops_gdf = load_and_filter_stops(zf, buffered_boundary)

        if stops_gdf.empty:
            logger.warning("No stops found within buffer. Check boundary and GTFS data.")
            sys.exit(1)

        # 3. Build stop ↔ mode mapping (filters stop_times to our stop_ids)
        stop_mode_pairs, routes_df, trips_with_mode, stop_times_df = (
            build_stop_mode_mapping(zf, set(stops_gdf["stop_id"]))
        )

        # 4. Build shape geometries from shapes.txt (actual GPS traces)
        shape_lookup = build_shapes_lookup(zf, buffered_boundary)

    # 5. Build stops layer (one row per stop × mode)
    stops_layer = build_stops_layer(stops_gdf, stop_mode_pairs)

    # 6. Build routes layer from shapes.txt (one line per route × direction)
    routes_layer = build_routes_layer(routes_df, trips_with_mode, shape_lookup)

    # 7. Save
    save_output(stops_layer, routes_layer)

    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
