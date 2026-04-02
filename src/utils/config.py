"""
Configuration and constants for the Nørrebro analysis project.
"""

from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
INTEGRATED_DATA_DIR = DATA_DIR / "integrated"
REPORTS_DIR = PROJECT_ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"

# Data categories
DATA_CATEGORIES = [
    "buildings",
    "roads",
    "cycling",
    "population",
    "health",
    "transport",
    "greenspaces",
    "boundary",
]

# Coordinate Reference Systems
CRS_DENMARK = "EPSG:25832"  # ETRS89 / UTM zone 32N (official Danish CRS)
CRS_WGS84 = "EPSG:4326"  # WGS84 (lat/lon for web maps)

# Study area
COPENHAGEN_MUNICIPALITY_CODE = "0101"
NORREBRO_BOUNDARY_FILE = PROCESSED_DATA_DIR / "norrebro_boundary.gpkg"
NORREBRO_BOUNDARY_LAYER = "norrebro_boundary"
NORREBRO_NEIGHBOURHOODS_LAYER = "neighbourhoods"

# File naming patterns
RAW_FILE_PATTERN = "{source}_{dataset}_{date}.{ext}"
PROCESSED_FILE_PATTERN = "norrebro_{category}.{ext}"

# Default file extensions
DEFAULT_GEO_FORMAT = "gpkg"  # GeoPackage
DEFAULT_TABULAR_FORMAT = "csv"

# Data sources (general portals)
DATA_SOURCES = {
    "sdfi": "https://dataforsyningen.dk/",
    "opendata_dk": "https://www.opendata.dk/",
    "dst": "https://www.dst.dk/",
    "osm": "https://www.openstreetmap.org/",
    "kk": "https://data.kk.dk/",
}

# Datafordeler API endpoints
DATAFORDELER_WFS = {
    "bbr": "https://wfs.datafordeler.dk/BBR/BBR_WFS/1.0.0/WFS",
    "dagi": "https://wfs.datafordeler.dk/DAGIM/DAGI_10MULTIGEOM_GMLSFP/1.0.0/WFS",
    "matriklen": "https://wfs.datafordeler.dk/MAT/MAT_WFS/1.0.0/WFS",
}
DATAFORDELER_FILE_DOWNLOAD_URL = "https://api.datafordeler.dk/FileDownloads/GetFile"

# BBR (Bygnings- og Boligregistret) configuration
BBR_LAYER = "bbr_v001:bygning_current"
BBR_ENHED_LAYER = "bbr_v001:enhed_current"  # Dwelling/unit layer
BBR_ID_COLUMNS = ["id_lokalId", "id.lokalId", "lokalId", "fid"]
BBR_KEY_ATTRIBUTES = {
    "use": "byg021BygningensAnvendelse",  # Building use/class code
    "area": "byg038SamletBygningsareal",  # Total built area (m²)
    "year": "byg026Opførelsesår",  # Construction year
    "municipality": "kommunekode",  # Municipality code
    "floors": "byg054AntalEtager",  # Number of floors
    "residential_area": "byg039BygningensSamledeBoligAreal",  # Residential area (m²)
    "commercial_area": "byg040BygningensSamledeErhvervsAreal",  # Commercial area (m²)
    "footprint_area": "byg041BebyggetAreal",  # Built footprint area (m²)
}
BBR_RAW_DIR = RAW_DATA_DIR / "bbr"
BBR_OUTPUT_FILE = BBR_RAW_DIR / "norrebro_bbr_buildings.gpkg"
BBR_ENHED_OUTPUT_FILE = BBR_RAW_DIR / "norrebro_bbr_enhed.gpkg"
BBR_ENHED_CSV = BBR_RAW_DIR / "norrebro_bbr_enhed.csv"  # building_id → antal_boliger

