"""
Configuration and constants for the Nørrebro analysis project.
"""

from pathlib import Path

# Project directories
PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
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
BBR_ID_COLUMNS = ["id_lokalId", "id.lokalId", "lokalId", "fid"]
BBR_KEY_ATTRIBUTES = {
    "use": "byg021BygningensAnvendelse",   # Building use/class code
    "area": "byg038SamletBygningsareal",   # Total built area (m²)
    "year": "byg026Opførelsesår",          # Construction year
    "municipality": "kommunekode",         # Municipality code
    "floors": "byg054AntalEtager",         # Number of floors
    "residential_area": "byg039BygningensSamledeBoligAreal",  # Residential area (m²)
    "commercial_area": "byg040BygningensSamledeErhvervsAreal",  # Commercial area (m²)
    "footprint_area": "byg041BebyggetAreal",  # Built footprint area (m²)
}
BBR_RAW_DIR = RAW_DATA_DIR / "bbr"
BBR_OUTPUT_FILE = BBR_RAW_DIR / "norrebro_bbr_buildings.gpkg"

# DAR (Danmarks Adresseregister) configuration
DAR_ENTITIES = {
    "husnummer": "Husnummer",        # House numbers (links to buildings)
    "adressepunkt": "Adressepunkt",  # Address/entrance point coordinates
}
DAR_RAW_DIR = RAW_DATA_DIR / "dar"
DAR_ADRESSEPUNKT_OUTPUT = DAR_RAW_DIR / "norrebro_dar_adressepunkt.gpkg"
DAR_HUSNUMMER_OUTPUT = DAR_RAW_DIR / "norrebro_dar_husnummer.gpkg"

# Building footprints configuration
INSPIRE_BUILDINGS_FILE = DATA_DIR / "buildings" / "building_inspire.gpkg"
BUILDING_FOOTPRINTS_OUTPUT = PROCESSED_DATA_DIR / "norrebro_building_footprints.gpkg"

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

# GTFS route type mapping
GTFS_ROUTE_TYPES = {
    "bus": [3, *range(700, 800)],
    "metro": [1, *range(400, 500)],
    "train": [2, *range(100, 200)],
}

# Analysis parameters
WALKING_SPEED = 1.4  # m/s (5 km/h)
CYCLING_SPEED = 4.17  # m/s (15 km/h)
MAX_WALK_DISTANCE = 800  # meters (10 min walk)
MAX_CYCLE_DISTANCE = 5000  # meters (20 min cycle)
NETWORK_BUFFER_M = MAX_WALK_DISTANCE  # buffer around boundary for network download
