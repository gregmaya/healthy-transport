"""
Integrate Building Datasets for Nørrebro

Joins BBR building attributes onto INSPIRE footprint polygons, links DAR entrance
points to enriched footprints, fills unmatched footprints via KNN neighbor averaging,
and ensures every residential BBR building has at least one entrance.

Outputs:
    data/integrated/norrebro_buildings.gpkg
        - buildings layer: footprint polygons with BBR + KNN-estimated attributes
        - entrances layer: entrance points with linked BBR attributes

Usage:
    python scripts/integrate/integrate_buildings.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    BUILDING_FOOTPRINTS_OUTPUT,
    BUILDINGS_OUTPUT,
    INTEGRATED_BUILDINGS,
    INTEGRATED_DATA_DIR,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_NEIGHBOURHOODS_LAYER,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# KNN parameters
KNN_K = 5
KNN_MAX_DIST = 30  # meters

# Neighbourhood gm_id mapping (short names → integer IDs matching population CSV)
GM_ID_MAPPING = {
    "Stefansgade": 1,
    "Mimersgade-kvarteret": 2,
    "Haraldsgade-kvarteret": 3,
    "Guldbergskvarteret": 4,
    "Blagardskvarteret": 5,
}

# Columns to fill via KNN
NUMERIC_COLS = [
    "floors",
    "total_area_m2",
    "residential_area_m2",
    "commercial_area_m2",
    "footprint_area_m2",
    "construction_year",
]
CATEGORICAL_COLS = [
    "use_category",
    "use_description",
    "construction_era",
    "wall_material",
    "roof_material",
    "heating_type",
]

# Output column selections
BUILDING_OUTPUT_COLS = [
    "building_id",
    "building_number",
    "use_code",
    "use_description",
    "use_category",
    "construction_year",
    "construction_era",
    "floors",
    "total_area_m2",
    "residential_area_m2",
    "commercial_area_m2",
    "footprint_area_m2",
    "wall_material",
    "roof_material",
    "heating_type",
    "gm_id",
    "neighbourhood_name",
    "attributes_source",
    "geometry",
]
ENTRANCE_OUTPUT_COLS = [
    "entrance_id",
    "positioning_type",
    "status",
    "building_id",
    "use_code",
    "use_description",
    "use_category",
    "construction_year",
    "construction_era",
    "floors",
    "total_area_m2",
    "residential_area_m2",
    "commercial_area_m2",
    "wall_material",
    "roof_material",
    "heating_type",
    "gm_id",
    "neighbourhood_name",
    "has_building",
    "entrance_source",
    "geometry",
]


def load_data():
    """Load all source datasets."""
    footprints = gpd.read_file(BUILDING_FOOTPRINTS_OUTPUT)
    bbr = gpd.read_file(BUILDINGS_OUTPUT, layer="buildings")
    entrances = gpd.read_file(BUILDINGS_OUTPUT, layer="entrances")
    neighbourhoods = gpd.read_file(
        NORREBRO_BOUNDARY_FILE, layer=NORREBRO_NEIGHBOURHOODS_LAYER
    )

    logger.info("Loaded: %d footprints, %d BBR, %d entrances, %d neighbourhood rows",
                len(footprints), len(bbr), len(entrances), len(neighbourhoods))
    return footprints, bbr, entrances, neighbourhoods


def join_bbr_to_footprints(footprints, bbr):
    """Section A: Spatial join BBR points onto footprint polygons."""
    logger.info("--- A. BBR → Footprints ---")

    bbr_attrs = bbr.drop(columns=["geometry"]).copy()
    enriched = gpd.sjoin(
        footprints, bbr_attrs.set_geometry(bbr.geometry),
        how="left", predicate="contains",
    )

    # Deduplicate: keep BBR with largest total_area_m2 per footprint
    dup_mask = enriched.index.duplicated(keep=False)
    if dup_mask.any():
        n_dup = enriched.index[dup_mask].nunique()
        enriched = (
            enriched.sort_values("total_area_m2", ascending=False)
            .groupby(enriched.index)
            .first()
        )
        enriched = gpd.GeoDataFrame(enriched, geometry="geometry", crs=footprints.crs)
        logger.info("Deduped %d multi-match footprints", n_dup)

    enriched = enriched.drop(columns=["index_right"], errors="ignore")

    n_matched = enriched["building_id"].notna().sum()
    n_unmatched = enriched["building_id"].isna().sum()
    logger.info("Enriched: %d with BBR, %d without", n_matched, n_unmatched)
    return enriched


def join_entrances_to_footprints(entrances, enriched):
    """Section B: Spatial join entrances onto buffered footprints."""
    logger.info("--- B. Entrances → Footprints ---")

    enriched_buffered = enriched.copy()
    enriched_buffered["geometry"] = enriched.geometry.buffer(2)
    enriched_centroids = enriched.geometry.centroid

    entrances_joined = gpd.sjoin(
        entrances, enriched_buffered, how="left", predicate="within"
    )

    # Deduplicate: keep nearest by centroid distance
    dup_mask = entrances_joined.index.duplicated(keep=False)
    if dup_mask.any():
        n_dup = entrances_joined.index[dup_mask].nunique()

        def pick_nearest(group):
            if len(group) == 1:
                return group.iloc[0]
            entrance_geom = group.geometry.iloc[0]
            dists = group["index_right"].apply(
                lambda idx: (
                    entrance_geom.distance(enriched_centroids.loc[idx])
                    if pd.notna(idx) else float("inf")
                )
            )
            return group.iloc[dists.argmin()]

        entrances_joined = (
            entrances_joined.groupby(entrances_joined.index)
            .apply(pick_nearest, include_groups=False)
            .reset_index(drop=True)
        )
        entrances_joined = gpd.GeoDataFrame(
            entrances_joined, geometry="geometry", crs=entrances.crs
        )
        logger.info("Deduped %d multi-match entrances", n_dup)

    matched = entrances_joined["index_right"].notna().sum()
    unmatched = entrances_joined["index_right"].isna().sum()
    logger.info("Entrances: %d matched, %d unmatched", matched, unmatched)
    return entrances_joined


def assign_neighbourhoods(enriched, neighbourhoods):
    """Section C: Assign buildings to sub-neighbourhoods."""
    logger.info("--- C. Neighbourhood Assignment ---")

    hoods = (
        neighbourhoods.drop_duplicates(subset=["neighbourhood_name"])
        .copy()
        .reset_index(drop=True)
    )
    hoods["gm_id"] = hoods["neighbourhood_name"].map(GM_ID_MAPPING)

    enriched_with_hood = gpd.sjoin(
        enriched,
        hoods[["gm_id", "neighbourhood_name", "geometry"]],
        how="left",
        predicate="intersects",
    )

    # Keep first match for border buildings
    dup_mask = enriched_with_hood.index.duplicated(keep="first")
    if dup_mask.any():
        enriched_with_hood = enriched_with_hood[~dup_mask]

    enriched_with_hood = enriched_with_hood.drop(columns=["index_right"], errors="ignore")

    in_hood = enriched_with_hood["gm_id"].notna().sum()
    logger.info("Buildings in a neighbourhood: %d / %d", in_hood, len(enriched_with_hood))
    return enriched_with_hood, hoods


def knn_fill_visualization(enriched_with_hood):
    """Section E: KNN fill for visualization dataset."""
    logger.info("--- E. KNN Fill (K=%d, %dm cap) ---", KNN_K, KNN_MAX_DIST)

    viz = enriched_with_hood.copy()
    viz["attributes_source"] = np.where(viz["building_id"].notna(), "bbr", "unmatched")

    matched_mask = viz["attributes_source"] == "bbr"
    unmatched_mask = ~matched_mask

    # Build KDTree
    matched_centroids = viz.loc[matched_mask, "geometry"].centroid
    unmatched_centroids = viz.loc[unmatched_mask, "geometry"].centroid

    matched_coords = np.column_stack([matched_centroids.x, matched_centroids.y])
    unmatched_coords = np.column_stack([unmatched_centroids.x, unmatched_centroids.y])

    tree = cKDTree(matched_coords)
    distances, indices = tree.query(unmatched_coords, k=KNN_K)

    # Flexible K: use however many neighbors are within cap
    within_cap_mask = distances <= KNN_MAX_DIST
    has_any_neighbor = within_cap_mask.sum(axis=1) > 0

    matched_df = viz.loc[matched_mask].reset_index(drop=True)
    unmatched_idx = viz.index[unmatched_mask]
    fill_idx = unmatched_idx[has_any_neighbor]
    fill_indices = indices[has_any_neighbor]
    fill_dist_mask = within_cap_mask[has_any_neighbor]

    # Numeric: mask out-of-range to NaN, then nanmean
    import warnings
    for col in NUMERIC_COLS:
        col_values = matched_df[col].to_numpy(dtype=float, na_value=np.nan)
        neighbor_values = col_values[fill_indices]
        neighbor_values = np.where(fill_dist_mask, neighbor_values, np.nan)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            viz.loc[fill_idx, col] = np.nanmean(neighbor_values, axis=1)

    # Categorical: mode of within-cap neighbors
    for col in CATEGORICAL_COLS:
        col_values = matched_df[col].to_numpy(dtype=object, na_value=np.nan)
        neighbor_values = col_values[fill_indices]
        modes = []
        for i, row in enumerate(neighbor_values):
            valid = row[fill_dist_mask[i] & pd.notna(row)]
            if len(valid) > 0:
                modes.append(pd.Series(valid).mode().iloc[0])
            else:
                modes.append(np.nan)
        viz.loc[fill_idx, col] = modes

    viz.loc[fill_idx, "attributes_source"] = "estimated"

    n_bbr = (viz["attributes_source"] == "bbr").sum()
    n_est = (viz["attributes_source"] == "estimated").sum()
    n_unm = (viz["attributes_source"] == "unmatched").sum()
    logger.info("BBR: %d, estimated: %d, unmatched: %d", n_bbr, n_est, n_unm)
    return viz


def build_model_entrances(entrances, enriched_with_hood, bbr, hoods):
    """Section F: Build model entrances + residential entrance guarantee."""
    logger.info("--- F. Model Entrances ---")

    enriched_buffered = enriched_with_hood.copy()
    enriched_buffered["geometry"] = enriched_with_hood.geometry.buffer(2)
    enriched_centroids = enriched_with_hood.geometry.centroid

    model = gpd.sjoin(entrances, enriched_buffered, how="left", predicate="within")

    # Deduplicate
    dup_mask = model.index.duplicated(keep=False)
    if dup_mask.any():
        def pick_nearest(group):
            if len(group) == 1:
                return group.iloc[0]
            entrance_geom = group.geometry.iloc[0]
            dists = group["index_right"].apply(
                lambda idx: (
                    entrance_geom.distance(enriched_centroids.loc[idx])
                    if pd.notna(idx) else float("inf")
                )
            )
            return group.iloc[dists.argmin()]

        model = (
            model.groupby(model.index)
            .apply(pick_nearest, include_groups=False)
            .reset_index(drop=True)
        )
        model = gpd.GeoDataFrame(model, geometry="geometry", crs=entrances.crs)

    model["has_building"] = model["index_right"].notna()
    model["entrance_source"] = np.where(model["has_building"], "spatial_join", None)

    # Select columns
    cols = [c for c in ENTRANCE_OUTPUT_COLS if c in model.columns]
    model = model[cols]

    linked = model["has_building"].sum()
    unlinked = (~model["has_building"]).sum()
    logger.info("Entrances: %d linked, %d unlinked", linked, unlinked)

    # --- Residential entrance guarantee ---
    logger.info("--- F2. Residential Entrance Guarantee ---")
    residential_bbr = bbr[bbr["use_category"] == "Residential"]
    matched_ids = set(model.loc[model["has_building"], "building_id"].dropna())
    orphaned = residential_bbr[~residential_bbr["building_id"].isin(matched_ids)]

    logger.info("Residential BBR: %d total, %d orphaned", len(residential_bbr), len(orphaned))

    if len(orphaned) > 0:
        entrance_coords = np.column_stack([entrances.geometry.x, entrances.geometry.y])
        orphan_coords = np.column_stack([orphaned.geometry.x, orphaned.geometry.y])

        entrance_tree = cKDTree(entrance_coords)
        distances_ent, indices_ent = entrance_tree.query(orphan_coords, k=1)

        nearest_ent = entrances.iloc[indices_ent].reset_index(drop=True)
        orphaned_reset = orphaned.reset_index(drop=True)

        synthetic = gpd.GeoDataFrame(
            {
                "entrance_id": nearest_ent["entrance_id"].values,
                "positioning_type": nearest_ent["positioning_type"].values,
                "status": nearest_ent["status"].values,
                "building_id": orphaned_reset["building_id"].values,
                "use_code": orphaned_reset["use_code"].values,
                "use_description": orphaned_reset["use_description"].values,
                "use_category": orphaned_reset["use_category"].values,
                "construction_year": orphaned_reset["construction_year"].values,
                "construction_era": orphaned_reset["construction_era"].values,
                "floors": orphaned_reset["floors"].values,
                "total_area_m2": orphaned_reset["total_area_m2"].values,
                "residential_area_m2": orphaned_reset["residential_area_m2"].values,
                "commercial_area_m2": orphaned_reset["commercial_area_m2"].values,
                "wall_material": orphaned_reset["wall_material"].values,
                "roof_material": orphaned_reset["roof_material"].values,
                "heating_type": orphaned_reset["heating_type"].values,
                "has_building": True,
                "entrance_source": "nearest",
            },
            geometry=nearest_ent.geometry.values,
            crs=entrances.crs,
        )

        # Add neighbourhood from spatial join on BBR point
        orphan_gdf = gpd.GeoDataFrame(
            orphaned_reset, geometry=orphaned.geometry.values, crs=entrances.crs
        )
        orphan_with_hood = gpd.sjoin(
            orphan_gdf,
            hoods[["gm_id", "neighbourhood_name", "geometry"]],
            how="left",
            predicate="within",
        )
        synthetic["gm_id"] = orphan_with_hood["gm_id"].values
        synthetic["neighbourhood_name"] = orphan_with_hood["neighbourhood_name"].values

        # Align columns
        for col in model.columns:
            if col not in synthetic.columns:
                synthetic[col] = np.nan
        synthetic = synthetic[model.columns]

        model = pd.concat([model, synthetic], ignore_index=True)
        model = gpd.GeoDataFrame(model, geometry="geometry", crs=entrances.crs)

        logger.info("Added %d synthetic pairings (median dist: %.1f m, max: %.1f m)",
                     len(synthetic), np.median(distances_ent), np.max(distances_ent))

    logger.info("Final model: %d entrances (%d spatial_join, %d nearest)",
                len(model),
                (model["entrance_source"] == "spatial_join").sum(),
                (model["entrance_source"] == "nearest").sum())
    return model


def save_outputs(buildings_out, model_entrances):
    """Section G: Save to GeoPackage."""
    logger.info("--- G. Save ---")

    INTEGRATED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    # Delete existing file to prevent append accumulation
    if INTEGRATED_BUILDINGS.exists():
        INTEGRATED_BUILDINGS.unlink()

    buildings_out.to_file(INTEGRATED_BUILDINGS, layer="buildings", driver="GPKG")
    model_entrances.to_file(
        INTEGRATED_BUILDINGS, layer="entrances", driver="GPKG", mode="a"
    )

    size_mb = INTEGRATED_BUILDINGS.stat().st_size / (1024 * 1024)
    logger.info("Saved: %s (%.1f MB)", INTEGRATED_BUILDINGS, size_mb)
    logger.info("  buildings: %d features, %d columns",
                len(buildings_out), len(buildings_out.columns))
    logger.info("  entrances: %d features, %d columns",
                len(model_entrances), len(model_entrances.columns))


def main():
    logger.info("=" * 60)
    logger.info("INTEGRATE BUILDING DATASETS")
    logger.info("=" * 60)

    # Load
    footprints, bbr, entrances, neighbourhoods = load_data()

    # A. BBR → footprints
    enriched = join_bbr_to_footprints(footprints, bbr)

    # B. Entrances → footprints (for exploration, used indirectly in F)
    _ = join_entrances_to_footprints(entrances, enriched)

    # C. Neighbourhood assignment
    enriched_with_hood, hoods = assign_neighbourhoods(enriched, neighbourhoods)

    # E. KNN fill for visualization
    viz = knn_fill_visualization(enriched_with_hood)

    # F. Model entrances + residential guarantee
    model_entrances = build_model_entrances(entrances, enriched_with_hood, bbr, hoods)

    # Prepare buildings output
    cols = [c for c in BUILDING_OUTPUT_COLS if c in viz.columns]
    buildings_out = viz[cols].copy()

    # G. Save
    save_outputs(buildings_out, model_entrances)

    # Summary
    logger.info("=" * 60)
    logger.info("INTEGRATION SUMMARY")
    logger.info("=" * 60)
    logger.info("Buildings: %d (bbr=%d, estimated=%d, unmatched=%d)",
                len(buildings_out),
                (buildings_out["attributes_source"] == "bbr").sum(),
                (buildings_out["attributes_source"] == "estimated").sum(),
                (buildings_out["attributes_source"] == "unmatched").sum())
    logger.info("Entrances: %d (spatial_join=%d, nearest=%d, unlinked=%d)",
                len(model_entrances),
                (model_entrances["entrance_source"] == "spatial_join").sum(),
                (model_entrances["entrance_source"] == "nearest").sum(),
                (~model_entrances["has_building"]).sum())

    # Verify residential coverage
    res_in_model = model_entrances[
        model_entrances["use_category"] == "Residential"
    ]["building_id"].nunique()
    res_in_bbr = (bbr["use_category"] == "Residential").sum()
    logger.info("Residential coverage: %d/%d BBR buildings have entrances",
                res_in_model, res_in_bbr)

    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
