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
    "boundary"
]

# Coordinate Reference Systems
CRS_DENMARK = "EPSG:25832"  # ETRS89 / UTM zone 32N (official Danish CRS)
CRS_WGS84 = "EPSG:4326"     # WGS84 (lat/lon for web maps)

# Nørrebro bounding box (approximate, in EPSG:4326)
# TODO: Replace with official boundary once downloaded
NORREBRO_BBOX = {
    "west": 12.53,
    "south": 55.68,
    "east": 12.57,
    "north": 55.71
}

# File naming patterns
RAW_FILE_PATTERN = "{source}_{dataset}_{date}.{ext}"
PROCESSED_FILE_PATTERN = "norrebro_{category}.{ext}"

# Default file extensions
DEFAULT_GEO_FORMAT = "gpkg"  # GeoPackage
DEFAULT_TABULAR_FORMAT = "csv"

# Data sources
DATA_SOURCES = {
    "sdfi": "https://dataforsyningen.dk/",
    "opendata_dk": "https://www.opendata.dk/",
    "dst": "https://www.dst.dk/",
    "osm": "https://www.openstreetmap.org/",
    "kk": "https://data.kk.dk/"
}

# Analysis parameters
WALKING_SPEED = 1.4  # m/s (5 km/h)
CYCLING_SPEED = 4.17  # m/s (15 km/h)
MAX_WALK_DISTANCE = 800  # meters (10 min walk)
MAX_CYCLE_DISTANCE = 5000  # meters (20 min cycle)