# DAR (Danmarks Adresseregister) configuration
DAR_ENTITIES = {
    "husnummer": "Husnummer",  # House numbers (links to buildings)
    "adressepunkt": "Adressepunkt",  # Address/entrance point coordinates
}
DAR_RAW_DIR = RAW_DATA_DIR / "dar"
DAR_ADRESSEPUNKT_OUTPUT = DAR_RAW_DIR / "norrebro_dar_adressepunkt.gpkg"
DAR_HUSNUMMER_OUTPUT = DAR_RAW_DIR / "norrebro_dar_husnummer.gpkg"

# Building footprints configuration
INSPIRE_BUILDINGS_FILE = DATA_DIR / "buildings" / "building_inspire.gpkg"
BUILDING_FOOTPRINTS_OUTPUT = PROCESSED_DATA_DIR / "norrebro_building_footprints.gpkg"
BUILDINGS_OUTPUT = PROCESSED_DATA_DIR / "norrebro_buildings.gpkg"

# Pedestrian network configuration
NETWORK_RAW_DIR = RAW_DATA_DIR / "network"
PEDESTRIAN_NETWORK_GRAPHML = NETWORK_RAW_DIR / "norrebro_pedestrian_network.graphml"
PEDESTRIAN_NETWORK_GPKG = PROCESSED_DATA_DIR / "norrebro_pedestrian_network.gpkg"

# Public transport configuration
TRANSPORT_RAW_DIR = RAW_DATA_DIR / "transport"
GTFS_ZIP_FILE = TRANSPORT_RAW_DIR / "rejseplanen_gtfs.zip"
GTFS_DOWNLOAD_URL = "https://www.rejseplanen.info/labs/GTFS.zip"
TRANSPORT_STOPS_OUTPUT = PROCESSED_DATA_DIR / "norrebro_transport_stops.gpkg"
TRANSPORT_BUFFER_M = 10_000  # 10 km buffer for transport stop coverage

# Cycling infrastructure configuration (Copenhagen Municipality WFS)
KK_WFS_URL = "https://wfs-kbhkort.kk.dk/k101/ows"
KK_CYCLING_LAYERS = {
    "cykelsti": "k101:cykelsti",
    "cykeldata": "k101:cykeldata",
    "cykelstativ": "k101:cykelstativ",
}
CYCLING_RAW_DIR = RAW_DATA_DIR / "cycling"
CYCLING_OUTPUT = PROCESSED_DATA_DIR / "norrebro_cycling.gpkg"

# Green spaces configuration (Copenhagen Municipality WFS)
KK_GREENSPACE_LAYERS = {
    "parkregister": "k101:parkregister",
    "park_groent_omr_oversigtskort": "k101:park_groent_omr_oversigtskort",
    "legeplads": "k101:legeplads",
}
GREENSPACES_RAW_DIR = RAW_DATA_DIR / "greenspaces"
GREENSPACES_OUTPUT = PROCESSED_DATA_DIR / "norrebro_greenspaces.gpkg"

# Health data configuration
HEALTH_RAW_DIR = RAW_DATA_DIR / "health"
HEALTH_ESUNDHED_FILE = HEALTH_RAW_DIR / "esundhed_kroniske_sygdomme_2010_2025.xlsx"
HEALTH_SUNDHEDSPROFIL_FILE = HEALTH_RAW_DIR / "copenhagen_sundhedsprofil_indicators.csv"
HEALTH_DODA1_FILE = HEALTH_RAW_DIR / "statbank_doda1_causes_of_death.csv"
HEALTH_FOD207_FILE = HEALTH_RAW_DIR / "statbank_fod207_deaths_by_municipality.csv"
HEALTH_HEAT_GUIDE_FILE = HEALTH_RAW_DIR / "WHO_HEAT_user_guide_2024.pdf"
HEALTH_OUTPUT = PROCESSED_DATA_DIR / "norrebro_health.csv"
HEALTH_DANSKERNESSUNDHED_DIR = HEALTH_RAW_DIR / "danskernessundhed"
HEAT_INPUTS_OUTPUT = PROCESSED_DATA_DIR / "heat_inputs.json"
HEALTH_SURVEY_BY_AGE_OUTPUT = PROCESSED_DATA_DIR / "health_survey_by_age.csv"
HEALTH_SURVEY_BY_MUNICIPALITY_OUTPUT = (
    PROCESSED_DATA_DIR / "health_survey_by_municipality.csv"
)
HEALTH_CAUSES_OF_DEATH_OUTPUT = PROCESSED_DATA_DIR / "health_causes_of_death.csv"
HEALTH_DEATHS_BY_MUNICIPALITY_OUTPUT = (
    PROCESSED_DATA_DIR / "health_deaths_by_municipality.csv"
)

