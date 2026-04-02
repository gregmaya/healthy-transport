"""
Score bus route segments for pedestrian accessibility and health benefit.

Replaces notebooks/11_scoring_bus_routes.ipynb.

Key improvements over the notebook:
  - Per-group walking speeds grounded in literature (Bohannon 1997; Lusardi 2003; Plaut 2005)
  - B(t) benefit curves expressed in time (minutes), anchored to the WHO GAPPA (2018)
    10-minute walk recommendation — each demographic group has its own speed and
    time horizon, so the same walk time means different physical distances per group
  - Uses CitySeer dev branch decay_fn: ONE compute_stats call per group at ONE distance
    threshold, with the Gaussian curve evaluated internally in Rust. This replaces the
    old 61-threshold + manual band-integration approach (24 traversals → 4 traversals).
  - Outputs scored pedestrian network segments to WEB_SEGMENTS_GEOJSON, which is
    then consumed by scripts/export/export_bus_route_segments.py for GTFS geometry
    remapping and stop enrichment

Score columns produced (on live bus-route segments):
  score_catchment           — B(t) × total_area_m2 per building; globally normalised [0,1]
  score_health_working_age  — B(t) × pop_working_age (15–64), mid scenario; globally normalised
  score_health_elderly      — B(t) × pop_elderly (65+), mid scenario; globally normalised
  score_health_children     — B(t) × pop_children (0–14), mid scenario; globally normalised
  score_health_combined     — equal-weight mean of three group scores

Normalisation: global (score / max across all live nodes). This preserves relative
ranking and yields [0, 1] range without requiring a second flat-decay traversal.

Usage:
  python scripts/score/score_bus_routes.py
  # Then run: python scripts/export/export_bus_route_segments.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from cityseer import decay as cityseer_decay
from cityseer.metrics import layers
from cityseer.tools import graphs, io

from src.utils.config import (
    CRS_DENMARK,
    CRS_WGS84,
    ENTRANCES_DEMOGRAPHICS_LAYER,
    INTEGRATED_BUILDINGS,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
    PEDESTRIAN_NETWORK_GPKG,
    SCORING_DECAY_PARAMS,
    SCORING_WALK_MINUTES,
    SCORING_WALKING_SPEEDS,
    TRANSPORT_STOPS_OUTPUT,
    WEB_SEGMENTS_GEOJSON,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Geometry constants
# ---------------------------------------------------------------------------

BUS_ROUTE_BUFFER_M = 15  # segments within this distance of a GTFS bus route are scored
INTERIOR_BUFFER_M  = 80  # midpoint this far inside boundary → interior=True

SCORE_COLS = [
    "score_catchment",
    "score_health_working_age",
    "score_health_elderly",
    "score_health_children",
    "score_health_combined",
]


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    # ==========================================================================
    # 1. Load input data
    # ==========================================================================

    log.info("Loading entrances_demographics from %s", INTEGRATED_BUILDINGS)
    entrances = gpd.read_file(INTEGRATED_BUILDINGS, layer=ENTRANCES_DEMOGRAPHICS_LAYER)
    log.info("Entrances: %d  CRS: %s", len(entrances), entrances.crs)

    log.info("Loading pedestrian network edges from %s", PEDESTRIAN_NETWORK_GPKG)
    gdf_edges = gpd.read_file(PEDESTRIAN_NETWORK_GPKG, layer="edges")
    log.info("Network edges: %d", len(gdf_edges))

    log.info("Loading bus routes from %s", TRANSPORT_STOPS_OUTPUT)
    gdf_routes = gpd.read_file(TRANSPORT_STOPS_OUTPUT, layer="routes").to_crs(CRS_DENMARK)
    bus_routes = gdf_routes[gdf_routes["transport_mode"] == "bus"].reset_index(drop=True)
    log.info("Bus routes: %d", len(bus_routes))

    log.info("Loading boundary from %s", NORREBRO_BOUNDARY_FILE)
    boundary      = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER).to_crs(CRS_DENMARK)
    boundary_poly = boundary.geometry.union_all()

    # ==========================================================================
    # 2. Build dual pedestrian network
    # ==========================================================================

    log.info("Building primal graph from network edges ...")
    G = io.nx_from_generic_geopandas(gdf_edges)
    G = graphs.nx_remove_filler_nodes(G)
    G = graphs.nx_decompose(G, decompose_max=20)
    log.info("Primal graph: %d nodes, %d edges", G.number_of_nodes(), G.number_of_edges())

    log.info("Converting to dual graph (primal edges → dual nodes) ...")
    G_dual = graphs.nx_to_dual(G)
    log.info("Dual graph: %d nodes (= 20m segments)", G_dual.number_of_nodes())

    # ==========================================================================
    # 3. Mark live nodes — only segments on bus routes receive scores
    # ==========================================================================

    log.info("Marking live nodes within %dm of bus routes ...", BUS_ROUTE_BUFFER_M)
    bus_buffer = bus_routes.geometry.union_all().buffer(BUS_ROUTE_BUFFER_M)

    live_count = 0
    for node, data in G_dual.nodes(data=True):
        primal_edge = data.get("primal_edge")
        is_live     = primal_edge is not None and primal_edge.intersects(bus_buffer)
        G_dual.nodes[node]["live"] = is_live
        if is_live:
            live_count += 1

    log.info("Live nodes (bus segments): %d / %d total dual nodes", live_count, G_dual.number_of_nodes())

    nodes_gdf, _, network_structure = io.network_structure_from_nx(G_dual)
    log.info("nodes_gdf shape: %s  geometry column: %s", nodes_gdf.shape, nodes_gdf.geometry.name)

    # ==========================================================================
    # 4. Prepare scoring data columns
    # ==========================================================================

    entrances = entrances.copy()

    # Deduplication: treat each building as one data point.
    # Multiple entrances per building share the same building_id → CitySeer
    # deduplicates so the building is counted once per network node.
    # Entrances without a building match fall back to their own entrance_id.
    entrances["_data_id"] = entrances["building_id"].where(
        entrances["building_id"].notna(), entrances["entrance_id"]
    )

    # Population groups — mid scenario only
    entrances["pop_working_age"] = (
        entrances["pop_young_adults_15_29_mid"].fillna(0)
        + entrances["pop_working_age_30_64_mid"].fillna(0)
    )
    entrances["pop_elderly"] = (
        entrances["pop_older_adults_65_79_mid"].fillna(0)
        + entrances["pop_very_elderly_80plus_mid"].fillna(0)
    )
    entrances["pop_children"] = entrances["pop_children_0_14_mid"].fillna(0)

    # Catchment weight: total built floor area regardless of use type.
    # Residential, commercial, institutional and mixed-use all contribute equally —
    # catchment is about physical proximity to built destinations, not residential stock.
    entrances["weight_area"] = entrances["total_area_m2"].fillna(0)

    log.info(
        "Population totals — working_age: %.0f  elderly: %.0f  children: %.0f  area(m²): %.0f",
        entrances["pop_working_age"].sum(),
        entrances["pop_elderly"].sum(),
        entrances["pop_children"].sum(),
        entrances["weight_area"].sum(),
    )

    # ==========================================================================
    # 5. Compute weighted accessibility statistics using decay_fn
    #
    # One compute_stats call per group, each with:
    #   - minutes=[max_min]        → a single distance threshold per group
    #   - speed_m_s=group_speed    → converts minutes to the group's effective metres
    #   - decay_fn=gaussian(...)   → Gaussian B(t) evaluated in Rust; no post-processing
    #
    # Parameters are in time (minutes) matching the WHO 10-minute walk target.
    # decay.gaussian(peak, cutoff, std) normalises internally to p ∈ [0,1].
    #
    # 4 network traversals total vs 24 in the previous multi-threshold approach.
    # ==========================================================================

    run_config = [
        # (label, data_col,          group key)
        ("working_age", "pop_working_age", "working_age"),
        ("elderly",     "pop_elderly",     "elderly"),
        ("children",    "pop_children",    "children"),
        ("catchment",   "weight_area",     "catchment"),
    ]

    for label, data_col, group in run_config:
        speed     = SCORING_WALKING_SPEEDS[group]
        max_min   = SCORING_WALK_MINUTES[group]
        peak_min  = SCORING_DECAY_PARAMS[group]["peak_min"]
        sigma_min = SCORING_DECAY_PARAMS[group]["sigma_min"]

        decay_expr = cityseer_decay.gaussian(
            peak=peak_min,
            cutoff=max_min,
            std=sigma_min,
        )
        log.info(
            "compute_stats [%s]  speed=%.2f m/s  max=%d min  peak=%.1f min  decay_fn=%s",
            label, speed, max_min, peak_min, decay_expr,
        )

        nodes_gdf, _ = layers.compute_stats(
            data_gdf=entrances,
            stats_column_labels=[data_col],
            nodes_gdf=nodes_gdf,
            network_structure=network_structure,
            minutes=[max_min],
            speed_m_s=speed,
            data_id_col="_data_id",
            decay_fn=decay_expr,
        )

        # Derive the output column name (distance in metres, rounded)
        dist_m = int(round(max_min * 60 * speed))
        raw_col = f"cc_{data_col}_sum_{dist_m}"
        if raw_col not in nodes_gdf.columns:
            # Inspect actual columns added to find the correct name
            new_cols = [c for c in nodes_gdf.columns if data_col in c and "_sum_" in c]
            log.warning("Expected column %s not found. Found: %s", raw_col, new_cols)
            raw_col = new_cols[0] if new_cols else None

        if raw_col:
            # Rename to a stable internal name to avoid collision across group calls
            nodes_gdf[f"_raw_{label}"] = nodes_gdf[raw_col]
            log.info("  raw column: %s → _raw_%s", raw_col, label)

    # ==========================================================================
    # 6. Normalise scores globally across live segments
    #
    # Global normalisation: score / max(score across live nodes).
    # Produces [0, 1] range where 1.0 = the best live segment in each group.
    # This preserves relative ranking without requiring a second flat-decay traversal
    # for the local-population denominator.
    # ==========================================================================

    log.info("Normalising scores globally across live segments ...")
    live_mask = nodes_gdf["live"].fillna(False)

    def _normalise_global(raw_col: str) -> np.ndarray:
        vals = nodes_gdf[raw_col].fillna(0).values
        live_max = float(np.nanmax(vals[live_mask.values]))
        if live_max > 0:
            return vals / live_max
        return vals

    def _log_score(name: str, arr: np.ndarray) -> None:
        live_vals = arr[live_mask.values]
        live_vals = live_vals[~np.isnan(live_vals)]
        log.info(
            "  %-30s  mean=%.4f  max=%.4f  n_live=%d",
            name, float(live_vals.mean()), float(live_vals.max()), len(live_vals),
        )

    for label, score_col in [
        ("working_age", "score_health_working_age"),
        ("elderly",     "score_health_elderly"),
        ("children",    "score_health_children"),
        ("catchment",   "score_catchment"),
    ]:
        nodes_gdf[score_col] = _normalise_global(f"_raw_{label}")
        _log_score(score_col, nodes_gdf[score_col].values)

    # Combined health score: equal-weight mean of three normalised group scores
    nodes_gdf["score_health_combined"] = (
        nodes_gdf["score_health_working_age"].fillna(0)
        + nodes_gdf["score_health_elderly"].fillna(0)
        + nodes_gdf["score_health_children"].fillna(0)
    ) / 3
    _log_score("score_health_combined", nodes_gdf["score_health_combined"].values)

    # ==========================================================================
    # 7. Interior flag
    # ==========================================================================

    log.info("Computing interior flag (midpoint >%dm inside boundary) ...", INTERIOR_BUFFER_M)
    interior_poly = boundary_poly.buffer(-INTERIOR_BUFFER_M)
    nodes_gdf["interior"] = nodes_gdf.geometry.centroid.within(interior_poly)
    log.info(
        "Interior segments: %d / %d live",
        int(nodes_gdf.loc[live_mask, "interior"].sum()),
        int(live_mask.sum()),
    )

    # ==========================================================================
    # 8. Export scored pedestrian segments
    # ==========================================================================

    log.info("Extracting live segments for export ...")
    live_segs = nodes_gdf[live_mask].copy()

    # The dual graph's nodes_gdf geometry is point (midpoint); primal_edge holds the
    # actual 20m LineString. Use primal_edge as the export geometry.
    if "primal_edge" in live_segs.columns:
        live_segs = gpd.GeoDataFrame(
            live_segs,
            geometry=gpd.GeoSeries(live_segs["primal_edge"], crs=CRS_DENMARK),
            crs=CRS_DENMARK,
        )
    else:
        log.warning("primal_edge column not found — using node point geometry")
        live_segs = live_segs.set_crs(CRS_DENMARK, allow_override=True)

    log.info("Live segments to export: %d", len(live_segs))

    for col in SCORE_COLS:
        if col in live_segs.columns:
            live_segs[col] = live_segs[col].round(5)

    out_cols = ["geometry", "interior"] + [c for c in SCORE_COLS if c in live_segs.columns]
    live_segs[out_cols].to_crs(CRS_WGS84).to_file(WEB_SEGMENTS_GEOJSON, driver="GeoJSON")
    log.info(
        "Exported pedestrian scored segments → %s  (%d features, %.0f KB)",
        WEB_SEGMENTS_GEOJSON,
        len(live_segs),
        WEB_SEGMENTS_GEOJSON.stat().st_size / 1024,
    )
    log.info(
        "score_health_combined range (live): %.4f – %.4f",
        float(live_segs["score_health_combined"].min()),
        float(live_segs["score_health_combined"].max()),
    )
    log.info(
        "Done. Run scripts/export/export_bus_route_segments.py to remap to GTFS geometry and enrich stops."
    )


if __name__ == "__main__":
    main()
