"""
Remap bus health scores to actual bus route geometries and export all web layers.

Replaces norrebro_bus_segments_scored.geojson (pedestrian network segments)
with scored segments whose geometry comes from the GTFS bus route lines.
GTFS routes are coordinate-snapped before union to merge parallel lines on the
same physical street (avoids duplicate click targets for the same corridor).

Also exports:
  - Grey context bus routes (outside scoring zone, within 2km)
  - Stops enriched with route_names + context flag (internal vs 2km context)
  - Neighbourhood polygons with population density
  - Entrance-level demographics for heatmap rendering

Outputs:
  data/web/norrebro_bus_segments_scored.geojson  -- ~1,400 scored 20m segments
  data/web/norrebro_bus_routes_context.geojson   -- grey context lines (2km beyond boundary)
  data/web/norrebro_stops.geojson                -- enriched, clipped to 2km, with context flag
  data/web/norrebro_neighbourhoods.geojson       -- 5 polygons with population density
  data/web/norrebro_demographics.geojson         -- entrance points with pop_total_mid

Usage:
  python scripts/export/export_bus_route_segments.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import set_precision
from shapely.geometry import LineString
from shapely.ops import unary_union
from shapely.strtree import STRtree

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.config import (
    CRS_DENMARK,
    CRS_WGS84,
    INTEGRATED_BUILDINGS,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    POPULATION_CSV,
    TRANSPORT_STOPS_OUTPUT,
    WEB_DATA_DIR,
    WEB_SEGMENTS_GEOJSON,
    WEB_STOPS_GEOJSON,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

WEB_BUS_CONTEXT_GEOJSON    = WEB_DATA_DIR / "norrebro_bus_routes_context.geojson"
WEB_NEIGHBOURHOODS_GEOJSON = WEB_DATA_DIR / "norrebro_neighbourhoods.geojson"
WEB_DEMOGRAPHICS_GEOJSON   = WEB_DATA_DIR / "norrebro_demographics.geojson"

SCORE_BUFFER_M   = 20      # scoring zone: district + this outward buffer
CONTEXT_BUFFER_M = 2000    # context zone: up to 2km beyond district
SNAP_GRID_M      = 5.0     # coordinate grid for merging nearby GTFS lines (metres)
SEG_MAX_LEN_M    = 20      # decompose bus routes into ≤20m segments
SEG_MIN_LEN_M    = 3       # drop degenerate sub-segments below this length
ROUTE_SNAP_M     = 15      # buffer around each segment to find overlapping routes
SCORE_SNAP_M     = 30      # search radius for neighbouring pedestrian segments
STOP_ROUTE_BUF_M = 30      # radius to associate routes with a stop

# gm_id → neighbourhood_name mapping (confirmed from entrances_demographics layer)
GM_TO_NAME = {
    1: "Stefansgade",
    2: "Mimersgade-kvarteret",
    3: "Haraldsgade-kvarteret",
    4: "Guldbergskvarteret",
    5: "Blagardskvarteret",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def decompose_line(line: LineString, max_len: float = SEG_MAX_LEN_M) -> list[LineString]:
    """Split a LineString into sub-segments of at most max_len metres."""
    seg = line.segmentize(max_len)
    coords = list(seg.coords)
    return [LineString([coords[i], coords[i + 1]]) for i in range(len(coords) - 1)]


def route_names_for_geoms(geoms, route_gdf: gpd.GeoDataFrame, buffer_m: float) -> list[str]:
    """
    For each geometry in geoms, find all overlapping routes within buffer_m
    and return their route_short_names as a comma-separated sorted string.
    """
    route_tree = STRtree(route_gdf.geometry.values)
    result = []
    for geom in geoms:
        buf = geom.buffer(buffer_m)
        idxs = route_tree.query(buf)
        names = sorted({
            route_gdf.iloc[i]["route_short_name"]
            for i in idxs
            if route_gdf.iloc[i].geometry.intersects(buf)
        })
        result.append(", ".join(names))
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # --- Load boundary ---
    log.info("Loading boundary from %s", NORREBRO_BOUNDARY_FILE)
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER).to_crs(CRS_DENMARK)
    boundary_poly = boundary.geometry.union_all()
    log.info("Boundary CRS: %s", boundary.crs)

    score_zone   = boundary_poly.buffer(SCORE_BUFFER_M)
    context_zone = boundary_poly.buffer(CONTEXT_BUFFER_M)
    log.info("Score zone: district + %dm | Context zone: district + %dm", SCORE_BUFFER_M, CONTEXT_BUFFER_M)

    # ==========================================================================
    # BUS ROUTE SEGMENTS
    # ==========================================================================

    # --- Load bus routes (city-wide) ---
    log.info("Loading bus routes from %s", TRANSPORT_STOPS_OUTPUT)
    routes = gpd.read_file(TRANSPORT_STOPS_OUTPUT, layer="routes")
    bus = routes[routes["transport_mode"] == "bus"].to_crs(CRS_DENMARK).reset_index(drop=True)
    log.info("Bus routes loaded: %d", len(bus))

    # --- Clip to scoring zone ---
    bus_score_clip = gpd.clip(bus, score_zone).reset_index(drop=True)
    log.info("Bus routes in scoring zone: %d  (%.0fm total)", len(bus_score_clip), bus_score_clip.geometry.length.sum())

    # --- Clip to context zone ---
    bus_context_clip = gpd.clip(bus, context_zone).reset_index(drop=True)
    log.info("Bus routes in context zone: %d", len(bus_context_clip))

    # --- Snap coordinates to 5m grid before dissolve ---
    # This merges GTFS lines for different routes that run on the same physical
    # street but were traced independently (typically offset by 1–4m).
    # Without snapping, unary_union leaves parallel near-duplicate corridors
    # that create stacked clickable features on the same street.
    log.info("Snapping routes to %.0fm coordinate grid before dissolve ...", SNAP_GRID_M)
    snapped = bus_score_clip.geometry.apply(lambda g: set_precision(g, SNAP_GRID_M))
    dissolved = unary_union(snapped)
    total_len = dissolved.length
    log.info("Dissolved bus corridors: %.0fm (was %.0fm before dissolve)", total_len, bus_score_clip.geometry.length.sum())

    # --- Decompose to ≤20m segments ---
    raw_segs = []
    geoms = list(dissolved.geoms) if hasattr(dissolved, "geoms") else [dissolved]
    for geom in geoms:
        if geom.geom_type == "LineString":
            raw_segs.extend(decompose_line(geom))
        elif geom.geom_type == "MultiLineString":
            for part in geom.geoms:
                raw_segs.extend(decompose_line(part))

    bus_segs = gpd.GeoDataFrame(geometry=raw_segs, crs=CRS_DENMARK)
    log.info("Segments before length filter: %d", len(bus_segs))
    bus_segs = bus_segs[bus_segs.geometry.length >= SEG_MIN_LEN_M].reset_index(drop=True)
    log.info("Segments after filtering < %dm: %d", SEG_MIN_LEN_M, len(bus_segs))

    # --- Load existing scored pedestrian segments ---
    log.info("Loading existing scored segments from %s", WEB_SEGMENTS_GEOJSON)
    scored_old = gpd.read_file(WEB_SEGMENTS_GEOJSON).to_crs(CRS_DENMARK)
    score_cols = [c for c in scored_old.columns if c.startswith("score_") or c.startswith("green_")]
    log.info("Score/green columns: %s", score_cols)

    ped_midpoints = scored_old.geometry.centroid
    tree = STRtree(ped_midpoints.values)

    # --- Remap scores: up to 2 nearest pedestrian segments within 30m, take MAX ---
    log.info("Remapping scores (max %dm radius, top-2 MAX) ...", SCORE_SNAP_M)
    score_arrays = {col: np.full(len(bus_segs), np.nan) for col in score_cols}

    for i, midpt in enumerate(bus_segs.geometry.centroid.values):
        candidates = tree.query_nearest(midpt, max_distance=SCORE_SNAP_M, return_distance=False, exclusive=False)
        if len(candidates) == 0:
            candidates = [tree.nearest(midpt)]
        top2 = candidates[:2]
        for col in score_cols:
            vals = scored_old.iloc[top2][col].values
            score_arrays[col][i] = float(np.nanmax(vals))

    for col in score_cols:
        bus_segs[col] = score_arrays[col]

    primary_score = next((c for c in score_cols if c == "score_health_combined"), score_cols[0])
    log.info("Score remapping complete. %s range: %.3f – %.3f",
             primary_score,
             float(np.nanmin(score_arrays[primary_score])),
             float(np.nanmax(score_arrays[primary_score])))

    # --- Attach route names (all routes through each segment, via 15m buffer) ---
    log.info("Attaching route names ...")
    bus_segs["route_names"] = route_names_for_geoms(bus_segs.geometry, bus_score_clip, ROUTE_SNAP_M)
    log.info("Segments with route_names: %d / %d", (bus_segs["route_names"] != "").sum(), len(bus_segs))

    # --- Export scored segments ---
    out_cols = ["geometry", "route_names"] + score_cols
    bus_segs[out_cols].to_crs(CRS_WGS84).to_file(WEB_SEGMENTS_GEOJSON, driver="GeoJSON")
    log.info("Exported scored segments → %s  (%d features, %.0f KB)",
             WEB_SEGMENTS_GEOJSON, len(bus_segs), WEB_SEGMENTS_GEOJSON.stat().st_size / 1024)

    # --- Export grey context routes (outside scoring zone) ---
    context_geom = context_zone.difference(score_zone)
    context_only = gpd.clip(bus_context_clip, context_geom).reset_index(drop=True)
    context_only[["geometry", "route_short_name"]].rename(
        columns={"route_short_name": "route_name"}
    ).to_crs(CRS_WGS84).to_file(WEB_BUS_CONTEXT_GEOJSON, driver="GeoJSON")
    log.info("Exported context routes → %s  (%d features, %.0f KB)",
             WEB_BUS_CONTEXT_GEOJSON, len(context_only), WEB_BUS_CONTEXT_GEOJSON.stat().st_size / 1024)

    # ==========================================================================
    # BUS STOPS (clipped to 2km context zone, with context flag)
    # ==========================================================================

    log.info("Enriching stops from %s ...", WEB_STOPS_GEOJSON)
    stops = gpd.read_file(WEB_STOPS_GEOJSON).to_crs(CRS_DENMARK)

    # Clip to 2km context zone — drop far-out-of-district stops (city-wide routes)
    stops = gpd.clip(stops, context_zone).reset_index(drop=True)
    log.info("Stops after clipping to 2km zone: %d", len(stops))

    # context = True → outside district + 20m buffer (greyed out in web app)
    stops["context"] = ~stops.geometry.within(score_zone)
    log.info("Internal stops: %d | Context stops: %d",
             (~stops["context"]).sum(), stops["context"].sum())

    # Attach all route names served by each stop
    stops["route_names"] = route_names_for_geoms(stops.geometry, bus, STOP_ROUTE_BUF_M)
    log.info("Stops with at least one route: %d / %d",
             (stops["route_names"] != "").sum(), len(stops))

    # --- Score each stop from nearest bus segment (within 60m, top-2 MAX) ---
    log.info("Scoring stops from nearest bus segments (max 60m radius, top-2 MAX) ...")
    seg_midpoints = bus_segs.geometry.centroid
    seg_tree = STRtree(seg_midpoints.values)

    stop_score_arrays = {col: np.full(len(stops), np.nan) for col in score_cols}
    for i, geom in enumerate(stops.geometry):
        candidates = seg_tree.query_nearest(geom, max_distance=60, return_distance=False, exclusive=False)
        if len(candidates) == 0:
            candidates = np.array([seg_tree.nearest(geom)])
        top2 = candidates[:2]
        for col in score_cols:
            vals = bus_segs.iloc[top2][col].values
            stop_score_arrays[col][i] = float(np.nanmax(vals))

    for col in score_cols:
        stops[col] = stop_score_arrays[col]

    primary_score = next((c for c in score_cols if c == "score_health_combined"), score_cols[0])
    scored_stops = (~np.isnan(stop_score_arrays[primary_score])).sum()
    log.info("Stops with scores: %d / %d  (%s range: %.3f – %.3f)",
             scored_stops, len(stops), primary_score,
             float(np.nanmin(stop_score_arrays[primary_score])),
             float(np.nanmax(stop_score_arrays[primary_score])))

    stops.to_crs(CRS_WGS84).to_file(WEB_STOPS_GEOJSON, driver="GeoJSON")
    log.info("Exported enriched stops → %s  (%d features, %.0f KB)",
             WEB_STOPS_GEOJSON, len(stops), WEB_STOPS_GEOJSON.stat().st_size / 1024)

    # ==========================================================================
    # NEIGHBOURHOOD POLYGONS WITH POPULATION
    # ==========================================================================

    log.info("Exporting neighbourhood polygons with population ...")
    nb = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer="neighbourhoods").to_crs(CRS_DENMARK)

    pop = pd.read_csv(POPULATION_CSV)
    pop_total = pop.groupby("gm_id")["people"].sum().reset_index().rename(columns={"people": "pop_total"})
    pop_total["neighbourhood_name"] = pop_total["gm_id"].map(GM_TO_NAME)

    # Dissolve duplicate polygon rows (layer has 10 rows for 5 neighbourhoods)
    nb = nb.dissolve(by="neighbourhood_name").reset_index()

    nb["area_m2"] = nb.geometry.area
    nb = nb.merge(pop_total[["neighbourhood_name", "pop_total"]], on="neighbourhood_name", how="left")
    nb["pop_density"] = (nb["pop_total"] / nb["area_m2"] * 1e6).round(1)  # people per km²

    nb[["geometry", "neighbourhood_name", "pop_total", "pop_density", "area_m2"]].to_crs(CRS_WGS84).to_file(
        WEB_NEIGHBOURHOODS_GEOJSON, driver="GeoJSON"
    )
    log.info("Exported neighbourhoods → %s  (%d features, %.0f KB)",
             WEB_NEIGHBOURHOODS_GEOJSON, len(nb), WEB_NEIGHBOURHOODS_GEOJSON.stat().st_size / 1024)

    # ==========================================================================
    # ENTRANCE-LEVEL DEMOGRAPHICS (for heatmap)
    # ==========================================================================

    log.info("Exporting entrance demographics from %s ...", INTEGRATED_BUILDINGS)
    demo = gpd.read_file(INTEGRATED_BUILDINGS, layer="entrances_demographics")
    demo = demo[demo["pop_total_mid"].notna() & (demo["pop_total_mid"] > 0)].copy()

    demo_web = demo[[
        "geometry",
        "pop_total_low",             "pop_total_mid",             "pop_total_high",
        "pop_children_0_14_low",     "pop_children_0_14_mid",     "pop_children_0_14_high",
        "pop_working_age_30_64_low", "pop_working_age_30_64_mid", "pop_working_age_30_64_high",
        "pop_older_adults_65_79_low","pop_older_adults_65_79_mid","pop_older_adults_65_79_high",
        "pop_very_elderly_80plus_low","pop_very_elderly_80plus_mid","pop_very_elderly_80plus_high",
        "dominant_group",
        "neighbourhood_name",
    ]].copy()

    # Pre-compute ±% uncertainty per group for tooltip use
    for grp, mid_col in [
        ("total",       "pop_total"),
        ("working_age", "pop_working_age_30_64"),
        ("elderly",     "pop_older_adults_65_79"),
        ("children",    "pop_children_0_14"),
    ]:
        lo = demo_web[f"{mid_col}_low"]
        hi = demo_web[f"{mid_col}_high"]
        mi = demo_web[f"{mid_col}_mid"].replace(0, np.nan)
        demo_web[f"unc_pct_{grp}"] = ((hi - lo) / mi * 100).round(1)

    # Round floats to 1 decimal to keep file size manageable
    float_cols = [c for c in demo_web.columns if c.startswith("pop_")]
    demo_web[float_cols] = demo_web[float_cols].round(1)

    # Round coordinates to 5 decimal places (~1m) to reduce file size
    from shapely.ops import transform
    demo_wgs = demo_web.to_crs(CRS_WGS84)
    demo_wgs.geometry = demo_wgs.geometry.apply(
        lambda pt: pt.__class__(round(pt.x, 5), round(pt.y, 5))
    )
    demo_wgs.to_file(WEB_DEMOGRAPHICS_GEOJSON, driver="GeoJSON")
    log.info("Exported demographics → %s  (%d features, %.0f KB)",
             WEB_DEMOGRAPHICS_GEOJSON, len(demo_web), WEB_DEMOGRAPHICS_GEOJSON.stat().st_size / 1024)

    log.info("All exports complete.")


if __name__ == "__main__":
    main()
