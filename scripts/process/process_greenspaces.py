"""
Process Copenhagen green spaces into a single Nørrebro GeoPackage.

Combines two layers (clipped to 1000m buffer around Nørrebro, matching
SCORING_BUFFER_M so that bus stops near the district edge can reach
Frederiksberg parks during scoring):
- parkregister: Official park registry polygons
- legeplads: Playground points

Column names are translated from Danish to English for readability.

Outputs:
    data/processed/norrebro_greenspaces.gpkg
        Layer 'parks': park polygons within 1000m of Nørrebro
        Layer 'playgrounds': playground points within 1000m of Nørrebro

Usage:
    python scripts/process/process_greenspaces.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd
from shapely import box

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    GREENSPACES_OUTPUT,
    GREENSPACES_RAW_DIR,
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

PARKREGISTER_COLUMNS = {
    "areal_id": "area_id",
    "park_id": "park_id",
    "navn_arealer": "area_name",
    "parknummer": "park_number",
    "parktype": "park_type",
    "navn_parker": "park_name",
    "undernavn": "sub_name",
    "bydelsnavn": "district",
    "ejerforhold": "ownership_type",
    "ejer": "owner",
    "areal": "area_m2",
    "fredning": "protection_status",
    "fredning_beskriv": "protection_description",
    "fredning_bygning": "building_protection",
    "fredning_fortid": "historical_protection",
    "udviklingsplan": "development_plan",
    "udviklingsaar": "development_year",
    "besoegstal": "visitor_count",
    "brugerunder": "user_surveys",
    "beskrivelse": "description",
    "link": "link",
    "opland_300": "catchment_pop_300m",
    "opland_875": "catchment_pop_875m",
    "registreringsdato": "registration_date",
    "rettelsesdato": "correction_date",
}

LEGEPLADS_COLUMNS = {
    "legeplads_id": "playground_id",
    "navn": "name",
    "adressebeskrivelse": "address",
    "bydel": "district",
    "legeplads_type": "playground_type",
    "aldersgruppe": "age_group",
    "ejer": "owner",
    "beskrivelse": "description",
    "link": "link",
    "lokaludvalgnavn": "local_council",
}


def main():
    logger.info("=" * 60)
    logger.info("PROCESS GREEN SPACES")
    logger.info("=" * 60)

    # Load boundary and create 1000m buffer (matching SCORING_BUFFER_M so that
    # bus stops near the district edge can reach Frederiksberg parks during scoring)
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info("Loaded boundary: CRS %s", boundary.crs)

    buffered = boundary.buffer(SCORING_BUFFER_M).union_all()
    bbox = box(*gpd.GeoSeries([buffered], crs=boundary.crs).total_bounds)

    # --- Layer 1: parks (clipped to 1000m buffer) ---
    logger.info("-" * 60)
    logger.info("LAYER 1: parks (clipped to %dm buffer)", SCORING_BUFFER_M)
    logger.info("-" * 60)

    parks_path = GREENSPACES_RAW_DIR / "kk_parkregister.gpkg"
    parks = gpd.read_file(parks_path, mask=bbox)
    logger.info("Loaded %d park features within bbox", len(parks))

    parks = parks[parks.intersects(buffered)]
    logger.info("Clipped to %d parks within %dm buffer", len(parks), SCORING_BUFFER_M)

    # Keep only mapped columns + geometry, rename to English
    parks_cols = [c for c in PARKREGISTER_COLUMNS if c in parks.columns]
    parks = parks[parks_cols + ["geometry"]].rename(columns=PARKREGISTER_COLUMNS)

    for val, count in parks["park_type"].value_counts().items():
        logger.info("  %s: %d", val, count)

    # --- Supplement: Frederiksberg municipality parks ---
    # kk_parkregister covers Copenhagen only; kk_park_groent_omr_oversigtskort
    # includes all municipalities. Add Frederiksberg polygons within the buffer.
    logger.info("-" * 60)
    logger.info("SUPPLEMENT: Frederiksberg parks from overview layer")
    logger.info("-" * 60)

    overview_path = GREENSPACES_RAW_DIR / "kk_park_groent_omr_oversigtskort.gpkg"
    overview = gpd.read_file(overview_path, mask=bbox)
    frb = overview[overview["kommune"] == "Frederiksberg"]
    frb = frb[frb.intersects(buffered)].copy()
    logger.info("Found %d Frederiksberg park polygons within buffer", len(frb))

    if len(frb) > 0:
        frb = frb[["geometry"]].copy()
        frb["park_type"] = "Frederiksberg"
        frb["park_name"] = None
        frb["area_m2"] = frb.geometry.area.round(1)
        # Fill all remaining schema columns with NaN so concat aligns
        for col in parks.columns:
            if col not in frb.columns:
                frb[col] = None
        frb = frb[parks.columns]  # align column order
        parks = pd.concat([parks, frb], ignore_index=True)
        logger.info("Total after merge: %d park features", len(parks))

    GREENSPACES_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    if GREENSPACES_OUTPUT.exists():
        GREENSPACES_OUTPUT.unlink()
    parks.to_file(GREENSPACES_OUTPUT, layer="parks", driver="GPKG")
    logger.info("Saved layer 'parks': %d features", len(parks))

    # --- Layer 2: playgrounds (clipped to 1000m buffer) ---
    logger.info("-" * 60)
    logger.info("LAYER 2: playgrounds (clipped to %dm buffer)", SCORING_BUFFER_M)
    logger.info("-" * 60)

    playgrounds_path = GREENSPACES_RAW_DIR / "kk_legeplads.gpkg"
    playgrounds = gpd.read_file(playgrounds_path, mask=bbox)
    logger.info("Loaded %d playground features within bbox", len(playgrounds))

    playgrounds = playgrounds[playgrounds.intersects(buffered)]
    logger.info("Clipped to %d playgrounds within %dm buffer", len(playgrounds), SCORING_BUFFER_M)

    # Keep only mapped columns + geometry, rename to English
    pg_cols = [c for c in LEGEPLADS_COLUMNS if c in playgrounds.columns]
    playgrounds = playgrounds[pg_cols + ["geometry"]].rename(columns=LEGEPLADS_COLUMNS)

    for val, count in playgrounds["playground_type"].value_counts().items():
        logger.info("  %s: %d", val, count)

    playgrounds.to_file(GREENSPACES_OUTPUT, layer="playgrounds", driver="GPKG", mode="a")
    logger.info("Saved layer 'playgrounds': %d features", len(playgrounds))

    # --- Summary ---
    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)
    size_mb = GREENSPACES_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info("Output: %s (%.1f MB)", GREENSPACES_OUTPUT, size_mb)


if __name__ == "__main__":
    main()