# GTFS route type mapping
GTFS_ROUTE_TYPES = {
    "bus": [3, *range(700, 800)],
    "metro": [1, *range(400, 500)],
    "train": [2, *range(100, 200)],
}

# Web export
WEB_DATA_DIR = DATA_DIR / "web"
WEB_SEGMENTS_GEOJSON = WEB_DATA_DIR / "norrebro_bus_segments_scored.geojson"
WEB_BOUNDARY_GEOJSON = WEB_DATA_DIR / "norrebro_boundary.geojson"
WEB_STOPS_GEOJSON = WEB_DATA_DIR / "norrebro_stops.geojson"

# Integrated data outputs
INTEGRATED_BUILDINGS = INTEGRATED_DATA_DIR / "norrebro_buildings.gpkg"
POPULATION_CSV = PROCESSED_DATA_DIR / "norrebro_neighbourhoods_population.csv"
DWELLINGS_CSV = PROCESSED_DATA_DIR / "norrebro_neighbourhoods_dwellings.csv"
ENTRANCES_DEMOGRAPHICS_LAYER = "entrances_demographics"
ENTRANCES_ACCESSIBILITY_LAYER = "entrances_accessibility"

# Analysis parameters
WALKING_SPEED = 1.4  # m/s (5 km/h)
CYCLING_SPEED = 4.17  # m/s (15 km/h)
MAX_WALK_DISTANCE = 1200  # meters (10 min walk)
MAX_CYCLE_DISTANCE = 5000  # meters (20 min cycle)
NETWORK_BUFFER_M = MAX_WALK_DISTANCE  # buffer around boundary for network download

# Bus segment scoring — per-group walking speeds (m/s)
# Sources:
#   Bohannon (1997): comfortable speed meta-analysis for working-age adults → 1.40 m/s
#   Lusardi et al. (2003) + Winter et al. (1990): community-dwelling elderly → 0.90 m/s
#   Plaut (2005) + Petzinger et al. (2015): school-age children → 1.00 m/s
SCORING_WALKING_SPEEDS = {
    "working_age": 1.40,  # m/s — Bohannon (1997)
    "elderly":     0.90,  # m/s — Lusardi et al. (2003)
    "children":    1.00,  # m/s — Plaut (2005)
    "catchment":   1.40,  # m/s — same as working age (area-based, not population-weighted)
}

# Maximum walk time per group (minutes), anchored to WHO GAPPA (2018) 10-minute walk target.
# Adjusted downward for groups with shorter effective walk radii.
SCORING_WALK_MINUTES = {
    "working_age": 10,
    "elderly":      8,
    "children":     7,
    "catchment":   10,
}

# Gaussian B(t) curve parameters in minutes:
#   peak_min  — time at which health benefit peaks
#   sigma_min — standard deviation (controls width of peak)
# Peak is set at the midpoint of max_minutes, modelling rising cardiovascular benefit
# in the first half of the walk and deterrence-driven decay in the second half.
SCORING_DECAY_PARAMS = {
    "working_age": {"peak_min": 5.0,  "sigma_min": 2.4},
    "elderly":     {"peak_min": 4.0,  "sigma_min": 2.0},
    "children":    {"peak_min": 3.5,  "sigma_min": 1.75},
    "catchment":   {"peak_min": 5.0,  "sigma_min": 2.4},
}
