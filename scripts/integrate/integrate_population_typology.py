"""
Integrate Population Typology onto Building Entrances

Applies a dwelling-typology model to assign age-specific population estimates
(low/mid/high) to each residential building, then joins those demographics
onto the existing entrances layer.

The typology model classifies buildings by average unit size (studio / small /
medium / family), maps each tier to a household-size distribution, then maps
household sizes to age-group profiles. A pycnophylactic normalization step
ensures neighbourhood × age group totals match the processed population CSV
exactly in all three scenarios.

Outputs:
    data/integrated/norrebro_buildings.gpkg
        - entrances_demographics layer: all entrances + demographic columns

Usage:
    python scripts/integrate/integrate_population_typology.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    DWELLINGS_CSV,
    ENTRANCES_DEMOGRAPHICS_LAYER,
    INTEGRATED_BUILDINGS,
    POPULATION_CSV,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Age group definitions
# ---------------------------------------------------------------------------
AGE_GROUP_BINS = [0, 15, 30, 65, 80, 200]
AGE_GROUP_LABELS = [
    "children_0_14",
    "young_adults_15_29",
    "working_age_30_64",
    "older_adults_65_79",
    "very_elderly_80plus",
]

# ---------------------------------------------------------------------------
# Dwelling typology tier thresholds (avg m² per unit)
# ---------------------------------------------------------------------------
TIER_BOUNDS = {"studio": 50, "small": 80, "medium": 110}  # family = > 110
TIER_ORDER = ["studio", "small", "medium", "family"]

# ---------------------------------------------------------------------------
# Prior matrices (mid scenario) — calibrated against dwellings CSV in notebook
# ---------------------------------------------------------------------------
# P(household_size | tier): rows sum to 1.0
TIER_TO_HS_MID = {
    "studio": {1: 0.90, 2: 0.07, 3: 0.02, "4+": 0.01},
    "small":  {1: 0.52, 2: 0.32, 3: 0.10, "4+": 0.06},
    "medium": {1: 0.12, 2: 0.40, 3: 0.28, "4+": 0.20},
    "family": {1: 0.03, 2: 0.15, 3: 0.32, "4+": 0.50},
}

# P(age_group | household_size): rows sum to 1.0
HS_TO_AGE = {
    1: {
        "children_0_14":      0.00,
        "young_adults_15_29": 0.65,
        "working_age_30_64":  0.25,
        "older_adults_65_79": 0.08,
        "very_elderly_80plus": 0.02,
    },
    2: {
        "children_0_14":      0.03,
        "young_adults_15_29": 0.22,
        "working_age_30_64":  0.57,
        "older_adults_65_79": 0.15,
        "very_elderly_80plus": 0.03,
    },
    3: {
        "children_0_14":      0.22,
        "young_adults_15_29": 0.15,
        "working_age_30_64":  0.52,
        "older_adults_65_79": 0.09,
        "very_elderly_80plus": 0.02,
    },
    "4+": {
        "children_0_14":      0.35,
        "young_adults_15_29": 0.10,
        "working_age_30_64":  0.47,
        "older_adults_65_79": 0.07,
        "very_elderly_80plus": 0.01,
    },
}

HS_KEYS = [1, 2, 3, "4+"]
# Uniform distribution over household-size categories (for prior perturbation)
_U = 1.0 / len(HS_KEYS)


def _perturb_tier_to_hs(mid: dict, alpha: float) -> dict:
    """
    Blend TIER_TO_HS priors toward/away from uniform.

    alpha=1.0  → mid (no change)
    alpha=0.6  → low (40% toward uniform)
    alpha=1.4  → high (40% amplified beyond mid)

    Each row still sums to 1.0 by construction.
    """
    result = {}
    for tier, probs in mid.items():
        result[tier] = {hs: alpha * p + (1 - alpha) * _U for hs, p in probs.items()}
    return result


TIER_TO_HS = {
    "low":  _perturb_tier_to_hs(TIER_TO_HS_MID, alpha=0.6),
    "mid":  TIER_TO_HS_MID,
    "high": _perturb_tier_to_hs(TIER_TO_HS_MID, alpha=1.4),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_age_lower(age_str: str) -> int:
    s = age_str.replace(" years", "")
    if "+" in s:
        return int(s.replace("+", ""))
    return int(s.split("-")[0])


def _classify_tier(m2: float) -> str:
    if m2 <= TIER_BOUNDS["studio"]:
        return "studio"
    elif m2 <= TIER_BOUNDS["small"]:
        return "small"
    elif m2 <= TIER_BOUNDS["medium"]:
        return "medium"
    return "family"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def compute_building_population(
    gdf_buildings: gpd.GeoDataFrame,
    df_pop: pd.DataFrame,
    df_dwell: pd.DataFrame,
) -> pd.DataFrame:
    """
    Run the typology model and return a DataFrame keyed by building_id with
    population columns for all three scenarios.
    """
    # --- Filter to residential buildings ---
    gdf_res = gdf_buildings[gdf_buildings["residential_area_m2"] > 0].copy()
    logger.info("Residential buildings: %s", f"{len(gdf_res):,}")

    # --- Fill null antal_boliger with neighbourhood median (BBR buildings only) ---
    bbr_mask = gdf_res["attributes_source"] == "bbr"
    hood_median = (
        gdf_res.loc[bbr_mask]
        .groupby("gm_id")["antal_boliger"]
        .median()
    )
    gdf_res["unit_weight"] = gdf_res["antal_boliger"].copy()
    null_mask = gdf_res["unit_weight"].isna()
    for gm_id, med in hood_median.items():
        mask = null_mask & (gdf_res["gm_id"] == gm_id)
        gdf_res.loc[mask, "unit_weight"] = med
    n_fallback = null_mask.sum()
    logger.info(
        "Buildings using fallback median: %d (%.1f%%)",
        n_fallback,
        n_fallback / len(gdf_res) * 100,
    )

    # --- Unit share within neighbourhood ---
    hood_unit_totals = gdf_res.groupby("gm_id")["unit_weight"].sum()
    gdf_res["hood_unit_total"] = gdf_res["gm_id"].map(hood_unit_totals)
    gdf_res["unit_share"] = gdf_res["unit_weight"] / gdf_res["hood_unit_total"]

    # --- Aggregate population CSV to 5 age groups ---
    df_pop = df_pop.copy()
    df_pop["age_lower"] = df_pop["ages"].apply(_parse_age_lower)
    df_pop["age_group"] = pd.cut(
        df_pop["age_lower"],
        bins=AGE_GROUP_BINS,
        labels=AGE_GROUP_LABELS,
        right=False,
    )
    pop_by_group = (
        df_pop.groupby(["gm_id", "age_group"], observed=False)["people"]
        .sum()
        .reset_index()
    )

    # --- Classify dwelling typology ---
    gdf_res["avg_unit_m2"] = (
        gdf_res["residential_area_m2"] / gdf_res["unit_weight"].clip(lower=1)
    )
    gdf_res["dwelling_typology"] = gdf_res["avg_unit_m2"].apply(_classify_tier)

    tier_dist = gdf_res["dwelling_typology"].value_counts()
    logger.info("Dwelling tier distribution: %s", tier_dist.to_dict())

    # --- For each scenario, compute pycnophylactic age-group estimates ---
    # All population columns are added directly to df_res; no merges needed.
    for scenario in ("low", "mid", "high"):
        tier_hs = TIER_TO_HS[scenario]

        # P(hs | tier) for each building
        for hs in HS_KEYS:
            gdf_res[f"_hs_prob_{hs}"] = gdf_res["dwelling_typology"].map(
                {t: tier_hs[t][hs] for t in tier_hs}
            )

        # age_weight[b, a] = Σ_hs P(hs|tier) × P(age|hs)
        for ag in AGE_GROUP_LABELS:
            gdf_res[f"_age_weight_{ag}"] = sum(
                gdf_res[f"_hs_prob_{hs}"] * HS_TO_AGE[hs][ag] for hs in HS_KEYS
            )

        # Pycnophylactic redistribution
        pop_cols_s = []
        for ag in AGE_GROUP_LABELS:
            adj_col = f"_adj_{ag}"
            gdf_res[adj_col] = gdf_res["unit_share"] * gdf_res[f"_age_weight_{ag}"]
            norm_denom = gdf_res.groupby("gm_id")[adj_col].transform("sum")
            norm_share = gdf_res[adj_col] / norm_denom
            ag_pop = (
                pop_by_group[pop_by_group["age_group"] == ag]
                .set_index("gm_id")["people"]
            )
            col = f"pop_{ag}_{scenario}"
            gdf_res[col] = gdf_res["gm_id"].map(ag_pop) * norm_share
            pop_cols_s.append(col)

        total_col = f"pop_total_{scenario}"
        gdf_res[total_col] = gdf_res[pop_cols_s].sum(axis=1)
        pop_cols_s.append(total_col)

        # Validate
        all_ok = True
        for ag in AGE_GROUP_LABELS:
            hood_sum = gdf_res.groupby("gm_id")[f"pop_{ag}_{scenario}"].sum()
            csv_total = (
                pop_by_group[pop_by_group["age_group"] == ag]
                .set_index("gm_id")["people"]
            )
            diff = (hood_sum - csv_total).abs().max()
            if diff >= 1e-6:
                logger.error(
                    "Validation FAIL [%s, %s]: max diff = %.2e", scenario, ag, diff
                )
                all_ok = False
        if all_ok:
            logger.info(
                "Validation OK [%s]: all neighbourhood × age group totals preserved",
                scenario,
            )
        logger.info(
            "Total population (%s): %s",
            scenario,
            f"{gdf_res[f'pop_total_{scenario}'].sum():,.0f}",
        )

    # Clean up temp columns
    tmp_cols = [c for c in gdf_res.columns if c.startswith("_")]
    gdf_res.drop(columns=tmp_cols, inplace=True)

    # --- Build output GeoDataFrame from gdf_res (polygon geometry preserved) ---
    # Geometry is retained so main() can use sjoin_nearest for the spatial fallback.
    all_pop_cols = [
        f"pop_{ag}_{s}"
        for s in ("low", "mid", "high")
        for ag in AGE_GROUP_LABELS
    ] + [f"pop_total_{s}" for s in ("low", "mid", "high")]

    gdf_res["n_dwelling_units"] = gdf_res["unit_weight"]

    mid_pop_cols = [f"pop_{ag}_mid" for ag in AGE_GROUP_LABELS]
    # Buffer-zone buildings (gm_id=null) have all-NA mid columns — use apply to skip them safely
    def _dominant(row):
        valid = row.dropna()
        if valid.empty or valid.sum() == 0:
            return None
        return valid.idxmax()
    gdf_res["dominant_group"] = (
        gdf_res[mid_pop_cols]
        .apply(_dominant, axis=1)
        .str.replace("_mid", "", regex=False)
        .str.replace("pop_", "", regex=False)
    )

    out_cols = [
        "building_id", "gm_id", "n_dwelling_units", "avg_unit_m2",
        "dwelling_typology", "dominant_group",
    ] + all_pop_cols

    return gdf_res[out_cols + ["geometry"]].copy()


def main():
    logger.info("Loading buildings from %s", INTEGRATED_BUILDINGS)
    gdf_buildings = gpd.read_file(INTEGRATED_BUILDINGS, layer="buildings")
    logger.info("Total buildings: %s", f"{len(gdf_buildings):,}")

    logger.info("Loading population CSV from %s", POPULATION_CSV)
    df_pop = pd.read_csv(POPULATION_CSV)
    logger.info("Population rows: %d, total people: %s", len(df_pop), f"{df_pop['people'].sum():,}")

    logger.info("Loading dwellings CSV from %s", DWELLINGS_CSV)
    df_dwell = pd.read_csv(DWELLINGS_CSV)
    logger.info("Dwellings rows: %d", len(df_dwell))

    # --- Run typology model ---
    pop_df = compute_building_population(gdf_buildings, df_pop, df_dwell)
    logger.info("Population model produced %s building rows", f"{len(pop_df):,}")

    # --- Prepare population lookup for Round 1 (building_id join) ---
    # pop_df is now a GeoDataFrame. Extract a plain DataFrame for the key join,
    # filtering out null building_ids (NaN==NaN merge causes cartesian explosion)
    # and dropping gm_id (collision with entrances' own gm_id column).
    pop_cols = [c for c in pop_df.columns if c.startswith("pop_")]
    pop_df_join = (
        pop_df.drop(columns=["geometry", "gm_id"])
        .dropna(subset=["building_id"])
        .copy()
    )
    if pop_df_join["building_id"].duplicated().any():
        meta_cols_agg = {
            c: "first"
            for c in pop_df_join.columns
            if c not in pop_cols + ["building_id"]
        }
        pop_df_join = pop_df_join.groupby("building_id", as_index=False).agg(
            {**meta_cols_agg, **{c: "sum" for c in pop_cols}}
        )
        mid_cols = [c for c in pop_cols if c.endswith("_mid")]
        pop_df_join["dominant_group"] = (
            pop_df_join[mid_cols]
            .idxmax(axis=1)
            .str.replace("_mid", "", regex=False)
            .str.replace("pop_", "", regex=False)
        )
    logger.info(
        "Round 1 lookup: %s unique building_ids (of %s model rows)",
        f"{len(pop_df_join):,}",
        f"{len(pop_df):,}",
    )

    # --- Load entrances ---
    logger.info("Loading entrances layer")
    gdf_entrances = gpd.read_file(INTEGRATED_BUILDINGS, layer="entrances")
    logger.info("Entrances: %s", f"{len(gdf_entrances):,}")

    # --- Round 1: building_id key join ---
    gdf_demo = gdf_entrances.merge(pop_df_join, on="building_id", how="left")
    assert len(gdf_demo) == len(gdf_entrances), (
        f"Merge changed row count: {len(gdf_demo)} != {len(gdf_entrances)}"
    )
    n_r1 = gdf_demo["n_dwelling_units"].notna().sum()
    logger.info(
        "Round 1 matched: %s of %s (%.1f%%)",
        f"{n_r1:,}", f"{len(gdf_demo):,}", n_r1 / len(gdf_demo) * 100,
    )

    # --- Round 2: spatial fallback for unmatched entrances ---
    # Entrances whose building_id is null (KNN-estimated INSPIRE footprints have no
    # BBR ID) are matched spatially to the nearest residential polygon within 10m.
    unmatched_mask = gdf_demo["n_dwelling_units"].isna()
    n_unmatched = unmatched_mask.sum()
    logger.info("Round 1 unmatched: %s — running spatial fallback", f"{n_unmatched:,}")

    if n_unmatched > 0:
        # Build spatial lookup: residential polygons with population columns.
        # Drop columns that already exist on entrances to avoid collisions.
        spatial_drop = [
            c for c in pop_df.columns
            if c in gdf_entrances.columns and c not in ("geometry",)
        ]
        pop_gdf_spatial = pop_df.drop(columns=spatial_drop, errors="ignore")

        unmatched_ent = gdf_demo.loc[unmatched_mask, ["entrance_id", "geometry"]].copy()

        spatial_matches = unmatched_ent.sjoin_nearest(
            pop_gdf_spatial,
            how="left",
            max_distance=10.0,
            distance_col="_dist",
        )
        # Deduplicate: one entrance can match multiple equidistant polygons — keep nearest
        spatial_matches = (
            spatial_matches.sort_values("_dist")
            .drop_duplicates(subset=["entrance_id"], keep="first")
            .drop(columns=["index_right", "_dist"], errors="ignore")
        )

        # Fill demographics into gdf_demo for the previously unmatched rows
        dem_cols = [c for c in spatial_matches.columns
                    if c not in ("entrance_id", "geometry")]
        fill_df = spatial_matches.set_index("entrance_id")[dem_cols]
        ent_idx = gdf_demo.loc[unmatched_mask, "entrance_id"]
        for col in dem_cols:
            if col not in gdf_demo.columns:
                gdf_demo[col] = np.nan
            gdf_demo.loc[unmatched_mask, col] = ent_idx.map(fill_df[col]).values

        n_filled = gdf_demo["n_dwelling_units"].notna().sum()
        logger.info(
            "After spatial fallback: %s of %s matched (%.1f%%)",
            f"{n_filled:,}", f"{len(gdf_demo):,}", n_filled / len(gdf_demo) * 100,
        )

    # --- Write new layer to GeoPackage ---
    logger.info(
        "Writing layer '%s' to %s", ENTRANCES_DEMOGRAPHICS_LAYER, INTEGRATED_BUILDINGS
    )
    gdf_demo.to_file(
        INTEGRATED_BUILDINGS,
        layer=ENTRANCES_DEMOGRAPHICS_LAYER,
        driver="GPKG",
    )

    size_mb = INTEGRATED_BUILDINGS.stat().st_size / 1_000_000
    logger.info(
        "Done — %s rows saved. GeoPackage size: %.1f MB",
        f"{len(gdf_demo):,}",
        size_mb,
    )


if __name__ == "__main__":
    main()
