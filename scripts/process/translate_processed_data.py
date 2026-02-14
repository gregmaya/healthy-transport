"""
Translate Danish column names and content values to English in processed GeoPackages.

Scans all processed GeoPackage files and applies translations where needed.
Currently translates:
- norrebro_cycling.gpkg: column names + content for both cykeldata and cykelstativ layers
- norrebro_greenspaces.gpkg: content for park_type in parks layer
- norrebro_boundary.gpkg: column rename (navn → name)

Other processed files (greenspaces, transport, building footprints, network) are already in English.

Outputs:
    Overwrites existing files in data/processed/ with English versions.

Usage:
    python scripts/process/translate_processed_data.py
"""

import logging
import sys
from pathlib import Path

import geopandas as gpd
import fiona

# Add project root to path for config imports
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from utils.config import (
    CYCLING_OUTPUT,
    GREENSPACES_OUTPUT,
    NORREBRO_BOUNDARY_FILE,
    NORREBRO_BOUNDARY_LAYER,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Translation dictionaries
# ---------------------------------------------------------------------------

# === CYCLING: cykeldata layer ===

CYKELDATA_COLUMNS = {
    "rute_nr": "route_number",
    "rutenavn": "route_name",
    "kategori": "category",
    "under_kategori": "sub_category",
    "kommune": "municipality",
}

CYKELDATA_CONTENT = {
    "category": {
        "Cykelsti": "Cycle path",
        "Supercykelsti": "Super cycle highway",
        "Grøn": "Green route",
        "Cykelmulighed": "Cycling option",
        "Cykelrute": "Cycle route",
        "Cykelgade": "Cycle street",
        "Lokal cykel- og gangforbindelse": "Local cycle and walk connection",
    },
    "sub_category": {
        "P": "Protected",
        "Grøn": "Green",
        "Cykelsti": "Cycle path",
        "P Cykelsti": "Protected cycle path",
    },
    "status": {
        "Eksisterende": "Existing",
        "Planlagt": "Planned",
        "Projekteret": "Projected",
    },
    "standard": {
        "Grøn": "Green",
        "Gul": "Yellow",
        "Rød": "Red",
    },
}

# === CYCLING: cykelstativ layer ===

CYKELSTATIV_COLUMNS = {
    "vejkode": "street_code",
    "vejnavn": "street_name",
    "bydel": "district",
    "stativ_type": "rack_type",
    "stativ_placering": "rack_placement",
    "stativ_udformning": "rack_design",
    "cykler_retning": "bike_direction",
    "antal_pladser": "num_spaces",
    "stativ_tilstand": "rack_condition",
    "stativ_ejer": "rack_owner",
    "stativ_foto": "rack_photo",
    "bemaerkning": "remark",
    "reg_metode": "registration_method",
    "reg_dato": "registration_date",
    "rettet_dato": "correction_date",
    "projektbeskrivelse": "project_description",
    "stativ_fjernet": "rack_removed",
}

CYKELSTATIV_CONTENT = {
    "rack_type": {
        "Andet": "Other",
        "Ikke registreret": "Not registered",
        "Bycykelstativ": "City bike rack",
        "Ladcykel": "Cargo bike",
        "Smedemodel": "Blacksmith model",
    },
    "rack_placement": {
        "På fortovsudvidelse": "On sidewalk extension",
        "På facade": "On facade",
        "Tæt på facade": "Close to facade",
        "På plads": "On square",
        "På fortov": "On sidewalk",
        "På gadeareal": "On street area",
        "Ikke registreret": "Not registered",
        "Andet": "Other",
    },
    "rack_design": {
        "Enkeltsidet": "Single-sided",
        "Dobbeltsidet": "Double-sided",
        "Ikke registreret": "Not registered",
        "Rundt": "Circular",
    },
    "bike_direction": {
        "Vinkelret": "Perpendicular",
        "Skråt 45 grader": "Angled 45 degrees",
        "Skråt 30 grader": "Angled 30 degrees",
        "Ikke registreret": "Not registered",
        "Andet": "Other",
    },
    "rack_condition": {
        "Ikke registreret": "Not registered",
        "Skal repareres": "Needs repair",
    },
    "rack_owner": {
        "Offentligt": "Public",
        "Privat": "Private",
        "Ikke registreret": "Not registered",
    },
    "registration_method": {
        "Digitaliseret manuelt": "Digitized manually",
        "Indmålt med GPS": "Measured with GPS",
        "Ikke registreret": "Not registered",
    },
}

# === GREENSPACES: parks layer ===

PARKS_CONTENT = {
    "park_type": {
        "Andet grønt område": "Other green area",
        "Lokale parker": "Local parks",
        "Regionale parker": "Regional parks",
        "Vandflader": "Water surfaces",
        "Kirkegårde": "Cemeteries",
        "Idrætsanlæg": "Sports facilities",
        "Planlagte grønne områder": "Planned green areas",
        "Naturområder": "Nature areas",
        "Haveanlæg": "Garden facilities",
    },
}

# === BOUNDARY ===

BOUNDARY_COLUMNS = {
    "navn": "name",
}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def translate_layer(gdf, column_map, content_map):
    """Rename columns and translate content values in a GeoDataFrame.

    Returns the translated GeoDataFrame and a dict of changes made.
    """
    changes = {"columns_renamed": [], "content_translated": {}}

    # Rename columns
    cols_to_rename = {k: v for k, v in column_map.items() if k in gdf.columns}
    if cols_to_rename:
        gdf = gdf.rename(columns=cols_to_rename)
        changes["columns_renamed"] = list(cols_to_rename.items())
        for old, new in cols_to_rename.items():
            logger.info(f"  Column renamed: {old} → {new}")

    # Translate content values
    for col, mapping in content_map.items():
        if col not in gdf.columns:
            continue
        before = gdf[col].copy()
        gdf[col] = gdf[col].replace(mapping)
        n_changed = (before != gdf[col]).sum()
        if n_changed > 0:
            changes["content_translated"][col] = n_changed
            logger.info(f"  Content translated: {col} ({n_changed} values)")

    return gdf, changes


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def translate_cycling():
    """Translate cycling GeoPackage layers."""
    logger.info(f"Processing: {CYCLING_OUTPUT.name}")

    # cykeldata layer
    logger.info("  Layer: cykeldata")
    cykeldata = gpd.read_file(CYCLING_OUTPUT, layer="cykeldata")
    row_count = len(cykeldata)
    cykeldata, changes_data = translate_layer(cykeldata, CYKELDATA_COLUMNS, CYKELDATA_CONTENT)
    logger.info(f"  Rows: {row_count} (unchanged)")

    # cykelstativ layer
    logger.info("  Layer: cykelstativ")
    cykelstativ = gpd.read_file(CYCLING_OUTPUT, layer="cykelstativ")
    row_count_stativ = len(cykelstativ)
    cykelstativ, changes_stativ = translate_layer(cykelstativ, CYKELSTATIV_COLUMNS, CYKELSTATIV_CONTENT)
    logger.info(f"  Rows: {row_count_stativ} (unchanged)")

    # Write back (first layer overwrites file, second appends)
    cykeldata.to_file(CYCLING_OUTPUT, layer="cykeldata", driver="GPKG", mode="w")
    cykelstativ.to_file(CYCLING_OUTPUT, layer="cykelstativ", driver="GPKG", mode="a")

    size_mb = CYCLING_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info(f"  Saved: {CYCLING_OUTPUT} ({size_mb:.1f} MB)")


def translate_greenspaces():
    """Translate greenspaces GeoPackage layers."""
    logger.info(f"Processing: {GREENSPACES_OUTPUT.name}")

    # Read all layers
    layers = fiona.listlayers(GREENSPACES_OUTPUT)
    logger.info(f"  Layers found: {layers}")

    layer_data = {}
    for layer_name in layers:
        if layer_name == "layer_styles":
            continue
        layer_data[layer_name] = gpd.read_file(GREENSPACES_OUTPUT, layer=layer_name)

    # Translate parks layer
    if "parks" in layer_data:
        logger.info("  Layer: parks")
        gdf = layer_data["parks"]
        row_count = len(gdf)
        gdf, changes = translate_layer(gdf, {}, PARKS_CONTENT)
        layer_data["parks"] = gdf
        logger.info(f"  Rows: {row_count} (unchanged)")

    # Write back all layers
    first = True
    for layer_name, gdf in layer_data.items():
        mode = "w" if first else "a"
        gdf.to_file(GREENSPACES_OUTPUT, layer=layer_name, driver="GPKG", mode=mode)
        first = False

    size_mb = GREENSPACES_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info(f"  Saved: {GREENSPACES_OUTPUT} ({size_mb:.1f} MB)")


def translate_boundary():
    """Translate boundary GeoPackage (only norrebro_boundary layer)."""
    logger.info(f"Processing: {NORREBRO_BOUNDARY_FILE.name}")

    # List all layers
    layers = fiona.listlayers(NORREBRO_BOUNDARY_FILE)
    logger.info(f"  Layers found: {layers}")

    # Read all layers first
    layer_data = {}
    for layer_name in layers:
        if layer_name == "layer_styles":
            continue  # QGIS internal table, skip
        layer_data[layer_name] = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=layer_name)

    # Translate the boundary layer
    if NORREBRO_BOUNDARY_LAYER in layer_data:
        logger.info(f"  Layer: {NORREBRO_BOUNDARY_LAYER}")
        gdf = layer_data[NORREBRO_BOUNDARY_LAYER]
        row_count = len(gdf)
        gdf, changes = translate_layer(gdf, BOUNDARY_COLUMNS, {})
        layer_data[NORREBRO_BOUNDARY_LAYER] = gdf
        logger.info(f"  Rows: {row_count} (unchanged)")

    # Write back all layers
    first = True
    for layer_name, gdf in layer_data.items():
        mode = "w" if first else "a"
        gdf.to_file(NORREBRO_BOUNDARY_FILE, layer=layer_name, driver="GPKG", mode=mode)
        first = False

    size_mb = NORREBRO_BOUNDARY_FILE.stat().st_size / (1024 * 1024)
    logger.info(f"  Saved: {NORREBRO_BOUNDARY_FILE} ({size_mb:.1f} MB)")


def main():
    logger.info("=== Translating Danish → English in processed GeoPackages ===")

    translate_cycling()
    translate_greenspaces()
    translate_boundary()

    logger.info("=== Translation complete ===")


if __name__ == "__main__":
    main()
