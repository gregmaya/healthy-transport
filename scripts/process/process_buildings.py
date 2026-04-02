"""
Process BBR building attributes and DAR entrance points into a single Nørrebro GeoPackage.

Combines two layers:
- buildings: BBR building points with translated columns, use descriptions, and construction eras
- entrances: DAR address points filtered to accurate entrance types (TD/TK only)

Building use codes are mapped to English descriptions per official BBR documentation
(https://teknik.bbr.dk/kodelister).

Outputs:
    data/processed/norrebro_buildings.gpkg
        Layer 'buildings': BBR building points within 1,000m buffer of Nørrebro boundary
        Layer 'entrances': DAR entrance points (TD/TK) within 1,200m of Nørrebro

Usage:
    python scripts/process/process_buildings.py
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
    BBR_ENHED_CSV,
    BBR_OUTPUT_FILE,
    BUILDINGS_OUTPUT,
    DAR_ADRESSEPUNKT_OUTPUT,
    MAX_WALK_DISTANCE,
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

# ---------------------------------------------------------------------------
# Column mappings (Danish → English)
# ---------------------------------------------------------------------------

BBR_COLUMNS = {
    "id_lokalId": "building_id",
    "byg007Bygningsnummer": "building_number",
    "byg021BygningensAnvendelse": "use_code",
    "byg026Opførelsesår": "construction_year",
    "byg054AntalEtager": "floors",
    "byg038SamletBygningsareal": "total_area_m2",
    "byg039BygningensSamledeBoligAreal": "residential_area_m2",
    "byg040BygningensSamledeErhvervsAreal": "commercial_area_m2",
    "byg041BebyggetAreal": "footprint_area_m2",
    "byg032YdervæggensMateriale": "wall_material",
    "byg033Tagdækningsmateriale": "roof_material",
    "byg056Varmeinstallation": "heating_type",
    "husnummer": "husnummer_id",
    "kommunekode": "municipality_code",
}

DAR_COLUMNS = {
    "id_lokalId": "entrance_id",
    "oprindelse_tekniskStandard": "positioning_type",
    "status": "status",
}

# ---------------------------------------------------------------------------
# BBR building use code → English description
# Source: https://teknik.bbr.dk/kodelister (BygAnvendelse)
# ---------------------------------------------------------------------------

BBR_USE_CODES = {
    # Residential (100-199)
    110: "Farm dwelling",
    120: "Detached single-family house",
    121: "Attached single-family house",
    122: "Detached house, low-density",
    130: "Row/chain/double house",
    131: "Row/chain/cluster house",
    132: "Semi-detached house",
    140: "Apartment building",
    150: "Dormitory",
    160: "Residential care institution",
    185: "Annex to year-round residence",
    190: "Other year-round residential",
    # Production/Agriculture (200-299)
    210: "Agriculture/horticulture/extraction",
    211: "Pig stable",
    212: "Cattle/sheep stable",
    213: "Poultry stable",
    214: "Mink facility",
    215: "Greenhouse (agricultural)",
    216: "Feed/crop storage",
    217: "Machine shed",
    218: "Hay/straw storage",
    219: "Other agricultural building",
    220: "Industrial/craft",
    221: "Industrial, integrated equipment",
    222: "Industrial, no integrated equipment",
    223: "Workshop",
    229: "Other production building",
    230: "Utility (power/water/waste)",
    231: "Energy production",
    232: "Energy distribution",
    233: "Water supply",
    234: "Waste/wastewater handling",
    239: "Other utility building",
    290: "Other agriculture/industry",
    # Transport/Commerce (300-399)
    310: "Transport/garage facility",
    311: "Railway/bus operation",
    312: "Aviation facility",
    313: "Parking/transport facility",
    314: "Residential parking",
    315: "Harbour facility",
    319: "Other transport facility",
    320: "Office/retail/warehouse",
    321: "Office",
    322: "Retail",
    323: "Warehouse",
    324: "Shopping centre",
    325: "Petrol station",
    329: "Other office/retail",
    330: "Hotel/restaurant/services",
    331: "Hotel/inn/conference centre",
    332: "Bed and breakfast",
    333: "Restaurant/café",
    334: "Private services",
    339: "Other services",
    390: "Other transport/commerce",
    # Culture/Institutional (400-499)
    410: "Cinema/theatre/library/museum/church",
    411: "Cinema/theatre/concert",
    412: "Museum",
    413: "Library",
    414: "Church/religious building",
    415: "Community centre",
    416: "Amusement park",
    419: "Other cultural building",
    420: "Education/research",
    421: "Primary school",
    422: "University",
    429: "Other education/research",
    430: "Hospital/medical",
    431: "Hospital",
    432: "Hospice/treatment home",
    433: "Health centre/clinic",
    439: "Other health facility",
    440: "Daycare",
    441: "Daycare institution",
    442: "24-hour institution service building",
    443: "Barracks",
    444: "Prison",
    449: "Other institutional building",
    451: "Shelter",
    490: "Other institution",
    # Recreation (500-599)
    510: "Summer house",
    520: "Holiday facility",
    521: "Holiday centre/camping",
    522: "Holiday apartments (rental)",
    523: "Holiday apartments (private)",
    529: "Other holiday building",
    530: "Sports facility",
    531: "Sports/leisure club",
    532: "Swimming facility",
    533: "Sports hall",
    534: "Stadium/tribune",
    535: "Horse stable/riding",
    539: "Other sports building",
    540: "Allotment garden house",
    585: "Annex to holiday home",
    590: "Other recreational building",
    # Accessory/Other (900-999)
    910: "Garage",
    920: "Carport",
    930: "Shed/outbuilding",
    940: "Greenhouse (private)",
    950: "Freestanding shelter",
    960: "Freestanding garden room",
    970: "Abandoned agricultural building",
    990: "Derelict building",
    999: "Unknown building",
}

# ---------------------------------------------------------------------------
# BBR material/heating code → English description
# Source: https://instruks.bbr.dk/registreringsindhold/0/31
# ---------------------------------------------------------------------------

WALL_MATERIAL_CODES = {
    1: "Brick",
    2: "Lightweight concrete",
    3: "Fibre cement (asbestos)",
    4: "Half-timbered",
    5: "Wood cladding",
    6: "Concrete elements",
    8: "Metal sheets",
    10: "Fibre cement (asbestos-free)",
    11: "PVC",
    12: "Glass",
    80: "Unknown",
    90: "Other",
}

ROOF_MATERIAL_CODES = {
    1: "Built-up (flat roof)",
    2: "Roofing felt",
    3: "Fibre cement (asbestos)",
    4: "Cement tiles",
    5: "Clay tiles",
    6: "Metal sheets",
    7: "Thatched",
    10: "Fibre cement (asbestos-free)",
    11: "PVC",
    12: "Glass",
    20: "Green roof",
    90: "Other",
}

HEATING_TYPE_CODES = {
    1: "District heating",
    2: "Central heating (own boiler)",
    3: "Stove (wood/coal)",
    5: "Heat pump",
    6: "Central heating (dual fuel)",
    7: "Electric heating",
    8: "Gas radiators",
    9: "No heating",
    99: "Unknown",
}


# ---------------------------------------------------------------------------
# Derived column helpers
# ---------------------------------------------------------------------------


def get_use_category(code):
    """Map a BBR use code to a broad category."""
    try:
        code = int(code)
    except (ValueError, TypeError):
        return None
    if 100 <= code < 200:
        return "Residential"
    if 200 <= code < 300:
        return "Production/Agriculture"
    if 310 <= code < 320:
        return "Transport"
    if 320 <= code < 330:
        return "Office/Retail"
    if 330 <= code < 340:
        return "Services"
    if 300 <= code < 400:
        return "Commerce/Transport"
    if 400 <= code < 500:
        return "Culture/Institutional"
    if 500 <= code < 600:
        return "Recreation"
    if 900 <= code < 1000:
        return "Accessory/Other"
    return None


def get_construction_era(year):
    """Map a construction year to a historical era."""
    try:
        year = int(year)
    except (ValueError, TypeError):
        return None
    if year < 1850:
        return "Before 1850"
    if year < 1900:
        return "1850-1900"
    if year < 1930:
        return "1900-1930"
    if year < 1960:
        return "1930-1960"
    if year < 1980:
        return "1960-1980"
    if year < 2000:
        return "1980-2000"
    return "After 2000"


def map_codes(series, code_map):
    """Map a numeric code series to descriptions using a lookup dict."""
    return series.apply(
        lambda x: code_map.get(int(x), None) if pd.notnull(x) else None
    )


# ---------------------------------------------------------------------------
# Main processing
# ---------------------------------------------------------------------------


def main():
    logger.info("=" * 60)
    logger.info("PROCESS BUILDINGS (BBR + DAR)")
    logger.info("=" * 60)

    # Load boundary
    boundary = gpd.read_file(NORREBRO_BOUNDARY_FILE, layer=NORREBRO_BOUNDARY_LAYER)
    logger.info("Loaded boundary: CRS %s", boundary.crs)

    # Buffer for DAR entrances (loaded from disk, includes all-Copenhagen data)
    buffered = boundary.buffer(MAX_WALK_DISTANCE).union_all()
    # Scoring buffer for BBR buildings — extends past boundary for edge-effect correction
    scoring_buffered = boundary.buffer(SCORING_BUFFER_M).union_all()
    bbox = box(*gpd.GeoSeries([buffered], crs=boundary.crs).total_bounds)

    # === Layer 1: buildings (BBR) ===
    logger.info("-" * 60)
    logger.info("LAYER 1: buildings (BBR, clipped to %dm buffer)", SCORING_BUFFER_M)
    logger.info("-" * 60)

    bbr = gpd.read_file(BBR_OUTPUT_FILE)
    logger.info("Loaded %d BBR features", len(bbr))

    # Clip to scoring buffer (re-download with wider bbox if count is unexpectedly low)
    bbr = bbr[bbr.intersects(scoring_buffered)]
    logger.info("Clipped to %d buildings within %dm buffer", len(bbr), SCORING_BUFFER_M)

    # Select and rename columns
    bbr_cols = [c for c in BBR_COLUMNS if c in bbr.columns]
    bbr = bbr[bbr_cols + ["geometry"]].rename(columns=BBR_COLUMNS)

    # Convert use_code to numeric for mapping
    bbr["use_code"] = pd.to_numeric(bbr["use_code"], errors="coerce")

    # Add derived columns
    bbr["use_description"] = map_codes(bbr["use_code"], BBR_USE_CODES)
    bbr["use_category"] = bbr["use_code"].apply(get_use_category)

    bbr["construction_year"] = pd.to_numeric(bbr["construction_year"], errors="coerce")
    bbr["construction_era"] = bbr["construction_year"].apply(get_construction_era)

    # Map material/heating codes to English descriptions
    bbr["wall_material"] = map_codes(bbr["wall_material"], WALL_MATERIAL_CODES)
    bbr["roof_material"] = map_codes(bbr["roof_material"], ROOF_MATERIAL_CODES)
    bbr["heating_type"] = map_codes(bbr["heating_type"], HEATING_TYPE_CODES)

    # Join antal_boliger from BBR Enhed (residential unit count per building)
    if BBR_ENHED_CSV.exists():
        enhed = pd.read_csv(BBR_ENHED_CSV)
        bbr = bbr.merge(enhed[["building_id", "antal_boliger"]], on="building_id", how="left")
        matched = bbr["antal_boliger"].notna().sum()
        total_units = int(bbr["antal_boliger"].sum(min_count=1) or 0)
        logger.info(
            "Joined antal_boliger: %d/%d buildings matched (%d total units)",
            matched, len(bbr), total_units,
        )
    else:
        bbr["antal_boliger"] = None
        logger.warning(
            "Enhed CSV not found (%s). Run download_bbr_enhed.py first. "
            "antal_boliger set to null.",
            BBR_ENHED_CSV,
        )

    # Log use category distribution
    logger.info("Use category distribution:")
    for cat, count in bbr["use_category"].value_counts().items():
        logger.info("  %s: %d", cat, count)

    unmapped = bbr["use_description"].isna() & bbr["use_code"].notna()
    if unmapped.any():
        missing_codes = bbr.loc[unmapped, "use_code"].unique()
        logger.warning("Unmapped use codes: %s", missing_codes)

    # Log construction era distribution
    logger.info("Construction era distribution:")
    for era, count in bbr["construction_era"].value_counts().items():
        logger.info("  %s: %d", era, count)

    # Save
    BUILDINGS_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    bbr.to_file(BUILDINGS_OUTPUT, layer="buildings", driver="GPKG")
    logger.info("Saved layer 'buildings': %d features, %d columns", len(bbr), len(bbr.columns))

    # === Layer 2: entrances (DAR) ===
    logger.info("-" * 60)
    logger.info("LAYER 2: entrances (DAR, clipped to %dm buffer)", MAX_WALK_DISTANCE)
    logger.info("-" * 60)

    dar = gpd.read_file(DAR_ADRESSEPUNKT_OUTPUT, mask=bbox)
    logger.info("Loaded %d DAR features within bbox", len(dar))

    # Filter to accurate entrance types only (TD=door, TK=facade)
    dar = dar[dar["oprindelse_tekniskStandard"].isin(["TD", "TK"])]
    logger.info("Filtered to %d valid entrances (TD/TK)", len(dar))

    # Clip to 800m buffer
    dar = dar[dar.intersects(buffered)]
    logger.info("Clipped to %d entrances within %dm buffer", len(dar), MAX_WALK_DISTANCE)

    # Select and rename columns
    dar_cols = [c for c in DAR_COLUMNS if c in dar.columns]
    dar = dar[dar_cols + ["geometry"]].rename(columns=DAR_COLUMNS)

    # Log positioning type distribution
    logger.info("Positioning type distribution:")
    for ptype, count in dar["positioning_type"].value_counts().items():
        logger.info("  %s: %d", ptype, count)

    dar.to_file(BUILDINGS_OUTPUT, layer="entrances", driver="GPKG", mode="a")
    logger.info("Saved layer 'entrances': %d features, %d columns", len(dar), len(dar.columns))

    # === Summary ===
    logger.info("=" * 60)
    logger.info("DONE")
    logger.info("=" * 60)
    size_mb = BUILDINGS_OUTPUT.stat().st_size / (1024 * 1024)
    logger.info("Output: %s (%.1f MB)", BUILDINGS_OUTPUT, size_mb)


if __name__ == "__main__":
    main()
